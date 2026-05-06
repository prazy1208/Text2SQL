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
        stack.enter_context(patch("backend.api.routes.query.insert_chat_message", return_value=1))
        stack.enter_context(patch("backend.api.routes.query.get_recent_chat_messages", return_value=[]))
        stack.enter_context(patch("backend.api.routes.query.get_session_memory", return_value={}))
        stack.enter_context(patch("backend.api.routes.query.insert_intent_review", return_value=1))
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
                    "resolved_question": "Total sales last month",
                    "confidence_score": 96,
                    "clarification_question": "",
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
    assert body["clarification_question"] == ""
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
        stack.enter_context(patch("backend.api.routes.query.insert_chat_message", return_value=1))
        stack.enter_context(patch("backend.api.routes.query.get_recent_chat_messages", return_value=[]))
        stack.enter_context(patch("backend.api.routes.query.get_session_memory", return_value={}))
        stack.enter_context(patch("backend.api.routes.query.insert_intent_review", return_value=1))
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
                return_value={
                    "rephrased_question": "Show totals across categories for the retail domain",
                    "resolved_question": "Show totals across categories for the retail domain",
                    "confidence_score": 96,
                    "clarification_question": "",
                    "keywords": ["totals", "categories"],
                    "business_insights": [],
                },
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
            json={"message": "show totals by category", "use_case": "retail", "session_id": sid},
        )

    assert res.status_code == 200
    body = res.json()
    assert "SQL validation" in (body.get("error") or "")
    assert body["generated_sql"]  # still returned for inspection
    assert body["clarification_question"] == ""


def test_post_query_low_confidence_returns_confirmation_prompt(client):
    sid = str(uuid.uuid4())
    with ExitStack() as stack:
        stack.enter_context(patch("backend.api.routes.query.session_exists", return_value=True))
        insert_chat = stack.enter_context(patch("backend.api.routes.query.insert_chat_message", return_value=1))
        stack.enter_context(patch("backend.api.routes.query.get_recent_chat_messages", return_value=[]))
        stack.enter_context(patch("backend.api.routes.query.get_session_memory", return_value={}))
        stack.enter_context(patch("backend.api.routes.query.list_relationships_from_metadata", return_value=[]))
        stack.enter_context(patch("backend.api.routes.query.insert_intent_output", return_value=11))
        insert_review = stack.enter_context(patch("backend.api.routes.query.insert_intent_review", return_value=22))
        run_table = stack.enter_context(patch("backend.api.routes.query.run_table_agent", return_value={"selected_tables": ["a.b"]}))
        stack.enter_context(
            patch(
                "backend.api.routes.query.run_intent",
                return_value={
                    "rephrased_question": "Find branch-wise high spenders for last month",
                    "resolved_question": "Find branch-wise high spenders for last month",
                    "confidence_score": 62,
                    "clarification_question": "Did you mean: find branch-wise high spenders for last month?",
                    "keywords": ["ranking", "spend", "branch"],
                    "business_insights": ["High activity entities"],
                },
            )
        )

        res = client.post(
            "/query",
            json={"message": "high spenders by branch last month", "use_case": "finance", "session_id": sid},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["needs_confirmation"] is True
    assert body["conversation_state"] == "waiting_intent_confirmation"
    assert body["intent_confidence"] == 62
    assert body["generated_sql"] == ""
    assert body["pending_intent_id"] == 11
    run_table.assert_not_called()
    insert_review.assert_called_once()
    # user turn + assistant confirmation prompt
    assert insert_chat.call_count >= 2


def test_post_query_intent_confirmation_yes_continues_pipeline(client):
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
        stack.enter_context(patch("backend.api.routes.query.insert_chat_message", return_value=1))
        stack.enter_context(patch("backend.api.routes.query.get_session_memory", return_value={}))
        stack.enter_context(
            patch(
                "backend.api.routes.query.get_latest_pending_intent",
                return_value={
                    "intent_output_id": 44,
                    "rephrased_question": "Top customers by spend last month",
                    "user_input": "top spenders",
                    "keywords": ["ranking", "spend"],
                    "business_insights": ["High activity entities"],
                    "confidence_score": 65,
                },
            )
        )
        update_review = stack.enter_context(
            patch("backend.api.routes.query.update_intent_review_status", return_value=None)
        )
        stack.enter_context(patch("backend.api.routes.query.list_relationships_from_metadata", return_value=[]))
        stack.enter_context(patch("backend.api.routes.query.insert_table_agent_output", return_value=9))
        stack.enter_context(patch("backend.api.routes.query.insert_column_agent_output", return_value=19))
        stack.enter_context(patch("backend.api.routes.query.insert_few_shot_agent_output", return_value=29))
        stack.enter_context(patch("backend.api.routes.query.insert_gen_sql_agent_output", return_value=39))
        run_table = stack.enter_context(
            patch("backend.api.routes.query.run_table_agent", return_value={"selected_tables": ["finance_schema.transactions"]})
        )
        stack.enter_context(
            patch(
                "backend.api.routes.query.run_column_agent",
                return_value={"selected_columns": {"finance_schema.transactions": ["transaction_id", "amount"]}},
            )
        )
        stack.enter_context(patch("backend.api.routes.query.run_few_shot_agent", return_value={"few_shot_examples": []}))
        stack.enter_context(
            patch(
                "backend.api.routes.query.run_gen_sql",
                return_value={
                    "generated_sql": "SELECT customer_id, sum(amount) FROM finance_schema.transactions GROUP BY customer_id",
                    "reasoning_summary": "aggregation",
                },
            )
        )
        stack.enter_context(patch("backend.api.routes.query.validate_generated_sql", return_value=validation_ok))

        res = client.post(
            "/query",
            json={
                "message": "yes",
                "use_case": "finance",
                "session_id": sid,
                "message_type": "intent_confirmation",
                "confirmation": "yes",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["conversation_state"] == "completed"
    assert body["needs_confirmation"] is False
    assert body["generated_sql"]
    update_review.assert_called_once_with(44, "confirmed")
    run_table.assert_called_once()


def test_post_query_intent_confirmation_no_waits_for_rephrase(client):
    sid = str(uuid.uuid4())
    with ExitStack() as stack:
        stack.enter_context(patch("backend.api.routes.query.session_exists", return_value=True))
        stack.enter_context(patch("backend.api.routes.query.insert_chat_message", return_value=1))
        stack.enter_context(patch("backend.api.routes.query.get_session_memory", return_value={}))
        stack.enter_context(
            patch(
                "backend.api.routes.query.get_latest_pending_intent",
                return_value={
                    "intent_output_id": 51,
                    "rephrased_question": "Branch-wise top spenders for last month",
                    "user_input": "top spenders",
                    "keywords": ["ranking", "branch"],
                    "business_insights": ["High activity entities"],
                    "confidence_score": 61,
                },
            )
        )
        update_review = stack.enter_context(
            patch("backend.api.routes.query.update_intent_review_status", return_value=None)
        )
        run_table = stack.enter_context(
            patch("backend.api.routes.query.run_table_agent", return_value={"selected_tables": ["x.y"]})
        )

        res = client.post(
            "/query",
            json={
                "message": "no",
                "use_case": "finance",
                "session_id": sid,
                "message_type": "intent_confirmation",
                "confirmation": "no",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["conversation_state"] == "waiting_user_rephrase"
    assert body["needs_confirmation"] is False
    assert body["generated_sql"] == ""
    assert body["pending_intent_id"] == 51
    update_review.assert_called_once_with(51, "rejected")
    run_table.assert_not_called()


def test_post_query_trivial_greeting_skips_confirmation_and_waits_for_query(client):
    """Pure greetings get a short reply and waiting_analytical_query — no Yes/No on meta-intent."""
    sid = str(uuid.uuid4())
    with ExitStack() as stack:
        stack.enter_context(patch("backend.api.routes.query.session_exists", return_value=True))
        stack.enter_context(patch("backend.api.routes.query.insert_chat_message", return_value=1))
        stack.enter_context(patch("backend.api.routes.query.get_recent_chat_messages", return_value=[]))
        stack.enter_context(patch("backend.api.routes.query.get_session_memory", return_value={}))
        stack.enter_context(patch("backend.api.routes.query.list_relationships_from_metadata", return_value=[]))
        stack.enter_context(patch("backend.api.routes.query.insert_intent_output", return_value=3))
        stack.enter_context(patch("backend.api.routes.query.insert_intent_review", return_value=4))
        run_intent = stack.enter_context(patch("backend.api.routes.query.run_intent"))
        run_table = stack.enter_context(patch("backend.api.routes.query.run_table_agent", return_value={"selected_tables": ["a.b"]}))

        res = client.post(
            "/query",
            json={"message": "hi", "use_case": "retail", "session_id": sid},
        )

    assert res.status_code == 200
    body = res.json()
    assert body["conversation_state"] == "waiting_analytical_query"
    assert body["needs_confirmation"] is False
    assert body["pending_intent_id"] is None
    assert "analyze" in (body.get("clarification_question") or "").lower()
    run_intent.assert_not_called()
    run_table.assert_not_called()


def test_post_query_open_invite_yes_returns_waiting_analytical_query(client):
    sid = str(uuid.uuid4())
    with ExitStack() as stack:
        stack.enter_context(patch("backend.api.routes.query.session_exists", return_value=True))
        stack.enter_context(patch("backend.api.routes.query.insert_chat_message", return_value=1))
        stack.enter_context(
            patch(
                "backend.api.routes.query.get_latest_pending_intent",
                return_value={
                    "intent_output_id": 70,
                    "rephrased_question": "User may want to explore analytics",
                    "user_input": "hello",
                    "keywords": ["explore"],
                    "business_insights": [],
                    "confidence_score": 55,
                },
            )
        )
        stack.enter_context(
            patch(
                "backend.api.routes.query.get_session_memory",
                return_value={"pending_confirm_kind": "open_invite", "pending_intent_output_id": 70},
            )
        )
        update_review = stack.enter_context(
            patch("backend.api.routes.query.update_intent_review_status", return_value=None)
        )
        run_table = stack.enter_context(patch("backend.api.routes.query.run_table_agent", return_value={"selected_tables": ["x.y"]}))

        res = client.post(
            "/query",
            json={
                "message": "yes",
                "use_case": "finance",
                "session_id": sid,
                "message_type": "intent_confirmation",
                "confirmation": "yes",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["conversation_state"] == "waiting_analytical_query"
    assert body["pending_intent_id"] is None
    assert body["generated_sql"] == ""
    update_review.assert_called_once_with(70, "rejected")
    run_table.assert_not_called()


def test_post_query_open_invite_no_returns_conversation_ended(client):
    sid = str(uuid.uuid4())
    with ExitStack() as stack:
        stack.enter_context(patch("backend.api.routes.query.session_exists", return_value=True))
        stack.enter_context(patch("backend.api.routes.query.insert_chat_message", return_value=1))
        stack.enter_context(
            patch(
                "backend.api.routes.query.get_latest_pending_intent",
                return_value={
                    "intent_output_id": 71,
                    "rephrased_question": "User may want to explore analytics",
                    "user_input": "hello",
                    "keywords": ["explore"],
                    "business_insights": [],
                    "confidence_score": 55,
                },
            )
        )
        stack.enter_context(
            patch(
                "backend.api.routes.query.get_session_memory",
                return_value={"pending_confirm_kind": "open_invite", "pending_intent_output_id": 71},
            )
        )
        update_review = stack.enter_context(
            patch("backend.api.routes.query.update_intent_review_status", return_value=None)
        )
        run_table = stack.enter_context(patch("backend.api.routes.query.run_table_agent", return_value={"selected_tables": ["x.y"]}))

        res = client.post(
            "/query",
            json={
                "message": "no",
                "use_case": "finance",
                "session_id": sid,
                "message_type": "intent_confirmation",
                "confirmation": "no",
            },
        )

    assert res.status_code == 200
    body = res.json()
    assert body["conversation_state"] == "conversation_ended"
    assert body["clarification_question"] == "Ok, thank you!"
    assert body["pending_intent_id"] is None
    update_review.assert_called_once_with(71, "rejected")
    run_table.assert_not_called()
