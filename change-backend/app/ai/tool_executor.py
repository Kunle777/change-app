import uuid
import re
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.ai.task_context import find_tasks_by_name
from app.tasks import service as task_service
from app.tasks.models import PriorityEnum, StatusEnum
from app.tasks.schemas import TaskCreate, TaskUpdate
from app.users.models import User
from sqlalchemy.ext.asyncio import AsyncSession


AUTO_EXECUTE_TOOLS = {"create_task"}
CONFIRMATION_REQUIRED_TOOLS = {"update_task", "delete_task"}
SUPPORTED_TOOLS = AUTO_EXECUTE_TOOLS | CONFIRMATION_REQUIRED_TOOLS


def _parse_task_id(raw: object) -> uuid.UUID:
    try:
        if not isinstance(raw, str):
            raise ValueError
        return uuid.UUID(raw)
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError("Model supplied a task_id that isn't a valid UUID") from error


def _user_timezone(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.last_active_timezone or "Africa/Lagos")
    except Exception:
        return ZoneInfo("Africa/Lagos")


def _parse_due_date(raw: object, user: User) -> datetime | None:
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("due_date must be an ISO 8601 date or date-time")

    value = raw.strip()
    zone = _user_timezone(user)
    try:
        if len(value) == 10:
            parsed_date = date.fromisoformat(value)
            parsed = datetime.combine(parsed_date, time(23, 59), tzinfo=zone)
        else:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=zone)
    except ValueError as error:
        raise ValueError("due_date must be a valid ISO 8601 date or date-time") from error
    return parsed.astimezone(timezone.utc)


async def _resolve_task(
    db: AsyncSession,
    user: User,
    arguments: dict,
    *,
    open_only: bool,
    for_update: bool = False,
) -> tuple[object | None, dict | None]:
    task_id = arguments.get("task_id")
    task_name = arguments.get("task_name")
    if task_id is not None:
        return (
            await task_service.get_task_by_id(
                db, _parse_task_id(task_id), user.id, for_update=for_update
            ),
            None,
        )
    if not isinstance(task_name, str) or not task_name.strip():
        raise ValueError("Please identify the task by its name")
    matches = await find_tasks_by_name(
        db, user.id, task_name, open_only=open_only, for_update=for_update
    )
    if not matches:
        return None, {"status": "not_found"}
    if len(matches) > 1:
        return None, {
            "status": "ambiguous",
            "candidates": [
                {
                    "title": task.title,
                    "status": task.status.name.lower(),
                    "deadline": (
                        task.due_date.isoformat() if task.due_date else None
                    ),
                }
                for task in matches[:5]
            ],
        }
    return matches[0], None


def _validate_requested_clock(raw: object, user: User, message: str | None) -> None:
    if not message:
        return
    requested = re.search(
        r"\b(?:at|by)?\s*(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b",
        message,
        re.I,
    )
    if requested:
        hour = int(requested.group(1))
        minute = int(requested.group(2) or 0)
        meridiem = requested.group(3).lower().replace(".", "")
        if not 1 <= hour <= 12 or minute > 59:
            raise ValueError("The requested time is invalid")
        expected_hour = (hour % 12) + (12 if meridiem == "pm" else 0)
    else:
        requested = re.search(
            r"\b(?:at|by)\s+([01]?\d|2[0-3]):([0-5]\d)\b", message, re.I
        )
        if not requested:
            if isinstance(raw, str) and len(raw.strip()) > 10:
                raise ValueError(
                    "No specific time was requested; use a date-only deadline instead"
                )
            return
        expected_hour, minute = int(requested.group(1)), int(requested.group(2))

    parsed = _parse_due_date(raw, user)
    if parsed is None or parsed.astimezone(_user_timezone(user)).hour != expected_hour:
        raise ValueError("The proposed date-time does not preserve the time you requested")
    if parsed.astimezone(_user_timezone(user)).minute != minute:
        raise ValueError("The proposed date-time does not preserve the time you requested")


_DATE_CUE = re.compile(
    r"\b(today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|next week|this week|"
    r"in \d+ (day|week|month)s?|"
    r"january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\b|\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b|"
    r"\b\d{4}-\d{2}-\d{2}\b",
    re.I,
)
_CLOCK_CUE = re.compile(
    r"\b(?:at|by)\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?\b|"
    r"\b\d{1,2}(?::\d{2})\s*(?:a\.?m\.?|p\.?m\.?)\b",
    re.I,
)


def _validate_requested_date(raw: object, message: str | None) -> None:
    if not message:
        return
    has_date = bool(_DATE_CUE.search(message))
    has_clock = bool(_CLOCK_CUE.search(message))
    has_due_date = raw is not None
    if has_due_date and not has_date:
        raise ValueError("A calendar date was not specified for this task change")
    if has_clock and not has_date:
        raise ValueError("Please specify the calendar date as well as the time")
    if has_date and not has_due_date:
        raise ValueError("The requested calendar date is missing from the proposed task change")


def _task_is_modifiable(task) -> bool:
    return not getattr(task, "is_deleted", False) and task.status in (
        StatusEnum.pending,
        StatusEnum.in_progress,
    )


def _parse_priority(raw: object, *, default: str | None = None) -> PriorityEnum | None:
    if raw is None and default is not None:
        raw = default
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError("priority must be low, medium, or high")
    try:
        return PriorityEnum[raw.lower()]
    except KeyError as error:
        raise ValueError("priority must be low, medium, or high") from error


def _check_argument_keys(arguments: dict, allowed: set[str]) -> None:
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object")
    unexpected = set(arguments) - allowed
    if unexpected:
        raise ValueError(f"Unexpected tool argument: {sorted(unexpected)[0]}")


def _due_date_snapshot(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


async def validate_confirmation_tool(
    db: AsyncSession,
    user: User,
    tool_name: str,
    arguments: dict,
    *,
    is_pending: bool = False,
    request_message: str | None = None,
) -> tuple[dict, str] | dict:
    """Validate a proposed action and recheck task ownership before staging confirmation."""
    if tool_name == "update_task":
        allowed = {"task_id", "task_name", "due_date", "priority"}
        if is_pending:
            allowed.update({"_expected_state", "due_date_is_all_day"})
        _check_argument_keys(arguments, allowed)
        if "due_date" not in arguments and "priority" not in arguments:
            raise ValueError("update_task requires a due_date or priority")
        _validate_requested_date(arguments.get("due_date"), request_message)
        task, resolution = await _resolve_task(
            db, user, arguments, open_only=True, for_update=is_pending
        )
        if resolution is not None:
            return resolution
        if task is None or not _task_is_modifiable(task):
            return {"status": "not_found"}
        if is_pending:
            expected = arguments.get("_expected_state")
            actual = {
                "due_date": _due_date_snapshot(task.due_date),
                "due_date_is_all_day": getattr(task, "due_date_is_all_day", None),
                "priority": task.priority.name.lower(),
                "status": task.status.name.lower(),
                "title": task.title,
            }
            if expected != actual:
                return {
                    "status": "stale",
                    "reason": "This task changed after the proposal. Ask me to prepare a fresh update.",
                }

        normalized = {"task_id": str(task.id)}
        summary_parts = []
        if "due_date" in arguments:
            _validate_requested_clock(
                arguments["due_date"], user, request_message
            )
            due_date = _parse_due_date(arguments["due_date"], user)
            if due_date is None:
                raise ValueError("due_date cannot be empty")
            normalized["due_date"] = due_date.isoformat()
            if is_pending:
                all_day = arguments.get("due_date_is_all_day")
                if not isinstance(all_day, bool):
                    raise ValueError("The pending deadline format is invalid")
                normalized["due_date_is_all_day"] = all_day
            else:
                normalized["due_date_is_all_day"] = (
                    len(arguments["due_date"].strip()) == 10
                )
            summary_parts.append(
                f"set its deadline to {arguments['due_date']}"
                + (" (date only)" if normalized["due_date_is_all_day"] else "")
            )
        if "priority" in arguments:
            priority = _parse_priority(arguments["priority"])
            if priority is None:
                raise ValueError("priority cannot be empty")
            normalized["priority"] = priority.name
            summary_parts.append(f"set its priority to {priority.name}")
        if not is_pending:
            normalized["_expected_state"] = {
                "due_date": _due_date_snapshot(task.due_date),
                "due_date_is_all_day": getattr(task, "due_date_is_all_day", None),
                "priority": task.priority.name.lower(),
                "status": task.status.name.lower(),
                "title": task.title,
            }
        return normalized, f'Update "{task.title}": {", ".join(summary_parts)}.'

    if tool_name == "delete_task":
        allowed = {"task_id", "task_name"}
        if is_pending:
            allowed.add("_expected_state")
        _check_argument_keys(arguments, allowed)
        task, resolution = await _resolve_task(
            db, user, arguments, open_only=True, for_update=is_pending
        )
        if resolution is not None:
            return resolution
        if task is None or not _task_is_modifiable(task):
            return {"status": "not_found"}
        if is_pending:
            expected = arguments.get("_expected_state")
            actual = {
                "title": task.title,
                "status": task.status.name.lower(),
            }
            if expected != actual:
                return {
                    "status": "stale",
                    "reason": "This task changed after the proposal. Ask me to prepare a fresh cancellation.",
                }
        normalized = {"task_id": str(task.id)}
        if not is_pending:
            normalized["_expected_state"] = {
                "title": task.title,
                "status": task.status.name.lower(),
            }
        return normalized, f'Cancel "{task.title}"?'

    if tool_name == "create_task":
        # Only reached when creation is forced through confirmation (untrusted context turn).
        _check_argument_keys(
            arguments, {"title", "due_date", "due_date_is_all_day", "priority"}
        )
        title = arguments.get("title")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 300:
            raise ValueError("title must contain between 1 and 300 characters")
        normalized: dict = {"title": title.strip()}
        summary = f'Add task "{title.strip()}"'
        _validate_requested_clock(
            arguments.get("due_date"), user, request_message
        )
        _validate_requested_date(arguments.get("due_date"), request_message)
        due_date = _parse_due_date(arguments.get("due_date"), user)
        if due_date is not None:
            normalized["due_date"] = due_date.isoformat()
            normalized["due_date_is_all_day"] = (
                len(str(arguments.get("due_date", "")).strip()) == 10
            )
            summary += f" due {arguments['due_date']}"
        priority = _parse_priority(arguments.get("priority"), default="medium")
        normalized["priority"] = priority.name
        return normalized, summary + "?"

    return {"status": "error", "reason": f"Unknown tool: {tool_name}"}


async def execute_tool(
    db: AsyncSession,
    user: User,
    tool_name: str,
    arguments: dict,
    *,
    request_message: str | None = None,
) -> dict:
    """Apply a tool mutation without committing; the caller owns the transaction."""
    if tool_name == "create_task":
        _check_argument_keys(
            arguments, {"title", "due_date", "due_date_is_all_day", "priority"}
        )
        title = arguments.get("title")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 300:
            raise ValueError("title must contain between 1 and 300 characters")
        _validate_requested_clock(arguments.get("due_date"), user, request_message)
        _validate_requested_date(arguments.get("due_date"), request_message)
        due_date = _parse_due_date(arguments.get("due_date"), user)
        priority = _parse_priority(arguments.get("priority"), default="medium")
        task = await task_service.create_task(
            db,
            TaskCreate(
                title=title.strip(),
                due_date=due_date,
                due_date_is_all_day=(
                    isinstance(arguments.get("due_date"), str)
                    and len(arguments["due_date"].strip()) == 10
                ),
                priority=priority,
            ),
            user_id=user.id,
            commit=False,
        )
        return {"status": "created", "task_id": str(task.id), "title": task.title}

    if tool_name == "update_task":
        normalized = await validate_confirmation_tool(
            db,
            user,
            tool_name,
            arguments,
            is_pending=True,
            request_message=request_message,
        )
        if isinstance(normalized, dict):
            return normalized
        safe_arguments, _ = normalized
        task_id = _parse_task_id(safe_arguments["task_id"])
        task = await task_service.get_task_by_id(db, task_id, user.id)
        if task is None or not _task_is_modifiable(task):
            return {"status": "error", "reason": "Task not found or not yours"}
        task_data = TaskUpdate(
            **{
                key: value
                for key, value in safe_arguments.items()
                if key not in {"task_id", "_expected_state"}
            }
        )
        updated = await task_service.update_task(
            db, task_id=task.id, user_id=user.id, task_data=task_data, commit=False
        )
        if updated is None:
            return {"status": "error", "reason": "Task not found or not yours"}
        await db.refresh(updated)
        if (
            "due_date" in safe_arguments
            and _due_date_snapshot(updated.due_date)
            != _due_date_snapshot(datetime.fromisoformat(safe_arguments["due_date"]))
        ):
            return {"status": "error", "reason": "The updated deadline could not be verified"}
        if (
            "due_date_is_all_day" in safe_arguments
            and updated.due_date_is_all_day != safe_arguments["due_date_is_all_day"]
        ):
            return {"status": "error", "reason": "The deadline format could not be verified"}
        if (
            "priority" in safe_arguments
            and updated.priority.name.lower() != safe_arguments["priority"].lower()
        ):
            return {"status": "error", "reason": "The updated priority could not be verified"}
        return {"status": "updated", "task_id": str(updated.id), "title": updated.title}

    if tool_name == "delete_task":
        normalized = await validate_confirmation_tool(
            db, user, tool_name, arguments, is_pending=True
        )
        if isinstance(normalized, dict):
            return normalized
        safe_arguments, _ = normalized
        task_id = _parse_task_id(safe_arguments["task_id"])
        task = await task_service.get_task_by_id(db, task_id, user.id)
        if task is None:
            return {"status": "error", "reason": "Task not found or not yours"}
        cancelled = await task_service.cancel_task(
            db, task_id=task.id, user_id=user.id, commit=False
        )
        if cancelled is None:
            return {"status": "error", "reason": "Task not found or not yours"}
        await db.refresh(cancelled)
        if not cancelled.is_deleted:
            return {"status": "error", "reason": "The cancellation could not be verified"}
        return {"status": "cancelled", "task_id": str(cancelled.id), "title": cancelled.title}

    return {"status": "error", "reason": f"Unknown tool: {tool_name}"}
