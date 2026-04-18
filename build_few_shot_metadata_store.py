"""
Read system_schema.few_shot_examples and write the few-shot catalog JSON (no embeddings).

Output:
  metadata_store/{FEWSHOT_METADATA_NAME}  (default: few_shot_examples_metadata.json)

Each item: id, question_text, sql_query, query_type (same row order as ORDER BY id).

Run from project root: python build_few_shot_metadata_store.py
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

from backend.config import FEWSHOT_METADATA_PATH, METADATA_STORE_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


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


def fetch_examples(engine) -> list[dict]:
    q = text(
        """
        SELECT id, question_text, sql_query, query_type
        FROM system_schema.few_shot_examples
        ORDER BY id
        """
    )
    with engine.connect() as conn:
        result = conn.execute(q)
        return [dict(r._mapping) for r in result]


def main():
    engine = get_engine()
    rows = fetch_examples(engine)
    METADATA_STORE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FEWSHOT_METADATA_PATH
    out_path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Wrote %d few-shot example(s) to %s", len(rows), out_path)


if __name__ == "__main__":
    main()
