"""Tests for routing table and model selection (no API calls)."""

import pytest
from unittest.mock import AsyncMock, patch
from app.models import ChatRequest, RoutingStrategy
from app.router import route, ROUTING_TABLE
from app.scorer import Complexity


def test_routing_table_completeness():
    """Every strategy+complexity combo should have a route."""
    strategies = [RoutingStrategy.AUTO, RoutingStrategy.COST, RoutingStrategy.LATENCY, RoutingStrategy.QUALITY]
    complexities = [Complexity.LOW, Complexity.MEDIUM, Complexity.HIGH]
    for s in strategies:
        for c in complexities:
            assert (s, c) in ROUTING_TABLE, f"Missing route for ({s}, {c})"


def test_routing_table_providers():
    """All routes should point to valid providers."""
    valid_providers = {"openai", "anthropic"}
    for key, (provider, model) in ROUTING_TABLE.items():
        assert provider in valid_providers, f"Invalid provider {provider} for {key}"


@pytest.mark.asyncio
async def test_route_calls_correct_model_for_low_cost():
    request = ChatRequest(prompt="What is Python?", strategy=RoutingStrategy.COST)

    mock_response = ("Python is a programming language.", None, 200.0)

    with patch("app.router._call_provider", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_response[0], \
            type("U", (), {"input_tokens": 10, "output_tokens": 20, "estimated_cost_usd": 0.0001})(), \
            mock_response[2]

        response = await route(request)
        # Low complexity + cost → cheapest model (haiku or gpt-4o-mini)
        assert response.model_used in ("claude-haiku-4-5-20251001", "gpt-4o-mini")
        assert response.fallback_used is False


@pytest.mark.asyncio
async def test_fallback_triggered_on_failure():
    request = ChatRequest(prompt="What is 2+2?", strategy=RoutingStrategy.AUTO)

    call_count = 0

    async def mock_call(provider, model, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Primary model failed")
        from app.models import UsageInfo
        usage = UsageInfo(input_tokens=5, output_tokens=5, estimated_cost_usd=0.00001)
        return "4", usage, 150.0

    with patch("app.router._call_provider", side_effect=mock_call):
        response = await route(request)
        assert response.fallback_used is True
        assert call_count >= 2


@pytest.mark.asyncio
async def test_force_model_override():
    request = ChatRequest(
        prompt="Hello",
        strategy=RoutingStrategy.AUTO,
        force_model="gpt-4o",
    )

    async def mock_call(provider, model, **kwargs):
        from app.models import UsageInfo
        usage = UsageInfo(input_tokens=5, output_tokens=5, estimated_cost_usd=0.001)
        return "Hello!", usage, 100.0

    with patch("app.router._call_provider", side_effect=mock_call):
        response = await route(request)
        assert response.model_used == "gpt-4o"
        assert "Forced" in response.routing_reason
