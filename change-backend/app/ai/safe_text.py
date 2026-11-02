import re


_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.I,
)
_COMPACT_UUID = re.compile(r"\b[0-9a-f]{32}\b", re.I)
_ACTION_REFERENCE = re.compile(r"\bpa_[0-9a-f]{64}\b", re.I)
_TASK_REFERENCE = re.compile(r"\btk_[0-9a-f]{64}\b", re.I)
_TOOL_CALL_REFERENCE = re.compile(r"\bcall_[a-f0-9]{8,}\b", re.I)
_LABELED_IDENTIFIER = re.compile(
    r"\b(?:(?:task|pending(?:[- ]action)?|action|tool(?:[- ]call)?|database|record|"
    r"internal|primary key)\s*)?(?:id|identifier|#)\s*(?:is\s+)?[:=#]?\s*"
    r"[a-z0-9_-]{1,64}\b",
    re.I,
)


def redact_internal_identifiers(value: str) -> str:
    value = _UUID.sub("[hidden identifier]", value)
    value = _COMPACT_UUID.sub("[hidden identifier]", value)
    value = _ACTION_REFERENCE.sub("[hidden identifier]", value)
    value = _TASK_REFERENCE.sub("[hidden identifier]", value)
    value = _TOOL_CALL_REFERENCE.sub("[hidden identifier]", value)
    return _LABELED_IDENTIFIER.sub("[hidden identifier]", value)
