"""GitHub repository handling for skill ingestion."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .models import GitHubFetchError, RepositoryMetadata
from .validator import validate_github_url

logger = logging.getLogger("services.skills.github")

# GitHub API configuration
GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# File size limits
MAX_FILE_SIZE = 1024 * 1024  # 1MB per file
MAX_TOTAL_SIZE = 10 * 1024 * 1024  # 10MB total
MAX_FILES = 100

# Files to prioritize
PRIORITY_FILES = {
    "readme.md",
    "readme.txt",
    "skill.md",
    "skill.txt",
    "doc.md",
    "docs/readme.md",
    "docs/skill.md",
    "docs/index.md",
    ".github/skill.md",
    "example.md",
    "examples/readme.md",
    "usage.md",
    "guide.md",
    "tutorial.md",
}

# Files to ignore
IGNORE_PATTERNS = {
    ".git",
    ".gitignore",
    ".github/workflows",
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


def fetch_github_repository(url: str) -> RepositoryMetadata:
    """
    Fetch GitHub repository metadata and key files.
    
    Validates URL, fetches repository info, and extracts relevant files.
    
    Raises: GitHubFetchError, InvalidGitHubURL, SSRFDetected
    """
    owner, repo = validate_github_url(url)
    
    logger.info(f"Fetching GitHub repository: {owner}/{repo}")
    
    try:
        import requests
    except ImportError:
        raise GitHubFetchError("requests library not available")
    
    try:
        # Fetch repository metadata via GitHub API
        repo_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": "VedaApex-SkillImport"}
        
        logger.debug(f"Fetching repo metadata from {repo_url}")
        resp = requests.get(repo_url, headers=headers, timeout=10)
        resp.raise_for_status()
        repo_data = resp.json()
        
        repo_name = repo_data.get("name", repo)
        repo_desc = repo_data.get("description", "")
        
        # Fetch directory contents
        logger.debug(f"Fetching directory tree for {owner}/{repo}")
        tree_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/main?recursive=1"
        
        resp = requests.get(tree_url, headers=headers, timeout=10)
        if resp.status_code == 404:
            # Try master branch
            tree_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/master?recursive=1"
            resp = requests.get(tree_url, headers=headers, timeout=10)
        
        resp.raise_for_status()
        tree_data = resp.json()
        
        files: List[str] = []
        total_size = 0
        
        if "tree" in tree_data:
            for item in tree_data["tree"]:
                if item["type"] == "blob":
                    path = item["path"]
                    size = item.get("size", 0)
                    
                    if is_ignored_file(path):
                        continue
                    
                    if size > MAX_FILE_SIZE:
                        logger.warning(f"Skipping large file: {path} ({size} bytes)")
                        continue
                    
                    total_size += size
                    if total_size > MAX_TOTAL_SIZE:
                        logger.warning(f"Repository exceeds max size limit")
                        break
                    
                    files.append(path)
                    
                    if len(files) >= MAX_FILES:
                        logger.warning(f"Repository has too many files, stopping at {MAX_FILES}")
                        break
        
        logger.info(f"Found {len(files)} relevant files in {owner}/{repo}")
        
        # Fetch priority files
        skill_files: Dict[str, str] = {}
        
        for file_path in files:
            path_lower = file_path.lower()
            
            # Prioritize common skill documentation files
            if any(path_lower.endswith(priority) for priority in PRIORITY_FILES):
                try:
                    raw_url = f"{GITHUB_RAW_BASE}/{owner}/{repo}/main/{file_path}"
                    
                    resp = requests.get(raw_url, headers=headers, timeout=10)
                    if resp.status_code == 404:
                        # Try master
                        raw_url = f"{GITHUB_RAW_BASE}/{owner}/{repo}/master/{file_path}"
                        resp = requests.get(raw_url, headers=headers, timeout=10)
                    
                    resp.raise_for_status()
                    content = resp.text
                    
                    if len(content) <= MAX_FILE_SIZE:
                        skill_files[file_path] = content
                        logger.debug(f"Fetched skill file: {file_path}")
                
                except Exception as e:
                    logger.warning(f"Failed to fetch {file_path}: {e}")
        
        metadata = RepositoryMetadata(
            name=repo_name,
            description=repo_desc or f"GitHub repository: {owner}/{repo}",
            owner=owner,
            url=f"https://github.com/{owner}/{repo}",
            files=files[:50],  # Limit to first 50 for metadata
            skill_files=skill_files,
            total_files=len(files),
            total_size_bytes=total_size,
        )
        
        logger.info(f"Successfully fetched repository metadata for {owner}/{repo}")
        return metadata
        
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API error: {e}")
        raise GitHubFetchError(f"Failed to fetch GitHub repository: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching GitHub repo: {e}")
        raise GitHubFetchError(f"Unexpected error: {str(e)}")
