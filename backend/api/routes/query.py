"""Routes: POST /query (Intent + Table + Column Agent), GET /use-cases."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.agents.column_agent import run_column_agent
from backend.agents.intent_agent import run_intent
from backend.agents.table_agent import run_table_agent
from backend.api.db import (
    create_session,
    insert_column_agent_output,
    insert_intent_output,
    insert_table_agent_output,
    session_exists,
)
from backend.config import USE_CASES

logger = logging.getLogger(__name__)
router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    message: str = Field(..., min_length=1)
    use_case: str = Field(...)
    session_id: str | None = Field(None)


class QueryResponse(BaseModel):
    session_id: str
    rephrased_question: str
    keywords: list[str]
    business_insights: list[str]
    selected_tables: list[str] = Field(default_factory=list)
    selected_columns: dict[str, list[str]] = Field(default_factory=dict)
    error: str | None = None


def _empty_response(session_id: str, error: str) -> QueryResponse:
    return QueryResponse(
        session_id=session_id,
        rephrased_question="",
        keywords=[],
        business_insights=[],
        selected_tables=[],
        selected_columns={},
        error=error,
    )


@router.get("/use-cases")
def get_use_cases() -> list[str]:
    return USE_CASES


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
            session_id = create_session()
        except Exception as e:
            logger.exception("Failed to create session")
            return _empty_response("", str(e))

    logger.info("Query request: use_case=%s", use_case)
    try:
        intent = run_intent(body.message.strip(), use_case)
    except Exception as e:
        logger.exception("Intent Agent failed")
        return _empty_response(session_id, str(e))

    rephrased = intent.get("rephrased_question", "")
    keywords = intent.get("keywords") or []
    business_insights = intent.get("business_insights") or []

    try:
        intent_output_id = insert_intent_output(
            session_id=session_id,
            use_case=use_case,
            user_input=body.message.strip(),
            rephrased_question=rephrased,
            keywords=keywords,
            business_insights=business_insights,
        )
    except Exception as e:
        logger.exception("Failed to persist intent output")
        return QueryResponse(
            session_id=session_id,
            rephrased_question=rephrased,
            keywords=keywords,
            business_insights=business_insights,
            selected_tables=[],
            selected_columns={},
            error=f"Save failed: {e}",
        )

    selected_tables: list[str] = []
    table_error: str | None = None
    try:
        table_out = run_table_agent(use_case, rephrased, keywords)
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
                col_out = run_column_agent(use_case, rephrased, keywords, selected_tables)
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

    err = table_error
    if column_error:
        err = f"{err}; {column_error}" if err else column_error

    return QueryResponse(
        session_id=session_id,
        rephrased_question=rephrased,
        keywords=keywords,
        business_insights=business_insights,
        selected_tables=selected_tables,
        selected_columns=selected_columns,
        error=err,
    )
