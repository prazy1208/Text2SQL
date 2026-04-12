"""
Extract foreign keys from pg_catalog for DOMAIN_SCHEMAS and upsert each row into
{schema}.table_relationships (trusted schema names from config only).

Requires: scripts/create_domain_schema_table_relationships.sql applied.

Run from project root: python scripts/extract_and_load_relationships.py
"""

from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv
from sqlalchemy import bindparam, create_engine, text

load_dotenv()

from backend.config import DOMAIN_SCHEMAS

_ALLOWED = frozenset(DOMAIN_SCHEMAS)

FK_QUERY = (
    text(
        """
    SELECT
        nsp_src.nspname AS source_schema,
        cls_src.relname AS source_table,
        att_src.attname AS source_column,
        nsp_tgt.nspname AS target_schema,
        cls_tgt.relname AS target_table,
        att_tgt.attname AS target_column,
        con.conname AS constraint_name
    FROM pg_constraint con
    JOIN pg_class cls_src ON cls_src.oid = con.conrelid
    JOIN pg_namespace nsp_src ON nsp_src.oid = cls_src.relnamespace
    JOIN pg_class cls_tgt ON cls_tgt.oid = con.confrelid
    JOIN pg_namespace nsp_tgt ON nsp_tgt.oid = cls_tgt.relnamespace
    CROSS JOIN LATERAL unnest(con.conkey, con.confkey) AS u(src_attnum, tgt_attnum)
    JOIN pg_attribute att_src
        ON att_src.attrelid = con.conrelid
        AND att_src.attnum = u.src_attnum
        AND NOT att_src.attisdropped
    JOIN pg_attribute att_tgt
        ON att_tgt.attrelid = con.confrelid
        AND att_tgt.attnum = u.tgt_attnum
        AND NOT att_tgt.attisdropped
    WHERE con.contype = 'f'
      AND nsp_src.nspname IN :domain_schemas
    ORDER BY
        nsp_src.nspname,
        cls_src.relname,
        con.conname,
        u.src_attnum
    """
    ).bindparams(bindparam("domain_schemas", expanding=True))
)


def _upsert_statement(qualified_schema: str) -> str:
    """Build INSERT for one domain schema; qualified_schema must be a member of DOMAIN_SCHEMAS."""
    return f"""
    INSERT INTO {qualified_schema}.table_relationships (
        source_table,
        source_column,
        target_schema,
        target_table,
        target_column,
        relationship_text,
        constraint_name
    ) VALUES (
        :source_table,
        :source_column,
        :target_schema,
        :target_table,
        :target_column,
        :relationship_text,
        :constraint_name
    )
    ON CONFLICT (source_table, source_column, target_schema, target_table, target_column)
    DO UPDATE SET
        relationship_text = EXCLUDED.relationship_text,
        constraint_name = EXCLUDED.constraint_name
    """


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


def relationship_text(
    source_schema: str,
    source_table: str,
    source_column: str,
    target_schema: str,
    target_table: str,
    target_column: str,
) -> str:
    return (
        f"{source_schema}.{source_table}.{source_column} -> "
        f"{target_schema}.{target_table}.{target_column}"
    )


def fetch_foreign_key_rows(engine, domain_schemas: tuple[str, ...]):
    with engine.connect() as conn:
        result = conn.execute(FK_QUERY, {"domain_schemas": list(domain_schemas)})
        return [dict(r._mapping) for r in result]


def row_to_payload(r: dict) -> dict:
    src_schema = r["source_schema"]
    tgt_schema = r["target_schema"]
    src_table = r["source_table"]
    src_col = r["source_column"]
    tgt_table = r["target_table"]
    tgt_col = r["target_column"]
    return {
        "source_table": src_table,
        "source_column": src_col,
        "target_schema": tgt_schema,
        "target_table": tgt_table,
        "target_column": tgt_col,
        "relationship_text": relationship_text(
            src_schema, src_table, src_col, tgt_schema, tgt_table, tgt_col
        ),
        "constraint_name": r["constraint_name"],
    }


def upsert_all(engine, pg_rows: list[dict]) -> dict[str, int]:
    """Upsert rows grouped by source_schema. Returns counts per schema."""
    counts: Counter[str] = Counter()
    # Precompile statements per domain schema (whitelist)
    stmts = {s: text(_upsert_statement(s)) for s in DOMAIN_SCHEMAS}
    with engine.begin() as conn:
        for r in pg_rows:
            src_schema = r["source_schema"]
            if src_schema not in _ALLOWED:
                raise ValueError(
                    f"FK row source_schema {src_schema!r} not in DOMAIN_SCHEMAS; check query filter."
                )
            payload = row_to_payload(r)
            conn.execute(stmts[src_schema], payload)
            counts[src_schema] += 1
    return dict(counts)


def main():
    engine = get_engine()
    pg_rows = fetch_foreign_key_rows(engine, DOMAIN_SCHEMAS)
    by_schema = Counter(r["source_schema"] for r in pg_rows)
    print(f"Found {len(pg_rows)} FK column reference(s) from pg_catalog.")
    for s in DOMAIN_SCHEMAS:
        print(f"  {s}: {by_schema.get(s, 0)}")
    counts = upsert_all(engine, pg_rows)
    total = sum(counts.values())
    print(f"Upserted {total} row(s) into domain table_relationships tables.")
    for s in DOMAIN_SCHEMAS:
        print(f"  {s}.table_relationships: {counts.get(s, 0)}")


if __name__ == "__main__":
    main()
