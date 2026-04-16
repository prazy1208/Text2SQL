"""
Business-rules retrieval service for the Intent Agent.
Loads FAISS index + metadata for a use_case, embeds the query, runs similarity search,
and returns a list of insight strings (business_insights).
"""

import json
import logging

from backend.config import (
    BUSINESS_RULES_INDEX_NAMES,
    BUSINESS_RULES_METADATA_NAMES,
    BUSINESS_RULES_STORE_DIR,
    FAISS_INDEX_DIR,
    USE_CASE_TO_SCHEMA,
)

logger = logging.getLogger(__name__)

_index_cache: dict[str, tuple] = {}
_embedding_model = None

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_TOP_K = 10


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model for retrieval: %s (first request may take 1–2 min)", EMBEDDING_MODEL_NAME)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("Embedding model ready.")
    return _embedding_model


def _load_index_and_metadata(schema_name: str) -> tuple:
    if schema_name in _index_cache:
        return _index_cache[schema_name]

    index_path = FAISS_INDEX_DIR / BUSINESS_RULES_INDEX_NAMES[schema_name]
    metadata_path = BUSINESS_RULES_STORE_DIR / BUSINESS_RULES_METADATA_NAMES[schema_name]

    if not index_path.exists():
        raise FileNotFoundError(
            f"Business-rules FAISS index not found: {index_path}. Run build_business_rules_vector_store.py."
        )
    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Business-rules metadata not found: {metadata_path}. Run build_business_rules_vector_store.py."
        )

    import faiss
    index = faiss.read_index(str(index_path))
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata_list = json.load(f)

    _index_cache[schema_name] = (index, metadata_list)
    logger.debug("Loaded index and metadata for %s (%d rules)", schema_name, len(metadata_list))
    return index, metadata_list


def retrieve_business_insights(
    use_case: str,
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[str]:
    """
    Return a list of business-insight strings for the given use_case and query text.
    """
    if not query or not query.strip():
        return []

    schema_name = USE_CASE_TO_SCHEMA.get(use_case)
    if not schema_name:
        logger.warning("Unknown use_case %r, skipping business-rules retrieval", use_case)
        return []

    index, metadata_list = _load_index_and_metadata(schema_name)
    n_total = index.ntotal
    if n_total == 0:
        return []

    k = min(top_k, n_total)
    model = _get_embedding_model()
    query_embedding = model.encode([query.strip()], show_progress_bar=False)
    import numpy as np
    query_vec = np.asarray(query_embedding, dtype=np.float32)

    distances, indices = index.search(query_vec, k)
    idx_list = indices[0].tolist()

    result = []
    for idx in idx_list:
        if idx < 0 or idx >= len(metadata_list):
            continue
        entry = metadata_list[idx]
        content = entry.get("content") or entry.get("insight") or entry.get("description") or ""
        if content:
            result.append(content.strip())
    return result
