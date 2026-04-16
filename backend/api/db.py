"""
Database helpers for Stage 1 API: sessions, intent_agent_output, table_agent_output,
column_agent_output.
"""

import json
import uuid

from sqlalchemy import text

from backend.config import APP_SCHEMA, get_engine


def create_session() -> str:
    """Insert a new session and return its session_id (UUID string)."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(f"INSERT INTO {APP_SCHEMA}.sessions DEFAULT VALUES RETURNING session_id")
        ).fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("Failed to create session")
    return str(row[0])


def session_exists(session_id: str) -> bool:
    """Return True if the given session_id exists in app_schema.sessions."""
    try:
        uid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        return False
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT 1 FROM {APP_SCHEMA}.sessions WHERE session_id = :sid"),
            {"sid": uid},
        ).fetchone()
    return row is not None


def insert_intent_output(
    session_id: str,
    use_case: str,
    user_input: str,
    rephrased_question: str,
    keywords: list[str],
    business_insights: list[str],
) -> int:
    """Insert one row into app_schema.intent_agent_output; return new row id."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.intent_agent_output
                (session_id, use_case, user_input, rephrased_question, keywords, business_insights)
                VALUES (:session_id, :use_case, :user_input, :rephrased_question, :keywords, :business_insights)
                RETURNING id
            """),
            {
                "session_id": uuid.UUID(session_id),
                "use_case": use_case,
                "user_input": user_input,
                "rephrased_question": rephrased_question or None,
                "keywords": keywords or [],
                "business_insights": business_insights or [],
            },
        )
        row = result.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("INSERT intent_agent_output did not return id")
    return int(row[0])


def insert_table_agent_output(intent_output_id: int, selected_tables: list[str]) -> int:
    """Insert one row into app_schema.table_agent_output; return new row id."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.table_agent_output (intent_output_id, selected_tables)
                VALUES (:intent_output_id, :selected_tables)
                RETURNING id
            """),
            {
                "intent_output_id": intent_output_id,
                "selected_tables": selected_tables or [],
            },
        )
        row = result.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("INSERT table_agent_output did not return id")
    return int(row[0])


def insert_column_agent_output(table_agent_output_id: int, selected_columns: dict) -> int:
    """
    Insert one row into app_schema.column_agent_output; return new row id.
    selected_columns: map table FQN -> list of column names, stored as JSONB.
    """
    engine = get_engine()
    payload = json.dumps(selected_columns or {})
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.column_agent_output (table_agent_output_id, selected_columns)
                VALUES (:table_agent_output_id, CAST(:selected_columns AS jsonb))
                RETURNING id
            """),
            {
                "table_agent_output_id": table_agent_output_id,
                "selected_columns": payload,
            },
        )
        row = result.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("INSERT column_agent_output did not return id")
    return int(row[0])
