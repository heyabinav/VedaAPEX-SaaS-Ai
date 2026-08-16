"""High-level skill ingestion service API."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from app.services.hf_storage.skills import SkillStorageService

from .ingestion import SkillIngestionService
from .models import GeneratedSkill, IngestionError

logger = logging.getLogger("services.skills.service")


class SkillService:
    """High-level API for skill ingestion and management."""
    
    @staticmethod
    async def import_github_skill(
        url: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import a GitHub repository as a user skill.
        
        Args:
            url: GitHub repository URL
            user_id: User ID (from authentication)
            name: Optional custom skill name
            description: Optional custom description
            level: Optional skill level (beginner, intermediate, advanced, expert)
        
        Returns:
            {
                "success": true,
                "skill": {
                    "id": "skill_xxx",
                    "name": "...",
                    "description": "...",
                    "level": "...",
                    "source": "user_requested",
                    "enabled": true
                }
            }
        
        Raises: IngestionError subclasses on failure
        """
        try:
            logger.info(f"Importing GitHub skill from {url} for user {user_id}")
            
            # Ingest the repository
            skill = await SkillIngestionService.ingest_github_url(
                url,
                user_id,
                name=name,
                description=description,
                level=level,
            )
            
            # Store the skill using existing storage service
            stored_skill = SkillService._store_generated_skill(user_id, skill)
            
            logger.info(f"GitHub skill stored: {stored_skill['id']}")
            
            return {
                "success": True,
                "skill": stored_skill,
            }
        
        except IngestionError as e:
            logger.error(f"Ingestion error: {e.code} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error importing GitHub skill: {e}")
            raise IngestionError("IMPORT_ERROR", str(e))
    
    @staticmethod
    async def import_folder_skill(
        zip_bytes: bytes,
        user_id: str,
        skill_name: Optional[str] = None,
        description: Optional[str] = None,
        level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import an uploaded folder/archive as a user skill.
        
        Args:
            zip_bytes: ZIP archive bytes
            user_id: User ID (from authentication)
            skill_name: Custom skill name
            description: Optional custom description
            level: Optional skill level (beginner, intermediate, advanced, expert)
        
        Returns:
            {
                "success": true,
                "skill": {
                    "id": "skill_xxx",
                    "name": "...",
                    "description": "...",
                    "level": "...",
                    "source": "user_requested",
                    "enabled": true
                }
            }
        
        Raises: IngestionError subclasses on failure
        """
        try:
            logger.info(f"Importing folder skill for user {user_id}")
            
            # Ingest the folder
            skill = await SkillIngestionService.ingest_folder_upload(
                zip_bytes,
                user_id,
                skill_name=skill_name,
                description=description,
                level=level,
            )
            
            # Store the skill using existing storage service
            stored_skill = SkillService._store_generated_skill(user_id, skill)
            
            logger.info(f"Folder skill stored: {stored_skill['id']}")
            
            return {
                "success": True,
                "skill": stored_skill,
            }
        
        except IngestionError as e:
            logger.error(f"Ingestion error: {e.code} - {e.message}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error importing folder skill: {e}")
            raise IngestionError("IMPORT_ERROR", str(e))
    
    @staticmethod
    def _store_generated_skill(user_id: str, skill: GeneratedSkill) -> Dict[str, Any]:
        """
        Store a generated skill in HuggingFace storage using existing SkillStorageService.
        
        Returns: Stored skill dictionary with ID
        """
        skill_dict = {
            "name": skill.name,
            "level": skill.level,
            "source": skill.source,
            "confidence": skill.confidence,
            # Additional fields for ingested skills
            "instructions": skill.instructions,
            "capabilities": skill.capabilities,
            "examples": skill.examples,
            "limitations": skill.limitations,
            "source_url": skill.source_url,
            "tags": skill.tags,
        }
        
        # Use existing storage service to add skill
        stored = SkillStorageService.add_skill(user_id, skill_dict)
        
        return stored
    
    @staticmethod
    def get_user_skills(user_id: str) -> Dict[str, Any]:
        """Get all skills for a user."""
        data = SkillStorageService.load_skills(user_id)
        return data
    
    @staticmethod
    def get_skill(user_id: str, skill_id: str) -> Dict[str, Any]:
        """Get a specific skill for a user."""
        return SkillStorageService.get_skill(user_id, skill_id)
    
    @staticmethod
    def enable_skill(user_id: str, skill_id: str) -> Dict[str, Any]:
        """Enable a skill for a user."""
        skill = SkillStorageService.get_skill(user_id, skill_id)
        updated = SkillStorageService.update_skill(user_id, skill_id, {"enabled": True})
        return updated
    
    @staticmethod
    def disable_skill(user_id: str, skill_id: str) -> Dict[str, Any]:
        """Disable a skill for a user."""
        skill = SkillStorageService.get_skill(user_id, skill_id)
        updated = SkillStorageService.update_skill(user_id, skill_id, {"enabled": False})
        return updated
    
    @staticmethod
    def delete_skill(user_id: str, skill_id: str) -> bool:
        """Delete a skill for a user."""
        return SkillStorageService.delete_skill(user_id, skill_id)
