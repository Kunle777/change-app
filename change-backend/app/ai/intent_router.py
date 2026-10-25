import re
from dataclasses import dataclass

OUT_OF_SCOPE_SIGNALS = [
    r"\bwrite (me )?(a |some )?(python|javascript|code|essay|poem)\b",
    r"\bwhat is bitcoin\b",
    r"\bhomework\b",
    r"\brecipe\b",
]

_PATTERN = re.compile(
    r"\b(why do i keep|keep (postponing|procrastinating|putting off)|pattern|"
    r"always (put off|postpone|delay)|what do i always)\b",
    re.I,
)
_POSTPONE = re.compile(
    r"\b(putting off|put off|postpon\w*|procrastinat\w*|not now|snooze|"
    r"keep delaying|what have i been putting)\b",
    re.I,
)
_FEELING = re.compile(
    r"\b(how (have i|am i|was i) (feeling|doing)|how('?s| is) my mood|"
    r"feeling lately|check-?ins?|my mood)\b",
    re.I,
)
_DATE_BROWSE = re.compile(
    r"\b(what did i (write|journal|dump|note|save)|show me my (notes|entries|brain ?dumps?|"
    r"check-?ins?)|my (brain ?dumps?|journal|entries) from)\b",
    re.I,
)
_RECALL = re.compile(
    r"\b(remember (what|when|that)|did i (tell|say|mention|write)|i (told you|mentioned|"
    r"said|wrote) |remind me what)\b",
    re.I,
)
_REVIEW = re.compile(
    r"\b(how was my|what did i get done|review my|what have i (done|completed)|"
    r"end of (the )?day)\b",
    re.I,
)
_HELP = re.compile(
    r"\b(stuck on|help me start|don'?t know where to start|overwhelmed|"
    r"break (this|it) down)\b",
    re.I,
)
_PLAN = re.compile(
    r"\b(what should i do|plan my (day|week)|focus on|to-?do|what do i have|"
    r"today'?s tasks?|help me plan|upcoming|due today)\b",
    re.I,
)

INTENT_KEYWORDS = {
    "task_planning": ["what should i do", "focus on", "plan my day", "today"],
    "pattern_reflection": ["why do i", "keep postponing", "keep procrastinating", "pattern"],
    "daily_review": ["how was my", "what did i get done", "review my"],
    "task_help": ["stuck on", "help me start", "don't know where to start", "overwhelmed"],
}

MEMORY_INTENTS = {
    "pattern_reflection",
    "postponement",
    "feeling",
    "date_browse",
    "recall",
}
TASK_INTENTS = {
    "task_planning",
    "task_help",
    "daily_review",
    "postponement",
    "pattern_reflection",
}
EVENT_INTENTS = {"postponement", "pattern_reflection", "daily_review"}
BEHAVIOR_INTENTS = {"postponement", "pattern_reflection"}


@dataclass(frozen=True)
class SourcePlan:
    intent: str
    need_tasks: bool
    need_events: bool
    need_behavior: bool
    need_memory: bool
    memory_source_types: tuple[str, ...] | None = None


def detect_intent(message: str) -> str:
    text = message.lower()

    for pattern in OUT_OF_SCOPE_SIGNALS:
        if re.search(pattern, text):
            return "out_of_scope"

    if _PATTERN.search(text):
        return "pattern_reflection"
    if _POSTPONE.search(text):
        return "postponement"
    if _FEELING.search(text):
        return "feeling"
    if _DATE_BROWSE.search(text):
        return "date_browse"
    if _RECALL.search(text):
        return "recall"
    if _REVIEW.search(text):
        return "daily_review"
    if _HELP.search(text):
        return "task_help"
    if _PLAN.search(text):
        return "task_planning"

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return intent

    return "general_coaching"


def plan_sources(question: str, intent: str | None = None) -> SourcePlan:
    intent = intent or detect_intent(question)
    if intent == "out_of_scope":
        return SourcePlan(intent, False, False, False, False)

    from app.memory.retrieval import should_retrieve

    need_memory = intent in MEMORY_INTENTS or should_retrieve(question, intent)
    memory_types: tuple[str, ...] | None = None
    if need_memory and intent == "feeling":
        memory_types = ("check_in", "brain_dump")
    elif need_memory and intent == "date_browse":
        memory_types = ("brain_dump", "check_in")

    return SourcePlan(
        intent=intent,
        need_tasks=intent in TASK_INTENTS,
        need_events=intent in EVENT_INTENTS,
        need_behavior=intent in BEHAVIOR_INTENTS,
        need_memory=need_memory,
        memory_source_types=memory_types,
    )
