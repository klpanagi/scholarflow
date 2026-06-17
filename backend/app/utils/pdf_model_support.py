import base64
from typing import Optional

from langchain_core.messages import HumanMessage

PDF_SUPPORTING_MODELS: list[str] = [
    # OpenAI
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-11-20",
    "gpt-4o-mini-2024-07-18",
    # Anthropic (via OpenRouter)
    "claude-3-5-sonnet",
    "claude-3-5-haiku",
    "claude-3-opus",
    "claude-3-sonnet",
    "claude-3-haiku",
    "anthropic/claude-3.5-sonnet",
    "anthropic/claude-3-5-sonnet",
    "anthropic/claude-3-opus",
    "anthropic/claude-3-sonnet",
    "anthropic/claude-3-haiku",
    "anthropic/claude-3.5-haiku",
    # Google (via OpenRouter)
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "google/gemini-1.5-pro",
    "google/gemini-1.5-flash",
    "google/gemini-2.0-flash",
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
]


def model_supports_pdf(model: str) -> bool:
    model_lower = model.lower()
    for pattern in PDF_SUPPORTING_MODELS:
        if pattern.lower() in model_lower:
            return True
    return False


def extract_text_from_message_content(content: str | list) -> str:
    """Extract plain text from message content (handles both string and multimodal list)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(parts)
    return str(content)


def create_multimodal_human_message(
    pdf_bytes: Optional[bytes],
    text_content: str,
    instruction: str = "",
) -> HumanMessage:
    """Create a HumanMessage with PDF if available, otherwise text-only."""
    if pdf_bytes:
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
        text_parts: list[str | dict] = []
        if instruction:
            text_parts.append({"type": "text", "text": instruction})
        text_parts.append({"type": "text", "text": text_content})
        text_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:application/pdf;base64,{pdf_b64}"},
        })
        return HumanMessage(content=text_parts)
    else:
        full_text = f"{instruction}\n\n{text_content}" if instruction else text_content
        return HumanMessage(content=full_text)
