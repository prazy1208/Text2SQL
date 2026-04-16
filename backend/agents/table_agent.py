"""
Table Agent (Stage 2 — table selection).
Inputs: use_case, rephrased_question, keywords (from Intent Agent).
Outputs: selected_tables as fully-qualified names schema.table_name validated against candidates.

Flow: shortlist candidate tables (metadata + optional FAISS) → LLM picks subset → validate against candidate set.
"""

from __future__ import annotations

import json
import logging
import re

from backend.services.llm_client import chat_completion
from backend.services.table_metadata_retrieval import (
    DEFAULT_TOP_K,
    candidate_tables_as_texts,
    shortlist_candidate_tables,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Table selection prompt (placeholders: rephrased_question, keywords_block, numbered_candidates)
# ---------------------------------------------------------------------------
TABLE_AGENT_PROMPT = """You are the Table Agent in a Natural Language to SQL system.

Your task is to select ALL database tables required to correctly answer the user's analytical question.

You are given:
1. The analytical question
2. Relevant keywords
3. A list of candidate tables

--------------------------------------------------
ANALYTICAL QUESTION
--------------------------------------------------
{rephrased_question}

--------------------------------------------------
KEYWORDS
--------------------------------------------------
{keywords_block}

--------------------------------------------------
CANDIDATE TABLES
--------------------------------------------------
{numbered_candidates}

--------------------------------------------------
SELECTION PRINCIPLES
--------------------------------------------------

- Select ALL tables that are necessary to answer the question correctly.
- Do NOT omit required tables, even if multiple tables are needed.
- If the question involves relationships between entities, include all relevant tables.
- Prefer correctness over minimality.

- Identify entities mentioned in the question (e.g., customers, accounts, patients, transactions, products, visits).
- Ensure each entity is represented by a selected table if required for analysis.

--------------------------------------------------
EXAMPLES
--------------------------------------------------

Finance Example:
Question: "Which accounts have the highest number of transactions?"
-> Selected Tables: ["finance_schema.accounts", "finance_schema.transactions"]

Retail Example:
Question: "Which customers bought which products?"
-> Selected Tables: ["retail_schema.customers", "retail_schema.orders", "retail_schema.products"]

Healthcare Example:
Question: "Which patients had which diagnoses during their visits?"
-> Selected Tables: ["healthcare_schema.patients", "healthcare_schema.visits", "healthcare_schema.diagnoses"]

--------------------------------------------------
STRICT RULES
--------------------------------------------------

- Select tables ONLY from the candidate list.
- Use exact table identifiers: schema_name.table_name
- Do NOT invent or modify table names
- Do NOT include column names
- Do NOT include explanations or extra text

- Do NOT include unrelated tables
- Do NOT include all tables by default
- Only include tables that are logically required

- If the query is ambiguous and no table can be confidently selected, return an empty list

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

Return ONLY valid JSON:

{{
  "selected_tables": ["schema_name.table_name"]
}}

OR

{{
  "selected_tables": ["schema_name.table1", "schema_name.table2"]
}}

OR

{{
  "selected_tables": []
}}

--------------------------------------------------
FINAL VALIDATION
--------------------------------------------------

Before responding, ensure:

- All entities in the question are covered by selected tables
- No required table is missing
- No unrelated table is included
- Output is valid JSON only"""


def _format_keywords(keywords: list[str] | None) -> str:
    if not keywords:
        return "(none)"
    lines = [f"- {k}" for k in keywords if k and str(k).strip()]
    return "\n".join(lines) if lines else "(none)"


def _candidate_fqn(c: dict) -> str:
    """Fully-qualified table name as used in prompts and validation."""
    return f"{c['schema_name']}.{c['table_name']}"


def _build_numbered_candidates_text(candidates: list[dict]) -> str:
    """Numbered list of table descriptions + explicit FQN for each row."""
    texts = candidate_tables_as_texts(candidates)
    blocks = []
    for i, (c, text) in enumerate(zip(candidates, texts), start=1):
        fqn = _candidate_fqn(c)
        blocks.append(f"### Candidate {i} — `{fqn}`\n{text}")
    return "\n\n".join(blocks)


def _parse_table_agent_response(response_text: str) -> list[str] | None:
    """
    Parse LLM response; return list of selected table strings or None on failure.
    """
    text = response_text.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text, flags=re.DOTALL)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text, flags=re.DOTALL)
    text = text.strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Failed to parse Table Agent JSON: %s", e)
        return None
    raw = data.get("selected_tables")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    out: list[str] = []
    for x in raw:
        if x is None:
            continue
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _validate_selected_tables(selected: list[str], allowed: set[str]) -> list[str]:
    """
    Keep only entries that exactly match a candidate FQN. Preserves order, deduplicates.
    """
    seen: set[str] = set()
    result: list[str] = []
    for name in selected:
        if name not in allowed:
            logger.info("Dropping invalid table selection (not in candidates): %r", name)
            continue
        if name in seen:
            continue
        seen.add(name)
        result.append(name)
    return result


def run_table_agent(
    use_case: str,
    rephrased_question: str,
    keywords: list[str] | None = None,
    top_k: int = DEFAULT_TOP_K,
) -> dict:
    """
    Select tables needed for the question using shortlist + LLM + validation.

    Returns:
        { "selected_tables": list[str] }  # FQNs schema.table_name, subset of shortlist candidates
    """
    rq = (rephrased_question or "").strip()
    candidates = shortlist_candidate_tables(
        use_case,
        rq,
        keywords,
        top_k=top_k,
    )

    if not candidates:
        logger.warning("Table Agent: no candidate tables for use_case=%r", use_case)
        return {"selected_tables": []}

    allowed = {_candidate_fqn(c) for c in candidates}
    numbered = _build_numbered_candidates_text(candidates)
    user_content = TABLE_AGENT_PROMPT.format(
        rephrased_question=rq or "(empty)",
        keywords_block=_format_keywords(keywords),
        numbered_candidates=numbered,
    )

    messages = [{"role": "user", "content": user_content}]

    try:
        response = chat_completion(messages)
    except Exception as e:
        logger.warning("Table Agent LLM call failed: %s", e)
        return {"selected_tables": []}

    parsed = _parse_table_agent_response(response)
    if parsed is None:
        logger.warning("Table Agent: could not parse LLM response.")
        return {"selected_tables": []}

    selected = _validate_selected_tables(parsed, allowed)
    return {"selected_tables": selected}
