# Enterprise AI Knowledge Assistant

Upload PDFs → ask questions across them → get answers with verifiable, page-level citations → compare LLMs on your own benchmark.

## Run it
```bash
cp .env.example .env          # set JWT_SECRET and HOSTED_API_KEY
docker compose up --build     # api :8000, frontend :3000
# optional local model:
docker compose --profile local up -d ollama && docker compose exec ollama ollama pull llama3.1:8b
```
Open http://localhost:3000, create an account, upload PDFs in Library, ask in Ask.

## Architecture
```
upload ─▶ API (validates, stores file) ─▶ Redis ─▶ Celery worker
                                                   extract (PyMuPDF) → chunk (page-aware) → embed → pgvector + tsvector
ask ─▶ retrieval.py: vector top-30 ┐
                     keyword top-30 ┴─ RRF fusion ─▶ cross-encoder rerank ─▶ top-k passages
    ─▶ generation.py: numbered sources → hosted API or Ollama → [n] citations
    ─▶ query_logs (latency, tokens) ─▶ evaluation dashboard
```
Retrieval and generation are separate modules so a bad answer can be traced to bad evidence (low `hit@k`) versus bad reasoning (good `hit@k`, low keyword recall / invalid citations).

## Security
JWT auth on every route; `owner_id` is filtered inside the SQL of both vector and keyword search and every document lookup; per-user Redis rate limit; PDF magic-byte + size checks; LLM and ingestion calls have timeouts and retries.

## Evaluation
1. Edit `experiments/benchmark.jsonl` (question, `expected_source` filename, `expected_keywords`).
2. `docker compose exec api python -m app.services.evaluation --email you@example.com --provider hosted`
3. Repeat with `--provider ollama` or `--no-rerank`; results append to `experiments/results.csv` and show on the Evaluation page.

## Tests
`pip install -r requirements.txt && pytest` (unit tests need no database).

## Suggested build order
1. Ingestion + vector search only, one LLM → 2. add keyword search + RRF → 3. add reranker → 4. Celery → 5. benchmark and compare models → 6. deploy (any VPS with Docker Compose + a reverse proxy such as Caddy for HTTPS; set `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` to your public URLs).

## Known limits
Tables are created with `create_all` (add Alembic before schema changes in production); scanned PDFs need OCR; the evaluation CLI runs benchmarks from the api container rather than from the UI.
