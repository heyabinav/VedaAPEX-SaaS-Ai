import os
import shutil
from typing import Optional
import logging
from app.core.config import settings

logger = logging.getLogger("media_backend")


class StorageManager:
    """
    SaaS Storage Manager that supports AWS S3 / Cloudflare R2 with automatic Local Storage fallback.
    """

    def __init__(self):
        # Read storage credentials from environment
        self.s3_endpoint_url = os.getenv("R2_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL")
        self.s3_access_key = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")
        self.s3_secret_key = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.s3_bucket = os.getenv("R2_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME")

        # Local storage setup
        self.local_upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        os.makedirs(self.local_upload_dir, exist_ok=True)

        # Detect if we should use Cloud Storage
        self.use_cloud = all([self.s3_access_key, self.s3_secret_key, self.s3_bucket])

        if self.use_cloud:
            try:
                import boto3

                # Configure client
                session_opts = {
                    "aws_access_key_id": self.s3_access_key,
                    "aws_secret_access_key": self.s3_secret_key,
                }
                if self.s3_endpoint_url:
                    session_opts["endpoint_url"] = self.s3_endpoint_url

                self.s3_client = boto3.client("s3", **session_opts)
                logger.info(
                    f"Cloud storage initialized successfully using bucket: {self.s3_bucket}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize cloud storage client. Falling back to local storage. Error: {e}"
                )
                self.use_cloud = False
        else:
            logger.info(
                "Cloud storage environment variables not complete. Local storage is active."
            )

    def upload_file(self, local_path: str, filename: str) -> str:
        """
        Uploads a local file to storage.
        Returns the public or static download URL.
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Source file not found at {local_path}")

        if self.use_cloud:
            try:
                # Content type guessing
                content_type = "application/octet-stream"
                if filename.lower().endswith((".jpg", ".jpeg")):
                    content_type = "image/jpeg"
                elif filename.lower().endswith(".png"):
                    content_type = "image/png"
                elif filename.lower().endswith(".webp"):
                    content_type = "image/webp"
                elif filename.lower().endswith(".mp4"):
                    content_type = "video/mp4"
                elif filename.lower().endswith(".mov"):
                    content_type = "video/quicktime"

                # Upload to S3/R2
                self.s3_client.upload_file(
                    local_path,
                    self.s3_bucket,
                    filename,
                    ExtraArgs={"ContentType": content_type},
                )

                # Construct public download URL
                if self.s3_endpoint_url:
                    # Cloudflare R2 or Custom Endpoint URL structure
                    url = f"{self.s3_endpoint_url.rstrip('/')}/{self.s3_bucket}/{filename}"
                else:
                    # Standard AWS S3 URL structure
                    url = f"https://{self.s3_bucket}.s3.amazonaws.com/{filename}"

                logger.info(f"Uploaded {filename} to Cloud Storage: {url}")
                return url
            except Exception as e:
                logger.error(f"Cloud upload failed for {filename}, caching locally. Error: {e}")
                # Fallback to local

        # Local storage execution
        dest_path = os.path.join(self.local_upload_dir, filename)
        if os.path.abspath(local_path) != os.path.abspath(dest_path):
            shutil.copy2(local_path, dest_path)

        logger.info(f"File cached in local storage at: {dest_path}")

        # Returns a path relative to the api base that is served via our GET /download/{id} route
        return f"/api/v1/media/download/{filename}"

    def delete_file(self, filename: str) -> bool:
        """
        Deletes a file from either cloud storage or local disk.
        """
        success = False
        if self.use_cloud:
            try:
                self.s3_client.delete_object(Bucket=self.s3_bucket, Key=filename)
                logger.info(f"Deleted {filename} from Cloud Storage.")
                success = True
            except Exception as e:
                logger.error(f"Failed to delete {filename} from cloud storage: {e}")

        # Always check and delete locally as well
        local_path = os.path.join(self.local_upload_dir, filename)
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
                logger.info(f"Deleted {filename} from local storage.")
                success = True
            except Exception as e:
                logger.error(f"Failed to delete local file {local_path}: {e}")

        return success

    def get_local_path(self, filename: str) -> str:
        """
        Helper to return local file path for local processing.
        """
        return os.path.join(self.local_upload_dir, filename)


# Global singleton storage manager
storage_manager = StorageManager()
