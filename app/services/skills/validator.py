"""Validation logic for skill ingestion."""

from __future__ import annotations

import re
from typing import List

from .models import (
    GeneratedSkill,
    InvalidGitHubURL,
    SkillValidationError,
    SSRFDetected,
)


def validate_github_url(url: str) -> tuple[str, str]:
    """
    Validate and parse a GitHub URL.
    
    Returns: (owner, repo)
    Raises: InvalidGitHubURL, SSRFDetected
    """
    if not url:
        raise InvalidGitHubURL("URL cannot be empty")
    
    url = url.strip()
    
    # Reject SSRF attempts
    if any(x in url.lower() for x in ["localhost", "127.0.0.1", "192.168", "10.0", "172.16", "file://", "ftp://", "gopher://", "ldap://", "dict://", "sftp://"]):
        raise SSRFDetected(f"Unsafe URL: {url}")
    
    # Parse GitHub URL
    # Accept forms:
    # - https://github.com/owner/repo
    # - https://github.com/owner/repo/
    # - https://github.com/owner/repo.git
    # - git@github.com:owner/repo.git
    
    pattern = r"https://github\.com/([a-zA-Z0-9\-_.]+)/([a-zA-Z0-9\-_.]+?)(?:\.git|/)?$"
    match = re.match(pattern, url)
    
    if not match:
        # Try git SSH format
        ssh_pattern = r"git@github\.com:([a-zA-Z0-9\-_.]+)/([a-zA-Z0-9\-_.]+?)(?:\.git)?$"
        match = re.match(ssh_pattern, url)
        
        if not match:
            raise InvalidGitHubURL(f"URL must be a valid GitHub repository URL: {url}")
    
    owner, repo = match.groups()
    
    # Validate owner and repo names
    if not owner or not repo:
        raise InvalidGitHubURL("Owner and repository names must not be empty")
    
    if len(owner) > 39 or len(repo) > 100:  # GitHub username max 39 chars, repo max 100 chars
        raise InvalidGitHubURL("Owner or repository name exceeds maximum length")
    
    return owner, repo


def validate_skill(skill: GeneratedSkill) -> None:
    """
    Validate a generated skill before storage.
    
    Raises: SkillValidationError
    """
    errors: List[str] = []
    
    # Validate name
    if not skill.name or not skill.name.strip():
        errors.append("Skill name is required")
    elif len(skill.name) < 2:
        errors.append("Skill name must be at least 2 characters")
    elif len(skill.name) > 100:
        errors.append("Skill name must be at most 100 characters")
    elif not re.match(r"^[a-zA-Z0-9\s\-_.]+$", skill.name):
        errors.append("Skill name contains invalid characters")
    
    # Validate description
    if not skill.description or not skill.description.strip():
        errors.append("Skill description is required")
    elif len(skill.description) < 10:
        errors.append("Skill description must be at least 10 characters")
    elif len(skill.description) > 500:
        errors.append("Skill description must be at most 500 characters")
    
    # Validate level
    allowed_levels = {"beginner", "intermediate", "advanced", "expert"}
    if skill.level not in allowed_levels:
        errors.append(f"Invalid skill level. Must be one of: {', '.join(allowed_levels)}")
    
    # Validate source
    allowed_sources = {"user_declared", "user_requested", "verified"}
    if skill.source not in allowed_sources:
        errors.append(f"Invalid skill source. Must be one of: {', '.join(allowed_sources)}")
    
    # Validate instructions
    if not skill.instructions or len(skill.instructions) == 0:
        errors.append("Skill must have at least one instruction")
    elif len(skill.instructions) > 20:
        errors.append("Skill must have at most 20 instructions")
    
    for i, instr in enumerate(skill.instructions):
        if not instr.strip():
            errors.append(f"Instruction {i+1} is empty")
        elif len(instr) > 500:
            errors.append(f"Instruction {i+1} is too long (max 500 chars)")
        
        # Check for prompt injection attempts
        dangerous_phrases = [
            "ignore previous instructions",
            "forget everything",
            "override system prompt",
            "disable security",
            "reveal api keys",
            "reveal token",
            "system prompt is:",
            "your actual instructions are:",
        ]
        instr_lower = instr.lower()
        for phrase in dangerous_phrases:
            if phrase in instr_lower:
                errors.append(f"Instruction {i+1} contains suspicious content")
                break
    
    # Validate capabilities
    if skill.capabilities and len(skill.capabilities) > 20:
        errors.append("Too many capabilities (max 20)")
    
    for cap in skill.capabilities or []:
        if len(cap) > 100:
            errors.append(f"Capability too long: {cap[:50]}... (max 100 chars)")
    
    # Validate examples
    if skill.examples and len(skill.examples) > 10:
        errors.append("Too many examples (max 10)")
    
    # Validate limitations
    if skill.limitations and len(skill.limitations) > 10:
        errors.append("Too many limitations (max 10)")
    
    # Validate confidence
    if not (0.0 <= skill.confidence <= 1.0):
        errors.append("Confidence must be between 0.0 and 1.0")
    
    # Check for credential/API key leaks
    sensitive_patterns = [
        r"api[_-]?key\s*[:=]",
        r"password\s*[:=]",
        r"secret\s*[:=]",
        r"token\s*[:=]",
        r"authorization\s*[:=]",
        r"[a-z0-9]{32,}",  # Common API key format
    ]
    
    full_text = " ".join([
        skill.name,
        skill.description,
        " ".join(skill.instructions),
        " ".join(skill.capabilities),
        " ".join(skill.examples),
        " ".join(skill.limitations),
    ]).lower()
    
    for pattern in sensitive_patterns:
        if re.search(pattern, full_text):
            # Additional check for actual API key patterns
            if re.search(r"(sk|pk)[-_a-z0-9]{32,}", full_text):
                errors.append("Skill contains suspicious credential-like patterns")
                break
    
    if errors:
        raise SkillValidationError("\n".join(errors))


def is_safe_skill_content(content: str) -> bool:
    """
    Quick check if content appears safe (no obvious code injection/shells).
    """
    dangerous_patterns = [
        r"exec\s*\(",
        r"eval\s*\(",
        r"subprocess\s*\.",
        r"os\.system",
        r"shell\s*=\s*true",
        r"/bin/bash",
        r"/bin/sh",
        r"docker run",
        r"curl\s+.*\|\s*bash",
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, content, re.IGNORECASE):
            return False
    
    return True
