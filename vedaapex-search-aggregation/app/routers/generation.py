from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.user import User
from app.models.token import AIGenerationHistory
from app.routers.auth import get_current_user_auth
from app.services.token_service import TokenService
from app.config.costs import GENERATION_COSTS
from datetime import datetime

router = APIRouter(prefix="/generate", tags=["AI Generation (Credits)"])


@router.get("/costs")
async def get_costs():
    return {"success": True, "data": GENERATION_COSTS}


@router.post("/{gen_type}")
async def process_generation(
    gen_type: str,
    request: Request,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    from app.services.exhaustion_service import ExhaustionService

    if ExhaustionService.is_crashed():
        raise HTTPException(
            status_code=503,
            detail="Couldn't reach server. Please try again later. / सर्वर तक नहीं पहुँचा जा सका। कृपया बाद में प्रयास करें।",
        )

    gen_key = (
        gen_type.upper()
        .replace("-", "_")
        .replace("bg_removal", "BG_REMOVAL")
        .replace("3d", "MODEL_3D")
    )
    # Normalize common variations
    type_map = {
        "IMAGE": "IMAGE",
        "VIDEO": "VIDEO",
        "PPT": "PPT",
        "3D": "MODEL_3D",
        "MODEL_3D": "MODEL_3D",
        "BG_REMOVAL": "BG_REMOVAL",
        "BG-REMOVAL": "BG_REMOVAL",
        "TEXT": "TEXT",
        "TTS": "TTS",
    }
    normalized = type_map.get(gen_key, gen_key)
    cost = GENERATION_COSTS.get(normalized)

    if cost is None:
        raise HTTPException(status_code=400, detail=f"Unknown generation type: {gen_type}")

    body = await request.json()
    prompt = body.get("prompt", "")

    # Check if user has an active premium subscription (Pro, Max, Ultra)
    is_free = True
    if user.subscription and user.subscription.status == "active":
        plan_name = user.subscription.plan.upper()
        if plan_name in ["PRO", "MAX", "ULTRA"]:
            is_free = False

    # Get balance and apply cost logic
    wallet = TokenService.get_balance(session, user.id)
    actual_cost = cost if is_free else 0

    if is_free:
        if wallet.balance < actual_cost:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "Insufficient Credits",
                    "required": actual_cost,
                    "available": wallet.balance,
                    "deficit": actual_cost - wallet.balance,
                },
            )

        # Deduct credits
        try:
            updated_wallet = TokenService.deduct_credits(
                session,
                user.id,
                actual_cost,
                tx_type="USAGE",
                description=f"{normalized} generation: -{actual_cost} credits",
                ip_address=request.client.host,
            )
        except ValueError as e:
            if str(e) == "INSUFFICIENT_CREDITS":
                raise HTTPException(status_code=402, detail="Insufficient Credits")
            raise
    else:
        # Premium users don't pay credits
        updated_wallet = wallet

    # Log generation
    gen = AIGenerationHistory(
        user_id=user.id,
        type=normalized,
        prompt=prompt,
        cost=actual_cost,
        status="SUCCESS",
        provider=body.get("provider"),
        model_used=body.get("model_used"),
        output_url=body.get("output_url"),
        ip_address=request.client.host,
    )
    session.add(gen)
    session.commit()

    return {
        "success": True,
        "message": (
            f"{normalized} generated successfully!"
            if is_free
            else f"{normalized} generated successfully (Unlimited Premium Access)!"
        ),
        "data": {
            "generation_id": gen.id,
            "credits_used": actual_cost,
            "balance": updated_wallet.balance,
            "previous_balance": updated_wallet.balance + actual_cost,
        },
    }


@router.get("/history")
async def get_history(
    page: int = 1,
    limit: int = 20,
    type: str = None,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    query = select(AIGenerationHistory).where(AIGenerationHistory.user_id == user.id)
    if type:
        query = query.where(AIGenerationHistory.type == type.upper())
    query = query.order_by(AIGenerationHistory.created_at.desc())

    all_gens = session.exec(query).all()
    total = len(all_gens)
    offset = (page - 1) * limit
    gens = all_gens[offset : offset + limit]

    return {
        "success": True,
        "data": {
            "generations": [
                {
                    "id": g.id,
                    "type": g.type,
                    "prompt": g.prompt[:100],
                    "cost": g.cost,
                    "status": g.status,
                    "created_at": g.created_at.isoformat(),
                }
                for g in gens
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": max(1, -(-total // limit)),
            },
        },
    }
