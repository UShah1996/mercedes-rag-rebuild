# Mercedes RAG Rebuild — SCOPE.md

**Sprint:** May 1 – May 14, 2026 (14 days)
**Repo:** github.com/UShah1996/mercedes-rag-rebuild
**Status:** 🟡 Scoping complete — sprint begins May 1

---

## Dataset Choice

**Selected: HuggingFace `ccdv/arxiv-summarization` (section split, ~5K papers)**

The `ccdv/arxiv-summarization` dataset was chosen over the NIST SP 800-series PDFs for four concrete reasons. First, **licensing**: the HuggingFace dataset is openly licensed for research use with a single `load_dataset()` call, whereas NIST PDFs require manual scraping of nist.gov, PDF parsing (with layout failures on tables and figures), and ambiguous redistribution terms when used in a public GitHub repo. Second, **size and balance**: the `section` split yields ~203K train rows (article section + abstract pairs), with clean `article` and `abstract` fields — enough volume to stress-test chunking and retrieval without requiring cloud storage provisioning beyond free-tier Azure AI Search. Third, **API availability**: HuggingFace Datasets streams directly into a Python ingest script with no browser automation, no rate limiting, and a deterministic 5K-paper eval slice reproducible by any reviewer of the repo. Fourth, **domain fit**: arXiv CS papers are a strong proxy for the long-form technical documentation RAG use case from the original Mercedes work (dense, multi-section documents where retrieval quality degrades without good chunking strategy), making eval numbers directly comparable to the resume claim without needing NDA-covered proprietary data.

---

## 14-Day Day-by-Day Breakdown

> **Dates:** May 1 (Thu) → May 14 (Thu), inclusive. Weekend days (May 3–4, May 10–11) are lighter milestone days — integration and review, no new infrastructure.

### Day 1 — May 1 (Thu): Ingest Pipeline
**Deliverable:** `ingest/ingest.py` committed and passing locally.
- Load `ccdv/arxiv-summarization` (section split) via `datasets` library.
- Stream 5,000 papers from the train split into a local JSONL file (`data/arxiv_5k.jsonl`).
- Each record: `{ "id": str, "article": str, "abstract": str, "word_count": int }`.
- CLI: `python ingest/ingest.py --split train --n 5000 --out data/arxiv_5k.jsonl`.
- Unit test: assert output file has exactly 5,000 lines, no nulls in `article` field.

### Day 2 — May 2 (Fri): Chunking + Embedding
**Deliverable:** `ingest/chunk_embed.py` — chunked + embedded JSONL ready for indexing.
- Chunking strategy: recursive character splitter, chunk_size=512 tokens, overlap=64. Justify in `docs/chunking_rationale.md` (1 paragraph: why 512 vs 256 vs 1024 for arXiv abstracts).
- Embedding model: `text-embedding-ada-002` via Azure OpenAI (or `all-MiniLM-L6-v2` locally if Azure key not set up yet).
- Output: `data/arxiv_5k_chunks.jsonl` — one record per chunk with fields `{ "chunk_id", "doc_id", "text", "embedding": [float] }`.
- Log total chunk count, avg chunk length, embedding latency per batch.

### Day 3 — May 5 (Mon): Azure AI Search Index
**Deliverable:** Index created in Azure AI Search; `ingest/index.py` pushes all chunks.
- Provision Azure AI Search (free tier or S1 if credits allow) in `westus2`.
- Schema: `chunk_id` (key), `doc_id`, `text` (searchable), `embedding` (vector, 1536-dim for ada-002).
- Configure HNSW vector search profile: `m=4`, `efConstruction=400`.
- `ingest/index.py --input data/arxiv_5k_chunks.jsonl --index-name mercedes-rag-v1`.
- Smoke test: query index for "transformer attention mechanism", assert top-1 result is non-empty.

### Day 4 — May 6 (Tue): FastAPI Retrieval Endpoint
**Deliverable:** `app/main.py` — FastAPI app with `/retrieve` and `/health` routes running locally.
- `POST /retrieve` — body: `{ "query": str, "k": int = 5 }` → returns `{ "results": [{"chunk_id", "doc_id", "text", "score"}] }`.
- `GET /health` → `{ "status": "ok", "index": "mercedes-rag-v1" }`.
- Azure AI Search client initialized from env vars (`AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_KEY`, `AZURE_SEARCH_INDEX`).
- Run with `uvicorn app.main:app --reload`; test with `curl` examples in `docs/api_examples.md`.
- Response time target: p50 < 300ms on local machine.

### Day 5 — May 7 (Wed): Redis Caching Layer
**Deliverable:** Redis cache wired into `/retrieve`; cache hit/miss logged.
- Spin up Redis via Docker: `docker run -d -p 6379:6379 redis:7-alpine`.
- Cache key: `sha256(query + str(k))` → serialized result list (JSON).
- TTL: 3600s (1 hour). Cache hit returns in < 5ms.
- Add `X-Cache: HIT|MISS` response header.
- Benchmark: run 100 identical queries, confirm p50 drops from ~280ms (miss) to < 5ms (hit).
- Config via env: `REDIS_URL=redis://localhost:6379`.

### Day 6 — May 8 (Thu): Query Rewriting + HyDE
**Deliverable:** `app/query_rewrite.py` — two retrieval modes: `direct` and `hyde`.
- **HyDE (Hypothetical Document Embeddings):** given query Q, call LLM to generate a hypothetical arXiv abstract that would answer Q; embed the hypothetical; retrieve against that embedding.
- Prompt template for HyDE generation stored in `app/prompts/hyde_prompt.txt`.
- `/retrieve` accepts optional `?mode=hyde` query param; defaults to `direct`.
- Log: for 10 sample queries, record direct vs HyDE top-3 doc_ids and manually eyeball quality (note in `docs/hyde_eval_notes.md`).
- This is the key differentiator from a basic RAG — directly ties to your resume claim on HyDE.

### Day 7 — May 9 (Fri): Eval Harness Run #1
**Deliverable:** `eval/run_eval.py` running end-to-end; baseline numbers written to `eval/results/run_001.json`.
- Use 200-paper eval slice (held-out from Day 1 ingest; use `abstract` as the ground-truth relevant doc for its own `article`).
- Metrics: `Recall@5`, `Recall@10`, `mean_latency_ms`, `p95_latency_ms`.
- Run both modes: `--retriever direct` and `--retriever hyde`.
- Write results to `eval/results/run_001.json`: `{ "run_id", "date", "retriever", "k", "recall_at_k", "mean_latency_ms", "p95_latency_ms" }`.
- Target baseline: Recall@5 > 0.55 for direct, > 0.65 for HyDE (if below, note in `docs/eval_notes.md` and flag for Day 10 optimization).

### Day 8 — May 10 (Sat): Async Batching *(lighter day)*
**Deliverable:** `/retrieve_batch` endpoint; async embedding calls.
- `POST /retrieve_batch` — body: `{ "queries": [str], "k": int }` → `{ "results": [[...]] }`.
- Use `asyncio.gather` to fan out embedding calls; respect Azure OpenAI rate limits with a semaphore (max 10 concurrent).
- Benchmark: batch of 50 queries — wall time with vs without batching.
- Integration test: assert batch results match 50 individual `/retrieve` calls.

### Day 9 — May 11 (Sun): Load Test Baseline *(lighter day)*
**Deliverable:** `scripts/load_test.py` using `locust` or `httpx` async; baseline numbers logged.
- Simulate 100 concurrent users, 60-second ramp, mixed traffic: 80% single-query, 20% batch.
- Record: requests/sec, p50/p95/p99 latency, error rate.
- Save to `eval/results/load_test_baseline.json`.
- Target: p95 < 800ms at 100 concurrent (pre-optimization baseline — numbers don't need to be great yet).

### Day 10 — May 12 (Mon): Optimization Pass
**Deliverable:** At least 2 concrete optimizations implemented + re-benchmarked.
- Review Day 7 eval + Day 9 load test — identify the top 2 bottlenecks.
- Likely targets: (a) embedding batch size tuning, (b) HNSW `efSearch` parameter tuning in Azure AI Search, (c) connection pooling for Redis client, (d) response payload trimming.
- Re-run eval harness: write to `eval/results/run_002.json`. Delta vs run_001 noted in `docs/eval_notes.md`.
- Re-run load test: write to `eval/results/load_test_post_opt.json`.

### Day 11 — May 13 (Tue): Docker + CI
**Deliverable:** `Dockerfile` + `docker-compose.yml` running the full stack; GitHub Actions CI passing.
- `Dockerfile`: multi-stage build, Python 3.11-slim, non-root user, < 500MB final image.
- `docker-compose.yml`: services `api` (FastAPI) + `redis` (Redis 7).
- `make up` starts the stack; `make test` runs unit + integration tests inside Docker.
- GitHub Actions: `.github/workflows/ci.yml` — on push to `main`: lint (ruff), type-check (mypy), unit tests (pytest). Target: green CI badge on README.
- No Azure credentials in CI (mock the Azure client for unit tests).

### Day 12 — May 14 (Wed): Eval Run #2 + Gap Analysis
**Deliverable:** `eval/results/run_003.json` on Dockerized stack; gap analysis written.
- Re-run full eval harness against the Docker stack (not local uvicorn) to confirm no regression.
- Write `docs/eval_summary.md`: table of run_001 → run_002 → run_003 numbers, 2-paragraph gap analysis ("what worked, what would I tackle in a sprint 2").
- This doc becomes your interview talking point: "here's how I measured and improved the system."

### Day 13 — May 15 (Thu): README + Architecture Diagram
**Deliverable:** `README.md` polished; `docs/architecture.png` committed.
- Architecture diagram (draw.io or Excalidraw export): user → FastAPI → [Redis cache | Azure AI Search (HNSW)] → Azure OpenAI embeddings → HyDE LLM call.
- README sections: Overview, Architecture (embed diagram), Quickstart (3 commands to run), Dataset, Eval Results (embed run_003 numbers), API Reference, Design Decisions (why HyDE, why 512-token chunks, why Redis TTL=3600).
- STAR story harvest: write 3 bullet-point STAR stories to `docs/star_stories.md` from the rebuild experience.

### Day 14 — May 16 (Fri): Load Test Final + Tag v1.0
**Deliverable:** Final load test results committed; repo tagged `v1.0`; push complete.
- Re-run load test on Docker stack: `eval/results/load_test_final.json`.
- Target: p95 < 500ms at 100 concurrent (post-optimization goal).
- Write `docs/load_test_summary.md`: baseline vs final table, 1-paragraph explanation of what moved the needle.
- `git tag v1.0 -m "scope locked, 14-day sprint complete"` and push.
- Pin repo on GitHub profile. Done.

---

## Key Files Created by Sprint End

```
mercedes-rag-rebuild/
├── app/
│   ├── main.py                  # FastAPI app
│   ├── query_rewrite.py         # HyDE + direct modes
│   └── prompts/
│       └── hyde_prompt.txt
├── ingest/
│   ├── ingest.py                # Dataset → JSONL
│   ├── chunk_embed.py           # Chunking + embedding
│   └── index.py                 # Push to Azure AI Search
├── eval/
│   ├── run_eval.py              # Eval harness
│   └── results/
│       ├── run_001.json
│       ├── run_002.json
│       ├── run_003.json
│       ├── load_test_baseline.json
│       ├── load_test_post_opt.json
│       └── load_test_final.json
├── scripts/
│   └── load_test.py
├── data/
│   ├── arxiv_5k.jsonl           # gitignored (large)
│   └── arxiv_5k_chunks.jsonl    # gitignored (large)
├── docs/
│   ├── chunking_rationale.md
│   ├── hyde_eval_notes.md
│   ├── eval_notes.md
│   ├── eval_summary.md
│   ├── load_test_summary.md
│   ├── api_examples.md
│   ├── architecture.png
│   └── star_stories.md
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── SCOPE.md                     # this file
└── README.md
```

---

## Non-Goals (Sprint 1)

- No authentication / API keys for the FastAPI endpoint (Sprint 2)
- No streaming responses (Sprint 2)
- No fine-tuned embedding model (post-sprint)
- No production Azure deployment (local Docker only for this sprint)
