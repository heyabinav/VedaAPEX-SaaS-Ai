"""
PowerPoint presentation generation API endpoint.

Integrates with existing AI provider system and asset storage.
Handles user authentication and file persistence.
"""

import logging
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.db.session import get_session
from app.routers.auth import get_current_user_auth
from app.models.user import User
from app.models.asset import AIAsset
from app.schemas.presentations import (
    PPTGenerationRequest,
    PPTGenerationResponse,
    PresentationPlan,
)
from app.services.ai_service import AIToolsService
from app.services.asset_storage_service import AssetStorageService
from app.services.ppt import generate_pptx

logger = logging.getLogger("app.routers.presentations")

router = APIRouter(prefix="/api/v1/presentations", tags=["presentations"])


async def _generate_presentation_plan(
    prompt: str,
    slide_count: int,
    theme: str,
    language: str,
    provider: Optional[str] = "auto",
) -> PresentationPlan:
    """
    Generate presentation plan from prompt using AI text model.
    
    The AI model returns a JSON structure (not binary) with slide content.
    Python then creates the actual PPTX file.
    """
    # Build system prompt for structured output
    system_prompt = f"""You are an expert presentation designer. Generate a complete presentation plan in JSON format.

The user has requested a {slide_count}-slide presentation in {language}.
Theme: {theme}

Return ONLY valid JSON (no markdown, no extra text) with this structure:
{{
    "title": "Presentation Title",
    "subtitle": "Optional subtitle",
    "author": "VedaApex",
    "theme": "{theme}",
    "language": "{language}",
    "slides": [
        {{
            "slide_number": 1,
            "layout": "title",
            "title": "Slide Title",
            "subtitle": "Optional",
            "bullets": [],
            "paragraphs": [],
            "speaker_notes": null,
            "image_search_queries": []
        }},
        ...more slides...
    ]
}}

CONSTRAINTS:
- Total slides: exactly {slide_count}
- Each slide must have: slide_number (1 to {slide_count}), layout, title
- Bullets: max 10 per slide, max 300 chars each
- Paragraphs: max 5 per slide, max 1000 chars each
- Layouts: title, section, content, two_column, title_and_content, quote, image_with_text, table, chart, code, conclusion
- Return ONLY JSON, NO MARKDOWN CODE BLOCKS
"""

    user_prompt = f"Create a presentation about: {prompt}"

    try:
        # Use existing AI provider system with text generation
        logger.info("Generating presentation plan: %s slides", slide_count)

        result = await AIToolsService.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            provider=provider,
            tier=1,
        )

        # Handle different response formats
        if isinstance(result, dict) and "choices" in result:
            # OpenAI format
            json_text = result["choices"][0]["message"]["content"]
        elif isinstance(result, dict) and "candidates" in result:
            # Gemini format
            json_text = result["candidates"][0]["content"]["parts"][0]["text"]
        elif isinstance(result, str):
            json_text = result
        elif isinstance(result, list):
            json_text = "".join(result) if result else ""
        else:
            raise ValueError(f"Unexpected AI response format: {type(result)}")

        # Clean up potential markdown wrapping
        json_text = json_text.strip()
        if json_text.startswith("```"):
            lines = json_text.split("\n")
            json_text = "\n".join(lines[1:-1]) if len(lines) > 2 else ""

        logger.info("Received AI response, parsing JSON...")

        # Parse JSON
        plan_dict = json.loads(json_text)

        # Validate against schema (will raise ValidationError if invalid)
        presentation_plan = PresentationPlan(**plan_dict)

        logger.info("Presentation plan validated: %d slides", len(presentation_plan.slides))
        return presentation_plan

    except json.JSONDecodeError as exc:
        logger.exception("Failed to parse AI-generated JSON: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI model returned invalid JSON: {exc}",
        ) from exc
    except ValueError as exc:
        logger.exception("Validation error in presentation plan: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Presentation plan validation failed: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Presentation plan generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presentation: {exc}",
        ) from exc


@router.post("/generate", response_model=PPTGenerationResponse)
async def generate_presentation(
    request: PPTGenerationRequest,
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
) -> PPTGenerationResponse:
    """
    Generate a PowerPoint presentation from a text prompt.
    
    Flow:
    1. User submits prompt with slide count and theme
    2. AI model generates structured presentation plan (JSON)
    3. Python creates actual PPTX file using python-pptx
    4. File is stored via AssetStorageService
    5. Metadata is saved to database
    6. Client receives download URL
    """
    try:
        presentation_id = str(uuid.uuid4())
        logger.info(
            "PPT generation requested: user=%s, slides=%d, theme=%s",
            current_user.id,
            request.slide_count,
            request.theme,
        )

        # Step 1: Generate presentation plan from AI
        presentation_plan = await _generate_presentation_plan(
            prompt=request.prompt,
            slide_count=request.slide_count,
            theme=request.theme.value,
            language=request.language,
            provider=request.provider,
        )

        # Step 2: Create PPTX file
        logger.info("Generating PPTX file...")
        pptx_bytes = generate_pptx(presentation_plan)

        # Step 3: Store file via AssetStorageService
        filename = f"{presentation_plan.title.replace(' ', '_')[:50]}_{presentation_id[:8]}.pptx"
        asset_storage = AssetStorageService()

        # Upload to storage (R2 or local)
        asset = await asset_storage.upload_asset(
            file_bytes=pptx_bytes,
            filename=filename,
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            asset_type="presentation",
            user_id=current_user.id,
            metadata={
                "presentation_id": presentation_id,
                "prompt": request.prompt,
                "slide_count": request.slide_count,
                "theme": request.theme.value,
                "provider": request.provider or "auto",
            },
        )

        logger.info(
            "PPT generated and stored: presentation_id=%s, attachment_id=%s, size=%d bytes",
            presentation_id,
            asset.id,
            len(pptx_bytes),
        )

        return PPTGenerationResponse(
            success=True,
            presentation_id=presentation_id,
            attachment_id=asset.id,
            filename=filename,
            file_size_bytes=len(pptx_bytes),
            status="completed",
            proxy_url=asset.proxy_url,
            error_message=None,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("PPT generation failed: %s", exc)
        return PPTGenerationResponse(
            success=False,
            presentation_id=None,
            attachment_id=None,
            filename="",
            file_size_bytes=0,
            status="failed",
            proxy_url=None,
            error_message=str(exc),
        )


@router.get("/{presentation_id}")
async def get_presentation_details(
    presentation_id: str,
    current_user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """
    Retrieve metadata for a generated presentation.
    
    Ensures user ownership before returning details.
    """
    try:
        # Find asset by presentation_id in metadata
        asset = (
            session.query(AIAsset)
            .filter(
                AIAsset.user_id == current_user.id,
                AIAsset.asset_type == "presentation",
            )
            .first()
        )

        if not asset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Presentation not found",
            )

        return {
            "presentation_id": presentation_id,
            "attachment_id": asset.id,
            "filename": asset.original_url or "presentation.pptx",
            "file_size_bytes": asset.file_size_bytes,
            "created_at": asset.created_at,
            "proxy_url": asset.proxy_url,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve presentation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
