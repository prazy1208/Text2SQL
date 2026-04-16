"""
Metadata-to-FAISS pipeline for PostgreSQL schemas (healthcare, retail, finance).
Extracts table/column metadata and comments, builds embeddings with sentence-transformers,
and stores them in per-schema FAISS indexes and metadata JSON.

Outputs per schema:
- Table-level: faiss_indexes/{schema}.index + metadata_store/{schema}_metadata.json
- Column-level: faiss_indexes/{schema}_columns.index + metadata_store/{schema}_columns_metadata.json
  (flat list order matches FAISS row indices 0..n-1).

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
    Column types come from pg_catalog.format_type (Postgres-native, includes length/precision).
    Returns a list of dicts, one per table, with keys: schema_name, table_name,
    table_description, columns (list of {name, description, data_type}).
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
    # Columns: comments + data type (format_type matches psql / CREATE TABLE spelling)
    columns_sql = text("""
        SELECT
            c.relname AS table_name,
            a.attname AS column_name,
            pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
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
        dtype = (row.data_type or "").strip() if row.data_type is not None else ""
        cols_by_table[tbl].append({
            "name": row.column_name,
            "description": (row.column_comment or "").strip(),
            "data_type": dtype,
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


def nested_metadata_to_flat_columns(metadata_list: list[dict]) -> list[dict]:
    """
    Flatten nested table metadata to one dict per column for column-level FAISS.

    Stable order (documented for rebuild alignment with vectors):
    tables sorted by table_name; within each table, columns sorted by name.
    Each row: schema_name, table_name, column_name, data_type, description,
    table_description, fqn (schema.table.column).
    """
    flat: list[dict] = []
    for m in sorted(metadata_list, key=lambda x: x["table_name"]):
        schema = m["schema_name"]
        table = m["table_name"]
        table_desc = (m.get("table_description") or "").strip()
        for col in sorted(m.get("columns") or [], key=lambda c: c["name"]):
            name = col["name"]
            desc = (col.get("description") or "").strip()
            dtype = (col.get("data_type") or "").strip()
            fqn = f"{schema}.{table}.{name}"
            flat.append({
                "schema_name": schema,
                "table_name": table,
                "column_name": name,
                "data_type": dtype,
                "description": desc,
                "table_description": table_desc,
                "fqn": fqn,
            })
    return flat


def column_flat_rows_to_texts(flat_rows: list[dict]) -> list[str]:
    """One embedding string per column (metadata only; no row data)."""
    texts = []
    for r in flat_rows:
        tdesc = r["table_description"] or "(no table description)"
        cdesc = r["description"] or "(no description)"
        dtype = r["data_type"] or "(unknown type)"
        text = "\n".join(
            [
                f"Schema: {r['schema_name']}",
                f"Table: {r['table_name']}",
                f"Table description: {tdesc}",
                f"Column: {r['column_name']}",
                f"Type: {dtype}",
                f"Column description: {cdesc}",
            ]
        )
        texts.append(text)
    return texts


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
            dtype = (col.get("data_type") or "").strip() or "(unknown type)"
            lines.append(f"  - {col['name']} ({dtype}): {desc}")
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


def build_column_faiss_index(schema_name: str, embeddings, flat_column_metadata: list[dict]):
    """
    Column-level FAISS: vector i corresponds to flat_column_metadata[i].
    Writes faiss_indexes/{schema}_columns.index and
    metadata_store/{schema}_columns_metadata.json.
    """
    import faiss
    import numpy as np

    if not flat_column_metadata:
        logger.warning("No columns to index for %s; skipping column FAISS.", schema_name)
        return

    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    METADATA_STORE_DIR.mkdir(parents=True, exist_ok=True)

    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
    n_vec = embeddings.shape[0]
    if n_vec != len(flat_column_metadata):
        raise ValueError(
            f"Column embedding count ({n_vec}) != flat metadata rows ({len(flat_column_metadata)}) "
            f"for {schema_name}"
        )

    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    index_path = FAISS_INDEX_DIR / f"{schema_name}_columns.index"
    faiss.write_index(index, str(index_path))
    logger.info(
        "Built column FAISS index for %s: %d vectors, dim=%d -> %s",
        schema_name,
        index.ntotal,
        d,
        index_path,
    )

    metadata_path = METADATA_STORE_DIR / f"{schema_name}_columns_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(flat_column_metadata, f, indent=2, ensure_ascii=False)
    logger.info("Saved column flat metadata to %s", metadata_path)


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

    flat_columns = nested_metadata_to_flat_columns(metadata_list)
    if flat_columns:
        col_texts = column_flat_rows_to_texts(flat_columns)
        col_embeddings = build_embeddings(col_texts, model)
        build_column_faiss_index(schema_name, col_embeddings, flat_columns)
    else:
        logger.warning("No column rows after flatten for %s; skipping column index.", schema_name)


def main():
    logger.info("Starting metadata-to-FAISS pipeline.")
    engine = get_engine()
    model = get_embedding_model()
    for schema_name in SCHEMAS:
        run_pipeline_for_schema(engine, schema_name, model)
    logger.info("Pipeline finished.")


if __name__ == "__main__":
    main()
