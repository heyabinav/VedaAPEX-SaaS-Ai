import json
from sqlmodel import Session

from app.models.website_requirement import WebsiteRequirement
from app.schemas.website import WebsiteRequirementsRequest


class WebsiteRequirementService:
    @staticmethod
    def _serialize_strings(values: list[str]) -> str:
        filtered = [value.strip() for value in values if value and value.strip()]
        return json.dumps(filtered, ensure_ascii=False)

    @staticmethod
    def _format_list(values: list[str]) -> str:
        filtered = [value.strip() for value in values if value and value.strip()]
        if not filtered:
            return "None provided"
        return "\n".join(f"- {item}" for item in filtered)

    @staticmethod
    def build_summary(body: WebsiteRequirementsRequest) -> str:
        lines: list[str] = [f"Business Name: {body.business_name}"]

        if body.website_type:
            lines.append(f"Website Type: {body.website_type}")
        if body.target_audience:
            lines.append(f"Target Audience: {body.target_audience}")

        lines.append("Primary Objectives:")
        lines.append(WebsiteRequirementService._format_list(body.primary_objectives))

        lines.append("Desired Features:")
        lines.append(WebsiteRequirementService._format_list(body.desired_features))

        lines.append("Content Pages:")
        lines.append(WebsiteRequirementService._format_list(body.content_pages))

        if body.preferred_style:
            lines.append(f"Preferred Style: {body.preferred_style}")
        if body.budget:
            lines.append(f"Budget: {body.budget}")
        if body.launch_timeline:
            lines.append(f"Launch Timeline: {body.launch_timeline}")
        if body.additional_notes:
            lines.append(f"Additional Notes: {body.additional_notes}")

        return "\n".join(lines)

    @staticmethod
    def create_requirement(
        session: Session,
        user_id: int,
        body: WebsiteRequirementsRequest,
    ) -> WebsiteRequirement:
        entry = WebsiteRequirement(
            user_id=user_id,
            business_name=body.business_name,
            website_type=body.website_type,
            target_audience=body.target_audience,
            primary_objectives_json=WebsiteRequirementService._serialize_strings(body.primary_objectives),
            desired_features_json=WebsiteRequirementService._serialize_strings(body.desired_features),
            content_pages_json=WebsiteRequirementService._serialize_strings(body.content_pages),
            preferred_style=body.preferred_style,
            budget=body.budget,
            launch_timeline=body.launch_timeline,
            additional_notes=body.additional_notes,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)
        return entry
