# Fly.io Deployment

## Why `sin` is used

As of May 22, 2026, Fly.io Managed Postgres is available in `sin` but not in `bom`, so the Fly deployment files use `sin` to keep the API, worker, media processor, Postgres, and Redis in one region.

## Files

- `vedaapex-backend/fly.toml`: Node API + BullMQ worker in one Fly app using process groups.
- `fly.media.toml`: private Python media processor Fly app.

## App names

- Public API app: `vedaapex-saas-api`
- Private media app: `vedaapex-media`
- Default public API URL after deploy: `https://vedaapex-saas-api.fly.dev`

If either app name is already taken in your Fly organization, update the `app` value in the corresponding `fly.toml` file before deploying.

## Exact PowerShell commands

### 1. Login and create apps

```powershell
fly auth login
fly apps create vedaapex-saas-api
fly apps create vedaapex-media
```

### 2. Create managed Postgres and Redis

```powershell
fly mpg create --name vedaapex-db --region sin --plan basic --volume-size 10
fly redis create --name vedaapex-redis --region sin --no-replicas
```

### 3. Attach Postgres to both apps

Run this first to copy the cluster ID:

```powershell
fly mpg list
```

Then attach the cluster:

```powershell
fly mpg attach <CLUSTER_ID> -a vedaapex-saas-api
fly mpg attach <CLUSTER_ID> -a vedaapex-media --database vedaapex_media
```

### 4. Get Redis private URL and set it on both apps

Run this first and copy the `Private URL` value:

```powershell
fly redis status vedaapex-redis
```

Then set it:

```powershell
fly secrets set REDIS_URL="redis://copied-private-url" -a vedaapex-saas-api
fly secrets set REDIS_URL="redis://copied-private-url" -a vedaapex-media
```

### 5. Prepare Fly env files

```powershell
Copy-Item .\vedaapex-backend\.env.production.example .\vedaapex-backend\.env.fly
Copy-Item .\media-processor.env.production.example .\media-processor.env.fly
```

Edit these values before import:

- `APP_BASE_URL=https://vedaapex-saas-api.fly.dev`
- `MEDIA_PROCESSOR_BASE_URL=http://vedaapex-media.internal:8000/api/v1/media-processor`
- `ALLOWED_ORIGINS` to your real website domain
- `OTP_MOCK_DELIVERY=false`
- All JWT, AI, Razorpay, SMTP, Firebase, and R2 secrets

### 6. Import secrets

```powershell
Get-Content .\vedaapex-backend\.env.fly | fly secrets import -a vedaapex-saas-api
Get-Content .\media-processor.env.fly | fly secrets import -a vedaapex-media
```

### 7. Deploy media processor first, then API app

```powershell
fly deploy -c .\fly.media.toml
fly deploy -c .\vedaapex-backend\fly.toml
```

### 8. Verify

```powershell
fly status -a vedaapex-media
fly status -a vedaapex-saas-api
fly logs -a vedaapex-saas-api
fly logs -a vedaapex-media
```

### 9. Scale process groups

```powershell
fly scale count web=1 worker=1 -a vedaapex-saas-api
```

## Notes

- The API app runs two process groups in one Fly app: `web` and `worker`.
- The media processor is private-only and is reached over Fly private networking at `vedaapex-media.internal`.
- `fly deploy` for the API runs `npx prisma migrate deploy` before release.
- R2 remains the recommended object storage target for this stack; Fly is only the compute/database/redis host in this setup.
