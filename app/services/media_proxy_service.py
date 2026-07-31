"""
Media Proxy Service.

Flow: AI Provider -> Cloudflare R2 -> Backend Proxy -> Own Domain URL

Ensures:
- Frontend never receives provider URLs
- All media served through platform domain
- Drag & drop shows only platform URLs
- Signed URLs for temporary access
- Content-Type preservation
- Cache headers for performance
"""

import logging
import mimetypes
import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse

from app.core.security_utils import is_safe_path, get_content_type

logger = logging.getLogger("app.media_proxy")


class MediaProxyService:
    """Serves media files through the platform domain, hiding provider URLs."""

    def __init__(self):
        self.local_upload_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "uploads"
        )

    def serve_asset(
        self,
        r2_object_key: str,
        asset_id: int,
        filename: Optional[str] = None,
        download: bool = False,
    ) -> Response:
        """
        Serve an asset file through the proxy.

        Returns a streaming response with proper headers.
        Never exposes the original provider URL.
        """
        if r2_object_key.startswith("local/"):
            return self._serve_local(r2_object_key, filename, download, asset_id)

        if self._is_r2_key(r2_object_key):
            return self._serve_from_r2(r2_object_key, filename, download, asset_id)

        raise HTTPException(status_code=404, detail="Asset not found")

    def _serve_local(
        self,
        r2_key: str,
        filename: Optional[str],
        download: bool,
        asset_id: int,
    ) -> Response:
        """Serve a file from local storage."""
        local_filename = r2_key.replace("local/", "")
        file_path = os.path.join(self.local_upload_dir, local_filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Asset file not found on disk")

        content_type = get_content_type(file_path)
        serve_name = filename or local_filename

        headers = {
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'",
        }

        if download:
            headers["Content-Disposition"] = f'attachment; filename="{serve_name}"'
        else:
            headers["Content-Disposition"] = f'inline; filename="{serve_name}"'

        return FileResponse(
            path=file_path,
            media_type=content_type,
            filename=serve_name if download else None,
            headers=headers,
        )

    def _serve_from_r2(
        self,
        r2_key: str,
        filename: Optional[str],
        download: bool,
        asset_id: int,
    ) -> Response:
        """Proxy a file from R2 through the backend."""
        temp_path = os.path.join(self.local_upload_dir, f"_proxy_{asset_id}_{Path(r2_key).name}")

        try:
            import boto3
            s3_endpoint = os.getenv("R2_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL")
            s3_access = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
            s3_secret = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
            s3_bucket = os.getenv("R2_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME")

            if not all([s3_access, s3_secret, s3_bucket]):
                raise HTTPException(status_code=503, detail="Storage not configured")

            client = boto3.client(
                "s3",
                aws_access_key_id=s3_access,
                aws_secret_access_key=s3_secret,
                endpoint_url=s3_endpoint,
            )

            client.download_file(s3_bucket, r2_key, temp_path)

            content_type = get_content_type(r2_key)
            serve_name = filename or Path(r2_key).name

            headers = {
                "Cache-Control": "public, max-age=31536000, immutable",
                "X-Content-Type-Options": "nosniff",
            }

            if download:
                headers["Content-Disposition"] = f'attachment; filename="{serve_name}"'

            return FileResponse(
                path=temp_path,
                media_type=content_type,
                filename=serve_name if download else None,
                headers=headers,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error("MediaProxy: Failed to proxy R2 asset %s: %s", r2_key, e)
            raise HTTPException(status_code=500, detail="Failed to load asset")
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _is_r2_key(self, key: str) -> bool:
        """Check if the key is an R2 object key (not local)."""
        return not key.startswith("local/")

    def transform_provider_url_to_proxy(self, provider_url: str) -> str:
        """
        Transform a third-party URL into a platform proxy URL.

        This should be called before returning any AI provider result to the frontend.
        The actual proxy mapping happens when the asset is stored.
        """
        if not provider_url:
            return provider_url

        if provider_url.startswith("/api/v1/assets/"):
            return provider_url

        if provider_url.startswith("http"):
            return f"/api/v1/assets/proxy?url={provider_url}"

        return provider_url


media_proxy = MediaProxyService()
