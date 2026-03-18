"""
Database helpers for Stage 1 API: sessions and intent_agent_output.
"""

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
) -> None:
    """Insert one row into app_schema.intent_agent_output."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.intent_agent_output
                (session_id, use_case, user_input, rephrased_question, keywords, business_insights)
                VALUES (:session_id, :use_case, :user_input, :rephrased_question, :keywords, :business_insights)
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
        conn.commit()
