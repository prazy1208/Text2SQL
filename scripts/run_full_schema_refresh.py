"""
Run full domain schema refresh in one command.

Pipeline order:
1) Apply scripts/create_domain_schemas.sql
2) Ensure domain table_relationships tables exist
3) Extract + upsert FK relationships into domain table_relationships
4) Build relationship embedding metadata JSON
5) Build table/column metadata JSON + FAISS indexes

Run from project root: python scripts/run_full_schema_refresh.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)
load_dotenv()


def get_engine():
    """Build SQLAlchemy engine from .env (DATABASE_URL or DB_* variables)."""
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


def apply_domain_schema_sql() -> None:
    """Execute scripts/create_domain_schemas.sql (multi-statement SQL)."""
    sql_file = PROJECT_ROOT / "scripts" / "create_domain_schemas.sql"
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_file}")

    sql = sql_file.read_text(encoding="utf-8")
    engine = get_engine()
    raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        cur.execute(sql)
        raw_conn.commit()
    finally:
        raw_conn.close()


def run_python_script(relative_path: str) -> None:
    """Run a Python script and raise if it fails."""
    script_path = PROJECT_ROOT / relative_path
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")
    cmd = [sys.executable, str(script_path)]
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)


def run_step(step_name: str, fn) -> None:
    start = time.perf_counter()
    print(f"[START] {step_name}")
    fn()
    elapsed = time.perf_counter() - start
    print(f"[OK] {step_name} ({elapsed:.2f}s)")


def main() -> None:
    print("Starting full schema refresh pipeline...")
    steps: list[tuple[str, callable]] = [
        ("Apply domain schema SQL", apply_domain_schema_sql),
        (
            "Ensure table_relationships tables",
            lambda: run_python_script("scripts/run_create_domain_schema_table_relationships.py"),
        ),
        (
            "Extract and load relationships",
            lambda: run_python_script("scripts/extract_and_load_relationships.py"),
        ),
        (
            "Build relationship embeddings metadata",
            lambda: run_python_script("build_relationship_embeddings.py"),
        ),
        (
            "Build metadata and FAISS indexes",
            lambda: run_python_script("build_vector_store.py"),
        ),
    ]

    try:
        for step_name, fn in steps:
            run_step(step_name, fn)
    except Exception as exc:
        print(f"[FAILED] Pipeline stopped: {exc}")
        raise

    print("Full schema refresh completed successfully.")


if __name__ == "__main__":
    main()
