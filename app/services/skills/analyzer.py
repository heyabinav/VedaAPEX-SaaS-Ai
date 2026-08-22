"""Skill content analyzer for understanding repository/folder purpose."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("services.skills.analyzer")


class SkillAnalyzer:
    """Analyzes skill content to extract capabilities, examples, and patterns."""
    
    @staticmethod
    def extract_title(content: str, filename: str = "") -> str:
        """Extract title from markdown or text content."""
        lines = content.split("\n")
        
        # Try to find H1 markdown heading
        for line in lines:
            if line.strip().startswith("# "):
                title = line.strip()[2:].strip()
                if title:
                    return title
        
        # Try filename
        if filename:
            name = filename.replace(".md", "").replace("_", " ").replace("-", " ").strip()
            if name:
                return name.title()
        
        # Use first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()[:100]
        
        return "Untitled Skill"
    
    @staticmethod
    def extract_description(content: str) -> str:
        """Extract description from markdown content."""
        lines = content.split("\n")
        description_lines = []
        in_header = True
        
        for line in lines:
            line = line.strip()
            
            # Skip initial headers
            if in_header and (line.startswith("#") or not line):
                if line:
                    in_header = False
                continue
            
            if line and not line.startswith(">") and not line.startswith("```"):
                description_lines.append(line)
                
                # Get first 2-3 sentences
                if len(description_lines) >= 3:
                    break
        
        description = " ".join(description_lines)
        
        # Clean up
        description = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", description)  # Remove markdown links
        description = description.replace("\\", "").strip()
        
        if len(description) > 500:
            description = description[:500].rsplit(" ", 1)[0] + "..."
        
        return description or "No description available"
    
    @staticmethod
    def extract_code_blocks(content: str, language: Optional[str] = None) -> List[str]:
        """Extract code blocks from markdown."""
        # Match ```language blocks
        if language:
            pattern = rf"```{re.escape(language)}\n(.*?)\n```"
        else:
            pattern = r"```\n(.*?)\n```"
        
        matches = re.findall(pattern, content, re.DOTALL)
        return [m.strip() for m in matches if m.strip()]
    
    @staticmethod
    def extract_capabilities(content: str, repo_name: str = "") -> List[str]:
        """Extract capabilities/features from content."""
        capabilities: List[str] = []

        def add_capability(value: str) -> None:
            cleaned = " ".join(value.split()).strip()
            if cleaned and cleaned not in capabilities:
                capabilities.append(cleaned)

        lines = content.splitlines()
        in_section = False
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            if re.match(r"^#+\s*(capabilities|features|functionality|what it does|how it works)\b", line, re.IGNORECASE):
                in_section = True
                continue

            if in_section:
                if re.match(r"^#+\s+", line):
                    break
                bullet = re.match(r"^[-*]\s+(.+)$", line)
                if bullet:
                    add_capability(bullet.group(1))
                elif not line.startswith(">"):
                    add_capability(line)

        if not capabilities:
            bullets = re.findall(r"^\s*[-*]\s+([^\n]+)", content, flags=re.MULTILINE)
            for bullet in bullets:
                add_capability(bullet)
        
        # Detect common capabilities from repo name
        repo_lower = repo_name.lower()
        
        if "auth" in repo_lower or "login" in repo_lower:
            capabilities.append("Authentication and user management")
        if "api" in repo_lower:
            capabilities.append("API integration and management")
        if "database" in repo_lower or "db" in repo_lower:
            capabilities.append("Database operations")
        if "test" in repo_lower or "testing" in repo_lower:
            capabilities.append("Testing and quality assurance")
        if "deploy" in repo_lower:
            capabilities.append("Deployment and DevOps")
        if "ml" in repo_lower or "machine" in repo_lower or "ai" in repo_lower:
            capabilities.append("Machine learning and AI")
        if "web" in repo_lower or "frontend" in repo_lower:
            add_capability("Web development and UI")
        if "data" in repo_lower:
            add_capability("Data processing and analysis")
        
        return capabilities[:10]  # Limit to 10
    
    @staticmethod
    def extract_examples(content: str) -> List[str]:
        """Extract examples and usage patterns from content."""
        examples = []
        
        # Look for examples section
        sections = re.split(r"\n#+\s*(examples|usage|tutorial|getting started|quick start)\s*\n", content, flags=re.IGNORECASE)
        
        if len(sections) > 1:
            examples_text = sections[-1]
            
            # Extract code blocks
            code_blocks = SkillAnalyzer.extract_code_blocks(examples_text)
            examples.extend(code_blocks[:3])
            
            # Extract text examples
            bullets = re.findall(r"[-*]\s+([^\n]+)", examples_text)
            for bullet in bullets[:3]:
                if bullet.strip() and len(bullet) < 200:
                    examples.append(bullet.strip())
        
        return examples[:5]  # Limit to 5
    
    @staticmethod
    def extract_limitations(content: str) -> List[str]:
        """Extract limitations from content."""
        limitations = []
        
        # Look for limitations/constraints/notes sections
        sections = re.split(r"\n#+\s*(limitations|constraints|notes|caveats|known issues)\s*\n", content, flags=re.IGNORECASE)
        
        if len(sections) > 1:
            limits_text = sections[-1]
            
            # Extract bullet points
            bullets = re.findall(r"[-*]\s+([^\n]+)", limits_text)
            limitations.extend([b.strip() for b in bullets if b.strip()])
        
        return limitations[:5]  # Limit to 5
    
    @staticmethod
    def detect_language(files: List[str]) -> Optional[str]:
        """Detect primary programming language from files."""
        language_score: Dict[str, int] = {}
        
        extensions_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".sh": "Bash",
            ".sql": "SQL",
        }
        
        for file_path in files:
            for ext, lang in extensions_map.items():
                if file_path.lower().endswith(ext):
                    language_score[lang] = language_score.get(lang, 0) + 1
        
        if language_score:
            return max(language_score, key=language_score.get)
        
        return None
    
    @staticmethod
    def determine_skill_level(content: str, files: List[str]) -> str:
        """Determine appropriate skill level based on content complexity."""
        content_lower = content.lower()
        files_lower = [f.lower() for f in files]
        
        # Count indicators of complexity
        advanced_indicators = [
            "advanced",
            "architecture",
            "optimization",
            "performance",
            "algorithm",
            "design pattern",
            "scalability",
            "microservices",
            "distributed",
            "concurrent",
        ]
        
        intermediate_indicators = [
            "tutorial",
            "guide",
            "integration",
            "configuration",
            "best practices",
            "deployment",
            "testing",
            "example",
        ]
        
        beginner_indicators = [
            "quick start",
            "getting started",
            "introduction",
            "hello world",
            "basic",
            "simple",
            "beginner",
        ]
        
        advanced_count = sum(1 for ind in advanced_indicators if ind in content_lower)
        intermediate_count = sum(1 for ind in intermediate_indicators if ind in content_lower)
        beginner_count = sum(1 for ind in beginner_indicators if ind in content_lower)
        
        # Check file count and complexity
        total_files = len(files)
        if total_files > 50:
            advanced_count += 2
        elif total_files > 20:
            intermediate_count += 1
        
        # Decide level
        if advanced_count > intermediate_count and advanced_count > beginner_count:
            return "advanced"
        elif intermediate_count > beginner_count:
            return "intermediate"
        else:
            return "beginner"
    
    @staticmethod
    def generate_instructions(
        content: str,
        capabilities: List[str],
        examples: List[str],
        language: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> List[str]:
        """Generate comprehensive skill instructions from analyzed content."""
        instructions = []
        
        # Base instruction
        instructions.append(f"This is a {language or 'technical'} skill imported from {source_url or 'a repository'}.")
        
        # Capabilities
        if capabilities:
            instructions.append(f"Main capabilities: {', '.join(capabilities[:5])}")
        
        # Usage pattern
        if examples:
            instructions.append(f"Typical usage: Follow the examples and patterns shown in the skill documentation.")
        
        # General guidance
        instructions.append("When users ask about this skill, provide clear explanations and practical examples.")
        instructions.append("Refer to the skill documentation and examples for accurate information.")
        
        # Limitations acknowledgement
        instructions.append("Be transparent about any known limitations or constraints of this skill.")
        
        return instructions[:10]  # Limit to 10 instructions
