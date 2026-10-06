import os
from google import genai
import json
from google.genai import types # type: ignore


_client: genai.Client | None = None


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