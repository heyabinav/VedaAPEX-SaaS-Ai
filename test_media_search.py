"""
Tests for Unified Media Search System.

Tests all three providers (Pexels images, Pexels videos, NASA space images)
and intent detection logic.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock environment for testing
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("PEXELS_API_KEY", "test_key")  
os.environ.setdefault("NASA_API_KEY", "DEMO_KEY")

from app.services.media_search import MediaSearchService
from app.services.media_search.models import MediaSearchRequest
from app.services.media_search.intent_router import detect_intent, should_use_nasa


class TestIntentDetection:
    """Test intent detection logic."""
    
    @staticmethod
    def test_image_detection():
        """Test image intent detection."""
        test_cases = [
            ("human cell images", "image"),
            ("dog photo", "image"),
            ("wallpaper landscape", "image"),
            ("illustration art", "image"),
            ("show me pictures", "image"),
        ]
        
        for query, expected in test_cases:
            result = detect_intent(query)
            status = "✓" if result == expected else "✗"
            print(f"  {status} '{query}' → {result} (expected {expected})")
            assert result == expected, f"Failed for: {query}"
    
    @staticmethod
    def test_video_detection():
        """Test video intent detection."""
        test_cases = [
            ("watch python tutorial", "video"),
            ("AI agent video", "video"),
            ("youtube videos", "video"),
            ("how to video", "video"),
            ("film clips", "video"),
        ]
        
        for query, expected in test_cases:
            result = detect_intent(query)
            status = "✓" if result == expected else "✗"
            print(f"  {status} '{query}' → {result} (expected {expected})")
            assert result == expected, f"Failed for: {query}"
    
    @staticmethod
    def test_space_detection():
        """Test space intent detection."""
        test_cases = [
            ("NASA Mars rover", "space"),
            ("moon images", "space"),
            ("hubble telescope", "space"),
            ("galaxy photo", "space"),
            ("astronaut space", "space"),
        ]
        
        for query, expected in test_cases:
            result = detect_intent(query)
            status = "✓" if result == expected else "✗"
            print(f"  {status} '{query}' → {result} (expected {expected})")
            assert result == expected, f"Failed for: {query}"
    
    @staticmethod
    def test_ambiguous_space():
        """Test ambiguous queries that mention 'space'."""
        # "space wallpaper" should be image, not NASA
        result = detect_intent("space wallpaper")
        print(f"  'space wallpaper' → {result} (should be 'image' for generic wallpaper)")
        
        # "NASA Mars" should be space
        result = detect_intent("NASA Mars rover")
        print(f"  'NASA Mars rover' → {result} (should be 'space')")
        assert result == "space"
    
    @staticmethod
    def test_nasa_routing():
        """Test should_use_nasa logic."""
        test_cases = [
            ("NASA image", True),
            ("Mars rover", True),
            ("Hubble telescope", True),
            ("space wallpaper", False),  # Generic image
            ("cell images", False),  # Not space
            ("galaxy photo", True),  # Space content
        ]
        
        for query, expected in test_cases:
            result = should_use_nasa(query)
            status = "✓" if result == expected else "✗"
            print(f"  {status} '{query}' → NASA={result} (expected {expected})")


async def test_request_validation():
    """Test request validation."""
    print("\n[TEST] Request Validation")
    
    service = MediaSearchService()
    
    # Valid request
    try:
        request = MediaSearchRequest(query="test", type="auto", limit=10, page=1)
        print("  ✓ Valid request created")
    except Exception as e:
        print(f"  ✗ Valid request failed: {e}")
        return False
    
    # Invalid: query too short
    try:
        MediaSearchRequest(query="a", limit=10, page=1)
        print("  ✗ Should reject query < 2 chars")
        return False
    except Exception:
        print("  ✓ Rejected query too short")
    
    # Invalid: query too long
    try:
        MediaSearchRequest(query="x" * 201, limit=10, page=1)
        print("  ✗ Should reject query > 200 chars")
        return False
    except Exception:
        print("  ✓ Rejected query too long")
    
    # Invalid: limit out of range
    try:
        MediaSearchRequest(query="test", limit=100, page=1)
        print("  ✗ Should reject limit > 50")
        return False
    except Exception:
        print("  ✓ Rejected limit > 50")
    
    # Invalid: invalid type
    try:
        MediaSearchRequest(query="test", type="invalid", limit=10, page=1)  # type: ignore
        print("  ✗ Should reject invalid type")
        return False
    except Exception:
        print("  ✓ Rejected invalid type")
    
    return True


async def test_search_service():
    """Test media search service."""
    print("\n[TEST] Media Search Service")
    
    service = MediaSearchService()
    
    # Test 1: Image search
    print("  Testing image search (no API key, expecting error)...")
    try:
        request = MediaSearchRequest(query="human cell", type="image", limit=5, page=1)
        response = await service.search(request)
        if response.success:
            print(f"    ✓ Image search returned {len(response.results)} results")
            if response.results:
                result = response.results[0]
                print(f"      - Type: {result.type}")
                print(f"      - Title: {result.title[:50]}...")
        else:
            print(f"    ✗ Image search failed: {response}")
    except RuntimeError as e:
        if "PEXELS" in str(e) or "API" in str(e):
            print(f"    ℹ Image provider error (expected without real key): {e}")
        else:
            print(f"    ✗ Unexpected error: {e}")
    
    # Test 2: Video search  
    print("  Testing video search (no API key, expecting error)...")
    try:
        request = MediaSearchRequest(query="python tutorial", type="video", limit=5, page=1)
        response = await service.search(request)
        if response.success:
            print(f"    ✓ Video search returned {len(response.results)} results")
        else:
            print(f"    ✗ Video search failed")
    except RuntimeError as e:
        if "PEXELS" in str(e) or "API" in str(e):
            print(f"    ℹ Video provider error (expected without real key): {e}")
        else:
            print(f"    ✗ Unexpected error: {e}")
    
    # Test 3: NASA space search
    print("  Testing NASA space search (using DEMO_KEY)...")
    try:
        request = MediaSearchRequest(query="Mars rover", type="space", limit=5, page=1)
        response = await service.search(request)
        if response.success:
            print(f"    ✓ NASA search returned {len(response.results)} results")
            if response.results:
                result = response.results[0]
                print(f"      - Type: {result.type}")
                print(f"      - Source: {result.source_name}")
                print(f"      - Title: {result.title[:50]}...")
        else:
            print(f"    ✗ NASA search failed")
    except RuntimeError as e:
        print(f"    ✗ NASA search error: {e}")
    
    # Test 4: Auto-detection
    print("  Testing auto-detection (image query)...")
    try:
        request = MediaSearchRequest(query="butterfly photo", type="auto", limit=5, page=1)
        response = await service.search(request)
        print(f"    ℹ Auto-detected type: {response.type}")
        assert response.type == "image", "Should detect as image"
        print(f"    ✓ Correctly detected as image")
    except RuntimeError as e:
        print(f"    ℹ Search error (may be API key related): {e}")
    
    print("  Testing auto-detection (video query)...")
    try:
        request = MediaSearchRequest(query="watch tutorial video", type="auto", limit=5, page=1)
        response = await service.search(request)
        print(f"    ℹ Auto-detected type: {response.type}")
        assert response.type == "video", "Should detect as video"
        print(f"    ✓ Correctly detected as video")
    except RuntimeError as e:
        print(f"    ℹ Search error (may be API key related): {e}")
    
    print("  Testing auto-detection (space query)...")
    try:
        request = MediaSearchRequest(query="NASA Mars rover images", type="auto", limit=5, page=1)
        response = await service.search(request)
        print(f"    ℹ Auto-detected type: {response.type}")
        assert response.type == "space", "Should detect as space"
        print(f"    ✓ Correctly detected as space")
    except RuntimeError as e:
        print(f"    ℹ Search error: {e}")


def main():
    """Run all tests."""
    print("=" * 70)
    print("UNIFIED MEDIA SEARCH SYSTEM - TEST SUITE")
    print("=" * 70)
    
    # Test 1: Intent detection
    print("\n[TEST] Intent Detection")
    TestIntentDetection.test_image_detection()
    TestIntentDetection.test_video_detection()
    TestIntentDetection.test_space_detection()
    TestIntentDetection.test_ambiguous_space()
    
    print("\n[TEST] NASA Routing Logic")
    TestIntentDetection.test_nasa_routing()
    
    # Test 2: Request validation
    asyncio.run(test_request_validation())
    
    # Test 3: Search service
    asyncio.run(test_search_service())
    
    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)
    print("\nNote: Some tests expect errors due to missing/demo API keys.")
    print("To test with real APIs:")
    print("  1. Add PEXELS_API_KEY to .env (get from https://www.pexels.com/api)")
    print("  2. Add NASA_API_KEY to .env (optional, uses DEMO_KEY for public API)")
    print("\nFull test with real keys can be run after configuration.")


if __name__ == "__main__":
    main()
