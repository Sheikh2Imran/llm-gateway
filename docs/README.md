# LLM Gateway

An intelligent routing gateway that sends each prompt to the **optimal LLM** based on complexity and your chosen strategy — minimizing cost and latency without sacrificing quality.

```
Client → FastAPI Gateway → Complexity Scorer → Router → OpenAI / Anthropic
                                                      ↓
                                               Fallback chain if primary fails
                                                      ↓
                                          Response + cost + latency metadata
```

---

## Features

- **Smart routing** — classifies prompt complexity (LOW / MEDIUM / HIGH) in <1ms using regex + token estimation
- **Four strategies** — `auto`, `cost`, `latency`, `quality`
- **Automatic fallback** — if the primary model fails, retries down a fallback chain across providers
- **Cost tracking** — every response includes token usage and estimated USD cost
- **Aggregate metrics** — `/metrics` endpoint shows total cost, avg latency, model distribution
- **Force override** — pass `force_model` to bypass routing for specific requests
- **Dockerized** — runs locally with one command; deploys to ECS Fargate via GitHub Actions

---

## Routing Table

| Complexity | AUTO / COST | LATENCY | QUALITY |
|---|---|---|---|
| LOW | claude-haiku-4-5 | gpt-4o-mini | gpt-4o |
| MEDIUM | gpt-4o-mini | claude-haiku-4-5 | claude-sonnet-4-6 |
| HIGH | claude-sonnet-4-6 | gpt-4o | gpt-4o |

---

## Quick Start

### 1. Clone & configure

```bash
git clone https://github.com/YOUR_USERNAME/llm-gateway
cd llm-gateway
cp ..env.example ..env
# Edit ..env and add your API keys
```

### 2. Run locally (Docker)

```bash
docker-compose up
```

API is live at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### 3. Run locally (Python)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## API Reference

### `POST /chat`

Route a prompt to the optimal model.

**Request:**
```json
{
  "prompt": "Write a Python function to binary search a list.",
  "strategy": "cost",
  "max_tokens": 1000,
  "system_prompt": "You are an expert Python developer."
}
```

**Strategies:** `auto` (default) | `cost` | `latency` | `quality`

**Response:**
```json
{
  "content": "def binary_search(arr, target): ...",
  "model_used": "claude-sonnet-4-6",
  "provider": "anthropic",
  "strategy_used": "cost",
  "latency_ms": 842.3,
  "usage": {
    "input_tokens": 45,
    "output_tokens": 180,
    "estimated_cost_usd": 0.003285
  },
  "routing_reason": "Strategy=cost, Complexity=high → claude-sonnet-4-6. Scorer: High-complexity keyword matched.",
  "fallback_used": false
}
```

### `GET /metrics`

```json
{
  "total_requests": 142,
  "total_cost_usd": 0.218,
  "avg_latency_ms": 612.4,
  "model_usage": { "claude-haiku-4-5-20251001": 89, "gpt-4o-mini": 41, "claude-sonnet-4-6": 12 },
  "provider_usage": { "anthropic": 101, "openai": 41 },
  "fallback_count": 2
}
```

### `GET /models`

Lists all available models and their pricing.

---

## Running Tests

```bash
pytest tests/ -v --cov=app
```

---

## Deploying to AWS ECS

### Prerequisites
- AWS account with ECR repository named `llm-gateway`
- ECS cluster `llm-gateway-cluster` with service `llm-gateway-service`
- IAM role with ECR push + ECS deploy permissions
- GitHub secrets: `AWS_ROLE_ARN`

### Deploy
Push to `main` — GitHub Actions handles the rest:
1. Runs tests
2. Builds Docker image → pushes to ECR
3. Updates ECS task definition → triggers rolling deployment

See `.github/workflows/ci.yml` for the full pipeline.

---

## Architecture Decisions

See [`docs/decisions.md`](docs/decisions.md) for trade-off analysis on:
- Why regex scoring instead of an LLM classifier
- Model selection rationale and pricing comparison
- Fallback chain design
- Metrics store migration path to CloudWatch

---

## Cost Comparison

For 1,000 requests (avg 200 input + 300 output tokens):

| Strategy | Approx. cost |
|---|---|
| `auto` / `cost` | ~$0.12 |
| `latency` | ~$0.09 |
| `quality` | ~$5.50 |

**AUTO is ~45× cheaper than QUALITY** for mixed workloads.

---

## Project Structure

```
llm-gateway/
├── app/
│   ├── main.py          # FastAPI app, routes, middleware
│   ├── router.py        # Routing logic + fallback chains
│   ├── scorer.py        # Prompt complexity classification
│   ├── metrics.py       # In-memory usage tracking
│   ├── models.py        # Pydantic schemas
│   ├── config.py        # Settings via env vars
│   └── providers/
│       ├── openai.py    # OpenAI wrapper
│       └── anthropic.py # Anthropic wrapper
├── tests/
│   ├── test_scorer.py
│   ├── test_router.py
│   └── test_metrics.py
├── docs/
│   └── decisions.md     # Architecture decision log
├── .github/workflows/
│   └── ci.yml           # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
