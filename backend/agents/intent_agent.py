"""
Intent Agent (Stage 1).
Inputs: user_message, use_case.
Outputs: rephrased_question, keywords, business_insights.
Steps: (1) Retrieve business rules via FAISS. (2) LLM interprets intent with rules in context; returns structured JSON.
"""

import json
import logging
import re

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

User Question:
{user_question}

Relevant Business Rules:
{retrieved_business_rules}

The business rules are domain knowledge retrieved using semantic similarity search.
They describe analytical concepts and insights relevant to the user's question.

--------------------------------------------------
YOUR TASK
--------------------------------------------------

1. Carefully read the user's question.

2. Identify the analytical objective behind the question.

3. Use the provided business rules only to better understand the business meaning of the request.

4. Rephrase the user question into a clear analytical instruction that precisely describes the user's goal.

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

--------------------------------------------------
OUTPUT FORMAT
--------------------------------------------------

Return ONLY valid JSON using the following structure:

{{
  "rephrased_question": "Clear analytical version of the user's question",
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

Include analytical intent (e.g. aggregation, comparison, ranking, trend) in the keywords list where relevant."""


def _format_retrieved_rules(rules: list[str]) -> str:
    """Format retrieved business rule strings for the prompt."""
    if not rules:
        return "(No relevant business rules retrieved.)"
    return "\n\n".join(f"{i + 1}. {r.strip()}" for i, r in enumerate(rules) if r and r.strip())


def _build_intent_user_message(user_question: str, retrieved_business_rules: list[str]) -> str:
    """Build the full prompt with user question and retrieved business rules."""
    rules_text = _format_retrieved_rules(retrieved_business_rules)
    return INTENT_PROMPT_TEMPLATE.format(
        user_question=user_question.strip(),
        retrieved_business_rules=rules_text,
    )


def _parse_intent_response(response_text: str) -> dict | None:
    """
    Parse LLM response into intent dict: rephrased_question, keywords, business_insights.
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
        kw = data.get("keywords")
        keywords = [str(x).strip() for x in kw] if isinstance(kw, list) else []
        keywords = [x for x in keywords if x]
        bi = data.get("business_insights")
        business_insights = [str(x).strip() for x in bi] if isinstance(bi, list) else []
        business_insights = [x for x in business_insights if x]
        return {
            "rephrased_question": rephrased,
            "keywords": keywords,
            "business_insights": business_insights,
        }
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("Failed to parse intent LLM response as JSON: %s", e)
        return None


def _get_intent_via_llm(user_question: str, retrieved_business_rules: list[str]) -> dict | None:
    """Call LLM with intent prompt (question + rules); return parsed intent dict or None."""
    from backend.services.llm_client import chat_completion

    user_content = _build_intent_user_message(user_question, retrieved_business_rules)
    messages = [
        {"role": "user", "content": user_content},
    ]
    response = chat_completion(messages)
    return _parse_intent_response(response)


def run_intent(user_message: str, use_case: str) -> dict:
    """
    Run Intent Agent: retrieve business rules, then LLM interprets intent (rephrase, keywords, business_insights).
    Returns dict with keys: rephrased_question, keywords, business_insights.
    Falls back to retrieved rules as business_insights if LLM is unavailable or fails.
    """
    user_question = user_message.strip() or ""
    logger.info("Running Intent Agent (use_case=%s)", use_case)

    # 1. Retrieve business rules first (used as input to the LLM)
    retrieved_rules = retrieve_business_insights(use_case, user_question, top_k=10)
    logger.info("Retrieved %d business rules, calling LLM.", len(retrieved_rules))

    # 2. Call LLM with user question + retrieved rules
    intent = None
    try:
        intent = _get_intent_via_llm(user_question, retrieved_rules)
    except ValueError as e:
        logger.info("LLM not available (%s), using fallback for intent.", e)
    except Exception as e:
        logger.warning("Intent LLM call failed (%s), using fallback.", e)

    # 3. Use LLM output or fallback
    if intent:
        return {
            "rephrased_question": intent.get("rephrased_question") or user_question,
            "keywords": intent.get("keywords") or [],
            "business_insights": intent.get("business_insights") or retrieved_rules,
        }
    return {
        "rephrased_question": user_question,
        "keywords": [],
        "business_insights": retrieved_rules,
    }
