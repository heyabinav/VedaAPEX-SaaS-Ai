from utils.time import utcnow

import json
from datetime import datetime
from sqlmodel import Session, select
from app.models.token import TokenWallet, TokenTransaction
from app.config.costs import SIGNUP_BONUS_CREDITS


class TokenService:
    """Atomic token wallet operations — all credit changes go through here."""

    @staticmethod
    def get_balance(session: Session, user_id: int) -> TokenWallet:
        wallet = session.exec(select(TokenWallet).where(TokenWallet.user_id == user_id)).first()
        if not wallet:
            raise ValueError("Wallet not found")
        return wallet

    @staticmethod
    def deduct_credits(
        session: Session,
        user_id: int,
        amount: int,
        tx_type: str = "USAGE",
        description: str = None,
        ip_address: str = None,
    ) -> TokenWallet:
        wallet = session.exec(select(TokenWallet).where(TokenWallet.user_id == user_id)).first()
        if not wallet:
            raise ValueError("Wallet not found")
        if wallet.balance < amount:
            raise ValueError("INSUFFICIENT_CREDITS")

        new_balance = wallet.balance - amount
        wallet.balance = new_balance
        wallet.lifetime_spent += amount
        wallet.updated_at = utcnow()
        session.add(wallet)

        tx = TokenTransaction(
            user_id=user_id,
            amount=-amount,
            type=tx_type,
            description=description,
            balance_after=new_balance,
            ip_address=ip_address,
            created_at=utcnow(),
        )
        session.add(tx)
        session.commit()
        session.refresh(wallet)
        return wallet

    @staticmethod
    def add_credits(
        session: Session,
        user_id: int,
        amount: int,
        tx_type: str = "PURCHASE",
        description: str = None,
        ip_address: str = None,
        metadata: dict = None,
    ) -> TokenWallet:
        wallet = session.exec(select(TokenWallet).where(TokenWallet.user_id == user_id)).first()
        if not wallet:
            raise ValueError("Wallet not found")

        new_balance = wallet.balance + amount
        wallet.balance = new_balance
        wallet.lifetime_earned += amount
        wallet.updated_at = utcnow()
        session.add(wallet)

        tx = TokenTransaction(
            user_id=user_id,
            amount=amount,
            type=tx_type,
            description=description,
            balance_after=new_balance,
            ip_address=ip_address,
            metadata_json=json.dumps(metadata) if metadata else None,
            created_at=utcnow(),
        )
        session.add(tx)
        session.commit()
        session.refresh(wallet)
        return wallet

    @staticmethod
    def create_wallet(session: Session, user_id: int, initial_balance: int = None) -> TokenWallet:
        bonus = initial_balance if initial_balance is not None else SIGNUP_BONUS_CREDITS

        wallet = TokenWallet(
            user_id=user_id,
            balance=bonus,
            lifetime_earned=bonus,
            updated_at=utcnow(),
        )
        session.add(wallet)

        tx = TokenTransaction(
            user_id=user_id,
            amount=bonus,
            type="SIGNUP_BONUS",
            description=f"Welcome bonus: {bonus} credits",
            balance_after=bonus,
            created_at=utcnow(),
        )
        session.add(tx)
        session.commit()
        session.refresh(wallet)
        return wallet

    @staticmethod
    def get_transactions(
        session: Session,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        tx_type: str = None,
    ) -> dict:
        query = select(TokenTransaction).where(TokenTransaction.user_id == user_id)
        if tx_type:
            query = query.where(TokenTransaction.type == tx_type)
        query = query.order_by(TokenTransaction.created_at.desc())

        total_q = select(TokenTransaction).where(TokenTransaction.user_id == user_id)
        if tx_type:
            total_q = total_q.where(TokenTransaction.type == tx_type)
        total = len(session.exec(total_q).all())

        offset = (page - 1) * limit
        transactions = session.exec(query.offset(offset).limit(limit)).all()

        return {
            "transactions": [
                {
                    "id": t.id,
                    "amount": t.amount,
                    "type": t.type,
                    "description": t.description,
                    "balance_after": t.balance_after,
                    "created_at": t.created_at.isoformat(),
                }
                for t in transactions
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": max(1, -(-total // limit)),
            },
        }