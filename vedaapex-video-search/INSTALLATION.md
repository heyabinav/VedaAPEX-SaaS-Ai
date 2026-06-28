# Installation & Setup Guide

## Prerequisites

- **Python**: 3.8 or higher
- **pip**: Latest version
- **git**: For cloning repository
- **Pexels API Key**: Get from https://www.pexels.com/api/

## Step-by-Step Installation

### 1. Get API Key

1. Visit https://www.pexels.com/api/
2. Sign up or log in
3. Copy your API key
4. Save it somewhere safe

### 2. Clone Repository

```bash
git clone https://github.com/your-org/vedaapex-video-search.git
cd vedaapex-video-search
```

### 3. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Anaconda (all platforms):**
```bash
conda create -n vedaapex python=3.10
conda activate vedaapex
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment

```bash
# Copy example file
cp .env.example .env

# Edit file and add your Pexels API key
# Windows: notepad .env
# macOS/Linux: nano .env
```

**Minimal Configuration** (.env):
```env
PEXELS_API_KEY=your_pexels_api_key_here
```

**Full Configuration** (.env):
```env
# Application
APP_ENV=development
LOG_LEVEL=INFO

# Pexels API
PEXELS_API_KEY=your_pexels_api_key_here

# Cache
CACHE_TYPE=memory
CACHE_TTL=3600
CACHE_MAX_SIZE=1000

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60

# Request
REQUEST_TIMEOUT=30
MAX_RESULTS=80
MAX_PAGE_SIZE=80
```

## Running Locally

### Development Server

```bash
python app.py
```

Server starts at: `http://localhost:8000`

API Docs: `http://localhost:8000/docs`

### Test the API

```bash
# Test image search
curl "http://localhost:8000/api/v1/images/search?q=nature"

# Test video search
curl "http://localhost:8000/api/v1/videos/search?q=nature"

# Test health
curl "http://localhost:8000/api/v1/health"
```

### With Uvicorn Directly

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### With Gunicorn (Production)

```bash
pip install gunicorn

gunicorn app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

## Docker Deployment

### Build Docker Image

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build
docker build -t vedaapex-video-search:latest .

# Run
docker run -d \
  -p 8000:8000 \
  -e PEXELS_API_KEY=your_key_here \
  -e LOG_LEVEL=INFO \
  vedaapex-video-search:latest

# View logs
docker logs <container_id>
```

### Docker Compose

```yaml
# docker-compose.yml
version: "3.9"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PEXELS_API_KEY=${PEXELS_API_KEY}
      - CACHE_TYPE=redis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

```bash
docker-compose up -d
```

## Advanced Configuration

### Using Redis Cache

**Install Redis:**
```bash
# macOS
brew install redis
redis-server

# Ubuntu/Debian
sudo apt-get install redis-server
redis-server

# Windows - Use Docker
docker run -d -p 6379:6379 redis:7-alpine
```

**Configure (.env):**
```env
CACHE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
```

### Custom API Keys List

**Configure (.env):**
```env
ENABLE_API_KEY_AUTH=true
ALLOWED_API_KEYS=key1,key2,key3
```

**Usage:**
```bash
curl -H "Authorization: Bearer key1" \
  "http://localhost:8000/api/v1/images/search?q=nature"
```

### Logging Configuration

**Configure (.env):**
```env
LOG_LEVEL=DEBUG    # DEBUG, INFO, WARNING, ERROR
LOG_FILE=logs/app.log
```

**Log files created in `logs/` directory**

## Deployment Guides

### Render

1. Connect GitHub repository
2. Create new Web Service
3. Set environment variables:
   - `PEXELS_API_KEY`
   - `APP_ENV=production`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app:app --host 0.0.0.0 --port 8000`
6. Deploy

### Heroku

```bash
# Install Heroku CLI
# From: https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Create app
heroku create vedaapex-video-search

# Set environment variables
heroku config:set PEXELS_API_KEY=your_key_here

# Create Procfile
echo "web: uvicorn app:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.10 vedaapex-video-search --region us-east-1

# Create environment
eb create vedaapex-video-search-env

# Set environment variables
eb setenv PEXELS_API_KEY=your_key_here

# Deploy
eb deploy

# Open app
eb open

# View logs
eb logs
```

### DigitalOcean App Platform

1. Connect GitHub repository
2. Select Python as runtime
3. Set environment variables
4. Configure port: 8000
5. Deploy

### Google Cloud Run

```bash
# Configure
gcloud config set project YOUR_PROJECT_ID

# Build image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vedaapex-video-search

# Deploy
gcloud run deploy vedaapex-video-search \
  --image gcr.io/YOUR_PROJECT_ID/vedaapex-video-search \
  --platform managed \
  --region us-central1 \
  --set-env-vars PEXELS_API_KEY=your_key_here \
  --allow-unauthenticated
```

## Troubleshooting

### API Key Not Working

**Error:**
```
ProviderError: 401 Unauthorized
```

**Solution:**
1. Check your Pexels API key
2. Verify key is set in `.env`
3. Restart server
4. Try regenerating key on Pexels website

### Port Already in Use

**Error:**
```
Address already in use
```

**Solution:**
```bash
# Change port
python app.py  # Default port 8000

# Or set PORT environment variable
PORT=8001 python app.py

# Or kill process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
kill -9 <PID>  # Kill process
```

### Cache Connection Failed

**Error:**
```
Failed to connect to Redis
```

**Solution:**
1. Check Redis is running: `redis-cli ping`
2. Verify Redis URL in `.env`
3. Fall back to in-memory cache: `CACHE_TYPE=memory`

### Rate Limit Exceeded

**Error:**
```
429 Too Many Requests
```

**Solution:**
1. Increase rate limit in `.env`: `RATE_LIMIT_PER_MINUTE=120`
2. Wait 60 seconds (rolling window)
3. Use different IP address if testing

## Performance Tuning

### Increase Workers

```bash
gunicorn app:app \
  --workers 8 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Increase Cache Size

```env
CACHE_TYPE=redis
CACHE_MAX_SIZE=10000
```

### Optimize Timeouts

```env
REQUEST_TIMEOUT=45
CACHE_TTL=7200
```

## Health Checks

```bash
# Verify service is running
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status":"healthy","version":"1.0.0",...}
```

## Next Steps

1. Read [README.md](./README.md) for API usage
2. Review [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
3. Deploy to your preferred platform
4. Monitor logs and metrics
5. Adjust configuration as needed
