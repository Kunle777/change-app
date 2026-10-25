import asyncio
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.users.dependencies import get_current_user
from app.users.models import User
from app.ai.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    PendingActionSummary,
)
from app.ai import service
from app.ai import action_service
from app.ai import gemini
from app.memory.policy import ai_processing_allowed
from app.ai.prompt_builder import build_system_prompt_for_user
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

    access = await ai_processing_allowed(db, current_user.id)
    if not access.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI features are turned off for this account",
        )
    if not await service.check_usage(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily AI limit reached")
    try:
        response = await service.handle_chat(
            db,
            current_user,
            payload.message,
            payload.conversation_id,
            current_user.last_active_timezone,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    await service.increment_usage(db, current_user.id)
    return response


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.list_conversations(db, current_user.id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation_route(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conversation = await service.get_conversation(db, current_user.id, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.get("/actions/pending", response_model=list[PendingActionSummary])
async def list_pending_actions_route(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await action_service.list_pending_actions(db, current_user, conversation_id)


@router.post("/actions/{pending_id}/confirm")
async def confirm_pending_action_route(
    pending_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await action_service.confirm_pending_action(db, current_user, pending_id)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/actions/{pending_id}/reject")
async def reject_pending_action_route(
    pending_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await action_service.reject_pending_action(db, current_user, pending_id)


@router.post("/evening-summary", response_model=ChatResponse)
async def evening_summary_route(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    access = await ai_processing_allowed(db, current_user.id)
    if not access.allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI features are turned off for this account",
        )
    if not await service.check_usage(db, current_user.id):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Daily AI limit reached")

    status_data = await checkin_service.get_todays_checkin_status(db, current_user)
    context = (
        f"Today's check-in status: morning done={status_data['morning_done']}; "
        f"evening done={status_data['evening_done']}."
    )
    system_prompt, _ = await build_system_prompt_for_user(
        db,
        current_user.id,
        "daily_review",
        context,
        timezone_name=current_user.last_active_timezone,
        additional_instructions=(
            "Give a short, warm, encouraging end-of-day summary in 2-3 sentences. "
            "Use only the supplied check-in status and recent activity."
        ),
    )
    summary = await asyncio.to_thread(gemini.generate_response, system_prompt)
    await service.increment_usage(db, current_user.id)
    return ChatResponse(intent="general_coaching", message=summary, suggested_actions=[])
