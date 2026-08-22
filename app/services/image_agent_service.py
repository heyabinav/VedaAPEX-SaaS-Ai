from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import settings
from app.services.ai_service import AIToolsService
from app.services.document_service import DocumentService
from app.services.search_router import SearchRouter

logger = logging.getLogger("services.image_agent_service")


class ImageAnalysis(BaseModel):
    summary: str = Field(min_length=1)
    detected_text: str | None = None
    visual_entities: list[str] = Field(default_factory=list)
    user_intent: str = Field(min_length=1)
    requires_tool: bool = False
    suggested_tools: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("suggested_tools", "visual_entities", mode="before")
    @classmethod
    def _coerce_string_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []


class ToolDecision(BaseModel):
    requires_tool: bool = False
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    final_answer_ready: bool = False


class ToolExecutionRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    status: Literal["success", "blocked", "failed"]
    result: Any = None
    error: str | None = None


class ImageAgentResult(BaseModel):
    final_answer: str
    image_analysis: ImageAnalysis
    tool_calls: list[ToolExecutionRecord] = Field(default_factory=list)
    status: str = "success"
    provider: str | None = None
    model: str | None = None
    max_iterations_reached: bool = False


class ImageAgentService:
    ALLOWED_TOOLS = {"web_search", "pdf_report"}
    MAX_TOOL_RESULT_CHARS = 6000

    @staticmethod
    def _image_attachments(attachments: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        images: list[dict[str, Any]] = []
        for item in attachments or []:
            if str(item.get("mime_type") or "").startswith("image/"):
                images.append(item)
        return images

    @staticmethod
    def has_image_attachments(attachments: list[dict[str, Any]] | None) -> bool:
        return bool(ImageAgentService._image_attachments(attachments))

    @staticmethod
    def _sanitize_attachments(attachments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": item.get("id"),
                "asset_id": item.get("asset_id"),
                "filename": item.get("filename"),
                "mime_type": item.get("mime_type"),
                "size": item.get("size"),
                "proxy_url": item.get("proxy_url"),
                "storage_key": item.get("storage_key"),
                "file_hash": item.get("file_hash"),
                "persistent": bool(item.get("persistent")),
            }
            for item in attachments
        ]

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any]:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                return json.loads(cleaned[start : end + 1])
            raise

    @staticmethod
    def _sanitize_tool_args(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "web_search":
            query = str(arguments.get("query") or "").strip()
            num_results = arguments.get("num_results", 5)
            try:
                num_results = int(num_results)
            except (TypeError, ValueError):
                num_results = 5
            return {"query": query[:300], "num_results": max(1, min(num_results, 10))}

        if tool_name == "pdf_report":
            title = str(arguments.get("title") or "Image Analysis Report").strip()[:120]
            prompt = str(arguments.get("prompt") or "").strip()[:2000]
            return {"title": title, "prompt": prompt}

        return {}

    @staticmethod
    def _sanitize_tool_result(result: Any) -> Any:
        if result is None:
            return None
        if isinstance(result, str):
            return result[: ImageAgentService.MAX_TOOL_RESULT_CHARS]
        if isinstance(result, list):
            return [ImageAgentService._sanitize_tool_result(item) for item in result[:10]]
        if isinstance(result, dict):
            sanitized: dict[str, Any] = {}
            for key, value in result.items():
                if str(key).lower() in {"api_key", "authorization", "token", "secret"}:
                    continue
                sanitized[key] = ImageAgentService._sanitize_tool_result(value)
            return sanitized
        return result

    @staticmethod
    async def analyze_image_intent(
        *,
        message: str,
        images: list[dict[str, Any]],
        context_messages: list[dict[str, str]] | None,
        model: str,
    ) -> ImageAnalysis:
        context = ""
        if context_messages:
            context = "\n".join(
                f"{item.get('role')}: {item.get('content')}" for item in context_messages[-6:]
            )

        prompt = (
            "Analyze the attached image(s) together with the user message. "
            "Return only a JSON object with these keys: summary, detected_text, "
            "visual_entities, user_intent, requires_tool, suggested_tools, confidence.\n\n"
            "Allowed suggested_tools are web_search and pdf_report. Suggest a tool only when it is necessary "
            "for the user's intent; simple image description, OCR, and chart Q&A usually do not need a tool.\n\n"
            f"Conversation context:\n{context or 'None'}\n\nUser message:\n{message}"
        )
        system_prompt = (
            "You are a careful multimodal analysis model. Separate visible facts, OCR text, "
            "user intent, and external tool needs. Do not invent details not visible in the images."
        )
        try:
            raw = await AIToolsService.generate_vision_text(
                prompt=prompt,
                system_prompt=system_prompt,
                images=images,
                provider=model or "auto",
                tier=1,
                response_mime_type="application/json",
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            logger.warning("Vision analysis provider unavailable: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="No vision-capable AI provider is currently available. Configure VISION_PROVIDER/VISION_MODEL with a valid backend API key.",
            ) from exc
        try:
            return ImageAnalysis.model_validate(ImageAgentService._extract_json_object(raw))
        except (ValidationError, json.JSONDecodeError, TypeError) as exc:
            logger.warning("Invalid structured image analysis response: %s", exc)
            fallback_summary = re.sub(r"\s+", " ", raw or "").strip()[:1000]
            return ImageAnalysis(
                summary=fallback_summary or "The image was analyzed, but the structured response was incomplete.",
                detected_text=None,
                visual_entities=[],
                user_intent=message,
                requires_tool=False,
                suggested_tools=[],
                confidence=None,
            )

    @staticmethod
    async def decide_next_tool(
        *,
        message: str,
        analysis: ImageAnalysis,
        tool_calls: list[ToolExecutionRecord],
        model: str,
    ) -> ToolDecision:
        if not analysis.requires_tool and not analysis.suggested_tools:
            return ToolDecision(requires_tool=False, final_answer_ready=True)

        prompt = (
            "Decide the next backend tool call for this image-aware user request. "
            "Return only JSON with keys: requires_tool, tool_name, arguments, reason, final_answer_ready.\n"
            f"Allowed tools: {sorted(ImageAgentService.ALLOWED_TOOLS)}.\n"
            "Use web_search only for current/external information, docs, product lookup, or web verification. "
            "Use pdf_report only when the user explicitly asks to create a PDF/report/document from the image. "
            "If no more tools are needed, set requires_tool=false and final_answer_ready=true.\n\n"
            f"User message: {message}\n"
            f"Image analysis: {analysis.model_dump_json()}\n"
            f"Prior tool calls: {[record.model_dump() for record in tool_calls]}"
        )
        raw = await AIToolsService.generate_text(
            prompt=prompt,
            system_prompt="You are a secure tool router. Never request arbitrary code, shell, filesystem, database, or unlisted tools.",
            tier=1,
            provider=model or "auto",
        )
        try:
            return ToolDecision.model_validate(ImageAgentService._extract_json_object(str(raw)))
        except Exception:
            for suggested in analysis.suggested_tools:
                if suggested in ImageAgentService.ALLOWED_TOOLS:
                    if suggested == "web_search":
                        query = analysis.detected_text or analysis.summary or message
                        return ToolDecision(
                            requires_tool=True,
                            tool_name="web_search",
                            arguments={"query": query, "num_results": 5},
                            reason="Fallback to validated suggested web_search.",
                        )
                    if suggested == "pdf_report" and "pdf" in message.lower():
                        return ToolDecision(
                            requires_tool=True,
                            tool_name="pdf_report",
                            arguments={"prompt": f"{message}\n\nImage analysis: {analysis.summary}"},
                            reason="Fallback to validated suggested pdf_report.",
                        )
            return ToolDecision(requires_tool=False, final_answer_ready=True)

    @staticmethod
    async def execute_tool(
        *,
        decision: ToolDecision,
        message: str,
        analysis: ImageAnalysis,
        attachments: list[dict[str, Any]],
        base_url: str | None,
    ) -> ToolExecutionRecord:
        tool_name = (decision.tool_name or "").strip()
        if not decision.requires_tool:
            return ToolExecutionRecord(tool_name=tool_name or "none", arguments={}, status="blocked", error="No tool requested.")
        if tool_name not in ImageAgentService.ALLOWED_TOOLS:
            return ToolExecutionRecord(
                tool_name=tool_name or "unknown",
                arguments={},
                status="blocked",
                error="Tool is not allowed.",
            )

        args = ImageAgentService._sanitize_tool_args(tool_name, decision.arguments)
        try:
            if tool_name == "web_search":
                query = args.get("query") or analysis.detected_text or analysis.summary or message
                if not query:
                    return ToolExecutionRecord(tool_name=tool_name, arguments=args, status="blocked", error="Missing search query.")
                result = await SearchRouter.search(query=query, num_results=args["num_results"])
                return ToolExecutionRecord(
                    tool_name=tool_name,
                    arguments={**args, "query": query[:300]},
                    status="success",
                    result=ImageAgentService._sanitize_tool_result(result),
                )

            if tool_name == "pdf_report":
                if "pdf" not in message.lower() and "report" not in message.lower() and "document" not in message.lower():
                    return ToolExecutionRecord(
                        tool_name=tool_name,
                        arguments=args,
                        status="blocked",
                        error="PDF/report tool requires an explicit document generation request.",
                    )
                prompt = args.get("prompt") or f"{message}\n\nImage analysis:\n{analysis.model_dump_json()}"
                result = await DocumentService.generate_pdf(
                    prompt=prompt,
                    base_url=base_url or settings.get_app_base_url(),
                    provider="auto",
                    tier=1,
                    attachments=attachments,
                )
                return ToolExecutionRecord(
                    tool_name=tool_name,
                    arguments=args,
                    status="success",
                    result=ImageAgentService._sanitize_tool_result({"url": result}),
                )
        except Exception as exc:
            logger.warning("Image-agent tool %s failed: %s", tool_name, exc)
            return ToolExecutionRecord(
                tool_name=tool_name,
                arguments=args,
                status="failed",
                error="Tool execution failed.",
            )

        return ToolExecutionRecord(tool_name=tool_name, arguments=args, status="blocked", error="Tool unavailable.")

    @staticmethod
    async def final_answer(
        *,
        message: str,
        images: list[dict[str, Any]],
        analysis: ImageAnalysis,
        tool_calls: list[ToolExecutionRecord],
        context_messages: list[dict[str, str]] | None,
        model: str,
        max_iterations_reached: bool,
    ) -> str:
        prompt = (
            "Answer the user's request using the image analysis and any tool results. "
            "Do not mention internal tool routing unless it is relevant to the answer. "
            "If a tool failed, give the best useful answer from the image and say what could not be verified.\n\n"
            f"User message: {message}\n"
            f"Image analysis: {analysis.model_dump_json()}\n"
            f"Tool calls: {[record.model_dump() for record in tool_calls]}\n"
            f"Maximum tool iterations reached: {max_iterations_reached}\n"
            f"Recent context: {context_messages[-6:] if context_messages else []}"
        )
        system_prompt = (
            "You are ApexVision. Give one natural-language final answer grounded in the attached image(s), "
            "conversation context, and sanitized tool observations."
        )
        try:
            answer = await AIToolsService.generate_vision_text(
                prompt=prompt,
                system_prompt=system_prompt,
                images=images,
                provider=model or "auto",
                tier=1,
            )
        except Exception as exc:
            logger.warning("Vision final-answer provider unavailable: %s", exc)
            raise HTTPException(
                status_code=503,
                detail="Vision final reasoning is currently unavailable. Please try again later.",
            ) from exc
        return str(answer or "").strip() or "I analyzed the image, but I could not generate a final answer."

    @staticmethod
    async def run(
        *,
        message: str,
        attachments: list[dict[str, Any]],
        context_messages: list[dict[str, str]] | None,
        model: str = "auto",
        base_url: str | None = None,
    ) -> ImageAgentResult:
        images = ImageAgentService._image_attachments(attachments)
        if not images:
            raise ValueError("ImageAgentService requires at least one image attachment.")

        if model and model != "auto" and not AIToolsService.provider_supports_vision(model, model):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "MODEL_DOES_NOT_SUPPORT_VISION",
                        "message": "The selected model does not support image analysis.",
                    },
                },
            )

        analysis = await ImageAgentService.analyze_image_intent(
            message=message,
            images=images,
            context_messages=context_messages,
            model=model,
        )

        tool_calls: list[ToolExecutionRecord] = []
        max_iterations = max(0, min(int(getattr(settings, "AI_MAX_TOOL_ITERATIONS", 5)), 10))
        max_iterations_reached = False

        for _ in range(max_iterations):
            decision = await ImageAgentService.decide_next_tool(
                message=message,
                analysis=analysis,
                tool_calls=tool_calls,
                model=model,
            )
            if not decision.requires_tool:
                break
            record = await ImageAgentService.execute_tool(
                decision=decision,
                message=message,
                analysis=analysis,
                attachments=attachments,
                base_url=base_url,
            )
            tool_calls.append(record)
            if record.status != "success":
                break
        else:
            max_iterations_reached = bool(max_iterations)

        answer = await ImageAgentService.final_answer(
            message=message,
            images=images,
            analysis=analysis,
            tool_calls=tool_calls,
            context_messages=context_messages,
            model=model,
            max_iterations_reached=max_iterations_reached,
        )
        return ImageAgentResult(
            final_answer=answer,
            image_analysis=analysis,
            tool_calls=tool_calls,
            provider=model or "auto",
            max_iterations_reached=max_iterations_reached,
        )

    @staticmethod
    def metadata(result: ImageAgentResult, attachments: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "multimodal": True,
            "attachments": ImageAgentService._sanitize_attachments(attachments),
            "image_analysis": result.image_analysis.model_dump(),
            "tool_calls": [record.model_dump() for record in result.tool_calls],
            "status": result.status,
            "max_iterations_reached": result.max_iterations_reached,
            "provider": result.provider,
            "model": result.model,
        }
