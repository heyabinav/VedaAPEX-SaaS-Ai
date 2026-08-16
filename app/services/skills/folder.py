"""Folder upload handling for skill ingestion."""

from __future__ import annotations

import io
import logging
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

from .models import FolderAnalysisError, FolderMetadata

logger = logging.getLogger("services.skills.folder")

# File size limits
MAX_FILE_SIZE = 1024 * 1024  # 1MB per file
MAX_TOTAL_SIZE = 10 * 1024 * 1024  # 10MB total
MAX_FILES = 100

# Max archive size before extraction
MAX_ARCHIVE_SIZE = 50 * 1024 * 1024  # 50MB

# Files to prioritize
PRIORITY_FILES = {
    "readme.md",
    "readme.txt",
    "skill.md",
    "skill.txt",
    "doc.md",
    "docs/readme.md",
    "docs/skill.md",
    "index.md",
    "example.md",
    "examples/readme.md",
    "usage.md",
    "guide.md",
}

# Files to ignore
IGNORE_PATTERNS = {
    ".git",
    ".gitignore",
    ".github",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".egg-info",
    ".lock",
    ".sum",
    "*.pyc",
    "*.pyo",
    "*.class",
    "*.o",
    ".DS_Store",
    "Thumbs.db",
}

# Safe file extensions
SAFE_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".html", ".css", ".java", ".cpp", ".c", ".go", ".rs", ".rb",
    ".php", ".sh", ".bash", ".sql", ".xml", ".csv",
}


def is_ignored_file(path: str) -> bool:
    """Check if file should be ignored."""
    path_lower = path.lower()
    
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("."):
            if f"/{pattern}/" in path_lower or path_lower.startswith(pattern + "/"):
                return True
        elif "*" in pattern:
            ext = pattern.replace("*", "")
            if path_lower.endswith(ext):
                return True
        else:
            if pattern in path_lower:
                return True
    
    return False


def is_safe_file_extension(path: str) -> bool:
    """Check if file has a safe extension."""
    if not Path(path).suffix:
        return True  # Files without extension (e.g., LICENSE)
    
    return Path(path).suffix.lower() in SAFE_EXTENSIONS


def is_safe_path(path: str, base_path: str) -> bool:
    """
    Verify path doesn't escape base directory (path traversal protection).
    """
    try:
        abs_path = Path(base_path) / path
        abs_base = Path(base_path).resolve()
        abs_resolved = abs_path.resolve()
        
        # Ensure resolved path is within base
        if not str(abs_resolved).startswith(str(abs_base)):
            logger.warning(f"Path traversal attempt detected: {path}")
            return False
        
        return True
    except Exception as e:
        logger.warning(f"Path safety check failed for {path}: {e}")
        return False


def extract_zip_safely(zip_bytes: bytes, max_size: int = MAX_ARCHIVE_SIZE) -> bytes:
    """
    Extract ZIP archive safely.
    
    Returns: Dictionary of extracted file paths and contents
    Raises: FolderAnalysisError
    """
    if len(zip_bytes) > max_size:
        raise FolderAnalysisError(f"Archive exceeds maximum size of {max_size} bytes")
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # Check for zip bombs
                total_size = 0
                for info in zf.infolist():
                    total_size += info.file_size
                    if total_size > MAX_TOTAL_SIZE:
                        raise FolderAnalysisError("Extracted archive exceeds maximum total size")
                
                # Extract with path traversal protection
                for info in zf.infolist():
                    if not is_safe_path(info.filename, temp_dir):
                        raise FolderAnalysisError(f"Unsafe path in archive: {info.filename}")
                    
                    zf.extract(info, temp_dir)
            
            return temp_dir
    except zipfile.BadZipFile as e:
        raise FolderAnalysisError(f"Invalid ZIP archive: {e}")
    except Exception as e:
        logger.error(f"Error extracting ZIP: {e}")
        raise FolderAnalysisError(f"Failed to extract archive: {e}")


def analyze_folder(folder_path: str, folder_name: str = "imported_skill", description: str = "") -> FolderMetadata:
    """
    Analyze a folder and extract skill-relevant files.
    
    Args:
        folder_path: Path to extracted folder
        folder_name: Name for the skill
        description: Optional description
    
    Raises: FolderAnalysisError
    """
    logger.info(f"Analyzing folder: {folder_path}")
    
    if not os.path.isdir(folder_path):
        raise FolderAnalysisError(f"Path is not a directory: {folder_path}")
    
    try:
        files: List[str] = []
        skill_files: Dict[str, str] = {}
        total_size = 0
        
        # Walk directory and collect files
        for root, dirs, filenames in os.walk(folder_path):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if not is_ignored_file(d)]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, folder_path)
                
                if is_ignored_file(rel_path):
                    continue
                
                if not is_safe_file_extension(rel_path):
                    logger.debug(f"Skipping unsafe file type: {rel_path}")
                    continue
                
                try:
                    file_size = os.path.getsize(file_path)
                    
                    if file_size > MAX_FILE_SIZE:
                        logger.warning(f"Skipping large file: {rel_path} ({file_size} bytes)")
                        continue
                    
                    total_size += file_size
                    if total_size > MAX_TOTAL_SIZE:
                        logger.warning(f"Folder analysis exceeds max size limit")
                        break
                    
                    files.append(rel_path)
                    
                    # Extract priority files
                    if any(rel_path.lower().endswith(priority) for priority in PRIORITY_FILES):
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                if len(content) <= MAX_FILE_SIZE:
                                    skill_files[rel_path] = content
                                    logger.debug(f"Extracted skill file: {rel_path}")
                        except Exception as e:
                            logger.warning(f"Failed to read {rel_path}: {e}")
                    
                    if len(files) >= MAX_FILES:
                        logger.warning(f"Folder has too many files, stopping at {MAX_FILES}")
                        break
                
                except Exception as e:
                    logger.warning(f"Error processing file {rel_path}: {e}")
        
        metadata = FolderMetadata(
            name=folder_name,
            description=description or f"Skill imported from folder: {folder_name}",
            files=files[:50],  # Limit to first 50 for metadata
            skill_files=skill_files,
            total_files=len(files),
            total_size_bytes=total_size,
        )
        
        logger.info(f"Successfully analyzed folder: found {len(files)} files")
        return metadata
        
    except Exception as e:
        logger.error(f"Error analyzing folder: {e}")
        raise FolderAnalysisError(f"Failed to analyze folder: {e}")


def cleanup_temp_folder(folder_path: str) -> None:
    """Safely cleanup temporary folder."""
    try:
        if os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
            logger.debug(f"Cleaned up temporary folder: {folder_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temporary folder {folder_path}: {e}")
