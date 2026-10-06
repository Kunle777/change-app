import re

INTENT_KEYWORDS = {
    "task_planning": ["what should i do", "focus on", "plan my day", "today"],
    "pattern_reflection": ["why do i", "keep postponing", "keep procrastinating", "pattern"],
    "daily_review": ["how was my", "what did i get done", "review my"],
    "task_help": ["stuck on", "help me start", "don't know where to start", "overwhelmed"],
}

OUT_OF_SCOPE_SIGNALS = [
    r"\bwrite (me )?(a |some )?(python|javascript|code|essay|poem)\b",
    r"\bwhat is bitcoin\b",
    r"\bhomework\b",
    r"\brecipe\b",
]


def detect_intent(message: str) -> str:
    text = message.lower()

    for pattern in OUT_OF_SCOPE_SIGNALS:
        if re.search(pattern, text):
            return "out_of_scope"

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return intent

    return "general_coaching"
