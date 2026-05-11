"""
Backfill app_schema.sessions: titles from first user message; optional client_id.

From project root:
  python scripts/run_backfill_session_metadata.py
  python scripts/run_backfill_session_metadata.py --client-id "<uuid from text2sql_client_id>"

Or set BACKFILL_CLIENT_ID in .env (used when --client-id is omitted).
"""

import argparse
import os
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

from backend.config import APP_SCHEMA


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


def run_title_backfill(engine) -> None:
    sql_file = PROJECT_ROOT / "scripts" / "backfill_session_metadata.sql"
    if not sql_file.exists():
        print(f"SQL file not found: {sql_file}")
        sys.exit(1)
    sql = sql_file.read_text(encoding="utf-8")
    raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        cur.execute(sql)
        raw_conn.commit()
    finally:
        raw_conn.close()


def run_client_id_backfill(engine, client_id: str) -> int:
    """Assign client_id to sessions that have messages but NULL client_id. Returns rowcount."""
    cid = uuid.UUID(str(client_id).strip())
    with engine.begin() as conn:
        result = conn.execute(
            text(f"""
                UPDATE {APP_SCHEMA}.sessions s
                SET client_id = :cid,
                    updated_at = CURRENT_TIMESTAMP
                WHERE s.client_id IS NULL
                  AND EXISTS (
                      SELECT 1 FROM {APP_SCHEMA}.chat_messages m
                      WHERE m.session_id = s.session_id
                  )
            """),
            {"cid": cid},
        )
        return result.rowcount or 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill session title and optional client_id")
    parser.add_argument(
        "--client-id",
        metavar="UUID",
        help="Browser client id (localStorage text2sql_client_id). Also reads BACKFILL_CLIENT_ID env.",
    )
    args = parser.parse_args()
    client_id = (args.client_id or os.getenv("BACKFILL_CLIENT_ID") or "").strip() or None

    engine = get_engine()
    run_title_backfill(engine)
    print("Done: title backfill (from backfill_session_metadata.sql).")

    if client_id:
        try:
            n = run_client_id_backfill(engine, client_id)
            print(f"Done: client_id backfill — updated {n} session(s) with NULL client_id (that have messages).")
        except ValueError as e:
            print(f"Invalid --client-id / BACKFILL_CLIENT_ID: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(
            "Skipped client_id backfill (no --client-id or BACKFILL_CLIENT_ID). "
            "GET /sessions only lists rows where client_id matches your browser; "
            "run again with: python scripts/run_backfill_session_metadata.py --client-id \"<uuid>\""
        )


if __name__ == "__main__":
    main()
