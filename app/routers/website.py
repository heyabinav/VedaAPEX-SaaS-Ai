from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models.user import User
from app.routers.auth import get_current_user_auth
from app.schemas.website import WebsiteRequirementsRequest, WebsiteRequirementsResponse
from app.services.website_requirement_service import WebsiteRequirementService

router = APIRouter(prefix="/api/website", tags=["Website"])


@router.post("/requirements", response_model=WebsiteRequirementsResponse)
async def submit_website_requirements(
    body: WebsiteRequirementsRequest,
    user: User = Depends(get_current_user_auth),
    session: Session = Depends(get_session),
):
    """Create a website requirements questionnaire and optionally persist it."""
    summary = WebsiteRequirementService.build_summary(body)
    result = {
        "success": True,
        "summary": summary,
        "saved": False,
        "questionnaire_id": None,
    }

    if body.save:
        requirement = WebsiteRequirementService.create_requirement(session, user.id, body)
        result["saved"] = True
        result["questionnaire_id"] = requirement.id

    return result
