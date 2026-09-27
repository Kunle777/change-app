from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str


class SuggestedAction(BaseModel):
    type: str  # "open_task" | "navigate" | "suggest_breakdown"
    label: str
    task_id: str | None = None
    screen: str | None = None


class ChatResponse(BaseModel):
    intent: str
    message: str
    suggested_actions: list[SuggestedAction] = []
