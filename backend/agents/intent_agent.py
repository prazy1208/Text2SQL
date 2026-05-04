"""
Intent Agent (Stage 1).
Inputs: user_message, use_case (+ optional conversation context).
Outputs: rephrased_question, keywords, business_insights, resolved_question.
Steps: (1) Retrieve business rules via FAISS. (2) LLM interprets intent with rules and
conversation context; returns structured JSON.
"""

import json
import logging
import re
from typing import Any

from backend.services.business_rules_retrieval import retrieve_business_insights

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent prompt (user question + retrieved business rules → structured intent)
# ---------------------------------------------------------------------------
INTENT_PROMPT_TEMPLATE = """You are the Intent Agent in an enterprise Natural Language to SQL system.

Your role is to interpret the user's analytical question and convert it into a clear, structured description of the user's intent.

You are NOT responsible for selecting tables, columns, or generating SQL queries.

You must only interpret the business meaning of the user's request.

--------------------------------------------------
INPUTS
--------------------------------------------------

Current User Message:
{user_question}

Conversation Context:
{conversation_context}

Relevant Business Rules:
{retrieved_business_rules}

The business rules are domain knowledge retrieved using semantic similarity search.
They describe analytical concepts and insights relevant to the user's question.

--------------------------------------------------
YOUR TASK
--------------------------------------------------

1. Carefully read the user's question.

2. Identify the analytical objective behind the current message, using context when needed.

3. Use the provided business rules only to better understand the business meaning of the request.

4. Rephrase the user request into a clear analytical instruction that precisely describes the user's goal.

   - If the current message is incomplete (for example: "yes", "no", "also by branch", "for last month"),
     use conversation context to resolve meaning.
   - If context is not needed, keep the interpretation focused on the current message.

5. Extract important analytical keywords (including intent type such as aggregation, comparison, ranking, trend, distribution, lookup) that will help downstream agents identify relevant datasets and attributes.

6. Identify business insights from the provided rules that align with the user's analytical intent.

--------------------------------------------------
IMPORTANT CONSTRAINTS
--------------------------------------------------

Follow these rules strictly:

• Do NOT generate SQL queries
• Do NOT reference database tables, schemas, or column names
• Do NOT invent new business rules or insights
• Only use insights that logically align with the retrieved rules
• If the user question is vague, clarify it while preserving the original meaning
• Keep the interpretation neutral and grounded in the provided information
• If the message is only a greeting or small talk with no analytical request, use a low
  confidence_score (below 0.95), keep rephrased_question honest (do not invent a dataset query),
  and use clarification_question only when you can state a concrete yes/no check.

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

Return ONLY valid JSON using the following structure:

{{
  "rephrased_question": "Clear analytical version of the user's question",
  "resolved_question": "Final merged question after applying context when needed",
  "confidence_score": 0.85,
  "clarification_question": "Short yes/no confirmation question for the user",
  "keywords": [
    "keyword1",
    "keyword2",
    "keyword3"
  ],
  "business_insights": [
    "Relevant insight derived from the business rules",
    "Another aligned insight if applicable"
  ]
}}

confidence_score must be your estimated certainty as a number from 0.0 to 1.0 inclusive
(e.g. 0.85 means 85% confident). Downstream code converts this to a percentage.

Include analytical intent (e.g. aggregation, comparison, ranking, trend) in the keywords list where relevant."""


CONTEXT_SUMMARY_MAX_CHARS = 1200


def normalize_confidence_score(raw: Any) -> int:
    """
    Map model output to integer percent 0-100 for storage and UI.

    - If raw is strictly between 0 and 1 inclusive of 1 (fractional / probability
      style), multiply by 100 and round (so 1 or 1.0 → 100, 0.85 → 85).
    - Otherwise treat raw as already a percentage (e.g. 72 → 72).
    - None or invalid values default to 50 (conservative for confirmation gating).
    """
    if raw is None:
        return 50
    try:
        x = float(raw)
    except (TypeError, ValueError):
        return 50
    if 0.0 < x <= 1.0:
        return max(0, min(100, int(round(x * 100))))
    return max(0, min(100, int(round(x))))


def _clean_text(v: Any) -> str:
    return str(v or "").strip()


def _normalize_message_entry(entry: dict[str, Any]) -> dict[str, str] | None:
    """Normalize message dict to {role, content} for context building."""
    if not isinstance(entry, dict):
        return None
    role = _clean_text(entry.get("role") or "user").lower()
    if role not in {"user", "assistant", "system"}:
        role = "user"
    content = _clean_text(entry.get("content"))
    if not content:
        return None
    return {"role": role, "content": content}


def _compact_text(text_value: str, max_chars: int = CONTEXT_SUMMARY_MAX_CHARS) -> str:
    text_value = _clean_text(text_value)
    if len(text_value) <= max_chars:
        return text_value
    return f"{text_value[:max_chars].rstrip()}..."


def _summarize_messages(messages: list[dict[str, str]]) -> str:
    """
    Deterministic, token-safe summary for older turns.
    This is a lightweight bridge until long-term memory retrieval is added.
    """
    if not messages:
        return "(none)"
    chunks: list[str] = []
    for m in messages:
        role = m["role"]
        content = _compact_text(m["content"], 220)
        chunks.append(f"- {role}: {content}")
    joined = "\n".join(chunks)
    return _compact_text(joined, CONTEXT_SUMMARY_MAX_CHARS)


def _build_conversation_context_block(
    user_question: str,
    recent_messages: list[dict[str, Any]] | None = None,
    last_confirmed_intent: str | None = None,
    pending_intent: str | None = None,
    session_summary: dict[str, Any] | str | None = None,
) -> str:
    """
    Build context block for intent prompt using policy:
      - 0 previous messages: current only.
      - 1-3 previous messages: include full previous turns.
      - >3 previous messages: include last 2 full turns + summary of older turns.
    """
    normalized = []
    for entry in recent_messages or []:
        m = _normalize_message_entry(entry)
        if m:
            normalized.append(m)

    lines: list[str] = []
    lines.append(f"- Current message: {user_question}")

    if not normalized:
        lines.append("- Previous messages: (none)")
    elif len(normalized) <= 3:
        lines.append("- Previous messages (full):")
        for m in normalized:
            lines.append(f"  - {m['role']}: {_compact_text(m['content'], 400)}")
    else:
        older = normalized[:-2]
        latest = normalized[-2:]
        lines.append("- Previous messages (recent full turns):")
        for m in latest:
            lines.append(f"  - {m['role']}: {_compact_text(m['content'], 400)}")
        lines.append("- Older messages summary:")
        lines.append(f"  {_summarize_messages(older)}")

    if last_confirmed_intent:
        lines.append(f"- Last confirmed intent: {_compact_text(last_confirmed_intent, 350)}")
    else:
        lines.append("- Last confirmed intent: (none)")

    if pending_intent:
        lines.append(f"- Pending intent awaiting confirmation: {_compact_text(pending_intent, 350)}")
    else:
        lines.append("- Pending intent awaiting confirmation: (none)")

    if isinstance(session_summary, dict) and session_summary:
        try:
            summary_json = json.dumps(session_summary, ensure_ascii=False)
        except Exception:
            summary_json = str(session_summary)
        lines.append(f"- Session summary: {_compact_text(summary_json, 700)}")
    elif isinstance(session_summary, str) and _clean_text(session_summary):
        lines.append(f"- Session summary: {_compact_text(session_summary, 700)}")
    else:
        lines.append("- Session summary: (none)")

    return "\n".join(lines)


def _format_retrieved_rules(rules: list[str]) -> str:
    """Format retrieved business rule strings for the prompt."""
    if not rules:
        return "(No relevant business rules retrieved.)"
    return "\n\n".join(f"{i + 1}. {r.strip()}" for i, r in enumerate(rules) if r and r.strip())


def _build_intent_user_message(
    user_question: str,
    retrieved_business_rules: list[str],
    conversation_context: str,
) -> str:
    """Build the full prompt with user question and retrieved business rules."""
    rules_text = _format_retrieved_rules(retrieved_business_rules)
    return INTENT_PROMPT_TEMPLATE.format(
        user_question=user_question.strip(),
        conversation_context=(conversation_context or "(none)").strip(),
        retrieved_business_rules=rules_text,
    )


def _parse_intent_response(response_text: str) -> dict | None:
    """
    Parse LLM response into intent dict: rephrased_question, resolved_question,
    confidence_score, clarification_question, keywords, business_insights.
    Tolerates markdown code fences. Returns None on parse failure.
    """
    text = response_text.strip()
    if "```json" in text:
        text = re.sub(r"^.*?```json\s*", "", text, flags=re.DOTALL)
    if "```" in text:
        text = re.sub(r"\s*```.*$", "", text, flags=re.DOTALL)
    text = text.strip()
    try:
        data = json.loads(text)
        rephrased = (data.get("rephrased_question") or "").strip()
        resolved = (data.get("resolved_question") or "").strip()
        confidence_score = normalize_confidence_score(data.get("confidence_score"))
        clarification_question = (data.get("clarification_question") or "").strip()
        kw = data.get("keywords")
        keywords = [str(x).strip() for x in kw] if isinstance(kw, list) else []
        keywords = [x for x in keywords if x]
        bi = data.get("business_insights")
        business_insights = [str(x).strip() for x in bi] if isinstance(bi, list) else []
        business_insights = [x for x in business_insights if x]
        return {
            "rephrased_question": rephrased,
            "resolved_question": resolved,
            "confidence_score": confidence_score,
            "clarification_question": clarification_question,
            "keywords": keywords,
            "business_insights": business_insights,
        }
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Failed to parse intent LLM response as JSON: %s", e)
        return None


def _get_intent_via_llm(
    user_question: str,
    retrieved_business_rules: list[str],
    conversation_context: str,
) -> dict | None:
    """Call LLM with intent prompt (question + rules); return parsed intent dict or None."""
    from backend.services.llm_client import chat_completion

    user_content = _build_intent_user_message(
        user_question,
        retrieved_business_rules,
        conversation_context,
    )
    messages = [
        {"role": "user", "content": user_content},
    ]
    response = chat_completion(messages)
    return _parse_intent_response(response)


def run_intent(
    user_message: str,
    use_case: str,
    *,
    recent_messages: list[dict[str, Any]] | None = None,
    last_confirmed_intent: str | None = None,
    pending_intent: str | None = None,
    session_summary: dict[str, Any] | str | None = None,
) -> dict:
    """
    Run Intent Agent: retrieve business rules, then LLM interprets intent (rephrase, keywords, business_insights).
    Returns dict with keys: rephrased_question, resolved_question, confidence_score,
    clarification_question, keywords, business_insights.
    Falls back to retrieved rules as business_insights if LLM is unavailable or fails.
    """
    user_question = user_message.strip() or ""
    logger.info("Running Intent Agent (use_case=%s)", use_case)

    # 1. Retrieve business rules first (used as input to the LLM)
    retrieved_rules = retrieve_business_insights(use_case, user_question, top_k=10)
    logger.info("Retrieved %d business rules, calling LLM.", len(retrieved_rules))
    context_block = _build_conversation_context_block(
        user_question,
        recent_messages=recent_messages,
        last_confirmed_intent=last_confirmed_intent,
        pending_intent=pending_intent,
        session_summary=session_summary,
    )

    # 2. Call LLM with user question + retrieved rules
    intent = None
    try:
        intent = _get_intent_via_llm(user_question, retrieved_rules, context_block)
    except ValueError as e:
        logger.info("LLM not available (%s), using fallback for intent.", e)
    except Exception as e:
        logger.warning("Intent LLM call failed (%s), using fallback.", e)

    # 3. Use LLM output or fallback
    if intent:
        return {
            "rephrased_question": intent.get("rephrased_question") or user_question,
            "resolved_question": intent.get("resolved_question") or intent.get("rephrased_question") or user_question,
            "confidence_score": normalize_confidence_score(intent.get("confidence_score")),
            "clarification_question": intent.get("clarification_question") or "",
            "keywords": intent.get("keywords") or [],
            "business_insights": intent.get("business_insights") or retrieved_rules,
        }
    return {
        "rephrased_question": user_question,
        "resolved_question": user_question,
        "confidence_score": 50,
        "clarification_question": "",
        "keywords": [],
        "business_insights": retrieved_rules,
    }
