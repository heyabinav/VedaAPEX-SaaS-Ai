import asyncio

from app.services.canva_service import CanvaService
from app.services.figma_service import FigmaService


def test_figma_tool_returns_helpful_error_when_not_connected():
    result = asyncio.run(FigmaService.list_figma_files("missing-user"))
    assert result["success"] is False
    assert "connect" in result["error"].lower()


def test_canva_tool_returns_helpful_error_when_not_connected():
    result = asyncio.run(CanvaService.list_canva_designs("missing-user"))
    assert result["success"] is False
    assert "connect" in result["error"].lower()
