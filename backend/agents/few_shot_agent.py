"""
Few-Shot Pattern Agent: selects the most relevant examples (question + query_type only in the prompt).

The LLM returns selected question/query_type pairs; we map them to full rows including sql_query for Gen-SQL.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.services.fewshot_retrieval import list_all_few_shot_examples
from backend.services.llm_client import chat_completion

logger = logging.getLogger(__name__)

FEW_SHOT_AGENT_PROMPT = """You are the Few-Shot Retrieval Agent in a Natural Language to SQL system.

Your task is to select the MOST RELEVANT examples from the provided candidate list.
These examples will be used by another agent to generate SQL.

--------------------------------------------------
INPUTS
--------------------------------------------------

ANALYTICAL QUESTION:
{rephrased_question}

KEYWORDS:
{keywords_block}

CANDIDATE EXAMPLES:
Each example contains:
- question
- query_type

{candidate_examples_block}

--------------------------------------------------
SELECTION STRATEGY (FOLLOW STRICTLY)
--------------------------------------------------

Step 1: Match Query Type (MOST IMPORTANT)

- Identify the query_type of the analytical question based on its structure.
- Focus on the type of operation (e.g., aggregation, filtering, join, ranking, time-based).
- Select examples that have the SAME or CLOSEST query_type.

--------------------------------------------------

Step 2: Match Meaning (SECONDARY)

- From the query_type-matched examples, select those most similar in meaning.
- Use the analytical question and keywords for similarity.
- Prefer examples that reflect similar intent (e.g., comparison, totals, trends).

--------------------------------------------------
IMPORTANT RULES
--------------------------------------------------

- Prioritize query_type match over keyword similarity.
- Do NOT select examples based only on shared words.
- Do NOT select irrelevant query types.
- Avoid selecting duplicate or nearly identical examples.
- If multiple query types are involved, select examples that together best represent the query.
- Include every example that is genuinely relevant; omit examples that are not. Order by relevance (best first).

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

Return ONLY valid JSON:

{{
  "selected_examples": [
    {{
      "question": "...",
      "query_type": "..."
    }},
    {{
      "question": "...",
      "query_type": "..."
    }}
  ]
}}

- Do NOT include SQL.
- Do NOT include explanations or extra text.
"""


def _format_keywords_block(keywords: list[str] | None) -> str:
    if not keywords:
        return "(none)"
    lines = [f"- {k}" for k in keywords if k and str(k).strip()]
    return "\n".join(lines) if lines else "(none)"


def _build_candidate_examples_block(rows: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for i, r in enumerate(rows, start=1):
        qt = (r.get("query_type") or "").strip()
        qn = (r.get("question_text") or "").strip()
        blocks.append(
            f"Example {i}:\n"
            f"- question: {json.dumps(qn)}\n"
            f"- query_type: {json.dumps(qt)}"
        )
    return "\n\n".join(blocks) if blocks else "(empty catalog)"


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split())


def _parse_selected_examples(response_text: str) -> list[dict[str, str]] | None:
    text = response_text.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text, flags=re.DOTALL)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text, flags=re.DOTALL)
    text = text.strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Failed to parse Few-Shot Agent JSON: %s", e)
        return None
    raw = data.get("selected_examples")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        q = item.get("question") if item.get("question") is not None else item.get("question_text")
        qt = item.get("query_type")
        if q is None or qt is None:
            continue
        out.append({"question": str(q).strip(), "query_type": str(qt).strip()})
    return out


def _resolve_examples_by_pairs(
    catalog: list[dict[str, Any]],
    selected: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Map LLM-selected question/query_type back to full catalog rows (order preserved, deduped)."""
    out: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    for sel in selected:
        qn = _norm_text(sel["question"])
        qt = _norm_text(sel["query_type"])
        key = (qn, qt)
        if key in seen_keys:
            continue
        row = _find_catalog_row(catalog, qn, qt)
        if row is None:
            logger.info(
                "Few-Shot Agent: no catalog row for question=%r query_type=%r",
                sel.get("question"),
                sel.get("query_type"),
            )
            continue
        seen_keys.add(key)
        out.append(dict(row))
    return out


def _find_catalog_row(
    catalog: list[dict[str, Any]],
    question_norm: str,
    query_type_norm: str,
) -> dict[str, Any] | None:
    for r in catalog:
        rq = _norm_text(str(r.get("question_text") or ""))
        rt = _norm_text(str(r.get("query_type") or ""))
        if rq == question_norm and rt == query_type_norm:
            return r
    return None


def run_few_shot_agent(
    rephrased_question: str,
    keywords: list[str] | None = None,
    business_insights: list[str] | None = None,
) -> dict[str, Any]:
    """
    Select all few-shot examples the LLM marks as relevant (question + query_type in prompt; full rows returned).

    ``business_insights`` is accepted for API compatibility; the current prompt does not include it.

    Returns:
        { "few_shot_examples": [ { id, question_text, sql_query, query_type }, ... ] }
    """
    _ = business_insights  # not in FEW_SHOT_AGENT_PROMPT; reserved for future prompt versions

    catalog = list_all_few_shot_examples()
    if not catalog:
        return {"few_shot_examples": []}

    rq = (rephrased_question or "").strip()
    user_content = FEW_SHOT_AGENT_PROMPT.format(
        rephrased_question=rq or "(empty)",
        keywords_block=_format_keywords_block(keywords),
        candidate_examples_block=_build_candidate_examples_block(catalog),
    )
    messages = [{"role": "user", "content": user_content}]

    try:
        response = chat_completion(messages)
    except Exception as e:
        logger.warning("Few-Shot Agent LLM call failed: %s", e)
        return {"few_shot_examples": []}

    parsed = _parse_selected_examples(response)
    if parsed is None:
        logger.warning("Few-Shot Agent: could not parse LLM response.")
        return {"few_shot_examples": []}

    examples = _resolve_examples_by_pairs(catalog, parsed)
    return {"few_shot_examples": examples}
