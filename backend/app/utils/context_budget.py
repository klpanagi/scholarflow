"""Model-aware context budgeting.

Ensures content fits within a model's effective context window,
leaving room for system prompts, instructions, and output.

Key insight: LLM quality degrades significantly past ~50K tokens
even with 1M+ context windows ("lost-in-the-middle" effect).
Strategy: use generous but bounded budgets, prioritizing
head/tail placement for critical content.
"""

import logging

logger = logging.getLogger(__name__)

# Model context window sizes (input tokens)
# These are EFFECTIVE sizes — we use conservative estimates
# because quality degrades before the hard limit.
MODEL_CONTEXT_WINDOWS = {
    # Gemini
    "google/gemini-2.5-flash": 1_048_576,
    "google/gemini-2.5-pro": 1_048_576,
    "google/gemini-2.0-flash": 1_048_576,
    "google/gemma-4-31b-it:free": 131_072,
    # OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-3.5-turbo": 16_385,
    # Anthropic (via OpenRouter)
    "anthropic/claude-sonnet-4": 200_000,
    "anthropic/claude-3.5-sonnet": 200_000,
    "anthropic/claude-3-haiku": 200_000,
    # DeepSeek
    "deepseek/deepseek-chat-v3-0324:free": 128_000,
    "deepseek/deepseek-r1:free": 128_000,
    # Mistral
    "mistralai/mistral-large": 128_000,
    # Meta
    "meta-llama/llama-3.1-405b": 131_072,
    # Qwen
    "qwen/qwen-2.5-72b": 128_000,
    # Cohere
    "cohere/command-r-plus": 128_000,
}

# We never use more than this fraction of the context window for content
# (rest reserved for system prompt + instructions + output)
CONTEXT_UTILIZATION = 0.60

# Absolute maximum content tokens — even large models degrade past this
MAX_CONTENT_TOKENS = 80_000

# Approximate chars per token (conservative estimate)
CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str) -> int:
    """Rough token estimate (chars / 3.5)."""
    return int(len(text) / CHARS_PER_TOKEN)


def get_context_budget(model: str | None = None, output_tokens: int = 4096) -> int:
    """Get the max content tokens for a given model.
    
    Args:
        model: Model identifier (e.g., "google/gemini-2.5-flash")
        output_tokens: Reserved tokens for LLM output
    
    Returns:
        Max tokens available for content (system prompt + input combined)
    """
    window = None
    if model:
        if model in MODEL_CONTEXT_WINDOWS:
            window = MODEL_CONTEXT_WINDOWS[model]
        else:
            for known_model, ctx in MODEL_CONTEXT_WINDOWS.items():
                if model.startswith(known_model):
                    window = ctx
                    logger.debug(f"Prefix-matched model '{model}' -> '{known_model}' ({ctx} tokens)")
                    break

    if window is None:
        window = 128_000
        logger.debug(f"Unknown model '{model}', using default context window of {window}")

    budget = int(window * CONTEXT_UTILIZATION) - output_tokens
    budget = min(budget, MAX_CONTENT_TOKENS)
    budget = max(budget, 4_096)  # absolute minimum

    return budget


def fit_to_budget(text: str, budget_tokens: int, label: str = "content") -> str:
    """Truncate text to fit within a token budget.
    
    Strategy: Keep the beginning (abstract/intro) and end (conclusion/results)
    since these are typically highest-value sections. Drop middle content.
    
    Args:
        text: The text to fit
        budget_tokens: Maximum tokens allowed
        label: Label for logging
    """
    current_tokens = estimate_tokens(text)
    if current_tokens <= budget_tokens:
        return text

    char_budget = int(budget_tokens * CHARS_PER_TOKEN)

    if len(text) <= char_budget:
        return text

    # Keep 60% from start (intro/abstract/methods) + 40% from end (results/conclusion)
    head_size = int(char_budget * 0.60)
    tail_size = char_budget - head_size

    head = text[:head_size]
    tail = text[-tail_size:]

    truncated = f"{head}\n\n[... content trimmed to fit context budget ({label}) ...]\n\n{tail}"

    logger.debug(
        f"Truncated {label}: {current_tokens} → ~{budget_tokens} tokens "
        f"({len(text)} → {len(truncated)} chars)"
    )
    return truncated


def budget_for_stages(
    model: str | None = None,
    system_prompt_tokens: int = 500,
    output_tokens: int = 4096,
) -> dict:
    """Calculate budgets for multi-stage pipelines.
    
    Returns a dict with budgets for different content categories.
    """
    total_budget = get_context_budget(model, output_tokens)
    available = total_budget - system_prompt_tokens

    return {
        "total": total_budget,
        "available": available,
        "paper_content": int(available * 0.60),  # 60% for paper text
        "prior_stages": int(available * 0.30),   # 30% for prior stage outputs
        "instructions": int(available * 0.10),    # 10% for task instructions
    }
