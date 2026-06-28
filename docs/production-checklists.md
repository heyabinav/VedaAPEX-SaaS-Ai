# VEDAAPEX Production Checklists

## Deployment Checklist

- `vedaapex-backend/.env.production` created from `.env.production.example`
- `media-processor.env.production` created from `media-processor.env.production.example`
- PostgreSQL reachable and `DATABASE_URL` tested
- Redis reachable and `REDIS_URL` tested
- `npx prisma migrate deploy` completed
- `npm run prisma:seed` completed where required
- `npm run build` succeeded
- `python -m compileall app` succeeded
- `/health` and `/ready` return `200`

## Security Checklist

- Strong `JWT_ACCESS_SECRET` and `JWT_REFRESH_SECRET` set
- `OTP_MOCK_DELIVERY=false` in production
- `ENABLE_CSRF=true` for browser session flows
- `ALLOWED_ORIGINS` restricted to real domains
- `MEDIA_PROCESSOR_API_KEY` set and kept private
- R2/Firebase keys stored only in host secrets manager
- Swagger disabled publicly unless explicitly required
- HTTPS enabled and certificate auto-renewal configured

## Production Readiness Checklist

- API runs as separate service from worker
- Queue backlog monitored in Redis
- Postgres backups scheduled and restore tested
- PM2 or container restart policy enabled
- Nginx request body limit sized for PDF/media uploads
- R2 signed URL expiry validated
- SMTP delivery verified
- Razorpay webhook secret configured and verified

## Scaling Checklist

- API replicas increased before raising single-instance size
- Worker concurrency adjusted based on BullMQ latency
- Media processor scaled independently from API
- Hot paper endpoints warmed by Redis cache
- Postgres connection limits aligned with Prisma pool settings
- CDN domain configured for R2 public asset delivery

## Testing Checklist

- Auth flows tested: Google, OTP, refresh, logout
- Paper upload, filter, download, and trending APIs tested
- AI paper analysis tested with OCR text present
- Answer evaluation tested with text and file uploads
- Media jobs tested for background removal, watermark removal, and enhancement
- Payment order creation and verification tested in live-like environment
- Restore test completed from latest Postgres backup
