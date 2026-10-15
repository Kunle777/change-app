# app/memory/__init__.py   (empty file)

# app/memory/config.py
import os

# Model name comes from the environment. It must stay pinned once vectors exist.
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")

# Dimension is a SCHEMA decision (it sizes the column), so it is a constant, not an env var.
EMBEDDING_DIM = 768