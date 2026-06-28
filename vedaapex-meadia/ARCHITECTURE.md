# Architecture Deep Dive

## 8-Tier Layered Architecture

### Tier 1-2: API Gateway & Orchestration

**Components:** `app.py`, middleware stack, exception handlers

**Responsibilities:**
- HTTP server orchestration (FastAPI/Uvicorn)
- CORS policy enforcement
- Security headers injection
- Rate limiting coordination
- Exception mapping to HTTP responses
- Request/response logging
- Startup/shutdown events

**Key Code:**

```python
# Middleware stack (bottom-to-top execution order)
app.add_middleware(CORSMiddleware)              # 1. CORS
app.add_middleware(SecurityHeadersMiddleware)   # 2. Security
app.add_middleware(RateLimitMiddleware)         # 3. Rate limiting
app.add_middleware(LoggingMiddleware)           # 4. Logging
```

**Design Patterns:**
- Exception handler decorators
- Middleware stacking pattern
- Lifespan event hooks (FastAPI 0.93+)

---

### Tier 3: Request Validation & Routing

**Components:** `routes/images.py`, `routes/videos.py`, `routes/health.py`

**Responsibilities:**
- HTTP method and path routing
- Query parameter parsing
- Request body validation (Pydantic)
- Input constraints enforcement
- Response serialization
- OpenAPI documentation

**Endpoints:**

```
GET /api/v1/images/search?q=...&page=...&page_size=...
GET /api/v1/videos/search?q=...&page=...&page_size=...
GET /api/v1/health
```

**Request Flow:**

```python
@app.get("/api/v1/images/search")
async def search_images(
    q: str = Query(..., min_length=2, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    # Pydantic validates input automatically
    # Call service layer
    results = await image_service.search(q, page, page_size)
    return SearchResponse(**results)
```

**Design Patterns:**
- RESTful endpoint design
- Pydantic validation
- Dependency injection

---

### Tier 4: Business Logic & Services

**Components:** `services/image_service.py`, `services/video_service.py`, `services/cache_service.py`

**Responsibilities:**
- Search orchestration
- Cache coordination
- Input normalization
- Response building
- Error propagation

**Example Flow:**

```python
async def search(query, page, page_size, use_cache=True):
    # 1. Validate
    query = validators.validate_query(query)
    
    # 2. Check cache
    cache_key = helpers.generate_cache_key("image", query, page)
    cached = await cache_service.get(cache_key)
    if cached:
        return cached  # Cache hit
    
    # 3. Call provider
    raw_results = await provider.search_images(query, limit, offset)
    
    # 4. Normalize
    normalized = normalize_results(raw_results)
    
    # 5. Cache
    await cache_service.set(cache_key, normalized)
    
    # 6. Return
    return normalized
```

**Design Patterns:**
- Service layer pattern
- Strategy pattern (cache backends)
- Cache-aside pattern

---

### Tier 5: Provider Integration

**Components:** `providers/wikimedia_provider.py`

**Responsibilities:**
- External API communication
- Request building with proper headers
- Response parsing
- Error handling and retry logic
- Protocol implementation

**Wikimedia Commons API:**

```
Base: https://commons.wikimedia.org/w/api.php
Auth: User-Agent header only (no API key)
Search: list=search with filetype filters
Details: prop=imageinfo for metadata
```

**Retry Logic:**

```python
async def _make_request(params, retry_count=0):
    try:
        response = await client.get(url, params=params)
        if response.status_code >= 500 and retry_count < max_retries:
            wait_time = retry_delay * (2 ** retry_count)
            await asyncio.sleep(wait_time)
            return await _make_request(params, retry_count + 1)
        return response.json()
    except asyncio.TimeoutError:
        if retry_count < max_retries:
            # Exponential backoff retry
            await asyncio.sleep(...)
            return await _make_request(params, retry_count + 1)
```

**Design Patterns:**
- Adapter pattern (provider abstraction)
- Retry pattern (exponential backoff)
- Circuit breaker (error thresholds)

---

### Tier 6: Caching Layer

**Components:** `services/cache_service.py` with `InMemoryCache` and `RedisCache`

**Responsibilities:**
- In-memory and distributed caching
- TTL management
- Key generation
- Cache invalidation
- Statistics

**Cache Key Generation:**

```python
cache_key = hashlib.md5(f"image:query:page".encode()).hexdigest()
# Example: "8f14e45fceea167a5a36dedd4bea2543"
```

**Backends:**

| Backend | Use Case | Pros | Cons |
|---------|----------|------|------|
| In-Memory | Development, single instance | Fast, simple | Lost on restart, single instance |
| Redis | Production, distributed | Persistent, shared | External dependency |

**LRU Eviction:**

```python
if len(cache) >= max_size:
    oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
    del cache[oldest_key]
```

**Design Patterns:**
- Strategy pattern (cache backends)
- Facade pattern (unified CacheService interface)
- Decorator pattern (cache wrapping provider)

---

### Tier 7: External APIs

**Components:** Wikimedia Commons REST API

**Endpoints Used:**

1. **Search API**
   ```
   POST /w/api.php
   action=query&list=search&srsearch=filetype:image query
   ```

2. **File Info API**
   ```
   POST /w/api.php
   action=query&prop=imageinfo&titles=File:Name.jpg
   ```

**Rate Limits:**
- ~500 req/min (generous for open API)
- No credentials required
- User-Agent header mandatory

**Response Format:**

```json
{
  "query": {
    "search": [
      {
        "ns": 6,
        "title": "File:Example.jpg",
        "pageid": 12345
      }
    ],
    "pages": {
      "12345": {
        "ns": 6,
        "title": "File:Example.jpg",
        "imageinfo": [{
          "url": "https://upload.wikimedia.org/...",
          "thumburl": "https://upload.wikimedia.org/...",
          "width": 1920,
          "height": 1080,
          "mime": "image/jpeg"
        }]
      }
    }
  }
}
```

---

### Tier 8: Infrastructure & Utilities

**Components:** `utils/`, `middleware/`, `config.py`, logging

**Responsibilities:**
- Configuration management
- Helper functions
- Exception definitions
- Input validation
- Environment setup

**Key Utilities:**

```python
# utils/helpers.py
helpers.generate_cache_key()      # MD5 cache key generation
helpers.get_timestamp()           # ISO 8601 timestamp
helpers.extract_image_metadata()  # Parse Wikimedia response
helpers.is_image()                # File type detection
helpers.is_video()                # File type detection

# utils/validators.py
validators.validate_query()       # Query length, regex check
validators.validate_pagination()  # Page and size validation
validators.sanitize_query()       # Clean input

# utils/exceptions.py
VedaApexException                 # Base exception
ValidationError                   # 400
ProviderError                     # 502
RateLimitError                    # 429
```

---

## Request Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ CLIENT REQUEST                                              │
│ GET /api/v1/images/search?q=cancer&page=1&page_size=20    │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │ [Tier 1-2] Middleware Stack         │
        ├──────────────────────────────────────┤
        │ • CORS check                         │
        │ • Security headers                   │
        │ • Rate limit check                   │
        │ • Request logging                    │
        └──────────────────┬───────────────────┘
                           │ ✓ Pass
        ┌──────────────────▼──────────────────┐
        │ [Tier 3] Route Handler               │
        ├──────────────────────────────────────┤
        │ • Parse query: "cancer"              │
        │ • Validate page: 1, page_size: 20   │
        │ • Call ImageSearchService            │
        └──────────────────┬───────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │ [Tier 4] ImageSearchService          │
        ├──────────────────────────────────────┤
        │ • Generate cache key                 │
        │ • Check cache layer                  │
        └──────────────────┬───────────────────┘
                           │ Cache miss
        ┌──────────────────▼──────────────────┐
        │ [Tier 5] WikimediaProvider           │
        ├──────────────────────────────────────┤
        │ • Build request params               │
        │ • Add User-Agent header              │
        │ • HTTP GET with retry logic          │
        └──────────────────┬───────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │ [Tier 7] Wikimedia Commons API       │
        ├──────────────────────────────────────┤
        │ • search: filetype:image cancer      │
        │ • Get page IDs and titles            │
        │ • imageinfo: fetch URLs, metadata    │
        │ • Return JSON response               │
        └──────────────────┬───────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │ [Tier 5] Parse & Normalize           │
        ├──────────────────────────────────────┤
        │ • Extract image URLs                 │
        │ • Build thumbnails                   │
        │ • Get dimensions                     │
        └──────────────────┬───────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │ [Tier 6] Cache Result                │
        ├──────────────────────────────────────┤
        │ • Key: MD5("image:cancer:1")         │
        │ • TTL: 3600 seconds                  │
        │ • Backend: In-Memory/Redis           │
        └──────────────────┬───────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │ [Tier 4] Build Response              │
        ├──────────────────────────────────────┤
        │ • Wrap results in SearchResponse     │
        │ • Add pagination info                │
        │ • Set cached=false                   │
        └──────────────────┬───────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │ [Tier 1-2] Response Middleware       │
        ├──────────────────────────────────────┤
        │ • Add response logging               │
        │ • Add security headers               │
        │ • Set rate limit headers             │
        └──────────────────┬───────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│ HTTP/1.1 200 OK                                            │
│ Content-Type: application/json                             │
│ X-RateLimit-Limit: 60                                      │
│ X-RateLimit-Remaining: 59                                  │
│                                                            │
│ {                                                          │
│   "success": true,                                         │
│   "provider": "wikimedia",                                 │
│   "query": "cancer",                                       │
│   "results": [...],                                        │
│   "pagination": {...},                                     │
│   "cached": false                                          │
│ }                                                          │
└────────────────────────────────────────────────────────────┘
```

---

## Error Handling

### Exception Hierarchy

```
Exception
├── VedaApexException (500)
│   ├── ValidationError (400)
│   ├── ProviderError (502)
│   ├── RateLimitError (429)
│   ├── CacheError (500)
│   └── NotFoundError (404)
└── HTTPException
    ├── 400: Bad Request
    ├── 401: Unauthorized
    ├── 404: Not Found
    └── 429: Too Many Requests
```

### Exception Handler Flow

```python
# In app.py
@app.exception_handler(VedaApexException)
async def veda_apex_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.__class__.__name__,
            "message": exc.message,
            "status_code": exc.status_code,
            "timestamp": helpers.get_timestamp(),
        },
    )
```

---

## Performance Considerations

### Response Time Breakdown (Typical)

| Component | Time | % |
|-----------|------|---|
| Middleware | 5ms | 1% |
| Validation | 2ms | 0.5% |
| Cache lookup | 1ms | 0.25% |
| Provider API | 800ms | 80% |
| Normalization | 50ms | 5% |
| Serialization | 20ms | 2% |
| Network/Logging | 122ms | 11.25% |
| **Total** | **1000ms** | **100%** |

### Cache Benefits

- **Cache hit:** ~50ms response time (95% reduction)
- **Hit rate:** ~70% with typical search patterns
- **Throughput:** 100+ RPS with caching

### Scaling Strategies

1. **Horizontal:** Multiple instances + load balancer + Redis
2. **Vertical:** Increase CPU/memory, tune cache TTL
3. **Caching:** Redis cluster for distributed caching
4. **CDN:** Cache responses at edge

---

## Security

### CORS Policy

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]
```

### Security Headers

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000
```

### Rate Limiting

```
60 requests per minute per IP address
Prevents abuse and DDoS attacks
```

### Input Validation

```
Query: 2-200 chars, alphanumeric + spaces
Page: >= 1
Page size: 1-100
Regex: ^[a-zA-Z0-9\s\-_.,&()]+$
```

---

## Monitoring & Observability

### Logs

```
logs/app.log (rotating, 10MB x 3 backups)
Format: timestamp - logger - level - function:line - message
Level: INFO (default), DEBUG (development)
```

### Metrics to Track

- Request count per endpoint
- Response time (min, max, avg, p95, p99)
- Cache hit rate
- Error rate by type
- Upstream provider latency
- Memory usage

### Health Checks

```
GET /api/v1/health
Response: { "status": "healthy", ... }
Interval: 30 seconds
```
