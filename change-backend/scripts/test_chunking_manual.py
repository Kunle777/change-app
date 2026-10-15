from app.memory.chunking import chunk_text

text = (
    "I am worried about my upcoming software engineering interview. "
    "I need to prepare for architecture questions and review my FastAPI code. "
    "I have also been struggling to complete my portfolio. "
    "Sometimes I feel overwhelmed because there are so many things to do. "
) * 8

chunks = chunk_text(
    text,
    max_chars=300,
    overlap_chars=50,
)

print(f"Original length: {len(text)}")
print(f"Number of chunks: {len(chunks)}")

for index, chunk in enumerate(chunks):
    print(f"\n--- CHUNK {index} ({len(chunk)} chars) ---")
    print(chunk)

assert chunks
assert all(len(chunk) <= 300 for chunk in chunks)
