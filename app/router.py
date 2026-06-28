import logging
from typing import Optional
from app.models import ChatRequest, ChatResponse, RoutingStrategy
from app.scorer import score_complexity, Complexity
from app.providers.openai_provider import call_openai
from app.providers.anthropic import call_anthropic
from app.config import get_settings

logger = logging.getLogger(__name__)

# (provider, model) tuples
ROUTING_TABLE: dict[tuple[RoutingStrategy, Complexity], tuple[str, str]] = {
    # AUTO / COST — cheapest that can handle it
    (RoutingStrategy.AUTO,    Complexity.LOW):    ("anthropic", "claude-haiku-4-5-20251001"),
    (RoutingStrategy.AUTO,    Complexity.MEDIUM): ("openai",    "gpt-4o-mini"),
    (RoutingStrategy.AUTO,    Complexity.HIGH):   ("anthropic", "claude-sonnet-4-6"),
    (RoutingStrategy.COST,    Complexity.LOW):    ("anthropic", "claude-haiku-4-5-20251001"),
    (RoutingStrategy.COST,    Complexity.MEDIUM): ("openai",    "gpt-4o-mini"),
    (RoutingStrategy.COST,    Complexity.HIGH):   ("anthropic", "claude-sonnet-4-6"),
    # LATENCY — fastest first
    (RoutingStrategy.LATENCY, Complexity.LOW):    ("openai",    "gpt-4o-mini"),
    (RoutingStrategy.LATENCY, Complexity.MEDIUM): ("anthropic", "claude-haiku-4-5-20251001"),
    (RoutingStrategy.LATENCY, Complexity.HIGH):   ("openai",    "gpt-4o"),
    # QUALITY — best available
    (RoutingStrategy.QUALITY, Complexity.LOW):    ("openai",    "gpt-4o"),
    (RoutingStrategy.QUALITY, Complexity.MEDIUM): ("anthropic", "claude-sonnet-4-6"),
    (RoutingStrategy.QUALITY, Complexity.HIGH):   ("openai",    "gpt-4o"),
}

# Fallback chains: primary → list of (provider, model) to try next
FALLBACK_CHAINS: dict[str, list[tuple[str, str]]] = {
    "claude-haiku-4-5-20251001": [("openai", "gpt-4o-mini"), ("anthropic", "claude-sonnet-4-6")],
    "gpt-4o-mini":          [("anthropic", "claude-haiku-4-5-20251001"), ("openai", "gpt-4o")],
    "claude-sonnet-4-6":    [("openai", "gpt-4o")],
    "gpt-4o":               [("anthropic", "claude-sonnet-4-6")],
}


async def _call_provider(
    provider: str,
    model: str,
    prompt: str,
    max_tokens: int,
    system_prompt: str,
):
    settings = get_settings()
    if provider == "openai":
        return await call_openai(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            api_key=settings.openai_api_key,
        )
    elif provider == "anthropic":
        return await call_anthropic(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            api_key=settings.anthropic_api_key,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


async def route(request: ChatRequest) -> ChatResponse:
    # Score prompt complexity
    complexity, score_reason = score_complexity(
        request.prompt, request.system_prompt or ""
    )

    system_prompt = request.system_prompt or "You are a helpful assistant."

    # Determine target model
    if request.force_model:
        # Manual override: try to figure out provider from model name
        model = request.force_model
        provider = "anthropic" if "claude" in model else "openai"
        routing_reason = f"Forced model override: {model}"
    else:
        provider, model = ROUTING_TABLE.get(
            (request.strategy, complexity),
            ("openai", "gpt-4o-mini"),  # safe default
        )
        routing_reason = (
            f"Strategy={request.strategy}, Complexity={complexity} → {model}. "
            f"Scorer: {score_reason}"
        )

    logger.info(f"Routing to {provider}/{model} | {routing_reason}")

    # Try primary model, then fallback chain
    fallback_used = False
    candidates = [(provider, model)] + FALLBACK_CHAINS.get(model, [])

    last_error: Optional[Exception] = None
    for attempt_provider, attempt_model in candidates:
        try:
            content, usage, latency_ms = await _call_provider(
                provider=attempt_provider,
                model=attempt_model,
                prompt=request.prompt,
                max_tokens=request.max_tokens,
                system_prompt=system_prompt,
            )
            if attempt_model != model:
                fallback_used = True
                routing_reason += f" | Fallback to {attempt_model}"

            return ChatResponse(
                content=content,
                attempt_model=attempt_model,
                provider=attempt_provider,
                strategy_used=request.strategy,
                latency_ms=round(latency_ms, 2),
                usage=usage,
                routing_reason=routing_reason,
                fallback_used=fallback_used,
            )
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt failed ({attempt_provider}/{attempt_model}): {e}")
            continue

    # All candidates failed
    raise RuntimeError(
        f"All models failed. Last error: {last_error}"
    )
