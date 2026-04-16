"""
Column metadata retrieval for the Column Agent (Step 5b — service).

Loads nested table metadata and, when many columns are in scope for selected tables,
runs FAISS on the per-column index (aligned with metadata_store/{schema}_columns_metadata.json).

Candidate rows match the flat build output: schema_name, table_name, column_name,
data_type, description, table_description, fqn.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import (
    FAISS_COLUMN_INDEX_NAMES,
    FAISS_INDEX_DIR,
    METADATA_STORE_DIR,
    USE_CASE_TO_SCHEMA,
)
from backend.services.business_rules_retrieval import _get_embedding_model
from backend.services.table_metadata_retrieval import (
    _build_retrieval_query,
    load_table_metadata_list,
)

logger = logging.getLogger(__name__)

# Per docs/COLUMN_AGENT_5B_PLAN.md
COLUMN_SHORTLIST_THRESHOLD = 20
COLUMN_FAISS_TOP_K = 20

_column_index_cache: dict[str, tuple[Any, list[dict]]] = {}


def load_flat_column_metadata(schema_name: str) -> list[dict]:
    """
    Load metadata_store/{schema_name}_columns_metadata.json (one dict per column, FAISS order).
    """
    path = METADATA_STORE_DIR / f"{schema_name}_columns_metadata.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Column metadata not found: {path}. Run build_vector_store.py for this schema."
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}, got {type(data).__name__}")
    return data


def _table_fqn(schema_name: str, table_name: str) -> str:
    return f"{schema_name}.{table_name}"


def _normalize_allowed_tables(
    selected_tables: list[str],
    expected_schema: str,
) -> set[str]:
    """
    Parse FQNs 'schema.table'; keep only those whose schema matches expected_schema.
    Returns set of 'schema.table' strings.
    """
    allowed: set[str] = set()
    for raw in selected_tables or []:
        s = (raw or "").strip()
        if not s or "." not in s:
            logger.info("Skipping invalid selected table (expected schema.table): %r", raw)
            continue
        parts = s.split(".", 1)
        sch = parts[0].strip()
        tbl = parts[1].strip()
        if not tbl:
            continue
        if sch != expected_schema:
            logger.warning(
                "Skipping selected table %r: schema %r != use_case schema %r",
                s,
                sch,
                expected_schema,
            )
            continue
        allowed.add(_table_fqn(sch, tbl))
    return allowed


def _columns_from_nested_for_tables(
    metadata_list: list[dict],
    allowed_table_fqns: set[str],
) -> list[dict]:
    """
    Column dicts for LLM/FAISS filter. Order matches build_vector_store.nested_metadata_to_flat_columns:
    tables by table_name, columns by name.
    """
    out: list[dict] = []
    for m in sorted(metadata_list, key=lambda x: x["table_name"]):
        schema = m["schema_name"]
        table = m["table_name"]
        if _table_fqn(schema, table) not in allowed_table_fqns:
            continue
        table_desc = (m.get("table_description") or "").strip()
        for col in sorted(m.get("columns") or [], key=lambda c: c["name"]):
            name = col["name"]
            out.append(
                {
                    "schema_name": schema,
                    "table_name": table,
                    "column_name": name,
                    "data_type": (col.get("data_type") or "").strip(),
                    "description": (col.get("description") or "").strip(),
                    "table_description": table_desc,
                    "fqn": f"{schema}.{table}.{name}",
                }
            )
    return out


def _load_column_faiss_and_flat(schema_name: str) -> tuple[Any, list[dict]]:
    if schema_name in _column_index_cache:
        return _column_index_cache[schema_name]

    index_filename = FAISS_COLUMN_INDEX_NAMES.get(schema_name)
    if not index_filename:
        raise ValueError(f"No column FAISS index mapping for schema {schema_name!r}")

    index_path = FAISS_INDEX_DIR / index_filename
    if not index_path.exists():
        raise FileNotFoundError(
            f"Column FAISS index not found: {index_path}. Run build_vector_store.py."
        )

    flat_meta = load_flat_column_metadata(schema_name)

    import faiss

    index = faiss.read_index(str(index_path))
    n_meta = len(flat_meta)
    n_index = index.ntotal
    if n_meta != n_index:
        logger.warning(
            "Column metadata count (%d) != FAISS ntotal (%d) for %s; index mapping may be wrong.",
            n_meta,
            n_index,
            schema_name,
        )

    _column_index_cache[schema_name] = (index, flat_meta)
    logger.debug(
        "Loaded column FAISS for %s (%d vectors, %d metadata rows)",
        schema_name,
        n_index,
        n_meta,
    )
    return index, flat_meta


def shortlist_candidate_columns(
    use_case: str,
    rephrased_question: str,
    keywords: list[str] | None,
    selected_tables: list[str],
    *,
    faiss_top_k: int | None = None,
) -> list[dict]:
    """
    Return column metadata dicts for the Column Agent (only columns from selected tables).

    - Resolves schema from use_case.
    - If total columns across selected tables <= COLUMN_SHORTLIST_THRESHOLD: returns all.
    - Else: FAISS search on column index with k = min(faiss_top_k or COLUMN_FAISS_TOP_K, n),
      then keeps rows whose table is in selected_tables (order preserved by distance).

    If selected_tables is empty or none match the schema, returns [].
    """
    schema_name = USE_CASE_TO_SCHEMA.get(use_case)
    if not schema_name:
        logger.warning("Unknown use_case %r, cannot shortlist column metadata", use_case)
        return []

    allowed_tables = _normalize_allowed_tables(selected_tables, schema_name)
    if not allowed_tables:
        return []

    metadata_list = load_table_metadata_list(schema_name)
    all_for_selection = _columns_from_nested_for_tables(metadata_list, allowed_tables)
    n = len(all_for_selection)
    if n == 0:
        return []

    k_cfg = faiss_top_k if faiss_top_k is not None else COLUMN_FAISS_TOP_K

    if n <= COLUMN_SHORTLIST_THRESHOLD:
        logger.debug(
            "Selected tables in %s have %d columns (<= %d); returning all as candidates.",
            schema_name,
            n,
            COLUMN_SHORTLIST_THRESHOLD,
        )
        return all_for_selection

    query_text = _build_retrieval_query(rephrased_question, keywords)
    if not query_text.strip():
        logger.warning(
            "No query text for column FAISS (%s); returning first %d columns from selection.",
            schema_name,
            min(k_cfg, n),
        )
        return all_for_selection[: min(k_cfg, n)]

    try:
        index, flat_aligned = _load_column_faiss_and_flat(schema_name)
    except (FileNotFoundError, ValueError) as e:
        logger.warning("Column FAISS unavailable (%s); falling back to first k columns: %s", schema_name, e)
        return all_for_selection[: min(k_cfg, n)]

    if index.ntotal == 0:
        return all_for_selection[: min(k_cfg, n)]

    import numpy as np

    k = min(k_cfg, len(flat_aligned), index.ntotal)
    model = _get_embedding_model()
    query_embedding = model.encode([query_text], show_progress_bar=False)
    query_vec = np.asarray(query_embedding, dtype=np.float32)
    distances, indices = index.search(query_vec, k)
    idx_list = indices[0].tolist()

    picked: list[dict] = []
    seen_fqn: set[str] = set()

    for idx in idx_list:
        if idx < 0 or idx >= len(flat_aligned):
            continue
        row = flat_aligned[idx]
        tbl_fqn = _table_fqn(row["schema_name"], row["table_name"])
        if tbl_fqn not in allowed_tables:
            continue
        fqn = row.get("fqn") or f"{row['schema_name']}.{row['table_name']}.{row['column_name']}"
        if fqn in seen_fqn:
            continue
        seen_fqn.add(fqn)
        picked.append(row)
        if len(picked) >= k_cfg:
            break

    if not picked:
        logger.warning(
            "Column FAISS returned no rows inside selected tables for %s; using nested slice.",
            schema_name,
        )
        return all_for_selection[: min(k_cfg, n)]

    return picked
