"""
Load FK relationship rows from each domain schema's table_relationships table.
Runtime: full list only (no FAISS / top_k). ORDER BY matches build_relationship_embeddings.py.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from backend.config import DOMAIN_SCHEMAS, get_engine

logger = logging.getLogger(__name__)

_ALLOWED = frozenset(DOMAIN_SCHEMAS)


def list_relationships_for_schema(schema_name: str) -> list[dict[str, Any]]:
    """
    Return all rows from {schema_name}.table_relationships in deterministic order.
    Each dict includes: id, schema_name, source_table, source_column, target_schema,
    target_table, target_column, relationship_text, constraint_name.
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
