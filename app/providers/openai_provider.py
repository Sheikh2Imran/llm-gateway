"""
Models used:
  - gpt-4o-mini  → cheap, fast  (LOW/MEDIUM complexity)
  - gpt-4o       → powerful     (HIGH complexity)
"""

import time
import logging
from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError
from app.models import ModelInfo, UsageInfo

logger = logging.getLogger(__name__)

# Pricing as of mid-2024 (USD per 1K tokens)
OPENAI_MODELS: dict[str, ModelInfo] = {
    "gpt-4o-mini": ModelInfo(
        provider="openai",
        model="gpt-4o-mini",
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.00060,
    ),
    "gpt-4o": ModelInfo(
        provider="openai",
        model="gpt-4o",
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
    ),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    info = OPENAI_MODELS.get(model)
    if not info:
        return 0.0
    return (input_tokens / 1000 * info.cost_per_1k_input) + (
        output_tokens / 1000 * info.cost_per_1k_output
    )


async def call_openai(
    prompt: str,
    model: str,
    max_tokens: int = 1000,
    system_prompt: str = "You are a helpful assistant.",
    api_key: str = "",
) -> tuple[str, UsageInfo, float]:
    """
    Returns (content, UsageInfo, latency_ms).
    Raises on failure so router can trigger fallback.
    """
    client = AsyncOpenAI(api_key=api_key)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    start = time.perf_counter()
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
    except (RateLimitError, APITimeoutError, APIError) as e:
        logger.warning(f"OpenAI {model} failed: {e}")
        raise

    latency_ms = (time.perf_counter() - start) * 1000
    content = response.choices[0].message.content or ""

    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    cost = _estimate_cost(model, input_tokens, output_tokens)

    usage = UsageInfo(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=round(cost, 6),
    )

    logger.info(
        f"OpenAI {model} | {input_tokens}+{output_tokens} tokens "
        f"| ${cost:.6f} | {latency_ms:.0f}ms"
    )
    return content, usage, latency_ms
