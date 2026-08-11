from typing import List, Optional

from pydantic import BaseModel, Field


class WebsiteRequirementsRequest(BaseModel):
    business_name: str = Field(..., min_length=1, description="Business or brand name")
    website_type: Optional[str] = Field(default=None, description="Type of website (e.g. landing page, e-commerce, portfolio)")
    target_audience: Optional[str] = Field(default=None, description="Primary audience or customer segments")
    primary_objectives: List[str] = Field(default_factory=list, description="Main goals or objectives for the website")
    desired_features: List[str] = Field(default_factory=list, description="Features or functionality required")
    content_pages: List[str] = Field(default_factory=list, description="Pages or sections the website should include")
    preferred_style: Optional[str] = Field(default=None, description="Design style or branding guidance")
    budget: Optional[str] = Field(default=None, description="Planned budget or pricing expectations")
    launch_timeline: Optional[str] = Field(default=None, description="Expected launch timeframe")
    additional_notes: Optional[str] = Field(default=None, description="Any extra details or preferences")
    save: bool = Field(default=False, description="If true, persist the questionnaire response to the database")


class WebsiteRequirementsResponse(BaseModel):
    success: bool = True
    summary: str
    questionnaire_id: Optional[int] = None
    saved: bool = False
