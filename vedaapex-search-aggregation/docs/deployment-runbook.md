# VEDAAPEX Deployment Runbook

## Prerequisites

- Node.js 20
- Python 3.11
- PostgreSQL 16
- Redis 7
- `pg_dump`
- PM2
- Nginx
- Docker and Docker Compose

## Docker Deployment

```bash
cp vedaapex-backend/.env.production.example vedaapex-backend/.env.production
cp media-processor.env.production.example media-processor.env.production
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml ps
```

## Prisma Deployment

```bash
cd vedaapex-backend
npm ci
npx prisma generate
npx prisma migrate deploy
npm run prisma:seed
```

## PM2 Startup

```bash
cd /srv/vedaapex/vedaapex-backend
npm ci
npm run build
npx prisma migrate deploy
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup
```

## Railway

1. Create three services in one Railway project: `vedaapex-api`, `vedaapex-worker`, and `vedaapex-media`.
2. Set root directories:
   - `vedaapex-api`: `/vedaapex-backend`
   - `vedaapex-worker`: `/vedaapex-backend`
   - `vedaapex-media`: `/`
3. Point each service at its config file:
   - `vedaapex-api`: `/vedaapex-backend/railway.toml`
   - `vedaapex-worker`: `/vedaapex-backend/railway.worker.toml`
   - `vedaapex-media`: `/railway.media.toml`

```bash
railway login
railway link
railway up --service vedaapex-api
railway up --service vedaapex-worker
railway up --service vedaapex-media
```

## Render

```bash
render blueprint validate render.yaml
```

Then create a Blueprint in Render using the repository root `render.yaml`, review the generated services, and provide the secret values marked `sync: false`.

## Ubuntu VPS

```bash
sudo apt-get update
sudo apt-get install -y nginx redis-server postgresql postgresql-contrib ffmpeg python3-pip python3-venv
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
sudo npm install -g pm2
```

```bash
sudo -u postgres psql -c "CREATE USER vedaapex WITH PASSWORD 'CHANGE_ME';"
sudo -u postgres psql -c "CREATE DATABASE vedaapex OWNER vedaapex;"
sudo systemctl enable --now postgresql redis-server nginx
```

```bash
sudo mkdir -p /srv/vedaapex
sudo rsync -av --delete ./ /srv/vedaapex/
```

```bash
cd /srv/vedaapex/vedaapex-backend
cp .env.production.example .env.production
npm ci
npm run build
npx prisma migrate deploy
pm2 start ecosystem.config.cjs
pm2 save
```

```bash
cd /srv/vedaapex
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp media-processor.env.production.example media-processor.env.production
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 --workers 2 --timeout 300
```

```bash
sudo cp deploy/nginx/vedaapex.conf /etc/nginx/conf.d/vedaapex.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Backup

```bash
cd /srv/vedaapex/vedaapex-backend
DATABASE_URL='postgresql://vedaapex:CHANGE_ME@127.0.0.1:5432/vedaapex' ./scripts/backup-postgres.sh
```
