# Code Examples - Integration Guide

## Table of Contents
1. [cURL Examples](#curl-examples)
2. [Python Examples](#python-examples)
3. [JavaScript Examples](#javascript-examples)
4. [Advanced Scenarios](#advanced-scenarios)

---

## cURL Examples

### Image Search - Mars

```bash
curl -X GET "http://localhost:8000/api/v1/images/search?q=mars&page_size=10" \
  -H "accept: application/json"
```

### Video Search - Apollo

```bash
curl -X GET "http://localhost:8000/api/v1/videos/search?q=apollo%20moon%20landing&page_size=5" \
  -H "accept: application/json"
```

### Pagination

```bash
# Page 1
curl "http://localhost:8000/api/v1/images/search?q=space&page=1&page_size=20"

# Page 2
curl "http://localhost:8000/api/v1/images/search?q=space&page=2&page_size=20"
```

### Health Check

```bash
curl "http://localhost:8000/api/v1/health"
```

### Response Example

```json
{
  "success": true,
  "provider": "multi-provider",
  "query": "mars rover",
  "results": [
    {
      "title": "Perseverance Rover on Mars",
      "description": "NASA's Perseverance rover exploring Jezero Crater",
      "media_type": "image",
      "provider": "nasa",
      "image_url": "https://images-assets.nasa.gov/...",
      "thumbnail_url": "https://images-assets.nasa.gov/.../thumb.jpg",
      "source_url": "https://images.nasa.gov/details/..."
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "has_next": true
  },
  "timestamp": "2024-01-15T10:30:00",
  "cached": false
}
```

---

## Python Examples

### Basic Search

```python
import httpx
import asyncio

async def search_mars():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={
                "q": "mars rover",
                "page_size": 10
            }
        )
        data = response.json()
        
        print(f"Query: {data['query']}")
        print(f"Results: {len(data['results'])}")
        
        for result in data['results']:
            print(f"  - {result['title']} ({result['provider']})")

asyncio.run(search_mars())
```

### Error Handling

```python
import httpx
import asyncio

async def search_with_error_handling():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(
                "http://localhost:8000/api/v1/images/search",
                params={"q": "mars"}
            )
            response.raise_for_status()
            data = response.json()
            
            if not data['success']:
                print(f"Error: {data['error']} - {data['message']}")
                return
            
            print(f"Found {len(data['results'])} results")
            
        except httpx.TimeoutException:
            print("Request timed out")
        except httpx.HTTPStatusError as e:
            print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
        except httpx.RequestError as e:
            print(f"Request Error: {e}")

asyncio.run(search_with_error_handling())
```

### Pagination

```python
import httpx
import asyncio

async def search_all_pages():
    async with httpx.AsyncClient() as client:
        page = 1
        all_results = []
        
        while True:
            response = await client.get(
                "http://localhost:8000/api/v1/images/search",
                params={
                    "q": "space",
                    "page": page,
                    "page_size": 20
                }
            )
            data = response.json()
            
            all_results.extend(data['results'])
            print(f"Page {page}: {len(data['results'])} results")
            
            if not data['pagination']['has_next']:
                break
            
            page += 1
        
        print(f"Total: {len(all_results)} results")

asyncio.run(search_all_pages())
```

### Video Search

```python
import httpx
import asyncio

async def search_videos():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/videos/search",
            params={
                "q": "apollo moon landing",
                "page_size": 5
            }
        )
        data = response.json()
        
        for video in data['results']:
            print(f"Title: {video['title']}")
            print(f"Provider: {video['provider']}")
            print(f"URL: {video['video_url']}")
            print(f"Thumbnail: {video['thumbnail_url']}")
            print()

asyncio.run(search_videos())
```

### Concurrent Searches

```python
import httpx
import asyncio

async def multi_search():
    queries = ["mars", "moon", "earth", "asteroid"]
    
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(
                "http://localhost:8000/api/v1/images/search",
                params={"q": query, "page_size": 5}
            )
            for query in queries
        ]
        
        responses = await asyncio.gather(*tasks)
        
        for query, response in zip(queries, responses):
            data = response.json()
            print(f"{query}: {len(data['results'])} results")

asyncio.run(multi_search())
```

### Class-based Integration

```python
import httpx
import asyncio

class VedaApexClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = None
    
    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.base_url)
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    async def search_images(self, query: str, page: int = 1, page_size: int = 20):
        response = await self.client.get(
            "/api/v1/images/search",
            params={"q": query, "page": page, "page_size": page_size}
        )
        response.raise_for_status()
        return response.json()
    
    async def search_videos(self, query: str, page: int = 1, page_size: int = 20):
        response = await self.client.get(
            "/api/v1/videos/search",
            params={"q": query, "page": page, "page_size": page_size}
        )
        response.raise_for_status()
        return response.json()
    
    async def health(self):
        response = await self.client.get("/api/v1/health")
        response.raise_for_status()
        return response.json()

async def main():
    async with VedaApexClient() as client:
        # Search images
        images = await client.search_images("mars rover")
        print(f"Found {len(images['results'])} images")
        
        # Search videos
        videos = await client.search_videos("apollo")
        print(f"Found {len(videos['results'])} videos")
        
        # Health check
        health = await client.health()
        print(f"Status: {health['status']}")

asyncio.run(main())
```

---

## JavaScript Examples

### Fetch API

```javascript
async function searchImages(query) {
    const response = await fetch(
        `/api/v1/images/search?q=${encodeURIComponent(query)}&page_size=10`
    );
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
}

// Usage
searchImages("mars rover")
    .then(data => {
        console.log(`Found ${data.results.length} images`);
        data.results.forEach(result => {
            console.log(`- ${result.title} (${result.provider})`);
        });
    })
    .catch(error => console.error("Error:", error));
```

### Async/Await

```javascript
async function multiSearch() {
    const queries = ["mars", "moon", "earth"];
    
    try {
        const responses = await Promise.all(
            queries.map(q => 
                fetch(`/api/v1/images/search?q=${encodeURIComponent(q)}&page_size=5`)
                    .then(r => r.json())
            )
        );
        
        responses.forEach((data, i) => {
            console.log(`${queries[i]}: ${data.results.length} results`);
        });
    } catch (error) {
        console.error("Error:", error);
    }
}

multiSearch();
```

### React Component

```javascript
import React, { useState, useEffect } from 'react';

function SearchResults({ query }) {
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    useEffect(() => {
        const search = async () => {
            setLoading(true);
            setError(null);
            
            try {
                const response = await fetch(
                    `/api/v1/images/search?q=${encodeURIComponent(query)}&page_size=20`
                );
                
                if (!response.ok) throw new Error("API error");
                
                const data = await response.json();
                setResults(data.results);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };
        
        if (query) search();
    }, [query]);
    
    if (loading) return <p>Loading...</p>;
    if (error) return <p>Error: {error}</p>;
    
    return (
        <div>
            <h2>Results for "{query}"</h2>
            <div className="grid">
                {results.map((result, i) => (
                    <div key={i} className="card">
                        <img src={result.thumbnail_url} alt={result.title} />
                        <h3>{result.title}</h3>
                        <p>{result.provider}</p>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default SearchResults;
```

---

## Advanced Scenarios

### Rate Limiting Handling

```python
import httpx
import asyncio
import time

async def search_with_rate_limit_handling():
    async with httpx.AsyncClient() as client:
        queries = ["mars", "moon", "earth"] * 30  # 90 queries
        
        for i, query in enumerate(queries):
            try:
                response = await client.get(
                    "http://localhost:8000/api/v1/images/search",
                    params={"q": query, "page_size": 5}
                )
                
                # Check rate limit headers
                remaining = response.headers.get('X-RateLimit-Remaining')
                print(f"{i+1}: {query} - Remaining: {remaining}")
                
                if response.status_code == 429:
                    print("Rate limited! Waiting 60 seconds...")
                    await asyncio.sleep(60)
                
            except httpx.RequestError as e:
                print(f"Error: {e}")
                await asyncio.sleep(1)

asyncio.run(search_with_rate_limit_handling())
```

### Caching Strategy

```python
import httpx
import asyncio
from datetime import datetime, timedelta

class CachedVedaApex:
    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache = {}
        self.cache_ttl = cache_ttl_seconds
    
    async def search(self, query: str):
        # Check cache
        if query in self.cache:
            timestamp, data = self.cache[query]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                print(f"Cache hit for '{query}'")
                return data
        
        # Fetch from API
        print(f"Fetching '{query}' from API...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8000/api/v1/images/search",
                params={"q": query, "page_size": 10}
            )
            data = response.json()
        
        # Store in cache
        self.cache[query] = (datetime.now(), data)
        return data

# Usage
async def demo():
    client = CachedVedaApex(cache_ttl_seconds=600)
    
    # First call - API hit
    result1 = await client.search("mars")
    
    # Second call - Cache hit
    result2 = await client.search("mars")
    
    # Different query - API hit
    result3 = await client.search("moon")

asyncio.run(demo())
```

### Batch Processing

```python
import httpx
import asyncio
from typing import List

async def batch_search(queries: List[str], batch_size: int = 3):
    """Search multiple queries in batches to respect rate limits."""
    async with httpx.AsyncClient() as client:
        results = []
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}: {batch}")
            
            # Concurrent search within batch
            tasks = [
                client.get(
                    "http://localhost:8000/api/v1/images/search",
                    params={"q": q, "page_size": 5}
                )
                for q in batch
            ]
            
            responses = await asyncio.gather(*tasks)
            
            for response, query in zip(responses, batch):
                data = response.json()
                results.append({
                    "query": query,
                    "count": len(data['results']),
                    "results": data['results']
                })
            
            # Wait between batches
            if i + batch_size < len(queries):
                await asyncio.sleep(1)
        
        return results

# Usage
queries = ["mars", "moon", "earth", "asteroid", "comet", "nebula"]
results = asyncio.run(batch_search(queries, batch_size=2))

for result in results:
    print(f"{result['query']}: {result['count']} results")
```

---

**These examples show common integration patterns! 🚀**
