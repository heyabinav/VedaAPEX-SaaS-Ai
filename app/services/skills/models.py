"""Data models for skill ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RepositoryMetadata:
    """Metadata extracted from a repository."""
    name: str
    description: str
    owner: str
    url: str
    files: List[str] = field(default_factory=list)
    readme_content: Optional[str] = None
    skill_files: Dict[str, str] = field(default_factory=dict)  # filename -> content
    examples: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    language: Optional[str] = None
    total_files: int = 0
    total_size_bytes: int = 0


@dataclass
class FolderMetadata:
    """Metadata extracted from an uploaded folder."""
    name: str
    description: str
    files: List[str] = field(default_factory=list)
    readme_content: Optional[str] = None
    skill_files: Dict[str, str] = field(default_factory=dict)  # filename -> content
    examples: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    total_files: int = 0
    total_size_bytes: int = 0


@dataclass
class GeneratedSkill:
    """Normalized skill generated from analyzed content."""
    name: str
    description: str
    level: str  # beginner, intermediate, advanced, expert
    source: str  # user_requested for ingested skills
    instructions: List[str]
    capabilities: List[str]
    examples: List[str]
    limitations: List[str]
    source_url: Optional[str] = None
    confidence: float = 0.8
    tags: List[str] = field(default_factory=list)


class IngestionError(Exception):
    """Base exception for skill ingestion errors."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class InvalidGitHubURL(IngestionError):
    def __init__(self, message: str = "Invalid GitHub URL"):
        super().__init__("INVALID_GITHUB_URL", message)


class GitHubFetchError(IngestionError):
    def __init__(self, message: str = "Failed to fetch GitHub repository"):
        super().__init__("GITHUB_FETCH_ERROR", message)


class SSRFDetected(IngestionError):
    def __init__(self, message: str = "SSRF or unsafe URL detected"):
        super().__init__("SSRF_DETECTED", message)


class FolderAnalysisError(IngestionError):
    def __init__(self, message: str = "Failed to analyze folder"):
        super().__init__("FOLDER_ANALYSIS_ERROR", message)


class SkillGenerationError(IngestionError):
    def __init__(self, message: str = "Failed to generate skill"):
        super().__init__("SKILL_GENERATION_ERROR", message)


class SkillValidationError(IngestionError):
    def __init__(self, message: str = "Skill validation failed"):
        super().__init__("SKILL_VALIDATION_ERROR", message)
