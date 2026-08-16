"""Search Decision Engine - Intelligently determines when web search is needed.

Analyzes user intent to avoid wasting API credits on unnecessary searches.
Uses keyword matching, patterns, and reasoning to classify search necessity.
"""

import logging
import re
from enum import Enum
from typing import Literal

logger = logging.getLogger("services.search_decision_engine")


class SearchRequestType(str, Enum):
    """Classification of user requests."""
    
    # No search needed
    GENERAL = "general"  # Stable/general knowledge
    REASONING = "reasoning"  # Can be reasoned without current data
    CREATIVE = "creative"  # Creative writing/generation
    CODING = "coding"  # Code generation/explanation (unless latest)
    TRANSLATION = "translation"  # Translation tasks
    WRITING = "writing"  # Writing/editing tasks
    EXPLANATION = "explanation"  # General explanations
    
    # Search required
    CURRENT = "current"  # Explicitly about current/now/today
    LATEST = "latest"  # Latest version/release/news
    NEWS = "news"  # News/events/announcements
    PRICE = "price"  # Current pricing/availability
    RESEARCH = "research"  # Deep research needed
    FACT_CHECK = "fact_check"  # Verify truth/accuracy
    COMPARISON = "comparison"  # Compare current options
    LOCAL = "local"  # Location-based info
    PRODUCT = "product"  # Current product info
    EXPLICIT = "explicit"  # User explicitly asks for search
    

class SearchDecisionEngine:
    """Intelligent search decision classifier."""
    
    # Keywords that explicitly indicate web search is needed
    EXPLICIT_SEARCH_KEYWORDS = {
        "search the web", "search online", "google", "look up",
        "find online", "browse", "what's online", "search for",
        "web search", "online search", "current", "latest",
        "today", "now", "this week", "this month", "breaking",
        "news", "recent", "newest", "updated", "live"
    }
    
    # Keywords indicating current/live information is needed
    CURRENT_KEYWORDS = {
        "current", "today", "now", "right now", "this week",
        "this month", "this year", "2026", "live", "breaking",
        "latest", "newest", "recent", "recently", "just",
        "currently", "at this moment", "as of", "up to date",
        "latest version", "latest release"
    }
    
    # Keywords indicating latest/version-specific info is needed
    LATEST_KEYWORDS = {
        "latest", "newest", "recent", "latest version",
        "latest release", "what's new", "new features",
        "new release", "upgrade", "breaking changes",
        "version", "update", "patch", "release notes"
    }
    
    # Keywords indicating news/events
    NEWS_KEYWORDS = {
        "news", "happened", "announcement", "announced",
        "broke", "breaking", "event", "events", "happening",
        "update", "reported", "said", "according", "sources",
        "media", "press", "statement", "official"
    }
    
    # Keywords indicating price/availability info
    PRICE_KEYWORDS = {
        "price", "cost", "expensive", "cheap", "afford",
        "budget", "pricing", "subscription", "free",
        "tier", "plan", "available", "availability",
        "in stock", "out of stock", "how much", "payment"
    }
    
    # Keywords indicating comparison/evaluation
    COMPARISON_KEYWORDS = {
        "vs", "versus", "compare", "better", "best",
        "difference", "which is", "pros and cons",
        "advantage", "disadvantage", "faster", "slower",
        "more", "less", "between"
    }
    
    # Keywords indicating local/location info
    LOCAL_KEYWORDS = {
        "near me", "nearby", "location", "address",
        "hours", "opening", "restaurant", "store",
        "business", "local", "city", "state", "country"
    }
    
    # Keywords that suggest stable/general knowledge
    STABLE_KEYWORDS = {
        "what is", "explain", "how does", "what are",
        "define", "meaning", "concept", "theory",
        "fundamental", "basic", "introduction", "overview"
    }
    
    # Keywords for reasoning/calculation
    REASONING_KEYWORDS = {
        "calculate", "compute", "solve", "math",
        "2 + 2", "square root", "logic", "reason",
        "think about", "analyze", "interpret"
    }
    
    # Keywords for creative tasks
    CREATIVE_KEYWORDS = {
        "write", "create", "generate", "compose",
        "brainstorm", "idea", "story", "poem",
        "article", "essay", "script", "design"
    }
    
    # Keywords for coding tasks
    CODING_KEYWORDS = {
        "code", "program", "function", "function",
        "variable", "class", "method", "syntax",
        "debug", "error", "fix", "implement"
    }
    
    # Patterns that need web search
    REQUIRES_SEARCH_PATTERNS = [
        r"what[\'s\s]+.*latest",
        r"latest.*version",
        r"current.*price",
        r"today[\'s\s]+",
        r"this week[\'s\s]+",
        r"breaking news",
        r"search.*web",
        r"search.*online",
        r"look.*up.*online",
        r"\bwhat[\'s\s]+new\b",
        r"news.*about",
        r"recent.*release",
        r"\bhappened\b.*today",
        r"find.*online",
    ]
    
    # Patterns that DON'T need web search
    NO_SEARCH_PATTERNS = [
        r"^write\s+a\s+",
        r"^create\s+a\s+",
        r"^generate\s+",
        r"^explain\s+",
        r"^what is\s+",
        r"^how\s+do\s+you\s+",
        r"^translate\s+",
        r"^calculate\s+",
        r"^\d+\s*\+\s*\d+",
    ]
    
    @staticmethod
    def classify_request(user_message: str) -> SearchRequestType:
        """
        Classify the user's request to determine if web search is needed.
        
        Args:
            user_message: The user's query/message
            
        Returns:
            SearchRequestType enum indicating the classification
        """
        if not user_message:
            return SearchRequestType.GENERAL
        
        message_lower = user_message.lower().strip()
        
        # Check explicit search requests first (highest priority)
        if SearchDecisionEngine._check_explicit_search(message_lower):
            return SearchRequestType.EXPLICIT
        
        # Check requires-search patterns
        for pattern in SearchDecisionEngine.REQUIRES_SEARCH_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return SearchDecisionEngine._classify_search_type(message_lower)
        
        # Check no-search patterns
        for pattern in SearchDecisionEngine.NO_SEARCH_PATTERNS:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return SearchDecisionEngine._classify_no_search_type(message_lower)
        
        # Check keyword-based classification
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.CURRENT_KEYWORDS):
            return SearchRequestType.CURRENT
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.LATEST_KEYWORDS):
            return SearchRequestType.LATEST
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.NEWS_KEYWORDS):
            return SearchRequestType.NEWS
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.PRICE_KEYWORDS):
            return SearchRequestType.PRICE
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.COMPARISON_KEYWORDS):
            return SearchRequestType.COMPARISON
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.LOCAL_KEYWORDS):
            return SearchRequestType.LOCAL
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.CREATIVE_KEYWORDS):
            return SearchRequestType.CREATIVE
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.CODING_KEYWORDS):
            return SearchRequestType.CODING
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.REASONING_KEYWORDS):
            return SearchRequestType.REASONING
        
        if SearchDecisionEngine._has_keywords(message_lower, SearchDecisionEngine.TRANSLATION_KEYWORDS):
            return SearchRequestType.TRANSLATION
        
        # Check for fact-checking language
        if SearchDecisionEngine._check_fact_check(message_lower):
            return SearchRequestType.FACT_CHECK
        
        # Default to general knowledge
        return SearchRequestType.GENERAL
    
    @staticmethod
    def should_search(user_message: str) -> bool:
        """
        Determine if web search should be performed.
        
        Args:
            user_message: The user's query/message
            
        Returns:
            True if web search is needed, False otherwise
        """
        request_type = SearchDecisionEngine.classify_request(user_message)
        
        # Types that require search
        requires_search = {
            SearchRequestType.CURRENT,
            SearchRequestType.LATEST,
            SearchRequestType.NEWS,
            SearchRequestType.PRICE,
            SearchRequestType.RESEARCH,
            SearchRequestType.FACT_CHECK,
            SearchRequestType.COMPARISON,
            SearchRequestType.LOCAL,
            SearchRequestType.PRODUCT,
            SearchRequestType.EXPLICIT,
        }
        
        return request_type in requires_search
    
    @staticmethod
    def _check_explicit_search(message: str) -> bool:
        """Check if user explicitly asked for web search."""
        for keyword in SearchDecisionEngine.EXPLICIT_SEARCH_KEYWORDS:
            if keyword in message:
                return True
        return False
    
    @staticmethod
    def _check_fact_check(message: str) -> bool:
        """Check for fact-checking intent."""
        patterns = [
            r"is\s+this\s+true",
            r"fact\s+check",
            r"is\s+this\s+real",
            r"did\s+.*\s+happen",
            r"verify\s+",
            r"confirm\s+",
        ]
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False
    
    @staticmethod
    def _classify_search_type(message: str) -> SearchRequestType:
        """Classify which type of search is needed."""
        if SearchDecisionEngine._has_keywords(message, SearchDecisionEngine.NEWS_KEYWORDS):
            return SearchRequestType.NEWS
        if SearchDecisionEngine._has_keywords(message, SearchDecisionEngine.LATEST_KEYWORDS):
            return SearchRequestType.LATEST
        if SearchDecisionEngine._has_keywords(message, SearchDecisionEngine.PRICE_KEYWORDS):
            return SearchRequestType.PRICE
        return SearchRequestType.RESEARCH
    
    @staticmethod
    def _classify_no_search_type(message: str) -> SearchRequestType:
        """Classify tasks that don't need search."""
        if SearchDecisionEngine._has_keywords(message, SearchDecisionEngine.CREATIVE_KEYWORDS):
            return SearchRequestType.CREATIVE
        if SearchDecisionEngine._has_keywords(message, SearchDecisionEngine.CODING_KEYWORDS):
            return SearchRequestType.CODING
        if SearchDecisionEngine._has_keywords(message, SearchDecisionEngine.REASONING_KEYWORDS):
            return SearchRequestType.REASONING
        return SearchRequestType.GENERAL
    
    @staticmethod
    def _has_keywords(message: str, keywords: set) -> bool:
        """Check if message contains any of the keywords."""
        for keyword in keywords:
            if keyword in message:
                return True
        return False
    
    # Translation keywords
    TRANSLATION_KEYWORDS = {
        "translate", "translation", "convert to",
        "language", "spanish", "french", "german",
        "chinese", "japanese", "hindi", "meaning"
    }
    
    @staticmethod
    def get_search_reason(user_message: str) -> str:
        """Get a human-readable reason for searching (or not searching)."""
        request_type = SearchDecisionEngine.classify_request(user_message)
        
        reasons = {
            SearchRequestType.CURRENT: "Current/live information requested",
            SearchRequestType.LATEST: "Latest version/release information needed",
            SearchRequestType.NEWS: "News/events/announcements requested",
            SearchRequestType.PRICE: "Current pricing/availability needed",
            SearchRequestType.RESEARCH: "In-depth research requested",
            SearchRequestType.FACT_CHECK: "Fact verification requested",
            SearchRequestType.COMPARISON: "Current comparison needed",
            SearchRequestType.LOCAL: "Location-specific information needed",
            SearchRequestType.PRODUCT: "Current product information needed",
            SearchRequestType.EXPLICIT: "User explicitly requested web search",
            SearchRequestType.GENERAL: "Stable general knowledge - no search needed",
            SearchRequestType.REASONING: "Question answerable via reasoning - no search needed",
            SearchRequestType.CREATIVE: "Creative task - no search needed",
            SearchRequestType.CODING: "Code generation - no search needed (unless latest)",
            SearchRequestType.TRANSLATION: "Translation task - no search needed",
            SearchRequestType.WRITING: "Writing task - no search needed",
            SearchRequestType.EXPLANATION: "General explanation - no search needed",
        }
        
        return reasons.get(request_type, "Decision unclear")
