"""
AI Asset Storage Service.

Manages permanent storage of AI-generated assets in Cloudflare R2:
- Upload with organized paths: /users/{user_id}/{category}/
- Metadata tracking in database
- Deduplication via content hashing
- Proxy URL generation (own domain only)
- Async upload support

Never exposes third-party URLs to the frontend.
"""

import hashlib
import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlmodel import Session

from app.core.config import settings
from app.core.security_utils import (
    get_content_type,
    get_file_category,
    generate_secure_filename,
    sanitize_filename,
)
from app.models.asset import AIAsset

logger = logging.getLogger("app.asset_storage")


class AssetStorageService:
    """Handles AI asset storage with Cloudflare R2 and local fallback."""

    def __init__(self):
        self.s3_endpoint_url = os.getenv("R2_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL")
        self.s3_access_key = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        self.s3_secret_key = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.s3_bucket = os.getenv("R2_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME")

        self.local_upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "uploads"
        )
        os.makedirs(self.local_upload_dir, exist_ok=True)

        self.use_cloud = bool(self.s3_access_key and self.s3_secret_key and self.s3_bucket)

        if self.use_cloud:
            try:
                import boto3
                session_opts = {
                    "aws_access_key_id": self.s3_access_key,
                    "aws_secret_access_key": self.s3_secret_key,
                }
                if self.s3_endpoint_url:
                    session_opts["endpoint_url"] = self.s3_endpoint_url
                self.s3_client = boto3.client("s3", **session_opts)
                logger.info("AssetStorage: Cloud storage initialized (bucket=%s)", self.s3_bucket)
            except Exception as e:
                logger.error("AssetStorage: Cloud init failed, using local: %s", e)
                self.use_cloud = False
        else:
            logger.info("AssetStorage: Using local storage (cloud not configured)")

    def upload_asset(
        self,
        session: Session,
        *,
        user_id: int,
        local_path: str,
        original_filename: str,
        original_url: Optional[str] = None,
        provider: str = "unknown",
        model: Optional[str] = None,
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        resolution: Optional[str] = None,
        seed: Optional[int] = None,
        generation_time_ms: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> AIAsset:
        """
        Upload an AI-generated asset to storage and create a database record.

        Returns the AIAsset model with proxy URL.
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Source file not found: {local_path}")

        safe_name = sanitize_filename(original_filename)
        secure_name = generate_secure_filename(Path(safe_name).suffix or ".bin")

        file_size = os.path.getsize(local_path)
        mime_type = get_content_type(safe_name)
        category = get_file_category(safe_name)

        content_hash = None
        with open(local_path, "rb") as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()

        r2_key = f"users/{user_id}/{category}/{secure_name}"
        proxy_url = f"/api/v1/assets/{{file_id}}"

        r2_bucket = self.s3_bucket if self.use_cloud else None

        if self.use_cloud:
            try:
                self.s3_client.upload_file(
                    local_path,
                    self.s3_bucket,
                    r2_key,
                    ExtraArgs={
                        "ContentType": mime_type,
                        "CacheControl": "public, max-age=31536000",
                    },
                )
                logger.info("AssetStorage: Uploaded %s to R2://%s/%s", safe_name, self.s3_bucket, r2_key)
            except Exception as e:
                logger.error("AssetStorage: R2 upload failed for %s: %s", safe_name, e)
                local_dest = os.path.join(self.local_upload_dir, secure_name)
                if os.path.abspath(local_path) != os.path.abspath(local_dest):
                    shutil.copy2(local_path, local_dest)
                r2_key = f"local/{secure_name}"
        else:
            local_dest = os.path.join(self.local_upload_dir, secure_name)
            if os.path.abspath(local_path) != os.path.abspath(local_dest):
                shutil.copy2(local_path, local_dest)
            r2_key = f"local/{secure_name}"

        asset = AIAsset(
            user_id=user_id,
            asset_type=category,
            provider=provider,
            model=model,
            prompt=prompt[:2000] if prompt else None,
            negative_prompt=negative_prompt[:1000] if negative_prompt else None,
            resolution=resolution,
            seed=seed,
            original_url=original_url,
            r2_object_key=r2_key,
            r2_bucket=r2_bucket,
            proxy_url=proxy_url,
            file_size_bytes=file_size,
            mime_type=mime_type,
            file_hash=content_hash,
            generation_time_ms=generation_time_ms,
            status="completed",
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)

        asset.proxy_url = f"/api/v1/assets/{asset.id}"
        session.add(asset)
        session.commit()
        session.refresh(asset)

        logger.info(
            "AssetStorage: Asset #%d stored | User: %d | Type: %s | Provider: %s | Size: %d bytes",
            asset.id, user_id, category, provider, file_size,
        )

        return asset

    def get_asset_path(self, r2_key: str) -> Optional[str]:
        """Get the local path or download from R2 if needed."""
        if r2_key.startswith("local/"):
            filename = r2_key.replace("local/", "")
            local_path = os.path.join(self.local_upload_dir, filename)
            if os.path.exists(local_path):
                return local_path
            return None

        if self.use_cloud:
            local_path = os.path.join(self.local_upload_dir, os.path.basename(r2_key))
            try:
                self.s3_client.download_file(self.s3_bucket, r2_key, local_path)
                return local_path
            except Exception as e:
                logger.error("AssetStorage: Failed to download %s from R2: %s", r2_key, e)
                return None

        return None

    def delete_asset(self, r2_key: str) -> bool:
        """Delete an asset from storage."""
        success = False

        if self.use_cloud and not r2_key.startswith("local/"):
            try:
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=r2_key)
                success = True
            except Exception as e:
                logger.error("AssetStorage: R2 delete failed: %s", e)

        if r2_key.startswith("local/"):
            local_path = os.path.join(self.local_upload_dir, r2_key.replace("local/", ""))
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    success = True
                except Exception as e:
                    logger.error("AssetStorage: Local delete failed: %s", e)

        return success

    def get_signed_url(self, r2_key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a pre-signed URL for temporary access (R2 only)."""
        if not self.use_cloud or r2_key.startswith("local/"):
            return None

        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.s3_bucket, "Key": r2_key},
                ExpiresIn=expires_in,
            )
            return url
        except Exception as e:
            logger.error("AssetStorage: Signed URL generation failed: %s", e)
            return None

    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        local_files = 0
        local_size = 0
        for f in os.scandir(self.local_upload_dir):
            if f.is_file():
                local_files += 1
                local_size += f.stat().st_size

        return {
            "local_files": local_files,
            "local_size_bytes": local_size,
            "local_size_mb": round(local_size / (1024 * 1024), 2),
            "cloud_enabled": self.use_cloud,
            "bucket": self.s3_bucket,
        }


asset_storage = AssetStorageService()
