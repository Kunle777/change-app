import asyncio
import math

from google.genai import types

from app.ai.gemini import get_client
from app.memory.config import EMBEDDING_DIM, EMBEDDING_MODEL


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vec))
    return [value / norm for value in vec] if norm > 0 else vec


async def embed_texts(texts: list[str], *, task_type: str) -> list[list[float]]:
    """Embed documents or queries using Gemini's corresponding retrieval task."""
    if not texts:
        return []
    if task_type not in {"RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"}:
        raise ValueError(f"Unsupported embedding task type: {task_type}")

    client = get_client()
    semaphore = asyncio.Semaphore(5)

    async def embed_one(content: str) -> list[float]:
        async with semaphore:
            result = await client.aio.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=content,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=EMBEDDING_DIM,
                ),
            )
        if result.embeddings is None or len(result.embeddings) != 1:
            count = 0 if result.embeddings is None else len(result.embeddings)
            raise ValueError(f"Expected one embedding for one input, got {count}")
        values = result.embeddings[0].values
        if values is None:
            raise ValueError("Embedding response did not include vector values")
        vector = [float(value) for value in values]
        if len(vector) != EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension mismatch: expected {EMBEDDING_DIM}, got {len(vector)}"
            )
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("Embedding response contained a non-finite value")
        return _normalize(vector)

    return await asyncio.gather(*(embed_one(content) for content in texts))
