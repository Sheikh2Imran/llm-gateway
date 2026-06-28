# Architecture Decision Log

## ADR-001: Complexity Scoring via Regex + Token Count

**Decision:** Use a lightweight regex pattern matcher + estimated token count to classify prompt complexity (LOW / MEDIUM / HIGH), rather than calling an LLM to classify.

**Rationale:**
- Calling an LLM to classify a prompt before routing would add 200–500ms latency and extra cost on *every* request — defeating the purpose of the gateway.
- Regex + token count runs in <1ms, zero cost.
- The trade-off is accuracy: a clever short prompt could be misclassified as LOW. Mitigation: users can pass `force_model` to override routing.

---

## ADR-002: Two Providers, Four Models

**Models selected:**

| Model | Provider | Input $/1K | Output $/1K | Best for |
|---|---|---|---|---|
| claude-haiku-4-5 | Anthropic | $0.00025 | $0.00125 | Simple Q&A, cheap routing |
| gpt-4o-mini | OpenAI | $0.00015 | $0.00060 | Fast, cheap, good general use |
| claude-sonnet-4-6 | Anthropic | $0.003 | $0.015 | Complex reasoning |
| gpt-4o | OpenAI | $0.005 | $0.015 | Best quality, code generation |

**Why not GPT-3.5?** Deprecated. gpt-4o-mini is cheaper and better.
**Why not Claude Opus?** ~15× more expensive than Sonnet for marginal gains. Add it if you need it.

---

## ADR-003: Fallback Chain Design

**Decision:** On provider failure, retry down a predefined fallback chain rather than re-running the complexity scorer.

**Chain logic:**
```
claude-haiku → gpt-4o-mini → claude-sonnet-4-6
gpt-4o-mini  → claude-haiku → gpt-4o
claude-sonnet → gpt-4o
gpt-4o        → claude-sonnet-4-6
```

**Rationale:**
- Fallback should cross providers (if Anthropic is down, try OpenAI)
- Escalate to a stronger model on fallback (better to over-serve than return an error)
- Maximum 3 attempts per request to cap tail latency

---

## ADR-004: In-Memory Metrics (Not Prometheus/CloudWatch Yet)

**Decision:** Use a thread-safe in-memory dataclass for metrics.

**Rationale:**
- Zero infrastructure dependencies for local development
- Easy to swap: replace `metrics.record()` calls with CloudWatch `put_metric_data` or a Prometheus counter

**Migration path to production:**
1. Add `boto3` and call `cloudwatch.put_metric_data()` inside `metrics.record()`
2. Or: add a `/metrics` Prometheus scrape endpoint with `prometheus-fastapi-instrumentator`

---

## ADR-005: Stateless Service Design

**Decision:** The gateway holds no conversation state between requests.

**Rationale:**
- Stateless services are trivially horizontally scalable on ECS Fargate
- If multi-turn conversation is needed: clients send full history in `prompt`, or we add a Redis session layer later

---

## Cost Comparison Example

For 1,000 requests with avg 200 input tokens + 300 output tokens:

| Strategy | Model mix | Estimated cost |
|---|---|---|
| COST/AUTO (80% haiku, 20% sonnet) | Mixed | ~$0.12 |
| LATENCY (80% gpt-4o-mini) | Mixed | ~$0.09 |
| QUALITY (all gpt-4o) | gpt-4o only | ~$5.50 |

**Takeaway:** AUTO strategy is ~45× cheaper than QUALITY for general workloads.
