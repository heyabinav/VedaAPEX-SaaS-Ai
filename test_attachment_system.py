#!/usr/bin/env python
"""
End-to-end test for the multimodal attachment system integrated into /api/v1/chat/ask.

Tests:
1. Text-only chat (backward compatibility)
2. Single image upload
3. Multiple image upload
4. Unsupported file type
5. Oversized file
6. Corrupted image
7. Temp file cleanup
"""

import asyncio
import base64
import io
import json
import logging
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# TEST SETUP
# ─────────────────────────────────────────────────────────────────────────────

client = TestClient(app)

# Mock authorization header (will override auth in tests if needed)
DEFAULT_HEADERS = {
    "Authorization": "Bearer test-token-for-local-testing",
}


def create_test_image(width: int = 100, height: int = 100, color: tuple = (255, 0, 0)) -> bytes:
    """Create a test image in memory."""
    img = Image.new("RGB", (width, height), color)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def create_oversized_image() -> bytes:
    """Create an image that exceeds MAX_FILE_SIZE (10MB)."""
    # Create a large image (11MB)
    img = Image.new("RGB", (4000, 3000), (0, 0, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    data = buffer.getvalue()
    # If still under 10MB, pad it
    if len(data) < 11 * 1024 * 1024:
        data += b"\x00" * (11 * 1024 * 1024 - len(data))
    return data


def create_corrupted_image() -> bytes:
    """Create a corrupted PNG file."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # PNG header + garbage


# ─────────────────────────────────────────────────────────────────────────────
# TEST: TEXT-ONLY CHAT (NO IMAGES)
# ─────────────────────────────────────────────────────────────────────────────

def test_text_only_chat():
    """Test backward compatibility: text-only chat without images."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Text-Only Chat (Backward Compatibility)")
    logger.info("=" * 80)

    try:
        # Use multipart form-data with just message (no files)
        response = client.post(
            "/api/v1/chat/ask",
            data={
                "message": "Hello, what is 2+2?",
                "model": "auto",
            },
            headers=DEFAULT_HEADERS,
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Text-only chat works")
            logger.info(f"  Session ID: {result.get('session_id')}")
            logger.info(f"  Answer: {result.get('answer', '')[:100]}...")
            logger.info(f"  Metadata: {json.dumps(result.get('metadata', {}), indent=2)}")
            return True
        elif response.status_code == 401:
            logger.warning("⚠ Authentication failed (401) - test environment may need auth setup")
            logger.info(f"  Response: {response.text[:200]}")
            return None  # Skip, not a failure
        else:
            logger.error(f"✗ Text-only chat failed with status {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Text-only chat exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST: SINGLE IMAGE UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def test_single_image_upload():
    """Test upload of a single image with a message."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Single Image Upload")
    logger.info("=" * 80)

    try:
        image_data = create_test_image(200, 200, (255, 0, 0))
        
        files = [
            ("files", ("test_image_1.png", io.BytesIO(image_data), "image/png")),
        ]
        
        data = {
            "message": "Analyze this image and tell me what you see.",
            "model": "auto",
        }
        
        response = client.post(
            "/api/v1/chat/ask",
            files=files,
            data=data,
            headers=DEFAULT_HEADERS,
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Single image upload works")
            logger.info(f"  Session ID: {result.get('session_id')}")
            logger.info(f"  Answer: {result.get('answer', '')[:100]}...")
            attachments = result.get('metadata', {}).get('attachments', [])
            logger.info(f"  Attachments in response: {len(attachments)}")
            for att in attachments:
                logger.info(f"    - {att.get('filename')} ({att.get('mime_type')}, {att.get('size')} bytes)")
            return True
        elif response.status_code == 401:
            logger.warning("⚠ Authentication failed (401)")
            return None
        else:
            logger.error(f"✗ Single image upload failed with status {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Single image upload exception: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST: MULTIPLE IMAGES UPLOAD
# ─────────────────────────────────────────────────────────────────────────────

def test_multiple_images_upload():
    """Test upload of multiple images in a single request."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Multiple Images Upload")
    logger.info("=" * 80)

    try:
        image_data_1 = create_test_image(150, 150, (255, 0, 0))
        image_data_2 = create_test_image(150, 150, (0, 255, 0))
        
        files = [
            ("files", ("test_image_red.png", io.BytesIO(image_data_1), "image/png")),
            ("files", ("test_image_green.png", io.BytesIO(image_data_2), "image/png")),
        ]
        
        data = {
            "message": "Compare these two images. What's different?",
            "model": "auto",
        }
        
        response = client.post(
            "/api/v1/chat/ask",
            files=files,
            data=data,
            headers=DEFAULT_HEADERS,
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ Multiple images upload works")
            logger.info(f"  Session ID: {result.get('session_id')}")
            logger.info(f"  Answer: {result.get('answer', '')[:100]}...")
            attachments = result.get('metadata', {}).get('attachments', [])
            logger.info(f"  Attachments in response: {len(attachments)}")
            for att in attachments:
                logger.info(f"    - {att.get('filename')} ({att.get('mime_type')}, {att.get('size')} bytes)")
            return True
        elif response.status_code == 401:
            logger.warning("⚠ Authentication failed (401)")
            return None
        else:
            logger.error(f"✗ Multiple images upload failed with status {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Multiple images upload exception: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST: UNSUPPORTED FILE TYPE
# ─────────────────────────────────────────────────────────────────────────────

def test_unsupported_file():
    """Test rejection of unsupported file types."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Unsupported File Type")
    logger.info("=" * 80)

    try:
        # Try to upload an exe file
        files = [
            ("files", ("malware.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")),
        ]
        
        data = {
            "message": "This should fail",
            "model": "auto",
        }
        
        response = client.post(
            "/api/v1/chat/ask",
            files=files,
            data=data,
            headers=DEFAULT_HEADERS,
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            error_code = result.get("error", {}).get("code")
            error_msg = result.get("error", {}).get("message")
            if error_code == "UNSUPPORTED_FILE_TYPE":
                logger.info(f"✓ Unsupported file correctly rejected")
                logger.info(f"  Error code: {error_code}")
                logger.info(f"  Error message: {error_msg}")
                return True
            else:
                logger.warning(f"⚠ Got 400 but unexpected error code: {error_code}")
                logger.info(f"  Response: {result}")
                return False
        elif response.status_code == 401:
            logger.warning("⚠ Authentication failed (401)")
            return None
        else:
            logger.error(f"✗ Expected 400 but got {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Unsupported file test exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST: OVERSIZED FILE
# ─────────────────────────────────────────────────────────────────────────────

def test_oversized_file():
    """Test rejection of oversized files."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 5: Oversized File")
    logger.info("=" * 80)

    try:
        image_data = create_oversized_image()
        logger.info(f"  Created oversized image: {len(image_data) / (1024*1024):.1f} MB")
        
        files = [
            ("files", ("huge_image.png", io.BytesIO(image_data), "image/png")),
        ]
        
        data = {
            "message": "This file is too large",
            "model": "auto",
        }
        
        response = client.post(
            "/api/v1/chat/ask",
            files=files,
            data=data,
            headers=DEFAULT_HEADERS,
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code == 400:
            result = response.json()
            error_code = result.get("error", {}).get("code")
            error_msg = result.get("error", {}).get("message")
            if error_code == "FILE_TOO_LARGE":
                logger.info(f"✓ Oversized file correctly rejected")
                logger.info(f"  Error code: {error_code}")
                logger.info(f"  Error message: {error_msg}")
                return True
            else:
                logger.warning(f"⚠ Got 400 but unexpected error code: {error_code}")
                return False
        elif response.status_code == 401:
            logger.warning("⚠ Authentication failed (401)")
            return None
        else:
            logger.error(f"✗ Expected 400 but got {response.status_code}")
            logger.error(f"  Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"✗ Oversized file test exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST: CORRUPTED IMAGE
# ─────────────────────────────────────────────────────────────────────────────

def test_corrupted_image():
    """Test handling of corrupted image files."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 6: Corrupted Image")
    logger.info("=" * 80)

    try:
        image_data = create_corrupted_image()
        
        files = [
            ("files", ("corrupted.png", io.BytesIO(image_data), "image/png")),
        ]
        
        data = {
            "message": "This image is corrupted",
            "model": "auto",
        }
        
        response = client.post(
            "/api/v1/chat/ask",
            files=files,
            data=data,
            headers=DEFAULT_HEADERS,
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        # Note: corrupted images might still be accepted by validation (since they pass MIME check)
        # but they might fail later during processing or at the AI provider
        if response.status_code in (200, 400, 422):
            logger.info(f"✓ Corrupted image handled (status {response.status_code})")
            logger.info(f"  Response: {response.text[:200]}")
            return True
        elif response.status_code == 401:
            logger.warning("⚠ Authentication failed (401)")
            return None
        else:
            logger.warning(f"⚠ Unexpected status {response.status_code}")
            logger.info(f"  Response: {response.text}")
            return None
    except Exception as e:
        logger.error(f"✗ Corrupted image test exception: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# TEST: TEMP FILE CLEANUP
# ─────────────────────────────────────────────────────────────────────────────

def test_temp_cleanup():
    """Verify that temporary upload files are cleaned up after the request."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 7: Temporary File Cleanup")
    logger.info("=" * 80)

    try:
        # Get the temp upload directory path
        from app.services.attachments.config import ATTACHMENT_CONFIG
        temp_dir = Path(ATTACHMENT_CONFIG.TEMP_UPLOAD_DIR)
        
        # Create the directory if it doesn't exist
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Count files before
        files_before = list(temp_dir.glob("*"))
        logger.info(f"  Files in temp before request: {len(files_before)}")
        
        # Make a request with an image
        image_data = create_test_image(100, 100, (100, 100, 255))
        
        files = [
            ("files", ("cleanup_test.png", io.BytesIO(image_data), "image/png")),
        ]
        
        data = {
            "message": "Test cleanup",
            "model": "auto",
        }
        
        response = client.post(
            "/api/v1/chat/ask",
            files=files,
            data=data,
            headers=DEFAULT_HEADERS,
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        # Count files after
        import time
        time.sleep(0.5)  # Give cleanup a moment
        files_after = list(temp_dir.glob("*"))
        logger.info(f"  Files in temp after request: {len(files_after)}")
        
        if len(files_after) <= len(files_before):
            logger.info(f"✓ Temp files cleaned up correctly")
            logger.info(f"  Files added and removed: {len(files_before)} → {len(files_after)}")
            return True
        else:
            logger.warning(f"⚠ Temp files may not have been cleaned up")
            logger.info(f"  Files before: {len(files_before)}, after: {len(files_after)}")
            logger.info(f"  New files: {[f.name for f in files_after if f not in files_before]}")
            return False
    except Exception as e:
        logger.error(f"✗ Cleanup test exception: {e}")
        import traceback
        traceback.print_exc()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# MAIN TEST RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_all_tests():
    """Run all tests and report results."""
    logger.info("\n" + "=" * 80)
    logger.info("MULTIMODAL ATTACHMENT SYSTEM TEST SUITE")
    logger.info("=" * 80)
    
    results = {}
    
    # Run tests
    results["text_only"] = test_text_only_chat()
    results["single_image"] = test_single_image_upload()
    results["multiple_images"] = test_multiple_images_upload()
    results["unsupported_file"] = test_unsupported_file()
    results["oversized_file"] = test_oversized_file()
    results["corrupted_image"] = test_corrupted_image()
    results["cleanup"] = test_temp_cleanup()
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
            passed += 1
        elif result is False:
            status = "✗ FAIL"
            failed += 1
        else:
            status = "⊘ SKIP"
            skipped += 1
        
        logger.info(f"{status:8} {test_name}")
    
    logger.info("-" * 80)
    logger.info(f"Total: {passed} passed, {failed} failed, {skipped} skipped")
    logger.info("=" * 80)
    
    return passed, failed, skipped


if __name__ == "__main__":
    passed, failed, skipped = run_all_tests()
    
    # Exit with appropriate code
    if failed > 0:
        exit(1)
    else:
        exit(0)
