# Quick Start Guide - 60 Seconds

## Installation

### Prerequisites
- Python 3.10+
- pip or conda

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

# Install dependencies
pip install -r requirements.txt

# Copy environment file
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

**Search Mars Images:**
```bash
curl "http://localhost:8000/api/v1/images/search?q=mars%20rover&page_size=5"
```

**Search Apollo Videos:**
```bash
curl "http://localhost:8000/api/v1/videos/search?q=apollo&page_size=5"
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
            "http://localhost:8000/api/v1/images/search",
            params={"q": "mars", "page_size": 5}
        )
        data = r.json()
        for result in data["results"]:
            print(f"✓ {result['title']} ({result['provider']})")

asyncio.run(search())
```

## Configuration

Edit `.env` to customize:

```bash
# API Key (optional - DEMO_KEY works)
NASA_DEMO_KEY=DEMO_KEY

# Port
PORT=8000

# Cache
CACHE_TYPE=memory  # or redis

# Logging
LOG_LEVEL=INFO
```

## Next Steps

- 📖 Read [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- 📚 See [EXAMPLES.md](EXAMPLES.md) for code samples
- 🐳 Check [INSTALLATION.md](INSTALLATION.md) for Docker/Cloud deployment
- 📋 Review [FILE_MANIFEST.md](FILE_MANIFEST.md) for file descriptions

## Troubleshooting

**Python not found?**
```bash
# Check installation
python3 --version

# Try with python3
python3 app.py
```

**Port already in use?**
```bash
# Use different port
PORT=8001 python app.py
```

**Dependencies missing?**
```bash
# Reinstall
pip install --upgrade -r requirements.txt
```

---

**✅ You're ready! Start searching! 🚀**
