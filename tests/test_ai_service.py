import asyncio
from io import BytesIO

import pytest
from PIL import Image

from app.services.ai_service import AIToolsService


def test_generate_text_with_huggingface_space(monkeypatch):
    async def fake_run_model(model, input_data, starting_tier=1):
        assert model == "CohereLabs/c4ai-command"
        assert "messages" in input_data
        assert input_data["messages"][-1]["content"] == "Hello"
        return {"choices": [{"message": {"content": "Response from CohereLabs c4ai-command"}}]}

    monkeypatch.setattr(
        "app.services.ai_service.HuggingFaceProvider.run_model",
        fake_run_model,
    )

    result = asyncio.run(
        AIToolsService.generate_text(
            prompt="Hello",
            system_prompt="You are a helpful assistant.",
            tier=1,
            provider="CohereLabs/c4ai-command",
        )
    )

    assert result == "Response from CohereLabs c4ai-command"


def test_generate_text_falls_back_to_another_provider_when_auto_provider_fails(monkeypatch):
    async def fake_free_run_model(*args, **kwargs):
        return {"choices": [{"message": {"content": "Recovered response"}}]}

    async def fake_replicate_run_model(*args, **kwargs):
        raise RuntimeError("replicate down")

    monkeypatch.setattr(
        "app.services.ai_service.FreeProvider.run_model",
        fake_free_run_model,
    )
    monkeypatch.setattr(
        "app.services.ai_service.ReplicateProvider.run_model",
        fake_replicate_run_model,
    )

    result = asyncio.run(
        AIToolsService.generate_text(
            prompt="Hello",
            system_prompt="You are a helpful assistant.",
            tier=1,
            provider="auto",
        )
    )

    assert result == "Recovered response"


def test_generate_text_handles_missing_provider_value(monkeypatch):
    async def fake_free_run_model(*args, **kwargs):
        return {"choices": [{"message": {"content": "Recovered response"}}]}

    monkeypatch.setattr(
        "app.services.ai_service.FreeProvider.run_model",
        fake_free_run_model,
    )

    result = asyncio.run(
        AIToolsService.generate_text(
            prompt="Hello",
            system_prompt="You are a helpful assistant.",
            tier=1,
            provider=None,
        )
    )

    assert result == "Recovered response"


def test_generate_text_returns_fallback_when_provider_fails(monkeypatch):
    async def fake_run_model(*args, **kwargs):
        raise RuntimeError("provider down")

    monkeypatch.setattr(
        "app.services.ai_service.ReplicateProvider.run_model",
        fake_run_model,
    )

    result = asyncio.run(
        AIToolsService.generate_text(
            prompt="Hello",
            system_prompt="You are a helpful assistant.",
            tier=1,
            provider="replicate",
        )
    )

    assert "unable to reach the text generation service" in result.lower()


def test_generate_image_with_piapi_provider(monkeypatch):
    async def fake_generate_image(prompt, tier, aspect_ratio):
        assert prompt == "car"
        assert aspect_ratio == "1:1"
        return "https://example.com/car.png"

    monkeypatch.setattr(
        "app.services.ai_service.PiAPIProvider.generate_image",
        fake_generate_image,
    )

    result = asyncio.run(
        AIToolsService.generate_image(
            prompt="car",
            aspect_ratio="1:1",
            num_outputs=1,
            tier=1,
            provider="piapi",
        )
    )

    assert result == ["https://example.com/car.png"]


def test_is_true_exhaustion_error_matches_real_exhaustion_signals():
    from app.routers.ai_tools import _is_true_exhaustion_error

    assert not _is_true_exhaustion_error("All providers failed for image. Last error: ...")
    assert _is_true_exhaustion_error("All free providers failed due to rate limits")
    assert _is_true_exhaustion_error("All premium providers failed: last error 429")
    assert _is_true_exhaustion_error("All platforms failed")
    assert _is_true_exhaustion_error("All tiers exhausted")


def test_text_generation_invalid_output_raises_service_unavailable(monkeypatch):
    async def fake_run_model(*args, **kwargs):
        return "I’m currently unable to reach the text generation service, so I’m returning a short fallback response."

    monkeypatch.setattr(
        "app.services.ai_service.ReplicateProvider.run_model",
        fake_run_model,
    )

    from app.routers.ai_tools import _is_valid_generation_output

    result = asyncio.run(
        AIToolsService.generate_text(
            prompt="Hello",
            system_prompt="You are a helpful assistant.",
            tier=1,
            provider="replicate",
        )
    )

    assert "unable to reach the text generation service" in result.lower()


def test_is_true_exhaustion_error_does_not_match_generic_provider_failures():
    from app.routers.ai_tools import _is_true_exhaustion_error
    assert not _is_true_exhaustion_error("Unauthorized access token")
    assert not _is_true_exhaustion_error("API key expired")


def test_generate_video_with_genspark_provider(monkeypatch):
    async def fake_generate_video(prompt, tier):
        assert prompt == "create a short clip"
        assert tier == 1
        return "https://example.com/video.mp4"

    monkeypatch.setattr(
        "app.services.ai_service.GensparkProvider.generate_video",
        fake_generate_video,
    )

    result = asyncio.run(
        AIToolsService.generate_video(
            prompt="create a short clip",
            tier=1,
            provider="genspark",
        )
    )

    assert result == "https://example.com/video.mp4"


def test_generate_text_concurrent_calls(monkeypatch):
    async def fake_run_model(model, input_data, starting_tier=1):
        assert model == "meta-llama/Llama-3.2-3B-Instruct"
        assert input_data["messages"][0]["role"] == "system"
        assert input_data["messages"][1]["role"] == "user"
        assert input_data["messages"][1]["content"].startswith("Hello")
        return {"choices": [{"message": {"content": "Concurrent response"}}]}

    monkeypatch.setattr(
        "app.services.ai_service.HuggingFaceProvider.run_model",
        fake_run_model,
    )

    async def run_many():
        tasks = [
            AIToolsService.generate_text(
                prompt=f"Hello {i}",
                system_prompt="You are a helpful assistant.",
                tier=1,
                provider="huggingface",
            )
            for i in range(10)
        ]
        return await asyncio.gather(*tasks)

    results = asyncio.run(run_many())
    assert results == ["Concurrent response"] * 10


def test_normalize_image_generation_result_stores_raw_bytes(monkeypatch):
    from app.routers.ai_tools import _normalize_image_generation_result

    class DummyAsset:
        proxy_url = "/api/v1/assets/123"

    captured = {}

    def fake_store_generated_image_bytes(
        session,
        *,
        user_id,
        image_bytes,
        provider,
        model=None,
        prompt=None,
        negative_prompt=None,
        resolution=None,
        seed=None,
        generation_time_ms=None,
        request_id=None,
        original_url=None,
    ):
        captured["user_id"] = user_id
        captured["image_bytes"] = image_bytes
        captured["provider"] = provider
        return DummyAsset()

    monkeypatch.setattr(
        "app.routers.ai_tools.asset_storage.store_generated_image_bytes",
        fake_store_generated_image_bytes,
    )

    buffer = BytesIO()
    Image.new("RGB", (1, 1), (255, 0, 0)).save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    result = _normalize_image_generation_result(
        image_bytes,
        session=object(),
        user_id=7,
        provider="cloudflare",
        prompt="generate a car image",
    )

    assert result == "/api/v1/assets/123"
    assert captured["user_id"] == 7
    assert captured["provider"] == "cloudflare"
    assert captured["image_bytes"] == image_bytes



def test_normalize_image_generation_result_rejects_invalid_bytes(monkeypatch):
    from app.routers.ai_tools import InvalidGeneratedImageError, _normalize_image_generation_result

    def fake_store_generated_image_bytes(*args, **kwargs):
        raise ValueError("Generated image provider returned invalid image bytes")

    monkeypatch.setattr(
        "app.routers.ai_tools.asset_storage.store_generated_image_bytes",
        fake_store_generated_image_bytes,
    )

    with pytest.raises(InvalidGeneratedImageError):
        _normalize_image_generation_result(
            b"\xff\x00\x01",
            session=object(),
            user_id=7,
            provider="cloudflare",
            prompt="generate a car image",
        )