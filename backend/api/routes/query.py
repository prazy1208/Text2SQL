"""Routes: POST /session, POST /query (full pipeline incl. Gen-SQL), GET /use-cases."""

import logging
import re
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from backend.agents.column_agent import run_column_agent
from backend.agents.few_shot_agent import run_few_shot_agent
from backend.agents.gen_sql_agent import run_gen_sql
from backend.agents.intent_agent import run_intent
from backend.agents.table_agent import run_table_agent
from backend.api.db import (
    create_session,
    delete_session_if_owned,
    get_all_chat_messages_ordered,
    get_latest_pending_intent,
    get_latest_rejected_intent_rephrase,
    get_recent_chat_messages,
    get_session_memory,
    get_session_pipeline_turns,
    get_session_row,
    insert_chat_message,
    insert_column_agent_output,
    insert_few_shot_agent_output,
    insert_gen_sql_agent_output,
    insert_intent_output,
    insert_intent_review,
    insert_table_agent_output,
    merge_session_memory,
    list_sessions_for_client,
    session_exists,
    set_session_title_if_unset,
    update_intent_review_status,
    update_session_use_case,
)
from backend.config import USE_CASE_TO_SCHEMA, USE_CASES
from backend.services.relationship_retrieval import (
    filter_relationships_for_selected_tables,
    list_relationships_from_metadata,
)
from backend.services.sql_validator import validate_generated_sql

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    message: str = Field(..., min_length=1)
    use_case: str = Field(...)
    session_id: str | None = Field(None)
    message_type: Literal["new_query", "intent_confirmation", "intent_correction"] = Field("new_query")
    confirmation: Literal["yes", "no"] | None = Field(None)
    client_id: str | None = Field(
        None,
        description="Optional UUID for anonymous chat lists; applied when a new session is created",
    )


class QueryResponse(BaseModel):
    session_id: str
    rephrased_question: str
    keywords: list[str]
    business_insights: list[str]
    few_shot_examples: list[dict] = Field(default_factory=list)
    selected_tables: list[str] = Field(default_factory=list)
    selected_columns: dict[str, list[str]] = Field(default_factory=dict)
    generated_sql: str = Field(default="", description="Synthesized SQL from Gen-SQL Agent")
    resolved_question: str = ""
    intent_confidence: int = 0
    needs_confirmation: bool = False
    clarification_question: str = ""
    conversation_state: str = "completed"
    pending_intent_id: int | None = None
    error: str | None = None


class SessionResponse(BaseModel):
    session_id: str


class SessionListItem(BaseModel):
    session_id: str
    title: str | None = None
    use_case: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ChatMessageItem(BaseModel):
    id: int
    role: str
    content: str
    message_type: str
    created_at: str | None = None


class PipelineTurnItem(BaseModel):
    """Structured pipeline snapshot for one intent_agent_output row (UI replay)."""

    model_config = {"extra": "ignore"}

    intent_output_id: int
    user_input: str
    rephrased_question: str = ""
    resolved_question: str = ""
    keywords: list[str] = Field(default_factory=list)
    business_insights: list[str] = Field(default_factory=list)
    intent_confidence: int = 0
    selected_tables: list[str] = Field(default_factory=list)
    selected_columns: dict[str, Any] = Field(default_factory=dict)
    few_shot_examples: list[Any] = Field(default_factory=list)
    generated_sql: str = ""
    conversation_state: str = "completed"
    error: str | None = None


def _normalize_optional_uuid(value: str | None, *, field: str) -> str | None:
    if value is None or not str(value).strip():
        return None
    try:
        return str(uuid.UUID(str(value).strip()))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"{field} must be a valid UUID") from e


def derive_session_title(user_text: str, max_chars: int = 60) -> str:
    """Short label from the first user question (single assign in DB; never overwritten there)."""
    s = " ".join((user_text or "").split())
    if not s:
        return "New chat"
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


_MAX_PIPELINE_COMPLETION_CHAT_CHARS = 200_000


def _persist_pipeline_completion_assistant(
    session_id: str,
    generated_sql: str,
    err: str | None,
) -> None:
    """Persist the main assistant turn so GET /sessions/.../messages can reload the thread."""
    parts = ["Here is what I found."]
    e = (err or "").strip()
    if e:
        parts.extend(["", e])
    gs = (generated_sql or "").strip()
    if gs:
        parts.extend(["", "Generated SQL:", gs])
    content = "\n".join(parts)
    if len(content) > _MAX_PIPELINE_COMPLETION_CHAT_CHARS:
        content = content[: _MAX_PIPELINE_COMPLETION_CHAT_CHARS - 40] + "\n… (truncated for storage)"
    try:
        insert_chat_message(
            session_id=session_id,
            role="assistant",
            message_type="pipeline_completed",
            content=content,
        )
    except Exception:
        logger.exception("Failed to persist pipeline completion assistant message")


def _empty_response(session_id: str, error: str) -> QueryResponse:
    return QueryResponse(
        session_id=session_id,
        rephrased_question="",
        resolved_question="",
        keywords=[],
        business_insights=[],
        few_shot_examples=[],
        selected_tables=[],
        selected_columns={},
        generated_sql="",
        intent_confidence=0,
        needs_confirmation=False,
        clarification_question="",
        conversation_state="error",
        pending_intent_id=None,
        error=error,
    )


INTENT_CONFIRM_THRESHOLD = 95

_OPEN_INVITE_RE = re.compile(
    r"(?is)\b("
    r"do\s+you\s+have\b"
    r"|what\s+(would|do)\s+you\b"
    r"|please\s+(describe|tell\s+me|share|provide)\b"
    r"|could\s+you\s+(please\s+)?(tell|describe|clarify)\b"
    r"|what\s+kind\s+of\b"
    r"|how\s+can\s+i\s+help\b"
    r"|what\s+are\s+you\s+looking\s+for\b"
    r"|tell\s+me\s+more\s+about\s+what\b"
    r"|any\s+analytical\s+question\b"
    r"|topic\s+you\s+would\s+like\s+to\s+explore\b"
    r")\b"
)


def _is_open_analytical_invitation(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(_OPEN_INVITE_RE.search(t))


def _is_trivial_user_message(msg: str) -> bool:
    m = (msg or "").strip().lower()
    if not m:
        return True
    if len(m) <= 3 and m.isalpha():
        return True
    trivial = {
        "hi",
        "hello",
        "hey",
        "yo",
        "sup",
        "thanks",
        "thank you",
        "thankyou",
        "ok",
        "okay",
        "k",
        "bye",
        "goodbye",
    }
    if m in trivial:
        return True
    if m.startswith("thank") and len(m) < 40:
        return True
    if m in {"good morning", "good afternoon", "good evening", "gm", "gn"}:
        return True
    return False


def _greeting_assistant_reply(user_message: str) -> str:
    """Short reply for trivial turns; no Yes/No — user should type their next question."""
    m = (user_message or "").strip().lower()
    if m.startswith("thank"):
        return "You're welcome! Whenever you're ready, describe the analysis you want."
    if m in {"bye", "goodbye"}:
        return "Goodbye! Come back anytime you have an analytical question."
    if m in {"hi", "hello", "hey", "yo", "sup", "gm", "gn"} or m in {
        "good morning",
        "good afternoon",
        "good evening",
    }:
        return "Hello! What would you like to analyze?"
    if m in {"ok", "okay", "k"}:
        return "Great — tell me what you'd like to explore in the data."
    return "Hi! When you're ready, describe what you'd like to analyze."


def _effective_intent_confidence(
    model_confidence: int,
    user_message: str,
    rephrased: str,
    keywords: list[str],
) -> int:
    c = max(0, min(100, int(model_confidence)))
    if _is_trivial_user_message(user_message):
        return min(c, 55)
    kw = keywords or []
    core = (rephrased or "").strip()
    if not kw and len(core) < 24:
        return min(c, 60)
    return c


def _strip_internal_memory_keys(summary: dict) -> dict:
    skip = {"pending_confirm_kind", "pending_intent_output_id"}
    return {k: v for k, v in summary.items() if k not in skip}


@router.get("/use-cases")
def get_use_cases() -> list[str]:
    return USE_CASES


@router.post("/session", response_model=SessionResponse)
def create_fresh_session(
    client_id: str | None = Query(
        default=None,
        description="Optional UUID; scopes session for GET /sessions",
    ),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
) -> SessionResponse:
    raw = (x_client_id or client_id or "").strip() or None
    cid = _normalize_optional_uuid(raw, field="client_id") if raw else None
    try:
        return SessionResponse(session_id=create_session(client_id=cid))
    except Exception as e:
        logger.exception("Failed to create session")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {e}") from e


@router.get("/sessions", response_model=list[SessionListItem])
def list_sessions(
    client_id: str = Query(..., min_length=1, description="UUID previously sent when creating sessions"),
    limit: int = Query(100, ge=1, le=500),
) -> list[SessionListItem]:
    cid = _normalize_optional_uuid(client_id, field="client_id")
    if not cid:
        raise HTTPException(status_code=400, detail="client_id is required")
    rows = list_sessions_for_client(cid, limit=limit)
    return [SessionListItem(**r) for r in rows]


def _assert_session_client_access(
    session_id: str,
    client_id: str | None,
    x_client_id: str | None,
) -> None:
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session_id")
    row = get_session_row(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    scoped = row.get("client_id")
    if scoped:
        raw = (x_client_id or client_id or "").strip()
        effective = _normalize_optional_uuid(raw, field="client_id") if raw else None
        if effective != scoped:
            raise HTTPException(
                status_code=403,
                detail="client_id does not match this session",
            )


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageItem])
def list_session_messages(
    session_id: str,
    client_id: str | None = Query(
        default=None,
        description="Must match session.client_id when the session is scoped",
    ),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
) -> list[ChatMessageItem]:
    _assert_session_client_access(session_id, client_id, x_client_id)
    msgs = get_all_chat_messages_ordered(session_id)
    return [ChatMessageItem(**m) for m in msgs]


@router.get("/sessions/{session_id}/pipeline-turns", response_model=list[PipelineTurnItem])
def list_session_pipeline_turns(
    session_id: str,
    client_id: str | None = Query(
        default=None,
        description="Must match session.client_id when the session is scoped",
    ),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
) -> list[PipelineTurnItem]:
    """Structured rows from intent/table/column/few-shot/gen-sql tables for rich replay."""
    _assert_session_client_access(session_id, client_id, x_client_id)
    rows = get_session_pipeline_turns(session_id)
    return [PipelineTurnItem(**r) for r in rows]


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    client_id: str | None = Query(
        default=None,
        description="Must match session.client_id (same as listing)",
    ),
    x_client_id: str | None = Header(default=None, alias="X-Client-Id"),
) -> Response:
    """Remove a session and all related app data (FK cascade). Scoped to owning client_id."""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Unknown session_id")
    raw = (x_client_id or client_id or "").strip()
    if not raw:
        raise HTTPException(
            status_code=400,
            detail="client_id query param or X-Client-Id header is required to delete a session",
        )
    cid = _normalize_optional_uuid(raw, field="client_id")
    if not delete_session_if_owned(session_id, cid):
        raise HTTPException(
            status_code=403,
            detail="Cannot delete this session (wrong client or session has no client_id)",
        )
    return Response(status_code=204)


@router.post("/query", response_model=QueryResponse)
def post_query(body: QueryRequest) -> QueryResponse:
    use_case = body.use_case.strip().lower()
    if use_case not in USE_CASES:
        raise HTTPException(status_code=400, detail=f"use_case must be one of: {USE_CASES}")

    if body.session_id:
        if not session_exists(body.session_id):
            raise HTTPException(status_code=400, detail="Invalid or unknown session_id")
        session_id = body.session_id
    else:
        try:
            raw_cid = (body.client_id or "").strip() or None
            cid = _normalize_optional_uuid(raw_cid, field="client_id") if raw_cid else None
            session_id = create_session(client_id=cid)
        except Exception as e:
            logger.exception("Failed to create session")
            return _empty_response("", str(e))

    logger.info("Query request: use_case=%s", use_case)
    user_message = body.message.strip()
    if not user_message:
        return _empty_response(session_id, "message cannot be empty")

    # Persist incoming user turn for chat history.
    try:
        insert_chat_message(
            session_id=session_id,
            role="user",
            message_type=body.message_type,
            content=user_message,
        )
    except Exception:
        logger.exception("Failed to persist user chat message")

    try:
        update_session_use_case(session_id, use_case)
        if body.message_type in ("new_query", "intent_correction"):
            set_session_title_if_unset(session_id, derive_session_title(user_message))
    except Exception:
        logger.exception("Failed to update session title/use_case")

    # Handle yes/no confirmation action before running a new intent.
    if body.message_type == "intent_confirmation":
        if body.confirmation not in {"yes", "no"}:
            return _empty_response(session_id, "confirmation must be 'yes' or 'no' for intent_confirmation")
        pending = get_latest_pending_intent(session_id)
        if not pending:
            return _empty_response(session_id, "No pending intent found for confirmation")
        session_mem = get_session_memory(session_id)
        confirm_kind = (session_mem or {}).get("pending_confirm_kind") or "intent_confirm"

        if confirm_kind == "open_invite" and body.confirmation == "yes":
            update_intent_review_status(pending["intent_output_id"], "rejected")
            try:
                merge_session_memory(
                    session_id,
                    {"pending_confirm_kind": None, "pending_intent_output_id": None},
                )
            except Exception:
                logger.exception("Failed to clear session memory after open-invite yes")
            follow = (
                "Please type your analytical question in the message box "
                "(for example: total sales by region last quarter)."
            )
            try:
                insert_chat_message(
                    session_id=session_id,
                    role="assistant",
                    message_type="intent_invite_accepted",
                    content=follow,
                )
            except Exception:
                logger.exception("Failed to persist assistant chat message")
            rq = (pending["rephrased_question"] or "").strip()
            return QueryResponse(
                session_id=session_id,
                rephrased_question=rq,
                resolved_question=rq,
                keywords=pending["keywords"] or [],
                business_insights=pending["business_insights"] or [],
                few_shot_examples=[],
                selected_tables=[],
                selected_columns={},
                generated_sql="",
                intent_confidence=int(pending["confidence_score"] or 0),
                needs_confirmation=False,
                clarification_question=follow,
                conversation_state="waiting_analytical_query",
                pending_intent_id=None,
                error=None,
            )

        if confirm_kind == "open_invite" and body.confirmation == "no":
            update_intent_review_status(pending["intent_output_id"], "rejected")
            try:
                merge_session_memory(
                    session_id,
                    {"pending_confirm_kind": None, "pending_intent_output_id": None},
                )
            except Exception:
                logger.exception("Failed to clear session memory after open-invite no")
            closing = "Ok, thank you!"
            try:
                insert_chat_message(
                    session_id=session_id,
                    role="assistant",
                    message_type="intent_conversation_closed",
                    content=closing,
                )
            except Exception:
                logger.exception("Failed to persist assistant chat message")
            rq = (pending["rephrased_question"] or "").strip()
            return QueryResponse(
                session_id=session_id,
                rephrased_question=rq,
                resolved_question=rq,
                keywords=pending["keywords"] or [],
                business_insights=pending["business_insights"] or [],
                few_shot_examples=[],
                selected_tables=[],
                selected_columns={},
                generated_sql="",
                intent_confidence=int(pending["confidence_score"] or 0),
                needs_confirmation=False,
                clarification_question=closing,
                conversation_state="conversation_ended",
                pending_intent_id=None,
                error=None,
            )

        if body.confirmation == "yes":
            try:
                merge_session_memory(
                    session_id,
                    {"pending_confirm_kind": None, "pending_intent_output_id": None},
                )
            except Exception:
                logger.exception("Failed to clear session memory after intent confirm yes")
            update_intent_review_status(pending["intent_output_id"], "confirmed")
            try:
                insert_chat_message(
                    session_id=session_id,
                    role="assistant",
                    message_type="intent_confirmation_result",
                    content="Thanks, I understood your intent. Proceeding to SQL generation.",
                )
            except Exception:
                logger.exception("Failed to persist confirmation assistant chat message")
            intent = {
                "rephrased_question": pending["rephrased_question"],
                "resolved_question": pending["rephrased_question"],
                "keywords": pending["keywords"] or [],
                "business_insights": pending["business_insights"] or [],
                "confidence_score": pending["confidence_score"],
                "clarification_question": "",
            }
            intent_output_id = pending["intent_output_id"]
        else:
            update_intent_review_status(pending["intent_output_id"], "rejected")
            try:
                merge_session_memory(
                    session_id,
                    {"pending_confirm_kind": None, "pending_intent_output_id": None},
                )
            except Exception:
                logger.exception("Failed to clear session memory after intent reject")
            try:
                insert_chat_message(
                    session_id=session_id,
                    role="assistant",
                    message_type="intent_rejected",
                    content="Thanks, please provide a corrected question.",
                )
            except Exception:
                logger.exception("Failed to persist rejection assistant chat message")
            return QueryResponse(
                session_id=session_id,
                rephrased_question=pending["rephrased_question"],
                resolved_question=pending["rephrased_question"],
                keywords=pending["keywords"] or [],
                business_insights=pending["business_insights"] or [],
                few_shot_examples=[],
                selected_tables=[],
                selected_columns={},
                generated_sql="",
                intent_confidence=int(pending["confidence_score"] or 0),
                needs_confirmation=False,
                clarification_question="Please provide a corrected question.",
                conversation_state="waiting_user_rephrase",
                pending_intent_id=pending["intent_output_id"],
                error=None,
            )
    else:
        # Build conversation context and run intent.
        try:
            recent_messages = get_recent_chat_messages(session_id, limit=8)
            session_summary = get_session_memory(session_id)
        except Exception:
            logger.exception("Failed to read chat context; continuing without it")
            recent_messages = []
            session_summary = {}
        if body.message_type in ("new_query", "intent_correction"):
            try:
                merge_session_memory(
                    session_id,
                    {"pending_confirm_kind": None, "pending_intent_output_id": None},
                )
            except Exception:
                logger.exception("Failed to reset pending confirmation flags in session memory")

    schema_name = USE_CASE_TO_SCHEMA[use_case]
    relationships: list[dict] = []
    try:
        relationships = list_relationships_from_metadata(schema_name)
    except Exception as e:
        logger.warning(
            "Could not load FK relationships from metadata for %s: %s",
            schema_name,
            e,
        )

    if body.message_type != "intent_confirmation":
        # Greeting / small talk only: respond in kind and wait for a real question (no Yes/No).
        if body.message_type == "new_query" and _is_trivial_user_message(user_message):
            rephrased = user_message.strip()
            resolved_question = rephrased
            keywords: list[str] = []
            business_insights: list[str] = []
            confidence_score = 50
            try:
                intent_output_id = insert_intent_output(
                    session_id=session_id,
                    use_case=use_case,
                    user_input=user_message,
                    rephrased_question=rephrased,
                    keywords=keywords,
                    business_insights=business_insights,
                )
                insert_intent_review(
                    intent_output_id=intent_output_id,
                    confidence_score=confidence_score,
                    confirmation_required=False,
                    confirmation_status="confirmed",
                )
            except Exception as e:
                logger.exception("Failed to persist greeting intent output")
                return QueryResponse(
                    session_id=session_id,
                    rephrased_question=rephrased,
                    resolved_question=resolved_question,
                    keywords=keywords,
                    business_insights=business_insights,
                    few_shot_examples=[],
                    selected_tables=[],
                    selected_columns={},
                    generated_sql="",
                    intent_confidence=confidence_score,
                    needs_confirmation=False,
                    clarification_question="",
                    conversation_state="error",
                    pending_intent_id=None,
                    error=f"Save failed: {e}",
                )
            reply = _greeting_assistant_reply(user_message)
            try:
                insert_chat_message(
                    session_id=session_id,
                    role="assistant",
                    message_type="greeting_ack",
                    content=reply,
                )
            except Exception:
                logger.exception("Failed to persist greeting assistant message")
            return QueryResponse(
                session_id=session_id,
                rephrased_question=rephrased,
                resolved_question=resolved_question,
                keywords=keywords,
                business_insights=business_insights,
                few_shot_examples=[],
                selected_tables=[],
                selected_columns={},
                generated_sql="",
                intent_confidence=confidence_score,
                needs_confirmation=False,
                clarification_question=reply,
                conversation_state="waiting_analytical_query",
                pending_intent_id=None,
                error=None,
            )

        pending_for_intent: str | None = None
        if body.message_type == "intent_correction":
            try:
                pending_for_intent = get_latest_rejected_intent_rephrase(session_id)
            except Exception:
                logger.exception("Failed to read rejected intent for correction context")
                pending_for_intent = None
        summary_for_intent: dict = {}
        if isinstance(session_summary, dict):
            summary_for_intent = _strip_internal_memory_keys(session_summary)
        try:
            intent = run_intent(
                user_message,
                use_case,
                recent_messages=recent_messages,
                last_confirmed_intent=None,
                pending_intent=pending_for_intent,
                session_summary=summary_for_intent,
            )
        except Exception as e:
            logger.exception("Intent Agent failed")
            return _empty_response(session_id, str(e))

        rephrased = intent.get("rephrased_question", "")
        resolved_question = intent.get("resolved_question") or rephrased
        keywords = intent.get("keywords") or []
        business_insights = intent.get("business_insights") or []
        _ics = intent.get("confidence_score")
        model_confidence = 50 if _ics is None else max(0, min(100, int(_ics)))
        confidence_score = _effective_intent_confidence(
            model_confidence, user_message, rephrased, keywords
        )
        intent["confidence_score"] = confidence_score
        clarification_question = (intent.get("clarification_question") or "").strip()
        needs_confirmation = confidence_score < INTENT_CONFIRM_THRESHOLD

        try:
            intent_output_id = insert_intent_output(
                session_id=session_id,
                use_case=use_case,
                user_input=user_message,
                rephrased_question=rephrased,
                keywords=keywords,
                business_insights=business_insights,
            )
            insert_intent_review(
                intent_output_id=intent_output_id,
                confidence_score=confidence_score,
                confirmation_required=needs_confirmation,
                confirmation_status="pending" if needs_confirmation else "confirmed",
            )
        except Exception as e:
            logger.exception("Failed to persist intent output")
            return QueryResponse(
                session_id=session_id,
                rephrased_question=rephrased,
                resolved_question=resolved_question,
                keywords=keywords,
                business_insights=business_insights,
                few_shot_examples=[],
                selected_tables=[],
                selected_columns={},
                generated_sql="",
                intent_confidence=confidence_score,
                needs_confirmation=needs_confirmation,
                clarification_question=clarification_question,
                conversation_state="error",
                pending_intent_id=None,
                error=f"Save failed: {e}",
            )

        if needs_confirmation:
            anchor = (rephrased or resolved_question or user_message).strip() or "—"
            prompt_text = (
                f'Did I understand correctly? You want: "{anchor}". Please answer Yes or No.'
            )
            open_invite = _is_open_analytical_invitation(clarification_question)
            confirm_kind = "open_invite" if open_invite else "intent_confirm"
            try:
                merge_session_memory(
                    session_id,
                    {
                        "pending_confirm_kind": confirm_kind,
                        "pending_intent_output_id": intent_output_id,
                    },
                )
            except Exception:
                logger.exception("Failed to persist pending confirmation kind in session memory")
            try:
                insert_chat_message(
                    session_id=session_id,
                    role="assistant",
                    message_type="intent_confirmation_prompt",
                    content=prompt_text,
                )
            except Exception:
                logger.exception("Failed to persist assistant confirmation prompt")
            return QueryResponse(
                session_id=session_id,
                rephrased_question=rephrased,
                resolved_question=resolved_question,
                keywords=keywords,
                business_insights=business_insights,
                few_shot_examples=[],
                selected_tables=[],
                selected_columns={},
                generated_sql="",
                intent_confidence=confidence_score,
                needs_confirmation=True,
                clarification_question=prompt_text,
                conversation_state="waiting_intent_confirmation",
                pending_intent_id=intent_output_id,
                error=None,
            )
    # Common fields for downstream pipeline path
    rephrased = intent.get("rephrased_question", "")
    resolved_question = intent.get("resolved_question") or rephrased
    keywords = intent.get("keywords") or []
    business_insights = intent.get("business_insights") or []
    _ics = intent.get("confidence_score")
    confidence_score = 50 if _ics is None else max(0, min(100, int(_ics)))
    clarification_question = (intent.get("clarification_question") or "").strip()

    few_shot_examples: list[dict] = []
    few_shot_error: str | None = None

    selected_tables: list[str] = []
    table_error: str | None = None
    try:
        table_out = run_table_agent(
            use_case,
            rephrased,
            keywords,
            relationships=relationships,
        )
        selected_tables = table_out.get("selected_tables") or []
    except Exception as e:
        logger.exception("Table Agent failed")
        table_error = f"Table Agent failed: {e}"

    table_agent_output_id: int | None = None
    try:
        table_agent_output_id = insert_table_agent_output(intent_output_id, selected_tables)
    except Exception as e:
        logger.exception("Failed to persist table agent output")
        persist_msg = f"Table selection save failed: {e}"
        table_error = f"{table_error}; {persist_msg}" if table_error else persist_msg

    selected_columns: dict[str, list[str]] = {}
    column_error: str | None = None
    if table_agent_output_id is not None:
        if selected_tables:
            try:
                rel_for_columns = filter_relationships_for_selected_tables(
                    schema_name,
                    relationships,
                    selected_tables,
                )
                col_out = run_column_agent(
                    use_case,
                    rephrased,
                    keywords,
                    selected_tables,
                    relationships=rel_for_columns,
                )
                selected_columns = col_out.get("selected_columns") or {}
            except Exception as e:
                logger.exception("Column Agent failed")
                column_error = f"Column Agent failed: {e}"
                selected_columns = {}
        try:
            insert_column_agent_output(table_agent_output_id, selected_columns)
        except Exception as e:
            logger.exception("Failed to persist column agent output")
            persist_col = f"Column selection save failed: {e}"
            column_error = f"{column_error}; {persist_col}" if column_error else persist_col

    try:
        fs_out = run_few_shot_agent(rephrased, keywords, business_insights)
        few_shot_examples = fs_out.get("few_shot_examples") or []
    except Exception as e:
        logger.exception("Few-Shot Agent failed")
        few_shot_examples = []
        few_shot_error = f"Few-Shot Agent failed: {e}"

    try:
        insert_few_shot_agent_output(intent_output_id, few_shot_examples)
    except Exception as e:
        logger.exception("Failed to persist few-shot agent output")
        persist_fs = f"Few-shot save failed: {e}"
        few_shot_error = f"{few_shot_error}; {persist_fs}" if few_shot_error else persist_fs

    generated_sql = ""
    reasoning_summary = ""
    gen_sql_error: str | None = None

    try:
        gen_out = run_gen_sql(
            use_case,
            rephrased,
            business_insights,
            few_shot_examples,
            selected_tables,
            selected_columns,
            relationships=relationships,
        )
        generated_sql = (gen_out.get("generated_sql") or "").strip()
        reasoning_summary = (gen_out.get("reasoning_summary") or "").strip()
    except Exception as e:
        logger.exception("Gen-SQL Agent failed")
        gen_sql_error = f"Gen-SQL Agent failed: {e}"

    try:
        validation = validate_generated_sql(
            generated_sql,
            selected_tables=selected_tables or None,
            selected_columns=selected_columns or None,
        )
    except Exception as e:
        logger.exception("SQL validator failed")
        validation = {
            "validation_passed": False,
            "validation_error_codes": "VALIDATOR_EXCEPTION",
            "validation_error_message": str(e),
            "blocked_keywords": "",
            "is_single_statement": False,
            "is_select_only": False,
        }

    if not validation.get("validation_passed"):
        msg = (validation.get("validation_error_message") or "").strip() or "SQL validation failed"
        codes = (validation.get("validation_error_codes") or "").strip()
        blocked = (validation.get("blocked_keywords") or "").strip()
        parts = [f"SQL validation: {msg}"]
        if codes:
            parts.append(f"({codes})")
        if blocked:
            parts.append(f"[blocked: {blocked}]")
        val_err = " ".join(parts)
        gen_sql_error = f"{gen_sql_error}; {val_err}" if gen_sql_error else val_err

    err = few_shot_error
    if table_error:
        err = f"{err}; {table_error}" if err else table_error
    if column_error:
        err = f"{err}; {column_error}" if err else column_error
    if gen_sql_error:
        err = f"{err}; {gen_sql_error}" if err else gen_sql_error

    try:
        insert_gen_sql_agent_output(
            intent_output_id,
            generated_sql,
            reasoning_summary if reasoning_summary else None,
            bool(validation.get("validation_passed")),
            str(validation.get("validation_error_codes") or ""),
            str(validation.get("validation_error_message") or ""),
            str(validation.get("blocked_keywords") or ""),
            bool(validation.get("is_single_statement")),
            bool(validation.get("is_select_only")),
        )
    except Exception as e:
        logger.exception("Failed to persist gen-sql agent output")
        persist_gen = f"Gen-SQL save failed: {e}"
        err = f"{err}; {persist_gen}" if err else persist_gen

    _persist_pipeline_completion_assistant(session_id, generated_sql, err)

    return QueryResponse(
        session_id=session_id,
        rephrased_question=rephrased,
        resolved_question=resolved_question,
        keywords=keywords,
        business_insights=business_insights,
        few_shot_examples=few_shot_examples,
        selected_tables=selected_tables,
        selected_columns=selected_columns,
        generated_sql=generated_sql,
        intent_confidence=confidence_score,
        needs_confirmation=False,
        clarification_question="",
        conversation_state="completed",
        pending_intent_id=None,
        error=err,
    )
