"""Concierge endpoint (Phase C) — one chat turn per request.

Thin per convention: validate, rate-limit, delegate to services/concierge.py.
The reply is safety-scanned (forbidden-phrase scan + strict retry + hard
block) inside the service chokepoint and always ships with the envelope.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.session import get_db
from apps.api.services.concierge import (
    MAX_MESSAGE_CHARS,
    check_rate_limit,
    concierge_chat,
)
from apps.api.services.safety import SafetyViolation

router = APIRouter(prefix="/v1/concierge", tags=["concierge"])


class ConciergeTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=MAX_MESSAGE_CHARS)


class ConciergeRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    history: list[ConciergeTurn] = Field(default_factory=list, max_length=16)
    symbol: str = Field(default="NG", max_length=8)
    route: str | None = Field(default=None, max_length=64)


class ConciergeSuggestion(BaseModel):
    route: str
    label: str


@router.post("/chat")
async def concierge_chat_endpoint(
    req: ConciergeRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> dict:
    client_key = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_key):
        raise HTTPException(
            status_code=429,
            detail="Concierge rate limit reached — please try again later.",
        )

    try:
        reply, suggestions, envelope = await concierge_chat(
            session,
            message=req.message,
            history=[t.model_dump() for t in req.history],
            symbol=req.symbol.upper(),
            route=req.route,
        )
    except SafetyViolation:
        # The scan blocked the model's output twice — return a safe refusal
        # rather than a 500 (the user did nothing wrong).
        raise HTTPException(
            status_code=502,
            detail=(
                "The concierge could not produce a response that meets the "
                "safety rules for this question. Try rephrasing — note it "
                "never gives trading advice."
            ),
        )

    return {
        "reply": reply,
        "suggestions": suggestions,
        "safety": envelope.model_dump(),
    }
