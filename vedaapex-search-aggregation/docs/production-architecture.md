# VEDAAPEX Production Architecture

## Service Topology

- `nginx`: public reverse proxy, TLS termination, request buffering, gzip.
- `vedaapex-api` (`vedaapex-backend/src/server.ts`): public REST API, auth, papers, payments, admin APIs.
- `vedaapex-worker` (`vedaapex-backend/src/worker.ts`): BullMQ worker for paper analysis, notifications, and media jobs.
- `vedaapex-media` (`app/main.py` + `app/routes/processor.py`): internal FastAPI microservice for CPU-heavy image/video processing.
- `PostgreSQL`: system of record for auth, papers, AI reports, media jobs, payments, analytics.
- `Redis`: BullMQ broker, OTP/session cache, Redis-backed rate limiting, hot paper-list cache.
- `Cloudflare R2`: durable storage for papers, answer uploads, media originals, and processed outputs.
- `Groq`, `OpenAI`, `Gemini`: cloud AI providers with ordered fallback in the Node AI gateway.

## Request Flow

1. Client requests hit `nginx` on `api.vedaapex.com`.
2. `nginx` forwards API traffic to `vedaapex-api`.
3. `vedaapex-api` authenticates users, enforces Redis-backed limits, and persists state in PostgreSQL.
4. Long-running work is queued in Redis via BullMQ and executed by `vedaapex-worker`.
5. Media jobs call the internal FastAPI processor at `http://media-processor:8000/api/v1/media-processor`.
6. Generated files are written to R2 and returned through signed URLs.

## Scaling Model

- Scale `vedaapex-api` horizontally first; it is stateless aside from Redis/Postgres dependencies.
- Keep `vedaapex-worker` separate so API latency is not impacted by AI or OCR bursts.
- Scale `vedaapex-worker` by concurrency and replica count when queue latency grows.
- Keep `vedaapex-media` private and scale independently based on CPU load and ffmpeg/rembg throughput.
- Use CDN-backed R2 public base URLs for heavy download traffic.

## Production Folder Layout

```text
Backend/
├── app/                         # Python FastAPI media processor
├── vedaapex-backend/            # Node.js API + BullMQ worker
├── deploy/nginx/vedaapex.conf   # Reverse proxy and TLS config
├── docs/                        # Runbooks, architecture, checklists
├── docker-compose.prod.yml      # Full platform local/VPS orchestration
├── media-processor.env.production.example
├── railway.media.toml
├── render.yaml
└── .github/workflows/platform-ci.yml
```
