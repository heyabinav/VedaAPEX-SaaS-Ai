#!/usr/bin/env python
"""
Simplified end-to-end test for the multimodal attachment system.
Tests routing, validation, and cleanup without requiring database/auth.
"""

import io
import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.models.user import User
from app.routers.auth import get_current_user_auth

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# TEST SETUP - Mock the dependencies
# ─────────────────────────────────────────────────────────────────────────────

# Create a mock user
mock_user = User(
    id="test-user-123",
    email="test@example.com",
    full_name="Test User",
)

# Create a mock database session
mock_session = MagicMock()

# Mock the authentication dependency
def mock_get_current_user():
    return mock_user

def mock_get_session():
    return mock_session

# Override the dependencies
app.dependency_overrides[get_current_user_auth] = mock_get_current_user
from app.db.session import get_session
app.dependency_overrides[get_session] = mock_get_session

client = TestClient(app)


def create_test_image(width: int = 100, height: int = 100, color: tuple = (255, 0, 0)) -> bytes:
    """Create a test image in memory."""
    img = Image.new("RGB", (width, height), color)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_oversized_image() -> bytes:
    """Create an image that exceeds MAX_FILE_SIZE."""
    img = Image.new("RGB", (4000, 3000), (0, 0, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    data = buffer.getvalue()
    if len(data) < 11 * 1024 * 1024:
        data += b"\x00" * (11 * 1024 * 1024 - len(data))
    return data


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: VALIDATION - UNSUPPORTED FILE TYPE
# ─────────────────────────────────────────────────────────────────────────────

def test_unsupported_file_type():
    """Test rejection of unsupported file types."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Unsupported File Type Validation")
    logger.info("=" * 80)

    try:
        files = [
            ("files", ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")),
        ]
        
        data = {"message": "Test", "model": "auto"}
        
        response = client.post("/api/v1/chat/ask", files=files, data=data)
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            error_code = result.get("error", {}).get("code")
            if error_code == "UNSUPPORTED_FILE_TYPE":
                logger.info(f"✓ Correctly rejected with: {error_code}")
                return True
            else:
                logger.info(f"Error code: {error_code}")
        
        logger.error(f"✗ Expected 400 UNSUPPORTED_FILE_TYPE but got {response.status_code}")
        logger.info(f"Response: {response.json()}")
        return False
    except Exception as e:
        logger.error(f"✗ Exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: VALIDATION - OVERSIZED FILE
# ─────────────────────────────────────────────────────────────────────────────

def test_oversized_file():
    """Test rejection of oversized files."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Oversized File Validation")
    logger.info("=" * 80)

    try:
        image_data = create_oversized_image()
        logger.info(f"Created image: {len(image_data) / (1024*1024):.1f} MB")
        
        files = [
            ("files", ("huge.png", io.BytesIO(image_data), "image/png")),
        ]
        
        data = {"message": "Test", "model": "auto"}
        
        response = client.post("/api/v1/chat/ask", files=files, data=data)
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            error_code = result.get("error", {}).get("code")
            if error_code == "FILE_TOO_LARGE":
                logger.info(f"✓ Correctly rejected with: {error_code}")
                return True
            else:
                logger.info(f"Error code: {error_code}")
        
        logger.error(f"✗ Expected 400 FILE_TOO_LARGE but got {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"✗ Exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: VALIDATION - TOO MANY FILES
# ─────────────────────────────────────────────────────────────────────────────

def test_too_many_files():
    """Test rejection when too many files are uploaded."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Too Many Files Validation")
    logger.info("=" * 80)

    try:
        image_data = create_test_image()
        
        # Try to upload 6 files (max is 5)
        files = [
            ("files", (f"image_{i}.png", io.BytesIO(image_data), "image/png"))
            for i in range(6)
        ]
        
        data = {"message": "Test", "model": "auto"}
        
        response = client.post("/api/v1/chat/ask", files=files, data=data)
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            error_code = result.get("error", {}).get("code")
            if error_code == "TOO_MANY_FILES":
                logger.info(f"✓ Correctly rejected with: {error_code}")
                return True
            else:
                logger.info(f"Error code: {error_code}")
        
        logger.error(f"✗ Expected 400 TOO_MANY_FILES but got {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"✗ Exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: TEMP FILE CLEANUP
# ─────────────────────────────────────────────────────────────────────────────

def test_temp_file_cleanup():
    """Test that temporary files are cleaned up even on validation errors."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Temporary File Cleanup on Validation Error")
    logger.info("=" * 80)

    try:
        from app.services.attachments.config import ATTACHMENT_CONFIG
        temp_dir = Path(ATTACHMENT_CONFIG.TEMP_UPLOAD_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        files_before = list(temp_dir.glob("*"))
        logger.info(f"Files before: {len(files_before)}")
        
        # Send a request that will fail validation (unsupported file)
        files = [
            ("files", ("test.exe", io.BytesIO(b"MZ"), "application/octet-stream")),
        ]
        data = {"message": "Test", "model": "auto"}
        
        response = client.post("/api/v1/chat/ask", files=files, data=data)
        logger.info(f"Response status: {response.status_code}")
        
        # Check cleanup
        import time
        time.sleep(0.2)
        files_after = list(temp_dir.glob("*"))
        logger.info(f"Files after: {len(files_after)}")
        
        if len(files_after) <= len(files_before):
            logger.info(f"✓ Cleanup successful (no leftover temp files)")
            return True
        else:
            logger.error(f"✗ Temp files not cleaned up!")
            logger.info(f"New files: {[f.name for f in files_after if f not in files_before]}")
            return False
    except Exception as e:
        logger.error(f"✗ Exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: ROUTE REGISTRATION AND MULTIPART SUPPORT
# ─────────────────────────────────────────────────────────────────────────────

def test_route_registration():
    """Test that the multipart route is correctly registered."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Route Registration")
    logger.info("=" * 80)

    try:
        routes = [r.path for r in app.routes if "chat" in r.path]
        
        if "/api/v1/chat/ask" in routes:
            logger.info(f"✓ Route /api/v1/chat/ask is registered")
            
            # Check that it's a POST route
            for route in app.routes:
                if route.path == "/api/v1/chat/ask":
                    if "POST" in route.methods or not hasattr(route, 'methods'):
                        logger.info(f"✓ Supports POST method")
                        return True
                    else:
                        logger.error(f"✗ Route doesn't support POST: {route.methods}")
                        return False
        
        logger.error(f"✗ Route /api/v1/chat/ask not found")
        logger.info(f"Available routes: {routes}")
        return False
    except Exception as e:
        logger.error(f"✗ Exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: ATTACHMENT METADATA STRUCTURE
# ─────────────────────────────────────────────────────────────────────────────

def test_attachment_metadata_structure():
    """Test that attachments are properly structured in the response."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Attachment Metadata Structure")
    logger.info("=" * 80)

    try:
        # Mock the ChatMemoryService to return a valid response
        with patch('app.services.chat_memory_service.ChatMemoryService.ask') as mock_ask:
            mock_ask.return_value = {
                "session_id": "test-session",
                "title": "Test",
                "answer": "Test response",
                "history": [],
                "metadata": {
                    "model": "auto",
                    "context_limit": 12,
                },
            }
            
            image_data = create_test_image()
            files = [
                ("files", ("test.png", io.BytesIO(image_data), "image/png")),
            ]
            data = {"message": "Analyze this image", "model": "auto"}
            
            response = client.post("/api/v1/chat/ask", files=files, data=data)
            
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                metadata = result.get("metadata", {})
                attachments = metadata.get("attachments", [])
                
                logger.info(f"✓ Response has metadata with attachments")
                logger.info(f"  Attachments count: {len(attachments)}")
                
                if len(attachments) > 0:
                    att = attachments[0]
                    required_fields = ["id", "filename", "mime_type", "size"]
                    missing = [f for f in required_fields if f not in att]
                    
                    if not missing:
                        logger.info(f"✓ Attachment has all required fields")
                        logger.info(f"  - id: {att['id']}")
                        logger.info(f"  - filename: {att['filename']}")
                        logger.info(f"  - mime_type: {att['mime_type']}")
                        logger.info(f"  - size: {att['size']} bytes")
                        return True
                    else:
                        logger.error(f"✗ Missing fields: {missing}")
                        return False
                else:
                    logger.error(f"✗ No attachments in metadata")
                    return False
            else:
                logger.error(f"✗ Got status {response.status_code}")
                logger.info(f"Response: {response.json()}")
                return False
    except Exception as e:
        logger.error(f"✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TEST RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests():
    """Run all tests and report results."""
    logger.info("\n" + "=" * 80)
    logger.info("ATTACHMENT SYSTEM VALIDATION TESTS")
    logger.info("(Testing validation, routing, and cleanup)")
    logger.info("=" * 80)
    
    results = {}
    
    # Run tests
    results["route_registration"] = test_route_registration()
    results["unsupported_file"] = test_unsupported_file_type()
    results["oversized_file"] = test_oversized_file()
    results["too_many_files"] = test_too_many_files()
    results["temp_cleanup"] = test_temp_file_cleanup()
    results["metadata_structure"] = test_attachment_metadata_structure()
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status:8} {test_name}")
    
    logger.info("-" * 80)
    logger.info(f"Total: {passed} passed, {failed} failed")
    logger.info("=" * 80)
    
    return passed, failed


if __name__ == "__main__":
    passed, failed = run_all_tests()
    exit(0 if failed == 0 else 1)
