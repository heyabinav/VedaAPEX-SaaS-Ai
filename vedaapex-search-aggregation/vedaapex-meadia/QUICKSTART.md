# Quickstart Guide

Get VedaApex Media running in 60 seconds!

## 60-Second Setup

### 1. Install & Run (Choose One)

**Option A: Automated (macOS/Linux)**

```bash
chmod +x setup.sh && ./setup.sh
```

**Option B: Automated (Windows)**

```cmd
setup.bat
```

**Option C: Manual**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

### 2. Test API

```bash
curl "http://localhost:8000/api/v1/images/search?q=wildl
ife&page=1&page_size=5"
```

### 3. View Docs

Open: http://localhost:8000/api/v1/docs

---

## 5-Minute Tutorial

### Step 1: Search Images

```bash
# Basic image search
curl "http://localhost:8000/api/v1/images/search?q=butterfly"

# With pagination
curl "http://localhost:8000/api/v1/images/search?q=butterfly&page=1&page_size=10"
```

**Response:**

```json
{
  "success": true,
  "provider": "wikimedia",
  "query": "butterfly",
  "results": [
    {
      "title": "File:Papilio_machaon_01.jpg",
      "media_type": "image",
      "image_url": "https://upload.wikimedia.org/...",
      "thumbnail_url": "https://upload.wikimedia.org/...",
      "source_url": "https://commons.wikimedia.org/wiki/File:Papilio_machaon_01.jpg",
      "width": 1600,
      "height": 1200,
      "mime_type": "image/jpeg"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "has_next": true
  },
  "cached": false
}
```

### Step 2: Search Videos

```bash
curl "http://localhost:8000/api/v1/videos/search?q=ocean&page_size=5"
```

### Step 3: Check Health

```bash
curl "http://localhost:8000/api/v1/health"
```

---

## Common Tasks

### Configure Cache

Edit `.env`:

```env
# Use Redis (recommended for production)
CACHE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600

# Or use in-memory (default, single instance only)
CACHE_TYPE=memory
CACHE_MAX_SIZE=1000
```

### Adjust Rate Limiting

Edit `.env`:

```env
# Allow 100 requests per minute per IP
RATE_LIMIT_PER_MINUTE=100
```

### Change Port

Edit `.env`:

```env
PORT=9000
```

Then: `http://localhost:9000/api/v1/docs`

### Enable Debug Logging

Edit `.env`:

```env
LOG_LEVEL=DEBUG
```

### Add Custom Search Filters

Create file `filters.py`:

```python
def filter_by_mime_type(results, mime_type):
    """Filter results by MIME type."""
    return [r for r in results if r.get("mime_type") == mime_type]

def filter_by_size(results, min_width=0, min_height=0):
    """Filter results by image dimensions."""
    return [
        r for r in results
        if r.get("width", 0) >= min_width and r.get("height", 0) >= min_height
    ]
```

---

## Python Client Example

```python
import httpx
import asyncio
from typing import Dict, List

class VedaApexMediaClient:
    """VedaApex Media API client."""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
    
    async def search_images(self, query: str, page: int = 1, page_size: int = 20) -> Dict:
        """Search images."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/images/search",
                params={
                    "q": query,
                    "page": page,
                    "page_size": page_size,
                },
            )
            return response.json()
    
    async def search_videos(self, query: str, page: int = 1, page_size: int = 20) -> Dict:
        """Search videos."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/videos/search",
                params={
                    "q": query,
                    "page": page,
                    "page_size": page_size,
                },
            )
            return response.json()

# Usage
async def main():
    client = VedaApexMediaClient()
    
    # Search images
    images = await client.search_images("lion", page_size=5)
    print(f"Found {len(images['results'])} images")
    
    for result in images['results']:
        print(f"- {result['title']}")
        print(f"  {result['image_url']}")

asyncio.run(main())
```

---

## JavaScript Client Example

```javascript
class VedaApexMediaClient {
  constructor(baseUrl = "http://localhost:8000") {
    this.baseUrl = baseUrl;
    this.apiBase = `${baseUrl}/api/v1`;
  }

  async searchImages(query, page = 1, pageSize = 20) {
    const params = new URLSearchParams({
      q: query,
      page,
      page_size: pageSize,
    });

    const response = await fetch(
      `${this.apiBase}/images/search?${params}`
    );
    return await response.json();
  }

  async searchVideos(query, page = 1, pageSize = 20) {
    const params = new URLSearchParams({
      q: query,
      page,
      page_size: pageSize,
    });

    const response = await fetch(
      `${this.apiBase}/videos/search?${params}`
    );
    return await response.json();
  }
}

// Usage
const client = new VedaApexMediaClient();

client.searchImages("mountain", { pageSize: 10 })
  .then(data => {
    console.log(`Found ${data.results.length} images`);
    data.results.forEach(img => {
      console.log(`- ${img.title}`);
      console.log(`  ${img.thumbnail_url}`);
    });
  })
  .catch(err => console.error("Search error:", err));
```

---

## React Component Example

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function MediaSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mediaType, setMediaType] = useState('images');

  const search = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const endpoint = `/api/v1/${mediaType}/search`;
      const { data } = await axios.get(endpoint, {
        params: { q: query, page_size: 10 },
      });

      setResults(data.results || []);
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>VedaApex Media Search</h1>

      <div>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search..."
          onKeyPress={(e) => e.key === 'Enter' && search()}
        />
        <button onClick={search}>Search</button>
      </div>

      <div>
        <label>
          <input
            type="radio"
            value="images"
            checked={mediaType === 'images'}
            onChange={(e) => setMediaType(e.target.value)}
          />
          Images
        </label>
        <label>
          <input
            type="radio"
            value="videos"
            checked={mediaType === 'videos'}
            onChange={(e) => setMediaType(e.target.value)}
          />
          Videos
        </label>
      </div>

      {loading && <p>Loading...</p>}

      <div className="results">
        {results.map((result) => (
          <div key={result.title} className="result-card">
            <img src={result.thumbnail_url} alt={result.title} />
            <h3>{result.title}</h3>
            <a href={result.source_url} target="_blank" rel="noopener noreferrer">
              View on Wikimedia
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

export default MediaSearch;
```

---

## Troubleshooting

### "Connection refused"

```bash
# Make sure server is running
python app.py

# Check port
lsof -i :8000
```

### Empty results

```bash
# Try different search terms
curl "http://localhost:8000/api/v1/images/search?q=earth"

# Check Wikimedia Commons directly
# https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=earth
```

### Slow responses

```bash
# Enable cache
CACHE_ENABLED=true
CACHE_TYPE=redis

# Increase page size
/search?q=...&page_size=50
```

### Rate limit errors

```bash
# Increase limit in .env
RATE_LIMIT_PER_MINUTE=100

# Or add delay between requests in your code
await asyncio.sleep(1)  # 1 second delay
```

---

## Next Steps

1. ✅ API is running
2. ✅ Made first search
3. 📖 Read [ARCHITECTURE.md](ARCHITECTURE.md) for deep dive
4. 🚀 See [EXAMPLES.md](EXAMPLES.md) for more code samples
5. 📋 Check [FILE_MANIFEST.md](FILE_MANIFEST.md) for code overview
6. 🌐 Deploy with [INSTALLATION.md](INSTALLATION.md)
