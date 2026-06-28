# Installation & Deployment Guide

## Table of Contents
1. [Local Development](#local-development)
2. [Docker](#docker)
3. [Cloud Deployment](#cloud-deployment)
4. [Production Configuration](#production-configuration)

---

## Local Development

### Requirements
- Python 3.10+
- pip or conda
- Git

### Setup

**1. Clone/Create project:**
```bash
cd vedaapex-space-image
```

**2. Create virtual environment:**
```bash
python -m venv venv
```

**3. Activate environment:**
```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**4. Install dependencies:**
```bash
pip install -r requirements.txt
```

**5. Setup environment:**
```bash
cp .env.example .env
# Edit .env with your keys
```

**6. Run server:**
```bash
python app.py
```

**7. Access API:**
- Docs: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

### Development Commands

```bash
# Run with auto-reload
uvicorn app:app --reload

# Run tests
pytest -v

# Run with coverage
pytest --cov=providers,services,utils --cov-report=html

# Lint code
pylint providers services utils routes middleware

# Format code
black . --line-length=100
```

---

## Docker

### Build Image

**Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Create logs directory
RUN mkdir -p logs

# Set environment
ENV PYTHONUNBUFFERED=1
ENV APP_ENV=production
ENV HOST=0.0.0.0

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()"

# Run app
CMD ["python", "app.py"]
```

### Build & Run

```bash
# Build
docker build -t vedaapex-space:latest .

# Run
docker run -p 8000:8000 \
  -e NASA_DEMO_KEY=DEMO_KEY \
  -e LOG_LEVEL=INFO \
  vedaapex-space:latest

# With environment file
docker run -p 8000:8000 --env-file .env vedaapex-space:latest

# With volume (logs)
docker run -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  vedaapex-space:latest
```

### Docker Compose

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NASA_DEMO_KEY=${NASA_DEMO_KEY:-DEMO_KEY}
      - APP_ENV=production
      - LOG_LEVEL=INFO
      - CACHE_TYPE=redis
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./logs:/app/logs
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

**Run:**
```bash
docker-compose up -d
```

---

## Cloud Deployment

### Render.com

**1. Create render.yaml:**
```yaml
services:
  - type: web
    name: vedaapex-space
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python app.py
    envVars:
      - key: NASA_DEMO_KEY
        scope: run
        value: DEMO_KEY
      - key: LOG_LEVEL
        scope: run
        value: INFO
      - key: CACHE_TYPE
        scope: run
        value: memory
```

**2. Deploy:**
```bash
git push origin main
# Render automatically deploys from GitHub
```

**3. Access:**
```
https://vedaapex-space.onrender.com/api/v1/docs
```

### Heroku

**1. Create Procfile:**
```
web: python app.py
```

**2. Create runtime.txt:**
```
python-3.12.0
```

**3. Deploy:**
```bash
heroku create vedaapex-space
git push heroku main
heroku logs --tail
```

**4. Set environment:**
```bash
heroku config:set NASA_DEMO_KEY=DEMO_KEY
heroku config:set LOG_LEVEL=INFO
```

### AWS Lambda + API Gateway

**1. Install serverless:**
```bash
npm install -g serverless
serverless plugin install -n serverless-python-requirements
```

**2. Create serverless.yml:**
```yaml
service: vedaapex-space

provider:
  name: aws
  runtime: python3.12
  region: us-east-1
  environment:
    NASA_DEMO_KEY: DEMO_KEY

functions:
  api:
    handler: app.app
    events:
      - http:
          path: /{proxy+}
          method: ANY
          cors: true
```

**3. Deploy:**
```bash
serverless deploy
```

### Google Cloud Run

**1. Create app.yaml:**
```yaml
runtime: python312

env: standard

entrypoint: python app.py

env_variables:
  NASA_DEMO_KEY: DEMO_KEY
  LOG_LEVEL: INFO
```

**2. Deploy:**
```bash
gcloud run deploy vedaapex-space \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure App Service

**1. Create .deployment:**
```
[config]
command = pip install -r requirements.txt
```

**2. Deploy:**
```bash
az webapp up --name vedaapex-space --runtime python:3.12
```

---

## Production Configuration

### Environment Variables

```bash
# Application
APP_NAME=VedaApex Space Image
APP_VERSION=1.0.0
APP_ENV=production
HOST=0.0.0.0
PORT=8000

# NASA API
NASA_API_URL=https://images-api.nasa.gov/search
NASA_DEMO_KEY=YOUR_API_KEY_HERE

# Providers
ENABLED_PROVIDERS=nasa,wikimedia,pexels
DEFAULT_PROVIDER=nasa

# Cache
CACHE_ENABLED=true
CACHE_TYPE=redis
CACHE_TTL=3600
REDIS_URL=redis://redis:6379/0

# Request
REQUEST_TIMEOUT=15
MAX_RESULTS=50
DEFAULT_PAGE_SIZE=20

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
```

### Performance Tuning

**1. Enable Redis caching:**
```bash
CACHE_TYPE=redis
REDIS_URL=redis://cache.example.com:6379/0
```

**2. Increase timeout for slow networks:**
```bash
REQUEST_TIMEOUT=30
```

**3. Adjust rate limiting:**
```bash
RATE_LIMIT_PER_MINUTE=100  # For higher throughput
```

**4. Set appropriate log level:**
```bash
LOG_LEVEL=WARNING  # Production (less verbose)
LOG_LEVEL=DEBUG    # Development (detailed)
```

### Monitoring

**1. Health endpoint:**
```bash
curl https://your-domain.com/api/v1/health
```

**2. Check logs:**
```bash
# Docker
docker logs container-id

# Cloud
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=vedaapex-space"

# Heroku
heroku logs --tail
```

**3. Metrics to monitor:**
- Response time (target: <1.5s for cache miss)
- Cache hit rate (target: >70%)
- Error rate (target: <1%)
- Rate limit hits (target: <5%)

### SSL/TLS

**1. For Render/Heroku/GCP:** Automatic

**2. For self-hosted:**
```bash
# Using Let's Encrypt
certbot certonly --standalone -d your-domain.com

# Configure Nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

### Auto-scaling

**Docker Swarm:**
```bash
docker swarm init
docker service create --name vedaapex-space \
  --publish 8000:8000 \
  --replicas 3 \
  vedaapex-space:latest
```

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vedaapex-space
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vedaapex-space
  template:
    metadata:
      labels:
        app: vedaapex-space
    spec:
      containers:
      - name: api
        image: vedaapex-space:latest
        ports:
        - containerPort: 8000
        env:
        - name: NASA_DEMO_KEY
          value: "DEMO_KEY"
```

---

**Ready for production! 🚀**
