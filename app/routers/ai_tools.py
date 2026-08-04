from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Any
from sqlmodel import Session
from datetime import datetime

from ..schemas.ai_tools import (
    ImageGenerationRequest,
    VideoGenerationRequest,
    TextGenerationRequest,
    PromptGenerationRequest,
    ThreeDModelGenerationRequest,
    TTSRequest,
    WeddingCardRequest,
    LogoRequest,
    ImageEnhanceRequest,
    GenerationResponse,
    WordGenerationRequest,
    ExcelGenerationRequest,
    PPTGenerationRequest,
    MusicGenerationRequest,
    PDFGenerationRequest,
    AnimationGenerationRequest,
    CodeGenerationRequest,
    DesignGenerationRequest,
    AdsGenerationRequest,
    HomeDesignRequest,
    InteriorDesignRequest,
    HomeMapRequest,
    ColorSuggestionRequest,
    ThreeDEditRequest,
    Furniture3DGenerationRequest,
)
from ..services.ai_service import AIToolsService
from ..services.auth_service import AuthService
from ..services.generation_policy_service import GenerationPolicyService
from ..services.smart_generation_service import (
    RoutedGenerationResult,
    SmartGenerationService,
)
from ..services.token_service import TokenService
from ..db.session import get_session
from ..models.token import AIGenerationHistory
from ..models.user import User, Generation
from ..core.config import settings

router = APIRouter(
    prefix="/ai",
    tags=["AI Tools"],
    responses={404: {"description": "Not found"}},
)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    return await AuthService.get_authenticated_user(request, credentials, session)


def _extract_output_url(result: Any) -> str | None:
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url") or first.get("output_url")

    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        if isinstance(result.get("video"), dict):
            return result["video"].get("url")
        return result.get("url") or result.get("output_url")

    return None


def _daily_limit_error(policy, gen_type: str) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={
            "message": f"Daily free credits exhausted for {gen_type}.",
            "plan": policy.plan_name,
            "credits_required": policy.usage_cost,
            "daily_limit": policy.daily_credit_limit,
            "daily_used": policy.daily_credits_used,
            "daily_remaining": policy.daily_credits_remaining,
            "wallet_balance": policy.wallet_balance,
            "suggestion": "Upgrade your plan or add credits to continue with premium fallback routing.",
        },
    )


def _is_true_exhaustion_error(err_msg: str) -> bool:
    normalized = err_msg.lower()
    return any(
        phrase in normalized
        for phrase in [
            "all platforms",
            "all tiers",
            "all free providers failed",
            "all premium providers failed",
            "all providers failed",
        ]
    )


async def _run_generation_with_policy(
    gen_type: str,
    generation_func,
    policy,
    kwargs: dict[str, Any],
) -> RoutedGenerationResult:
    preferred_provider = kwargs.get("provider")

    if SmartGenerationService.supports_free_first(gen_type, kwargs):
        if policy.use_daily_free_route:
            try:
                return await SmartGenerationService.run_route(
                    gen_type=gen_type,
                    generation_func=generation_func,
                    kwargs=kwargs,
                    route_mode="free",
                    preferred_provider=preferred_provider,
                )
            except Exception:
                if not policy.allow_premium_fallback:
                    raise
                return await SmartGenerationService.run_route(
                    gen_type=gen_type,
                    generation_func=generation_func,
                    kwargs=kwargs,
                    route_mode="premium",
                    preferred_provider=preferred_provider,
                )

        if not policy.allow_premium_fallback:
            raise _daily_limit_error(policy, gen_type)

        return await SmartGenerationService.run_route(
            gen_type=gen_type,
            generation_func=generation_func,
            kwargs=kwargs,
            route_mode="premium",
            preferred_provider=preferred_provider,
        )

    result = await generation_func(**kwargs)
    return RoutedGenerationResult(
        result=result,
        provider=kwargs.get("provider"),
        route_mode="direct",
    )


async def check_and_log_generation(
    user: User,
    gen_type: str,
    log_prompt: str,
    session: Session,
    generation_func,
    *args,
    **kwargs,
):
    from app.services.exhaustion_service import ExhaustionService

    # If a crash state exists, allow one recovery attempt so the API can clear
    # itself when provider access is restored.
    crashed_today = ExhaustionService.is_crashed()
    if crashed_today:
        pass

    del args
    policy = GenerationPolicyService.build_policy(session, user, gen_type)
    if not policy.use_daily_free_route and not policy.allow_premium_fallback:
        raise _daily_limit_error(policy, gen_type)

    try:
        routed = await _run_generation_with_policy(
            gen_type=gen_type,
            generation_func=generation_func,
            policy=policy,
            kwargs=kwargs,
        )
        result = routed.result

    except Exception as e:
        session.add(
            AIGenerationHistory(
                user_id=user.id,
                type=policy.cost_key,
                prompt=log_prompt,
                cost=0,
                status="FAILED",
                provider=kwargs.get("provider"),
                created_at=datetime.utcnow(),
            )
        )
        session.commit()

        err_msg = str(e).lower()
        if _is_true_exhaustion_error(err_msg):
            ExhaustionService.mark_crashed()
            raise HTTPException(
                status_code=503,
                detail="Couldn't reach server. Please try again later. / सर्वर तक नहीं पहुँचा जा सका। कृपया बाद में प्रयास करें।",
            )
        raise e

    output_url = _extract_output_url(result)

    generation_log = Generation(
        user_id=user.id,
        type=gen_type,
        prompt=log_prompt,
        output_url=output_url,
        created_at=datetime.utcnow(),
    )
    session.add(generation_log)

    session.add(
        AIGenerationHistory(
            user_id=user.id,
            type=policy.cost_key,
            prompt=log_prompt,
            output_url=output_url,
            cost=policy.usage_cost if policy.daily_credit_limit is not None else 0,
            status="SUCCESS",
            provider=routed.provider,
            model_used=routed.route_mode,
            created_at=datetime.utcnow(),
        )
    )

    if policy.charge_wallet_on_success:
        TokenService.deduct_credits(
            session,
            user.id,
            policy.usage_cost,
            tx_type="USAGE",
            description=f"{policy.cost_key} generation: -{policy.usage_cost} credits",
        )
    else:
        session.commit()

    # Clear any previous exhaustion crash state once generation succeeds again.
    ExhaustionService.clear_crash()

    if hasattr(user, "webhook_url") and user.webhook_url:
        from ..services.webhook_service import WebhookService
        import asyncio

        asyncio.create_task(
            WebhookService.broadcast_generation_completed(
                user.id, gen_type, output_url, user.webhook_url
            )
        )

    return result


@router.post("/generate/image", response_model=GenerationResponse)
async def generate_image(
    request: ImageGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        result = await check_and_log_generation(
            user=current_user,
            gen_type="image",
            log_prompt=request.prompt,
            session=session,
            generation_func=AIToolsService.generate_image,
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            num_outputs=request.num_outputs,
            tier=request.tier,
            provider=request.provider,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/video", response_model=GenerationResponse)
async def generate_video(
    request: VideoGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        result = await check_and_log_generation(
            user=current_user,
            gen_type="video",
            log_prompt=request.prompt,
            session=session,
            generation_func=AIToolsService.generate_video,
            prompt=request.prompt,
            tier=request.tier,
            provider=request.provider,
            avatar_id=request.avatar_id,
            voice_id=request.voice_id,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/text", response_model=GenerationResponse)
async def generate_text(
    request: TextGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        provider = getattr(request, "provider", "auto")
        result = await check_and_log_generation(
            user=current_user,
            gen_type="text",
            log_prompt=request.prompt,
            session=session,
            generation_func=AIToolsService.generate_text,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            tier=request.tier,
            provider=provider,
        )
        # Replicate text models often return a list of tokens
        if isinstance(result, list):
            result = "".join(result)
        # Handle OpenAI format (free.ai)
        elif isinstance(result, dict) and "choices" in result:
            result = result["choices"][0]["message"]["content"]

        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/text-to-text", response_model=GenerationResponse)
async def generate_text_to_text(
    request: TextGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        provider = getattr(request, "provider", "auto")
        result = await check_and_log_generation(
            user=current_user,
            gen_type="text",
            log_prompt=request.prompt,
            session=session,
            generation_func=AIToolsService.generate_text,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            tier=request.tier,
            provider=provider,
        )
        if isinstance(result, list):
            result = "".join(result)
        elif isinstance(result, dict) and "choices" in result:
            result = result["choices"][0]["message"]["content"]

        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/prompt", response_model=GenerationResponse)
async def generate_prompt(
    request: PromptGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        result = await check_and_log_generation(
            user=current_user,
            gen_type="prompt",
            log_prompt=request.base_concept,
            session=session,
            generation_func=AIToolsService.generate_prompt,
            base_concept=request.base_concept,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/code-generate", response_model=GenerationResponse)
async def generate_code_generate(
    request: CodeGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        result = await check_and_log_generation(
            user=current_user,
            gen_type="code",
            log_prompt=f"{request.language}: {request.prompt}",
            session=session,
            generation_func=AIToolsService.generate_code,
            prompt=request.prompt,
            language=request.language or "python",
            tier=request.tier,
            provider=request.provider,
        )
        if isinstance(result, list):
            result = "".join(result)
        elif isinstance(result, dict) and "choices" in result:
            result = result["choices"][0]["message"]["content"]

        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/3d", response_model=GenerationResponse)
async def generate_3d_model(
    request: ThreeDModelGenerationRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        result = await check_and_log_generation(
            user=current_user,
            gen_type="3d",
            log_prompt=request.prompt or request.image_url or "",
            session=session,
            generation_func=AIToolsService.generate_3d_model,
            prompt=request.prompt,
            image_url=request.image_url,
            tier=request.tier,
            provider=request.provider,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/tts", response_model=GenerationResponse)
async def generate_tts(
    request: TTSRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        result = await check_and_log_generation(
            user=current_user,
            gen_type="tts",
            log_prompt=request.text,
            session=session,
            generation_func=AIToolsService.generate_tts,
            text=request.text,
            voice=request.voice,
            tier=request.tier,
            provider=request.provider,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/wedding-card", response_model=GenerationResponse)
async def generate_wedding_card(
    request: WeddingCardRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        log_prompt = f"Wedding card: {request.bride_name} & {request.groom_name}"
        result = await check_and_log_generation(
            user=current_user,
            gen_type="image",
            log_prompt=log_prompt,
            session=session,
            generation_func=AIToolsService.generate_wedding_card,
            groom_name=request.groom_name,
            bride_name=request.bride_name,
            date=request.date,
            venue=request.venue,
            theme=request.theme_prompt,
            tier=request.tier,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/logo", response_model=GenerationResponse)
async def generate_logo(
    request: LogoRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        log_prompt = f"Logo: {request.brand_name} ({request.niche})"
        result = await check_and_log_generation(
            user=current_user,
            gen_type="image",
            log_prompt=log_prompt,
            session=session,
            generation_func=AIToolsService.generate_logo,
            brand_name=request.brand_name,
            niche=request.niche,
            style=request.style_prompt,
            tier=request.tier,
            provider=request.provider,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhance/image", response_model=GenerationResponse)
async def enhance_image(
    request: ImageEnhanceRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        result = await check_and_log_generation(
            user=current_user,
            gen_type="image",
            log_prompt=request.prompt or "Image enhance",
            session=session,
            generation_func=AIToolsService.enhance_image,
            image_url=request.image_url,
            prompt=request.prompt,
            tier=request.tier,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/ppt", response_model=GenerationResponse)
async def generate_ppt(
    request: PPTGenerationRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    provider = getattr(request, "provider", "2slides")

    if provider == "2slides":
        from app.services.providers.twoslides_provider import TwoslidesProvider

        try:
            result = await check_and_log_generation(
                user=current_user,
                gen_type="ppt",
                log_prompt=request.prompt,
                session=session,
                generation_func=TwoslidesProvider.generate_ppt,
                prompt=request.prompt,
                starting_tier=request.tier,
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif provider == "presenton":
        from app.services.providers.presenton_provider import PresentonProvider

        try:
            result = await check_and_log_generation(
                user=current_user,
                gen_type="ppt",
                log_prompt=request.prompt,
                session=session,
                generation_func=PresentonProvider.generate_ppt,
                prompt=request.prompt,
                starting_tier=request.tier,
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif provider == "skillboss":
        from app.services.providers.skillboss_provider import SkillbossProvider

        try:
            result = await check_and_log_generation(
                user=current_user,
                gen_type="ppt",
                log_prompt=request.prompt,
                session=session,
                generation_func=SkillbossProvider.generate_ppt,
                prompt=request.prompt,
                starting_tier=request.tier,
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    elif provider in ["groq", "ollama"]:
        from app.services.document_service import DocumentService

        try:
            result = await check_and_log_generation(
                user=current_user,
                gen_type="ppt",
                log_prompt=request.prompt,
                session=session,
                generation_func=DocumentService.generate_ppt,
                prompt=request.prompt,
                base_url=str(req.base_url),
                provider=provider,
                tier=request.tier,
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        from app.core.config import settings

        if not settings.DOCUMENT_COMPILER_KEY:
            raise HTTPException(
                status_code=501,
                detail="Document compilation feature is currently inactive. Please configure DOCUMENT_COMPILER_KEY in your .env file to activate.",
            )
        try:
            from app.services.document_service import DocumentService

            result = await check_and_log_generation(
                user=current_user,
                gen_type="ppt",
                log_prompt=request.prompt,
                session=session,
                generation_func=DocumentService.generate_ppt,
                prompt=request.prompt,
                base_url=str(req.base_url),
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/word", response_model=GenerationResponse)
async def generate_word(
    request: WordGenerationRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    provider = getattr(request, "provider", "document_compiler")

    if provider in ["groq", "ollama"]:
        from app.services.document_service import DocumentService

        try:
            result = await check_and_log_generation(
                user=current_user,
                gen_type="word",
                log_prompt=request.prompt,
                session=session,
                generation_func=DocumentService.generate_word,
                prompt=request.prompt,
                base_url=str(req.base_url),
                provider=provider,
                tier=request.tier,
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        from app.core.config import settings

        if not settings.DOCUMENT_COMPILER_KEY:
            raise HTTPException(
                status_code=501,
                detail="Document compilation feature is currently inactive. Please configure DOCUMENT_COMPILER_KEY in your .env file to activate.",
            )
        try:
            from app.services.document_service import DocumentService

            result = await check_and_log_generation(
                user=current_user,
                gen_type="word",
                log_prompt=request.prompt,
                session=session,
                generation_func=DocumentService.generate_word,
                prompt=request.prompt,
                base_url=str(req.base_url),
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/excel", response_model=GenerationResponse)
async def generate_excel(
    request: ExcelGenerationRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    provider = getattr(request, "provider", "document_compiler")

    if provider in ["groq", "ollama"]:
        from app.services.document_service import DocumentService

        try:
            result = await check_and_log_generation(
                user=current_user,
                gen_type="excel",
                log_prompt=request.prompt,
                session=session,
                generation_func=DocumentService.generate_excel,
                prompt=request.prompt,
                base_url=str(req.base_url),
                provider=provider,
                tier=request.tier,
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        from app.core.config import settings

        if not settings.DOCUMENT_COMPILER_KEY:
            raise HTTPException(
                status_code=501,
                detail="Document compilation feature is currently inactive. Please configure DOCUMENT_COMPILER_KEY in your .env file to activate.",
            )
        try:
            from app.services.document_service import DocumentService

            result = await check_and_log_generation(
                user=current_user,
                gen_type="excel",
                log_prompt=request.prompt,
                session=session,
                generation_func=DocumentService.generate_excel,
                prompt=request.prompt,
                base_url=str(req.base_url),
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# =============================================
#   MUSIC GENERATION (Suno / Udio via PiAPI)
# =============================================
@router.post("/generate/music", response_model=GenerationResponse)
async def generate_music(
    request: MusicGenerationRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        result = await check_and_log_generation(
            user=current_user,
            gen_type="music",
            log_prompt=request.prompt,
            session=session,
            generation_func=AIToolsService.generate_music,
            prompt=request.prompt,
            tier=request.tier,
            provider=request.provider,
        )
        return GenerationResponse(status="success", result=result)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================
#   PDF DOCUMENT GENERATION (Groq / Ollama)
# =============================================
@router.post("/generate/pdf", response_model=GenerationResponse)
async def generate_pdf(
    request: PDFGenerationRequest,
    req: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    provider = getattr(request, "provider", "document_compiler")

    if provider in ["groq", "ollama"]:
        from app.services.document_service import DocumentService

        try:
            result = await check_and_log_generation(
                user=current_user,
                gen_type="pdf",
                log_prompt=request.prompt,
                session=session,
                generation_func=DocumentService.generate_pdf,
                prompt=request.prompt,
                base_url=str(req.base_url),
                provider=provider,
                tier=request.tier,
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        from app.core.config import settings

        if not settings.DOCUMENT_COMPILER_KEY:
            raise HTTPException(
                status_code=501,
                detail="Document compilation feature is currently inactive. Please configure DOCUMENT_COMPILER_KEY in your .env file to activate.",
            )
        try:
            from app.services.document_service import DocumentService

            result = await check_and_log_generation(
                user=current_user,
                gen_type="pdf",
                log_prompt=request.prompt,
                session=session,
                generation_func=DocumentService.generate_pdf,
                prompt=request.prompt,
                base_url=str(req.base_url),
            )
            return GenerationResponse(status="success", result=result)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
