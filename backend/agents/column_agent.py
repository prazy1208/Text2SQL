"""
Column Agent (Stage 2b — column selection).
Inputs: use_case, rephrased_question, keywords (same as Table Agent), plus selected_tables from Table Agent.
Outputs: selected_columns as { "schema.table": ["col1", ...] } validated against shortlist candidates.

Flow: shortlist candidate columns (nested metadata + optional column FAISS) → LLM picks subset → validate.
"""

from __future__ import annotations

import json
import logging
import re

from backend.services.column_metadata_retrieval import shortlist_candidate_columns
from backend.services.llm_client import chat_completion

logger = logging.getLogger(__name__)

COLUMN_AGENT_PROMPT = """You are the Column Agent in a Natural Language to SQL system.

Your task is to select ALL necessary columns required to correctly answer the analytical question,
while keeping the selection lean, complete, and interpretable, using only the candidate columns provided.

You are given:
1. The analytical question
2. Relevant keywords
3. Numbered candidate columns (each is schema.table.column)

--------------------------------------------------
ANALYTICAL QUESTION
--------------------------------------------------
{rephrased_question}

--------------------------------------------------
KEYWORDS
--------------------------------------------------
{keywords_block}

--------------------------------------------------
CANDIDATE COLUMNS
--------------------------------------------------
{numbered_candidates}

--------------------------------------------------
SELECTION PRINCIPLES
--------------------------------------------------

- Select ALL columns required to correctly answer the query.
- Do NOT omit required columns, even if multiple are needed.
- Prefer correctness over minimality, but avoid unnecessary columns.

- Identify entities, measures, filters, and relationships from the question.
- Ensure each entity or operation in the query is supported by selected columns.

- ALWAYS include identifier columns (e.g., *_id) for every table used.
- Include human-readable columns (e.g., name, category) when the query refers to entities like customers, products, or patients.
- If the output represents entities (customers, patients, products), include both ID and descriptive fields.

--------------------------------------------------
CRITICAL RULES
--------------------------------------------------

1. JOIN HANDLING (STRICT):
- If multiple tables are involved, you MUST include join keys.
- Join keys are mandatory and typically include *_id columns.
- If two tables are indirectly related, include the intermediate table's join keys as well.
- NEVER skip join paths between tables.

2. AGGREGATION (STRICT):
- For COUNT → include an identifier column (e.g., transaction_id, visit_id)
- For SUM/AVG → include numeric columns (e.g., amount, total_cost)
- For GROUP BY → include entity identifiers (e.g., account_id, product_id)
- ALWAYS include identifier columns even in aggregation queries for completeness

3. FILTERS / CONDITIONS:
- Include columns required for filtering (e.g., dates, categories, status)

4. OUTPUT FIELDS:
- Include human-readable columns when needed (e.g., names, categories)
- Include identifier columns (e.g., *_id) to uniquely represent results

5. RELATIONSHIP COMPLETENESS:
- If the query involves entities connected through another table, include all necessary tables and their key columns.
- Example: patients → visits → diagnoses requires visit_id to connect them.
- Do NOT skip intermediate relationships.

--------------------------------------------------
STRICT RULES
--------------------------------------------------

- Select columns ONLY from the candidate list.
- Use exact table keys: schema_name.table_name
- Use exact column names (only column_name in arrays).
- Do NOT invent or modify column names.
- Do NOT include columns from tables not present in candidates.
- Do NOT include explanations or extra text.

- Do NOT include all columns by default.
- Do NOT include unrelated columns.

- If the query is ambiguous or required columns cannot be determined, return an empty object.

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

Return ONLY valid JSON:

{{
  "selected_columns": {{
    "schema_name.table_name": ["column_a", "column_b"]
  }}
}}

Use one key per table that needs columns. Omit tables that need no columns.

Example:

{{
  "selected_columns": {{
    "finance_schema.transactions": ["transaction_id", "account_id"],
    "finance_schema.accounts": ["account_id"]
  }}
}}

Or if nothing applies:

{{
  "selected_columns": {{}}
}}

--------------------------------------------------
FINAL VALIDATION
--------------------------------------------------

- Ensure all required join keys are included if multiple tables are involved (no skipped join paths)
- Ensure intermediate / bridge tables have their key columns when relationships are indirect
- Ensure required columns for aggregation/grouping/filtering are included
- Ensure identifier or human-readable columns are included for interpretability
- Ensure no unrelated columns are selected
- Ensure output is valid JSON only"""


def _format_keywords(keywords: list[str] | None) -> str:
    if not keywords:
        return "(none)"
    lines = [f"- {k}" for k in keywords if k and str(k).strip()]
    return "\n".join(lines) if lines else "(none)"


def _table_fqn(row: dict) -> str:
    return f"{row['schema_name']}.{row['table_name']}"


def _build_numbered_candidates_text(candidates: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(candidates, start=1):
        fqn = c.get("fqn") or f"{c['schema_name']}.{c['table_name']}.{c['column_name']}"
        dtype = (c.get("data_type") or "").strip() or "(unknown type)"
        tdesc = (c.get("table_description") or "").strip() or "(no table description)"
        cdesc = (c.get("description") or "").strip() or "(no description)"
        body = "\n".join(
            [
                f"Schema: {c['schema_name']}",
                f"Table: {c['table_name']}",
                f"Column: {c['column_name']}",
                f"Type: {dtype}",
                f"Table description: {tdesc}",
                f"Column description: {cdesc}",
            ]
        )
        blocks.append(f"### Candidate {i} — `{fqn}`\n{body}")
    return "\n\n".join(blocks)


def _allowed_columns_by_table(candidates: list[dict]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for c in candidates:
        t = _table_fqn(c)
        out.setdefault(t, set()).add(c["column_name"])
    return out


def _parse_column_agent_response(response_text: str) -> dict[str, list[str]] | None:
    text = response_text.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text, flags=re.DOTALL)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text, flags=re.DOTALL)
    text = text.strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Failed to parse Column Agent JSON: %s", e)
        return None
    raw = data.get("selected_columns")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        return None
    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        if k is None:
            continue
        tk = str(k).strip()
        if not tk:
            continue
        if not isinstance(v, list):
            return None
        cols: list[str] = []
        for x in v:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                cols.append(s)
        out[tk] = cols
    return out


def _validate_selected_columns(
    parsed: dict[str, list[str]],
    allowed_by_table: dict[str, set[str]],
) -> dict[str, list[str]]:
    """Keep only tables and columns that appear in candidates. Preserves order, dedupes columns."""
    result: dict[str, list[str]] = {}
    for table_fqn, cols in parsed.items():
        allowed_cols = allowed_by_table.get(table_fqn)
        if not allowed_cols:
            logger.info("Dropping unknown table in column selection: %r", table_fqn)
            continue
        seen: set[str] = set()
        good: list[str] = []
        for col in cols:
            if col not in allowed_cols:
                logger.info("Dropping invalid column %r for table %r", col, table_fqn)
                continue
            if col in seen:
                continue
            seen.add(col)
            good.append(col)
        if good:
            result[table_fqn] = good
    return result


def run_column_agent(
    use_case: str,
    rephrased_question: str,
    keywords: list[str] | None,
    selected_tables: list[str],
    *,
    faiss_top_k: int | None = None,
) -> dict:
    """
    Select columns for selected_tables using shortlist + LLM + validation.

    Returns:
        { "selected_columns": dict[str, list[str]] }  # table FQN -> column names
    """
    rq = (rephrased_question or "").strip()
    st = [s for s in (selected_tables or []) if s and str(s).strip()]
    if not st:
        return {"selected_columns": {}}

    candidates = shortlist_candidate_columns(
        use_case,
        rq,
        keywords,
        st,
        faiss_top_k=faiss_top_k,
    )
    if not candidates:
        logger.warning("Column Agent: no candidate columns for use_case=%r", use_case)
        return {"selected_columns": {}}

    allowed_by_table = _allowed_columns_by_table(candidates)
    numbered = _build_numbered_candidates_text(candidates)
    user_content = COLUMN_AGENT_PROMPT.format(
        rephrased_question=rq or "(empty)",
        keywords_block=_format_keywords(keywords),
        numbered_candidates=numbered,
    )
    messages = [{"role": "user", "content": user_content}]

    try:
        response = chat_completion(messages)
    except Exception as e:
        logger.warning("Column Agent LLM call failed: %s", e)
        return {"selected_columns": {}}

    parsed = _parse_column_agent_response(response)
    if parsed is None:
        logger.warning("Column Agent: could not parse LLM response.")
        return {"selected_columns": {}}

    selected = _validate_selected_columns(parsed, allowed_by_table)
    return {"selected_columns": selected}
