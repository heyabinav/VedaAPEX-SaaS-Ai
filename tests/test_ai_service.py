import asyncio

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


def test_is_true_exhaustion_error_matches_all_provider_failures():
    from app.routers.ai_tools import _is_true_exhaustion_error

    assert _is_true_exhaustion_error("All providers failed for image. Last error: ...")
    assert _is_true_exhaustion_error("All free providers failed due to rate limits")
    assert _is_true_exhaustion_error("All premium providers failed: last error 429")
    assert _is_true_exhaustion_error("All platforms failed")
    assert _is_true_exhaustion_error("All tiers exhausted")


def test_is_true_exhaustion_error_does_not_match_provider_rate_limits():
    from app.routers.ai_tools import _is_true_exhaustion_error

    assert not _is_true_exhaustion_error("Rate limit exceeded for provider x")
    assert not _is_true_exhaustion_error("Unauthorized access token")
    assert not _is_true_exhaustion_error("Quota exceeded on one provider")
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
