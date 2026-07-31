"""
Repository pattern for AI Asset database operations.
"""

from typing import Optional

from sqlmodel import Session, select, func

from app.models.asset import AIAsset


class AssetRepository:
    """Data access layer for AI assets."""

    @staticmethod
    def get_by_id(session: Session, asset_id: int) -> Optional[AIAsset]:
        return session.get(AIAsset, asset_id)

    @staticmethod
    def get_by_user(
        session: Session,
        user_id: int,
        asset_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[AIAsset], int]:
        query = select(AIAsset).where(AIAsset.user_id == user_id)
        if asset_type:
            query = query.where(AIAsset.asset_type == asset_type)
        query = query.order_by(AIAsset.created_at.desc())

        all_assets = session.exec(query).all()
        total = len(all_assets)
        offset = (page - 1) * limit
        return all_assets[offset: offset + limit], total

    @staticmethod
    def get_by_hash(session: Session, file_hash: str) -> Optional[AIAsset]:
        return session.exec(
            select(AIAsset).where(AIAsset.file_hash == file_hash)
        ).first()

    @staticmethod
    def count_by_type(session: Session) -> dict:
        stats = session.exec(
            select(AIAsset.asset_type, func.count(AIAsset.id)).group_by(AIAsset.asset_type)
        ).all()
        return {t: c for t, c in stats}

    @staticmethod
    def total_size(session: Session) -> int:
        result = session.exec(select(func.sum(AIAsset.file_size_bytes))).one()
        return result or 0

    @staticmethod
    def count_all(session: Session) -> int:
        return session.exec(select(func.count(AIAsset.id))).one() or 0

    @staticmethod
    def delete(session: Session, asset: AIAsset) -> bool:
        try:
            session.delete(asset)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False
