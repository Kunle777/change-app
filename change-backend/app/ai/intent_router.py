import re
from collections.abc import Iterable
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


# --- Composable source cues -------------------------------------------------
# Each cue decides ONE source independently; the plan is the union of whatever fires.
# `intent` stays as a single label for logging and the prompt, but it no longer
# gates which sources are loaded.
_TASK_CUE = re.compile(
    r"\b(tasks?|to-?dos?|due|deadlines?|overdue|working on|on my plate|my list|"
    r"schedule[sd]?|reminders?|upcoming|today|tomorrow|this week|next week|backlog|"
    r"what (should|do) i|focus on|plan my|portfolio|project)\b",
    re.I,
)
_STRUGGLE_CUE = re.compile(
    r"\b(struggl\w*|stuck|can'?t (start|finish|get)|hard to (start|finish|focus)|"
    r"why (is|am|are|can'?t|do|does|might)|not (getting|making) (anywhere|progress)|"
    r"falling behind|behind on|keep (failing|missing|forgetting))\b",
    re.I,
)
_EVENT_CUE = re.compile(
    r"\b(postpon\w*|putting off|put off|delay\w*|resched\w*|snooze\w*|not now|"
    r"push(ed|ing)? (back|it|this)|moved|"
    r"keep (postponing|delaying|pushing|putting)|history|completed)\b",
    re.I,
)
_BEHAVIOR_CUE = re.compile(
    r"\b(pattern|habit|always|usually|tend to|keep (postponing|delaying|putting|avoiding|"
    r"procrastinating)|why do i keep|every time|how (am|have) i been doing|my progress)\b",
    re.I,
)
_MOOD_CUE = re.compile(
    r"\b(feel(ing|s)?|mood|check-?ins?|stress(ed)?|anxious|overwhelm\w*|tired|energy|"
    r"motivat\w*|burn(ed|t)? ?out)\b",
    re.I,
)
_ACTION_CUE = re.compile(
    r"(^|\b(please|can you|could you|would you|i want you to|i need you to)\s+)"
    r"(add|create|make|set up|schedule|remind|reschedule|move|push|change|update|"
    r"cancel|delete|remove|rename|bump)\b|\bremind me\b|\badd (a |an |this |it )?"
    r"(task|reminder|to my)\b"
    r"|\bput (it|this|that)\b.{0,20}\b(list|tasks?)\b"
    r"|\bdon'?t let me forget\b|\bnote (this|that) down\b|\bwrite (this|that) down\b",
    re.I,
)
_STOP_WORDS = frozenset(
    "the a an to of for my on in and or with this that it is be at by do i me up".split()
)
_REFERS_TO_TASK = re.compile(r"\b(this|that|the|my) (task|one|thing|project)\b", re.I)


def is_action_request(message: str) -> bool:
    """Deterministic check that the CURRENT user message asks for a task change."""
    return bool(_ACTION_CUE.search(message or ""))


def _words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9']+", (text or "").lower())
        if len(word) > 2 and word not in _STOP_WORDS
    }


def mentions_open_task(message: str, titles: "Iterable[str]") -> bool:
    """True when the message names one of the user's open tasks (by title words)."""
    message_words = _words(message)
    if not message_words:
        return False
    lowered = (message or "").lower()
    for title in titles:
        title = (title or "").strip().lower()
        if len(title) >= 4 and title in lowered:
            return True
        title_words = _words(title)
        if not title_words:
            continue
        overlap = title_words & message_words
        # One distinctive shared word ("portfolio") is enough; short words are not.
        if any(len(word) >= 5 for word in overlap):
            return True
        if len(overlap) >= 2 or (title_words and overlap == title_words):
            return True
    return False


@dataclass(frozen=True)
class SourcePlan:
    intent: str
    need_tasks: bool
    need_events: bool
    need_behavior: bool
    need_memory: bool
    memory_source_types: tuple[str, ...] | None = None
    action_intent: bool = False


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


_FOLLOW_UP = re.compile(
    r"^(and|but|so|what about|how about|why|what else|more|that|those|it|they|then|also)\b", re.I
)


def is_follow_up(message: str) -> bool:
    text = (message or "").strip()
    return bool(text) and (len(text.split()) <= 5 or bool(_FOLLOW_UP.match(text)))


def plan_sources(
    question: str,
    intent: str | None = None,
    *,
    task_titles: "Iterable[str]" = (),
    previous_question: str | None = None,
) -> SourcePlan:
    """Select context sources independently from cues in the message.

    `task_titles` are the user's own open task titles; naming one pulls in that
    task's facts, events and behavior so "why am I stuck on my portfolio?" works.
    """
    intent = intent or detect_intent(question)
    if intent == "out_of_scope":
        return SourcePlan(intent, False, False, False, False)

    from app.memory.retrieval import should_retrieve

    text = question or ""
    action = is_action_request(text)
    task_named = mentions_open_task(text, task_titles)
    struggle = bool(_STRUGGLE_CUE.search(text))
    mood = bool(_MOOD_CUE.search(text))

    need_behavior = (
        intent in BEHAVIOR_INTENTS
        or bool(_BEHAVIOR_CUE.search(text))
        or (struggle and (task_named or bool(_REFERS_TO_TASK.search(text))))
    )
    need_events = (
        intent in EVENT_INTENTS
        or need_behavior
        or bool(_EVENT_CUE.search(text))
        or (struggle and (task_named or bool(_REFERS_TO_TASK.search(text))))
    )
    need_tasks = (
        intent in TASK_INTENTS
        or need_events
        or action
        or task_named
        or bool(_TASK_CUE.search(text))
        or (struggle and bool(_REFERS_TO_TASK.search(text)))
    )
    need_memory = (
        intent in MEMORY_INTENTS
        or should_retrieve(text, intent)
        or (struggle and mood)
    )

    memory_types: tuple[str, ...] | None = None
    if need_memory and (intent in ("feeling", "date_browse") or (mood and intent not in ("recall",))):
        recall_like = intent in ("recall", "pattern_reflection", "postponement")
        if not recall_like:
            memory_types = ("check_in", "brain_dump")

    plan = SourcePlan(
        intent=intent,
        need_tasks=need_tasks,
        need_events=need_events,
        need_behavior=need_behavior,
        need_memory=need_memory,
        memory_source_types=memory_types,
        action_intent=action,
    )
    if previous_question and is_follow_up(text):
        # A short follow-up ("and the week before?") continues the previous topic, so it
        # inherits that turn's SOURCES. It never inherits an action request.
        previous = plan_sources(previous_question, task_titles=task_titles)
        if previous.intent != "out_of_scope":
            plan = SourcePlan(
                intent=intent,
                need_tasks=plan.need_tasks or previous.need_tasks,
                need_events=plan.need_events or previous.need_events,
                need_behavior=plan.need_behavior or previous.need_behavior,
                need_memory=plan.need_memory or previous.need_memory,
                memory_source_types=plan.memory_source_types or previous.memory_source_types,
                action_intent=action,
            )
    return plan
