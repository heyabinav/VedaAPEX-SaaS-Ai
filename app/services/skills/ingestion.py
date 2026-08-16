"""Main skill ingestion service coordinating all components."""

from __future__ import annotations

import logging
import tempfile
from typing import Optional, Tuple

from .folder import analyze_folder, cleanup_temp_folder, extract_zip_safely
from .generator import generate_skill_from_folder, generate_skill_from_repository
from .github import fetch_github_repository
from .models import GeneratedSkill, IngestionError
from .validator import validate_skill

logger = logging.getLogger("services.skills.ingestion")


class SkillIngestionService:
    """Coordinates skill ingestion from various sources."""
    
    @staticmethod
    async def ingest_github_url(
        url: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        level: Optional[str] = None,
    ) -> GeneratedSkill:
        """
        Ingest a GitHub repository as a skill.
        
        Process:
        1. Validate GitHub URL
        2. Fetch repository metadata and files
        3. Analyze repository content
        4. Generate normalized skill
        5. Validate skill
        
        Args:
            url: GitHub repository URL
            user_id: User ID owning the skill
            name: Optional custom skill name
            description: Optional custom description
            level: Optional skill level override
        
        Returns: GeneratedSkill object (not yet stored)
        Raises: IngestionError subclasses
        """
        logger.info(f"Starting GitHub ingestion: {url} for user {user_id}")
        
        try:
            # Step 1: Fetch repository
            logger.debug(f"Step 1: Fetching GitHub repository...")
            repo_metadata = fetch_github_repository(url)
            
            # Step 2: Generate skill
            logger.debug(f"Step 2: Generating skill from repository...")
            skill = generate_skill_from_repository(
                repo_metadata,
                name=name,
                description=description,
                level=level,
            )
            
            # Step 3: Validate skill
            logger.debug(f"Step 3: Validating generated skill...")
            validate_skill(skill)
            
            logger.info(f"Successfully ingested GitHub skill: {skill.name}")
            return skill
            
        except IngestionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during GitHub ingestion: {e}")
            from .models import SkillGenerationError
            raise SkillGenerationError(f"Failed to ingest GitHub repository: {str(e)}")
    
    @staticmethod
    async def ingest_folder_upload(
        zip_bytes: bytes,
        user_id: str,
        skill_name: Optional[str] = None,
        description: Optional[str] = None,
        level: Optional[str] = None,
    ) -> GeneratedSkill:
        """
        Ingest an uploaded folder/archive as a skill.
        
        Process:
        1. Extract ZIP archive safely
        2. Analyze folder content
        3. Generate normalized skill
        4. Validate skill
        5. Cleanup temp files
        
        Args:
            zip_bytes: ZIP archive bytes
            user_id: User ID owning the skill
            skill_name: Optional custom skill name
            description: Optional custom description
            level: Optional skill level override
        
        Returns: GeneratedSkill object (not yet stored)
        Raises: IngestionError subclasses
        """
        logger.info(f"Starting folder upload ingestion for user {user_id}")
        
        temp_folder = None
        try:
            # Step 1: Extract ZIP
            logger.debug(f"Step 1: Extracting ZIP archive...")
            temp_folder = extract_zip_safely(zip_bytes)
            
            # Step 2: Analyze folder
            logger.debug(f"Step 2: Analyzing folder structure...")
            folder_name = skill_name or "imported_skill"
            folder_metadata = analyze_folder(
                temp_folder,
                folder_name=folder_name,
                description=description or "",
            )
            
            # Step 3: Generate skill
            logger.debug(f"Step 3: Generating skill from folder...")
            skill = generate_skill_from_folder(
                folder_metadata,
                name=skill_name,
                description=description,
                level=level,
            )
            
            # Step 4: Validate skill
            logger.debug(f"Step 4: Validating generated skill...")
            validate_skill(skill)
            
            logger.info(f"Successfully ingested folder skill: {skill.name}")
            return skill
            
        except IngestionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during folder ingestion: {e}")
            from .models import SkillGenerationError
            raise SkillGenerationError(f"Failed to ingest folder upload: {str(e)}")
        finally:
            # Cleanup
            if temp_folder:
                cleanup_temp_folder(temp_folder)
