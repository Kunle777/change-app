import re


_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def chunk_text(text: str, *, max_chars: int = 900, overlap_chars: int = 120) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be between zero and max_chars")

    normalized = (text or "").strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    pieces: list[str] = []
    for sentence in _SPLIT.split(normalized):
        sentence = sentence.strip()
        while len(sentence) > max_chars:
            pieces.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        if sentence:
            pieces.append(sentence)

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current} {piece}".strip() if current else piece
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
        tail = current[-overlap_chars:] if overlap_chars else ""
        if " " in tail:
            tail = tail.split(" ", 1)[1]
        current = f"{tail} {piece}".strip()
        if len(current) > max_chars:
            current = piece

    if current:
        chunks.append(current)
    return chunks
