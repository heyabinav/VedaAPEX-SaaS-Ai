import asyncio
import json
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.pool import StaticPool

from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.user import User
from app.services.ai_service import AIToolsService
from app.services.attachments.service import AttachmentService
from app.services.attachments.validator import AttachmentValidationError
from app.services.chat_memory_service import ChatMemoryService
from app.services.image_agent_service import (
    ImageAgentResult,
    ImageAgentService,
    ImageAnalysis,
    ToolDecision,
    ToolExecutionRecord,
)


def _png_bytes(color=(255, 0, 0)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (8, 8), color=color).save(buf, format="PNG")
    return buf.getvalue()


def _image_attachment(name="sample.png") -> dict:
    data = _png_bytes()
    return {
        "id": "att_1",
        "filename": name,
        "mime_type": "image/png",
        "size": len(data),
        "data": data,
        "temp_path": "",
        "path": "",
    }


def test_image_attachment_validation_accepts_real_image():
    upload = UploadFile(filename="ok.png", file=BytesIO(_png_bytes()), headers={"content-type": "image/png"})
    attachments, normalized = asyncio.run(AttachmentService.process([upload], user_id=1))

    assert attachments[0].is_image is True
    assert normalized[0]["mime_type"] == "image/png"
    AttachmentService.cleanup(attachments)


def test_attachment_persistence_adds_durable_asset_metadata(monkeypatch):
    upload = UploadFile(filename="ok.png", file=BytesIO(_png_bytes()), headers={"content-type": "image/png"})

    def fake_upload_asset(session, **kwargs):
        return SimpleNamespace(
            id=77,
            proxy_url="/api/v1/assets/77",
            r2_object_key="users/1/images/ok.png",
            file_hash="abc123",
        )

    monkeypatch.setattr("app.services.attachments.service.asset_storage.upload_asset", fake_upload_asset)

    attachments, normalized = asyncio.run(AttachmentService.process([upload], user_id=1, session=object()))

    assert attachments[0].persisted is True
    assert attachments[0].asset_id == 77
    assert normalized[0]["asset_id"] == 77
    assert normalized[0]["proxy_url"] == "/api/v1/assets/77"
    AttachmentService.cleanup(attachments)


def test_image_attachment_validation_rejects_corrupted_image():
    upload = UploadFile(filename="bad.png", file=BytesIO(b"not an image"), headers={"content-type": "image/png"})

    with pytest.raises(AttachmentValidationError) as exc:
        asyncio.run(AttachmentService.process([upload], user_id=1))

    assert exc.value.code == "CORRUPTED_IMAGE"


def test_vision_capability_detection():
    assert AIToolsService.provider_supports_vision("gemini")
    assert AIToolsService.provider_supports_vision("openrouter", "openai/gpt-4o-mini")
    assert not AIToolsService.provider_supports_vision("groq", "llama3-8b-8192")


def test_text_only_model_rejection_for_image_input():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            ImageAgentService.run(
                message="What is this?",
                attachments=[_image_attachment()],
                context_messages=[],
                model="groq",
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail["error"]["code"] == "MODEL_DOES_NOT_SUPPORT_VISION"


def test_structured_image_analysis_parsing(monkeypatch):
    async def fake_vision_text(**kwargs):
        return json.dumps(
            {
                "summary": "A Next.js error screen.",
                "detected_text": "Module not found",
                "visual_entities": ["browser", "stack trace"],
                "user_intent": "Fix the error",
                "requires_tool": True,
                "suggested_tools": ["web_search"],
                "confidence": 0.91,
            }
        )

    monkeypatch.setattr(AIToolsService, "generate_vision_text", fake_vision_text)

    analysis = asyncio.run(
        ImageAgentService.analyze_image_intent(
            message="Fix this",
            images=[_image_attachment()],
            context_messages=[],
            model="auto",
        )
    )

    assert analysis.summary == "A Next.js error screen."
    assert analysis.suggested_tools == ["web_search"]


def test_tool_selection_from_structured_decision(monkeypatch):
    async def fake_text(**kwargs):
        return '{"requires_tool":true,"tool_name":"web_search","arguments":{"query":"Next.js module not found","num_results":3},"reason":"docs","final_answer_ready":false}'

    monkeypatch.setattr(AIToolsService, "generate_text", fake_text)
    decision = asyncio.run(
        ImageAgentService.decide_next_tool(
            message="Fix this",
            analysis=ImageAnalysis(summary="error", user_intent="debug", requires_tool=True, suggested_tools=["web_search"]),
            tool_calls=[],
            model="auto",
        )
    )

    assert decision.tool_name == "web_search"
    assert decision.arguments["query"] == "Next.js module not found"


def test_blocked_unknown_tool():
    record = asyncio.run(
        ImageAgentService.execute_tool(
            decision=ToolDecision(requires_tool=True, tool_name="shell", arguments={"cmd": "dir"}),
            message="Fix this",
            analysis=ImageAnalysis(summary="error", user_intent="debug", requires_tool=True),
            attachments=[_image_attachment()],
            base_url="http://testserver/",
        )
    )

    assert record.status == "blocked"
    assert record.error == "Tool is not allowed."


def test_successful_web_search_tool_execution(monkeypatch):
    async def fake_search(query, num_results=10, request_type=None):
        return {"provider": "mock", "result_count": 1, "results": [{"title": "Fix", "url": "https://example.com", "snippet": "Use npm install"}]}

    monkeypatch.setattr("app.services.image_agent_service.SearchRouter.search", fake_search)
    record = asyncio.run(
        ImageAgentService.execute_tool(
            decision=ToolDecision(requires_tool=True, tool_name="web_search", arguments={"query": "Next.js error", "num_results": 5}),
            message="Fix this",
            analysis=ImageAnalysis(summary="error", user_intent="debug", requires_tool=True),
            attachments=[_image_attachment()],
            base_url="http://testserver/",
        )
    )

    assert record.status == "success"
    assert record.result["provider"] == "mock"


def test_tool_failure_is_sanitized(monkeypatch):
    async def fake_search(*args, **kwargs):
        raise RuntimeError("secret stack trace")

    monkeypatch.setattr("app.services.image_agent_service.SearchRouter.search", fake_search)
    record = asyncio.run(
        ImageAgentService.execute_tool(
            decision=ToolDecision(requires_tool=True, tool_name="web_search", arguments={"query": "x"}),
            message="Find info",
            analysis=ImageAnalysis(summary="x", user_intent="search", requires_tool=True),
            attachments=[_image_attachment()],
            base_url="http://testserver/",
        )
    )

    assert record.status == "failed"
    assert record.error == "Tool execution failed."


def test_multiple_images_are_sent_together(monkeypatch):
    captured = {}

    async def fake_vision_text(**kwargs):
        captured["count"] = len(kwargs["images"])
        return '{"summary":"two images","user_intent":"compare","requires_tool":false}'

    monkeypatch.setattr(AIToolsService, "generate_vision_text", fake_vision_text)
    analysis = asyncio.run(
        ImageAgentService.analyze_image_intent(
            message="Compare these",
            images=[_image_attachment("one.png"), _image_attachment("two.png")],
            context_messages=[],
            model="auto",
        )
    )

    assert captured["count"] == 2
    assert analysis.summary == "two images"


def test_maximum_tool_iterations(monkeypatch):
    monkeypatch.setattr("app.services.image_agent_service.settings.AI_MAX_TOOL_ITERATIONS", 2)

    async def fake_analyze(**kwargs):
        return ImageAnalysis(summary="needs search", user_intent="search", requires_tool=True, suggested_tools=["web_search"])

    async def fake_decide(**kwargs):
        return ToolDecision(requires_tool=True, tool_name="web_search", arguments={"query": "x"})

    async def fake_execute(**kwargs):
        return ToolExecutionRecord(tool_name="web_search", arguments={"query": "x"}, status="success", result={"results": []})

    async def fake_final(**kwargs):
        return "done"

    monkeypatch.setattr(ImageAgentService, "analyze_image_intent", fake_analyze)
    monkeypatch.setattr(ImageAgentService, "decide_next_tool", fake_decide)
    monkeypatch.setattr(ImageAgentService, "execute_tool", fake_execute)
    monkeypatch.setattr(ImageAgentService, "final_answer", fake_final)

    result = asyncio.run(ImageAgentService.run(message="Find this", attachments=[_image_attachment()], context_messages=[], model="auto"))

    assert len(result.tool_calls) == 2
    assert result.max_iterations_reached is True


def test_final_answer_generation(monkeypatch):
    async def fake_vision_text(**kwargs):
        assert "Tool calls" in kwargs["prompt"]
        return "The screenshot shows a missing module. Install the dependency."

    monkeypatch.setattr(AIToolsService, "generate_vision_text", fake_vision_text)
    answer = asyncio.run(
        ImageAgentService.final_answer(
            message="Fix this",
            images=[_image_attachment()],
            analysis=ImageAnalysis(summary="missing module", user_intent="debug"),
            tool_calls=[],
            context_messages=[],
            model="auto",
            max_iterations_reached=False,
        )
    )

    assert "missing module" in answer


def test_no_vision_provider_fallback_error(monkeypatch):
    monkeypatch.setattr(AIToolsService, "get_vision_provider_candidates", lambda preferred_provider=None: [])

    with pytest.raises(RuntimeError):
        asyncio.run(
            AIToolsService.generate_vision_text(
                prompt="x",
                system_prompt=None,
                images=[_image_attachment()],
                provider="auto",
            )
        )


def test_pdf_report_tool_execution(monkeypatch):
    async def fake_generate_pdf(**kwargs):
        assert kwargs["attachments"]
        return "http://testserver/static/report.pdf"

    monkeypatch.setattr("app.services.image_agent_service.DocumentService.generate_pdf", fake_generate_pdf)
    record = asyncio.run(
        ImageAgentService.execute_tool(
            decision=ToolDecision(requires_tool=True, tool_name="pdf_report", arguments={"prompt": "Create report"}),
            message="Create a PDF report from this",
            analysis=ImageAnalysis(summary="chart", user_intent="report", requires_tool=True),
            attachments=[_image_attachment()],
            base_url="http://testserver/",
        )
    )

    assert record.status == "success"
    assert record.result["url"].endswith("report.pdf")


def test_streaming_request_with_image_preserves_existing_non_stream_contract(monkeypatch):
    metadata = ImageAgentService.metadata(
        ImageAgentResult(
            final_answer="answer",
            image_analysis=ImageAnalysis(summary="image", user_intent="answer"),
            tool_calls=[],
        ),
        [_image_attachment()],
    )

    assert metadata["multimodal"] is True
    assert "stream" not in metadata


def test_history_persistence_for_image_agent(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)

    async def fake_run(**kwargs):
        return ImageAgentResult(
            final_answer="Final image answer",
            image_analysis=ImageAnalysis(summary="image summary", user_intent="answer"),
            tool_calls=[
                ToolExecutionRecord(
                    tool_name="web_search",
                    arguments={"query": "image"},
                    status="success",
                    result={"results": []},
                )
            ],
        )

    async def noop_async(*args, **kwargs):
        return {}

    monkeypatch.setattr(ImageAgentService, "run", fake_run)
    monkeypatch.setattr("app.services.chat_memory_service.SupabaseService.get_user_profile_facts", noop_async)
    monkeypatch.setattr("app.services.chat_memory_service.ChatMemoryService.load_memory_facts_from_supabase", noop_async)
    monkeypatch.setattr("app.services.chat_memory_service.ChatMemoryService.save_memory_facts_to_supabase", noop_async)
    monkeypatch.setattr("app.services.chat_memory_service.HFChatStorageService.sync_session", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.services.chat_memory_service.RedisChatMemory.save_message", noop_async)
    monkeypatch.setattr("app.services.chat_memory_service.RedisChatMemory.restore_from_database", noop_async)

    with Session(engine) as session:
        user = User(email="test@example.com", full_name="Test User", hashed_password="x")
        session.add(user)
        session.commit()
        session.refresh(user)

        result = asyncio.run(
            ChatMemoryService.ask(
                session=session,
                user=user,
                session_id=None,
                message="What is this?",
                model="auto",
                attachments=[_image_attachment()],
                base_url="http://testserver/",
            )
        )

        messages = session.exec(select(ChatMessage).where(ChatMessage.session_id == result["session_id"])).all()
        assistant = next(msg for msg in messages if msg.role == "assistant")
        metadata = json.loads(assistant.metadata_json)

    assert result["answer"] == "Final image answer"
    assert metadata["multimodal"] is True
    assert metadata["image_analysis"]["summary"] == "image summary"
    assert metadata["tool_calls"][0]["tool_name"] == "web_search"
