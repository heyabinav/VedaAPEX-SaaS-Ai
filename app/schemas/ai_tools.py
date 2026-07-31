from pydantic import BaseModel
from typing import Optional, Any, Dict


class ImageGenerationRequest(BaseModel):
    prompt: str
    tier: int = 1  # 1 to 9
    num_outputs: int = 1
    aspect_ratio: str = "1:1"
    provider: Optional[str] = "auto"  # Free-route first, then premium fallback.


class VideoGenerationRequest(BaseModel):
    prompt: str
    tier: int = 1  # 1 to 8
    provider: Optional[str] = "auto"  # Free-route first, then premium fallback.
    avatar_id: Optional[str] = None
    voice_id: Optional[str] = None


class TextGenerationRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    tier: int = 1
    provider: Optional[str] = "auto"  # Free-route first, then premium fallback.


class PromptGenerationRequest(BaseModel):
    base_concept: str


class ThreeDModelGenerationRequest(BaseModel):
    prompt: Optional[str] = None
    image_url: Optional[str] = None
    tier: int = 1  # 1 to 8
    provider: Optional[str] = "replicate"  # Can be "replicate", "krea", "piapi", "trellis", "triposplat", "triposr"


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None
    tier: int = 1
    provider: Optional[str] = "apexspeech"  # Can be "apexspeech", "fal", "replicate"


class WeddingCardRequest(BaseModel):
    groom_name: str
    bride_name: str
    date: str
    venue: str
    theme_prompt: Optional[str] = None
    tier: int = 1


class LogoRequest(BaseModel):
    brand_name: str
    niche: str
    style_prompt: Optional[str] = None
    tier: int = 1
    provider: Optional[str] = "auto"


class ImageEnhanceRequest(BaseModel):
    image_url: str
    prompt: Optional[str] = None
    tier: int = 1


class WordGenerationRequest(BaseModel):
    prompt: str
    tier: int = 1
    provider: Optional[str] = "document_compiler"  # Can be "document_compiler", "groq", "ollama"


class ExcelGenerationRequest(BaseModel):
    prompt: str
    tier: int = 1
    provider: Optional[str] = "document_compiler"  # Can be "document_compiler", "groq", "ollama"


class PPTGenerationRequest(BaseModel):
    prompt: str
    tier: int = 1
    provider: Optional[str] = (
        "skillboss"  # Can be "2slides", "presenton", "skillboss", "document_compiler", "groq", "ollama"
    )


class MusicGenerationRequest(BaseModel):
    prompt: str
    tier: int = 1
    provider: Optional[str] = "suno"  # Can be "suno" or "udio"


class PDFGenerationRequest(BaseModel):
    prompt: str
    tier: int = 1
    provider: Optional[str] = "document_compiler"  # Can be "document_compiler", "groq", "ollama"


class AnimationGenerationRequest(BaseModel):
    prompt: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    tier: int = 1
    provider: Optional[str] = "fal"  # Can be "fal", "replicate", "kling", "luma"


class CodeGenerationRequest(BaseModel):
    prompt: str
    language: Optional[str] = "python"
    tier: int = 1
    provider: Optional[str] = "groq"  # Can be "groq", "openrouter", "ollama"


class DesignGenerationRequest(BaseModel):
    prompt: str
    tier: int = 1
    provider: Optional[str] = "tensor"  # Can be "tensor", "fal", "replicate"


class AdsGenerationRequest(BaseModel):
    product_name: str
    description: str
    target_audience: Optional[str] = None
    tier: int = 1
    provider: Optional[str] = "groq"  # Can be "groq", "openai"


class HomeDesignRequest(BaseModel):
    prompt: str
    image_url: Optional[str] = None
    tier: int = 1
    provider: Optional[str] = "replicate"  # Can be "replicate", "fal"


class InteriorDesignRequest(BaseModel):
    prompt: str
    room_type: str
    style: Optional[str] = "modern"
    image_url: Optional[str] = None
    tier: int = 1
    provider: Optional[str] = "replicate"


class HomeMapRequest(BaseModel):
    prompt: str
    plot_size: Optional[str] = None
    tier: int = 1
    provider: Optional[str] = "replicate"


class ColorSuggestionRequest(BaseModel):
    prompt: str
    tier: int = 1
    provider: Optional[str] = "groq"


class ThreeDEditRequest(BaseModel):
    model_url: str  # Task ID or GLB URL to refine
    prompt: str
    tier: int = 1
    provider: Optional[str] = "meshy"


class Furniture3DGenerationRequest(BaseModel):
    name: str
    width: float = 1.0
    depth: float = 1.0
    height: float = 0.75
    tier: int = 1


class GenerationResponse(BaseModel):
    status: str
    result: Any
