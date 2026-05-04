"""
Database helpers for Stage 1 API: sessions, intent_agent_output, few_shot_agent_output,
table_agent_output, column_agent_output, gen_sql_agent_output.
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


def insert_chat_message(session_id: str, role: str, content: str, message_type: str = "message") -> int:
    """Insert one chat message row; return new id."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.chat_messages (session_id, role, message_type, content)
                VALUES (:session_id, :role, :message_type, :content)
                RETURNING id
            """),
            {
                "session_id": uuid.UUID(session_id),
                "role": (role or "user").strip().lower(),
                "message_type": (message_type or "message").strip().lower(),
                "content": content or "",
            },
        )
        row = result.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("INSERT chat_messages did not return id")
    return int(row[0])


def get_recent_chat_messages(session_id: str, limit: int = 6) -> list[dict]:
    """Fetch latest chat messages for a session (oldest-first in returned list)."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT role, content, message_type, created_at
                FROM {APP_SCHEMA}.chat_messages
                WHERE session_id = :session_id
                ORDER BY id DESC
                LIMIT :limit
            """),
            {"session_id": uuid.UUID(session_id), "limit": max(1, int(limit))},
        ).fetchall()
    out = []
    for r in reversed(rows):
        out.append(
            {
                "role": (r.role or "").strip().lower(),
                "content": r.content or "",
                "message_type": (r.message_type or "").strip().lower(),
                "created_at": str(r.created_at) if r.created_at else None,
            }
        )
    return out


def upsert_session_memory(session_id: str, summary_json: dict, last_summarized_message_id: int | None = None) -> None:
    """Create or update session_memory summary for a session."""
    engine = get_engine()
    payload = json.dumps(summary_json or {})
    with engine.connect() as conn:
        conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.session_memory (session_id, summary_json, last_summarized_message_id)
                VALUES (:session_id, CAST(:summary_json AS jsonb), :last_summarized_message_id)
                ON CONFLICT (session_id)
                DO UPDATE SET
                    summary_json = EXCLUDED.summary_json,
                    last_summarized_message_id = EXCLUDED.last_summarized_message_id,
                    updated_at = CURRENT_TIMESTAMP
            """),
            {
                "session_id": uuid.UUID(session_id),
                "summary_json": payload,
                "last_summarized_message_id": last_summarized_message_id,
            },
        )
        conn.commit()


def get_session_memory(session_id: str) -> dict:
    """Fetch session summary JSON for a session; returns {} if missing."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(f"""
                SELECT summary_json
                FROM {APP_SCHEMA}.session_memory
                WHERE session_id = :session_id
            """),
            {"session_id": uuid.UUID(session_id)},
        ).fetchone()
    if not row:
        return {}
    return dict(row.summary_json or {})


def merge_session_memory(session_id: str, updates: dict) -> None:
    """Merge updates into existing session_memory.summary_json (shallow merge). None values remove keys."""
    if not session_exists(session_id):
        return
    cur = get_session_memory(session_id)
    if not isinstance(cur, dict):
        cur = {}
    merged = dict(cur)
    for k, v in (updates or {}).items():
        if v is None:
            merged.pop(k, None)
        else:
            merged[k] = v
    upsert_session_memory(session_id, merged)


def insert_intent_review(
    intent_output_id: int,
    confidence_score: int,
    confirmation_required: bool,
    confirmation_status: str = "pending",
) -> int:
    """Insert/replace one intent_review row linked to an intent_output_id."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.intent_review
                (intent_output_id, confidence_score, confirmation_required, confirmation_status)
                VALUES (:intent_output_id, :confidence_score, :confirmation_required, :confirmation_status)
                ON CONFLICT (intent_output_id)
                DO UPDATE SET
                    confidence_score = EXCLUDED.confidence_score,
                    confirmation_required = EXCLUDED.confirmation_required,
                    confirmation_status = EXCLUDED.confirmation_status
                RETURNING id
            """),
            {
                "intent_output_id": intent_output_id,
                "confidence_score": max(0, min(100, int(confidence_score))),
                "confirmation_required": bool(confirmation_required),
                "confirmation_status": (confirmation_status or "pending").strip().lower(),
            },
        )
        row = result.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("UPSERT intent_review did not return id")
    return int(row[0])


def update_intent_review_status(intent_output_id: int, confirmation_status: str) -> None:
    """Update intent_review status and reviewed_at for one intent_output_id."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text(f"""
                UPDATE {APP_SCHEMA}.intent_review
                SET confirmation_status = :confirmation_status,
                    reviewed_at = CURRENT_TIMESTAMP
                WHERE intent_output_id = :intent_output_id
            """),
            {
                "intent_output_id": intent_output_id,
                "confirmation_status": (confirmation_status or "pending").strip().lower(),
            },
        )
        conn.commit()


def get_latest_pending_intent(session_id: str) -> dict | None:
    """Return latest pending intent for a session, or None if none exists."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(f"""
                SELECT i.id AS intent_output_id,
                       i.rephrased_question,
                       i.user_input,
                       i.keywords,
                       i.business_insights,
                       r.confidence_score
                FROM {APP_SCHEMA}.intent_agent_output i
                JOIN {APP_SCHEMA}.intent_review r
                  ON r.intent_output_id = i.id
                WHERE i.session_id = :session_id
                  AND r.confirmation_required = TRUE
                  AND r.confirmation_status = 'pending'
                ORDER BY i.id DESC
                LIMIT 1
            """),
            {"session_id": uuid.UUID(session_id)},
        ).fetchone()
    if not row:
        return None
    return {
        "intent_output_id": int(row.intent_output_id),
        "rephrased_question": row.rephrased_question or "",
        "user_input": row.user_input or "",
        "keywords": list(row.keywords or []),
        "business_insights": list(row.business_insights or []),
        "confidence_score": int(row.confidence_score or 0),
    }


def get_latest_rejected_intent_rephrase(session_id: str) -> str | None:
    """Latest rejected intent's rephrased_question for corrections, or None."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(f"""
                SELECT i.rephrased_question
                FROM {APP_SCHEMA}.intent_agent_output i
                JOIN {APP_SCHEMA}.intent_review r ON r.intent_output_id = i.id
                WHERE i.session_id = :session_id
                  AND r.confirmation_status = 'rejected'
                ORDER BY i.id DESC
                LIMIT 1
            """),
            {"session_id": uuid.UUID(session_id)},
        ).fetchone()
    if not row:
        return None
    rq = (row.rephrased_question or "").strip()
    return rq or None


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


def insert_few_shot_agent_output(intent_output_id: int, few_shot_examples: list[dict]) -> int:
    """
    Insert one row into app_schema.few_shot_agent_output; return new row id.
    few_shot_examples: list of dicts (id, question_text, sql_query, query_type), stored as JSONB.
    """
    engine = get_engine()
    payload = json.dumps(few_shot_examples or [])
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.few_shot_agent_output (intent_output_id, few_shot_examples)
                VALUES (:intent_output_id, CAST(:few_shot_examples AS jsonb))
                RETURNING id
            """),
            {
                "intent_output_id": intent_output_id,
                "few_shot_examples": payload,
            },
        )
        row = result.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("INSERT few_shot_agent_output did not return id")
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


def insert_gen_sql_agent_output(
    intent_output_id: int,
    generated_sql: str,
    reasoning_summary: str | None,
    validation_passed: bool,
    validation_error_codes: str,
    validation_error_message: str,
    blocked_keywords: str,
    is_single_statement: bool,
    is_select_only: bool,
) -> int:
    """
    Insert one row into app_schema.gen_sql_agent_output; return new row id.
    Validation fields are stored in separate columns (no JSON blob).
    """
    engine = get_engine()
    rs = (reasoning_summary or "").strip() or None
    with engine.connect() as conn:
        result = conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.gen_sql_agent_output (
                    intent_output_id,
                    generated_sql,
                    reasoning_summary,
                    validation_passed,
                    validation_error_codes,
                    validation_error_message,
                    blocked_keywords,
                    is_single_statement,
                    is_select_only
                )
                VALUES (
                    :intent_output_id,
                    :generated_sql,
                    :reasoning_summary,
                    :validation_passed,
                    :validation_error_codes,
                    :validation_error_message,
                    :blocked_keywords,
                    :is_single_statement,
                    :is_select_only
                )
                RETURNING id
            """),
            {
                "intent_output_id": intent_output_id,
                "generated_sql": generated_sql or "",
                "reasoning_summary": rs,
                "validation_passed": validation_passed,
                "validation_error_codes": validation_error_codes or "",
                "validation_error_message": validation_error_message or "",
                "blocked_keywords": blocked_keywords or "",
                "is_single_statement": is_single_statement,
                "is_select_only": is_select_only,
            },
        )
        row = result.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("INSERT gen_sql_agent_output did not return id")
    return int(row[0])
