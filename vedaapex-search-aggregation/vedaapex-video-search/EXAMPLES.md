# API Usage Examples

## Python Examples

### Using httpx

```python
import httpx
import asyncio

# Async HTTP client
async def search_images_async():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={
                "q": "mountain landscape",
                "page": 1,
                "page_size": 20,
                "sort": "latest"
            }
        )
        data = response.json()
        print(f"Found {len(data['results'])} images")
        for image in data['results']:
            print(f"  - {image['title']} by {image['photographer']}")

# Run
asyncio.run(search_images_async())
```

### Using requests

```python
import requests

def search_videos():
    response = requests.get(
        "http://localhost:8000/api/v1/videos/search",
        params={
            "q": "sunset",
            "page": 1,
            "page_size": 10
        }
    )
    data = response.json()
    
    if data['success']:
        for video in data['results']:
            print(f"{video['id']}: {video['duration']}s")
    else:
        print(f"Error: {data['error']}")

search_videos()
```

### With Authentication

```python
import httpx

async def search_with_auth(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={"q": "nature"},
            headers=headers
        )
        return response.json()
```

---

## cURL Examples

### Image Search

```bash
# Basic search
curl "http://localhost:8000/api/v1/images/search?q=nature"

# With pagination
curl "http://localhost:8000/api/v1/images/search?q=mountain&page=2&page_size=30"

# With sorting
curl "http://localhost:8000/api/v1/images/search?q=sunset&sort=popular"
```

### Video Search

```bash
# Basic search
curl "http://localhost:8000/api/v1/videos/search?q=nature"

# With options
curl "http://localhost:8000/api/v1/videos/search?q=rain&page=1&page_size=15"
```

### Health Check

```bash
curl http://localhost:8000/api/v1/health
```

### Cache Management

```bash
# Get cache stats
curl http://localhost:8000/api/v1/cache/stats

# Clear cache
curl -X POST http://localhost:8000/api/v1/cache/clear
```

### With Authentication

```bash
# Header method
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "http://localhost:8000/api/v1/images/search?q=nature"

# Custom header
curl -H "X-API-Key: YOUR_API_KEY" \
  "http://localhost:8000/api/v1/images/search?q=nature"

# Query parameter
curl "http://localhost:8000/api/v1/images/search?q=nature&api_key=YOUR_API_KEY"
```

---

## JavaScript Examples

### Using Fetch API

```javascript
// Image search
async function searchImages() {
  const response = await fetch(
    'http://localhost:8000/api/v1/images/search?q=nature&page=1&page_size=20'
  );
  const data = await response.json();
  console.log(data.results);
}

// With authentication
async function searchWithAuth(apiKey) {
  const response = await fetch(
    'http://localhost:8000/api/v1/images/search?q=mountain',
    {
      headers: {
        'Authorization': `Bearer ${apiKey}`
      }
    }
  );
  return response.json();
}

searchImages();
```

### Using Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY'
  }
});

// Image search
async function searchImages(query) {
  try {
    const response = await api.get('/images/search', {
      params: {
        q: query,
        page: 1,
        page_size: 20
      }
    });
    console.log(response.data);
  } catch (error) {
    console.error('Error:', error.response.data);
  }
}

// Video search
async function searchVideos(query) {
  const response = await api.get('/videos/search', {
    params: { q: query }
  });
  return response.data;
}

searchImages('nature');
```

---

## Response Examples

### Successful Image Search

```json
{
  "success": true,
  "query": "mountain",
  "provider": "pexels",
  "results": [
    {
      "id": "2387793",
      "title": "Person rock climbing",
      "image_url": "https://images.pexels.com/...",
      "thumbnail_url": "https://images.pexels.com/...",
      "photographer": "Andrew Butler",
      "photographer_url": "https://www.pexels.com/@andrew",
      "source_url": "https://www.pexels.com/photo/...",
      "width": 5456,
      "height": 3632,
      "avg_color": "#9CA5A8"
    },
    {
      "id": "1252500",
      "title": "Timelapse Photography of Pink Sky",
      "image_url": "https://images.pexels.com/...",
      "thumbnail_url": "https://images.pexels.com/...",
      "photographer": "Mikhail Nilov",
      "photographer_url": "https://www.pexels.com/@mikhail",
      "source_url": "https://www.pexels.com/photo/...",
      "width": 6000,
      "height": 4000,
      "avg_color": "#D08070"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 8000,
    "has_next": true
  },
  "timestamp": "2024-01-15T14:30:00",
  "cached": false
}
```

### Successful Video Search

```json
{
  "success": true,
  "query": "nature",
  "provider": "pexels",
  "results": [
    {
      "id": "3571551",
      "video_url": "https://videos.pexels.com/...",
      "thumbnail_url": "https://images.pexels.com/...",
      "duration": 20,
      "creator": "Tobias Tullius",
      "source_url": "https://www.pexels.com/video/...",
      "width": 1920,
      "height": 1080
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 5000,
    "has_next": true
  },
  "timestamp": "2024-01-15T14:30:00",
  "cached": false
}
```

### Error Response

```json
{
  "success": false,
  "error": "ValidationError",
  "message": "Query must be at least 1 character",
  "status_code": 400,
  "timestamp": "2024-01-15T14:30:00"
}
```

### Cached Response

```json
{
  "success": true,
  "query": "sunset",
  "provider": "pexels",
  "results": [...],
  "pagination": {...},
  "timestamp": "2024-01-15T14:25:00",
  "cached": true
}
```

### Health Response

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-15T14:30:00",
  "uptime": 3600.5,
  "cache_status": "operational"
}
```

---

## Pagination Examples

### First Page

```bash
curl "http://localhost:8000/api/v1/images/search?q=nature&page=1&page_size=20"
```

### Next Page

```bash
# Response indicates has_next: true
curl "http://localhost:8000/api/v1/images/search?q=nature&page=2&page_size=20"
```

### Different Page Sizes

```bash
# 50 results per page
curl "http://localhost:8000/api/v1/images/search?q=nature&page_size=50"

# Max 80 results
curl "http://localhost:8000/api/v1/images/search?q=nature&page_size=80"
```

---

## Error Handling Examples

### Python Error Handling

```python
import httpx
from typing import Optional, Dict, Any

async def search_with_error_handling(query: str) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "http://localhost:8000/api/v1/images/search",
                params={"q": query}
            )
            
            # Check for HTTP errors
            if response.status_code == 401:
                print("Authentication failed - check API key")
                return None
            elif response.status_code == 429:
                print("Rate limited - wait 60 seconds")
                return None
            elif response.status_code >= 500:
                print("Server error - try again later")
                return None
            
            # Check response
            data = response.json()
            if not data.get('success'):
                print(f"API error: {data.get('message')}")
                return None
                
            return data
            
    except httpx.TimeoutException:
        print("Request timed out")
        return None
    except httpx.ConnectError:
        print("Connection failed")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
```

### JavaScript Error Handling

```javascript
async function searchImagesWithErrorHandling(query) {
  try {
    const response = await fetch(
      `http://localhost:8000/api/v1/images/search?q=${encodeURIComponent(query)}`
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(`${response.status}: ${error.message}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(`API Error: ${data.error}`);
    }
    
    return data;
    
  } catch (error) {
    console.error('Search failed:', error.message);
    // Handle error appropriately
    return null;
  }
}
```

---

## Performance Tips

### Caching Strategy

```python
# Cache is automatic and transparent
# First request: fetches from API
# Second request (same query, same page): served from cache (1-hour default)

# Cached responses include: "cached": true
```

### Pagination Best Practices

```bash
# Good: Fetch 20-30 results per request
curl "http://localhost:8000/api/v1/images/search?q=nature&page_size=20"

# Avoid: Requesting too many results
# Max: 80 per page
```

### Rate Limiting

```bash
# Respect the rate limit (default: 60 req/min per IP)
# Check response headers:
# X-RateLimit-Limit: 60
# X-RateLimit-Remaining: 45

# Implement exponential backoff for retries
```

---

## Batch Processing

### Multiple Searches

```python
import asyncio
import httpx

async def batch_search(queries: list[str]):
    async with httpx.AsyncClient() as client:
        tasks = []
        for query in queries:
            task = client.get(
                "http://localhost:8000/api/v1/images/search",
                params={"q": query}
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]

# Search multiple queries
results = asyncio.run(batch_search(["nature", "sunset", "mountain"]))
```

---

## Integration Examples

### Save Results to CSV

```python
import csv
import asyncio
import httpx

async def save_search_results(query: str, filename: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={"q": query, "page_size": 80}
        )
        data = response.json()
        
        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'title', 'photographer', 'image_url'])
            writer.writeheader()
            for result in data['results']:
                writer.writerow({
                    'id': result['id'],
                    'title': result['title'],
                    'photographer': result['photographer'],
                    'image_url': result['image_url']
                })

asyncio.run(save_search_results("sunset", "sunsets.csv"))
```

### Display in Web App

```javascript
async function displayImageGallery(query) {
  const response = await fetch(
    `http://localhost:8000/api/v1/images/search?q=${query}&page_size=40`
  );
  const data = await response.json();
  
  const gallery = document.getElementById('gallery');
  gallery.innerHTML = data.results.map(img => `
    <div class="image-item">
      <img src="${img.thumbnail_url}" alt="${img.title}" />
      <p>${img.title}</p>
      <small>by ${img.photographer}</small>
      <a href="${img.source_url}" target="_blank">View on Pexels</a>
    </div>
  `).join('');
}
```
