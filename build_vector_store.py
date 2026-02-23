"""
Metadata-to-FAISS pipeline for PostgreSQL schemas (healthcare, retail, finance).
Extracts table/column metadata and comments, builds embeddings with sentence-transformers,
and stores them in per-schema FAISS indexes and metadata JSON.
Run: python build_vector_store.py
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()

# Output directories
FAISS_INDEX_DIR = Path("faiss_indexes")
METADATA_STORE_DIR = Path("metadata_store")
SCHEMAS = ["healthcare_schema", "retail_schema", "finance_schema"]


def get_engine():
    """Build SQLAlchemy engine from .env (DATABASE_URL or DB_* variables)."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "postgres")
    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def extract_metadata(engine, schema_name: str) -> list[dict]:
    """
    Extract schema/table/column metadata and COMMENT ON TABLE / COMMENT ON COLUMN.
    Returns a list of dicts, one per table, with keys: schema_name, table_name,
    table_description, columns (list of {name, description}).
    """
    # Tables with comments (pg_catalog)
    tables_sql = text("""
        SELECT
            c.relname AS table_name,
            COALESCE(pg_catalog.obj_description(c.oid, 'pg_class'), '') AS table_comment
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = :schema_name
          AND c.relkind = 'r'
        ORDER BY c.relname
    """)
    # Columns with comments
    columns_sql = text("""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            COALESCE(pg_catalog.col_description(c.oid, a.attnum), '') AS column_comment
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = :schema_name
          AND c.relkind = 'r'
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY c.relname, a.attnum
    """)

    with engine.connect() as conn:
        tables = conn.execute(tables_sql, {"schema_name": schema_name}).fetchall()
        columns = conn.execute(columns_sql, {"schema_name": schema_name}).fetchall()

    # Group columns by table
    cols_by_table: dict[str, list[dict]] = {}
    for row in columns:
        tbl = row.table_name
        if tbl not in cols_by_table:
            cols_by_table[tbl] = []
        cols_by_table[tbl].append({
            "name": row.column_name,
            "description": (row.column_comment or "").strip(),
        })

    # Build one record per table
    result = []
    for row in tables:
        table_name = row.table_name
        table_comment = (row.table_comment or "").strip()
        result.append({
            "schema_name": schema_name,
            "table_name": table_name,
            "table_description": table_comment,
            "columns": cols_by_table.get(table_name, []),
        })

    logger.info("Extracted metadata for %d tables in %s", len(result), schema_name)
    return result


def metadata_to_texts(metadata_list: list[dict]) -> list[str]:
    """
    Turn per-table metadata into structured text chunks suitable for embedding.
    One string per table.
    """
    texts = []
    for m in metadata_list:
        lines = [
            f"Schema: {m['schema_name']}",
            f"Table: {m['table_name']}",
            f"Description: {m['table_description'] or '(no description)'}",
            "Columns:",
        ]
        for col in m["columns"]:
            desc = col["description"] or "(no description)"
            lines.append(f"  - {col['name']}: {desc}")
        texts.append("\n".join(lines))
    return texts


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """Load the sentence-transformers model once. Reuse the returned model for all schemas."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def build_embeddings(texts: list[str], model):
    """
    Generate embeddings for a list of texts using a pre-loaded sentence-transformers model.
    Returns a numpy array of shape (len(texts), embedding_dim).
    """
    logger.info("Encoding %d text(s)", len(texts))
    embeddings = model.encode(texts, show_progress_bar=len(texts) > 10)
    return embeddings


def build_faiss_index(schema_name: str, embeddings, metadata_list: list[dict]):
    """
    Create a FAISS IndexFlatL2 for the given embeddings, save the index to
    faiss_indexes/{schema}.index and metadata to metadata_store/{schema}_metadata.json.
    """
    import faiss
    import numpy as np

    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_STORE_DIR.mkdir(parents=True, exist_ok=True)

    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    n = index.ntotal
    logger.info("Built FAISS index for %s: %d vectors, dim=%d", schema_name, n, d)

    index_path = FAISS_INDEX_DIR / f"{schema_name}.index"
    faiss.write_index(index, str(index_path))
    logger.info("Saved FAISS index to %s", index_path)

    metadata_path = METADATA_STORE_DIR / f"{schema_name}_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_list, f, indent=2, ensure_ascii=False)
    logger.info("Saved metadata to %s", metadata_path)


def run_pipeline_for_schema(engine, schema_name: str, model):
    """Extract metadata, build embeddings, and write FAISS index + metadata for one schema."""
    logger.info("Processing schema: %s", schema_name)
    metadata_list = extract_metadata(engine, schema_name)
    if not metadata_list:
        logger.warning("No tables found in %s, skipping.", schema_name)
        return
    texts = metadata_to_texts(metadata_list)
    embeddings = build_embeddings(texts, model)
    build_faiss_index(schema_name, embeddings, metadata_list)


def main():
    logger.info("Starting metadata-to-FAISS pipeline.")
    engine = get_engine()
    model = get_embedding_model()
    for schema_name in SCHEMAS:
        run_pipeline_for_schema(engine, schema_name, model)
    logger.info("Pipeline finished.")


if __name__ == "__main__":
    main()
