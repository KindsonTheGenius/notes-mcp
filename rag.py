"""
RAG helper for notes-mcp — copy into notes-mcp/rag.py during filming.

Requires: openai, python-dotenv
Set DOCS_DIR in notes-mcp/.env to the absolute path of the markdown folder.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# override=True so an empty inherited OPENAI_API_KEY (common in IDE shells)
# cannot block the value from notes-mcp/.env.
load_dotenv(Path(__file__).with_name(".env"), override=True)

DOCS_DIR = Path(os.getenv("DOCS_DIR"))
EMBED_MODEL = "text-embedding-3-small"

# Cache: list of {"source", "text", "embedding"}
_CHUNKS: list[dict] | None = None


def _client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")
    return OpenAI(api_key=key)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _chunk_markdown(text: str, source: str) -> list[dict]:
    """Split on blank lines / headings into small passages."""
    parts: list[str] = []
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") and buf:
            parts.append("\n".join(buf).strip())
            buf = [line]
        elif not line.strip() and buf:
            parts.append("\n".join(buf).strip())
            buf = []
        else:
            buf.append(line)
    if buf:
        parts.append("\n".join(buf).strip())
    return [{"source": source, "text": p} for p in parts if p]


def _embed_texts(texts: list[str]) -> list[list[float]]:
    client = _client()
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    # API returns in input order
    return [item.embedding for item in resp.data]


def _ensure_index() -> list[dict]:
    global _CHUNKS
    if _CHUNKS is not None:
        return _CHUNKS

    if not DOCS_DIR.exists():
        raise RuntimeError(f"No docs folder at {DOCS_DIR}")

    raw: list[dict] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        raw.extend(_chunk_markdown(path.read_text(encoding="utf-8"), path.name))

    if not raw:
        raise RuntimeError(f"No .md files in {DOCS_DIR}")

    vectors = _embed_texts([c["text"] for c in raw])
    for chunk, vec in zip(raw, vectors):
        chunk["embedding"] = vec

    _CHUNKS = raw
    return _CHUNKS


def retrieve(query: str, top_k: int = 3) -> str:
    """Return the top_k most similar doc chunks for a query."""
    chunks = _ensure_index()
    q_vec = _embed_texts([query])[0]
    ranked = sorted(
        chunks,
        key=lambda c: _cosine(q_vec, c["embedding"]),
        reverse=True,
    )[: max(1, top_k)]

    blocks = []
    for i, c in enumerate(ranked, 1):
        score = _cosine(q_vec, c["embedding"])
        blocks.append(
            f"[{i}] source={c['source']} score={score:.3f}\n{c['text']}"
        )
    return "\n\n---\n\n".join(blocks)

