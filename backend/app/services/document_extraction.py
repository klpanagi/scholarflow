"""Text extraction + chunking for uploaded chat files."""

import logging
from typing import Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Chunk size in words (same as asset_tasks.py)
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF using PyMuPDF."""
    doc = fitz.open(stream=content, filetype="pdf")
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages)


def extract_text_from_txt(content: bytes) -> str:
    """Extract text from a plain-text file."""
    return content.decode("utf-8", errors="replace")


def extract_text(content: bytes, filename: str) -> Optional[str]:
    """Extract text from an uploaded file based on extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return extract_text_from_pdf(content)
    elif ext in ("txt", "md", "csv"):
        return extract_text_from_txt(content)
    else:
        logger.warning("Unsupported file extension '%s' for %s", ext, filename)
        return None


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into word-based chunks with overlap.

    Returns a list of chunk strings (not dicts) suitable for injection into LLM context.
    """
    words = text.split()
    if not words:
        return []
    if len(words) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_text = " ".join(words[start:end])
        chunks.append(chunk_text)
        if end >= len(words):
            break
        start = end - overlap
    return chunks


def count_tokens(text: str) -> int:
    """Estimate token count using tiktoken cl100k_base encoding."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Fallback: ~1.3 tokens per word
        return int(len(text.split()) * 1.3)
