"""
Backend config: PROJECT_ROOT, database, app_schema, and paths to FAISS/metadata stores.
Load .env from project root so the app works regardless of CWD.
"""

import os
from pathlib import Path

# Project root = parent of backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env from project root (idempotent if already loaded)
def _load_dotenv():
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
APP_SCHEMA = "app_schema"

def get_engine():
    """Build SQLAlchemy engine from .env (DATABASE_URL or DB_*). Call after dotenv is loaded."""
    _load_dotenv()
    from sqlalchemy import create_engine
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


# ---------------------------------------------------------------------------
# Paths (all under PROJECT_ROOT)
# ---------------------------------------------------------------------------
FAISS_INDEX_DIR = PROJECT_ROOT / "faiss_indexes"
METADATA_STORE_DIR = PROJECT_ROOT / "metadata_store"
BUSINESS_RULES_STORE_DIR = PROJECT_ROOT / "business_rules_store"

# Per-schema FAISS index filenames (table-level metadata, Table Agent)
FAISS_INDEX_NAMES = {
    "healthcare_schema": "healthcare_schema.index",
    "retail_schema": "retail_schema.index",
    "finance_schema": "finance_schema.index",
}

# Per-schema FAISS index filenames (one vector per column, Column Agent shortlist)
FAISS_COLUMN_INDEX_NAMES = {
    "healthcare_schema": "healthcare_schema_columns.index",
    "retail_schema": "retail_schema_columns.index",
    "finance_schema": "finance_schema_columns.index",
}

# Business-rules FAISS index filenames
BUSINESS_RULES_INDEX_NAMES = {
    "healthcare_schema": "business_rules_healthcare_schema.index",
    "retail_schema": "business_rules_retail_schema.index",
    "finance_schema": "business_rules_finance_schema.index",
}

# Business-rules metadata JSON filenames
BUSINESS_RULES_METADATA_NAMES = {
    "healthcare_schema": "healthcare_schema_rules.json",
    "retail_schema": "retail_schema_rules.json",
    "finance_schema": "finance_schema_rules.json",
}

# Few-shot SQL pattern catalog (system_schema.few_shot_examples → JSON via build_few_shot_metadata_store.py)
FEWSHOT_METADATA_NAME = os.getenv("FEWSHOT_METADATA_NAME", "few_shot_examples_metadata.json")
FEWSHOT_METADATA_PATH = METADATA_STORE_DIR / FEWSHOT_METADATA_NAME

# FK relationship embeddings metadata (build_relationship_embeddings.py; no FAISS in v1)
RELATIONSHIP_METADATA_NAMES = {
    "healthcare_schema": "relationships_healthcare_schema_metadata.json",
    "retail_schema": "relationships_retail_schema_metadata.json",
    "finance_schema": "relationships_finance_schema_metadata.json",
}

# ---------------------------------------------------------------------------
# Use cases (for dropdown and validation)
# ---------------------------------------------------------------------------
USE_CASES = ["healthcare", "retail", "finance"]

# Map API use_case to schema name (for FAISS and DB)
USE_CASE_TO_SCHEMA = {
    "healthcare": "healthcare_schema",
    "retail": "retail_schema",
    "finance": "finance_schema",
}
