# NASA Provider Integration Guide

## Overview

The NASA Image and Video Library API provides free access to NASA's extensive multimedia library including photos, videos, and datasets.

## Endpoint Details

### Base URL
```
https://images-api.nasa.gov/search
```

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| q | string | Yes | Search term |
| media_type | string | No | `image` or `video` |
| yearStart | integer | No | Start year (default: 1920) |
| yearEnd | integer | No | End year (default: current) |
| page | integer | No | Page number (default: 1) |
| api_key | string | No | API key (default: DEMO_KEY) |

### Response Format

```json
{
  "collection": {
    "version": "1.0",
    "href": "https://images-api.nasa.gov/search?...",
    "items": [
      {
        "href": "https://images-assets.nasa.gov/image/...",
        "data": [
          {
            "nasa_id": "PIA23412",
            "title": "Perseverance Rover",
            "description": "...",
            "keywords": ["rover", "mars"],
            "location": "Mars",
            "photographer": "NASA/JPL-Caltech",
            "date_created": "2021-01-01T00:00:00Z",
            "media_type": "image"
          }
        ],
        "links": [
          {
            "rel": "preview",
            "href": "https://images-assets.nasa.gov/image/.../~thumb.jpg",
            "render": "image"
          },
          {
            "rel": "captions",
            "href": "https://images-assets.nasa.gov/image/.../Captions.VTT",
            "render": "captions"
          }
        ]
      }
    ],
    "metadata": {
      "total_hits": 8000,
      "total_pages": 400
    }
  }
}
```

## API Key

### Getting an API Key

1. Visit https://api.nasa.gov/
2. Fill out the registration form
3. Check your email for API key
4. Add to `.env`:

```bash
NASA_DEMO_KEY=your_api_key_here
```

### Demo Key

For development and testing:
```bash
NASA_DEMO_KEY=DEMO_KEY
```

## Supported Media Types

### Images
- JPEG
- PNG
- TIFF
- GIF

### Videos
- MP4
- MOV
- M4V

## Search Examples

### Mars Images
```
https://images-api.nasa.gov/search?q=mars&media_type=image
```

### Apollo Mission Videos
```
https://images-api.nasa.gov/search?q=apollo&media_type=video
```

### Earth Imagery (Last 5 years)
```
https://images-api.nasa.gov/search?q=earth&yearStart=2019&yearEnd=2024&media_type=image
```

## Rate Limits

- **Free Tier:** 40 requests/hour
- **Authenticated:** 1,000 requests/hour
- **Reset:** Midnight UTC

## Retry Strategy

The NASA provider implements exponential backoff:

```
Initial request
  ↓ (500 error)
Wait 1s, retry
  ↓ (500 error)
Wait 2s, retry
  ↓ (500 error)
Wait 4s, retry
  ↓ (fail)
Raise ProviderError
```

## Response Normalization

Raw NASA responses are normalized to unified format:

```python
{
    "title": "NASA Image Title",
    "description": "Image description",
    "media_type": "image",
    "provider": "nasa",
    "image_url": "https://...",
    "thumbnail_url": "https://...",
    "source_url": "https://..."
}
```

## Common Queries

### Space Exploration
- apollo
- mars rover
- moon landing
- space shuttle
- international space station
- astronaut
- galaxy

### Earth Sciences
- earth
- climate
- weather
- ocean
- atmosphere
- glacier

### Technology
- satellite
- hubble
- telescope
- spacecraft
- probe

## Error Handling

| Error | Status | Cause | Solution |
|-------|--------|-------|----------|
| Invalid Query | 400 | Malformed request | Check query parameters |
| Rate Limited | 429 | Too many requests | Wait or upgrade API key |
| Server Error | 500 | NASA server issue | Retry with backoff |
| Timeout | 504 | Network/server slow | Increase timeout or retry |

## Tips

1. **Use Specific Terms** - "mars rover" returns better results than "mars"
2. **Year Filtering** - Use yearStart/yearEnd for historical searches
3. **Cache Results** - Cache frequently searched terms
4. **Batch Requests** - Multiple searches in parallel (respecting rate limits)
5. **Handle Errors** - Always implement retry logic

## Integration Test

```python
import asyncio
from providers.nasa_provider import NASAProvider

async def test():
    provider = NASAProvider()
    result = await provider.search_images("mars rover", page=1)
    print(f"Found {len(result['collection']['items'])} results")

asyncio.run(test())
```

## References

- **Official API Docs:** https://api.nasa.gov/
- **Image & Video Library:** https://images.nasa.gov/
- **API GitHub:** https://github.com/nasa/api
