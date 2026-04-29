# mercedes-rag-rebuild

> **Production-grade RAG service** — rebuilt from the original Mercedes-Benz MLOps engagement to demonstrate full-stack ML engineering at interview depth.

**Sprint active:** May 1 – May 16, 2026 · **Status:** 🚧 Coming May 2026

---

## What this is

A from-scratch rebuild of the RAG service I built at Mercedes-Benz, using public data and open tooling so every design decision is visible and reproducible. The original handled 1K concurrent users with async batching and a Redis caching layer; this rebuild replicates that architecture end-to-end and adds a HyDE (Hypothetical Document Embeddings) retrieval mode with a full eval harness.

## Tech stack

| Layer | Technology |
|---|---|
| **Dataset** | HuggingFace `ccdv/arxiv-summarization` (~5K CS papers) |
| **Embeddings** | Azure OpenAI `text-embedding-ada-002` |
| **Vector index** | Azure AI Search (HNSW, cosine similarity) |
| **API** | FastAPI + Uvicorn |
| **Caching** | Redis 7 (TTL-based, SHA256 keyed) |
| **Retrieval modes** | Direct embedding · HyDE (LLM-generated hypothetical doc) |
| **Eval** | Custom harness — Recall@K, faithfulness, latency (p50/p95) |
| **Infra** | Docker · docker-compose · GitHub Actions CI |
| **Language** | Python 3.11 |

## Coming May 2026

- [ ] Day 1–2: Ingest pipeline + chunking/embedding
- [ ] Day 3–4: Azure AI Search index + FastAPI endpoint
- [ ] Day 5–6: Redis cache + HyDE query rewriting
- [ ] Day 7: Eval harness run #1 (baseline Recall@5 target: >0.55)
- [ ] Day 8–10: Async batching + load test + optimization pass
- [ ] Day 11–12: Docker + CI + eval run #2
- [ ] Day 13–14: README + architecture diagram + load test final + `v1.0` tag

## Architecture (coming Day 13)

```
User Query
    │
    ▼
FastAPI  ──► Redis Cache (HIT → return)
    │
    ▼ MISS
[HyDE] LLM → hypothetical doc embed
    │  [direct] embed query directly
    ▼
Azure AI Search (HNSW vector index)
    │
    ▼
Top-K chunks → response
```

## Eval targets

| Metric | Baseline goal | Post-optimization goal |
|---|---|---|
| Recall@5 (direct) | > 0.55 | > 0.65 |
| Recall@5 (HyDE) | > 0.65 | > 0.75 |
| p95 latency (100 concurrent) | < 800ms | < 500ms |
| Cache hit latency | — | < 5ms |

## Related

- Original project: Mercedes-Benz AI/MLOps engagement (proprietary, not public)
- Dataset: [ccdv/arxiv-summarization](https://huggingface.co/datasets/ccdv/arxiv-summarization)
- Eval skeleton: [`eval/run_eval.py`](eval/run_eval.py)
- Sprint plan: [`SCOPE.md`](SCOPE.md)
