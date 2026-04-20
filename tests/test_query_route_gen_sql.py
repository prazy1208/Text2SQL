"""Integration-style tests for POST /query Gen-SQL path (DB and LLM mocked)."""

import uuid
from contextlib import ExitStack
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_post_query_includes_generated_sql_and_persists_gen_sql_row(client):
    sid = str(uuid.uuid4())
    validation_ok = {
        "validation_passed": True,
        "validation_error_codes": "",
        "validation_error_message": "",
        "blocked_keywords": "",
        "is_single_statement": True,
        "is_select_only": True,
    }
    with ExitStack() as stack:
        stack.enter_context(patch("backend.api.routes.query.session_exists", return_value=True))
        stack.enter_context(
            patch("backend.api.routes.query.list_relationships_from_metadata", return_value=[])
        )
        stack.enter_context(patch("backend.api.routes.query.insert_intent_output", return_value=1))
        stack.enter_context(patch("backend.api.routes.query.insert_table_agent_output", return_value=10))
        stack.enter_context(patch("backend.api.routes.query.insert_column_agent_output", return_value=20))
        stack.enter_context(patch("backend.api.routes.query.insert_few_shot_agent_output", return_value=30))
        insert_gen = stack.enter_context(
            patch("backend.api.routes.query.insert_gen_sql_agent_output", return_value=100)
        )
        stack.enter_context(
            patch(
                "backend.api.routes.query.run_intent",
                return_value={
                    "rephrased_question": "Total sales last month",
                    "keywords": ["sales"],
                    "business_insights": ["Use net amounts"],
                },
            )
        )
        stack.enter_context(
            patch("backend.api.routes.query.run_table_agent", return_value={"selected_tables": ["public.orders"]})
        )
        stack.enter_context(
            patch(
                "backend.api.routes.query.run_column_agent",
                return_value={"selected_columns": {"public.orders": ["id", "amount"]}},
            )
        )
        stack.enter_context(patch("backend.api.routes.query.run_few_shot_agent", return_value={"few_shot_examples": []}))
        stack.enter_context(
            patch(
                "backend.api.routes.query.run_gen_sql",
                return_value={
                    "generated_sql": "SELECT sum(amount) FROM public.orders",
                    "reasoning_summary": "agg",
                },
            )
        )
        stack.enter_context(patch("backend.api.routes.query.validate_generated_sql", return_value=validation_ok))

        res = client.post(
            "/query",
            json={"message": "sales?", "use_case": "retail", "session_id": sid},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["generated_sql"] == "SELECT sum(amount) FROM public.orders"
    assert body["rephrased_question"] == "Total sales last month"
    insert_gen.assert_called_once()
    args, kwargs = insert_gen.call_args
    assert args[0] == 1  # intent_output_id
    assert args[1] == "SELECT sum(amount) FROM public.orders"
    assert args[2] == "agg"  # reasoning_summary
    assert args[3] is True  # validation_passed


def test_post_query_merges_validation_failure_into_error(client):
    sid = str(uuid.uuid4())
    validation_bad = {
        "validation_passed": False,
        "validation_error_codes": "FORBIDDEN_KEYWORD",
        "validation_error_message": "blocked",
        "blocked_keywords": "DELETE",
        "is_single_statement": True,
        "is_select_only": False,
    }
    with ExitStack() as stack:
        stack.enter_context(patch("backend.api.routes.query.session_exists", return_value=True))
        stack.enter_context(
            patch("backend.api.routes.query.list_relationships_from_metadata", return_value=[])
        )
        stack.enter_context(patch("backend.api.routes.query.insert_intent_output", return_value=1))
        stack.enter_context(patch("backend.api.routes.query.insert_table_agent_output", return_value=10))
        stack.enter_context(patch("backend.api.routes.query.insert_column_agent_output", return_value=20))
        stack.enter_context(patch("backend.api.routes.query.insert_few_shot_agent_output", return_value=30))
        stack.enter_context(patch("backend.api.routes.query.insert_gen_sql_agent_output", return_value=100))
        stack.enter_context(
            patch(
                "backend.api.routes.query.run_intent",
                return_value={"rephrased_question": "q", "keywords": [], "business_insights": []},
            )
        )
        stack.enter_context(patch("backend.api.routes.query.run_table_agent", return_value={"selected_tables": ["a.b"]}))
        stack.enter_context(patch("backend.api.routes.query.run_column_agent", return_value={"selected_columns": {"a.b": ["x"]}}))
        stack.enter_context(patch("backend.api.routes.query.run_few_shot_agent", return_value={"few_shot_examples": []}))
        stack.enter_context(
            patch(
                "backend.api.routes.query.run_gen_sql",
                return_value={"generated_sql": "SELECT 1; DELETE FROM a.b", "reasoning_summary": ""},
            )
        )
        stack.enter_context(patch("backend.api.routes.query.validate_generated_sql", return_value=validation_bad))

        res = client.post(
            "/query",
            json={"message": "x", "use_case": "retail", "session_id": sid},
        )

    assert res.status_code == 200
    body = res.json()
    assert "SQL validation" in (body.get("error") or "")
    assert body["generated_sql"]  # still returned for inspection
