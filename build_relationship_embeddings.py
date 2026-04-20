"""
Embed rows from each domain schema's table_relationships (relationship_text) using
sentence-transformers (all-MiniLM-L6-v2). Writes JSON only — no FAISS.

Outputs per schema (aligned with DB row order: deterministic ORDER BY):
  metadata_store/relationships_{schema}_metadata.json

Each item: id, schema_name, source_*, target_*, relationship_text, constraint_name, embedding.

Run from project root: python build_relationship_embeddings.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

from backend.config import DOMAIN_SCHEMAS, METADATA_STORE_DIR, RELATIONSHIP_METADATA_NAMES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

_ALLOWED = frozenset(DOMAIN_SCHEMAS)


def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "text2sql_db")
    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def fetch_rows(engine, schema: str) -> list[dict]:
    if schema not in _ALLOWED:
        raise ValueError(f"Invalid schema: {schema}")
    q = text(
        f"""
        SELECT
            id,
            source_table,
            source_column,
            target_schema,
            target_table,
            target_column,
            relationship_text,
            constraint_name
        FROM {schema}.table_relationships
        ORDER BY
            source_table,
            source_column,
            target_schema,
            target_table,
            target_column,
            id
        """
    )
    with engine.connect() as conn:
        result = conn.execute(q)
        return [dict(r._mapping) for r in result]


def get_model():
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def main():
    engine = get_engine()
    model = get_model()
    METADATA_STORE_DIR.mkdir(parents=True, exist_ok=True)

    for schema in DOMAIN_SCHEMAS:
        rows = fetch_rows(engine, schema)
        texts = [r["relationship_text"] for r in rows]
        if not texts:
            logger.info("%s: no rows; writing empty list to JSON", schema)
            embeddings_list = []
        else:
            logger.info("%s: encoding %d relationship(s)", schema, len(texts))
            emb = model.encode(texts, show_progress_bar=len(texts) > 8)
            embeddings_list = emb.tolist()

        out: list[dict] = []
        for i, r in enumerate(rows):
            item = {
                "id": r["id"],
                "schema_name": schema,
                "source_table": r["source_table"],
                "source_column": r["source_column"],
                "target_schema": r["target_schema"],
                "target_table": r["target_table"],
                "target_column": r["target_column"],
                "relationship_text": r["relationship_text"],
                "constraint_name": r["constraint_name"],
                "embedding": embeddings_list[i] if embeddings_list else [],
            }
            out.append(item)

        fname = RELATIONSHIP_METADATA_NAMES[schema]
        path = METADATA_STORE_DIR / fname
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        logger.info("Wrote %s (%d record(s))", path, len(out))


if __name__ == "__main__":
    main()
