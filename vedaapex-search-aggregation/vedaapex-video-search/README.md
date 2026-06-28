# VedaApex Video Search Backend

Production-ready 8-tier backend architecture for image and video search powered by Pexels API.

## 🚀 Features

- **FastAPI REST API** - Modern, fast async HTTP framework
- **Pexels Integration** - Search for images and videos
- **8-Tier Architecture** - Scalable, maintainable codebase
- **Caching System** - Redis or in-memory LRU cache
- **Rate Limiting** - Per-IP request throttling
- **API Authentication** - API key validation
- **Retry Logic** - Automatic retry with exponential backoff
- **Error Handling** - Comprehensive error responses
- **Structured Logging** - Request/response logging
- **Security Headers** - CORS, XSS, CSRF protection
- **Async/Await** - Non-blocking HTTP requests
- **Pagination** - Efficient result navigation
- **Response Normalization** - Unified JSON format

## 📋 System Architecture (8-Tier)

```
Tier 1: API Layer (FastAPI, Versioned Endpoints, OpenAPI Docs)
         ↓
Tier 2: Authentication Layer (API Key Validation, Security Headers)
         ↓
Tier 3: Validation Layer (Input Sanitization, Request Schema)
         ↓
Tier 4: Business Logic Layer (Image/Video Search Services)
         ↓
Tier 5: Provider Layer (Pexels API Integration, Retry Logic)
         ↓
Tier 6: Cache Layer (Redis/In-Memory, TTL Management)
         ↓
Tier 7: Logging & Monitoring (Structured Logs, Metrics)
         ↓
Tier 8: Response Layer (Unified Format, Pagination)
```

## 📁 Project Structure

```
vedaapex-video-search/
├── app.py                      # Main FastAPI application
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
│
├── middleware/                 # Tier 2 - Authentication & Security
│   ├── auth.py                # API key authentication
│   ├── logging.py             # Request/response logging
│   ├── security.py            # Security headers & rate limiting
│   └── __init__.py
│
├── routes/                     # Tier 1 - API Layer
│   ├── images.py              # Image search endpoints
│   ├── videos.py              # Video search endpoints
│   ├── health.py              # Health check & cache management
│   └── __init__.py
│
├── services/                   # Tier 4 - Business Logic
│   ├── image_service.py       # Image search logic
│   ├── video_service.py       # Video search logic
│   ├── cache_service.py       # Tier 6 - Cache management
│   └── __init__.py
│
├── providers/                  # Tier 5 - Provider Abstraction
│   ├── pexels_provider.py     # Pexels API integration
│   └── __init__.py
│
├── schemas/                    # Tier 3 & 8 - Validation & Response
│   ├── requests.py            # Request models
│   ├── responses.py           # Response models
│   └── __init__.py
│
├── utils/                      # Utilities
│   ├── validators.py          # Tier 3 - Input validation
│   ├── exceptions.py          # Custom exceptions
│   ├── helpers.py             # Helper utilities
│   └── __init__.py
│
├── cache/                      # Tier 6 - Cache storage
├── logs/                       # Tier 7 - Log files
│
└── README.md                  # This file
```

## 🔧 Installation

### Prerequisites
- Python 3.8+
- pip or conda
- Pexels API Key (get from https://www.pexels.com/api/)

### Step 1: Clone Repository
```bash
git clone <repository-url>
cd vedaapex-video-search
```

### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Setup Environment Variables
```bash
# Copy example to .env
cp .env.example .env

# Edit .env with your configuration
# Windows
notepad .env

# macOS/Linux
nano .env
```

### Step 5: Required Environment Variables
```env
# Required
PEXELS_API_KEY=your_api_key_here

# Optional (sensible defaults provided)
CACHE_TYPE=memory              # "memory" or "redis"
CACHE_TTL=3600                # Cache time-to-live in seconds
RATE_LIMIT_PER_MINUTE=60      # Requests per minute
REQUEST_TIMEOUT=30            # Request timeout in seconds
```

## 🏃 Running the Application

### Development Mode
```bash
python app.py
```

Application will be available at `http://localhost:8000`

API documentation at `http://localhost:8000/docs`

### Production Mode
```bash
# Using Gunicorn + Uvicorn
pip install gunicorn

gunicorn app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

## 📡 API Endpoints

### Image Search
```bash
GET /api/v1/images/search?q=nature&page=1&page_size=20

Response:
{
  "success": true,
  "query": "nature",
  "provider": "pexels",
  "results": [
    {
      "id": "12345",
      "title": "Mountain landscape",
      "image_url": "https://images.pexels.com/...",
      "thumbnail_url": "https://images.pexels.com/...",
      "photographer": "John Doe",
      "photographer_url": "https://www.pexels.com/...",
      "source_url": "https://www.pexels.com/photo/...",
      "width": 5000,
      "height": 3000,
      "avg_color": "#90A870"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 5000,
    "has_next": true
  },
  "timestamp": "2024-01-01T12:00:00",
  "cached": false
}
```

### Video Search
```bash
GET /api/v1/videos/search?q=nature&page=1&page_size=20

Response:
{
  "success": true,
  "query": "nature",
  "provider": "pexels",
  "results": [
    {
      "id": "12345",
      "video_url": "https://videos.pexels.com/...",
      "thumbnail_url": "https://images.pexels.com/...",
      "duration": 60,
      "creator": "Jane Smith",
      "source_url": "https://www.pexels.com/video/...",
      "width": 1920,
      "height": 1080
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 5000,
    "has_next": true
  },
  "timestamp": "2024-01-01T12:00:00",
  "cached": false
}
```

### Health Check
```bash
GET /api/v1/health

Response:
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00",
  "uptime": 3600.5,
  "cache_status": "operational"
}
```

### Cache Stats
```bash
GET /api/v1/cache/stats

Response:
{
  "success": true,
  "data": {
    "enabled": true,
    "type": "in_memory",
    "total_entries": 45,
    "max_size": 1000,
    "expired_entries": 2,
    "available_space": 955
  },
  "timestamp": "2024-01-01T12:00:00"
}
```

### Clear Cache
```bash
POST /api/v1/cache/clear

Response:
{
  "success": true,
  "message": "Cache cleared successfully",
  "timestamp": "2024-01-01T12:00:00"
}
```

## 🔐 Authentication

### Using API Key

**Header Method:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/images/search?q=nature"
```

**Custom Header:**
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://localhost:8000/api/v1/images/search?q=nature"
```

**Query Parameter:**
```bash
curl "http://localhost:8000/api/v1/images/search?q=nature&api_key=YOUR_API_KEY"
```

## 🚀 Deployment

### Deploy to Render

1. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub

2. **Connect Repository**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select the repository

3. **Configure Deployment**
   - Name: `vedaapex-video-search`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app:app --host 0.0.0.0 --port 8000`

4. **Add Environment Variables**
   - Click "Environment"
   - Add all variables from `.env`
   - Most important: `PEXELS_API_KEY`

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically deploy

### Deploy to Heroku

```bash
# Login to Heroku
heroku login

# Create Heroku app
heroku create vedaapex-video-search

# Set environment variables
heroku config:set PEXELS_API_KEY=your_key_here

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### Deploy to AWS

```bash
# Use AWS Elastic Beanstalk
eb init
eb create vedaapex-video-search-env
eb deploy
```

## 🔒 Security Recommendations

### 1. API Key Management
- ✅ Rotate API keys regularly
- ✅ Store keys in environment variables
- ✅ Never commit keys to git
- ✅ Use `.env` file in `.gitignore`

### 2. HTTPS/SSL
- ✅ Use HTTPS in production
- ✅ Use TLS 1.2 or higher
- ✅ Implement HSTS headers

### 3. Rate Limiting
- ✅ Enforce per-IP rate limits
- ✅ Monitor for abuse patterns
- ✅ Implement exponential backoff

### 4. Input Validation
- ✅ Validate all query parameters
- ✅ Sanitize user input
- ✅ Limit query length
- ✅ Use regex patterns

### 5. Security Headers
- ✅ X-Content-Type-Options: nosniff
- ✅ X-Frame-Options: DENY
- ✅ X-XSS-Protection: 1; mode=block
- ✅ Strict-Transport-Security
- ✅ Referrer-Policy

### 6. Logging & Monitoring
- ✅ Log all API requests
- ✅ Monitor error rates
- ✅ Alert on suspicious activity
- ✅ Rotate logs regularly

## ⚡ Performance Optimization

### 1. Caching Strategy
- Cache search results for 1 hour (default)
- Implement cache invalidation
- Monitor cache hit rates

### 2. Database Optimization
- Use Redis for cache backend in production
- Index frequently searched queries
- Implement query result pagination

### 3. Request Optimization
- Set appropriate request timeouts
- Implement connection pooling
- Use gzip compression

### 4. Infrastructure
- Use CDN for static assets
- Implement horizontal scaling
- Use load balancing

## 📊 Performance Metrics

### Expected Performance
- **Response Time**: < 200ms (with cache)
- **Cache Hit Rate**: 70-80%
- **API Rate Limit**: 60 req/min per IP
- **Max Results**: 80 per page

### Monitoring
- Track response times
- Monitor cache hit/miss ratio
- Track error rates
- Monitor API quota usage

## 🧪 Testing

### Manual Testing
```bash
# Test image search
curl "http://localhost:8000/api/v1/images/search?q=nature"

# Test video search
curl "http://localhost:8000/api/v1/videos/search?q=nature"

# Test health
curl "http://localhost:8000/api/v1/health"
```

### Automated Testing
```bash
pytest tests/
```

## 📝 Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `PEXELS_API_KEY` | - | Pexels API key (required) |
| `CACHE_TYPE` | memory | Cache backend: memory or redis |
| `CACHE_TTL` | 3600 | Cache time-to-live in seconds |
| `CACHE_MAX_SIZE` | 1000 | Maximum cache entries |
| `RATE_LIMIT_PER_MINUTE` | 60 | Requests per minute limit |
| `REQUEST_TIMEOUT` | 30 | HTTP request timeout in seconds |
| `MAX_RESULTS` | 80 | Maximum results per search |
| `MAX_PAGE_SIZE` | 80 | Maximum page size |
| `ENABLE_API_KEY_AUTH` | true | Require API key authentication |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |

## 🤝 Contributing

1. Create a feature branch
2. Make your changes
3. Write tests
4. Submit a pull request

## 📄 License

MIT License - See LICENSE file

## 🆘 Support

For issues and questions:
- GitHub Issues: https://github.com/your-repo/issues
- Email: support@vedaapex.com
- Documentation: /docs (when running)

## 🙏 Acknowledgments

- [Pexels](https://www.pexels.com/) - Free stock photos and videos
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Pydantic](https://pydantic-settings.readthedocs.io/) - Data validation
