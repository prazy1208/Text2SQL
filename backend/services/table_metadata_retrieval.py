"""
Table metadata retrieval for the Table Agent (Step 5a).

Loads per-schema table metadata from metadata_store. Candidate **text** for the Table Agent
is schema + table name + table description only (column details are left to a later agent).
FAISS shortlist (N > threshold) still uses the existing table index built from full metadata.
If the schema has more than TABLE_SHORTLIST_THRESHOLD tables, runs FAISS similarity search
with the same embedding model as the index build (all-MiniLM-L6-v2).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import (
    FAISS_INDEX_DIR,
    FAISS_INDEX_NAMES,
    METADATA_STORE_DIR,
    USE_CASE_TO_SCHEMA,
)
# Reuse one SentenceTransformer instance with business-rules retrieval (same model name).
from backend.services.business_rules_retrieval import _get_embedding_model

logger = logging.getLogger(__name__)

TABLE_SHORTLIST_THRESHOLD = 10
DEFAULT_TOP_K = 10

_table_index_cache: dict[str, tuple[Any, list[dict]]] = {}


def table_metadata_summary_for_agent(m: dict) -> dict:
    """
    Table-level fields only for the Table Agent (no columns; another agent will use column metadata).
    """
    return {
        "schema_name": m["schema_name"],
        "table_name": m["table_name"],
        "table_description": m.get("table_description") or "",
    }


def metadata_entry_to_text(m: dict) -> str:
    """One table → short structured text (schema, table, description only)."""
    desc = m.get("table_description") or "(no description)"
    return "\n".join(
        [
            f"Schema: {m['schema_name']}",
            f"Table: {m['table_name']}",
            f"Description: {desc}",
        ]
    )


def load_table_metadata_list(schema_name: str) -> list[dict]:
    """
    Load metadata_store/{schema_name}_metadata.json (list of table dicts, same order as FAISS).
    """
    path = METADATA_STORE_DIR / f"{schema_name}_metadata.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Table metadata not found: {path}. Run build_vector_store.py for this schema."
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}, got {type(data).__name__}")
    return data


def _build_retrieval_query(rephrased_question: str, keywords: list[str] | None) -> str:
    parts: list[str] = []
    if rephrased_question and rephrased_question.strip():
        parts.append(rephrased_question.strip())
    if keywords:
        for k in keywords:
            if k and str(k).strip():
                parts.append(str(k).strip())
    return " ".join(parts) if parts else ""


def _load_table_faiss_and_metadata(schema_name: str) -> tuple[Any, list[dict]]:
    """FAISS index + table metadata list (cached). Vectors align with metadata list indices."""
    if schema_name in _table_index_cache:
        return _table_index_cache[schema_name]

    index_filename = FAISS_INDEX_NAMES.get(schema_name)
    if not index_filename:
        raise ValueError(f"No FAISS index mapping for schema {schema_name!r}")

    index_path = FAISS_INDEX_DIR / index_filename
    if not index_path.exists():
        raise FileNotFoundError(
            f"Table FAISS index not found: {index_path}. Run build_vector_store.py."
        )

    metadata_list = load_table_metadata_list(schema_name)

    import faiss

    index = faiss.read_index(str(index_path))
    n_meta = len(metadata_list)
    n_index = index.ntotal
    if n_meta != n_index:
        logger.warning(
            "Metadata count (%d) != FAISS ntotal (%d) for %s; mapping by index may be wrong.",
            n_meta,
            n_index,
            schema_name,
        )

    _table_index_cache[schema_name] = (index, metadata_list)
    logger.debug(
        "Loaded table FAISS index for %s (%d vectors, %d metadata rows)",
        schema_name,
        n_index,
        n_meta,
    )
    return index, metadata_list


def shortlist_candidate_tables(
    use_case: str,
    rephrased_question: str,
    keywords: list[str] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict]:
    """
    Return candidate table metadata dicts for the Table Agent.

    - Resolves schema from use_case via USE_CASE_TO_SCHEMA.
    - If N <= TABLE_SHORTLIST_THRESHOLD: returns all tables (full metadata dicts).
    - If N > TABLE_SHORTLIST_THRESHOLD: embeds query from rephrased_question + keywords,
      FAISS search with k = min(top_k, N), returns metadata rows at those indices.

    Each dict has schema_name, table_name, table_description only (no columns).
    """
    schema_name = USE_CASE_TO_SCHEMA.get(use_case)
    if not schema_name:
        logger.warning("Unknown use_case %r, cannot shortlist table metadata", use_case)
        return []

    metadata_list = load_table_metadata_list(schema_name)
    n = len(metadata_list)
    if n == 0:
        return []

    if n <= TABLE_SHORTLIST_THRESHOLD:
        logger.debug(
            "Schema %s has %d tables (<= %d); returning all as candidates.",
            schema_name,
            n,
            TABLE_SHORTLIST_THRESHOLD,
        )
        return [table_metadata_summary_for_agent(m) for m in metadata_list]

    query_text = _build_retrieval_query(rephrased_question, keywords)
    if not query_text.strip():
        logger.warning(
            "No query text for FAISS shortlist (%s); returning first %d tables.",
            schema_name,
            min(top_k, n),
        )
        return [
            table_metadata_summary_for_agent(m)
            for m in metadata_list[: min(top_k, n)]
        ]

    index, meta_aligned = _load_table_faiss_and_metadata(schema_name)
    if index.ntotal == 0:
        return []

    k = min(top_k, n, index.ntotal)
    import numpy as np

    model = _get_embedding_model()
    query_embedding = model.encode([query_text], show_progress_bar=False)
    query_vec = np.asarray(query_embedding, dtype=np.float32)
    distances, indices = index.search(query_vec, k)
    idx_list = indices[0].tolist()

    seen: set[int] = set()
    result: list[dict] = []
    for idx in idx_list:
        if idx < 0:
            continue
        if idx in seen:
            continue
        seen.add(idx)
        if idx >= len(meta_aligned):
            continue
        result.append(table_metadata_summary_for_agent(meta_aligned[idx]))

    return result


def candidate_tables_as_texts(candidates: list[dict]) -> list[str]:
    """Structured text per candidate table (for LLM context)."""
    return [metadata_entry_to_text(m) for m in candidates]
