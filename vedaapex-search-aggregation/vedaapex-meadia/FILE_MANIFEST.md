# File Manifest & Architecture Reference

Complete overview of all files, dependencies, and module relationships.

---

## Directory Structure

```
vedaapex-meadia/
├── app.py                          # Main FastAPI application
├── config.py                       # Configuration management
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template
├── setup.sh                        # Linux/macOS setup script
├── setup.bat                       # Windows setup script
├── .gitignore                      # Git ignore patterns
├── README.md                       # Project overview
├── QUICKSTART.md                   # 60-second setup guide
├── ARCHITECTURE.md                 # 8-tier architecture deep dive
├── INSTALLATION.md                 # Deployment guide
├── EXAMPLES.md                     # Code examples
├── FILE_MANIFEST.md                # This file
│
├── routes/                         # API endpoint handlers (Tier 3)
│   ├── __init__.py
│   ├── images.py                   # Image search endpoints
│   ├── videos.py                   # Video search endpoints
│   └── health.py                   # Health check endpoint
│
├── services/                       # Business logic (Tier 4)
│   ├── __init__.py
│   ├── image_service.py            # Image search orchestration
│   ├── video_service.py            # Video search orchestration
│   └── cache_service.py            # Caching abstraction layer
│
├── providers/                      # External API integration (Tier 5)
│   ├── __init__.py
│   └── wikimedia_provider.py       # Wikimedia Commons API client
│
├── schemas/                        # Pydantic models (Data layer)
│   ├── __init__.py
│   ├── requests.py                 # Request models
│   └── responses.py                # Response models
│
├── middleware/                     # Request/response processing
│   ├── __init__.py
│   ├── logging.py                  # Request/response logging
│   └── rate_limit.py               # Per-IP rate limiting
│
├── utils/                          # Utilities (Tier 8)
│   ├── __init__.py
│   ├── exceptions.py               # Custom exception classes
│   ├── validators.py               # Input validation
│   └── helpers.py                  # Helper functions
│
├── cache/                          # Cache implementations
│   └── (no files, cache in services/)
│
└── logs/                           # Application logs
    └── app.log                     # Rotating log file
```

---

## File Descriptions

### Core Application

#### `app.py` (450 lines)

**Purpose:** FastAPI application orchestrator

**Key Components:**
- FastAPI app initialization
- Middleware stack setup
- Exception handlers
- Lifespan events (startup/shutdown)
- Router registration
- Security headers
- CORS policy
- Root endpoint

**Key Functions:**
- `lifespan()` - App startup/shutdown
- `add_security_headers()` - Security middleware
- `veda_apex_exception_handler()` - Exception mapping
- `root()` - Root endpoint

**Dependencies:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import config
from services.cache_service import cache_service
from middleware.logging import LoggingMiddleware
from middleware.rate_limit import RateLimitMiddleware
from routes import images, videos, health
from utils.helpers import helpers
```

**Execution Mode:** Async

---

#### `config.py` (140 lines)

**Purpose:** Centralized configuration management

**Key Components:**
- Settings class with environment variables
- Configuration validation
- Type casting and defaults

**Key Attributes:**
- `APP_NAME`, `APP_VERSION`, `APP_ENV`
- `HOST`, `PORT`, `LOG_LEVEL`
- `WIKIMEDIA_API_URL`, `WIKIMEDIA_USER_AGENT`
- `CACHE_TYPE`, `CACHE_TTL`, `REDIS_URL`
- `RATE_LIMIT_PER_MINUTE`, `REQUEST_TIMEOUT`
- `MIN_QUERY_LENGTH`, `MAX_QUERY_LENGTH`

**Key Methods:**
- `is_production()` - Check if production
- `validate_config()` - Validate constraints

**Dependencies:**
```python
from pydantic_settings import BaseSettings
from functools import lru_cache
```

**Global Export:**
```python
config = get_settings()  # Singleton pattern
```

---

### Routes (Tier 3: Request Validation)

#### `routes/images.py` (80 lines)

**Purpose:** Image search API endpoints

**Endpoints:**
- `GET /api/v1/images/search` - Search images

**Query Parameters:**
- `q` (str, required): Search query (2-200 chars)
- `page` (int, default=1): Page number (≥1)
- `page_size` (int, default=20): Results per page (1-100)

**Response Model:** `SearchResponse`

**Key Function:**
```python
@app.get("/api/v1/images/search")
async def search_images(q, page, page_size, request):
    # Validation, error handling, service call
```

**Dependencies:**
```python
from services.image_service import ImageSearchService
from providers.wikimedia_provider import WikimediaProvider
from schemas.responses import SearchResponse, ErrorResponse
from utils.exceptions import VedaApexException, ValidationError
```

---

#### `routes/videos.py` (80 lines)

**Purpose:** Video search API endpoints

**Endpoints:**
- `GET /api/v1/videos/search` - Search videos

**Same structure as images.py but for VideoSearchService**

---

#### `routes/health.py` (60 lines)

**Purpose:** Health check endpoints

**Endpoints:**
- `GET /api/v1/health` - Health check

**Response Model:** `HealthResponse`

**Returns:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00",
  "provider": "operational"
}
```

---

### Services (Tier 4: Business Logic)

#### `services/cache_service.py` (250 lines)

**Purpose:** Caching abstraction layer

**Classes:**

1. **CacheBackend** (Abstract)
   - Methods: `get()`, `set()`, `delete()`, `clear()`, `get_stats()`

2. **InMemoryCache** (100 lines)
   - LRU eviction
   - TTL management
   - Max size enforcement
   
3. **RedisCache** (100 lines)
   - Redis connection
   - JSON serialization
   - Async operations

4. **CacheService** (50 lines)
   - Unified interface
   - Backend selection
   - Configuration integration

**Key Functions:**
- `initialize()` - Setup cache backend
- `get(key)` - Retrieve cached value
- `set(key, value)` - Cache value with TTL
- `get_stats()` - Cache statistics

**Global Export:**
```python
cache_service = CacheService()
```

---

#### `services/image_service.py` (100 lines)

**Purpose:** Image search orchestration

**Class:** `ImageSearchService`

**Key Method:** `search(query, page, page_size, use_cache=True)`

**Flow:**
1. Validate query and pagination
2. Generate cache key
3. Check cache (hit → return cached)
4. Call provider if cache miss
5. Normalize results
6. Cache result
7. Return response

**Dependencies:**
```python
from providers.wikimedia_provider import WikimediaProvider
from services.cache_service import cache_service
from utils.helpers import helpers
from utils.validators import validators
```

---

#### `services/video_service.py` (100 lines)

**Purpose:** Video search orchestration

**Identical structure to ImageSearchService but for videos**

---

### Providers (Tier 5: External API Integration)

#### `providers/wikimedia_provider.py` (250 lines)

**Purpose:** Wikimedia Commons API client

**Class:** `WikimediaProvider`

**API Endpoints Used:**
1. Search API: `/w/api.php?action=query&list=search`
2. File Info API: `/w/api.php?action=query&prop=imageinfo`

**Key Methods:**

1. `search_images(query, limit, offset)` (50 lines)
   - Search parameters: filetype:image, sort by timestamp
   - Returns: search results with file titles

2. `search_videos(query, limit, offset)` (50 lines)
   - Search parameters: filetype:video
   - Returns: video search results

3. `get_file_info(titles)` (40 lines)
   - Fetch detailed file information
   - Extract URLs, MIME types, dimensions

4. `_make_request(params, retry_count)` (80 lines)
   - HTTP client with retry logic
   - Exponential backoff (2^n seconds)
   - Max 3 retries on 5xx errors
   - Timeout handling

**Retry Logic:**
```
Initial attempt
  ↓ (fail)
Wait 1s, retry
  ↓ (fail)
Wait 2s, retry
  ↓ (fail)
Wait 4s, retry
  ↓ (fail)
Raise ProviderError
```

**Error Handling:**
- `ProviderError` on network errors
- `asyncio.TimeoutError` on timeouts
- HTTP status code checking

**Dependencies:**
```python
import httpx
import asyncio
from config import config
from utils.exceptions import ProviderError
from utils.helpers import helpers
```

---

### Schemas (Data Models)

#### `schemas/requests.py` (40 lines)

**Purpose:** Request validation models

**Models:**
1. `SearchRequest`
   - Fields: query, page, page_size
   - Validation: Pydantic Field constraints

**Decorators:**
- `@root_validator` - Cross-field validation
- `Field()` - Field-level constraints

---

#### `schemas/responses.py` (180 lines)

**Purpose:** Response serialization models

**Models:**

1. **MediaResult** (20 lines)
   - Fields: title, media_type, image_url, video_url, thumbnail_url, source_url, width, height, duration, mime_type

2. **Pagination** (10 lines)
   - Fields: page, page_size, total_count, has_next

3. **SearchResponse** (20 lines)
   - Fields: success, provider, query, results, pagination, timestamp, cached

4. **HealthResponse** (10 lines)
   - Fields: status, version, timestamp, provider

5. **ErrorResponse** (10 lines)
   - Fields: success, error, message, status_code, timestamp

**Features:**
- Type validation
- Example configurations
- Automatic OpenAPI documentation

---

### Middleware

#### `middleware/logging.py` (40 lines)

**Purpose:** Request/response logging

**Class:** `LoggingMiddleware`

**Features:**
- Request method, path, client IP logging
- Response status and duration
- Process time header injection

**Key Method:** `dispatch(request, call_next)`

---

#### `middleware/rate_limit.py` (70 lines)

**Purpose:** Per-IP rate limiting

**Class:** `RateLimitMiddleware`

**Features:**
- Fixed window rate limiting (60-second window)
- Per-IP tracking
- Automatic timestamp cleanup
- 429 response on limit exceeded

**Headers:**
- `X-RateLimit-Limit`: 60
- `X-RateLimit-Remaining`: X

---

### Utilities (Tier 8)

#### `utils/exceptions.py` (50 lines)

**Purpose:** Custom exception hierarchy

**Exception Classes:**
```
VedaApexException (base, 500)
├── ValidationError (400)
├── ProviderError (502)
├── RateLimitError (429)
├── CacheError (500)
└── NotFoundError (404)
```

**Attributes:**
- `message` - Error message
- `status_code` - HTTP status

---

#### `utils/validators.py` (80 lines)

**Purpose:** Input validation

**Class:** `Validators`

**Methods:**
1. `validate_query(query)` - Check length, regex, type
2. `validate_pagination(page, page_size)` - Validate ranges
3. `sanitize_query(query)` - Remove dangerous chars

**Constraints:**
- Query: 2-200 chars, alphanumeric + spaces
- Page: ≥ 1
- Page size: 1-100
- Regex: `^[a-zA-Z0-9\s\-_.,&()\u0080-\uFFFF]+$`

---

#### `utils/helpers.py` (150 lines)

**Purpose:** Helper functions

**Class:** `Helpers`

**Static Methods:**

1. `generate_cache_key(prefix, query, page)` → str
   - MD5 hash of "prefix:query:page"

2. `get_timestamp()` → str
   - ISO 8601 format

3. `truncate_string(text, max_length)` → str
   - Ellipsis truncation

4. `extract_file_extension(filename)` → str
   - File extension extraction

5. `is_image(filename)` → bool
   - Check if image file

6. `is_video(filename)` → bool
   - Check if video file

7. `extract_image_metadata(file_data)` → dict
   - Parse Wikimedia response
   - Extract URLs, dimensions

8. `extract_video_metadata(file_data)` → dict
   - Parse Wikimedia video response

---

## Dependencies

### Core Framework

```
fastapi>=0.110.0          # Web framework
uvicorn[standard]>=0.28.0 # ASGI server
pydantic>=2.0.0           # Validation
pydantic-settings>=2.0.0  # Configuration
python-dotenv>=1.0.0      # Environment variables
```

### HTTP Clients

```
httpx>=0.25.0             # Async HTTP
aiohttp>=3.9.0            # Alternative async HTTP
```

### Caching

```
redis>=5.0.0              # Redis client (optional)
```

### Development

```
pytest>=7.0.0             # Testing framework
pytest-asyncio>=0.21.0    # Async test support
httpx[http2]>=0.25.0      # HTTP/2 support
```

---

## Module Dependency Graph

```
app.py
├── config.py
├── services/cache_service.py
├── middleware/logging.py
├── middleware/rate_limit.py
├── routes/images.py
│   ├── services/image_service.py
│   │   ├── providers/wikimedia_provider.py
│   │   ├── services/cache_service.py
│   │   ├── utils/helpers.py
│   │   └── utils/validators.py
│   ├── schemas/responses.py
│   └── utils/exceptions.py
├── routes/videos.py
│   ├── services/video_service.py
│   │   └── (same as image_service)
│   └── (same as images.py)
├── routes/health.py
│   ├── services/cache_service.py
│   └── utils/helpers.py
└── utils/helpers.py
```

---

## Import Order

When writing code, import in this order:

```python
# 1. Standard library
import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

# 2. Third-party
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel, Field
import httpx

# 3. Local (config first)
from config import config

# 4. Local (utils)
from utils.exceptions import VedaApexException
from utils.validators import validators
from utils.helpers import helpers

# 5. Local (services)
from services.cache_service import cache_service

# 6. Local (middleware, providers, etc)
from middleware.logging import LoggingMiddleware
from providers.wikimedia_provider import WikimediaProvider

# 7. Local (routes last)
from routes import images, videos, health
```

---

## Statistics

### Codebase Metrics

| Metric | Count |
|--------|-------|
| Total Files | 23 |
| Python Files | 18 |
| Documentation Files | 6 |
| Setup Scripts | 2 |
| Total Lines of Code | ~3,500 |
| Comment Lines | ~800 |
| Blank Lines | ~600 |

### By Component

| Component | Files | Lines | Purpose |
|-----------|-------|-------|---------|
| Routes | 3 | 220 | API endpoints |
| Services | 3 | 350 | Business logic |
| Providers | 1 | 250 | External APIs |
| Schemas | 2 | 180 | Data models |
| Middleware | 2 | 110 | Request processing |
| Utils | 3 | 280 | Helpers & validation |
| Config/App | 2 | 590 | Setup & orchestration |
| Documentation | 6 | 2,000+ | User guides |

---

## Execution Flow (Complete)

```
1. START: python app.py
   ↓
2. app.py:lifespan() → startup
   ├── Initialize FastAPI
   ├── Setup middleware stack
   ├── Register routers
   └── cache_service.initialize()
   ↓
3. Uvicorn server starts on 0.0.0.0:8000
   ↓
4. Client: GET /api/v1/images/search?q=wildlife&page=1
   ↓
5. Middleware (bottom-to-top):
   ├── LoggingMiddleware: Start timer, log request
   ├── RateLimitMiddleware: Check per-IP limit
   ├── SecurityHeadersMiddleware: Inject headers
   └── CORSMiddleware: Check origin
   ↓
6. Route Handler (routes/images.py:search_images)
   ├── Pydantic validates query, page, page_size
   ├── Call ImageSearchService.search()
   ↓
7. ImageSearchService.search()
   ├── Validate query with validators.validate_query()
   ├── Generate cache key: MD5("image:wildlife:1")
   ├── Try cache_service.get(cache_key)
   ├─ Cache miss → Call provider
   ↓
8. WikimediaProvider.search_images()
   ├── Build request params
   ├── Call _make_request() with retry logic
   ├── GET /w/api.php?action=query&list=search...
   ├── Parse response JSON
   ├── Extract file titles with helpers.is_image()
   ├── Call get_file_info(titles)
   ├── Extract URLs, MIME types
   ↓
9. Wikimedia Commons API Response
   ↓
10. Normalize Response
    ├── Extract with helpers.extract_image_metadata()
    ├── Build SearchResponse model
    ├── Set cached=False
    ↓
11. Cache Result
    ├── cache_service.set(cache_key, response)
    ├── InMemoryCache or RedisCache backend
    ├── TTL: 3600 seconds
    ↓
12. Return SearchResponse
    └── Pydantic serializes to JSON
    ↓
13. Middleware (top-to-bottom):
    ├── LoggingMiddleware: Log response, duration
    ├── SecurityHeadersMiddleware: Add headers
    ├── RateLimitMiddleware: Update headers
    └── CORSMiddleware: Add origin headers
    ↓
14. HTTP/1.1 200 OK
    Content-Type: application/json
    X-RateLimit-Limit: 60
    X-RateLimit-Remaining: 59
    
    {
      "success": true,
      "provider": "wikimedia",
      "query": "wildlife",
      "results": [...],
      "cached": false
    }
    ↓
15. Subsequent request for same query
    ├── cache_service.get(cache_key) → HIT
    ├── Return cached result
    ├── Set cached=True
    ├── Response time: ~50ms
```

---

## Testing Structure

### Unit Tests (Not Implemented)

```
tests/
├── test_validators.py
├── test_helpers.py
├── test_image_service.py
├── test_video_service.py
├── test_cache_service.py
└── test_routes.py
```

### Integration Tests

```
tests/
├── test_full_search_flow.py
├── test_provider_integration.py
└── test_error_handling.py
```

---

## Configuration Hierarchy

1. **Defaults** (hardcoded in config.py)
2. **.env file** (overrides defaults)
3. **Environment variables** (overrides .env)
4. **Runtime validation** (config.validate_config())

---

## Performance Characteristics

### Memory

- Base: ~50MB (Python + FastAPI + dependencies)
- Per cached result: ~1KB
- Max cache (in-memory): ~1GB (1000 results)

### CPU

- Request validation: <1ms
- Cache lookup: <1ms
- Provider call: 800-2000ms
- Response serialization: <5ms

### I/O

- HTTP request timeout: 30s
- Database query: N/A
- File I/O: Only logs

### Concurrency

- Max connections: Unlimited (async)
- Max concurrent requests: Limited by rate limiting
- Connection pooling: 100 connections (httpx default)
