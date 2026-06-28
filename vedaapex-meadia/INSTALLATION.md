# Installation & Deployment Guide

## Table of Contents

1. [Local Development](#local-development)
2. [Docker](#docker)
3. [Cloud Deployment](#cloud-deployment)
4. [Production Checklist](#production-checklist)

---

## Local Development

### Prerequisites

- Python 3.8+
- Git
- (Optional) Redis

### Step 1: Clone & Setup

```bash
cd vedaapex-meadia
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Configuration

```bash
cp .env.example .env
# Edit .env with your settings
```

### Step 3: Run Application

```bash
python app.py
```

Visit http://localhost:8000/api/v1/docs

---

## Docker

### Prerequisites

- Docker
- Docker Compose (optional)

### Build Image

```bash
docker build -t vedaapex-media:latest .
```

### Run Container

```bash
docker run -p 8000:8000 \
  -e APP_ENV=production \
  -e CACHE_TYPE=redis \
  -e REDIS_URL=redis://redis:6379/0 \
  vedaapex-media:latest
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - CACHE_TYPE=redis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    networks:
      - app

  redis:
    image: redis:7-alpine
    networks:
      - app
    volumes:
      - redis_data:/data

volumes:
  redis_data:

networks:
  app:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

CMD ["python", "app.py"]
```

---

## Cloud Deployment

### Heroku

```bash
# Create app
heroku create vedaapex-media

# Add Redis addon
heroku addons:create heroku-redis:premium-0

# Set environment
heroku config:set APP_ENV=production
heroku config:set CACHE_TYPE=redis

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

**Procfile:**

```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

### AWS (EC2)

```bash
# SSH into instance
ssh -i key.pem ubuntu@instance-ip

# Install Python
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv redis-server

# Clone repo
git clone <repo-url>
cd vedaapex-meadia

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/vedaapex-media.service
```

**Service File:**

```ini
[Unit]
Description=VedaApex Media API
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/vedaapex-meadia
Environment="PATH=/home/ubuntu/vedaapex-meadia/venv/bin"
ExecStart=/home/ubuntu/vedaapex-meadia/venv/bin/python app.py

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start vedaapex-media
sudo systemctl enable vedaapex-media
```

### Google Cloud Run

```bash
# Create service
gcloud run deploy vedaapex-media \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "APP_ENV=production"
```

### DigitalOcean App Platform

1. Connect GitHub repository
2. Create App
3. Configure:

```yaml
name: vedaapex-media
services:
  - name: api
    github:
      repo: your-org/vedaapex-meadia
      branch: main
    build_command: pip install -r requirements.txt
    http_port: 8000
    run_command: python app.py
```

---

## Production Checklist

### Security

- [ ] Set `APP_ENV=production` in config
- [ ] Use HTTPS (configure reverse proxy)
- [ ] Set strong CORS origins
- [ ] Enable rate limiting
- [ ] Rotate API credentials regularly
- [ ] Enable logging and monitoring

### Performance

- [ ] Use Redis for caching (not in-memory)
- [ ] Configure appropriate cache TTL
- [ ] Set rate limits based on usage
- [ ] Enable gzip compression
- [ ] Use CDN for static assets

### Monitoring

- [ ] Setup centralized logging
- [ ] Configure alerting
- [ ] Monitor response times
- [ ] Track error rates
- [ ] Monitor memory/CPU usage

### Deployment

- [ ] Test in staging first
- [ ] Configure auto-scaling
- [ ] Setup load balancing
- [ ] Configure database backups
- [ ] Document deployment process
- [ ] Setup rollback procedures

---

## Scaling

### Horizontal Scaling

1. Deploy multiple instances
2. Use load balancer (Nginx, HAProxy)
3. Share cache with Redis
4. Monitor performance

### Vertical Scaling

1. Increase server resources
2. Tune cache settings
3. Optimize database queries
4. Profile bottlenecks

---

## Monitoring & Logging

### Centralized Logging

```bash
# Install ELK Stack
docker run -d --name elasticsearch docker.elastic.co/elasticsearch/elasticsearch:8.0.0 \
  -e discovery.type=single-node

docker run -d -p 5601:5601 --link elasticsearch docker.elastic.co/kibana/kibana:8.0.0
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
response_time = Histogram('response_time_seconds', 'Response time')
```

---

## Troubleshooting

### Port Already in Use

```bash
# Linux/macOS
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Redis Connection Error

```bash
# Check Redis
redis-cli ping
# Should return: PONG

# Reset Redis
redis-cli FLUSHALL
```

### Certificate Errors (HTTPS)

```bash
# Generate self-signed cert
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365

# Use with uvicorn
uvicorn app:app --ssl-keyfile=key.pem --ssl-certfile=cert.pem
```
