import os

EMBEDDING_MODEL = (
    os.getenv("EMBEDDING_MODEL")
    or os.getenv("GEMINI_EMBEDDING_MODEL")
    or "gemini-embedding-2"
)
EMBEDDING_DIM = 768
