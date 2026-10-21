import os
from google import genai
import json
from google.genai import types # type: ignore


_client: genai.Client | None = None


CREATE_TASK_TOOL = types.FunctionDeclaration(
    name="create_task",
    description=(
        "Create a task when the user clearly asks to add, schedule, or remember something. "
        "This action executes immediately."
    ),
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "title": types.Schema(type="STRING"),
            "due_date": types.Schema(
                type="STRING",
                description="ISO 8601 date or date-time. Omit if the user did not specify a date.",
            ),
            "priority": types.Schema(type="STRING", enum=["low", "medium", "high"]),
        },
        required=["title"],
    ),
)

UPDATE_TASK_TOOL = types.FunctionDeclaration(
    name="update_task",
    description=(
        "Propose changing an existing task's due date or priority. task_id must be copied "
        "exactly from a task in the provided context; never invent one. This requires confirmation."
    ),
    parameters=types.Schema(
        type="OBJECT",
        properties={
            "task_id": types.Schema(type="STRING"),
            "due_date": types.Schema(type="STRING", description="ISO 8601 date or date-time."),
            "priority": types.Schema(type="STRING", enum=["low", "medium", "high"]),
        },
        required=["task_id"],
    ),
)

DELETE_TASK_TOOL = types.FunctionDeclaration(
    name="delete_task",
    description=(
        "Propose cancelling a task the user no longer wants. task_id must be copied exactly "
        "from a task in the provided context; never invent one. This requires confirmation."
    ),
    parameters=types.Schema(
        type="OBJECT",
        properties={"task_id": types.Schema(type="STRING")},
        required=["task_id"],
    ),
)

TASK_TOOLS = types.Tool(
    function_declarations=[CREATE_TASK_TOOL, UPDATE_TASK_TOOL, DELETE_TASK_TOOL]
)


def get_client() -> genai.Client:
    """Lazily create a single reused Gemini client instead of one per call."""
    global _client
    if _client is None:
        api_key = os.environ["GEMINI_API_KEY"]
        _client = genai.Client(api_key=api_key)
    return _client


def generate_response(prompt: str) -> str:
    """
    Sends a single prompt to Gemini and returns the text response.
    No memory, no context — that's built by whoever calls this,
    per the RAG design (retrieve -> augment -> generate -> store).
    """
    client = get_client()
    model_name = os.environ["GEMINI_MODEL"]

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
    )
    return response.text




def generate_structured(prompt: str) -> list[str]:
    """
    Sends a prompt instructing Gemini to return ONLY a JSON array of strings.
    Returns a parsed Python list. Raises ValueError if the model's output
    isn't valid JSON — never trust the model blindly.
    """
    client = get_client()
    model_name = os.environ["GEMINI_MODEL"]

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    try:
        steps = json.loads(response.text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned invalid JSON: {e}")

    if not isinstance(steps, list):
        raise ValueError("Expected a JSON array of steps")

    return steps


def generate_chat_response_with_tools(
    system_prompt: str, history, new_message: str, *, allow_tools: bool = True
) -> dict:
    """Return one model response and at most one manually handled tool call."""
    gemini_history = []
    for turn in history:
        gemini_history.extend(
            (
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=turn["question"])],
                ),
                types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=turn["response"])],
                ),
            )
        )
    config_kwargs = {"system_instruction": system_prompt}
    if allow_tools:
        config_kwargs["tools"] = [TASK_TOOLS]
    chat = get_client().chats.create(
        model=os.environ["GEMINI_MODEL"],
        history=gemini_history,
        config=types.GenerateContentConfig(**config_kwargs),
    )
    response = chat.send_message(new_message)
    function_calls = response.function_calls or []
    if not function_calls:
        return {"text": response.text or "I couldn't finish that response.", "tool_call": None}

    function_call = function_calls[0]
    if not function_call.name:
        return {"text": response.text or "I couldn't understand that task action.", "tool_call": None}
    return {
        "text": None,
        "tool_call": {
            "name": function_call.name,
            "args": dict(function_call.args or {}),
        },
        "chat": chat,
    }


def send_tool_result(chat, tool_name: str, result: dict) -> str:
    function_response = types.Part.from_function_response(
        name=tool_name,
        response=result,
    )
    response = chat.send_message(types.Content(role="tool", parts=[function_response]))
    if response.function_calls:
        return "I can handle one task change per message. Please send the next change separately."
    return response.text or "I completed the task request."
