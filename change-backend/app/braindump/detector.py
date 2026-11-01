import re

ACTION_VERBS = [
    "finish", "call", "email", "submit", "buy", "pay", "reply", "schedule",
    "book", "send", "review", "complete", "prepare", "meet", "pick up",
    "renew", "cancel", "confirm", "update", "fix", "clean", "apply",
]

TIME_SIGNALS = [
    r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b", r"\b(?:at|by)\s+\d{1,2}\b",
]


def looks_like_possible_task(content: str) -> bool:
    text = content.lower()
    has_action = any(re.search(rf"\b{re.escape(verb)}\b", text) for verb in ACTION_VERBS)
    has_time = any(re.search(pattern, text) for pattern in TIME_SIGNALS)
    return has_action or has_time