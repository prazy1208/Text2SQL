"""
Column Agent (Stage 2b — column selection).
Inputs: use_case, rephrased_question, keywords (same as Table Agent), plus selected_tables from Table Agent.
Outputs: selected_columns as { "schema.table": ["col1", ...] } validated against shortlist ∪ FK join columns.

Flow: shortlist candidate columns (nested metadata + optional column FAISS) → LLM picks subset → validate (candidates plus source/target columns from relationship rows).
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
while keeping the selection lean, complete, and interpretable.

You are given:
1. The analytical question
2. Relevant keywords
3. Foreign-key relationships between selected tables
4. Numbered candidate columns (each is schema.table.column)

--------------------------------------------------
ANALYTICAL QUESTION
--------------------------------------------------
{rephrased_question}

--------------------------------------------------
KEYWORDS
--------------------------------------------------
{keywords_block}

--------------------------------------------------
FOREIGN KEY RELATIONSHIPS
--------------------------------------------------
{relationships_block}

Each relationship is formatted as:
schema.table.column -> schema.table.column

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
- If the output represents entities, include both ID and descriptive fields.

--------------------------------------------------
RELATIONSHIP-AWARE COLUMN COMPLETENESS (CRITICAL)
--------------------------------------------------

- Use the provided relationships to understand how tables connect at the column level.

- If multiple tables are involved:
  → You MUST include join key columns from BOTH sides of each relationship.

- If two tables are indirectly related:
  → Include join keys for ALL intermediate relationships in the chain.

- Think in join paths:
  table A.column → table B.column → table C.column

- NEVER skip join keys required to connect tables.

- If a required join column is NOT present in the candidate list:
  → You MUST still include it if it exists in the relationship definitions.

- Only include columns that exist in:
  1. Candidate columns OR
  2. Relationship definitions (for join completeness)

--------------------------------------------------
CRITICAL RULES
--------------------------------------------------

1. JOIN HANDLING (STRICT):
- Join keys are MANDATORY when multiple tables are involved.
- Include both sides of the join (e.g., account_id in both tables).
- Ensure join paths are fully connected (no broken joins).

2. AGGREGATION (STRICT):
- For COUNT → include identifier column (e.g., transaction_id, visit_id)
- For SUM/AVG → include numeric columns (e.g., amount, total_cost)
- For GROUP BY → include grouping identifiers (e.g., account_id, product_id)
- ALWAYS include identifier columns even in aggregation queries

3. FILTERS / CONDITIONS:
- Include columns needed for filtering (dates, categories, status, etc.)

4. OUTPUT FIELDS:
- Include human-readable columns when needed (names, categories)
- Include identifier columns for uniqueness

5. RELATIONSHIP COMPLETENESS:
- If entities are connected through intermediate tables:
  → Include all required join columns across the chain
- Example:
  patients → visits → diagnoses
  requires:
  patient_id (patients + visits)
  visit_id (visits + diagnoses)

--------------------------------------------------
STRICT RULES
--------------------------------------------------

- Use exact table keys: schema_name.table_name
- Use exact column names (only column_name in arrays)
- Do NOT invent or modify column names
- Do NOT include explanations or extra text

- Do NOT include all columns by default
- Do NOT include unrelated columns

- Columns may be selected from:
  1. Candidate list
  2. Relationship expansion (ONLY for required join keys)

- If the query is ambiguous or required columns cannot be determined, return an empty object

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

Before responding, ensure:

- All join paths are fully connected via required columns
- No join key is missing if multiple tables are involved
- Intermediate relationships have their key columns included
- Aggregation, grouping, and filtering columns are present
- Identifier and human-readable columns are included where needed
- No unrelated columns are selected
- Output is valid JSON only"""


def _format_keywords(keywords: list[str] | None) -> str:
    if not keywords:
        return "(none)"
    lines = [f"- {k}" for k in keywords if k and str(k).strip()]
    return "\n".join(lines) if lines else "(none)"


def _format_relationships_block(relationships: list[dict] | None) -> str:
    if not relationships:
        return "(none)"
    lines: list[str] = []
    for r in relationships:
        rt = (r.get("relationship_text") or "").strip()
        if rt:
            lines.append(f"- {rt}")
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


def _merge_relationship_join_columns_into_allowed(
    allowed_by_table: dict[str, set[str]],
    relationships: list[dict] | None,
) -> None:
    """Add source_column / target_column from FK rows so join keys validate if missing from shortlist."""
    if not relationships:
        return
    for r in relationships:
        sn = (r.get("schema_name") or "").strip()
        st = (r.get("source_table") or "").strip()
        sc = (r.get("source_column") or "").strip()
        ts = (r.get("target_schema") or "").strip()
        tt = (r.get("target_table") or "").strip()
        tc = (r.get("target_column") or "").strip()
        if sn and st and sc:
            allowed_by_table.setdefault(f"{sn}.{st}", set()).add(sc)
        if ts and tt and tc:
            allowed_by_table.setdefault(f"{ts}.{tt}", set()).add(tc)


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
    """Keep only tables/columns allowed (shortlist + FK relationship columns). Preserves order, dedupes."""
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
    relationships: list[dict] | None = None,
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
    _merge_relationship_join_columns_into_allowed(allowed_by_table, relationships)
    numbered = _build_numbered_candidates_text(candidates)
    user_content = COLUMN_AGENT_PROMPT.format(
        rephrased_question=rq or "(empty)",
        keywords_block=_format_keywords(keywords),
        relationships_block=_format_relationships_block(relationships),
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
