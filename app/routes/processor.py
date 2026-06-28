import os
import tempfile
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, HttpUrl
from sqlmodel import Session

from app.core.config import settings
from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.processor_service import ProcessorService

router = APIRouter(prefix="/media-processor", tags=["Media Processor"])


class ProcessRequest(BaseModel):
    sourceUrl: HttpUrl
    assetType: Literal["IMAGE", "VIDEO"]
    jobType: Literal[
        "IMAGE_BACKGROUND_REMOVAL",
        "VIDEO_BACKGROUND_REMOVAL",
        "IMAGE_ENHANCEMENT",
        "VIDEO_ENHANCEMENT",
    ]
    mimeType: str
    options: dict[str, Any] = {}


processor_service = ProcessorService(
    timeout_seconds=settings.MEDIA_DOWNLOAD_TIMEOUT_SECONDS,
    max_download_mb=settings.MEDIA_MAX_DOWNLOAD_MB,
)


def verify_processor_key(authorization: str | None):
    if not settings.MEDIA_PROCESSOR_API_KEY:
        return

    expected = f"Bearer {settings.MEDIA_PROCESSOR_API_KEY}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid media processor authorization.")


def normalize_output_url(request: Request, output_url: str) -> str:
    if output_url.startswith("http://") or output_url.startswith("https://"):
        return output_url

    base_url = (
        settings.MEDIA_PUBLIC_BASE_URL.rstrip("/")
        if settings.MEDIA_PUBLIC_BASE_URL
        else str(request.base_url).rstrip("/")
    )
    return f"{base_url}{output_url}"


def verify_processor_job(job_type: str) -> None:
    if "WATERMARK" in job_type:
        raise HTTPException(
            status_code=403,
            detail="Watermark removal is not available through this API.",
        )


async def authenticate_processor_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> User | None:
    bearer_token = None
    if authorization and authorization.startswith("Bearer "):
        bearer_token = authorization.removeprefix("Bearer ").strip()

    user = AuthService.get_user_from_any_api_key(
        session,
        x_api_key=x_api_key,
        bearer_token=bearer_token,
    )

    if settings.MEDIA_PROCESSOR_API_KEY and bearer_token == settings.MEDIA_PROCESSOR_API_KEY:
        return None

    if user:
        request.state.user_id = user.id
        return user

    if settings.MEDIA_PROCESSOR_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid media processor authorization.")

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Supply x-api-key or Bearer API key.",
    )


@router.get("/health")
async def processor_health():
    return {"status": "ok", "service": "python-media-processor"}


@router.post("/process")
async def process_media(
    request: Request,
    payload: ProcessRequest,
    _: User | None = Depends(authenticate_processor_user),
):
    verify_processor_job(payload.jobType)
    result = processor_service.process(
        str(payload.sourceUrl),
        payload.assetType,
        payload.jobType,
        payload.mimeType,
        payload.options,
    )

    if "outputUrl" in result:
        result["outputUrl"] = normalize_output_url(request, str(result["outputUrl"]))

    return result


@router.post("/upload/image/background-removal")
async def upload_image_background_removal(
    request: Request,
    file: UploadFile = File(...),
    _: User | None = Depends(authenticate_processor_user),
):
    return await _process_uploaded_media(
        request,
        file,
        asset_type="IMAGE",
        job_type="IMAGE_BACKGROUND_REMOVAL",
        options={},
    )


@router.post("/upload/video/background-removal")
async def upload_video_background_removal(
    request: Request,
    file: UploadFile = File(...),
    _: User | None = Depends(authenticate_processor_user),
):
    return await _process_uploaded_media(
        request,
        file,
        asset_type="VIDEO",
        job_type="VIDEO_BACKGROUND_REMOVAL",
        options={},
    )


@router.post("/upload/image/enhance")
async def upload_image_enhancement(
    request: Request,
    target_resolution: Literal["2k", "4k"] = "4k",
    face_enhance: bool = False,
    denoise: bool = True,
    sharpen: bool = True,
    file: UploadFile = File(...),
    _: User | None = Depends(authenticate_processor_user),
):
    return await _process_uploaded_media(
        request,
        file,
        asset_type="IMAGE",
        job_type="IMAGE_ENHANCEMENT",
        options={
            "targetResolution": target_resolution,
            "faceEnhance": face_enhance,
            "denoise": denoise,
            "sharpen": sharpen,
        },
    )


@router.post("/upload/video/enhance")
async def upload_video_enhancement(
    request: Request,
    target_resolution: Literal["2k", "4k"] = "2k",
    face_enhance: bool = False,
    denoise: bool = True,
    sharpen: bool = True,
    file: UploadFile = File(...),
    _: User | None = Depends(authenticate_processor_user),
):
    return await _process_uploaded_media(
        request,
        file,
        asset_type="VIDEO",
        job_type="VIDEO_ENHANCEMENT",
        options={
            "targetResolution": target_resolution,
            "faceEnhance": face_enhance,
            "denoise": denoise,
            "sharpen": sharpen,
        },
    )


async def _process_uploaded_media(
    request: Request,
    file: UploadFile,
    asset_type: Literal["IMAGE", "VIDEO"],
    job_type: Literal[
        "IMAGE_BACKGROUND_REMOVAL",
        "VIDEO_BACKGROUND_REMOVAL",
        "IMAGE_ENHANCEMENT",
        "VIDEO_ENHANCEMENT",
    ],
    options: dict[str, Any],
):
    mime_type = file.content_type or ""
    _validate_upload(asset_type, mime_type)
    suffix = os.path.splitext(file.filename or "")[1] or processor_service._suffix_from_mime(
        mime_type
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name
        temp_file.write(await file.read())

    try:
        result = processor_service.process_local_file(
            temp_path, asset_type, job_type, mime_type, options
        )
        if "outputUrl" in result:
            result["outputUrl"] = normalize_output_url(request, str(result["outputUrl"]))
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _validate_upload(asset_type: str, mime_type: str) -> None:
    allowed_types = {
        "IMAGE": {"image/jpeg", "image/png", "image/webp"},
        "VIDEO": {
            "video/mp4",
            "video/quicktime",
            "video/x-matroska",
            "video/x-msvideo",
            "video/webm",
        },
    }

    if mime_type not in allowed_types[asset_type]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported {asset_type.lower()} mime type: {mime_type}",
        )
