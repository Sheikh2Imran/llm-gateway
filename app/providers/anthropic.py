"""
Models used:
  - claude-haiku-4-5  → cheap, fast  (LOW/MEDIUM complexity)
  - claude-sonnet-4-6 → powerful     (HIGH complexity)
"""

import time
import logging
import anthropic as anthropic_sdk
from app.models import ModelInfo, UsageInfo

logger = logging.getLogger(__name__)

# Pricing (USD per 1K tokens)
ANTHROPIC_MODELS: dict[str, ModelInfo] = {
    "claude-haiku-4-5-20251001": ModelInfo(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
    ),
    "claude-sonnet-4-6": ModelInfo(
        provider="anthropic",
        model="claude-sonnet-4-6",
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
    ),
}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    info = ANTHROPIC_MODELS.get(model)
    if not info:
        return 0.0
    return (input_tokens / 1000 * info.cost_per_1k_input) + (
        output_tokens / 1000 * info.cost_per_1k_output
    )


async def call_anthropic(
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
    client = anthropic_sdk.AsyncAnthropic(api_key=api_key)

    start = time.perf_counter()
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
    except (anthropic_sdk.RateLimitError, anthropic_sdk.APITimeoutError, anthropic_sdk.APIError) as e:
        logger.warning(f"Anthropic {model} failed: {e}")
        raise

    latency_ms = (time.perf_counter() - start) * 1000
    content = response.content[0].text if response.content else ""

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost = _estimate_cost(model, input_tokens, output_tokens)

    usage = UsageInfo(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=round(cost, 6),
    )

    logger.info(
        f"Anthropic {model} | {input_tokens}+{output_tokens} tokens "
        f"| ${cost:.6f} | {latency_ms:.0f}ms"
    )
    return content, usage, latency_ms
