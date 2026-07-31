"""
Mock draft results delivery.

Mock drafts are not persisted server-side — they live in the browser's
localStorage. This endpoint exists so a user can get a copy out: it mails the
summary they just generated to the address on their own account.

Deliberately no recipient field. Letting a caller choose the destination would
turn this into an open relay for arbitrary attacker-supplied text, so the
address always comes from the authenticated session.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.email import send_mock_draft_summary
from app.limiter import limiter
from app.models import User

router = APIRouter(tags=["mock-draft"])

MAX_SUMMARY_CHARS = 40_000


class MockDraftEmailIn(BaseModel):
    summary: str = Field(min_length=1, max_length=MAX_SUMMARY_CHARS)
    slot: int = Field(ge=1, le=32)
    rounds: int = Field(ge=1, le=30)
    value_index: float = Field(ge=-1000, le=1000)


@router.post("/mock-draft/email", status_code=202)
@limiter.limit("5/hour")
async def email_mock_draft(
    request: Request,
    payload: MockDraftEmailIn,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if not current_user.email:
        raise HTTPException(status_code=400, detail="Your account has no email address")

    # Sent in the background so a slow SMTP hop doesn't block the response.
    background.add_task(
        send_mock_draft_summary,
        current_user.email,
        payload.summary,
        payload.slot,
        payload.rounds,
        payload.value_index,
    )
    return {"status": "queued", "to": current_user.email}
