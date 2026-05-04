"""Tests for Intent Agent context-window policy and parsing."""

from backend.agents.intent_agent import (
    _build_conversation_context_block,
    _parse_intent_response,
    normalize_confidence_score,
)


def test_context_block_includes_full_history_when_up_to_three_messages():
    block = _build_conversation_context_block(
        "also include by region",
        recent_messages=[
            {"role": "user", "content": "show top customers"},
            {"role": "assistant", "content": "Do you mean by spend?"},
            {"role": "user", "content": "yes by spend"},
        ],
        last_confirmed_intent="Top customers by spend",
        pending_intent=None,
        session_summary=None,
    )
    assert "Previous messages (full)" in block
    assert "Older messages summary" not in block
    assert "Last confirmed intent: Top customers by spend" in block


def test_context_block_summarizes_when_more_than_three_messages():
    block = _build_conversation_context_block(
        "for last quarter",
        recent_messages=[
            {"role": "user", "content": "show sales by month"},
            {"role": "assistant", "content": "Which domain?"},
            {"role": "user", "content": "retail"},
            {"role": "assistant", "content": "Do you want total sales?"},
            {"role": "user", "content": "yes"},
        ],
        last_confirmed_intent="Monthly retail sales",
        pending_intent="Monthly retail sales with confirmation pending",
        session_summary={"session_goal": "trend analysis"},
    )
    assert "Older messages summary" in block
    assert "Previous messages (recent full turns)" in block
    assert "Pending intent awaiting confirmation" in block
    assert "Session summary:" in block


def test_parse_intent_response_reads_confidence_and_resolved_question():
    payload = """
    {
      "rephrased_question": "Top spenders by branch",
      "resolved_question": "Show top spenders by branch for last month",
      "confidence_score": 72,
      "clarification_question": "Did you mean top spenders by branch for last month?",
      "keywords": ["ranking", "spend", "branch"],
      "business_insights": ["High activity entities"]
    }
    """
    parsed = _parse_intent_response(payload)
    assert parsed is not None
    assert parsed["resolved_question"] == "Show top spenders by branch for last month"
    assert parsed["confidence_score"] == 72
    assert parsed["clarification_question"].startswith("Did you mean")


def test_normalize_confidence_score_fractional():
    assert normalize_confidence_score(0.85) == 85
    assert normalize_confidence_score(1) == 100
    assert normalize_confidence_score(1.0) == 100
    assert normalize_confidence_score(0.72) == 72
    assert normalize_confidence_score("0.9") == 90


def test_normalize_confidence_score_already_percent():
    assert normalize_confidence_score(72) == 72
    assert normalize_confidence_score(100) == 100


def test_normalize_confidence_score_none_or_invalid_defaults_conservative():
    assert normalize_confidence_score(None) == 50
    assert normalize_confidence_score("not-a-number") == 50


def test_parse_intent_response_confidence_as_fraction():
    payload = """{"rephrased_question": "x", "resolved_question": "x", "confidence_score": 0.79,
    "clarification_question": "", "keywords": [], "business_insights": []}"""
    parsed = _parse_intent_response(payload)
    assert parsed is not None
    assert parsed["confidence_score"] == 79
