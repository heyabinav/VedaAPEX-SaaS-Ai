import os
import uuid
import logging
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    BackgroundTasks,
    Request,
)
from sqlmodel import Session, select
from datetime import datetime

from app.db.session import get_session
from app.models.user import User
from app.models.task import Task
from app.storage.storage_manager import storage_manager
from app.middleware.auth_middleware import authenticate_user
from app.middleware.rate_limit import rate_limit
from app.services.token_service import TokenService
from app.workers.tasks import (
    run_image_enhancement,
    run_video_enhancement,
    run_image_watermark_removal,
    run_video_watermark_removal,
    enhance_image_task,
    enhance_video_task,
    remove_watermark_image_task,
    remove_watermark_video_task,
)

logger = logging.getLogger("media_backend")

router = APIRouter(
    prefix="/media",
    tags=["SaaS Media Processing"],
    responses={404: {"description": "Not found"}},
)

# ─── Credit Cost Config ──────────────────────────────────
COST_IMAGE_ENHANCE = 5
COST_VIDEO_ENHANCE = 20
COST_IMAGE_WATERMARK = 5
COST_VIDEO_WATERMARK = 20


def is_celery_active() -> bool:
    """
    Checks if Celery message broker (Redis) is online and active.
    If offline, the router falls back to native FastAPI BackgroundTasks.
    """
    try:
        from app.workers.celery_app import celery_app

        # Run a quick check
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=1)
        return True
    except Exception:
        logger.warning(
            "Celery/Redis worker connection failed. Using FastAPI BackgroundTasks fallback."
        )
        return False


def verify_and_deduct_credits(session: Session, user: User, cost: int, description: str, ip: str):
    """
    Helper to check user plan and wallet balance, performing atomic credit deduction.
    """
    # Pro, Max, and Ultra users are granted free usage (unlimited)
    if user.subscription and user.subscription.status == "active":
        if user.subscription.plan.upper() in ["PRO", "MAX", "ULTRA"]:
            return  # Premium subscription zero-credit deduction bypass

    # Free users are evaluated
    try:
        TokenService.deduct_credits(
            session=session,
            user_id=user.id,
            amount=cost,
            tx_type="USAGE",
            description=description,
            ip_address=ip,
        )
    except ValueError as e:
        if str(e) == "INSUFFICIENT_CREDITS":
            wallet = TokenService.get_balance(session, user.id)
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "Insufficient Credits",
                    "required": cost,
                    "available": wallet.balance,
                    "suggestion": "Please upgrade your subscription to Pro, Max, or Ultra for unlimited access!",
                },
            )
        raise HTTPException(status_code=500, detail="Credit billing transaction failed.")


def get_task_priority(user: User) -> str:
    """VedaCLI: Determine Celery queue priority based on user subscription tier."""
    if not user.subscription or user.subscription.status != "active":
        return "low_priority"

    plan = user.subscription.plan.upper()
    if plan in ["ULTRA", "MAX"]:
        return "high_priority"
    elif plan == "PRO":
        return "default"
    return "low_priority"


# ─── Upload API Endpoints ─────────────────────────────────


@router.post("/upload/image", dependencies=[Depends(rate_limit(30, 60))])
async def upload_image(
    file: UploadFile = File(...), current_user: User = Depends(authenticate_user)
):
    """
    Uploads an image (JPG, PNG, WEBP), validates size (<15MB), and caches locally for processing.
    """
    # 1. Mime-type validations
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Only JPG, PNG, and WEBP are allowed.",
        )

    # 2. File size limit validations (15MB)
    MAX_SIZE = 15 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 15MB maximum limit.")

    # 3. Cache file
    ext = os.path.splitext(file.filename)[1] or ".png"
    unique_filename = f"upload_{uuid.uuid4().hex}{ext}"
    local_path = storage_manager.get_local_path(unique_filename)

    with open(local_path, "wb") as f:
        f.write(content)

    logger.info(f"Cached image upload from User {current_user.id}: {unique_filename}")
    return {
        "filename": unique_filename,
        "url": f"/api/v1/media/download/{unique_filename}",
    }


@router.post("/upload/video", dependencies=[Depends(rate_limit(10, 60))])
async def upload_video(
    file: UploadFile = File(...), current_user: User = Depends(authenticate_user)
):
    """
    Uploads a video (MP4, MOV, MKV, AVI), validates size (<100MB), and caches locally.
    """
    allowed_types = [
        "video/mp4",
        "video/quicktime",
        "video/x-matroska",
        "video/x-msvideo",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Only MP4, MOV, MKV, and AVI are allowed.",
        )

    # File size limit (100MB)
    MAX_SIZE = 100 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 100MB maximum limit.")

    ext = os.path.splitext(file.filename)[1] or ".mp4"
    unique_filename = f"upload_{uuid.uuid4().hex}{ext}"
    local_path = storage_manager.get_local_path(unique_filename)

    with open(local_path, "wb") as f:
        f.write(content)

    logger.info(f"Cached video upload from User {current_user.id}: {unique_filename}")
    return {
        "filename": unique_filename,
        "url": f"/api/v1/media/download/{unique_filename}",
    }


# ─── Enhancement APIs ────────────────────────────────────


@router.post("/enhance/image")
async def enhance_image(
    request: Request,
    filename: str,
    scale: int = 4,
    face_enhance: bool = False,
    denoise: bool = True,
    sharpen: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(authenticate_user),
    session: Session = Depends(get_session),
):
    """
    Triggers the Image Enhancer job. Deducts 5 credits from Free users.
    """
    if scale not in [2, 4]:
        raise HTTPException(status_code=400, detail="Super-resolution scale must be 2 or 4.")

    local_path = storage_manager.get_local_path(filename)
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Uploaded file not found. Upload it first.")

    # 1. Billing check and credit deduction
    verify_and_deduct_credits(
        session=session,
        user=current_user,
        cost=COST_IMAGE_ENHANCE,
        description=f"AI Image Enhancer ({scale}x scale)",
        ip=request.client.host,
    )

    # 2. Register DB Task
    task_id = f"task_img_enh_{uuid.uuid4().hex[:16]}"
    task = Task(
        id=task_id,
        user_id=current_user.id,
        type="enhance_image",
        status="PENDING",
        progress=0,
        input_path=filename,
    )
    session.add(task)
    session.commit()

    options = {
        "scale": scale,
        "face_enhance": face_enhance,
        "denoise": denoise,
        "sharpen": sharpen,
    }

    # 3. Schedule task with priority queuing
    if is_celery_active():
        enhance_image_task.apply_async(
            args=[task_id, local_path, options], queue=get_task_priority(current_user)
        )
    else:
        background_tasks.add_task(run_image_enhancement, task_id, local_path, options)

    return {
        "success": True,
        "task_id": task_id,
        "status": "PENDING",
        "cost": COST_IMAGE_ENHANCE,
    }


@router.post("/enhance/video")
async def enhance_video(
    request: Request,
    filename: str,
    scale: int = 2,
    face_enhance: bool = False,
    denoise: bool = True,
    sharpen: bool = True,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(authenticate_user),
    session: Session = Depends(get_session),
):
    """
    Triggers Video Super-resolution sequence. Deducts 20 credits from Free users.
    """
    if scale not in [2, 4]:
        raise HTTPException(status_code=400, detail="Super-resolution scale must be 2 or 4.")

    local_path = storage_manager.get_local_path(filename)
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Uploaded file not found. Upload it first.")

    verify_and_deduct_credits(
        session=session,
        user=current_user,
        cost=COST_VIDEO_ENHANCE,
        description=f"AI Video Enhancer ({scale}x scale)",
        ip=request.client.host,
    )

    task_id = f"task_vid_enh_{uuid.uuid4().hex[:16]}"
    task = Task(
        id=task_id,
        user_id=current_user.id,
        type="enhance_video",
        status="PENDING",
        progress=0,
        input_path=filename,
    )
    session.add(task)
    session.commit()

    options = {
        "scale": scale,
        "face_enhance": face_enhance,
        "denoise": denoise,
        "sharpen": sharpen,
    }

    if is_celery_active():
        enhance_video_task.apply_async(
            args=[task_id, local_path, options], queue=get_task_priority(current_user)
        )
    else:
        background_tasks.add_task(run_video_enhancement, task_id, local_path, options)

    return {
        "success": True,
        "task_id": task_id,
        "status": "PENDING",
        "cost": COST_VIDEO_ENHANCE,
    }


# ─── Watermark Removal APIs ──────────────────────────────


@router.post("/remove-watermark/image")
async def remove_watermark_image(
    request: Request,
    filename: str,
    mask_filename: str,
    algorithm: str = "telea",  # "telea", "ns" or "lama"
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(authenticate_user),
    session: Session = Depends(get_session),
):
    """
    Triggers watermark object removal using binary mask. Deducts 5 credits.
    """
    local_path = storage_manager.get_local_path(filename)
    mask_path = storage_manager.get_local_path(mask_filename)

    if not os.path.exists(local_path) or not os.path.exists(mask_path):
        raise HTTPException(
            status_code=404,
            detail="Source image or mask file not found in uploads cache.",
        )

    verify_and_deduct_credits(
        session=session,
        user=current_user,
        cost=COST_IMAGE_WATERMARK,
        description="Image Watermark Remover",
        ip=request.client.host,
    )

    task_id = f"task_img_wtm_{uuid.uuid4().hex[:16]}"
    task = Task(
        id=task_id,
        user_id=current_user.id,
        type="remove_watermark_image",
        status="PENDING",
        progress=0,
        input_path=filename,
    )
    session.add(task)
    session.commit()

    options = {"algorithm": algorithm}

    if is_celery_active():
        remove_watermark_image_task.apply_async(
            args=[task_id, local_path, mask_path, options],
            queue=get_task_priority(current_user),
        )
    else:
        background_tasks.add_task(
            run_image_watermark_removal, task_id, local_path, mask_path, options
        )

    return {
        "success": True,
        "task_id": task_id,
        "status": "PENDING",
        "cost": COST_IMAGE_WATERMARK,
    }


@router.post("/remove-watermark/video")
async def remove_watermark_video(
    request: Request,
    filename: str,
    mask_filename: str,
    algorithm: str = "telea",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(authenticate_user),
    session: Session = Depends(get_session),
):
    """
    Triggers video frame watermark removal using binary mask. Deducts 20 credits.
    """
    local_path = storage_manager.get_local_path(filename)
    mask_path = storage_manager.get_local_path(mask_filename)

    if not os.path.exists(local_path) or not os.path.exists(mask_path):
        raise HTTPException(
            status_code=404,
            detail="Source video or mask image not found in uploads cache.",
        )

    verify_and_deduct_credits(
        session=session,
        user=current_user,
        cost=COST_VIDEO_WATERMARK,
        description="Video Watermark Remover",
        ip=request.client.host,
    )

    task_id = f"task_vid_wtm_{uuid.uuid4().hex[:16]}"
    task = Task(
        id=task_id,
        user_id=current_user.id,
        type="remove_watermark_video",
        status="PENDING",
        progress=0,
        input_path=filename,
    )
    session.add(task)
    session.commit()

    options = {"algorithm": algorithm}

    if is_celery_active():
        remove_watermark_video_task.apply_async(
            args=[task_id, local_path, mask_path, options],
            queue=get_task_priority(current_user),
        )
    else:
        background_tasks.add_task(
            run_video_watermark_removal, task_id, local_path, mask_path, options
        )

    return {
        "success": True,
        "task_id": task_id,
        "status": "PENDING",
        "cost": COST_VIDEO_WATERMARK,
    }


# ─── Status, Serving & Deletions ─────────────────────────


@router.get("/task/status/{id}")
async def get_task_status(
    id: str,
    current_user: User = Depends(authenticate_user),
    session: Session = Depends(get_session),
):
    """
    Returns progress metrics, task states, outputs, and exception errors.
    """
    task = session.get(Task, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    # Restrict users from viewing other tenants' tasks (multi-user isolation)
    if task.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Forbidden. Multi-user access violation.")

    return {
        "task_id": task.id,
        "type": task.type,
        "status": task.status,
        "progress": task.progress,
        "output_url": task.output_path,
        "error": task.error_message,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


@router.get("/download/{filename}")
async def get_file_download(filename: str):
    """
    Directly serves outputs and cache uploads from the local filesystem when cloud is disabled.
    """
    from fastapi.responses import FileResponse

    local_path = storage_manager.get_local_path(filename)
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="Media file not found on disk.")

    return FileResponse(local_path)


@router.delete("/cleanup/{id}")
async def cleanup_task(
    id: str,
    current_user: User = Depends(authenticate_user),
    session: Session = Depends(get_session),
):
    """
    Flushes cache files linked with a task ID from storage and deletes the database task record.
    """
    task = session.get(Task, id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    if task.user_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Access denied.")

    # Remove files
    storage_manager.delete_file(task.input_path)
    if task.output_path:
        # Extract filename from url
        out_filename = os.path.basename(task.output_path)
        storage_manager.delete_file(out_filename)

    # Delete task
    session.delete(task)
    session.commit()

    return {
        "success": True,
        "message": f"Flushed all cache files and task {id} deleted successfully.",
    }
