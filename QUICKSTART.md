# Quick Start - 60 Seconds

## Installation

### Prerequisites
- Python 3.10+
- pip

### Setup

**macOS/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

### Manual Setup

```bash
# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Install
pip install -r requirements.txt

# Copy environment
cp .env.example .env
```

## Run the Server

```bash
python app.py
```

Output:
```
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: Application startup complete
```

## Test the API

### 1. Visit Interactive Docs
Open browser: http://localhost:8000/api/v1/docs

### 2. Try Example Requests

**Search for Cancer Cell (Scientific):**
```bash
curl "http://localhost:8000/api/v1/search?q=cancer%20cell&page_size=5"
```

**Search for Mars (Space):**
```bash
curl "http://localhost:8000/api/v1/search?q=mars&page_size=5"
```

**Search for Nature (General):**
```bash
curl "http://localhost:8000/api/v1/search?q=nature&page_size=5"
```

**Health Check:**
```bash
curl "http://localhost:8000/api/v1/health"
```

### 3. Using Python

```python
import httpx
import asyncio

async def search():
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "http://localhost:8000/api/v1/search",
            params={"q": "mars", "page_size": 5}
        )
        data = r.json()
        print(f"Provider: {data['selected_provider']}")
        print(f"Results: {len(data['results'])}")

asyncio.run(search())
```

## Configuration

Edit `.env` to customize:

```bash
# API Keys
PEXELS_API_KEY=your_key_here
NASA_API_KEY=DEMO_KEY

# Providers
ENABLE_PEXELS=true
ENABLE_WIKIMEDIA=true
ENABLE_NASA=true

# Cache
CACHE_TYPE=memory

# Port
PORT=8000
```

## API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/search?q=...` | **Unified search** (auto routing) |
| `GET /api/v1/health` | Health check |
| `GET /api/v1/docs` | OpenAPI docs |

## Next Steps

- 📖 Read [README.md](README.md) for full overview
- 🏗️ See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- 🚀 Check [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
- 🧠 Learn [INTELLIGENT_ROUTING.md](INTELLIGENT_ROUTING.md) for routing algorithm

## Troubleshooting

**Python not found?**
```bash
python3 --version
python3 app.py
```

**Port already in use?**
```bash
PORT=8001 python app.py
```

**Dependencies missing?**
```bash
pip install --upgrade -r requirements.txt
```

---

**✅ You're ready! Start searching! 🚀**
