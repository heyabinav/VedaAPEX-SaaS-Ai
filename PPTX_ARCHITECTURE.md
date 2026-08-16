# PowerPoint Generation System - Architecture Document

## 📂 File Structure

```
backend/
├── app/
│   ├── schemas/
│   │   └── presentations.py          ✨ NEW - Pydantic models for PPTX
│   │       ├── SlideLayout (enum)
│   │       ├── Theme (enum)
│   │       ├── Slide (dataclass)
│   │       ├── PresentationPlan
│   │       ├── PPTGenerationRequest
│   │       └── PPTGenerationResponse
│   │
│   ├── services/
│   │   ├── ppt/                       ✨ NEW - PPTX generation service
│   │   │   ├── __init__.py
│   │   │   ├── generator.py           (700+ lines)
│   │   │   └── themes.py              (planned for future)
│   │   │
│   │   ├── ai_service.py              (existing - reused)
│   │   │   └── AIToolsService._generate_text_with_provider()
│   │   │
│   │   └── asset_storage_service.py   (existing - reused)
│   │       └── AssetStorageService.upload_asset()
│   │
│   ├── routers/
│   │   ├── presentations.py           ✨ NEW - FastAPI endpoints
│   │   │   ├── POST /api/v1/presentations/generate
│   │   │   └── GET /api/v1/presentations/{id}
│   │   │
│   │   └── auth.py                    (existing - reused)
│   │       └── get_current_user_auth
│   │
│   ├── models/
│   │   ├── user.py                    (existing - reused)
│   │   ├── asset.py                   (existing - reused)
│   │   │   └── AIAsset model
│   │   └── ...
│   │
│   ├── db/
│   │   └── session.py                 (existing - reused)
│   │       └── get_session
│   │
│   └── main.py                        (modified)
│       └── app.include_router(presentations_router)
│
├── tests/
│   └── test_ppt_generation.py         ✨ NEW - Comprehensive test suite
│       ├── TestPPTXGeneration
│       ├── TestPresentationPlanValidation
│       ├── TestPresentationEndpoint
│       ├── TestTextOverflowHandling
│       ├── TestUserIsolation
│       ├── TestAIResponseParsing
│       ├── TestStorageIntegration
│       └── TestEndToEndWorkflow
│
├── PPTX_IMPLEMENTATION.md             ✨ NEW - Implementation summary
├── PPTX_QUICK_REFERENCE.md            ✨ NEW - Quick reference guide
└── requirements.txt                   (no changes - all deps exist)
    ├── python-pptx>=0.6.21            (already present)
    ├── fastapi>=0.110.1               (already present)
    ├── pydantic>=2.12.5               (already present)
    └── ...
```

---

## 🔄 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT REQUEST                           │
│  POST /api/v1/presentations/generate                             │
│  { prompt, slide_count, theme, provider }                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────┐
        │  AUTHENTICATION LAYER           │
        │  get_current_user_auth()        │
        │  ✓ Verify JWT token             │
        │  ✓ Extract user_id              │
        └────────┬──────────────────────┘
                 │
                 ▼
    ┌────────────────────────────────────┐
    │  VALIDATION LAYER                  │
    │  PPTGenerationRequest validation   │
    │  ✓ Prompt length (10-2000 chars)   │
    │  ✓ Slide count (3-200)             │
    │  ✓ Theme enum check                │
    └────────┬──────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│  AI TEXT GENERATION                          │
│  AIToolsService.generate_text()              │
│  ✓ Calls: Gemini, Groq, OpenAI, etc.       │
│  ✓ Provider: auto-routing with fallback      │
│  ✓ Returns: JSON string (not binary)         │
└────────┬──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  JSON PARSING                                │
│  ✓ Clean markdown if wrapped                │
│  ✓ Parse JSON response                       │
│  ✓ Handle multiple AI formats                │
│  ✗ Fail if invalid JSON                      │
└────────┬──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  SCHEMA VALIDATION                           │
│  Pydantic PresentationPlan validation        │
│  ✓ SlideLayout enum checks                   │
│  ✓ Slide number sequencing                   │
│  ✓ Text length constraints                   │
│  ✓ Table/Chart structure validation          │
│  ✗ Fail if invalid structure                 │
└────────┬──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  PPTX FILE GENERATION                        │
│  PPTGenerator.generate()                     │
│  ✓ Apply theme colors                        │
│  ✓ Render each slide with layout             │
│  ✓ Add text, bullets, tables, charts         │
│  ✓ Text overflow protection                  │
│  ✓ Return PPTX bytes (ZIP format)            │
└────────┬──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  ASSET STORAGE                               │
│  AssetStorageService.upload_asset()          │
│  ✓ Upload to R2 or local filesystem          │
│  ✓ SHA-256 deduplication                     │
│  ✓ Path: /users/{user_id}/...               │
│  ✓ Return proxy URL (never raw URL)          │
└────────┬──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  DATABASE METADATA                           │
│  Save AIAsset record                         │
│  ✓ user_id (from verified token)             │
│  ✓ asset_type = "presentation"               │
│  ✓ file_size_bytes                           │
│  ✓ proxy_url                                 │
│  ✓ metadata JSON (prompt, theme, etc.)       │
└────────┬──────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────┐
│  RESPONSE TO CLIENT                          │
│  {                                           │
│    "success": true,                          │
│    "presentation_id": "uuid",                │
│    "attachment_id": 42,                      │
│    "proxy_url": "https://cdn.../file.pptx"  │
│  }                                           │
└──────────────────────────────────────────────┘
```

---

## 🏗️ Component Architecture

### Layer 1: Presentation Schemas (Input/Output)

```
schemas/presentations.py
│
├── SlideLayout (enum)
│   └── 11 layout types
│
├── Theme (enum)
│   └── 5 color themes
│
├── Slide (dataclass)
│   ├── slide_number: int
│   ├── layout: SlideLayout
│   ├── title: str
│   ├── bullets: List[str]
│   ├── table: Optional[Table]
│   ├── chart: Optional[Chart]
│   └── ... (10+ fields)
│
├── PresentationPlan (dataclass)
│   ├── title: str
│   ├── slides: List[Slide]
│   ├── theme: Theme
│   └── validation: slides must be sequential 1..N
│
└── API Models
    ├── PPTGenerationRequest
    └── PPTGenerationResponse
```

### Layer 2: Generator Service (PPTX Creation)

```
services/ppt/
│
├── generator.py
│   └── PPTGenerator
│       ├── __init__(plan: PresentationPlan)
│       ├── generate() → bytes
│       ├── _add_slide(spec)
│       ├── _add_title_slide()
│       ├── _add_content_slide()
│       ├── _add_two_column_slide()
│       ├── _add_table_slide()
│       ├── _add_chart_slide()
│       └── THEMES (5 color palettes)
│
└── __init__.py
    └── generate_pptx(plan) → bytes
```

### Layer 3: API Endpoints (Request Handling)

```
routers/presentations.py
│
├── @router.post("/generate")
│   └── generate_presentation()
│       ├── Verify auth (get_current_user_auth)
│       ├── Validate request (PPTGenerationRequest)
│       ├── Generate plan (AIToolsService)
│       ├── Parse JSON response
│       ├── Validate schema (PresentationPlan)
│       ├── Create PPTX (PPTGenerator)
│       ├── Upload file (AssetStorageService)
│       ├── Save metadata (database)
│       └── Return proxy URL
│
└── @router.get("/{presentation_id}")
    └── get_presentation_details()
        ├── Verify auth
        ├── Verify ownership
        └── Return metadata
```

---

## 🔐 Security Layers

### Layer 1: Authentication

```
Request Headers
    ↓
JWT Token validation (get_current_user_auth)
    ↓
User ID extraction from token (never from request)
    ↓
User object injected as dependency
```

### Layer 2: Authorization

```
User object available in endpoint
    ↓
Verify user_id from token matches asset owner
    ↓
Query database filtered by user_id
    ↓
Return 404 if ownership check fails
```

### Layer 3: Input Validation

```
Request payload
    ↓
Pydantic schema validation
    ↓
Type checking + constraints (lengths, ranges)
    ↓
Rejection if invalid
```

### Layer 4: Output Sanitization

```
Generated PPTX file
    ↓
Upload to storage (R2 or local)
    ↓
Generate proxy URL (never raw URL)
    ↓
Return proxy URL only (client can't see S3 path)
```

---

## 🧪 Testing Architecture

```
tests/test_ppt_generation.py

├── UNIT TESTS (Low-level)
│   ├── TestPPTXGeneration
│   │   └── Test python-pptx library integration
│   ├── TestPresentationPlanValidation
│   │   └── Test Pydantic schema validation
│   └── TestAIResponseParsing
│       └── Test JSON parsing from different AI formats
│
├── INTEGRATION TESTS (Mid-level)
│   ├── TestTextOverflowHandling
│   │   └── Test text constraint enforcement
│   ├── TestStorageIntegration
│   │   └── Test AssetStorageService mocking
│   └── TestUserIsolation
│       └── Test user ownership verification
│
└── SMOKE TESTS (High-level)
    └── TestEndToEndWorkflow
        └── Test complete workflow from plan to file
```

---

## 📊 State Machine: Request Lifecycle

```
        ┌─────────────────┐
        │ REQUEST RECEIVED│
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ AUTHENTICATE    │
        │ ✓ JWT valid?    │
        └────┬───────────┘
             │ NO
             ├──→ 401 Unauthorized ──→ RETURN
             │
             │ YES
             ▼
        ┌─────────────────┐
        │ VALIDATE INPUT  │
        │ ✓ Schema OK?    │
        └────┬───────────┘
             │ NO
             ├──→ 422 Unprocessable ──→ RETURN
             │
             │ YES
             ▼
        ┌─────────────────┐
        │ GENERATE PLAN   │
        │ ✓ AI success?   │
        └────┬───────────┘
             │ NO
             ├──→ 500 Error ──→ RETURN
             │
             │ YES
             ▼
        ┌─────────────────┐
        │ PARSE JSON      │
        │ ✓ Valid JSON?   │
        └────┬───────────┘
             │ NO
             ├──→ 500 Error ──→ RETURN
             │
             │ YES
             ▼
        ┌─────────────────┐
        │ VALIDATE PLAN   │
        │ ✓ Schema OK?    │
        └────┬───────────┘
             │ NO
             ├──→ 422 Unprocessable ──→ RETURN
             │
             │ YES
             ▼
        ┌─────────────────┐
        │ CREATE PPTX     │
        │ ✓ Success?      │
        └────┬───────────┘
             │ NO
             ├──→ 500 Error ──→ RETURN
             │
             │ YES
             ▼
        ┌─────────────────┐
        │ UPLOAD FILE     │
        │ ✓ Success?      │
        └────┬───────────┘
             │ NO
             ├──→ 500 Error ──→ RETURN
             │
             │ YES
             ▼
        ┌─────────────────┐
        │ SAVE METADATA   │
        │ ✓ Success?      │
        └────┬───────────┘
             │ NO
             ├──→ 500 Error ──→ RETURN
             │
             │ YES
             ▼
        ┌──────────────────────┐
        │ 200 OK + Proxy URL   │
        │ SUCCESS              │
        └──────────────────────┘
```

---

## 🔌 Integration Points

### With Existing VedaApex Systems

```
app.services.ai_service.AIToolsService
    │
    ├─ Used by: generate_presentation()
    ├─ Method: generate_text()
    ├─ Returns: JSON structure
    └─ Supports: Gemini, Groq, OpenAI, FAL, Replicate, etc.

app.services.asset_storage_service.AssetStorageService
    │
    ├─ Used by: generate_presentation()
    ├─ Method: upload_asset()
    ├─ Stores: R2 (Cloudflare) or local filesystem
    └─ Returns: proxy_url (never raw URL)

app.routers.auth.get_current_user_auth
    │
    ├─ Used by: @Depends(get_current_user_auth)
    ├─ Verifies: JWT token
    └─ Returns: User object with id

app.db.session.get_session
    │
    ├─ Used by: @Depends(get_session)
    ├─ Provides: SQLModel session
    └─ Used for: AIAsset metadata persistence

app.models.asset.AIAsset
    │
    ├─ Used by: Metadata storage
    ├─ Fields: user_id, asset_type, proxy_url, file_size_bytes
    └─ Query: filtered by user_id
```

---

## 📈 Performance Characteristics

| Operation | Duration | Notes |
|-----------|----------|-------|
| AI Text Generation | 2-8s | Depends on provider & response size |
| PPTX Creation | <1s | python-pptx is fast |
| R2 Upload | 1-3s | Network dependent |
| Database Save | <100ms | Local transaction |
| **Total Request Time** | **4-12s** | Mostly waiting on AI |

---

## 🔄 Dependency Graph

```
presentations.py (router)
    │
    ├─→ app.schemas.presentations
    ├─→ app.services.ppt
    │   ├─→ app.schemas.presentations
    │   └─→ python-pptx library
    │
    ├─→ app.services.ai_service
    │   └─→ app.services.providers
    │       ├─→ groq_provider
    │       ├─→ gemini_provider
    │       └─→ ... (50+ providers)
    │
    ├─→ app.services.asset_storage_service
    │   └─→ boto3 (S3/R2)
    │
    ├─→ app.routers.auth
    │   └─→ app.models.user
    │
    └─→ app.db.session
        └─→ app.models.asset
```

---

## ✨ Design Patterns Used

### 1. **Dependency Injection**
- FastAPI dependencies for auth, session, request validation
- Follows VedaApex conventions

### 2. **Validation Layer**
- Pydantic models separate API contracts from implementation
- Schema validation at multiple levels

### 3. **Service Encapsulation**
- PPTGenerator handles low-level PPTX creation
- Public API in __init__.py hides implementation

### 4. **Structured Error Handling**
- HTTPException with status codes
- Safe error messages (no stack traces to client)
- Full logging server-side

### 5. **Provider Abstraction**
- AI text generation abstraction (AIToolsService)
- Multiple provider support with auto-routing
- Fallback logic when primary provider fails

---

## 🎓 Extension Points (Future)

### Feature 1: Custom Slide Layouts
```python
# Future: add custom_layouts parameter
layouts = {
    "my_layout": CustomSlideLayout(...)
}
generator = PPTGenerator(plan, custom_layouts=layouts)
```

### Feature 2: Image Insertion
```python
# Future: auto-download images
Slide(
    ...
    image_urls=["https://example.com/image.png"],
    image_alignment="left"
)
```

### Feature 3: Template System
```python
# Future: load presentation from template
generator = PPTGenerator(plan, template="corporate_2026")
```

### Feature 4: Caching
```python
# Future: cache presentations by hash
cache_key = hash(plan.dumps())
if cache[cache_key]:
    return cached_pptx_bytes
```

---

## 📝 Summary

The PowerPoint generation system is designed with:

✅ **Clean Architecture** - Layered separation of concerns
✅ **Security First** - Authentication, authorization, validation
✅ **Integration Ready** - Uses existing VedaApex infrastructure
✅ **Highly Testable** - Isolated components, comprehensive test suite
✅ **Production Ready** - Error handling, logging, monitoring
✅ **Future Proof** - Extensible design for new features
