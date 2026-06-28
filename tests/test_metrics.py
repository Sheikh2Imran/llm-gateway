"""Tests for the metrics store."""

import pytest
from app.metrics import MetricsStore


def make_store():
    return MetricsStore()


def test_initial_state():
    store = make_store()
    summary = store.summary()
    assert summary["total_requests"] == 0
    assert summary["total_cost_usd"] == 0.0
    assert summary["fallback_count"] == 0


def test_record_increments_counts():
    store = make_store()
    store.record("gpt-4o-mini", "openai", 200.0, 0.0001, False)
    store.record("claude-haiku-4-5-20251001", "anthropic", 150.0, 0.0002, True)

    summary = store.summary()
    assert summary["total_requests"] == 2
    assert summary["fallback_count"] == 1
    assert summary["model_usage"]["gpt-4o-mini"] == 1
    assert summary["model_usage"]["claude-haiku-4-5-20251001"] == 1
    assert summary["provider_usage"]["openai"] == 1
    assert summary["provider_usage"]["anthropic"] == 1


def test_avg_latency():
    store = make_store()
    store.record("gpt-4o-mini", "openai", 100.0, 0.0, False)
    store.record("gpt-4o-mini", "openai", 300.0, 0.0, False)
    assert store.summary()["avg_latency_ms"] == 200.0


def test_reset():
    store = make_store()
    store.record("gpt-4o-mini", "openai", 200.0, 0.001, False)
    store.reset()
    summary = store.summary()
    assert summary["total_requests"] == 0
    assert summary["total_cost_usd"] == 0.0
