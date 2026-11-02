from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError


class InvalidModelResponse(Exception):
    pass


@dataclass(frozen=True)
class FailureInfo:
    code: str
    status_code: int
    message: str


class AIRequestError(Exception):
    def __init__(self, info: FailureInfo, request_id: str):
        super().__init__(info.code)
        self.info = info
        self.request_id = request_id


def classify_ai_failure(error: Exception) -> FailureInfo:
    if isinstance(error, SQLAlchemyError):
        return FailureInfo(
            "database_error", 503,
            "Elvyn couldn't access the information needed for this request. Please try again.",
        )
    error_name = type(error).__name__.lower()
    if isinstance(error, TimeoutError) or any(
        word in error_name for word in ("timeout", "deadlineexceeded")
    ):
        return FailureInfo(
            "request_timeout", 504,
            "Elvyn took too long to respond. Please try again.",
        )
    if isinstance(error, ConnectionError) or any(
        word in error_name
        for word in ("connection", "connecterror", "network")
    ):
        return FailureInfo(
            "network_error", 503,
            "Elvyn couldn't connect to a required service. Please try again.",
        )

    code = getattr(error, "code", None)
    status = getattr(error, "status_code", None)
    try:
        status = int(status or code)
    except (TypeError, ValueError):
        status = None
    label = " ".join(
        str(value or "") for value in (code, getattr(error, "status", ""))
    ).upper()
    detail = str(error).casefold()
    if isinstance(error, InvalidModelResponse):
        return FailureInfo(
            "invalid_model_response", 502,
            "Elvyn couldn't form a reliable response. Please try asking another way.",
        )
    if status == 429 or "RESOURCE_EXHAUSTED" in label:
        quota = "quota" in detail or "resource_exhausted" in label
        return FailureInfo(
            "provider_quota" if quota else "provider_rate_limit",
            429,
            (
                "Elvyn's AI service is at its current usage limit. Please try again later."
                if quota
                else "Elvyn's AI service is handling too many requests. Please try again shortly."
            ),
        )
    if (
        status in {400, 401, 403}
        and (
        "api key" in detail or status in {401, 403}
        )
    ) or any(token in label for token in ("UNAUTHENTICATED", "PERMISSION_DENIED")):
        return FailureInfo(
            "provider_auth", 502,
            "Elvyn's AI service is temporarily unavailable. Please contact support if this continues.",
        )
    if (status is not None and status >= 500) or any(
        token in label for token in ("UNAVAILABLE", "INTERNAL")
    ):
        return FailureInfo(
            "provider_outage", 503,
            "Elvyn's AI service is temporarily unavailable. Please try again shortly.",
        )
    return FailureInfo(
        "backend_error", 500,
        "Elvyn couldn't complete that request. Please try again.",
    )
