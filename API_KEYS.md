# API Keys Configuration Guide

## 🔑 Required & Optional API Keys

### Tier 1: REQUIRED for Production
These keys are essential to make searches work:

#### 1. **PEXELS_API_KEY** ⭐ REQUIRED
- **Purpose**: General image search (nature, animals, people, etc.)
- **Provider**: Pexels
- **Free Tier**: ✅ Yes (free API)
- **How to Get**:
  1. Go to https://www.pexels.com/api/
  2. Click "Create API Key"
  3. Sign up or login
  4. Copy your API key
- **Usage**: Used for general queries (default primary provider)
- **Requests/Month**: 200 requests/month (free tier)
- **Example Key Format**: `563492ad6f91700000000000000000000`

#### 2. **NASA_API_KEY** ⭐ HIGHLY RECOMMENDED
- **Purpose**: Space images and NASA data
- **Provider**: NASA Open API
- **Free Tier**: ✅ Yes (free API)
- **Default Value**: `DEMO_KEY` (limited but works)
- **How to Get**:
  1. Go to https://api.nasa.gov/
  2. Enter your email
  3. Agree to terms
  4. Instant API key via email
  5. Copy from email or regenerate at https://api.nasa.gov/
- **Usage**: Used for space-related queries (primary for "mars", "moon", etc.)
- **Requests/Hour**: Unlimited (free tier)
- **Example Key Format**: `abcd1234efgh5678ijkl9012mnop3456`

#### 3. **WIKIMEDIA_API_KEY** ✅ OPTIONAL
- **Purpose**: Scientific and general images from Wikimedia Commons
- **Provider**: Wikimedia Foundation
- **Free Tier**: ✅ Yes (completely free, no key needed)
- **Authentication**: Does NOT require API key
- **Usage**: Used for scientific queries (medical, biology, etc.)
- **Requests**: Unlimited
- **Note**: Leave empty or omit - works without any key

---

## 📋 .env File Structure

### Complete .env Template

```bash
# ============================================
# APPLICATION SETTINGS
# ============================================
APP_NAME=VedaApex Search Aggregation
APP_VERSION=1.0.0
APP_ENV=production
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO

# ============================================
# API KEYS (⭐ = Required/Recommended)
# ============================================

# PEXELS API - For general image search ⭐
# Get from: https://www.pexels.com/api/
PEXELS_API_KEY=your_pexels_key_here

# NASA API - For space images ⭐
# Get from: https://api.nasa.gov/
# Default: DEMO_KEY (limited but works)
NASA_API_KEY=your_nasa_key_here

# WIKIMEDIA API - For scientific images ✅
# Free! No key needed - leave empty or use: wikimedia_user_agent_header
WIKIMEDIA_API_KEY=

# ============================================
# PROVIDER SETTINGS
# ============================================
ENABLE_PEXELS=true
ENABLE_WIKIMEDIA=true
ENABLE_NASA=true

# ============================================
# CACHE SETTINGS
# ============================================
CACHE_ENABLED=true
CACHE_TYPE=memory          # Options: memory, redis
CACHE_TTL=3600            # Seconds (1 hour)
REDIS_URL=redis://localhost:6379/0

# ============================================
# REQUEST SETTINGS
# ============================================
REQUEST_TIMEOUT=15        # Seconds per provider
MAX_RESULTS=50           # Max results to return
DEFAULT_PAGE_SIZE=20     # Default results per page

# ============================================
# RATE LIMITING
# ============================================
RATE_LIMIT_PER_MINUTE=60  # Requests per minute per IP

# ============================================
# QUERY SETTINGS
# ============================================
MIN_QUERY_LENGTH=2        # Minimum query characters
MAX_QUERY_LENGTH=200      # Maximum query characters

# ============================================
# CORS SETTINGS
# ============================================
CORS_ORIGINS=["*"]        # Allow all origins (change in production)
```

---

## 🛠️ Step-by-Step Setup

### Step 1: Get Pexels API Key (5 minutes)
```bash
1. Visit: https://www.pexels.com/api/
2. Click "Create API Key" button
3. Sign up or login with email
4. Verify email if needed
5. Copy API key from dashboard
6. Add to .env:
   PEXELS_API_KEY=your_key_here
```

### Step 2: Get NASA API Key (2 minutes)
```bash
1. Visit: https://api.nasa.gov/
2. Fill in form with your email
3. Accept terms
4. Get API key instantly in email
5. Copy API key
6. Add to .env:
   NASA_API_KEY=your_key_here
```

### Step 3: Wikimedia (No Key Needed!)
```bash
# Wikimedia Commons is completely free and requires no API key!
# Just leave WIKIMEDIA_API_KEY empty:
WIKIMEDIA_API_KEY=
```

### Step 4: Create .env File
```bash
# Copy template
cp .env.example .env

# Edit with your keys
nano .env   # or use your favorite editor

# Windows:
notepad .env
```

### Step 5: Verify Setup
```bash
# Run the app
python app.py

# Test endpoints
curl "http://localhost:8000/api/v1/search?q=mars"
curl "http://localhost:8000/api/v1/health"
```

---

## 🔄 Provider Priority by Query Type

### How Keys Are Used

**Space Queries** (mars, moon, nasa, astronaut):
```
Primary: NASA_API_KEY (required)
Fallbacks: Wikimedia (free) → Pexels (optional)
```

**Scientific Queries** (cancer, cell, microscope):
```
Primary: Wikimedia (free, no key needed)
Fallbacks: NASA → Pexels
```

**General Queries** (nature, dog, city):
```
Primary: PEXELS_API_KEY (required)
Fallbacks: Wikimedia → NASA
```

---

## ⚙️ Configuration Examples

### Minimal Production Setup (2 keys)
```bash
PEXELS_API_KEY=your_pexels_key
NASA_API_KEY=your_nasa_key
ENABLE_PEXELS=true
ENABLE_WIKIMEDIA=true
ENABLE_NASA=true
CACHE_TYPE=redis
```

### Development Setup (1 key)
```bash
PEXELS_API_KEY=your_pexels_key
NASA_API_KEY=DEMO_KEY      # Use demo key
ENABLE_PEXELS=true
ENABLE_WIKIMEDIA=true
ENABLE_NASA=true
CACHE_TYPE=memory
```

### Testing Setup (No keys needed)
```bash
# Using mock providers
ENABLE_PEXELS=true
ENABLE_WIKIMEDIA=true
ENABLE_NASA=true
# Keys can be empty - mock providers return dummy data
```

---

## 🚀 Deployment Checklist

### Before Production:
- [ ] ✅ Pexels API key obtained and tested
- [ ] ✅ NASA API key obtained and tested
- [ ] ✅ .env file created (never commit to git!)
- [ ] ✅ CORS_ORIGINS updated (remove ["*"] for production)
- [ ] ✅ LOG_LEVEL=WARNING (for production)
- [ ] ✅ CACHE_TYPE=redis (recommended for production)
- [ ] ✅ RATE_LIMIT_PER_MINUTE adjusted if needed
- [ ] ✅ All providers enabled if keys are available

### Docker Deployment:
```bash
docker run -p 8000:8000 \
  -e PEXELS_API_KEY=your_key \
  -e NASA_API_KEY=your_key \
  -e CACHE_TYPE=redis \
  vedaapex-search
```

### Render/Cloud Deployment:
Set environment variables in dashboard:
```
PEXELS_API_KEY = your_key
NASA_API_KEY = your_key
CACHE_TYPE = redis
REDIS_URL = your_redis_url
```

---

## 🔍 Testing API Keys

### Test Pexels
```bash
curl "http://localhost:8000/api/v1/search?q=nature&media_type=image"
```

### Test NASA
```bash
curl "http://localhost:8000/api/v1/search?q=mars&media_type=image"
```

### Test Wikimedia
```bash
curl "http://localhost:8000/api/v1/search?q=cancer%20cell&media_type=image"
```

### Check Health
```bash
curl "http://localhost:8000/api/v1/health"
```

Response shows enabled providers:
```json
{
  "status": "healthy",
  "providers": [
    "pexels",
    "wikimedia",
    "nasa"
  ]
}
```

---

## 📊 API Key Limits

| Provider | Free Tier | Paid Tier | Requests/Month |
|----------|:---------:|:---------:|:--------------:|
| **Pexels** | ✅ | Yes | 200/month |
| **NASA** | ✅ | No (free) | Unlimited |
| **Wikimedia** | ✅ | N/A | Unlimited |

---

## ⚠️ Security Notes

### Never Commit .env File
```bash
# Add to .gitignore (already done)
echo ".env" >> .gitignore

# Verify it's ignored
git status  # Should NOT show .env
```

### Environment Variables Priority
```
.env file > System environment > Default values
```

### Production Security
1. Use environment variables, NOT .env file
2. Store keys in secure secret manager:
   - AWS Secrets Manager
   - Azure Key Vault
   - Render Secrets
   - GitHub Secrets
3. Rotate keys periodically
4. Monitor API usage

---

## 🎯 Quick Reference

```
What I Need?
├─ For Space Search (mars, moon)
│  └─ NASA_API_KEY ✅
│
├─ For Science Search (cancer, cell)
│  └─ Nothing! (Wikimedia is free)
│
├─ For General Search (nature, city)
│  └─ PEXELS_API_KEY ✅
│
└─ For Best Results
   └─ All 3: Pexels + NASA + Wikimedia
```

---

**🎉 Ready to get your API keys? Start with [Step 1](#step-1-get-pexels-api-key-5-minutes)!**
