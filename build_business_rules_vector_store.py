"""
Business-rules-to-FAISS pipeline for Stage 1 Intent Agent.
Reads from domain-schema business_rules tables (healthcare, retail, finance),
builds one embedding per rule, and writes FAISS indexes + metadata to
business_rules_store/ (separate from metadata_store/ to avoid confusion).
Run: python build_business_rules_vector_store.py
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()

# Output: FAISS indexes in faiss_indexes/ (with business_rules_ prefix), metadata in business_rules_store/
FAISS_INDEX_DIR = Path("faiss_indexes")
BUSINESS_RULES_STORE_DIR = Path("business_rules_store")

# Schema name -> business rules table name (in that schema)
SCHEMA_TO_TABLE = {
    "healthcare_schema": "healthcare_business_rules",
    "retail_schema": "retail_business_rules",
    "finance_schema": "finance_business_rules",
}


def get_engine():
    """Build SQLAlchemy engine from .env (same pattern as build_vector_store.py)."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "postgres")
    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def fetch_business_rules(engine, schema_name: str) -> list[dict]:
    """
    Load all rows from the business_rules table for the given schema.
    Returns list of dicts: rule_id, concept_name, description, insight, keywords, created_at.
    """
    table_name = SCHEMA_TO_TABLE[schema_name]
    full_name = f"{schema_name}.{table_name}"
    # Table name is from our SCHEMA_TO_TABLE map (safe identifiers only)
    safe_sql = text(
        f"""
        SELECT rule_id, concept_name, description, insight, keywords, created_at
        FROM {schema_name}.{table_name}
        ORDER BY rule_id
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(safe_sql).fetchall()
    result = []
    for row in rows:
        keywords = list(row.keywords) if row.keywords else []
        result.append({
            "rule_id": row.rule_id,
            "concept_name": row.concept_name or "",
            "description": row.description or "",
            "insight": row.insight or "",
            "keywords": keywords,
            "created_at": str(row.created_at) if row.created_at else None,
        })
    logger.info("Fetched %d business rules from %s", len(result), full_name)
    return result


def rule_to_content(rule: dict) -> str:
    """Build one searchable text per rule for embedding (concept_name, description, insight, keywords)."""
    parts = [
        rule.get("concept_name", ""),
        rule.get("description", ""),
        rule.get("insight", ""),
    ]
    kw = rule.get("keywords") or []
    if kw:
        parts.append(" ".join(kw))
    return " ".join(p for p in parts if p).strip() or "(no content)"


def rules_to_metadata_entries(rules: list[dict]) -> list[dict]:
    """
    Build metadata list: one entry per rule with index position, rule fields, and 'content' for retrieval.
    """
    entries = []
    for i, rule in enumerate(rules):
        content = rule_to_content(rule)
        entries.append({
            "index": i,
            "rule_id": rule["rule_id"],
            "concept_name": rule["concept_name"],
            "description": rule["description"],
            "insight": rule["insight"],
            "keywords": rule["keywords"],
            "content": content,
        })
    return entries


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """Load sentence-transformers model (same as build_vector_store.py)."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def build_embeddings(texts: list[str], model):
    """Generate embeddings for a list of texts. Returns numpy array (n, dim)."""
    import numpy as np

    logger.info("Encoding %d text(s)", len(texts))
    embeddings = model.encode(texts, show_progress_bar=len(texts) > 10)
    return np.asarray(embeddings, dtype=np.float32)


def write_faiss_and_metadata(
    schema_name: str,
    embeddings,
    metadata_entries: list[dict],
):
    """
    Write FAISS index to faiss_indexes/business_rules_{schema}.index
    and metadata to business_rules_store/{schema}_rules.json.
    """
    import faiss
    import numpy as np

    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    BUSINESS_RULES_STORE_DIR.mkdir(parents=True, exist_ok=True)

    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
    d = embeddings.shape[1]
    index = faiss.IndexFlatL2(d)
    index.add(embeddings)
    n = index.ntotal
    logger.info("Built business-rules FAISS index for %s: %d vectors, dim=%d", schema_name, n, d)

    index_filename = f"business_rules_{schema_name}.index"
    index_path = FAISS_INDEX_DIR / index_filename
    faiss.write_index(index, str(index_path))
    logger.info("Saved FAISS index to %s", index_path)

    metadata_filename = f"{schema_name}_rules.json"
    metadata_path = BUSINESS_RULES_STORE_DIR / metadata_filename
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_entries, f, indent=2, ensure_ascii=False)
    logger.info("Saved metadata to %s (business_rules_store, separate from metadata_store)", metadata_path)


def run_pipeline_for_schema(engine, schema_name: str, model):
    """Fetch rules, build content + embeddings, write FAISS index and metadata to business_rules_store."""
    logger.info("Processing business rules for schema: %s", schema_name)
    rules = fetch_business_rules(engine, schema_name)
    if not rules:
        logger.warning("No business rules in %s, skipping.", schema_name)
        return
    texts = [rule_to_content(r) for r in rules]
    metadata_entries = rules_to_metadata_entries(rules)
    embeddings = build_embeddings(texts, model)
    write_faiss_and_metadata(schema_name, embeddings, metadata_entries)


def main():
    logger.info("Starting business-rules-to-FAISS pipeline (output in business_rules_store/).")
    engine = get_engine()
    model = get_embedding_model()
    for schema_name in SCHEMA_TO_TABLE:
        run_pipeline_for_schema(engine, schema_name, model)
    logger.info("Pipeline finished. Indexes in faiss_indexes/, metadata in business_rules_store/.")


if __name__ == "__main__":
    main()
