"""Routes for Intent Agent: POST /query, GET /use-cases."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.agents.intent_agent import run_intent
from backend.api.db import create_session, insert_intent_output, session_exists
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
    error: str | None = None


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
            return QueryResponse(session_id="", rephrased_question="", keywords=[], business_insights=[], error=str(e))

    logger.info("Intent request: use_case=%s", use_case)
    try:
        intent = run_intent(body.message.strip(), use_case)
    except Exception as e:
        logger.exception("Intent Agent failed")
        return QueryResponse(session_id=session_id, rephrased_question="", keywords=[], business_insights=[], error=str(e))

    rephrased = intent.get("rephrased_question", "")
    keywords = intent.get("keywords") or []
    business_insights = intent.get("business_insights") or []

    try:
        insert_intent_output(
            session_id=session_id,
            use_case=use_case,
            user_input=body.message.strip(),
            rephrased_question=rephrased,
            keywords=keywords,
            business_insights=business_insights,
        )
    except Exception as e:
        logger.exception("Failed to persist intent output")
        return QueryResponse(session_id=session_id, rephrased_question=rephrased, keywords=keywords, business_insights=business_insights, error=f"Save failed: {e}")

    return QueryResponse(session_id=session_id, rephrased_question=rephrased, keywords=keywords, business_insights=business_insights, error=None)
