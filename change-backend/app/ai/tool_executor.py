import uuid
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.tasks import service as task_service
from app.tasks.models import PriorityEnum
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
) -> tuple[dict, str] | dict:
    """Validate a proposed action and recheck task ownership before staging confirmation."""
    if tool_name == "update_task":
        allowed = {"task_id", "due_date", "priority"}
        if is_pending:
            allowed.add("_expected_state")
        _check_argument_keys(arguments, allowed)
        task_id = _parse_task_id(arguments.get("task_id"))
        if "due_date" not in arguments and "priority" not in arguments:
            raise ValueError("update_task requires a due_date or priority")
        task = await task_service.get_task_by_id(
            db, task_id, user.id, for_update=is_pending
        )
        if task is None:
            return {"status": "error", "reason": "Task not found or not yours"}
        if is_pending:
            expected = arguments.get("_expected_state")
            actual = {
                "due_date": _due_date_snapshot(task.due_date),
                "priority": task.priority.name.lower(),
            }
            if expected != actual:
                return {
                    "status": "stale",
                    "reason": "This task changed after the proposal. Ask me to prepare a fresh update.",
                }

        normalized = {"task_id": str(task.id)}
        summary_parts = []
        if "due_date" in arguments:
            due_date = _parse_due_date(arguments["due_date"], user)
            if due_date is None:
                raise ValueError("due_date cannot be empty")
            normalized["due_date"] = due_date.isoformat()
            summary_parts.append(f"set its due date to {arguments['due_date']}")
        if "priority" in arguments:
            priority = _parse_priority(arguments["priority"])
            if priority is None:
                raise ValueError("priority cannot be empty")
            normalized["priority"] = priority.name
            summary_parts.append(f"set its priority to {priority.name}")
        if not is_pending:
            normalized["_expected_state"] = {
                "due_date": _due_date_snapshot(task.due_date),
                "priority": task.priority.name.lower(),
            }
        return normalized, f'Update "{task.title}": {", ".join(summary_parts)}.'

    if tool_name == "delete_task":
        _check_argument_keys(arguments, {"task_id"})
        task_id = _parse_task_id(arguments.get("task_id"))
        task = await task_service.get_task_by_id(db, task_id, user.id)
        if task is None:
            return {"status": "error", "reason": "Task not found or not yours"}
        return {"task_id": str(task.id)}, f'Cancel "{task.title}"?'

    return {"status": "error", "reason": f"Unknown tool: {tool_name}"}


async def execute_tool(
    db: AsyncSession,
    user: User,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Apply a tool mutation without committing; the caller owns the transaction."""
    if tool_name == "create_task":
        _check_argument_keys(arguments, {"title", "due_date", "priority"})
        title = arguments.get("title")
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 300:
            raise ValueError("title must contain between 1 and 300 characters")
        due_date = _parse_due_date(arguments.get("due_date"), user)
        priority = _parse_priority(arguments.get("priority"), default="medium")
        task = await task_service.create_task(
            db,
            TaskCreate(title=title.strip(), due_date=due_date, priority=priority),
            user_id=user.id,
            commit=False,
        )
        return {"status": "created", "task_id": str(task.id), "title": task.title}

    if tool_name == "update_task":
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
        return {"status": "updated", "task_id": str(updated.id), "title": updated.title}

    if tool_name == "delete_task":
        _check_argument_keys(arguments, {"task_id"})
        task_id = _parse_task_id(arguments.get("task_id"))
        task = await task_service.get_task_by_id(db, task_id, user.id)
        if task is None:
            return {"status": "error", "reason": "Task not found or not yours"}
        cancelled = await task_service.cancel_task(
            db, task_id=task.id, user_id=user.id, commit=False
        )
        if cancelled is None:
            return {"status": "error", "reason": "Task not found or not yours"}
        return {"status": "cancelled", "task_id": str(cancelled.id), "title": cancelled.title}

    return {"status": "error", "reason": f"Unknown tool: {tool_name}"}
