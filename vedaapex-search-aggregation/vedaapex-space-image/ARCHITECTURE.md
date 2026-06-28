# Architecture Guide - 8-Tier Layered System

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Tier 1: Entry Point                                             │
│  ─────────────────────────────────────────────────────────────   │
│  FastAPI Application (app.py)                                    │
│  - Lifespan events (startup/shutdown)                            │
│  - Root endpoint "/"                                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Tier 2: Middleware Stack                                        │
│  ─────────────────────────────────────────────────────────────   │
│  1. CORS Middleware                                              │
│  2. Security Headers (X-Content-Type-Options, etc)               │
│  3. Rate Limiting (60 req/min per IP)                            │
│  4. Request/Response Logging                                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Tier 3: Exception Handlers                                      │
│  ─────────────────────────────────────────────────────────────   │
│  - VedaApexException → 500, 400, 429, 404                        │
│  - HTTPException → 4xx/5xx with formatted JSON                   │
│  - General Exception → 500 with logging                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Tier 4: Routers                                                 │
│  ─────────────────────────────────────────────────────────────   │
│  - routes/images.py  → GET /api/v1/images/search                 │
│  - routes/videos.py  → GET /api/v1/videos/search                 │
│  - routes/health.py  → GET /api/v1/health                        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Tier 5: Services                                                │
│  ─────────────────────────────────────────────────────────────   │
│  ImageSearchService                                              │
│    ├─ Cache check (memory/redis)                                 │
│    ├─ Call ProviderManager if cache miss                         │
│    ├─ Store in cache                                             │
│    └─ Return SearchResponse                                      │
│                                                                  │
│  VideoSearchService (identical pattern)                          │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Tier 6: Provider Manager                                        │
│  ─────────────────────────────────────────────────────────────   │
│  1. Query Categorization                                         │
│     • Space: "mars", "moon", "astronaut", "rover" → NASA first   │
│     • Scientific: "cancer cell", "neuron", "biology" → Wiki 1st  │
│     • General: all other queries → Pexels first                  │
│                                                                  │
│  2. Provider Routing                                             │
│     • Space: [nasa, wikimedia, pexels]                           │
│     • Scientific: [wikimedia, nasa, pexels]                      │
│     • General: [pexels, wikimedia, nasa]                         │
│                                                                  │
│  3. Concurrent Provider Search                                   │
│     • asyncio.gather(*tasks) for parallel execution              │
│     • Independent timeouts per provider                          │
│     • Exception handling per provider                            │
│                                                                  │
│  4. Result Deduplication                                         │
│     • MD5(title) creates unique hash                             │
│     • Skip duplicate hashes                                      │
│     • Preserve first occurrence (highest priority)               │
│                                                                  │
│  5. Smart Ranking                                                │
│     • Provider score: len(priority_list) - position              │
│     • Space query: NASA=3, Wiki=2, Pexels=1                      │
│     • Sort descending by score                                   │
│     • Remove score before returning                              │
│                                                                  │
│  6. Response Normalization                                       │
│     • Convert provider-specific → unified schema                 │
│     • Ensure all fields present (title, url, etc)                │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Tier 7: Provider Layer                                          │
│  ─────────────────────────────────────────────────────────────   │
│  NASAProvider                                                    │
│    ├─ API: https://images-api.nasa.gov/search                    │
│    ├─ Params: q, media_type, page, api_key                       │
│    ├─ Response: collection.items[] with data/links               │
│    ├─ Retry: 3 attempts, exponential backoff (1s, 2s, 4s)        │
│    ├─ Timeout: 15s per request                                   │
│    └─ Error: ProviderError with message                          │
│                                                                  │
│  WikimediaProvider                                               │
│    ├─ API: https://commons.wikimedia.org/w/api.php              │
│    ├─ Params: q, filetype (image/video), page                    │
│    ├─ Response: query.search[] with imageinfo[]                  │
│    ├─ Retry: 3 attempts, exponential backoff                     │
│    ├─ Timeout: 20s per request                                   │
│    └─ Formats: jpg, png, gif (images); webm, mp4 (videos)        │
│                                                                  │
│  PexelsProvider                                                  │
│    ├─ API: https://api.pexels.com/v1/search                      │
│    ├─ Params: query, page, per_page                              │
│    ├─ Response: photos[] with src, url fields                    │
│    ├─ Retry: 3 attempts, exponential backoff                     │
│    ├─ Timeout: 30s per request                                   │
│    └─ Auth: X-API-Key header                                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│  Tier 8: External APIs                                           │
│  ─────────────────────────────────────────────────────────────   │
│  NASA Images API      → 50+ million images/videos                │
│  Wikimedia Commons    → 86+ million files (free)                 │
│  Pexels API           → High-quality photos (free)               │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow Example

### Request: `GET /api/v1/images/search?q=mars%20rover&page=1&page_size=20`

```
1. MIDDLEWARE
   ├─ Log request
   ├─ Check rate limit (IP: 192.168.1.1 = 15/60 requests)
   └─ Add security headers

2. ROUTE HANDLER (routes/images.py)
   ├─ Validate query: "mars rover" ✓ (2-200 chars)
   ├─ Validate pagination: page=1, page_size=20 ✓
   └─ Call ImageSearchService.search()

3. SERVICE LAYER (services/image_service.py)
   ├─ Generate cache key: "image:mars rover:1"
   ├─ Check cache: MISS
   └─ Call ProviderManager.search_images()

4. PROVIDER MANAGER (services/provider_manager.py)
   ├─ Categorize query: "mars rover" → "space"
   ├─ Get priorities: ["nasa", "wikimedia", "pexels"]
   ├─ CONCURRENT SEARCH:
   │  ├─ Task 1: NASAProvider.search_images()
   │  │  └─ API call + retry logic
   │  ├─ Task 2: WikimediaProvider.search_images()
   │  │  └─ API call + retry logic
   │  └─ Task 3: PexelsProvider.search_images()
   │     └─ API call + retry logic
   ├─ Collect results: 45 total
   ├─ Deduplicate: 45 → 38 (7 duplicate titles)
   ├─ Rank: Sort by provider score
   │  • NASA results: score=3 (first)
   │  • Wikimedia results: score=2
   │  • Pexels results: score=1 (last)
   ├─ Truncate: 38 → 20 (max results)
   └─ Return normalized response

5. SERVICE LAYER (continued)
   ├─ Store in cache (TTL: 3600s)
   └─ Return SearchResponse

6. RESPONSE
   ├─ Format JSON
   ├─ Add headers (X-RateLimit-Remaining, etc)
   └─ Send to client (200 OK)

Total Time: ~1000-1500ms (first request)
Subsequent: ~50ms (from cache)
```

## Query Categorization Algorithm

```python
def _categorize_query(query: str) -> str:
    query_lower = query.lower()
    
    # Check space keywords first
    if any(kw in query_lower for kw in SPACE_KEYWORDS):
        return "space"
    
    # Check scientific keywords
    if any(kw in query_lower for kw in SCIENTIFIC_KEYWORDS):
        return "scientific"
    
    # Default to general
    return "general"

# SPACE_KEYWORDS
[
    "nasa", "mars", "moon", "astronaut", "galaxy", "rover",
    "earth", "saturn", "jupiter", "space", "spacecraft",
    "satellite", "orbit", "cosmic", "star", "solar", "sun",
    "planet", "asteroid", "comet", "nebula", "apollo", "hubble"
]

# SCIENTIFIC_KEYWORDS
[
    "cancer cell", "neuron", "microscope", "biology",
    "science", "research", "medical", "anatomy", "cell",
    "bacteria", "virus", "dna", "protein", "chemistry",
    "physics", "experiment", "laboratory"
]
```

## Deduplication Algorithm

```python
def _deduplicate_results(results: List[dict]) -> List[dict]:
    seen = {}
    deduplicated = []
    
    for result in results:
        # Create hash from title (MD5)
        title_hash = hashlib.md5(result["title"].encode()).hexdigest()
        
        # Skip if already seen
        if title_hash in seen:
            continue
        
        # Mark as seen
        seen[title_hash] = True
        deduplicated.append(result)
    
    return deduplicated

# Example
Input:  [
    {"title": "Mars Rover 1", ...},
    {"title": "Mars Rover 1", ...},  # Duplicate (different provider)
    {"title": "Mars Rover 2", ...},
]
Output: [
    {"title": "Mars Rover 1", ...},
    {"title": "Mars Rover 2", ...},
]
```

## Ranking Algorithm

```python
def _rank_results(results: List[dict], provider_scores: dict) -> List[dict]:
    # Add provider score to each result
    for result in results:
        provider = result["provider"]
        result["score"] = provider_scores.get(provider, 0)
    
    # Sort by score (descending), then by original order
    ranked = sorted(results, key=lambda x: -x["score"])
    
    # Remove score field before returning
    for result in ranked:
        del result["score"]
    
    return ranked

# Example (Space Query)
# Provider scores: nasa=3, wikimedia=2, pexels=1

Input Results:
  [
    {"title": "Curiosity", "provider": "pexels", ...},     score=1
    {"title": "Perseverance", "provider": "nasa", ...},     score=3
    {"title": "Spirit", "provider": "wikimedia", ...},      score=2
  ]

After Ranking:
  [
    {"title": "Perseverance", "provider": "nasa", ...},     # score=3
    {"title": "Spirit", "provider": "wikimedia", ...},      # score=2
    {"title": "Curiosity", "provider": "pexels", ...},      # score=1
  ]
```

## Caching Strategy

```
Cache-Aside Pattern:

1. Client requests: GET /api/v1/images/search?q=mars&page=1

2. Generate cache key: md5("image:mars:1") = "abc123..."

3. Check cache:
   ├─ HIT  → Return cached response (50ms)
   └─ MISS → Continue

4. Fetch from providers:
   ├─ Call ProviderManager (1000-2000ms)
   └─ Get results

5. Store in cache:
   ├─ Cache[key] = results
   ├─ TTL = 3600 seconds
   └─ Backend: memory or redis

6. Return to client

Next identical request → Cache HIT (50ms)
```

## Error Handling Flow

```
Provider API Call
       │
       ├─ Success (200-299)
       │  └─ Parse and return
       │
       ├─ Client Error (400-499)
       │  ├─ 400: ValidationError (immediate)
       │  ├─ 429: RateLimitError (skip this provider)
       │  └─ Other: Log and skip
       │
       └─ Server Error (500-599)
          ├─ Attempt retry 1 (wait 1s)
          │  └─ Success → Return
          ├─ Still error → Retry 2 (wait 2s)
          │  └─ Success → Return
          ├─ Still error → Retry 3 (wait 4s)
          │  └─ Success → Return
          └─ Still error → ProviderError (skip provider)

Timeout (>15s)
       │
       ├─ Attempt retry 1 (wait 1s)
       ├─ Attempt retry 2 (wait 2s)
       ├─ Attempt retry 3 (wait 4s)
       └─ Still timeout → ProviderError
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Query validation | <1ms | Regex + string checks |
| Cache lookup | ~1-5ms | In-memory or Redis |
| Categorization | <1ms | Keyword matching |
| Concurrent API calls | 1000-2000ms | 3 providers in parallel |
| Deduplication | ~10-50ms | MD5 hashing + set lookup |
| Ranking | <1ms | Sorting results |
| Response formatting | <1ms | JSON serialization |
| **Total (miss)** | **1000-2100ms** | Multi-provider search |
| **Total (hit)** | **~50ms** | From cache |

## Scalability

### Throughput
- **Single Instance:** 100-200 RPS (with caching)
- **Distributed:** Scale horizontally with Redis cache

### Memory
- **Per Instance:** ~100MB base + cache
- **Cache Size:** LRU limit or Redis size

### API Rate Limits
- **NASA:** 1,000 req/hour (with key)
- **Wikimedia:** Unlimited (no key needed)
- **Pexels:** 200 req/hour (free tier)

---

**This 8-tier architecture ensures scalability, maintainability, and reliability! 🚀**
