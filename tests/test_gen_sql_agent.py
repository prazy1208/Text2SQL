"""Unit tests for backend.agents.gen_sql_agent (LLM mocked)."""

from unittest.mock import patch

from backend.agents import gen_sql_agent


def test_run_gen_sql_empty_rephrased():
    out = gen_sql_agent.run_gen_sql(
        "retail",
        "",
        [],
        [],
        ["public.t"],
        {},
    )
    assert out["generated_sql"] == ""
    assert "Missing" in out["reasoning_summary"]


def test_run_gen_sql_no_tables():
    out = gen_sql_agent.run_gen_sql(
        "retail",
        "Show revenue",
        [],
        [],
        [],
        {},
    )
    assert out["generated_sql"] == ""
    assert "No tables" in out["reasoning_summary"]


def test_run_gen_sql_parses_llm_json():
    payload = '{"generated_sql": "SELECT 1", "reasoning_summary": "smoke"}'
    with patch.object(gen_sql_agent, "chat_completion", return_value=payload) as mock_chat:
        out = gen_sql_agent.run_gen_sql(
            "retail",
            "Count rows",
            ["rule"],
            [{"id": 1, "query_type": "agg", "question_text": "q", "sql_query": "SELECT 1"}],
            ["public.orders"],
            {"public.orders": ["id"]},
        )
    assert out["generated_sql"] == "SELECT 1"
    assert out["reasoning_summary"] == "smoke"
    mock_chat.assert_called_once()
    _args, kwargs = mock_chat.call_args
    assert kwargs.get("agent_name") == gen_sql_agent.AGENT_GEN_SQL


def test_run_gen_sql_invalid_json_from_model():
    with patch.object(gen_sql_agent, "chat_completion", return_value="not json"):
        out = gen_sql_agent.run_gen_sql(
            "retail",
            "Q",
            [],
            [],
            ["public.t"],
            {"public.t": ["id"]},
        )
    assert out["generated_sql"] == ""
    assert "Could not extract SQL" in out["reasoning_summary"]


def test_run_gen_sql_llm_raises():
    with patch.object(gen_sql_agent, "chat_completion", side_effect=RuntimeError("api down")):
        out = gen_sql_agent.run_gen_sql(
            "retail",
            "Q",
            [],
            [],
            ["public.t"],
            {"public.t": ["id"]},
        )
    assert out["generated_sql"] == ""
    assert "api down" in out["reasoning_summary"]
