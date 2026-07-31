from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.canva_service import CanvaService
from app.services.figma_service import FigmaService

router = APIRouter(prefix="/api/v1/mcp/designs", tags=["Design MCP"])


class FigmaListFilesRequest(BaseModel):
    user_id: str = Field(..., description="User ID associated with the connected Figma account")


class FigmaDesignRequest(BaseModel):
    user_id: str = Field(..., description="User ID associated with the connected Figma account")
    file_key: str = Field(..., description="Figma file key")


class FigmaCreateFileRequest(BaseModel):
    user_id: str = Field(..., description="User ID associated with the connected Figma account")
    name: str = Field(..., description="Name for the new Figma file")


class FigmaExportRequest(BaseModel):
    user_id: str = Field(..., description="User ID associated with the connected Figma account")
    file_key: str = Field(..., description="Figma file key")
    format: str = Field(default="png", description="Export format: png, jpg, svg, or pdf")


class CanvaListDesignsRequest(BaseModel):
    user_id: str = Field(..., description="User ID associated with the connected Canva account")


class CanvaCreateDesignRequest(BaseModel):
    user_id: str = Field(..., description="User ID associated with the connected Canva account")
    title: str = Field(..., description="Title for the new Canva design")
    design_type: str = Field(..., description="One of instagram_post, youtube_thumbnail, logo, poster, presentation, or flyer")


class CanvaExportRequest(BaseModel):
    user_id: str = Field(..., description="User ID associated with the connected Canva account")
    design_id: str = Field(..., description="Canva design id")
    format: str = Field(default="pdf", description="Export format: pdf, png, or jpg")


class CanvaDuplicateRequest(BaseModel):
    user_id: str = Field(..., description="User ID associated with the connected Canva account")
    design_id: str = Field(..., description="Canva design id to duplicate")
    new_title: str = Field(..., description="Title for the duplicated design")


@router.post("/figma/list-files", operation_id="list_figma_files", summary="List Figma files", description="List all Figma files and projects of the connected user. Returns a helpful message if the account is not connected.")
async def list_figma_files(payload: FigmaListFilesRequest):
    return await FigmaService.list_figma_files(payload.user_id)


@router.post("/figma/get-design", operation_id="get_figma_design", summary="Get a Figma design", description="Get the full details of a specific Figma design file including pages and components. Returns a helpful message if the account is not connected.")
async def get_figma_design(payload: FigmaDesignRequest):
    return await FigmaService.get_figma_design(payload.user_id, payload.file_key)


@router.post("/figma/create-file", operation_id="create_figma_file", summary="Create a new Figma file", description="Create a new blank Figma file with the supplied name. Returns a helpful message if the account is not connected.")
async def create_figma_file(payload: FigmaCreateFileRequest):
    return await FigmaService.create_figma_file(payload.user_id, payload.name)


@router.post("/figma/export", operation_id="export_figma_design", summary="Export a Figma design", description="Export a Figma design as png, jpg, svg, or pdf. Returns a helpful message if the account is not connected.")
async def export_figma_design(payload: FigmaExportRequest):
    return await FigmaService.export_figma_design(payload.user_id, payload.file_key, payload.format)


@router.post("/canva/list-designs", operation_id="list_canva_designs", summary="List Canva designs", description="List all Canva designs of the connected user. Returns a helpful message if the account is not connected.")
async def list_canva_designs(payload: CanvaListDesignsRequest):
    return await CanvaService.list_canva_designs(payload.user_id)


@router.post("/canva/create-design", operation_id="create_canva_design", summary="Create a Canva design", description="Create a new Canva design for social media posts, thumbnails, logos, posters, presentations, or flyers. Returns a helpful message if the account is not connected.")
async def create_canva_design(payload: CanvaCreateDesignRequest):
    return await CanvaService.create_canva_design(payload.user_id, payload.title, payload.design_type)


@router.post("/canva/export", operation_id="export_canva_design", summary="Export a Canva design", description="Export a Canva design as pdf, png, or jpg. Returns a helpful message if the account is not connected.")
async def export_canva_design(payload: CanvaExportRequest):
    return await CanvaService.export_canva_design(payload.user_id, payload.design_id, payload.format)


@router.post("/canva/duplicate", operation_id="duplicate_canva_design", summary="Duplicate a Canva design", description="Duplicate a Canva design as a new design that can be edited immediately. Returns a helpful message if the account is not connected.")
async def duplicate_canva_design(payload: CanvaDuplicateRequest):
    return await CanvaService.duplicate_canva_design(payload.user_id, payload.design_id, payload.new_title)
