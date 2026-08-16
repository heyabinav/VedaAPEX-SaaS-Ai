"""
PowerPoint presentation service initialization and public API.
"""

from app.schemas.presentations import PresentationPlan
from app.services.ppt.generator import PPTGenerator

__all__ = ["PPTGenerator", "generate_pptx"]


def generate_pptx(presentation_plan: PresentationPlan) -> bytes:
    """
    Generate a PowerPoint file from a validated presentation plan.
    
    Args:
        presentation_plan: Validated PresentationPlan containing slides and metadata
        
    Returns:
        Binary PPTX file as bytes
        
    Raises:
        ValueError: If presentation plan is invalid
        Exception: If PPTX generation fails
    """
    generator = PPTGenerator(presentation_plan)
    return generator.generate()
