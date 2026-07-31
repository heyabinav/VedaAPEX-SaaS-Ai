"""
Background worker for async media uploads.

Provides:
- Async upload to R2 without blocking the request
- Retry logic for transient failures
- Upload progress tracking
"""

import asyncio
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("app.workers.async_upload")


class AsyncUploadWorker:
    """
    Background worker that handles async uploads to Cloudflare R2.
    Used by the asset storage service for non-blocking uploads.
    """

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the background upload worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("AsyncUploadWorker started")

    async def stop(self):
        """Stop the background upload worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        logger.info("AsyncUploadWorker stopped")

    async def enqueue_upload(
        self,
        local_path: str,
        r2_key: str,
        content_type: str = "application/octet-stream",
        max_retries: int = 3,
        callback=None,
    ):
        """Enqueue a file for async upload to R2."""
        await self._queue.put({
            "local_path": local_path,
            "r2_key": r2_key,
            "content_type": content_type,
            "max_retries": max_retries,
            "retries": 0,
            "callback": callback,
            "enqueued_at": time.time(),
        })

    async def _process_queue(self):
        """Process upload queue items."""
        while self._running:
            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            success = await self._upload_with_retry(item)
            if not success and item["retries"] < item["max_retries"]:
                item["retries"] += 1
                await asyncio.sleep(2 ** item["retries"])
                await self._queue.put(item)

    async def _upload_with_retry(self, item: dict) -> bool:
        """Upload a single file with retry logic."""
        local_path = item["local_path"]
        r2_key = item["r2_key"]

        if not os.path.exists(local_path):
            logger.error("AsyncUpload: File not found: %s", local_path)
            return False

        try:
            import boto3

            s3_endpoint = os.getenv("R2_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL")
            s3_access = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
            s3_secret = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
            s3_bucket = os.getenv("R2_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME")

            if not all([s3_access, s3_secret, s3_bucket]):
                logger.warning("AsyncUpload: R2 not configured, skipping upload")
                return False

            loop = asyncio.get_event_loop()
            client = boto3.client(
                "s3",
                aws_access_key_id=s3_access,
                aws_secret_access_key=s3_secret,
                endpoint_url=s3_endpoint,
            )

            await loop.run_in_executor(
                None,
                lambda: client.upload_file(
                    local_path, s3_bucket, r2_key,
                    ExtraArgs={"ContentType": item["content_type"]},
                ),
            )

            duration = time.time() - item["enqueued_at"]
            logger.info(
                "AsyncUpload: Uploaded %s -> R2://%s/%s (%.1fs, attempt %d)",
                os.path.basename(local_path), s3_bucket, r2_key,
                duration, item["retries"] + 1,
            )

            if item.get("callback"):
                try:
                    await item["callback"](r2_key)
                except Exception as e:
                    logger.error("AsyncUpload: Callback failed: %s", e)

            return True

        except Exception as e:
            logger.error(
                "AsyncUpload: Failed to upload %s (attempt %d/%d): %s",
                os.path.basename(local_path), item["retries"] + 1,
                item["max_retries"], e,
            )
            return False

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()


async_upload_worker = AsyncUploadWorker()
