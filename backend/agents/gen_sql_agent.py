"""
Gen-SQL Agent (Step 7 — SQL synthesis).
Inputs: rephrased_question, business_insights, few_shot_examples, selected_tables, selected_columns;
optional relationships (same FK row dicts as Table Agent — from metadata_store JSON) for JOIN hints.
Output: generated_sql (single read-only statement) plus reasoning_summary (often empty when model returns SQL only).

Uses the dedicated Gen-SQL model via llm_client (agent_name=gen_sql).
Dialect: PostgreSQL (Supabase).
"""

from __future__ import annotations

import json
import logging
import re

from backend.services.llm_client import AGENT_GEN_SQL, chat_completion

logger = logging.getLogger(__name__)

GEN_SQL_SYSTEM = """You are the SQL Generation Agent. Follow the user message exactly for process and output shape.
Dialect: PostgreSQL (Supabase). Emit a single read-only statement: SELECT or WITH … SELECT only (no INSERT, UPDATE, DELETE, DDL).
Use PostgreSQL syntax and built-ins (e.g. date_trunc, INTERVAL '1 month', CURRENT_DATE, standard string/date types).
Output must match what the user message asks for (typically SQL only, no prose)."""

GEN_SQL_AGENT_PROMPT = """You are the SQL Generation Agent in a Natural Language to SQL system.

Your task is to generate a correct, efficient, and executable SQL query.

--------------------------------------------------
INPUTS
--------------------------------------------------

ANALYTICAL QUESTION:
{rephrased_question}

SELECTED TABLES:
{selected_tables}

SELECTED COLUMNS:
{selected_columns}

TABLE RELATIONSHIPS:
{relationships_block}

FEW-SHOT PATTERNS:
{few_shot_block}

BUSINESS RULES:
{business_rules_block}

--------------------------------------------------
SQL GENERATION PROCESS (FOLLOW STRICTLY)
--------------------------------------------------

You MUST construct the SQL query following the logical order of SQL execution:

1. FROM / JOIN
2. WHERE
3. GROUP BY
4. HAVING
5. SELECT
6. DISTINCT
7. ORDER BY
8. LIMIT / OFFSET

--------------------------------------------------

Step 1: FROM / JOIN
- Start with base tables
- If multiple tables are present:
  - Use the provided relationships to JOIN tables
  - Do NOT assume joins
  - Do NOT skip intermediate tables

--------------------------------------------------

Step 2: WHERE
- Apply filtering conditions (dates, categories, thresholds, etc.)
- Use business rules where applicable

--------------------------------------------------

Step 3: GROUP BY
- Apply only if aggregation is required

--------------------------------------------------

Step 4: HAVING
- Apply only if filtering on aggregated results is needed

--------------------------------------------------

Step 5: SELECT
- Include required columns
- Apply aggregation functions where needed
- Use aliases for readability

--------------------------------------------------

Step 6: DISTINCT
- Apply only if the query explicitly requires unique values

--------------------------------------------------

Step 7: ORDER BY
- Apply when sorting or ranking is needed

--------------------------------------------------

Step 8: LIMIT / OFFSET
- Apply LIMIT to restrict output size
- Use LIMIT 100 by default unless specified otherwise

--------------------------------------------------
IMPORTANT NOTE
--------------------------------------------------

- Not all steps are required for every query
- Only include clauses that are necessary based on the analytical question
- Do NOT force unused clauses into the query

--------------------------------------------------
CRITICAL RULES
--------------------------------------------------

- Use ONLY provided tables and columns
- Do NOT invent tables or columns
- Do NOT include columns not selected earlier
- Ensure joins are correct and complete using relationships
- Use only SELECT queries (NO INSERT, UPDATE, DELETE, DROP)
- Ensure compatibility with PostgreSQL (Supabase runs PostgreSQL). Use standard PostgreSQL syntax and functions.
- Prefer simple, clear, and efficient queries

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

Return ONLY the SQL query.
Do NOT include explanations or extra text.
"""


def _format_business_rules(insights: list[str] | None) -> str:
    if not insights:
        return "(none)"
    lines = [f"- {str(x).strip()}" for x in insights if x and str(x).strip()]
    return "\n".join(lines) if lines else "(none)"


def _format_few_shot(examples: list[dict] | None) -> str:
    if not examples:
        return "(none)"
    blocks: list[str] = []
    for i, ex in enumerate(examples, start=1):
        if not isinstance(ex, dict):
            continue
        eid = ex.get("id", "—")
        qt = str(ex.get("query_type") or "").strip()
        qn = str(ex.get("question_text") or "").strip()
        sql = str(ex.get("sql_query") or "").strip()
        blocks.append(
            f"### Example {i} (id={eid})\n"
            f"- query_type: {qt or '—'}\n"
            f"- question_text: {qn or '—'}\n"
            f"- sql_query:\n{sql or '(none)'}"
        )
    return "\n\n".join(blocks) if blocks else "(none)"


def _format_selected_tables(tables: list[str] | None) -> str:
    if not tables:
        return "(none — do not invent tables)"
    return "\n".join(f"- `{t}`" for t in tables if t and str(t).strip())


def _format_selected_columns(selected: dict[str, list[str]] | None) -> str:
    if not selected:
        return "(none — do not invent columns)"
    lines: list[str] = []
    for table_fqn, cols in sorted(selected.items()):
        if not table_fqn or not str(table_fqn).strip():
            continue
        if not isinstance(cols, list):
            continue
        names = [str(c).strip() for c in cols if c and str(c).strip()]
        if not names:
            lines.append(f"- `{table_fqn}`: (no columns listed)")
        else:
            lines.append(f"- `{table_fqn}`: {', '.join(names)}")
    return "\n".join(lines) if lines else "(none — do not invent columns)"


def _format_relationships_block(relationships: list[dict] | None) -> str:
    """Same shape as Table/Column agents: rows with relationship_text from domain table_relationships."""
    if not relationships:
        return (
            "(None provided. Infer joins only from selected columns, few-shot patterns, and keys such as *_id. "
            "Do not invent foreign keys.)"
        )
    lines: list[str] = []
    for r in relationships:
        rt = (r.get("relationship_text") or "").strip()
        if rt:
            lines.append(f"- {rt}")
    return "\n".join(lines) if lines else "(none)"


def _parse_gen_sql_response(response_text: str) -> tuple[str, str] | None:
    """
    Return (generated_sql, reasoning_summary).
    Supports: JSON legacy {{generated_sql, reasoning_summary}}, fenced ```sql```, or plain SQL starting WITH/SELECT/EXPLAIN.
    """
    text = (response_text or "").strip()
    if not text:
        return None

    # ```sql ... ``` or ``` ... ```
    if "```" in text:
        if "```json" in text.lower():
            text = re.sub(r"^.*?```json\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
        else:
            text = re.sub(r"^.*?```(?:sql|postgresql)?\s*", "", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"\s*```\s*$", "", text, flags=re.DOTALL).strip()

    # Legacy JSON body
    if text.lstrip().startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "generated_sql" in data:
                sql = str(data.get("generated_sql") or "").strip()
                reason = str(data.get("reasoning_summary") or "").strip()
                return sql, reason
        except (json.JSONDecodeError, TypeError):
            pass

    # Plain SQL (prompt: return ONLY the query)
    if re.match(r"^\s*(WITH|SELECT|EXPLAIN)\b", text, re.IGNORECASE):
        return text.strip(), ""

    logger.warning("Gen-SQL response is neither valid JSON nor SQL-looking: %r", text[:300])
    return None


def run_gen_sql(
    use_case: str,
    rephrased_question: str,
    business_insights: list[str] | None,
    few_shot_examples: list[dict] | None,
    selected_tables: list[str] | None,
    selected_columns: dict[str, list[str]] | None,
    *,
    relationships: list[dict] | None = None,
) -> dict:
    """
    Synthesize one SQL query from pipeline context.

    relationships: optional FK rows for the active domain (from list_relationships_from_metadata; same as Table Agent).

    Returns:
        { "generated_sql": str, "reasoning_summary": str }
    """
    _ = use_case  # not in current user-facing prompt; keep signature for callers
    rq = (rephrased_question or "").strip()
    if not rq:
        return {
            "generated_sql": "",
            "reasoning_summary": "Missing rephrased_question; cannot generate SQL.",
        }

    if not selected_tables:
        return {
            "generated_sql": "",
            "reasoning_summary": "No tables selected upstream; cannot generate SQL.",
        }

    user_msg = GEN_SQL_AGENT_PROMPT.format(
        rephrased_question=rq,
        selected_tables=_format_selected_tables(selected_tables),
        selected_columns=_format_selected_columns(selected_columns),
        relationships_block=_format_relationships_block(relationships),
        few_shot_block=_format_few_shot(few_shot_examples),
        business_rules_block=_format_business_rules(business_insights),
    )

    messages = [
        {"role": "system", "content": GEN_SQL_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    try:
        raw = chat_completion(messages, agent_name=AGENT_GEN_SQL)
    except Exception as e:
        logger.exception("Gen-SQL Agent LLM call failed")
        return {
            "generated_sql": "",
            "reasoning_summary": f"LLM error: {e}",
        }

    parsed = _parse_gen_sql_response(raw)
    if parsed is None:
        return {
            "generated_sql": "",
            "reasoning_summary": "Could not extract SQL from model response.",
        }

    sql, reason = parsed
    return {
        "generated_sql": sql,
        "reasoning_summary": reason,
    }
