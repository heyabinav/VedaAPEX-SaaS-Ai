# 🔑 API Keys Summary - VedaApex Search Aggregation

## 📊 API Keys Needed (.env Structure)

### Tier 1: REQUIRED API Keys ⭐⭐⭐

```
1. PEXELS_API_KEY
   - Purpose: General images (nature, animals, people, city, etc.)
   - Provider: Pexels (Free)
   - Get from: https://www.pexels.com/api/
   - Status: REQUIRED ✅
   - Tier: Free (200 req/month)
   - Example: 563492ad6f91700000000000000000000

2. NASA_API_KEY
   - Purpose: Space images (mars, moon, astronaut, etc.)
   - Provider: NASA Open API (Free)
   - Get from: https://api.nasa.gov/
   - Status: HIGHLY RECOMMENDED ⭐
   - Tier: Free (Unlimited)
   - Default: DEMO_KEY (limited but works)
   - Example: abcd1234efgh5678ijkl9012mnop3456
```

### Tier 2: OPTIONAL API Keys ✅

```
3. WIKIMEDIA_API_KEY
   - Purpose: Scientific images (cancer, microscope, biology, etc.)
   - Provider: Wikimedia Commons (Completely FREE)
   - Status: OPTIONAL (No key needed!)
   - Tier: Free (Unlimited, No authentication)
   - Note: Leave empty - works without any key
   - Example: Leave blank or empty string
```

---

## 🗂️ Complete .env File Structure

### Copy this template and fill in your keys:

```ini
# ============================================
# 1. APPLICATION CONFIGURATION
# ============================================
APP_NAME=VedaApex Search Aggregation
APP_VERSION=1.0.0
APP_ENV=production
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO

# ============================================
# 2. API KEYS (IMPORTANT - Add your keys here)
# ============================================

# ⭐ PEXELS API KEY - REQUIRED
# Get from: https://www.pexels.com/api/
# Steps: Visit site → Click "Create API Key" → Sign up → Copy key
PEXELS_API_KEY=your_pexels_key_here

# ⭐ NASA API KEY - RECOMMENDED
# Get from: https://api.nasa.gov/
# Steps: Visit site → Enter email → Accept terms → Get key
# OR use default DEMO_KEY (limited usage)
NASA_API_KEY=DEMO_KEY

# ✅ WIKIMEDIA API KEY - OPTIONAL (No key needed!)
# Wikimedia Commons is completely free and requires no key
# Leave empty or use default
WIKIMEDIA_API_KEY=

# ============================================
# 3. PROVIDER ENABLEMENT
# ============================================
ENABLE_PEXELS=true
ENABLE_WIKIMEDIA=true
ENABLE_NASA=true

# ============================================
# 4. CACHE CONFIGURATION
# ============================================
CACHE_ENABLED=true
CACHE_TYPE=memory          # Options: memory (dev), redis (prod)
CACHE_TTL=3600            # Cache time: 1 hour
REDIS_URL=redis://localhost:6379/0

# ============================================
# 5. REQUEST CONFIGURATION
# ============================================
REQUEST_TIMEOUT=15        # Seconds per provider timeout
MAX_RESULTS=50           # Maximum results returned
DEFAULT_PAGE_SIZE=20     # Default results per page

# ============================================
# 6. RATE LIMITING
# ============================================
RATE_LIMIT_PER_MINUTE=60  # Requests per IP per minute

# ============================================
# 7. QUERY CONSTRAINTS
# ============================================
MIN_QUERY_LENGTH=2        # Minimum search query length
MAX_QUERY_LENGTH=200      # Maximum search query length

# ============================================
# 8. CORS SETTINGS
# ============================================
CORS_ORIGINS=["*"]        # Allow all origins (change for production!)
```

---

## 📋 Quick Reference: What Keys Do What?

### Query Type → Provider → API Key Needed

```
🌍 GENERAL QUERIES (nature, dog, city, travel)
   └─ Primary: PEXELS
      Required Key: PEXELS_API_KEY ✅

🚀 SPACE QUERIES (mars, moon, nasa, astronaut)
   └─ Primary: NASA
      Required Key: NASA_API_KEY ⭐

🔬 SCIENTIFIC QUERIES (cancer, cell, microscope)
   └─ Primary: WIKIMEDIA
      Required Key: None! (Free/No auth)
```

---

## 🛠️ Step-by-Step: Get Your API Keys

### Step 1: Pexels API Key (5 minutes) ⭐
```
1. Open: https://www.pexels.com/api/
2. Click "Create API Key" button
3. Sign up with email
4. Verify email
5. Copy API key from dashboard
6. Add to .env:
   PEXELS_API_KEY=your_copied_key
```

### Step 2: NASA API Key (2 minutes) ⭐
```
1. Open: https://api.nasa.gov/
2. Fill email in form
3. Accept terms & conditions
4. Get key instantly via email
5. Copy the API key
6. Add to .env:
   NASA_API_KEY=your_nasa_key
```

### Step 3: Wikimedia (No Key Needed!) ✅
```
Wikimedia Commons is 100% free and requires NO API key!
Just leave it empty:
   WIKIMEDIA_API_KEY=
```

---

## ✅ Complete .env Example

```ini
# Application
APP_NAME=VedaApex Search Aggregation
APP_VERSION=1.0.0
APP_ENV=production
PORT=8000
HOST=0.0.0.0
LOG_LEVEL=INFO

# API Keys - YOUR KEYS HERE!
PEXELS_API_KEY=563492ad6f917000000000000000000a
NASA_API_KEY=DEMO_KEY
WIKIMEDIA_API_KEY=

# Providers
ENABLE_PEXELS=true
ENABLE_WIKIMEDIA=true
ENABLE_NASA=true

# Cache
CACHE_ENABLED=true
CACHE_TYPE=memory
CACHE_TTL=3600
REDIS_URL=redis://localhost:6379/0

# Request
REQUEST_TIMEOUT=15
MAX_RESULTS=50
DEFAULT_PAGE_SIZE=20

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Query
MIN_QUERY_LENGTH=2
MAX_QUERY_LENGTH=200

# CORS
CORS_ORIGINS=["*"]
```

---

## 🚀 How to Use

### 1. Create .env File
```bash
cp .env.example .env
```

### 2. Edit .env and Add Your Keys
```bash
# Linux/macOS
nano .env

# Windows
notepad .env
```

### 3. Add Your API Keys
```
PEXELS_API_KEY=your_key_from_pexels
NASA_API_KEY=your_key_from_nasa
```

### 4. Run Application
```bash
python app.py
```

### 5. Test It Works
```bash
# Space query
curl "http://localhost:8000/api/v1/search?q=mars"

# Science query
curl "http://localhost:8000/api/v1/search?q=cancer+cell"

# General query
curl "http://localhost:8000/api/v1/search?q=nature"
```

---

## 🐳 Docker Deployment

```bash
# Build image
docker build -t vedaapex-search .

# Run with your API keys
docker run -p 8000:8000 \
  -e PEXELS_API_KEY=your_key \
  -e NASA_API_KEY=your_key \
  -e CACHE_TYPE=redis \
  vedaapex-search
```

---

## 🌐 Production Deployment

### Environment Variables Setup

```bash
# On Render, Heroku, AWS, etc.
# Set these environment variables:

PEXELS_API_KEY=your_key
NASA_API_KEY=your_key
CACHE_TYPE=redis
REDIS_URL=your_redis_url
LOG_LEVEL=WARNING
CORS_ORIGINS=["https://yourdomain.com"]
```

---

## 🔍 Verify Setup

### Check Health
```bash
curl "http://localhost:8000/api/v1/health"

# Response shows enabled providers:
# {
#   "status": "healthy",
#   "providers": ["pexels", "wikimedia", "nasa"]
# }
```

### Test Each Provider

**Test Pexels:**
```bash
curl "http://localhost:8000/api/v1/search?q=nature&media_type=image"
```

**Test NASA:**
```bash
curl "http://localhost:8000/api/v1/search?q=mars&media_type=image"
```

**Test Wikimedia:**
```bash
curl "http://localhost:8000/api/v1/search?q=cancer+cell&media_type=image"
```

---

## 📊 API Key Limits

| Provider | Free Tier | Cost | Limit |
|----------|:---------:|:----:|:-----:|
| **Pexels** | ✅ Free | $0 | 200/month |
| **NASA** | ✅ Free | $0 | Unlimited |
| **Wikimedia** | ✅ Free | $0 | Unlimited |

---

## ⚠️ Security Checklist

- [ ] ✅ Never commit .env file (add to .gitignore)
- [ ] ✅ Keep API keys SECRET
- [ ] ✅ Use environment variables in production
- [ ] ✅ Rotate keys periodically
- [ ] ✅ Use HTTPS for production
- [ ] ✅ Monitor API usage
- [ ] ✅ Set CORS_ORIGINS correctly
- [ ] ✅ Use Redis for production cache

---

## 🎯 Minimal Setup (Get Started Quickly)

```ini
# Just these 3 lines minimum:
PEXELS_API_KEY=your_pexels_key
NASA_API_KEY=DEMO_KEY
WIKIMEDIA_API_KEY=
```

---

## 📞 Troubleshooting

### "API Key Invalid"
- Check key is copied completely (no spaces)
- Verify key is valid on provider website
- Make sure .env file is being read

### "Provider Returned Error"
- Check API quota/limit on provider dashboard
- Verify API key is still active
- Check network connection

### "All Providers Failed"
- Check .env file exists and has correct keys
- Verify at least one provider is enabled
- Check logs: `tail -f logs/app.log`

---

## 📚 Full Documentation

See these files for more details:

- **API_KEYS.md** - Detailed API keys guide
- **README.md** - Project overview
- **QUICKSTART.md** - 60-second setup
- **ARCHITECTURE.md** - System design
- **INTELLIGENT_ROUTING.md** - How routing works
- **PROJECT_SUMMARY.md** - Project completion details

---

## 🎉 GitHub Repository

**Pushed to:** https://github.com/himanshukumar276129-art/verbose-barnacle.git

**Contents:**
- ✅ 38 files
- ✅ Complete source code
- ✅ Full documentation
- ✅ Test suite
- ✅ Docker support
- ✅ Setup scripts

---

## 🚀 Ready to Deploy!

1. Get your API keys (5-10 minutes)
2. Create .env file
3. Add keys to .env
4. Run: `python app.py`
5. Visit: `http://localhost:8000/api/v1/docs`

**Happy searching! 🔍✨**
