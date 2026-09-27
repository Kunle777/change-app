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

    if not await service.check_usage(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily AI limit reached")
    try:
        response = await service.handle_chat(db, current_user.id, payload.message)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    await service.increment_usage(db, current_user.id)
    return response


@router.post("/evening-summary", response_model=ChatResponse)
async def evening_summary_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await service.check_usage(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily AI limit reached")

    status_data = await checkin_service.get_todays_checkin_status(db, current_user)
    prompt = (
        f"The user completed their evening check-in. "
        f"Morning done: {status_data['morning_done']}, Evening done: {status_data['evening_done']}. "
        f"Give a short, warm, encouraging end-of-day summary in 2-3 sentences."
    )
    summary = gemini.generate_response(prompt)
    await service.increment_usage(db, current_user.id)
    return ChatResponse(intent="general_coaching", message=summary, suggested_actions=[])