"""
Few-shot catalog load for the Few-Shot Agent: read curated examples as text (no vectors).

Primary source: metadata_store JSON (see build_few_shot_metadata_store.py).
Optional fallback: system_schema.few_shot_examples when the file is missing or unusable.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from backend.config import FEWSHOT_METADATA_PATH, get_engine

logger = logging.getLogger(__name__)

_db_fallback_logged = False


def _fetch_from_db() -> list[dict[str, Any]]:
    engine = get_engine()
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


def list_all_few_shot_examples() -> list[dict[str, Any]]:
    """
    Load all few-shot examples from FEWSHOT_METADATA_PATH (JSON array of objects).

    If the file is missing or invalid, fall back to Postgres once and log a single warning.
    Returns [] if the JSON is a valid empty array, or if both file and DB yield nothing / DB errors.
    """
    global _db_fallback_logged
    path = FEWSHOT_METADATA_PATH

    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            logger.warning("%s: expected a JSON array; trying database", path)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read few-shot metadata %s (%s); trying database", path, e)

    if not _db_fallback_logged:
        logger.warning(
            "Few-shot catalog: loading from database (metadata missing or unusable: %s)",
            path,
        )
        _db_fallback_logged = True
    try:
        return _fetch_from_db()
    except Exception:
        logger.exception("Few-shot database load failed")
        return []
