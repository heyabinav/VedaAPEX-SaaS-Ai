from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "VedaCLI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "SUPER_SECRET_KEY_CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    DATABASE_URL: str = "sqlite:///./vedaapex.db"

    # AI API Keys (to be filled via .env)
    OPENAI_API_KEY: Optional[str] = None
    CLAUDE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DOCUMENT_COMPILER_KEY: Optional[str] = None

    # Replicate Tier Keys
    REPLICATE_API_KEY_TIER1: Optional[str] = None
    REPLICATE_API_KEY_TIER2: Optional[str] = None
    REPLICATE_API_KEY_TIER3: Optional[str] = None
    REPLICATE_API_KEY_TIER4: Optional[str] = None

    # Fal AI Tier Keys
    FAL_API_KEY_TIER1: Optional[str] = None
    FAL_API_KEY_TIER2: Optional[str] = None
    FAL_API_KEY_TIER3: Optional[str] = None
    FAL_API_KEY_TIER4: Optional[str] = None
    FAL_API_KEY_TIER5: Optional[str] = None
    FAL_API_KEY_TIER6: Optional[str] = None
    FAL_API_KEY_TIER7: Optional[str] = None
    FAL_API_KEY_TIER8: Optional[str] = None

    # Tensor.art Tier Keys
    TENSOR_API_KEY_TIER1: Optional[str] = None
    TENSOR_API_KEY_TIER2: Optional[str] = None
    TENSOR_API_KEY_TIER3: Optional[str] = None
    TENSOR_API_KEY_TIER4: Optional[str] = None
    TENSOR_API_KEY_TIER5: Optional[str] = None
    TENSOR_API_KEY_TIER6: Optional[str] = None
    TENSOR_API_KEY_TIER7: Optional[str] = None
    TENSOR_API_KEY_TIER8: Optional[str] = None

    # Krea.ai Tier Keys
    KREA_API_KEY_TIER1: Optional[str] = None
    KREA_API_KEY_TIER2: Optional[str] = None
    KREA_API_KEY_TIER3: Optional[str] = None
    KREA_API_KEY_TIER4: Optional[str] = None
    KREA_API_KEY_TIER5: Optional[str] = None
    KREA_API_KEY_TIER6: Optional[str] = None
    KREA_API_KEY_TIER7: Optional[str] = None
    KREA_API_KEY_TIER8: Optional[str] = None

    # BFL.ai Tier Keys
    BFL_API_KEY_TIER1: Optional[str] = None
    BFL_API_KEY_TIER2: Optional[str] = None
    BFL_API_KEY_TIER3: Optional[str] = None
    BFL_API_KEY_TIER4: Optional[str] = None
    BFL_API_KEY_TIER5: Optional[str] = None
    BFL_API_KEY_TIER6: Optional[str] = None

    # GetImg.ai Tier Keys
    GETIMG_API_KEY_TIER1: Optional[str] = None
    GETIMG_API_KEY_TIER2: Optional[str] = None
    GETIMG_API_KEY_TIER3: Optional[str] = None
    GETIMG_API_KEY_TIER4: Optional[str] = None
    GETIMG_API_KEY_TIER5: Optional[str] = None
    GETIMG_API_KEY_TIER6: Optional[str] = None
    GETIMG_API_KEY_TIER7: Optional[str] = None
    GETIMG_API_KEY_TIER8: Optional[str] = None

    # Freepik Tier Keys
    FREEPIK_API_KEY_TIER1: Optional[str] = None
    FREEPIK_API_KEY_TIER2: Optional[str] = None
    FREEPIK_API_KEY_TIER3: Optional[str] = None
    FREEPIK_API_KEY_TIER4: Optional[str] = None

    # Free.ai Tier Keys
    FREE_API_KEY_TIER1: Optional[str] = None
    FREE_API_KEY_TIER2: Optional[str] = None
    FREE_API_KEY_TIER3: Optional[str] = None
    FREE_API_KEY_TIER4: Optional[str] = None
    FREE_API_KEY_TIER5: Optional[str] = None
    FREE_API_KEY_TIER6: Optional[str] = None
    FREE_API_KEY_TIER7: Optional[str] = None
    FREE_API_KEY_TIER8: Optional[str] = None
    FREE_API_KEY_TIER9: Optional[str] = None

    # Segmind Tier Keys
    SEGMIND_API_KEY_TIER1: Optional[str] = None
    SEGMIND_API_KEY_TIER2: Optional[str] = None
    SEGMIND_API_KEY_TIER3: Optional[str] = None
    SEGMIND_API_KEY_TIER4: Optional[str] = None
    SEGMIND_API_KEY_TIER5: Optional[str] = None
    SEGMIND_API_KEY_TIER6: Optional[str] = None
    SEGMIND_API_KEY_TIER7: Optional[str] = None
    SEGMIND_API_KEY_TIER8: Optional[str] = None

    # Together AI Tier Keys
    TOGETHER_API_KEY_TIER1: Optional[str] = None
    TOGETHER_API_KEY_TIER2: Optional[str] = None
    TOGETHER_API_KEY_TIER3: Optional[str] = None
    TOGETHER_API_KEY_TIER4: Optional[str] = None
    TOGETHER_API_KEY_TIER5: Optional[str] = None
    TOGETHER_API_KEY_TIER6: Optional[str] = None
    TOGETHER_API_KEY_TIER7: Optional[str] = None
    TOGETHER_API_KEY_TIER8: Optional[str] = None

    # Fireworks AI Tier Keys
    FIREWORKS_API_KEY_TIER1: Optional[str] = None
    FIREWORKS_API_KEY_TIER2: Optional[str] = None
    FIREWORKS_API_KEY_TIER3: Optional[str] = None
    FIREWORKS_API_KEY_TIER4: Optional[str] = None
    FIREWORKS_API_KEY_TIER5: Optional[str] = None
    FIREWORKS_API_KEY_TIER6: Optional[str] = None
    FIREWORKS_API_KEY_TIER7: Optional[str] = None
    FIREWORKS_API_KEY_TIER8: Optional[str] = None

    # Cloudflare Tier Keys
    CLOUDFLARE_ACCOUNT_ID_TIER1: Optional[str] = None
    CLOUDFLARE_API_KEY_TIER1: Optional[str] = None
    CLOUDFLARE_ACCOUNT_ID_TIER2: Optional[str] = None
    CLOUDFLARE_API_KEY_TIER2: Optional[str] = None
    CLOUDFLARE_ACCOUNT_ID_TIER3: Optional[str] = None
    CLOUDFLARE_API_KEY_TIER3: Optional[str] = None
    CLOUDFLARE_ACCOUNT_ID_TIER4: Optional[str] = None
    CLOUDFLARE_API_KEY_TIER4: Optional[str] = None
    CLOUDFLARE_ACCOUNT_ID_TIER5: Optional[str] = None
    CLOUDFLARE_API_KEY_TIER5: Optional[str] = None
    CLOUDFLARE_ACCOUNT_ID_TIER6: Optional[str] = None
    CLOUDFLARE_API_KEY_TIER6: Optional[str] = None
    CLOUDFLARE_ACCOUNT_ID_TIER7: Optional[str] = None
    CLOUDFLARE_API_KEY_TIER7: Optional[str] = None
    CLOUDFLARE_ACCOUNT_ID_TIER8: Optional[str] = None
    CLOUDFLARE_API_KEY_TIER8: Optional[str] = None

    # Pollinations Tier Keys
    POLLINATIONS_API_KEY_TIER1: Optional[str] = None

    # ElevenLabs Tier Keys
    ELEVENLABS_API_KEY_TIER1: Optional[str] = None
    ELEVENLABS_API_KEY_TIER2: Optional[str] = None
    ELEVENLABS_API_KEY_TIER3: Optional[str] = None
    ELEVENLABS_API_KEY_TIER4: Optional[str] = None
    ELEVENLABS_API_KEY_TIER5: Optional[str] = None
    ELEVENLABS_API_KEY_TIER6: Optional[str] = None
    ELEVENLABS_API_KEY_TIER7: Optional[str] = None

    # Pixverse Tier Keys
    PIXVERSE_API_KEY_TIER1: Optional[str] = None
    PIXVERSE_API_KEY_TIER2: Optional[str] = None
    PIXVERSE_API_KEY_TIER3: Optional[str] = None
    PIXVERSE_API_KEY_TIER4: Optional[str] = None
    PIXVERSE_API_KEY_TIER5: Optional[str] = None
    PIXVERSE_API_KEY_TIER6: Optional[str] = None
    PIXVERSE_API_KEY_TIER7: Optional[str] = None
    PIXVERSE_API_KEY_TIER8: Optional[str] = None

    # Imagenart Tier Keys
    IMAGENART_API_KEY_TIER1: Optional[str] = None
    IMAGENART_API_KEY_TIER2: Optional[str] = None
    IMAGENART_API_KEY_TIER3: Optional[str] = None
    IMAGENART_API_KEY_TIER4: Optional[str] = None
    IMAGENART_API_KEY_TIER5: Optional[str] = None
    IMAGENART_API_KEY_TIER6: Optional[str] = None
    IMAGENART_API_KEY_TIER7: Optional[str] = None
    IMAGENART_API_KEY_TIER8: Optional[str] = None

    # HeyGen Tier Keys
    HEYGEN_API_KEY_TIER1: Optional[str] = None
    HEYGEN_API_KEY_TIER2: Optional[str] = None
    HEYGEN_API_KEY_TIER3: Optional[str] = None
    HEYGEN_API_KEY_TIER4: Optional[str] = None
    HEYGEN_API_KEY_TIER5: Optional[str] = None
    HEYGEN_API_KEY_TIER6: Optional[str] = None
    HEYGEN_API_KEY_TIER7: Optional[str] = None
    HEYGEN_API_KEY_TIER8: Optional[str] = None

    # D-ID Tier Keys
    DID_API_KEY_TIER1: Optional[str] = None
    DID_API_KEY_TIER2: Optional[str] = None
    DID_API_KEY_TIER3: Optional[str] = None
    DID_API_KEY_TIER4: Optional[str] = None
    DID_API_KEY_TIER5: Optional[str] = None
    DID_API_KEY_TIER6: Optional[str] = None
    DID_API_KEY_TIER7: Optional[str] = None
    DID_API_KEY_TIER8: Optional[str] = None

    # DeepAI Tier Keys
    DEEPAI_API_KEY_TIER1: Optional[str] = None
    DEEPAI_API_KEY_TIER2: Optional[str] = None
    DEEPAI_API_KEY_TIER3: Optional[str] = None
    DEEPAI_API_KEY_TIER4: Optional[str] = None
    DEEPAI_API_KEY_TIER5: Optional[str] = None
    DEEPAI_API_KEY_TIER6: Optional[str] = None
    DEEPAI_API_KEY_TIER7: Optional[str] = None
    DEEPAI_API_KEY_TIER8: Optional[str] = None

    # Fotor AI Tier Keys
    FOTOR_API_KEY_TIER1: Optional[str] = None
    FOTOR_API_KEY_TIER2: Optional[str] = None
    FOTOR_API_KEY_TIER3: Optional[str] = None
    FOTOR_API_KEY_TIER4: Optional[str] = None
    FOTOR_API_KEY_TIER5: Optional[str] = None
    FOTOR_API_KEY_TIER6: Optional[str] = None
    FOTOR_API_KEY_TIER7: Optional[str] = None
    FOTOR_API_KEY_TIER8: Optional[str] = None

    # Wix Tier Keys
    WIX_API_KEY_TIER1: Optional[str] = None
    WIX_API_KEY_TIER2: Optional[str] = None
    WIX_API_KEY_TIER3: Optional[str] = None
    WIX_API_KEY_TIER4: Optional[str] = None
    WIX_API_KEY_TIER5: Optional[str] = None
    WIX_API_KEY_TIER6: Optional[str] = None
    WIX_API_KEY_TIER7: Optional[str] = None
    WIX_API_KEY_TIER8: Optional[str] = None
    WIX_API_KEY_TIER9: Optional[str] = None

    # Zoviz Tier Keys
    ZOVIZ_API_KEY_TIER1: Optional[str] = None
    ZOVIZ_API_KEY_TIER2: Optional[str] = None
    ZOVIZ_API_KEY_TIER3: Optional[str] = None
    ZOVIZ_API_KEY_TIER4: Optional[str] = None
    ZOVIZ_API_KEY_TIER5: Optional[str] = None
    ZOVIZ_API_KEY_TIER6: Optional[str] = None
    ZOVIZ_API_KEY_TIER7: Optional[str] = None
    ZOVIZ_API_KEY_TIER8: Optional[str] = None

    # Presenton AI Tier Keys
    PRESENTON_API_KEY_TIER1: Optional[str] = None
    PRESENTON_API_KEY_TIER2: Optional[str] = None
    PRESENTON_API_KEY_TIER3: Optional[str] = None
    PRESENTON_API_KEY_TIER4: Optional[str] = None
    PRESENTON_API_KEY_TIER5: Optional[str] = None
    PRESENTON_API_KEY_TIER6: Optional[str] = None
    PRESENTON_API_KEY_TIER7: Optional[str] = None
    PRESENTON_API_KEY_TIER8: Optional[str] = None

    # 2Slides Tier Keys
    TWOSLIDES_API_KEY_TIER1: Optional[str] = None
    TWOSLIDES_API_KEY_TIER2: Optional[str] = None
    TWOSLIDES_API_KEY_TIER3: Optional[str] = None
    TWOSLIDES_API_KEY_TIER4: Optional[str] = None
    TWOSLIDES_API_KEY_TIER5: Optional[str] = None
    TWOSLIDES_API_KEY_TIER6: Optional[str] = None
    TWOSLIDES_API_KEY_TIER7: Optional[str] = None
    TWOSLIDES_API_KEY_TIER8: Optional[str] = None

    # Skillboss Tier Keys
    SKILLBOSS_API_KEY_TIER1: Optional[str] = None
    SKILLBOSS_API_KEY_TIER2: Optional[str] = None
    SKILLBOSS_API_KEY_TIER3: Optional[str] = None
    SKILLBOSS_API_KEY_TIER4: Optional[str] = None
    SKILLBOSS_API_KEY_TIER5: Optional[str] = None
    SKILLBOSS_API_KEY_TIER6: Optional[str] = None
    SKILLBOSS_API_KEY_TIER7: Optional[str] = None
    SKILLBOSS_API_KEY_TIER8: Optional[str] = None

    # PiAPI Tier Keys
    PIAPI_API_KEY_TIER1: Optional[str] = None
    PIAPI_API_KEY_TIER2: Optional[str] = None
    PIAPI_API_KEY_TIER3: Optional[str] = None
    PIAPI_API_KEY_TIER4: Optional[str] = None
    PIAPI_API_KEY_TIER5: Optional[str] = None
    PIAPI_API_KEY_TIER6: Optional[str] = None
    PIAPI_API_KEY_TIER7: Optional[str] = None
    PIAPI_API_KEY_TIER8: Optional[str] = None

    # Ollama Tier Keys
    OLLAMA_API_KEY_TIER1: Optional[str] = None
    OLLAMA_API_KEY_TIER2: Optional[str] = None
    OLLAMA_API_KEY_TIER3: Optional[str] = None
    OLLAMA_API_KEY_TIER4: Optional[str] = None
    OLLAMA_API_KEY_TIER5: Optional[str] = None
    OLLAMA_API_KEY_TIER6: Optional[str] = None
    OLLAMA_API_KEY_TIER7: Optional[str] = None
    OLLAMA_API_KEY_TIER8: Optional[str] = None

    # Chutes AI Tier Keys
    CHUTES_API_KEY_TIER1: Optional[str] = None
    CHUTES_API_KEY_TIER2: Optional[str] = None
    CHUTES_API_KEY_TIER3: Optional[str] = None
    CHUTES_API_KEY_TIER4: Optional[str] = None
    CHUTES_API_KEY_TIER5: Optional[str] = None
    CHUTES_API_KEY_TIER6: Optional[str] = None
    CHUTES_API_KEY_TIER7: Optional[str] = None
    CHUTES_API_KEY_TIER8: Optional[str] = None

    # Groq Tier Keys
    GROQ_API_KEY_TIER1: Optional[str] = None
    GROQ_API_KEY_TIER2: Optional[str] = None
    GROQ_API_KEY_TIER3: Optional[str] = None
    GROQ_API_KEY_TIER4: Optional[str] = None
    GROQ_API_KEY_TIER5: Optional[str] = None
    GROQ_API_KEY_TIER6: Optional[str] = None
    GROQ_API_KEY_TIER7: Optional[str] = None
    GROQ_API_KEY_TIER8: Optional[str] = None
    GROQ_API_KEY_TIER9: Optional[str] = None

    # Genspark Tier Keys
    GENSPARK_API_KEY_TIER1: Optional[str] = None
    GENSPARK_API_KEY_TIER2: Optional[str] = None
    GENSPARK_API_KEY_TIER3: Optional[str] = None
    GENSPARK_API_KEY_TIER4: Optional[str] = None
    GENSPARK_API_KEY_TIER5: Optional[str] = None
    GENSPARK_API_KEY_TIER6: Optional[str] = None
    GENSPARK_API_KEY_TIER7: Optional[str] = None
    GENSPARK_API_KEY_TIER8: Optional[str] = None
    GENSPARK_API_BASE_URL: Optional[str] = None
    GENSPARK_VIDEO_CREATE_PATH: str = "/v1/video/generations"
    GENSPARK_VIDEO_STATUS_PATH: str = "/v1/video/generations/{task_id}"
    GENSPARK_AUTH_HEADER: str = "Authorization"
    GENSPARK_AUTH_SCHEME: str = "Bearer"

    # Tripo3D Tier Keys
    TRIPO3D_API_KEY_TIER1: Optional[str] = None
    TRIPO3D_API_KEY_TIER2: Optional[str] = None
    TRIPO3D_API_KEY_TIER3: Optional[str] = None
    TRIPO3D_API_KEY_TIER4: Optional[str] = None
    TRIPO3D_API_KEY_TIER5: Optional[str] = None
    TRIPO3D_API_KEY_TIER6: Optional[str] = None
    TRIPO3D_API_KEY_TIER7: Optional[str] = None
    TRIPO3D_API_KEY_TIER8: Optional[str] = None
    TRIPO3D_API_BASE_URL: str = "https://api.tripo3d.ai/v2/openapi"
    TRIPO3D_MODEL_VERSION: str = "Turbo-v1.0-20250506"
    TRIPO3D_EXPORT_FORMAT: str = "GLB"

    # TripoSplat Space config
    TRIPOSPLAT_SPACE_URL: str = "https://vast-ai-triposplat.hf.space"

    # TripoSR Space config
    TRIPOSR_SPACE_URL: str = "https://stabilityai-triposr.hf.space"

    # Microsoft TRELLIS.2 Space config
    TRELLIS2_SPACE_URL: str = "https://microsoft-trellis2.hf.space"

    # Ollama Base URL config
    OLLAMA_API_BASE: Optional[str] = "http://localhost:11434/v1"

    # Bytez Tier Keys
    BYTEZ_API_KEY_TIER1: Optional[str] = None
    BYTEZ_API_KEY_TIER2: Optional[str] = None
    BYTEZ_API_KEY_TIER3: Optional[str] = None
    BYTEZ_API_KEY_TIER4: Optional[str] = None
    BYTEZ_API_KEY_TIER5: Optional[str] = None
    BYTEZ_API_KEY_TIER6: Optional[str] = None
    BYTEZ_API_KEY_TIER7: Optional[str] = None
    BYTEZ_API_KEY_TIER8: Optional[str] = None

    # OpenRouter Tier Keys
    OPENROUTER_API_KEY_TIER1: Optional[str] = None
    OPENROUTER_API_KEY_TIER2: Optional[str] = None
    OPENROUTER_API_KEY_TIER3: Optional[str] = None
    OPENROUTER_API_KEY_TIER4: Optional[str] = None
    OPENROUTER_API_KEY_TIER5: Optional[str] = None
    OPENROUTER_API_KEY_TIER6: Optional[str] = None
    OPENROUTER_API_KEY_TIER7: Optional[str] = None
    OPENROUTER_API_KEY_TIER8: Optional[str] = None
    OPENROUTER_API_KEY_TIER9: Optional[str] = None
    OPENROUTER_API_KEY_TIER10: Optional[str] = None

    # RapidAPI Tier Keys
    RAPIDAPI_API_KEY_TIER1: Optional[str] = None
    RAPIDAPI_API_KEY_TIER2: Optional[str] = None
    RAPIDAPI_API_KEY_TIER3: Optional[str] = None
    RAPIDAPI_API_KEY_TIER4: Optional[str] = None
    RAPIDAPI_API_KEY_TIER5: Optional[str] = None
    RAPIDAPI_API_KEY_TIER6: Optional[str] = None
    RAPIDAPI_API_KEY_TIER7: Optional[str] = None
    RAPIDAPI_API_KEY_TIER8: Optional[str] = None

    # AIMLAPI Tier Keys
    AIMLAPI_API_KEY_TIER1: Optional[str] = None
    AIMLAPI_API_KEY_TIER2: Optional[str] = None
    AIMLAPI_API_KEY_TIER3: Optional[str] = None
    AIMLAPI_API_KEY_TIER4: Optional[str] = None
    AIMLAPI_API_KEY_TIER5: Optional[str] = None
    AIMLAPI_API_KEY_TIER6: Optional[str] = None
    AIMLAPI_API_KEY_TIER7: Optional[str] = None
    AIMLAPI_API_KEY_TIER8: Optional[str] = None

    # NVIDIA Tier Keys
    NVIDIA_API_KEY_TIER1: Optional[str] = None
    NVIDIA_API_KEY_TIER2: Optional[str] = None
    NVIDIA_API_KEY_TIER3: Optional[str] = None
    NVIDIA_API_KEY_TIER4: Optional[str] = None
    NVIDIA_API_KEY_TIER5: Optional[str] = None
    NVIDIA_API_KEY_TIER6: Optional[str] = None
    NVIDIA_API_KEY_TIER7: Optional[str] = None
    NVIDIA_API_KEY_TIER8: Optional[str] = None

    # Kling AI Tier Keys (Access Key + Secret Key)
    KLING_ACCESS_KEY_TIER1: Optional[str] = None
    KLING_SECRET_KEY_TIER1: Optional[str] = None
    KLING_ACCESS_KEY_TIER2: Optional[str] = None
    KLING_SECRET_KEY_TIER2: Optional[str] = None
    KLING_ACCESS_KEY_TIER3: Optional[str] = None
    KLING_SECRET_KEY_TIER3: Optional[str] = None
    KLING_ACCESS_KEY_TIER4: Optional[str] = None
    KLING_SECRET_KEY_TIER4: Optional[str] = None
    KLING_ACCESS_KEY_TIER5: Optional[str] = None
    KLING_SECRET_KEY_TIER5: Optional[str] = None
    KLING_ACCESS_KEY_TIER6: Optional[str] = None
    KLING_SECRET_KEY_TIER6: Optional[str] = None
    KLING_ACCESS_KEY_TIER7: Optional[str] = None
    KLING_SECRET_KEY_TIER7: Optional[str] = None
    KLING_ACCESS_KEY_TIER8: Optional[str] = None
    KLING_SECRET_KEY_TIER8: Optional[str] = None

    # Hugging Face Tier Keys
    HUGGINGFACE_API_KEY_TIER1: Optional[str] = None
    HUGGINGFACE_API_KEY_TIER2: Optional[str] = None
    HUGGINGFACE_API_KEY_TIER3: Optional[str] = None
    HUGGINGFACE_API_KEY_TIER4: Optional[str] = None
    HUGGINGFACE_API_KEY_TIER5: Optional[str] = None
    HUGGINGFACE_API_KEY_TIER6: Optional[str] = None
    HUGGINGFACE_API_KEY_TIER7: Optional[str] = None
    HUGGINGFACE_API_KEY_TIER8: Optional[str] = None
    HUGGINGFACE_API_KEY_TIER9: Optional[str] = None

    # Super API Tier Keys
    SUPER_API_KEY_TIER1: Optional[str] = None
    SUPER_API_KEY_TIER2: Optional[str] = None
    SUPER_API_KEY_TIER3: Optional[str] = None
    SUPER_API_KEY_TIER4: Optional[str] = None
    SUPER_API_KEY_TIER5: Optional[str] = None
    SUPER_API_KEY_TIER6: Optional[str] = None
    SUPER_API_KEY_TIER7: Optional[str] = None

    # Logo.dev Tier Keys (Publisher Key + Secret Key)
    LOGODEV_PUBLISHER_KEY_TIER1: Optional[str] = None
    LOGODEV_SECRET_KEY_TIER1: Optional[str] = None
    LOGODEV_PUBLISHER_KEY_TIER2: Optional[str] = None
    LOGODEV_SECRET_KEY_TIER2: Optional[str] = None
    LOGODEV_PUBLISHER_KEY_TIER3: Optional[str] = None
    LOGODEV_SECRET_KEY_TIER3: Optional[str] = None
    LOGODEV_PUBLISHER_KEY_TIER4: Optional[str] = None
    LOGODEV_SECRET_KEY_TIER4: Optional[str] = None
    LOGODEV_PUBLISHER_KEY_TIER5: Optional[str] = None
    LOGODEV_SECRET_KEY_TIER5: Optional[str] = None
    LOGODEV_PUBLISHER_KEY_TIER6: Optional[str] = None
    LOGODEV_SECRET_KEY_TIER6: Optional[str] = None
    LOGODEV_PUBLISHER_KEY_TIER7: Optional[str] = None
    LOGODEV_SECRET_KEY_TIER7: Optional[str] = None
    LOGODEV_PUBLISHER_KEY_TIER8: Optional[str] = None
    LOGODEV_SECRET_KEY_TIER8: Optional[str] = None

    # Tavily Tier Keys
    TAVILY_API_KEY_TIER1: Optional[str] = None
    TAVILY_API_KEY_TIER2: Optional[str] = None
    TAVILY_API_KEY_TIER3: Optional[str] = None
    TAVILY_API_KEY_TIER4: Optional[str] = None
    TAVILY_API_KEY_TIER5: Optional[str] = None
    TAVILY_API_KEY_TIER6: Optional[str] = None
    TAVILY_API_KEY_TIER7: Optional[str] = None
    TAVILY_API_KEY_TIER8: Optional[str] = None

    # Shotstack Tier Keys
    SHOTSTACK_API_KEY_TIER1: Optional[str] = None
    SHOTSTACK_API_KEY_TIER2: Optional[str] = None
    SHOTSTACK_API_KEY_TIER3: Optional[str] = None
    SHOTSTACK_API_KEY_TIER4: Optional[str] = None
    SHOTSTACK_API_KEY_TIER5: Optional[str] = None
    SHOTSTACK_API_KEY_TIER6: Optional[str] = None
    SHOTSTACK_API_KEY_TIER7: Optional[str] = None
    SHOTSTACK_API_KEY_TIER8: Optional[str] = None

    # Templar Tier Keys (tempplar.odysii.in)
    TEMPLAR_API_KEY_TIER1: Optional[str] = None
    TEMPLAR_API_KEY_TIER2: Optional[str] = None
    TEMPLAR_API_KEY_TIER3: Optional[str] = None
    TEMPLAR_API_KEY_TIER4: Optional[str] = None
    TEMPLAR_API_KEY_TIER5: Optional[str] = None
    TEMPLAR_API_KEY_TIER6: Optional[str] = None
    TEMPLAR_API_KEY_TIER7: Optional[str] = None
    TEMPLAR_API_KEY_TIER8: Optional[str] = None

    # CLAID.AI Tier Keys
    CLAID_API_KEY_TIER1: Optional[str] = None
    CLAID_API_KEY_TIER2: Optional[str] = None
    CLAID_API_KEY_TIER3: Optional[str] = None
    CLAID_API_KEY_TIER4: Optional[str] = None
    CLAID_API_KEY_TIER5: Optional[str] = None
    CLAID_API_KEY_TIER6: Optional[str] = None
    CLAID_API_KEY_TIER7: Optional[str] = None
    CLAID_API_KEY_TIER8: Optional[str] = None

    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_TIMEOUT_SECONDS: int = 15

    # OAuth / App Configuration (Generic - fallback)
    OAUTH_CLIENT_ID: Optional[str] = None
    OAUTH_CLIENT_SECRET: Optional[str] = None

    # Google OAuth Credentials
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None

    # Google Workspace OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = "http://localhost:8000/connectors/google/callback"

    # GitHub OAuth Credentials
    GITHUB_OAUTH_CLIENT_ID: Optional[str] = None
    GITHUB_OAUTH_CLIENT_SECRET: Optional[str] = None
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_REDIRECT_URI: Optional[str] = "http://localhost:8000/connectors/github/callback"

    # Notion OAuth Credentials
    NOTION_CLIENT_ID: Optional[str] = None
    NOTION_CLIENT_SECRET: Optional[str] = None
    NOTION_REDIRECT_URI: Optional[str] = "http://localhost:8000/connectors/notion/callback"

    # Canva OAuth Credentials
    CANVA_CLIENT_ID: Optional[str] = None
    CANVA_CLIENT_SECRET: Optional[str] = None
    CANVA_REDIRECT_URI: Optional[str] = "http://localhost:8000/connectors/canva/callback"
    CANVA_AUTHORIZATION_URL: str = "https://accounts.canva.com/oauth/authorize"
    CANVA_TOKEN_URL: str = "https://accounts.canva.com/oauth/token"
    CANVA_API_BASE_URL: str = "https://api.canva.com/v1"
    CANVA_SUCCESS_REDIRECT_URL: Optional[str] = "https://vedaapex.com/canva/return"
    CANVA_SCOPES: Optional[str] = "openid email profile design:meta design:content design:tools:embeds"

    # Encrypted OAuth token storage
    OAUTH_TOKEN_ENCRYPTION_KEY: Optional[str] = None

    # Figma OAuth / API
    FIGMA_CLIENT_ID: Optional[str] = None
    FIGMA_CLIENT_SECRET: Optional[str] = None
    FIGMA_REDIRECT_URI: Optional[str] = "http://localhost:8000/connectors/figma/callback"
    FIGMA_API_BASE_URL: str = "https://api.figma.com/v1"
    FIGMA_AUTHORIZATION_URL: str = "https://www.figma.com/oauth"
    FIGMA_TOKEN_URL: str = "https://www.figma.com/api/oauth/token"

    # App URLs
    APP_BASE_URL: Optional[str] = None
    FRONTEND_BASE_URL: Optional[str] = None

    # Session Cookie Configuration
    SESSION_COOKIE_NAME: str = "vedaapex_session"
    SESSION_COOKIE_MAX_AGE: int = 60 * 60 * 24 * 7  # 7 days
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: str = "lax"

    # Environment mode
    APP_ENV: str = "development"

    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    RAZORPAY_CURRENCY: str = "INR"
    RAZORPAY_MIN_AMOUNT_PAISA: int = 1000
    MEDIA_PROCESSOR_API_KEY: Optional[str] = None
    MEDIA_PUBLIC_BASE_URL: Optional[str] = None
    MEDIA_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    MEDIA_DOWNLOAD_TIMEOUT_SECONDS: int = 120
    MEDIA_MAX_DOWNLOAD_MB: int = 150

    # ── Asset Storage ─────────────────────────────────────
    R2_ENDPOINT_URL: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    ASSET_STORAGE_ENABLED: bool = True

    # ── Platform Domain ───────────────────────────────────
    PLATFORM_DOMAIN: Optional[str] = None

    # ── Logging ───────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    ENABLE_FILE_LOGGING: bool = True
    LOG_FILE_MAX_SIZE_MB: int = 50
    LOG_FILE_BACKUP_COUNT: int = 5

    # ── Security ──────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 150
    ALLOWED_UPLOAD_EXTENSIONS: str = ".jpg,.jpeg,.png,.gif,.webp,.mp4,.mov,.mp3,.wav,.pdf,.docx,.xlsx,.pptx"
    ADMIN_IP_WHITELIST: Optional[str] = None

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


settings = Settings()
