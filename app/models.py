from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class RoutingStrategy(str, Enum):
    COST = "cost"
    LATENCY = "latency"
    QUALITY = "quality"
    AUTO = "auto"  # default: balance cost + latency


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000)
    strategy: RoutingStrategy = RoutingStrategy.AUTO
    max_tokens: int = Field(default=1000, ge=1, le=4096)
    system_prompt: Optional[str] = None
    force_model: Optional[str] = None  # override routing, e.g. "gpt-4o"


class ModelInfo(BaseModel):
    provider: str
    model: str
    cost_per_1k_input: float   # USD
    cost_per_1k_output: float  # USD
    avg_latency_ms: Optional[float] = None


class UsageInfo(BaseModel):
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class ChatResponse(BaseModel):
    content: str
    attempt_model: str
    provider: str
    strategy_used: RoutingStrategy
    latency_ms: float
    usage: UsageInfo
    routing_reason: str
    fallback_used: bool = False


class MetricsSummary(BaseModel):
    total_requests: int
    total_cost_usd: float
    avg_latency_ms: float
    attempt_model: dict[str, int]
    provider_usage: dict[str, int]
    fallback_count: int