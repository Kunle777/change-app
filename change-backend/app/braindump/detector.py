import re

ACTION_VERBS = [
    "finish", "call", "email", "submit", "buy", "pay", "reply", "schedule",
    "book", "send", "review", "complete", "prepare", "meet", "pick up",
    "renew", "cancel", "confirm", "update", "fix", "clean", "apply",
]

DATE_TIME_SIGNALS = [
    r"\btomorrow\b", r"\btoday\b", r"\btonight\b", r"\bnext week\b",
    r"\bmonday\b", r"\btuesday\b", r"\bwednesday\b", r"\bthursday\b",
    r"\bfriday\b", r"\bsaturday\b", r"\bsunday\b",
    r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b", r"\bat \d{1,2}\b",
]


def looks_like_possible_task(content: str) -> bool:
    text = content.lower()
    has_action = any(re.search(rf"\b{re.escape(verb)}\b", text) for verb in ACTION_VERBS)
    has_date_time = any(re.search(pattern, text) for pattern in DATE_TIME_SIGNALS)
    return has_action or has_date_time