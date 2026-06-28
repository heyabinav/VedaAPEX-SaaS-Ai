import os
import shutil
import tempfile
import logging
import requests
from datetime import datetime
from sqlmodel import Session
from app.db.session import engine
from app.models.task import Task
from app.workers.celery_app import celery_app
from app.storage.storage_manager import storage_manager
from app.ffmpeg.video_processor import VideoProcessor
from app.enhancer.image_enhancer import ImageEnhancer
from app.watermark.watermark_remover import WatermarkRemover

logger = logging.getLogger("media_backend")

# Initialize enhancers and watermarks
image_enhancer = ImageEnhancer()
watermark_remover = WatermarkRemover()


def update_task_db(
    task_id: str,
    status: str,
    progress: int,
    output_path: str = None,
    error_message: str = None,
):
    """
    Updates the database state for a background task.
    """
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if task:
            task.status = status
            task.progress = progress
            if output_path:
                task.output_path = output_path
            if error_message:
                task.error_message = error_message
            task.updated_at = datetime.utcnow()
            session.add(task)
            session.commit()
            logger.info(f"Updated Task {task_id} in DB: Status={status}, Progress={progress}%")


def trigger_webhook(task_id: str, status: str, output_url: str = None, error: str = None):
    """
    Optionally sends a Webhook notification containing task updates to target endpoints.
    """
    webhook_url = os.getenv("WEBHOOK_NOTIFICATION_URL")
    if not webhook_url:
        return

    try:
        payload = {
            "event": ("media_task.completed" if status == "COMPLETED" else "media_task.failed"),
            "task_id": task_id,
            "status": status,
            "output_url": output_url,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
        }
        response = requests.post(webhook_url, json=payload, timeout=5)
        logger.info(f"Webhook broadcasted to {webhook_url}. Response code: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed sending webhook notification: {e}")


# ─── Dual-Mode Core Execution Logic ──────────────────────


def run_image_enhancement(task_id: str, file_path: str, options: dict) -> str:
    """
    Runs the image enhancement sequence.
    """
    try:
        update_task_db(task_id, "PROCESSING", 20)

        # Determine output location
        filename = os.path.basename(file_path)
        output_filename = f"enhanced_{filename}"
        output_local_path = storage_manager.get_local_path(output_filename)

        # Execute enhancement pipeline
        image_enhancer.enhance(
            input_path=file_path,
            output_path=output_local_path,
            scale=options.get("scale", 4),
            face_enhance=options.get("face_enhance", False),
            denoise=options.get("denoise", True),
            sharpen=options.get("sharpen", True),
        )

        update_task_db(task_id, "PROCESSING", 80)

        # Upload completed output to storage manager
        output_url = storage_manager.upload_file(output_local_path, output_filename)

        update_task_db(task_id, "COMPLETED", 100, output_path=output_url)
        trigger_webhook(task_id, "COMPLETED", output_url)

        # Auto cleanup raw uploaded file if needed
        if os.path.exists(file_path):
            os.remove(file_path)

        return output_url
    except Exception as e:
        logger.error(f"Error in image enhancement task {task_id}: {e}")
        update_task_db(task_id, "FAILED", 100, error_message=str(e))
        trigger_webhook(task_id, "FAILED", error=str(e))
        raise e


def run_video_enhancement(task_id: str, file_path: str, options: dict) -> str:
    """
    Runs video super-resolution sequence frame-by-frame.
    """
    temp_dir = tempfile.mkdtemp(prefix=f"video_enhance_{task_id}_")
    try:
        update_task_db(task_id, "PROCESSING", 10)

        # Analyze original video details
        info = VideoProcessor.get_video_info(file_path)

        # Extract frames to temp folder
        frame_dir = os.path.join(temp_dir, "frames")
        VideoProcessor.extract_frames(file_path, frame_dir)
        update_task_db(task_id, "PROCESSING", 25)

        # Select and enhance frames in target folder
        frames = sorted([f for f in os.listdir(frame_dir) if f.endswith(".png")])
        total_frames = len(frames)

        if total_frames == 0:
            raise RuntimeError("FFmpeg frame extraction yielded zero frames.")

        logger.info(f"Enhancing {total_frames} video frames...")

        # Enhances frames and updates progress indicators
        for i, frame in enumerate(frames):
            frame_path = os.path.join(frame_dir, frame)
            # Enhance frame in-place
            image_enhancer.enhance(
                input_path=frame_path,
                output_path=frame_path,
                scale=options.get("scale", 2),  # Default 2x for video to optimize speed
                face_enhance=options.get("face_enhance", False),
                denoise=options.get("denoise", True),
                sharpen=options.get("sharpen", True),
            )

            # Progress increments between 25% and 85%
            current_progress = 25 + int((i / total_frames) * 60)
            if i % max(1, total_frames // 10) == 0:
                update_task_db(task_id, "PROCESSING", current_progress)

        update_task_db(task_id, "PROCESSING", 85)

        # Reassemble the video
        filename = os.path.basename(file_path)
        output_filename = f"enhanced_{filename}"
        output_local_path = storage_manager.get_local_path(output_filename)

        VideoProcessor.assemble_video(
            frame_dir=frame_dir,
            original_video_path=file_path,
            output_path=output_local_path,
            fps=info["fps"],
            has_audio=info["has_audio"],
        )

        update_task_db(task_id, "PROCESSING", 95)

        # Upload complete video
        output_url = storage_manager.upload_file(output_local_path, output_filename)

        update_task_db(task_id, "COMPLETED", 100, output_path=output_url)
        trigger_webhook(task_id, "COMPLETED", output_url)

        # Auto cleanup uploads
        if os.path.exists(file_path):
            os.remove(file_path)

        return output_url
    except Exception as e:
        logger.error(f"Error in video enhancement task {task_id}: {e}")
        update_task_db(task_id, "FAILED", 100, error_message=str(e))
        trigger_webhook(task_id, "FAILED", error=str(e))
        raise e
    finally:
        # File removal for extracted sequences
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def run_image_watermark_removal(task_id: str, file_path: str, mask_path: str, options: dict) -> str:
    """
    Runs image watermark removal sequence.
    """
    try:
        update_task_db(task_id, "PROCESSING", 20)

        filename = os.path.basename(file_path)
        output_filename = f"clean_{filename}"
        output_local_path = storage_manager.get_local_path(output_filename)

        # Execute watermark removal
        watermark_remover.remove_watermark(
            image_path=file_path,
            mask_path=mask_path,
            output_path=output_local_path,
            algorithm=options.get("algorithm", "telea"),
        )

        update_task_db(task_id, "PROCESSING", 80)

        # Upload clean image
        output_url = storage_manager.upload_file(output_local_path, output_filename)

        update_task_db(task_id, "COMPLETED", 100, output_path=output_url)
        trigger_webhook(task_id, "COMPLETED", output_url)

        # Cleanup temporary input uploads
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(mask_path):
            os.remove(mask_path)

        return output_url
    except Exception as e:
        logger.error(f"Error in image watermark removal task {task_id}: {e}")
        update_task_db(task_id, "FAILED", 100, error_message=str(e))
        trigger_webhook(task_id, "FAILED", error=str(e))
        raise e


def run_video_watermark_removal(task_id: str, file_path: str, mask_path: str, options: dict) -> str:
    """
    Runs video frame-by-frame watermark removal.
    """
    temp_dir = tempfile.mkdtemp(prefix=f"video_watermark_{task_id}_")
    try:
        update_task_db(task_id, "PROCESSING", 10)

        # Analyze original video details
        info = VideoProcessor.get_video_info(file_path)

        # Extract frames to temp folder
        frame_dir = os.path.join(temp_dir, "frames")
        VideoProcessor.extract_frames(file_path, frame_dir)
        update_task_db(task_id, "PROCESSING", 25)

        # Process each frame
        frames = sorted([f for f in os.listdir(frame_dir) if f.endswith(".png")])
        total_frames = len(frames)

        if total_frames == 0:
            raise RuntimeError("FFmpeg frame extraction yielded zero frames.")

        logger.info(f"Removing watermark from {total_frames} frames...")

        for i, frame in enumerate(frames):
            frame_path = os.path.join(frame_dir, frame)
            # Remove watermark from frame in-place
            watermark_remover.remove_watermark(
                image_path=frame_path,
                mask_path=mask_path,
                output_path=frame_path,
                algorithm=options.get("algorithm", "telea"),
            )

            # Progress increments between 25% and 85%
            current_progress = 25 + int((i / total_frames) * 60)
            if i % max(1, total_frames // 10) == 0:
                update_task_db(task_id, "PROCESSING", current_progress)

        update_task_db(task_id, "PROCESSING", 85)

        # Reassemble video
        filename = os.path.basename(file_path)
        output_filename = f"clean_{filename}"
        output_local_path = storage_manager.get_local_path(output_filename)

        VideoProcessor.assemble_video(
            frame_dir=frame_dir,
            original_video_path=file_path,
            output_path=output_local_path,
            fps=info["fps"],
            has_audio=info["has_audio"],
        )

        update_task_db(task_id, "PROCESSING", 95)

        # Upload complete video
        output_url = storage_manager.upload_file(output_local_path, output_filename)

        update_task_db(task_id, "COMPLETED", 100, output_path=output_url)
        trigger_webhook(task_id, "COMPLETED", output_url)

        # Cleanup upload cache files
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(mask_path):
            os.remove(mask_path)

        return output_url
    except Exception as e:
        logger.error(f"Error in video watermark removal task {task_id}: {e}")
        update_task_db(task_id, "FAILED", 100, error_message=str(e))
        trigger_webhook(task_id, "FAILED", error=str(e))
        raise e
    finally:
        # File removal for extracted sequences
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# ─── Celery Task Definitions (for Redis Workers) ─────────


@celery_app.task(name="tasks.enhance_image")
def enhance_image_task(task_id: str, file_path: str, options: dict):
    return run_image_enhancement(task_id, file_path, options)


@celery_app.task(name="tasks.enhance_video")
def enhance_video_task(task_id: str, file_path: str, options: dict):
    return run_video_enhancement(task_id, file_path, options)


@celery_app.task(name="tasks.remove_watermark_image")
def remove_watermark_image_task(task_id: str, file_path: str, mask_path: str, options: dict):
    return run_image_watermark_removal(task_id, file_path, mask_path, options)


@celery_app.task(name="tasks.remove_watermark_video")
def remove_watermark_video_task(task_id: str, file_path: str, mask_path: str, options: dict):
    return run_video_watermark_removal(task_id, file_path, mask_path, options)
