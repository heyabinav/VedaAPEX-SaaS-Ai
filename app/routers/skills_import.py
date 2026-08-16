"""API Router for Skill Ingestion (GitHub and Folder imports).

Endpoints:
- POST /api/v1/skills/import/github     - Import GitHub repository as skill
- POST /api/v1/skills/import/folder     - Import folder upload as skill
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.exceptions import AppException
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.services.skills.models import IngestionError
from app.services.skills.service import SkillService
from app.schemas.persistent_skill import SkillSingleResponse, SkillItem

logger = logging.getLogger("routers.skills_import")

router = APIRouter(prefix="/skills/import", tags=["Skill Ingestion"])


class SkillImportRequest:
    """Request body for GitHub skill import."""
    def __init__(self, url: str, name: Optional[str] = None, description: Optional[str] = None, level: Optional[str] = None):
        self.url = url
        self.name = name
        self.description = description
        self.level = level


from pydantic import BaseModel, Field


class GitHubImportRequest(BaseModel):
    """Request to import a GitHub repository as a skill."""
    url: str = Field(..., description="GitHub repository URL (e.g., https://github.com/owner/repo)")
    name: Optional[str] = Field(None, description="Custom skill name (optional)")
    description: Optional[str] = Field(None, description="Custom description (optional)")
    level: Optional[str] = Field(None, description="Skill level: beginner, intermediate, advanced, expert (optional)")


class FolderImportRequest(BaseModel):
    """Request to import a folder as a skill."""
    skill_name: str = Field(..., description="Name for the imported skill")
    description: Optional[str] = Field(None, description="Skill description (optional)")
    level: Optional[str] = Field(None, description="Skill level: beginner, intermediate, advanced, expert (optional)")


@router.post("/github", response_model=SkillSingleResponse)
async def import_github_skill(
    body: GitHubImportRequest,
    user: User = Depends(get_current_user_auth),
) -> SkillSingleResponse:
    """
    Import a GitHub repository as a user skill.
    
    Process:
    1. Validate GitHub URL
    2. Fetch repository contents safely
    3. Analyze repository structure and documentation
    4. Generate normalized skill
    5. Validate skill
    6. Store in user's skill registry
    
    Args:
        body: GitHub import request with URL and optional metadata
        user: Authenticated user
    
    Returns:
        SkillSingleResponse with imported skill details
    
    Raises:
        400: Invalid GitHub URL or ingestion failed
        401: Unauthorized
        429: Too many requests / rate limited
    """
    try:
        logger.info(f"GitHub skill import request from user {user.id}: {body.url}")
        
        # Import skill using the service
        result = await SkillService.import_github_skill(
            url=body.url,
            user_id=user.id,
            name=body.name,
            description=body.description,
            level=body.level,
        )
        
        if result["success"]:
            skill_data = result["skill"]
            return SkillSingleResponse(
                success=True,
                skill=SkillItem(**skill_data),
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to import GitHub skill"),
            )
    
    except IngestionError as e:
        logger.warning(f"Ingestion validation error: {e.code} - {e.message}")
        
        error_status_map = {
            "INVALID_GITHUB_URL": 400,
            "SSRF_DETECTED": 400,
            "GITHUB_FETCH_ERROR": 502,
            "SKILL_GENERATION_ERROR": 400,
            "SKILL_VALIDATION_ERROR": 400,
        }
        
        status_code = error_status_map.get(e.code, 400)
        raise HTTPException(
            status_code=status_code,
            detail=f"{e.code}: {e.message}",
        )
    
    except Exception as e:
        logger.error(f"Unexpected error importing GitHub skill: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)[:100]}",
        )


@router.post("/folder", response_model=SkillSingleResponse)
async def import_folder_skill(
    skill_name: str = Form(..., description="Name for the imported skill"),
    description: Optional[str] = Form(None, description="Skill description"),
    level: Optional[str] = Form(None, description="Skill level"),
    files: list[UploadFile] = File(..., description="Folder files (uploaded as ZIP or multiple files)"),
    user: User = Depends(get_current_user_auth),
) -> SkillSingleResponse:
    """
    Import an uploaded folder/archive as a user skill.
    
    Process:
    1. Receive folder files or ZIP archive
    2. Extract safely (path traversal protection, zip bomb protection)
    3. Analyze folder structure and documentation
    4. Generate normalized skill
    5. Validate skill
    6. Store in user's skill registry
    
    Args:
        skill_name: Name for the new skill
        description: Optional description
        level: Optional skill level
        files: Uploaded folder files (typically as a single ZIP file)
        user: Authenticated user
    
    Returns:
        SkillSingleResponse with imported skill details
    
    Raises:
        400: Invalid folder structure or ingestion failed
        401: Unauthorized
        413: File too large
    """
    try:
        logger.info(f"Folder skill import request from user {user.id}: {skill_name}")
        
        if not files or len(files) == 0:
            raise HTTPException(
                status_code=400,
                detail="No files uploaded",
            )
        
        # Handle single ZIP file
        if len(files) == 1:
            file = files[0]
            
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="File has no name",
                )
            
            # Read file bytes
            file_bytes = await file.read()
            
            if len(file_bytes) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file is empty",
                )
            
            # Import skill using the service
            result = await SkillService.import_folder_skill(
                zip_bytes=file_bytes,
                user_id=user.id,
                skill_name=skill_name,
                description=description,
                level=level,
            )
            
            if result["success"]:
                skill_data = result["skill"]
                return SkillSingleResponse(
                    success=True,
                    skill=SkillItem(**skill_data),
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=result.get("error", "Failed to import folder skill"),
                )
        
        else:
            # TODO: Handle multiple files (create ZIP in memory)
            raise HTTPException(
                status_code=400,
                detail="Multiple file uploads not yet supported; please upload as a single ZIP file",
            )
    
    except IngestionError as e:
        logger.warning(f"Ingestion error: {e.code} - {e.message}")
        
        error_status_map = {
            "FOLDER_ANALYSIS_ERROR": 400,
            "SKILL_GENERATION_ERROR": 400,
            "SKILL_VALIDATION_ERROR": 400,
        }
        
        status_code = error_status_map.get(e.code, 400)
        raise HTTPException(
            status_code=status_code,
            detail=f"{e.code}: {e.message}",
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error importing folder skill: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)[:100]}",
        )
