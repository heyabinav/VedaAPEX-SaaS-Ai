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
