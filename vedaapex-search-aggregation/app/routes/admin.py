import os
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from typing import Optional

from app.db.session import get_session
from app.models.user import User
from app.models.task import Task
from app.models.token import TokenWallet, TokenTransaction
from app.middleware.auth_middleware import authenticate_admin

router = APIRouter(
    prefix="/admin/dashboard",
    tags=["Admin Media Dashboard"],
    dependencies=[Depends(authenticate_admin)],
    responses={403: {"description": "Administrative access only."}},
)


@router.get("/queue/status")
async def get_queue_status(session: Session = Depends(get_session)):
    """
    Queue Monitoring API. Returns real-time counts of background media tasks grouped by status.
    """
    try:
        # Group by status counts
        statuses = ["PENDING", "PROCESSING", "COMPLETED", "FAILED"]
        status_counts = {status: 0 for status in statuses}

        # Query DB for counts
        for status in statuses:
            count = len(session.exec(select(Task).where(Task.status == status)).all())
            status_counts[status] = count

        # Get active Celery task queues if Celery is running
        celery_stats = {"worker_nodes": "Offline"}
        try:
            from app.workers.celery_app import celery_app

            inspect = celery_app.control.inspect()
            if inspect:
                active = inspect.active() or {}
                reserved = inspect.reserved() or {}
                celery_stats = {
                    "worker_nodes": len(active),
                    "active_tasks_count": sum(len(tasks) for tasks in active.values()),
                    "reserved_tasks_count": sum(len(tasks) for tasks in reserved.values()),
                }
        except Exception:
            pass  # Celery inspector offline

        return {
            "success": True,
            "queue_active": celery_stats.get("worker_nodes") != "Offline",
            "db_tasks": status_counts,
            "celery_workers": celery_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch queue status: {str(e)}")


@router.get("/tasks/list")
async def get_tasks_list(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    Administrative Auditing API. Returns a paginated list of all media tasks in the system.
    """
    query = select(Task)

    if status:
        query = query.where(Task.status == status.upper())
    if task_type:
        query = query.where(Task.type == task_type)

    query = query.order_by(Task.created_at.desc())

    all_tasks = session.exec(query).all()
    total = len(all_tasks)
    offset = (page - 1) * limit
    paginated_tasks = all_tasks[offset : offset + limit]

    result = []
    for t in paginated_tasks:
        user = session.get(User, t.user_id)
        result.append(
            {
                "task_id": t.id,
                "user": {
                    "id": t.user_id,
                    "email": user.email if user else "Deleted User",
                },
                "type": t.type,
                "status": t.status,
                "progress": t.progress,
                "input_file": t.input_path,
                "output_url": t.output_path,
                "error": t.error_message,
                "created_at": t.created_at.isoformat(),
            }
        )

    return {
        "success": True,
        "data": {
            "tasks": result,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": max(1, -(-total // limit)),
            },
        },
    }


@router.get("/usage/metrics")
async def get_usage_metrics(session: Session = Depends(get_session)):
    """
    Tenant Usage Analytics API. Aggregates system metrics (credits spent, successful runs).
    """
    # 1. Calculate credit spent on media processing
    media_types = ["USAGE"]
    txs = session.exec(
        select(TokenTransaction).where(
            TokenTransaction.type == "USAGE",
            TokenTransaction.description.contains("Image")
            | TokenTransaction.description.contains("Video"),
        )
    ).all()

    total_credits_spent = abs(sum(t.amount for t in txs))

    # 2. Get task type distribution
    task_types = [
        "enhance_image",
        "enhance_video",
        "remove_watermark_image",
        "remove_watermark_video",
    ]
    type_counts = {}
    for t_type in task_types:
        count = len(
            session.exec(select(Task).where(Task.type == t_type, Task.status == "COMPLETED")).all()
        )
        type_counts[t_type] = count

    return {
        "success": True,
        "metrics": {
            "completed_image_enhancers": type_counts.get("enhance_image", 0),
            "completed_video_enhancers": type_counts.get("enhance_video", 0),
            "completed_image_watermark_removers": type_counts.get("remove_watermark_image", 0),
            "completed_video_watermark_removers": type_counts.get("remove_watermark_video", 0),
            "total_media_credits_billed": total_credits_spent,
        },
    }
