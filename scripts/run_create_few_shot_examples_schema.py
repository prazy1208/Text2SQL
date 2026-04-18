"""Apply scripts/create_system_schema_few_shot_examples.sql. Run from project root."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


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


def main():
    sql_file = PROJECT_ROOT / "scripts" / "create_system_schema_few_shot_examples.sql"
    if not sql_file.exists():
        print(f"SQL file not found: {sql_file}")
        sys.exit(1)
    sql = sql_file.read_text(encoding="utf-8")
    engine = get_engine()
    raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        cur.execute(sql)
        raw_conn.commit()
    finally:
        raw_conn.close()
    print("Done. system_schema.few_shot_examples created.")


if __name__ == "__main__":
    main()
