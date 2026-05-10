"""
Database helpers for Stage 1 API: sessions, intent_agent_output, few_shot_agent_output,
table_agent_output, column_agent_output, gen_sql_agent_output.
"""

import json
import uuid

from sqlalchemy import text

from backend.config import APP_SCHEMA, get_engine


def create_session(client_id: str | None = None, use_case: str | None = None) -> str:
    """Insert a new session and return its session_id (UUID string).

    Optional client_id scopes sessions for anonymous multi-chat listing (GET /sessions).
    use_case may be set at creation time or later via update_session_use_case.
    """
    engine = get_engine()
    cid = None
    if client_id:
        try:
            cid = uuid.UUID(str(client_id).strip())
        except (ValueError, TypeError):
            cid = None
    uc = (use_case or "").strip() or None
    if uc and len(uc) > 64:
        uc = uc[:64]

    with engine.connect() as conn:
        if cid is not None or uc is not None:
            row = conn.execute(
                text(f"""
                    INSERT INTO {APP_SCHEMA}.sessions (client_id, use_case)
                    VALUES (:client_id, :use_case)
                    RETURNING session_id
                """),
                {"client_id": cid, "use_case": uc},
            ).fetchone()
        else:
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


def set_session_title_if_unset(session_id: str, title: str) -> None:
    """Set sessions.title only when currently null or blank (immutable after first assign)."""
    t = (title or "").strip()
    if not t:
        return
    if len(t) > 200:
        t = t[:199] + "…"
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        return
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text(f"""
                UPDATE {APP_SCHEMA}.sessions
                SET title = :title, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = :sid
                  AND (title IS NULL OR trim(title) = '')
            """),
            {"sid": sid, "title": t},
        )
        conn.commit()


def update_session_use_case(session_id: str, use_case: str) -> None:
    """Persist last domain for the session (VARCHAR(64))."""
    uc = (use_case or "").strip()
    if not uc or len(uc) > 64:
        return
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        return
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(
            text(f"""
                UPDATE {APP_SCHEMA}.sessions
                SET use_case = :use_case, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = :sid
            """),
            {"sid": sid, "use_case": uc},
        )
        conn.commit()


def insert_chat_message(session_id: str, role: str, content: str, message_type: str = "message") -> int:
    """Insert one chat message row; return new id."""
    engine = get_engine()
    sid = uuid.UUID(session_id)
    with engine.begin() as conn:
        result = conn.execute(
            text(f"""
                INSERT INTO {APP_SCHEMA}.chat_messages (session_id, role, message_type, content)
                VALUES (:session_id, :role, :message_type, :content)
                RETURNING id
            """),
            {
                "session_id": sid,
                "role": (role or "user").strip().lower(),
                "message_type": (message_type or "message").strip().lower(),
                "content": content or "",
            },
        )
        row = result.fetchone()
        conn.execute(
            text(f"""
                UPDATE {APP_SCHEMA}.sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE session_id = :sid
            """),
            {"sid": sid},
        )
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


def list_sessions_for_client(client_id: str, limit: int = 100) -> list[dict]:
    """Return sessions for this browser client, newest activity first.

    Only ``client_id = :cid`` (strict). Rows with NULL ``client_id`` do **not** appear
    until you backfill them for this browser — see ``docs/BACKFILL_SESSIONS.md``.

    Only sessions with at least one ``chat_messages`` row are listed.
    """
    try:
        cid = uuid.UUID(str(client_id).strip())
    except (ValueError, TypeError):
        return []
    engine = get_engine()
    lim = max(1, min(500, int(limit)))
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT s.session_id, s.title, s.use_case, s.created_at, s.updated_at
                FROM {APP_SCHEMA}.sessions s
                WHERE s.client_id = :cid
                  AND EXISTS (
                      SELECT 1 FROM {APP_SCHEMA}.chat_messages m
                      WHERE m.session_id = s.session_id
                  )
                ORDER BY s.updated_at DESC
                LIMIT :lim
            """),
            {"cid": cid, "lim": lim},
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "session_id": str(r.session_id),
                "title": r.title if r.title is not None else None,
                "use_case": r.use_case if r.use_case is not None else None,
                "created_at": str(r.created_at) if r.created_at else None,
                "updated_at": str(r.updated_at) if r.updated_at else None,
            }
        )
    return out


def delete_session_if_owned(session_id: str, client_id: str) -> bool:
    """Delete a session row only when ``sessions.client_id`` equals ``client_id``.

    Returns True if a row was deleted. Unscoped sessions (``client_id`` NULL) are not
    deletable through this path. Cascades remove related app_schema rows.
    """
    try:
        sid = uuid.UUID(session_id)
        cid = uuid.UUID(str(client_id).strip())
    except (ValueError, TypeError):
        return False
    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            text(f"""
                DELETE FROM {APP_SCHEMA}.sessions
                WHERE session_id = :sid AND client_id = :cid
                RETURNING session_id
            """),
            {"sid": sid, "cid": cid},
        ).fetchone()
    return row is not None


def get_session_row(session_id: str) -> dict | None:
    """Return session_id, title, use_case, client_id, created_at, updated_at or None."""
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        return None
    engine = get_engine()
    with engine.connect() as conn:
        r = conn.execute(
            text(f"""
                SELECT session_id, title, use_case, client_id, created_at, updated_at
                FROM {APP_SCHEMA}.sessions
                WHERE session_id = :sid
            """),
            {"sid": sid},
        ).fetchone()
    if not r:
        return None
    return {
        "session_id": str(r.session_id),
        "title": r.title if r.title is not None else None,
        "use_case": r.use_case if r.use_case is not None else None,
        "client_id": str(r.client_id) if r.client_id is not None else None,
        "created_at": str(r.created_at) if r.created_at else None,
        "updated_at": str(r.updated_at) if r.updated_at else None,
    }


def get_session_pipeline_turns(session_id: str) -> list[dict]:
    """One row per intent_agent_output, joined to downstream agent tables (for UI replay)."""
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        return []
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT
                    i.id AS intent_output_id,
                    i.user_input,
                    i.rephrased_question,
                    i.keywords,
                    i.business_insights,
                    COALESCE(r.confidence_score, 0) AS intent_confidence,
                    COALESCE(t.selected_tables, CAST(ARRAY[] AS text[])) AS selected_tables,
                    COALESCE(c.selected_columns, CAST('{{}}' AS jsonb)) AS selected_columns,
                    COALESCE(f.few_shot_examples, CAST('[]' AS jsonb)) AS few_shot_examples,
                    COALESCE(g.generated_sql, '') AS generated_sql,
                    COALESCE(g.validation_passed, false) AS validation_passed,
                    COALESCE(g.validation_error_message, '') AS validation_error_message,
                    COALESCE(g.validation_error_codes, '') AS validation_error_codes
                FROM {APP_SCHEMA}.intent_agent_output i
                LEFT JOIN {APP_SCHEMA}.intent_review r ON r.intent_output_id = i.id
                LEFT JOIN {APP_SCHEMA}.table_agent_output t ON t.intent_output_id = i.id
                LEFT JOIN {APP_SCHEMA}.column_agent_output c ON c.table_agent_output_id = t.id
                LEFT JOIN {APP_SCHEMA}.few_shot_agent_output f ON f.intent_output_id = i.id
                LEFT JOIN {APP_SCHEMA}.gen_sql_agent_output g ON g.intent_output_id = i.id
                WHERE i.session_id = :sid
                ORDER BY i.id ASC
            """),
            {"sid": sid},
        ).fetchall()

    def _kw(row) -> list[str]:
        v = row.keywords
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x is not None]
        return []

    def _insights(row) -> list[str]:
        v = row.business_insights
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x is not None]
        return []

    def _tables(row) -> list[str]:
        v = row.selected_tables
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v if x is not None]
        return []

    def _cols(row) -> dict:
        v = row.selected_columns
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v) if v.strip() else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def _fewshot(row) -> list:
        v = row.few_shot_examples
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v) if v.strip() else []
            except json.JSONDecodeError:
                return []
        return []

    out: list[dict] = []
    for row in rows:
        vm = (row.validation_error_message or "").strip()
        vc = (row.validation_error_codes or "").strip()
        err = None
        if not bool(row.validation_passed) and (vm or vc):
            err = vm
            if vc:
                err = f"{err} ({vc})".strip() if err else vc

        rq = (row.rephrased_question or "").strip()
        out.append(
            {
                "intent_output_id": int(row.intent_output_id),
                "user_input": row.user_input or "",
                "rephrased_question": rq,
                "resolved_question": rq,
                "keywords": _kw(row),
                "business_insights": _insights(row),
                "intent_confidence": int(row.intent_confidence or 0),
                "selected_tables": _tables(row),
                "selected_columns": _cols(row),
                "few_shot_examples": _fewshot(row),
                "generated_sql": (row.generated_sql or "").strip(),
                "conversation_state": "completed",
                "error": err,
            }
        )
    return out


def get_all_chat_messages_ordered(session_id: str) -> list[dict]:
    """Full transcript for a session, oldest first (UI hydration)."""
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, TypeError):
        return []
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"""
                SELECT id, role, content, message_type, created_at
                FROM {APP_SCHEMA}.chat_messages
                WHERE session_id = :session_id
                ORDER BY id ASC
            """),
            {"session_id": sid},
        ).fetchall()
    return [
        {
            "id": int(r.id),
            "role": (r.role or "").strip().lower(),
            "content": r.content or "",
            "message_type": (r.message_type or "").strip().lower(),
            "created_at": str(r.created_at) if r.created_at else None,
        }
        for r in rows
    ]


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
