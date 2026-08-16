"""Intent detection for media searches - determines what type of search (image/video/space)."""

from typing import Literal
import re

# Keywords for each intent
IMAGE_KEYWORDS = {
    "image", "images", "photo", "photos", "picture", "pictures", "wallpaper", 
    "wallpapers", "diagram", "diagrams", "illustration", "illustrations",
    "graphic", "graphics", "screenshot", "screenshots", "poster", "posters",
    "painting", "paintings", "artwork", "painting", "drawing", "drawings",
    "render", "renders", "icon", "icons", "avatar", "avatars", "meme", "memes",
    "thumbnail", "thumbnails", "visual", "visuals", "design", "designs"
}

VIDEO_KEYWORDS = {
    "video", "videos", "watch", "clip", "clips", "tutorial", "tutorials",
    "youtube", "vimeo", "streaming", "stream", "broadcast", "live",
    "film", "films", "movie", "movies", "episode", "episodes",
    "how to", "playback", "recording", "footage", "reel", "reels"
}

SPACE_KEYWORDS = {
    "nasa", "space", "mars", "moon", "jupiter", "saturn", "venus", "mercury",
    "galaxy", "galaxies", "nebula", "nebulae", "astronaut", "astronauts",
    "solar system", "telescope", "hubble", "space station", "iss",
    "rover", "planet", "planets", "star", "stars", "constellation",
    "asteroid", "asteroids", "comet", "comets", "spacecraft", "rocket",
    "satellite", "satellites", "earth orbit", "exoplanet", "exoplanets",
    "black hole", "pulsar", "quasar", "universe", "cosmos", "astronomer",
    "solar", "astronomy", "astrophysics", "space image", "space photo"
}


def detect_intent(query: str) -> Literal["image", "video", "space"]:
    """
    Detect search intent from query.
    
    Uses deterministic keyword matching with context-aware priority:
    1. If video keywords present → video
    2. If space keywords present (galaxy, nebula, mars, moon, etc.) → space
       - Exception: "space wallpaper" or "space background" → image
    3. Otherwise → image
    
    Args:
        query: User search query
        
    Returns:
        "image", "video", or "space" intent
    """
    query_lower = query.lower().strip()
    
    # Count keyword matches for each type
    image_score = sum(1 for kw in IMAGE_KEYWORDS if kw in query_lower)
    video_score = sum(1 for kw in VIDEO_KEYWORDS if kw in query_lower)
    space_score = sum(1 for kw in SPACE_KEYWORDS if kw in query_lower)
    
    # Priority 1: Video keywords always win if present
    if video_score > 0:
        return "video"
    
    # Priority 2: Space keywords (unless it's decorative wallpaper)
    if space_score > 0:
        # Only exception: bare "space" keyword (not specific objects like galaxy/mars)
        # combined with decorative intent
        if query_lower == "space wallpaper" or query_lower == "space background":
            return "image"
        
        # All other space keyword matches → space search
        return "space"
    
    # Priority 3: Image keywords
    if image_score > 0:
        return "image"
    
    # Fallback heuristics when no keywords match
    
    # Explicit video phrases
    if any(phrase in query_lower for phrase in ["watch ", "playback", "streaming", "film about", "movie about"]):
        return "video"
    
    # Default: assume image search for visual content
    return "image"


def should_use_nasa(query: str) -> bool:
    """
    Determine if this should specifically use NASA API.
    
    NASA is best for:
    - Explicit NASA mentions
    - Specific space objects (Mars, Moon, Jupiter, galaxy, nebula, etc.)
    - Telescope/observatory content
    - Professional space/astronomy content
    
    General queries like "space wallpaper" should use image search instead.
    """
    query_lower = query.lower()
    
    # Strong NASA indicators
    if any(kw in query_lower for kw in ["nasa", "mars rover", "telescope", "hubble", "space station"]):
        return True
    
    # Specific celestial objects - return True unless looking for decorative content
    celestial = {"mars", "moon", "jupiter", "saturn", "venus", "mercury", "galaxy", "nebula", "asteroid", "comet"}
    if any(obj in query_lower for obj in celestial):
        # Return True unless explicitly looking for generic/decorative images
        if not any(generic in query_lower for generic in ["wallpaper", "background"]):
            return True
    
    # Astronomy/professional space content
    if any(kw in query_lower for kw in ["astronomer", "observatory", "astrophysics", "exoplanet", "rover"]):
        return True
    
    return False
