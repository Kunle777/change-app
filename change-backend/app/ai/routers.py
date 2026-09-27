import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.Users.dependencies import get_current_user  # Adjust path if different in your project
from app.Users.models import User
from app.ai.schemas import ChatRequest, ChatResponse
from app.ai import service
from app.ai import gemini
from app.checkins import service as checkin_service


router = APIRouter(
    prefix="/api/ai",
    tags=["AI"],
)

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai_route(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    try:
        await service.check_usage(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))

    ai_response_text = gemini.generate_response(payload.message)
    await service.increment_usage(db, current_user.id)
    return ChatResponse(response=ai_response_text)


@router.post("/evening-summary", response_model=ChatResponse)
async def evening_summary_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await service.check_usage(db, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(e))

    status_data = await checkin_service.get_todays_checkin_status(db, current_user)
    prompt = (
        f"The user completed their evening check-in. "
        f"Morning done: {status_data['morning_done']}, Evening done: {status_data['evening_done']}. "
        f"Give a short, warm, encouraging end-of-day summary in 2-3 sentences."
    )
    summary = gemini.generate_response(prompt)
    await service.increment_usage(db, current_user.id)
    return ChatResponse(response=summary)