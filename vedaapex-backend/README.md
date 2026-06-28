# VEDAAPEX Backend

Backend-only Node.js/Express/TypeScript service for the VEDAAPEX EdTech SaaS platform. This service was scaffolded in its own folder so it can be integrated with the existing website without overwriting the Python code already in the workspace.

## Stack

- Node.js 20
- Express.js + TypeScript
- Prisma ORM + PostgreSQL
- Redis + BullMQ
- Firebase Admin SDK
- Cloudflare R2 or Firebase Storage
- JWT access/refresh auth
- OpenAI + Gemini AI provider layer
- Image/video background removal and watermark removal job APIs

## Included Modules

- `src/controllers`: REST controller layer
- `src/routes/v1`: versioned API routes
- `src/services`: business logic for auth, papers, AI, study flows, notifications, analytics
- `src/services/media.service.ts`: upload/register assets, queue media jobs, fetch processed outputs
- `src/middleware`: auth, validation, rate limiting, sanitization, centralized error handling
- `src/ai`: provider gateway and prompt builders
- `src/storage`: R2/Firebase storage adapters with signed URL support
- `src/queues`: BullMQ workers for paper analysis and notifications
- `prisma/schema.prisma`: production-oriented data model

## Key API Areas

- `POST /api/v1/auth/google`
- `POST /api/v1/auth/otp/request`
- `POST /api/v1/auth/otp/verify`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`
- `GET /api/v1/papers`
- `GET /api/v1/papers/coverage`
- `POST /api/v1/papers/upload`
- `POST /api/v1/papers/bulk-import`
- `POST /api/v1/ai/papers/:paperId/analyze`
- `POST /api/v1/ai/papers/:paperId/study-pack`
- `POST /api/v1/ai/answers/evaluate`
- `POST /api/v1/study/plans/generate`
- `POST /api/v1/study/mock-tests/generate`
- `POST /api/v1/media/assets/upload`
- `POST /api/v1/media/jobs`
- `GET /api/v1/admin/analytics/overview`

## Local Setup

1. Copy `.env.example` to `.env` and fill the secrets.
2. Install dependencies with `npm install`.
3. Start infra with `docker-compose up postgres redis -d`.
4. Generate the Prisma client with `npm run prisma:generate`.
5. Run migrations with `npm run prisma:migrate`.
6. Start the API with `npm run dev`.

Swagger docs are exposed at `/docs` when `ENABLE_SWAGGER=true`.

## Integration Notes

- Point the website’s auth flow at `/api/v1/auth/*`.
- Exchange Google or Firebase tokens for first-party JWTs from this backend.
- Use `/api/v1/papers`, `/api/v1/papers/coverage`, and `/api/v1/papers/:paperId/download` for class 9-12, previous-10-years paper browsing and secure downloads.
- Use `/api/v1/papers/bulk-import` to ingest large paper catalogs for classes 9, 10, 11, and 12.
- Use `/api/v1/ai/*` for paper analysis, answer evaluation, study chat, and generated question-answer study packs.
- Use `/api/v1/media/*` for image/video background removal and watermark-removal workflows.
- Keep admin-only upload and analytics screens behind the `ADMIN` role.

## Deployment

- Docker: `Dockerfile` + root `docker-compose.prod.yml`
- Fly.io: `fly.toml` for API/worker + root `../fly.media.toml` for the private Python processor
- PM2: `ecosystem.config.cjs`
- Railway: `railway.toml` + `railway.worker.toml`
- Media processor Railway: root `railway.media.toml`
- Render Blueprint: root `render.yaml`

Additional production docs:

- `../docs/production-architecture.md`
- `../docs/deployment-runbook.md`
- `../docs/production-checklists.md`
- `../docs/fly-io-deploy.md`

## Current Notes

- Paper preview generation and OCR escalation are scaffold-ready through the analysis pipeline, but the actual image-rendering/OCR microservice should be wired according to the deployment environment you choose.
- Media processing supports `MEDIA_PROCESSOR_MODE=passthrough` for dev verification and `MEDIA_PROCESSOR_MODE=http` for a real processor service.
- R2 is the default storage target; switch to Firebase Storage with `STORAGE_PROVIDER=firebase`.
