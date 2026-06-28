# File Manifest - Complete Project Structure

## Project Overview

**VedaApex Space Image** - Production-ready multi-provider image and video search backend.
- **Total Files:** 32
- **Total Lines of Code:** ~4,500
- **Architecture:** 8-tier layered system
- **Providers:** NASA, Wikimedia Commons, Pexels

---

## Directory Structure

```
vedaapex-space-image/
├── Root Configuration Files
├── providers/ (Provider integrations)
├── services/ (Business logic)
├── routes/ (HTTP endpoints)
├── schemas/ (Data models)
├── middleware/ (HTTP middleware)
├── utils/ (Utilities)
├── tests/ (Unit tests)
├── logs/ (Runtime logs)
└── Documentation
```

---

## File Listing

### Root Configuration (5 files)

| File | Lines | Purpose |
|------|-------|---------|
| **app.py** | 450 | FastAPI application entry point, middleware stack, exception handlers |
| **config.py** | 140 | Centralized configuration, environment variables, query keywords |
| **requirements.txt** | 10 | Python dependencies (fastapi, httpx, redis, pytest, etc) |
| **.env.example** | 65 | Environment variable template with defaults |
| **.gitignore** | 30 | Git ignore patterns (venv, logs, .env, __pycache__) |

---

### Providers (4 files)

**Purpose:** API integrations for external services

| File | Lines | Provider | Features |
|------|-------|----------|----------|
| **nasa_provider.py** | 180 | NASA | Async search, exponential backoff retry, 15s timeout |
| **wikimedia_provider.py** | 200+ | Wikimedia Commons | Free API, image/video filtering, no key required |
| **pexels_provider.py** | 200+ | Pexels | High-quality photos, API key auth, 30s timeout |
| **__init__.py** | 5 | Package | Module initialization |

**Key Methods:**
- `search_images(query, page, page_size)` - Search images
- `search_videos(query, page, page_size)` - Search videos
- `_make_request()` - HTTP request with retry logic

---

### Services (4 files)

**Purpose:** Business logic and orchestration

| File | Lines | Purpose |
|------|-------|---------|
| **provider_manager.py** | 350+ | Multi-provider routing, deduplication, ranking |
| **image_service.py** | 70 | Image search orchestration with caching |
| **video_service.py** | 70 | Video search orchestration with caching |
| **__init__.py** | 5 | Module initialization |

**Key Features:**
- Query categorization (space/scientific/general)
- Provider priority routing
- MD5-based deduplication
- Provider-based ranking
- Result normalization
- Cache-aside caching

---

### Routes (4 files)

**Purpose:** HTTP API endpoints

| File | Lines | Endpoints |
|------|-------|-----------|
| **images.py** | 70 | `GET /api/v1/images/search` - Image search with validation |
| **videos.py** | 70 | `GET /api/v1/videos/search` - Video search with validation |
| **health.py** | 50 | `GET /api/v1/health` - Health check with provider status |
| **__init__.py** | 5 | Module initialization |

**Request Parameters:**
- `q` (string, required) - Search query (2-200 chars)
- `page` (int, optional) - Page number (≥1)
- `page_size` (int, optional) - Results per page (1-100)

---

### Schemas (3 files)

**Purpose:** Pydantic data models for validation and documentation

| File | Lines | Models |
|------|-------|--------|
| **requests.py** | 45 | ImageSearchRequest, VideoSearchRequest |
| **responses.py** | 120 | MediaResult, Pagination, SearchResponse, HealthResponse, ErrorResponse |
| **__init__.py** | 5 | Module initialization |

**Key Models:**
- `SearchResponse` - Unified search results
- `MediaResult` - Single media item
- `Pagination` - Pagination metadata
- `HealthResponse` - Service health

---

### Middleware (3 files)

**Purpose:** HTTP request/response processing

| File | Lines | Middleware |
|------|-------|------------|
| **logging.py** | 50 | Request/response logging, process time header |
| **rate_limit.py** | 80 | Per-IP rate limiting (60 req/min) |
| **__init__.py** | 5 | Module initialization |

**Stack Order:**
1. CORS → Allow cross-origin requests
2. Security Headers → X-Content-Type-Options, etc
3. Rate Limiting → Per-IP fixed window
4. Logging → Request/response logging

---

### Utils (4 files)

**Purpose:** Helper functions and utilities

| File | Lines | Purpose |
|------|-------|---------|
| **exceptions.py** | 45 | Custom exceptions (VedaApexException, ValidationError, ProviderError, etc) |
| **validators.py** | 50 | Input validation (query length, pagination) |
| **helpers.py** | 35 | Utility functions (cache key generation, timestamps, truncation) |
| **__init__.py** | 5 | Module initialization |

**Key Functions:**
- `validate_query()` - Validate search query
- `validate_pagination()` - Validate page/page_size
- `generate_cache_key()` - MD5 cache key generation
- `get_timestamp()` - ISO 8601 timestamp

---

### Tests (5 files)

**Purpose:** Unit and integration tests

| File | Lines | Tests |
|------|-------|-------|
| **test_nasa_provider.py** | 60 | NASA provider, retry logic, timeout handling |
| **test_validators.py** | 50 | Query validation, pagination validation |
| **test_helpers.py** | 40 | Cache key generation, timestamps, truncation |
| **test_provider_manager.py** | 60 | Categorization, routing, deduplication, ranking |
| **__init__.py** | 5 | Module initialization |

**Run Tests:**
```bash
pytest                              # All tests
pytest tests/test_nasa_provider.py  # Specific test
pytest --cov                        # With coverage
```

---

### Documentation (6 files)

| File | Lines | Purpose |
|------|-------|---------|
| **README.md** | 600 | Project overview, features, quick start, API examples |
| **QUICKSTART.md** | 150 | 60-second setup and first requests |
| **ARCHITECTURE.md** | 700 | 8-tier system design, algorithms, data flow |
| **INSTALLATION.md** | 500 | Local, Docker, and cloud deployment |
| **EXAMPLES.md** | 400 | cURL, Python, JavaScript code examples |
| **NASA_API_GUIDE.md** | 300 | NASA API details, authentication, common queries |

---

### Deployment (2 files)

| File | Purpose |
|------|---------|
| **setup.sh** | Automated setup for macOS/Linux |
| **setup.bat** | Automated setup for Windows |

**Features:**
- Python version check
- Virtual environment creation
- Dependency installation
- .env file creation
- Log directory creation

---

### Logs (1 directory)

| Item | Purpose |
|------|---------|
| **logs/** | Runtime logs directory (created at runtime) |

**Log Files:**
- `app.log` - Rotating log file (10MB × 3 backups)

---

## File Dependencies

```
app.py (entry point)
  ├─ config.py
  ├─ routes/
  │  ├─ images.py → services/image_service.py
  │  ├─ videos.py → services/video_service.py
  │  └─ health.py
  ├─ middleware/
  │  ├─ logging.py
  │  └─ rate_limit.py
  └─ utils/
     ├─ exceptions.py
     └─ helpers.py

services/
  ├─ image_service.py → provider_manager.py
  └─ video_service.py → provider_manager.py

provider_manager.py
  ├─ providers/nasa_provider.py
  ├─ providers/wikimedia_provider.py
  ├─ providers/pexels_provider.py
  └─ utils/

schemas/
  ├─ requests.py
  └─ responses.py

tests/
  ├─ test_nasa_provider.py → providers/
  ├─ test_validators.py → utils/validators.py
  ├─ test_helpers.py → utils/helpers.py
  └─ test_provider_manager.py → services/provider_manager.py
```

---

## Query Categorization Keywords

### Space Keywords (34)
```
nasa, mars, moon, astronaut, galaxy, rover, earth, saturn, jupiter,
space, spacecraft, satellite, orbit, cosmic, star, solar, sun, planet,
asteroid, comet, nebula, apollo, hubble, mission, launch, shuttle,
iss, esa, roscosmos, spacesuit, gravity, acceleration, propulsion
```

### Scientific Keywords (20)
```
cancer cell, neuron, microscope, biology, science, research, medical,
anatomy, cell, bacteria, virus, dna, protein, chemistry, physics,
experiment, laboratory, medicine, disease, treatment
```

---

## Provider Routing Logic

### Query Type Detection

```python
# Space queries → "mars", "moon", etc
if any(kw in query_lower for kw in SPACE_KEYWORDS):
    return "space"

# Scientific queries → "cancer cell", "neuron", etc
elif any(kw in query_lower for kw in SCIENTIFIC_KEYWORDS):
    return "scientific"

# Default → general queries
else:
    return "general"
```

### Provider Priority

| Query Type | Provider 1 | Provider 2 | Provider 3 |
|------------|-----------|-----------|-----------|
| Space | NASA (score 3) | Wikimedia (2) | Pexels (1) |
| Scientific | Wikimedia (3) | NASA (2) | Pexels (1) |
| General | Pexels (3) | Wikimedia (2) | NASA (1) |

---

## API Response Schema

```json
{
  "success": true,
  "provider": "multi-provider",
  "query": "mars rover",
  "results": [
    {
      "title": "string",
      "description": "string",
      "media_type": "image|video",
      "provider": "nasa|wikimedia|pexels",
      "image_url": "string or null",
      "video_url": "string or null",
      "thumbnail_url": "string or null",
      "source_url": "string"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "has_next": true
  },
  "timestamp": "2024-01-15T10:30:00",
  "cached": false
}
```

---

## Performance Metrics

| Operation | Time | Note |
|-----------|------|------|
| Query validation | <1ms | Regex checks |
| Cache lookup | 1-5ms | Memory/Redis |
| API call (single) | 200-500ms | Network |
| Concurrent API calls (3) | 1000-2000ms | Parallel requests |
| Deduplication | 10-50ms | MD5 hashing |
| Response format | <1ms | JSON encoding |
| **Total (cache hit)** | ~50ms | Fastest path |
| **Total (cache miss)** | 1000-2100ms | Full search |

---

## Error Codes

| Code | Meaning | Handler |
|------|---------|---------|
| 200 | Success | SearchResponse |
| 400 | Bad Request | ValidationError |
| 429 | Too Many Requests | RateLimitError |
| 500 | Server Error | VedaApexException |
| 502 | Bad Gateway | ProviderError |

---

## Configuration Parameters

```
APP_NAME = "VedaApex Space Image"
APP_VERSION = "1.0.0"
APP_ENV = "development|production"
PORT = 8000
HOST = "0.0.0.0"

NASA_API_URL = "https://images-api.nasa.gov/search"
NASA_DEMO_KEY = "DEMO_KEY"

ENABLED_PROVIDERS = "nasa,wikimedia,pexels"
REQUEST_TIMEOUT = 15 seconds
MAX_RESULTS = 50
DEFAULT_PAGE_SIZE = 20

CACHE_ENABLED = true
CACHE_TYPE = "memory|redis"
CACHE_TTL = 3600 seconds

RATE_LIMIT_PER_MINUTE = 60
LOG_LEVEL = "DEBUG|INFO|WARNING|ERROR"
```

---

## Development Workflow

```bash
# 1. Setup
./setup.sh

# 2. Activate environment
source venv/bin/activate

# 3. Run server
python app.py

# 4. Run tests
pytest

# 5. Access API
# Browser: http://localhost:8000/api/v1/docs
# CLI: curl http://localhost:8000/api/v1/images/search?q=mars
```

---

**Complete project documentation! 📚**
