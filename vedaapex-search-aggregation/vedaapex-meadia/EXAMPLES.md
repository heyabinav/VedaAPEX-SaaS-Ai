# Usage Examples

## Table of Contents

1. [cURL Examples](#curl-examples)
2. [Python Examples](#python-examples)
3. [JavaScript Examples](#javascript-examples)
4. [Advanced Scenarios](#advanced-scenarios)

---

## cURL Examples

### Basic Image Search

```bash
curl -X GET "http://localhost:8000/api/v1/images/search?q=wildlife" \
  -H "Accept: application/json"
```

### Image Search with Pagination

```bash
# Page 1
curl "http://localhost:8000/api/v1/images/search?q=microscopy&page=1&page_size=20"

# Page 2
curl "http://localhost:8000/api/v1/images/search?q=microscopy&page=2&page_size=20"
```

### Video Search

```bash
curl "http://localhost:8000/api/v1/videos/search?q=ocean&page_size=5"
```

### Save Results to File

```bash
curl "http://localhost:8000/api/v1/images/search?q=flower" > results.json
```

### Pretty Print Response

```bash
curl "http://localhost:8000/api/v1/images/search?q=bird" | python -m json.tool
```

---

## Python Examples

### Basic Usage

```python
import httpx

async def search_images():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={"q": "butterfly", "page_size": 5}
        )
        return response.json()

import asyncio
results = asyncio.run(search_images())
print(f"Found {len(results['results'])} images")
```

### With Error Handling

```python
import httpx
import asyncio
from typing import Dict, Optional

async def safe_search(query: str) -> Optional[Dict]:
    """Search with error handling."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                "http://localhost:8000/api/v1/images/search",
                params={"q": query, "page_size": 10},
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        print(f"HTTP error: {e}")
        return None
    except ValueError as e:
        print(f"Invalid JSON: {e}")
        return None

# Usage
results = asyncio.run(safe_search("landscape"))
if results:
    for img in results['results']:
        print(f"✓ {img['title']}")
```

### Pagination Loop

```python
import httpx
import asyncio

async def get_all_results(query: str, max_pages: int = 5):
    """Fetch all results with pagination."""
    all_results = []
    
    async with httpx.AsyncClient() as client:
        for page in range(1, max_pages + 1):
            response = await client.get(
                "http://localhost:8000/api/v1/images/search",
                params={
                    "q": query,
                    "page": page,
                    "page_size": 50,
                },
            )
            data = response.json()
            
            if not data['results']:
                break  # No more results
            
            all_results.extend(data['results'])
            
            print(f"Page {page}: {len(data['results'])} results, "
                  f"Total: {len(all_results)}")
            
            if not data['pagination']['has_next']:
                break
    
    return all_results

# Usage
results = asyncio.run(get_all_results("mountain", max_pages=3))
print(f"Total results: {len(results)}")
```

### Download Images

```python
import httpx
import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse

async def download_images(query: str, output_dir: str = "downloads"):
    """Download search results."""
    os.makedirs(output_dir, exist_ok=True)
    
    async with httpx.AsyncClient() as client:
        # Search
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={"q": query, "page_size": 5},
        )
        data = response.json()
        
        # Download each image
        for result in data['results']:
            url = result['image_url']
            filename = Path(url).name or f"{result['title']}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            try:
                img_response = await client.get(url)
                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
                print(f"✓ Downloaded: {filename}")
            except Exception as e:
                print(f"✗ Failed: {filename} - {e}")

# Usage
asyncio.run(download_images("sunset", output_dir="./images"))
```

### Search Multiple Queries

```python
import httpx
import asyncio

async def batch_search(queries: list[str]) -> dict:
    """Search multiple queries concurrently."""
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(
                "http://localhost:8000/api/v1/images/search",
                params={"q": q, "page_size": 10},
            )
            for q in queries
        ]
        
        responses = await asyncio.gather(*tasks)
        
        results = {}
        for query, response in zip(queries, responses):
            results[query] = response.json()
        
        return results

# Usage
queries = ["forest", "ocean", "mountain"]
results = asyncio.run(batch_search(queries))

for query, data in results.items():
    print(f"{query}: {len(data['results'])} results")
```

---

## JavaScript Examples

### Basic Fetch

```javascript
async function searchImages(query) {
  const response = await fetch(
    `/api/v1/images/search?q=${encodeURIComponent(query)}&page_size=10`
  );
  return await response.json();
}

// Usage
searchImages("wildlife")
  .then(data => {
    console.log(`Found ${data.results.length} images`);
    data.results.forEach(img => console.log(img.title));
  })
  .catch(err => console.error("Error:", err));
```

### With Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 5000,
});

async function searchMedia(type, query, page = 1) {
  try {
    const { data } = await api.get(`/${type}/search`, {
      params: { q: query, page, page_size: 20 },
    });
    return data;
  } catch (error) {
    console.error(`Search failed: ${error.message}`);
    return null;
  }
}

// Usage
const images = await searchMedia('images', 'butterfly');
const videos = await searchMedia('videos', 'ocean');
```

### React Hook

```javascript
import { useState, useEffect } from 'react';

function useMediaSearch(query, mediaType = 'images') {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!query) {
      setResults([]);
      return;
    }

    const fetchResults = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `/api/v1/${mediaType}/search?q=${encodeURIComponent(query)}&page_size=20`
        );
        const data = await response.json();

        if (!data.success) throw new Error(data.message);

        setResults(data.results);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    const debounceTimer = setTimeout(fetchResults, 500);
    return () => clearTimeout(debounceTimer);
  }, [query, mediaType]);

  return { results, loading, error };
}

// Usage
function SearchComponent() {
  const [query, setQuery] = useState('');
  const [mediaType, setMediaType] = useState('images');
  const { results, loading, error } = useMediaSearch(query, mediaType);

  return (
    <div>
      <input
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search..."
      />

      {loading && <p>Searching...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      <div className="gallery">
        {results.map(item => (
          <div key={item.title}>
            <img src={item.thumbnail_url} alt={item.title} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Vue 3 Composable

```javascript
import { ref, watch } from 'vue';

export function useMediaSearch(mediaType = 'images') {
  const query = ref('');
  const results = ref([]);
  const loading = ref(false);

  const search = async () => {
    if (!query.value) {
      results.value = [];
      return;
    }

    loading.value = true;
    try {
      const response = await fetch(
        `/api/v1/${mediaType}/search?q=${encodeURIComponent(query.value)}`
      );
      const data = await response.json();
      results.value = data.results;
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      loading.value = false;
    }
  };

  // Debounced search
  let timeout;
  watch(query, () => {
    clearTimeout(timeout);
    timeout = setTimeout(search, 500);
  });

  return { query, results, loading };
}

// Usage in component
<template>
  <div>
    <input v-model="query" placeholder="Search images..." />
    <p v-if="loading">Loading...</p>
    <div class="gallery">
      <img
        v-for="item in results"
        :key="item.title"
        :src="item.thumbnail_url"
        :alt="item.title"
      />
    </div>
  </div>
</template>

<script setup>
import { useMediaSearch } from './composables/useMediaSearch';
const { query, results, loading } = useMediaSearch('images');
</script>
```

---

## Advanced Scenarios

### Caching & Rate Limiting Awareness

```python
import httpx
import asyncio
import time

async def smart_search(query: str):
    """Smart search that respects cache."""
    async with httpx.AsyncClient() as client:
        print(f"Searching: {query}")
        
        start = time.time()
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={"q": query, "page_size": 20},
        )
        elapsed = time.time() - start
        
        data = response.json()
        
        print(f"Time: {elapsed:.2f}s, Cached: {data['cached']}")
        
        # If not cached, wait before next request to respect rate limits
        if not data['cached']:
            print("First fetch (uncached), waiting before next request...")
            await asyncio.sleep(1)

# Usage
async def main():
    queries = ["mountain", "mountain", "ocean", "ocean"]
    for q in queries:
        await smart_search(q)

asyncio.run(main())
```

### Error Recovery

```python
import httpx
import asyncio

async def resilient_search(query: str, max_retries: int = 3):
    """Search with automatic retry on failure."""
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "http://localhost:8000/api/v1/images/search",
                    params={"q": query},
                )
                response.raise_for_status()
                return response.json()
        
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Attempt {attempt+1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                print(f"All {max_retries} attempts failed")
                raise

# Usage
try:
    results = asyncio.run(resilient_search("butterfly"))
    print(f"Success: {len(results['results'])} results")
except Exception as e:
    print(f"Failed: {e}")
```

### Build Gallery HTML

```python
import httpx
import asyncio

async def create_gallery_html(query: str, output_file: str = "gallery.html"):
    """Create HTML gallery from search results."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8000/api/v1/images/search",
            params={"q": query, "page_size": 20},
        )
        data = response.json()
    
    html = f"""
    <html>
    <head>
        <title>VedaApex Media Gallery - {query}</title>
        <style>
            .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; }}
            .item {{ cursor: pointer; }}
            img {{ width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <h1>Search Results: {query}</h1>
        <p>Total: {len(data['results'])} results</p>
        <div class="gallery">
    """
    
    for item in data['results']:
        html += f"""
            <div class="item">
                <a href="{item['source_url']}" target="_blank">
                    <img src="{item['thumbnail_url']}" alt="{item['title']}" />
                    <p>{item['title']}</p>
                </a>
            </div>
        """
    
    html += """
        </div>
    </body>
    </html>
    """
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Gallery saved to {output_file}")

# Usage
asyncio.run(create_gallery_html("flower", "flower_gallery.html"))
```

---

## Performance Tips

1. **Use pagination** to limit results
2. **Reuse HTTP connections** (connection pooling)
3. **Implement caching** on client side too
4. **Use async/await** for concurrent requests
5. **Handle rate limits** gracefully with delays
6. **Cache API responses** locally
