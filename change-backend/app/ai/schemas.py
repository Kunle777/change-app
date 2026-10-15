from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str
    conversation_id: UUID | None = None


class SuggestedAction(BaseModel):
    type: str  # "open_task" | "navigate" | "suggest_breakdown"
    label: str
    task_id: str | None = None
    screen: str | None = None


class MemorySource(BaseModel):
    id: str
    kind: str
    date: str
    snippet: str


class ChatResponse(BaseModel):
    intent: str
    message: str
    suggested_actions: list[SuggestedAction] = []
    conversation_id: UUID | None = None
    pending_action_id: UUID | None = None
    pending_action_summary: str | None = None
    memory_sources: list[MemorySource] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    updated_at: datetime


class ConversationTurn(BaseModel):
    id: UUID
    question: str
    response: str
    intent: str | None
    created_at: datetime | None
    pending_action_id: UUID | None = None


class ConversationDetail(ConversationSummary):
    messages: list[ConversationTurn]


class PendingActionSummary(BaseModel):
    id: UUID
    summary: str
    expires_at: datetime
