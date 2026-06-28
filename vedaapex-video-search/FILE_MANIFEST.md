# VedaApex Video Search Backend - File Manifest

## Project Overview
Production-ready 8-tier backend architecture for image and video search using Pexels API and FastAPI.

## Directory Structure & File Descriptions

### Root Files
```
vedaapex-video-search/
├── app.py                    ⭐ Main FastAPI application entry point
├── config.py                 ⭐ Configuration management (centralized settings)
├── requirements.txt          📦 Python dependencies
├── .env.example             🔒 Environment variables template
├── .gitignore               📝 Git ignore patterns
├── setup.sh                 🔧 Setup script for Unix/macOS
├── setup.bat                🔧 Setup script for Windows
├── README.md                📖 Project documentation & usage guide
├── INSTALLATION.md          📖 Detailed installation & deployment guide
├── ARCHITECTURE.md          📖 Technical architecture documentation
└── FILE_MANIFEST.md         📖 This file
```

### Application Code

#### `middleware/` - Tier 2: Authentication & Security
```
middleware/
├── __init__.py              📝 Package initialization
├── auth.py                  🔐 API key authentication & validation
│   - APIKeyAuth class
│   - extract_api_key()
│   - validate_api_key()
│   - verify_api_key()
│
├── logging.py               📊 Request/response logging middleware
│   - LoggingMiddleware class
│   - StructuredLoggingFormatter class
│
└── security.py              🛡️  Security headers & rate limiting
    - SecurityHeadersMiddleware class
    - RateLimitMiddleware class
```

#### `routes/` - Tier 1: API Layer
```
routes/
├── __init__.py              📝 Package initialization
├── images.py                🖼️  Image search endpoints
│   - search_images()           GET /api/v1/images/search
│   - get_image_suggestions()   GET /api/v1/images/suggestions
│
├── videos.py                🎬 Video search endpoints
│   - search_videos()           GET /api/v1/videos/search
│   - get_video_suggestions()   GET /api/v1/videos/suggestions
│
└── health.py                ❤️  Health & cache management endpoints
    - health_check()            GET /api/v1/health
    - get_cache_stats()         GET /api/v1/cache/stats
    - clear_cache()             POST /api/v1/cache/clear
```

#### `services/` - Tier 4: Business Logic & Tier 6: Caching
```
services/
├── __init__.py              📝 Package initialization
├── image_service.py         🖼️  Image search service
│   - ImageSearchService class
│   - search() method
│   - _normalize_response()
│   - get_suggestions()
│
├── video_service.py         🎬 Video search service
│   - VideoSearchService class
│   - search() method
│   - _normalize_response()
│   - get_suggestions()
│
└── cache_service.py         💾 Cache management
    - CacheBackend (abstract)
    - InMemoryCache class (LRU)
    - RedisCache class (distributed)
    - CacheService class (facade)
```

#### `providers/` - Tier 5: Provider Layer
```
providers/
├── __init__.py              📝 Package initialization
└── pexels_provider.py       🔌 Pexels API integration
    - PexelsProvider class
    - search_images() method
    - search_videos() method
    - _make_request() method (with retry logic)
    - Retry handling (429, 5xx, timeouts)
```

#### `schemas/` - Tier 3 & 8: Validation & Response
```
schemas/
├── __init__.py              📝 Package initialization
├── requests.py              📥 Pydantic request models
│   - PaginationParams
│   - ImageSearchRequest
│   - VideoSearchRequest
│
└── responses.py             📤 Pydantic response models
    - ImageResult
    - VideoResult
    - Pagination
    - ImageSearchResponse
    - VideoSearchResponse
    - ErrorResponse
    - HealthResponse
```

#### `utils/` - Utility Modules
```
utils/
├── __init__.py              📝 Package initialization
├── exceptions.py            ⚠️  Custom exception classes
│   - VedaApexException (base)
│   - ValidationError
│   - AuthenticationError
│   - RateLimitError
│   - ProviderError
│   - CacheError
│   - NotFoundError
│   - InternalServerError
│
├── validators.py            ✅ Input validation utilities
│   - Validators class
│   - validate_search_query()
│   - validate_pagination()
│   - validate_api_key()
│   - validate_sort_order()
│   - sanitize_query()
│
└── helpers.py               🔧 Helper utilities
    - Helpers class
    - generate_cache_key()
    - get_timestamp()
    - parse_api_key_from_header()
    - extract_image_metadata()
    - extract_video_metadata()
    - truncate_string()
```

### Storage & Logging
```
cache/                       💾 Cache directory (for in-memory cache)
├── __init__.py              📝 Package initialization
└── [cache files]            (Generated at runtime)

logs/                        📊 Log files
└── app.log                  (Generated at runtime)
```

## File Statistics

| Category | Count | Lines | Description |
|----------|-------|-------|-------------|
| Python Code | 13 | ~2,500 | Application code files |
| Configuration | 2 | ~150 | Config & environment |
| Documentation | 4 | ~1,000 | Guides & architecture |
| Setup Scripts | 2 | ~80 | Installation helpers |
| Dependencies | 1 | 11 | Python packages |
| Total | 22+ | ~3,730 | Complete project |

## Module Dependencies

### Tier 1 (API Layer)
- `routes/images.py` → services, schemas, middleware, config
- `routes/videos.py` → services, schemas, middleware, config
- `routes/health.py` → services, schemas, config

### Tier 2 (Authentication)
- `middleware/auth.py` → config, utils/helpers, utils/exceptions
- `middleware/logging.py` → (standard library only)
- `middleware/security.py` → (standard library only)

### Tier 3 (Validation)
- `schemas/requests.py` → (Pydantic only)
- `schemas/responses.py` → (Pydantic only)
- `utils/validators.py` → utils/exceptions

### Tier 4 (Business Logic)
- `services/image_service.py` → providers, services/cache, utils, schemas, config
- `services/video_service.py` → providers, services/cache, utils, schemas, config

### Tier 5 (Provider)
- `providers/pexels_provider.py` → config, utils/exceptions

### Tier 6 (Cache)
- `services/cache_service.py` → config

### Tier 7 (Logging)
- `middleware/logging.py` → (standard library only)

### Tier 8 (Response)
- `schemas/responses.py` → (Pydantic only)
- `app.py` → (exception handlers use helpers)

## Key Features by File

### Data Validation
- `schemas/requests.py` - Pydantic models with field validation
- `utils/validators.py` - Custom validation logic
- `middleware/auth.py` - API key format validation

### Error Handling
- `utils/exceptions.py` - Custom exception hierarchy
- `app.py` - Global exception handlers
- `providers/pexels_provider.py` - Provider-level error handling

### Caching
- `services/cache_service.py` - Unified cache interface
- `services/image_service.py` - Cache integration for images
- `services/video_service.py` - Cache integration for videos
- `routes/health.py` - Cache statistics & management

### Logging
- `middleware/logging.py` - Request/response logging
- `app.py` - Application lifecycle logging

### Security
- `middleware/auth.py` - Authentication
- `middleware/security.py` - Security headers, rate limiting
- `utils/validators.py` - Input sanitization

### API Integration
- `providers/pexels_provider.py` - Pexels API calls with retry logic

## Configuration Files

### `config.py`
- Central configuration management
- Environment variable handling
- Validation logic
- All 20+ settings in one place

### `.env.example`
- Template for required environment variables
- Copy to `.env` and fill in values
- Never commit actual `.env` to git

## Setup & Deployment Files

### `setup.sh` (Unix/macOS)
- Automated environment setup
- Virtual environment creation
- Dependency installation
- Directory initialization

### `setup.bat` (Windows)
- Same functionality as setup.sh
- Windows-specific commands
- Batch script format

## Documentation Files

### `README.md`
- Project overview
- Installation instructions
- API endpoint documentation
- Example requests/responses
- Configuration reference
- Security recommendations
- Performance tips

### `INSTALLATION.md`
- Step-by-step setup guide
- Docker deployment
- Multiple cloud platform guides
- Troubleshooting section
- Performance tuning

### `ARCHITECTURE.md`
- Detailed 8-tier architecture explanation
- Request/response flow diagrams
- Error handling flow
- Performance considerations
- Security considerations
- Monitoring & observability

## Dependencies by Type

### Production Dependencies
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `aiohttp` - Async HTTP client
- `python-dotenv` - Environment variables

### Optional Dependencies
- `redis` - Distributed caching
- `gunicorn` - Production server
- `pytest` - Testing framework

## File Sizes (Approximate)

| File | Size | Description |
|------|------|-------------|
| `app.py` | 12 KB | Main application |
| `config.py` | 5 KB | Configuration |
| `providers/pexels_provider.py` | 8 KB | Provider integration |
| `services/cache_service.py` | 10 KB | Cache management |
| `services/image_service.py` | 8 KB | Image search logic |
| `services/video_service.py` | 8 KB | Video search logic |
| `routes/images.py` | 7 KB | Image endpoints |
| `routes/videos.py` | 7 KB | Video endpoints |
| `routes/health.py` | 6 KB | Health endpoints |
| `schemas/responses.py` | 10 KB | Response models |
| `schemas/requests.py` | 3 KB | Request models |
| `utils/validators.py` | 6 KB | Validation utilities |
| `utils/exceptions.py` | 3 KB | Exception classes |
| `utils/helpers.py` | 6 KB | Helper functions |
| `middleware/auth.py` | 5 KB | Authentication |
| `middleware/security.py` | 7 KB | Security |
| `middleware/logging.py` | 4 KB | Logging |

## Import Order (Dependency Resolution)

1. `config.py` - No dependencies (except env)
2. `utils/exceptions.py` - Uses config
3. `utils/validators.py` - Uses exceptions
4. `utils/helpers.py` - Uses validators
5. `schemas/requests.py` - Uses validators
6. `schemas/responses.py` - Uses schemas
7. `middleware/auth.py` - Uses config, helpers, exceptions
8. `middleware/logging.py` - Standard library only
9. `middleware/security.py` - Standard library only
10. `providers/pexels_provider.py` - Uses config, exceptions
11. `services/cache_service.py` - Uses config
12. `services/image_service.py` - Uses all services, providers, utils, schemas
13. `services/video_service.py` - Uses all services, providers, utils, schemas
14. `routes/images.py` - Uses all above
15. `routes/videos.py` - Uses all above
16. `routes/health.py` - Uses cache_service, schemas, config
17. `app.py` - Uses everything

## Checklist for Completeness

✅ Core Application
- [x] main app.py
- [x] Configuration (config.py)
- [x] Dependencies (requirements.txt)

✅ Tier 1 - API Layer
- [x] Image routes
- [x] Video routes
- [x] Health routes

✅ Tier 2 - Authentication & Security
- [x] API key authentication
- [x] Security headers middleware
- [x] Rate limiting middleware
- [x] Logging middleware

✅ Tier 3 - Validation Layer
- [x] Request schemas (Pydantic)
- [x] Input validators
- [x] Error exceptions

✅ Tier 4 - Business Logic Layer
- [x] Image search service
- [x] Video search service

✅ Tier 5 - Provider Layer
- [x] Pexels provider
- [x] Retry logic
- [x] Timeout handling

✅ Tier 6 - Cache Layer
- [x] In-memory cache
- [x] Redis cache support
- [x] Cache service

✅ Tier 7 - Logging & Monitoring
- [x] Request logging
- [x] Error logging
- [x] Structured logging

✅ Tier 8 - Response Layer
- [x] Response models
- [x] Error responses
- [x] Pagination responses

✅ Documentation
- [x] README.md
- [x] INSTALLATION.md
- [x] ARCHITECTURE.md
- [x] FILE_MANIFEST.md

✅ Setup & Deployment
- [x] setup.sh
- [x] setup.bat
- [x] .env.example
- [x] .gitignore

## Next Steps

1. **Installation**: Follow INSTALLATION.md
2. **Configuration**: Copy .env.example to .env and add Pexels API key
3. **Development**: Run `python app.py`
4. **Testing**: Visit http://localhost:8000/docs
5. **Deployment**: Follow deployment guides in INSTALLATION.md
6. **Monitoring**: Check logs in logs/ directory

## Support & References

- **Pexels API**: https://www.pexels.com/api/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Uvicorn Docs**: https://www.uvicorn.org/
- **Python Docs**: https://docs.python.org/3/
