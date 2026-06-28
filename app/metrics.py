"""
metrics.py — In-memory metrics store.
For production, swap this out for CloudWatch / Prometheus / Datadog.
"""

from collections import defaultdict
from threading import Lock


class MetricsStore:
    def __init__(self):
        self.total_requests: int = 0
        self.total_cost_usd: float = 0.0
        self.total_latency_ms: float = 0.0
        self.fallback_count: int = 0
        self.attempt_model: dict = defaultdict(int)
        self.provider_usage: dict = defaultdict(int)
        self._lock = Lock()

    def record(
        self,
        model: str,
        provider: str,
        latency_ms: float,
        cost_usd: float,
        fallback_used: bool,
    ) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_cost_usd += cost_usd
            self.total_latency_ms += latency_ms
            self.attempt_model[model] += 1
            self.provider_usage[provider] += 1
            if fallback_used:
                self.fallback_count += 1

    def summary(self) -> dict:
        with self._lock:
            avg_latency = (
                self.total_latency_ms / self.total_requests
                if self.total_requests > 0
                else 0.0
            )
            return {
                "total_requests": self.total_requests,
                "total_cost_usd": round(self.total_cost_usd, 6),
                "avg_latency_ms": round(avg_latency, 2),
                "attempt_model": dict(self.attempt_model),
                "provider_usage": dict(self.provider_usage),
                "fallback_count": self.fallback_count,
            }

    def reset(self) -> None:
        with self._lock:
            self.total_requests = 0
            self.total_cost_usd = 0.0
            self.total_latency_ms = 0.0
            self.fallback_count = 0
            self.attempt_model = defaultdict(int)
            self.provider_usage = defaultdict(int)


# Singleton
metrics = MetricsStore()