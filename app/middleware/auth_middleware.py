from fastapi import Depends, Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.services.auth_service import AuthService

security = HTTPBearer(auto_error=False)


async def authenticate_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session),
) -> User:
    """
    SaaS authentication dependency.
    Validates a backend API key or a Supabase Bearer token.
    """
    return await AuthService.get_authenticated_user(request, credentials, session)


async def authenticate_admin(current_user: User = Depends(authenticate_user)) -> User:
    """
    Access control dependency that ensures the authenticated user is an administrator.
    """
    if current_user.role.upper() != "ADMIN" and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Forbidden. Administrative privileges required.",
        )
    return current_user
