# Architecture Documentation

## 8-Tier Backend Architecture

### Tier 1: API Layer
**Purpose**: REST API endpoints with OpenAPI documentation

**Components**:
- `routes/images.py` - Image search endpoints
- `routes/videos.py` - Video search endpoints
- `routes/health.py` - Health & cache management
- FastAPI application instance in `app.py`

**Key Features**:
- Versioned endpoints (`/api/v1/`)
- Automatic OpenAPI/Swagger docs
- JSON request/response bodies
- Status code standardization

**Example Endpoint**:
```python
@router.get("/api/v1/images/search")
async def search_images(q: str, page: int, page_size: int):
    # Delegates to service layer
    return await image_service.search(...)
```

---

### Tier 2: Authentication Layer
**Purpose**: Validate requests and enforce security

**Components**:
- `middleware/auth.py` - API key validation
- `middleware/security.py` - Security headers
- `middleware/logging.py` - Request logging

**Key Features**:
- API key extraction (header, custom header, query param)
- Key validation against allowed list
- Security headers (CORS, XSS, CSP, HSTS)
- Rate limiting (per-IP, fixed window)
- Request/response logging

**Authentication Flow**:
```
Request → Extract API Key → Validate Key → Add Security Headers → Log Request
                                    ↓
                            If invalid → 401 Unauthorized
                            If rate limited → 429 Too Many Requests
```

---

### Tier 3: Validation Layer
**Purpose**: Ensure all input is safe and valid

**Components**:
- `schemas/requests.py` - Pydantic request models
- `utils/validators.py` - Validation functions
- Request middleware validation

**Key Features**:
- Query validation (1-256 characters, regex pattern)
- Pagination validation (page ≥ 1, 1 ≤ page_size ≤ 80)
- API key format validation
- Input sanitization (remove special chars)
- Sort order validation

**Validation Flow**:
```python
query = validators.validate_search_query(query)  # Validate & sanitize
page, page_size = validators.validate_pagination(page, page_size)
sort = validators.validate_sort_order(sort)
```

---

### Tier 4: Business Logic Layer
**Purpose**: Orchestrate search operations and caching

**Components**:
- `services/image_service.py` - Image search logic
- `services/video_service.py` - Video search logic

**Key Methods**:
```python
async def search(query, page, page_size, sort, use_cache=True):
    # 1. Validate input
    # 2. Check cache
    # 3. Call provider if not cached
    # 4. Normalize response
    # 5. Cache results
    # 6. Return results
```

**Features**:
- Cache-first strategy
- Provider abstraction
- Response normalization
- Error handling
- Search suggestions

---

### Tier 5: Provider Layer
**Purpose**: Integrate with external APIs

**Components**:
- `providers/pexels_provider.py` - Pexels API integration

**Key Features**:
- Async HTTP requests
- Retry logic with exponential backoff
- Rate limit handling (429 responses)
- Timeout protection
- Error handling
- Request/response logging

**Retry Logic**:
```
Attempt 1 → Fail?
            ├─ Rate Limited (429) → Wait & Retry
            ├─ Server Error (5xx) → Exponential backoff → Retry
            ├─ Timeout → Exponential backoff → Retry
            ├─ Max retries exceeded → Raise ProviderError
            └─ Success → Return data
```

**Request Headers**:
- `Authorization`: Pexels API key
- `Accept`: application/json
- `User-Agent`: VedaApex-Video-Search/1.0

---

### Tier 6: Cache Layer
**Purpose**: Reduce API calls and improve response times

**Components**:
- `services/cache_service.py` - Cache management
- Cache backends: InMemoryCache, RedisCache

**Features**:
- Multiple backends (memory, Redis)
- TTL-based expiration (default 1 hour)
- LRU eviction policy (in-memory)
- Key generation (MD5 hash)
- Cache statistics

**Cache Key Format**:
```
MD5("search_image:query:page")
```

**In-Memory Cache**:
- Simple dict-based storage
- TTL tracked per entry
- LRU eviction when max_size reached
- Good for development/single-instance

**Redis Cache**:
- Distributed cache
- Persistent across restarts
- Shared across instances
- Better for production/multi-instance

**Cache Workflow**:
```python
# Check cache
cached = await cache_service.get_search_results(query, page, "image")

if cached:
    return cached  # Return cached result

# Cache miss - fetch from provider
result = await provider.search_images(...)

# Store in cache
await cache_service.set_search_results(query, page, result, "image")

return result
```

---

### Tier 7: Logging & Monitoring Layer
**Purpose**: Track behavior and diagnose issues

**Components**:
- `middleware/logging.py` - Structured logging
- Log files in `logs/` directory

**Logged Information**:
- Request method, path, client IP
- Response status code
- Processing time
- Cache hits/misses
- Errors and exceptions
- API quota usage

**Log Format**:
```
2024-01-01 12:00:00 - app - INFO - GET /api/v1/images/search - Status: 200 - Time: 0.123s
```

**Log Levels**:
- `DEBUG`: Detailed debugging info
- `INFO`: General information
- `WARNING`: Warning messages (rate limits, validation)
- `ERROR`: Errors (failed requests, exceptions)

---

### Tier 8: Response Layer
**Purpose**: Return consistent, well-formatted responses

**Components**:
- `schemas/responses.py` - Pydantic response models
- `app.py` - Exception handlers

**Response Format - Success**:
```json
{
  "success": true,
  "query": "nature",
  "provider": "pexels",
  "results": [...],
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

**Response Format - Error**:
```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Query must be at least 1 character",
  "status_code": 400,
  "timestamp": "2024-01-01T12:00:00"
}
```

**HTTP Status Codes**:
- `200`: Success
- `400`: Validation error
- `401`: Authentication failed
- `404`: Endpoint not found
- `429`: Rate limit exceeded
- `500`: Server error
- `502`: Provider error

---

## Request Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CLIENT REQUEST                                           │
│    GET /api/v1/images/search?q=nature&page=1&page_size=20  │
│    Headers: Authorization: Bearer API_KEY                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MIDDLEWARE STACK (request processing)                    │
│    ├─ LoggingMiddleware: Log request                       │
│    ├─ RateLimitMiddleware: Check rate limit                │
│    ├─ SecurityHeadersMiddleware: Add headers               │
│    └─ APIKeyAuth: Extract & validate API key              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ROUTE HANDLER (routes/images.py)                         │
│    @router.get("/api/v1/images/search")                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. VALIDATION LAYER                                         │
│    ├─ Validate query (length, regex)                       │
│    ├─ Validate pagination (page, page_size)                │
│    └─ Validate sort order                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. BUSINESS LOGIC (services/image_service.py)              │
│    ├─ Check cache                                          │
│    │  ├─ HIT: Return cached result                        │
│    │  └─ MISS: Continue to step 6                         │
│    └─ Prepare request                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. PROVIDER LAYER (providers/pexels_provider.py)            │
│    ├─ Build request with headers & params                  │
│    ├─ Make async HTTP request                              │
│    ├─ Handle retries (429, 5xx, timeouts)                  │
│    ├─ Parse JSON response                                  │
│    └─ Return raw data                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. CACHE LAYER (services/cache_service.py)                 │
│    ├─ Normalize response                                   │
│    ├─ Generate cache key                                   │
│    ├─ Store in cache (memory or Redis)                     │
│    └─ Set TTL expiration                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. RESPONSE LAYER (schemas/responses.py)                   │
│    ├─ Format response (Pydantic model)                     │
│    ├─ Add pagination info                                  │
│    ├─ Add metadata (timestamp, cached flag)                │
│    └─ Validate response format                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. MIDDLEWARE STACK (response processing)                   │
│    ├─ Add response headers (X-Process-Time, X-Request-ID)  │
│    ├─ Add security headers                                 │
│    ├─ Log response                                         │
│    └─ Return to client                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. CLIENT RESPONSE                                         │
│    Status: 200 OK                                           │
│    Headers: Content-Type: application/json, Security hdrs  │
│    Body: { success, query, provider, results, ... }        │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Handling Flow

```
Request
  │
  ├─ Validation Error?
  │  └─ 400 Bad Request
  │
  ├─ Authentication Error?
  │  └─ 401 Unauthorized
  │
  ├─ Rate Limit Exceeded?
  │  └─ 429 Too Many Requests
  │
  ├─ Provider Error?
  │  ├─ Retry (exponential backoff)
  │  └─ If fails after max retries → 502 Bad Gateway
  │
  ├─ Cache Error?
  │  └─ Log & continue (fallback to direct request)
  │
  ├─ Validation Error?
  │  └─ 400 Bad Request
  │
  ├─ Unexpected Error?
  │  └─ 500 Internal Server Error
  │
  └─ Success?
     └─ 200 OK with normalized response
```

---

## Configuration Hierarchy

```
Default Values (in code)
         ↓
.env file environment variables
         ↓
Runtime environment variables
         ↓
Programmatic overrides
```

**Example Configuration Flow**:
```python
# config.py
class Settings(BaseSettings):
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))  # default: 1 hour
    # If environment has "CACHE_TTL=7200", uses 7200
    # Otherwise uses default 3600
```

---

## Performance Considerations

### 1. Caching Strategy
- **Hit Rate Target**: 70-80%
- **TTL**: Adjustable (default 1 hour)
- **Max Entries**: 1000 (in-memory) or unlimited (Redis)

### 2. Database Query Optimization
- Cache search results
- Paginate results (20-80 per page)
- Avoid duplicate requests

### 3. Response Size Optimization
- Return only necessary fields
- Compress JSON responses
- Use pagination to limit data

### 4. Concurrency
- Async/await for non-blocking I/O
- Multiple worker processes (production)
- Connection pooling

---

## Scalability Considerations

### Vertical Scaling
- Increase server resources (CPU, RAM)
- Larger cache size
- More worker processes

### Horizontal Scaling
- Load balancer (nginx, HAProxy)
- Multiple instances
- Shared Redis cache
- Distributed logging

### Database Scaling
- Index frequently searched queries
- Implement query result pagination
- Archive old logs

---

## Security Considerations

### Input Validation
- ✅ Length limits (1-256 chars)
- ✅ Regex pattern matching
- ✅ SQL injection prevention (not applicable - no DB)
- ✅ XSS prevention

### API Key Security
- ✅ Keys never logged
- ✅ Keys validated server-side
- ✅ Keys stored in environment
- ✅ Rotation mechanism

### Transport Security
- ✅ HTTPS in production
- ✅ TLS 1.2+
- ✅ HSTS headers

### Rate Limiting
- ✅ Per-IP limits
- ✅ Request throttling
- ✅ Prevent brute force

---

## Monitoring & Observability

### Key Metrics
- Request rate
- Response time (p50, p95, p99)
- Error rate
- Cache hit ratio
- API quota usage

### Logging
- Request logs (method, path, IP, duration)
- Error logs (type, message, stack trace)
- Provider logs (API calls, retries)
- Cache logs (hits, misses, evictions)

### Alerting
- High error rate (> 5%)
- High response time (> 1s)
- API quota near limit (> 80%)
- Service downtime
