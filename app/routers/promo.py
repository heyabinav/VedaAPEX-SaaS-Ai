from utils.time import utcnow

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.user import User
from app.models.token import PromoCode, PromoCodeUsage
from app.routers.auth import get_current_user_auth
from app.routers.admin import admin_only
from app.services.token_service import TokenService
from datetime import datetime

router = APIRouter(prefix="/promo", tags=["Promo Codes"])


@router.post("/redeem")
async def redeem_promo(
    request: Request,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    body = await request.json()
    code = body.get("code", "").upper()
    if not code:
        raise HTTPException(status_code=400, detail="Promo code is required.")

    promo = session.exec(select(PromoCode).where(PromoCode.code == code)).first()
    if not promo:
        raise HTTPException(status_code=404, detail="Invalid promo code.")
    if not promo.is_active:
        raise HTTPException(status_code=400, detail="Promo code inactive.")
    if promo.expires_at and promo.expires_at < utcnow():
        raise HTTPException(status_code=400, detail="Promo code expired.")
    if promo.current_uses >= promo.max_uses:
        raise HTTPException(status_code=400, detail="Promo code usage limit reached.")

    existing = session.exec(
        select(PromoCodeUsage).where(
            PromoCodeUsage.user_id == user.id, PromoCodeUsage.promo_code_id == promo.id
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already used this promo code.")

    promo.current_uses += 1
    session.add(promo)
    usage = PromoCodeUsage(user_id=user.id, promo_code_id=promo.id, credits_awarded=promo.credits)
    session.add(usage)
    session.commit()

    wallet = TokenService.add_credits(
        session,
        user.id,
        promo.credits,
        tx_type="PROMO_CODE",
        description=f"Promo {code}: +{promo.credits} credits",
        ip_address=request.client.host,
    )
    return {
        "success": True,
        "message": f"+{promo.credits} credits!",
        "data": {"credits_awarded": promo.credits, "balance": wallet.balance},
    }


@router.post("/create")
async def create_promo(
    request: Request,
    admin: User = Depends(admin_only),
    session: Session = Depends(get_session),
):
    body = await request.json()
    promo = PromoCode(
        code=body["code"].upper(),
        credits=int(body["credits"]),
        max_uses=int(body.get("max_uses", 100)),
        expires_at=(datetime.fromisoformat(body["expires_at"]) if body.get("expires_at") else None),
    )
    session.add(promo)
    session.commit()
    session.refresh(promo)
    return {
        "success": True,
        "data": {"id": promo.id, "code": promo.code, "credits": promo.credits},
    }


@router.get("/list")
async def list_promos(admin: User = Depends(admin_only), session: Session = Depends(get_session)):
    promos = session.exec(select(PromoCode).order_by(PromoCode.created_at.desc())).all()
    return {
        "success": True,
        "data": [
            {
                "id": p.id,
                "code": p.code,
                "credits": p.credits,
                "max_uses": p.max_uses,
                "current_uses": p.current_uses,
                "is_active": p.is_active,
            }
            for p in promos
        ],
    }