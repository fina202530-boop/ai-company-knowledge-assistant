CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def chunk_text(text: str) -> list[str]:
    normalized_text = " ".join(text.split())
    chunks: list[str] = []
    start = 0

    while start < len(normalized_text):
        end = min(start + CHUNK_SIZE, len(normalized_text))
        if end < len(normalized_text):
            boundary = normalized_text.rfind(" ", start, end)
            if boundary > start:
                end = boundary

        chunk = normalized_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == len(normalized_text):
            break

        next_start = max(start + 1, end - CHUNK_OVERLAP)
        overlap_boundary = normalized_text.find(" ", next_start, end)
        if overlap_boundary != -1:
            next_start = overlap_boundary + 1
        start = next_start

    return chunks
