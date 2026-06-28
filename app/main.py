import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.metrics import metrics
from app.models import ChatRequest, ChatResponse, MetricsSummary
from app.router import route

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 {settings.app_name} v{settings.app_version} starting up")
    yield
    logger.info("🛑 Shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "An intelligent LLM routing gateway that selects the optimal model "
        "based on prompt complexity and your chosen strategy (cost / latency / quality)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ──────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration_ms:.0f}ms)"
    )
    return response


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, tags=["Gateway"])
async def chat(request: ChatRequest):
    """
    Route a prompt to the optimal LLM based on complexity and strategy.

    **Strategies:**
    - `auto` (default) — balance cost and latency
    - `cost` — always pick cheapest capable model
    - `latency` — always pick fastest model
    - `quality` — always pick best model regardless of cost
    """
    try:
        response = await route(request)
        metrics.record(
            model=response.attempt_model,
            provider=response.provider,
            latency_ms=response.latency_ms,
            cost_usd=response.usage.estimated_cost_usd,
            fallback_used=response.fallback_used,
        )
        return response

    except RuntimeError as e:
        logger.error(f"All providers failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/metrics", response_model=MetricsSummary, tags=["Observability"])
async def get_metrics():
    """Aggregate usage stats: cost, latency, model distribution, fallbacks."""
    return metrics.summary()


@app.post("/metrics/reset", tags=["Observability"])
async def reset_metrics():
    """Reset all metrics counters."""
    metrics.reset()
    return {"message": "Metrics reset"}


@app.get("/models", tags=["Info"])
async def list_models():
    """List all available models and their pricing."""
    from app.providers.openai_provider import OPENAI_MODELS
    from app.providers.anthropic import ANTHROPIC_MODELS

    all_models = {**OPENAI_MODELS, **ANTHROPIC_MODELS}
    return {
        name: {
            "provider": m.provider,
            "cost_per_1k_input_usd": m.cost_per_1k_input,
            "cost_per_1k_output_usd": m.cost_per_1k_output,
        }
        for name, m in all_models.items()
    }


# ── Error handlers ───────────────────────────────────────────────────────────

@app.exception_handler(404)
async def not_found(request: Request, exc):
    return JSONResponse(status_code=404, content={"detail": "Route not found"})


@app.exception_handler(500)
async def server_error(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
