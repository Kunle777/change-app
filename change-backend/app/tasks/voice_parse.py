import json
import re
import asyncio
from datetime import date, time

from app.ai.gemini import generate_response


def _fallback(transcript: str) -> dict[str, str | None]:
    return {
        "title": transcript.strip()[:100],
        "due_date": None,
        "time": None,
        "priority": "medium",
    }


async def parse_voice_task(transcript: str, today: date | None = None) -> dict[str, str | None]:
    clean_transcript = transcript.strip()
    if not clean_transcript:
        return _fallback("New task")

    prompt = (
        "Extract one task from this spoken request. Reply with only one JSON object with "
        '"title" (short task name), "due_date" (YYYY-MM-DD or null), '
        '"time" (24-hour HH:MM or null), and "priority" (low, medium, or high). '
        "Use null when the user did not give a date or time. Do not guess dates. "
        "Interpret relative dates such as tomorrow using today's date: "
        f"{(today or date.today()).isoformat()}.\nSpoken request: {clean_transcript!r}"
    )

    try:
        raw = (await asyncio.to_thread(generate_response, prompt)).strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return _fallback(clean_transcript)

        title = parsed.get("title")
        title = title.strip()[:100] if isinstance(title, str) and title.strip() else clean_transcript[:100]

        due_date = parsed.get("due_date")
        if isinstance(due_date, str):
            try:
                due_date = date.fromisoformat(due_date).isoformat()
            except ValueError:
                due_date = None
        else:
            due_date = None

        parsed_time = parsed.get("time")
        if isinstance(parsed_time, str):
            try:
                parsed_time = time.fromisoformat(parsed_time).strftime("%H:%M")
            except ValueError:
                parsed_time = None
        else:
            parsed_time = None

        priority = parsed.get("priority")
        if not isinstance(priority, str) or priority.lower() not in {"low", "medium", "high"}:
            priority = "medium"

        return {
            "title": title,
            "due_date": due_date,
            "time": parsed_time,
            "priority": priority.lower(),
        }
    except Exception:
        return _fallback(clean_transcript)
