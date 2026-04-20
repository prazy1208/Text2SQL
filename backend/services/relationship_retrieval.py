"""
FK relationship rows for agents: primary path loads from metadata_store JSON (no DB).
Optional DB helper remains for tooling that reads Postgres directly.

Runtime for POST /query: list_relationships_from_metadata(schema_name) → same dict shape
as before (id, schema_name, source_*, target_*, relationship_text, constraint_name), with
embedding vectors stripped.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from backend.config import DOMAIN_SCHEMAS, METADATA_STORE_DIR, RELATIONSHIP_METADATA_NAMES, get_engine

logger = logging.getLogger(__name__)

_ALLOWED = frozenset(DOMAIN_SCHEMAS)


def list_relationships_from_metadata(schema_name: str) -> list[dict[str, Any]]:
    """
    Load FK rows from metadata_store/relationships_{schema}_metadata.json (no database).

    Each item matches build_relationship_embeddings.py output except embeddings are omitted
    from returned dicts to keep prompts small.

    Returns [] if the file is missing or unreadable (logs a warning).
    """
    if schema_name not in _ALLOWED:
        raise ValueError(
            f"schema_name must be one of {sorted(_ALLOWED)}, got {schema_name!r}"
        )
    fname = RELATIONSHIP_METADATA_NAMES.get(schema_name)
    if not fname:
        raise ValueError(f"No relationship metadata filename for {schema_name!r}")
    path = METADATA_STORE_DIR / fname
    if not path.is_file():
        logger.warning("Relationship metadata file missing: %s", path)
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Could not read relationship metadata %s: %s", path, e)
        return []
    if not isinstance(raw, list):
        logger.warning("Relationship metadata must be a JSON array: %s", path)
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        row = {k: v for k, v in item.items() if k != "embedding"}
        row.setdefault("schema_name", schema_name)
        out.append(row)
    out.sort(
        key=lambda r: (
            str(r.get("source_table") or ""),
            str(r.get("source_column") or ""),
            str(r.get("target_schema") or ""),
            str(r.get("target_table") or ""),
            str(r.get("target_column") or ""),
            int(r["id"]) if isinstance(r.get("id"), int) else 0,
        )
    )
    return out


def list_relationships_for_schema(schema_name: str) -> list[dict[str, Any]]:
    """
    Return all rows from {schema_name}.table_relationships (Postgres).

    Used by offline scripts (e.g. build_relationship_embeddings.py). Agents and POST /query
    should use list_relationships_from_metadata instead.
    """
    if schema_name not in _ALLOWED:
        raise ValueError(
            f"schema_name must be one of {sorted(_ALLOWED)}, got {schema_name!r}"
        )
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
        FROM {schema_name}.table_relationships
        ORDER BY
            source_table,
            source_column,
            target_schema,
            target_table,
            target_column,
            id
        """
    )
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(q)
        rows = [dict(r._mapping) for r in result]
    for r in rows:
        r["schema_name"] = schema_name
    return rows


def filter_relationships_for_selected_tables(
    schema_name: str,
    relationships: list[dict[str, Any]],
    selected_tables: list[str],
) -> list[dict[str, Any]]:
    """
    Keep FK edges where both the referencing table and the referenced table appear
    in selected_tables (schema.table FQNs).
    """
    if not selected_tables:
        return []
    sel = {t.strip() for t in selected_tables if t and str(t).strip()}
    out: list[dict[str, Any]] = []
    for r in relationships:
        src_fqn = f"{schema_name}.{r['source_table']}"
        tgt_fqn = f"{r['target_schema']}.{r['target_table']}"
        if src_fqn in sel and tgt_fqn in sel:
            out.append(r)
    return out
