"""Skill generation from analyzed content."""

from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Optional, Union

from .analyzer import SkillAnalyzer
from .models import FolderMetadata, GeneratedSkill, RepositoryMetadata

logger = logging.getLogger("services.skills.generator")


def generate_skill_from_repository(
    metadata: RepositoryMetadata,
    name: Optional[str] = None,
    description: Optional[str] = None,
    level: Optional[str] = None,
) -> GeneratedSkill:
    """Generate a normalized skill from repository metadata."""
    
    logger.info(f"Generating skill from repository: {metadata.url}")
    
    # Determine skill name
    if name:
        skill_name = name.strip()
    else:
        skill_name = SkillAnalyzer.extract_title(
            "\n".join(metadata.skill_files.values()),
            metadata.name
        )
    
    # Determine description
    if description:
        skill_description = description.strip()
    else:
        skill_description = metadata.description
        if not skill_description and metadata.skill_files:
            skill_description = SkillAnalyzer.extract_description(
                "\n".join(list(metadata.skill_files.values())[:3])
            )
    
    # Extract content for analysis
    full_content = "\n\n".join([
        metadata.description,
        "\n".join(f"### {name}\n{content}" for name, content in list(metadata.skill_files.items())[:5])
    ])
    
    # Analyze content
    capabilities = SkillAnalyzer.extract_capabilities(full_content, metadata.name)
    examples = SkillAnalyzer.extract_examples(full_content)
    limitations = SkillAnalyzer.extract_limitations(full_content)
    language = SkillAnalyzer.detect_language(metadata.files)
    
    # Determine level
    if level:
        skill_level = level.lower()
    else:
        skill_level = SkillAnalyzer.determine_skill_level(full_content, metadata.files)
    
    # Generate instructions
    instructions = SkillAnalyzer.generate_instructions(
        full_content,
        capabilities,
        examples,
        language,
        metadata.url,
    )
    
    skill = GeneratedSkill(
        name=skill_name,
        description=skill_description,
        level=skill_level,
        source="user_requested",  # Imported skills are user-requested
        instructions=instructions,
        capabilities=capabilities,
        examples=examples,
        limitations=limitations,
        source_url=metadata.url,
        confidence=0.8,
        tags=["imported", language.lower() if language else ""],
    )
    
    logger.info(f"Generated skill: {skill.name}")
    return skill


def generate_skill_from_folder(
    metadata: FolderMetadata,
    name: Optional[str] = None,
    description: Optional[str] = None,
    level: Optional[str] = None,
) -> GeneratedSkill:
    """Generate a normalized skill from folder metadata."""
    
    logger.info(f"Generating skill from folder: {metadata.name}")
    
    # Determine skill name
    if name:
        skill_name = name.strip()
    else:
        skill_name = SkillAnalyzer.extract_title(
            "\n".join(metadata.skill_files.values()),
            metadata.name
        )
    
    # Determine description
    if description:
        skill_description = description.strip()
    else:
        skill_description = metadata.description
        if not skill_description and metadata.skill_files:
            skill_description = SkillAnalyzer.extract_description(
                "\n".join(list(metadata.skill_files.values())[:3])
            )
    
    # Extract content for analysis
    full_content = "\n\n".join([
        metadata.description,
        "\n".join(f"### {name}\n{content}" for name, content in list(metadata.skill_files.items())[:5])
    ])
    
    # Analyze content
    capabilities = SkillAnalyzer.extract_capabilities(full_content, metadata.name)
    examples = SkillAnalyzer.extract_examples(full_content)
    limitations = SkillAnalyzer.extract_limitations(full_content)
    language = SkillAnalyzer.detect_language(metadata.files)
    
    # Determine level
    if level:
        skill_level = level.lower()
    else:
        skill_level = SkillAnalyzer.determine_skill_level(full_content, metadata.files)
    
    # Generate instructions
    instructions = SkillAnalyzer.generate_instructions(
        full_content,
        capabilities,
        examples,
        language,
        None,  # No source URL for folder imports
    )
    
    skill = GeneratedSkill(
        name=skill_name,
        description=skill_description,
        level=skill_level,
        source="user_requested",  # Imported skills are user-requested
        instructions=instructions,
        capabilities=capabilities,
        examples=examples,
        limitations=limitations,
        source_url=None,
        confidence=0.8,
        tags=["imported", "folder", language.lower() if language else ""],
    )
    
    logger.info(f"Generated skill: {skill.name}")
    return skill
