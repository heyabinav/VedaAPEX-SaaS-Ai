# Quick Start Guide

## 60-Second Setup

### 1. Clone & Navigate
```bash
git clone <repo-url>
cd vedaapex-video-search
```

### 2. Run Setup Script

**macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```bash
setup.bat
```

### 3. Add API Key
```bash
# Edit .env
nano .env  # or notepad .env on Windows

# Add your Pexels API key:
PEXELS_API_KEY=your_key_here
```

### 4. Run Server
```bash
python app.py
```

### 5. Visit API
```
http://localhost:8000/docs
```

---

## 5-Minute Tutorial

### Search Images

```bash
curl "http://localhost:8000/api/v1/images/search?q=nature&page=1&page_size=20"
```

**Response:**
```json
{
  "success": true,
  "query": "nature",
  "provider": "pexels",
  "results": [
    {
      "id": "12345",
      "title": "Mountain landscape",
      "image_url": "https://...",
      "photographer": "John Doe"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "has_next": true
  }
}
```

### Search Videos

```bash
curl "http://localhost:8000/api/v1/videos/search?q=nature"
```

### Check Health

```bash
curl "http://localhost:8000/api/v1/health"
```

### Using Python

```python
import httpx

async def search_images():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={"q": "nature", "page": 1, "page_size": 20}
        )
        return response.json()
```

---

## Common Tasks

### Enable Redis Caching

1. Install Redis:
```bash
# macOS
brew install redis
redis-server

# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

2. Update `.env`:
```env
CACHE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
```

3. Restart server

### Increase Rate Limit

Edit `.env`:
```env
RATE_LIMIT_PER_MINUTE=120
```

### Change Cache TTL

Edit `.env`:
```env
CACHE_TTL=7200  # 2 hours instead of default 1 hour
```

### Add More API Keys

Edit `.env`:
```env
ENABLE_API_KEY_AUTH=true
ALLOWED_API_KEYS=key1,key2,key3
```

---

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `401 Unauthorized` | Check Pexels API key in `.env` |
| `429 Too Many Requests` | Increase `RATE_LIMIT_PER_MINUTE` in `.env` |
| `Port 8000 in use` | Set `PORT=8001` or kill process on 8000 |
| `Redis connection failed` | Change to `CACHE_TYPE=memory` or start Redis |

---

## Next Steps

1. ✅ Server running locally
2. 📖 Read [README.md](./README.md) for full API docs
3. 🏗️ Review [ARCHITECTURE.md](./ARCHITECTURE.md) for design details
4. 🚀 Deploy using [INSTALLATION.md](./INSTALLATION.md) deployment guides
5. 📊 Monitor logs in `logs/` directory

---

## Support

- **API Docs**: http://localhost:8000/docs (when running)
- **GitHub Issues**: [Create issue](https://github.com/your-repo/issues)
- **Email**: support@vedaapex.com
