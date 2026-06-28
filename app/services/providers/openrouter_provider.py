import httpx
import asyncio
from typing import Any
from ...core.config import settings


class OpenRouterProvider:
    # Model to tier API key mapping
    MODEL_KEY_MAP = {
        "x-ai/grok-imagine-video": settings.OPENROUTER_API_KEY_TIER1,
        "qwen/qwen3-coder:free": settings.OPENROUTER_API_KEY_TIER2,
        "meta-llama/llama-3.3-70b-instruct:free": settings.OPENROUTER_API_KEY_TIER3,
        "openai/sora-2-pro": settings.OPENROUTER_API_KEY_TIER4,
        "deepseek/deepseek-v4-flash:free": settings.OPENROUTER_API_KEY_TIER5,
        "google/lyria-3-pro-preview": settings.OPENROUTER_API_KEY_TIER6,
        "x-ai/grok-imagine-image-quality": settings.OPENROUTER_API_KEY_TIER7,
        "google/gemma-4-31b-it:free": settings.OPENROUTER_API_KEY_TIER8,
        "recraft/recraft-v.1-pro": settings.OPENROUTER_API_KEY_TIER9,
        "black-forest-labs/flux.2-pro": settings.OPENROUTER_API_KEY_TIER10,
    }

    @staticmethod
    def get_api_key_by_model(model: str) -> str:
        # Check direct match
        key = OpenRouterProvider.MODEL_KEY_MAP.get(model)
        if key:
            return key
        # Check partial match (case insensitive)
        for model_name, api_key in OpenRouterProvider.MODEL_KEY_MAP.items():
            if model_name.lower() in model.lower() and api_key:
                return api_key
        return ""

    @staticmethod
    def get_api_key_by_tier(tier: int) -> str:
        keys = {
            1: settings.OPENROUTER_API_KEY_TIER1,
            2: settings.OPENROUTER_API_KEY_TIER2,
            3: settings.OPENROUTER_API_KEY_TIER3,
            4: settings.OPENROUTER_API_KEY_TIER4,
            5: settings.OPENROUTER_API_KEY_TIER5,
            6: settings.OPENROUTER_API_KEY_TIER6,
            7: settings.OPENROUTER_API_KEY_TIER7,
            8: settings.OPENROUTER_API_KEY_TIER8,
            9: settings.OPENROUTER_API_KEY_TIER9,
            10: settings.OPENROUTER_API_KEY_TIER10,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int) -> Any:
        # 1. Determine which API key to use
        # If it's a specific model mapped to a key, try that first
        api_key = OpenRouterProvider.get_api_key_by_model(model)

        # 2. Check if we are running video generation
        # OpenRouter video endpoint: POST /api/v1/videos
        is_video = (
            "video" in model.lower()
            or "sora" in model.lower()
            or "lyria" in model.lower()
            or "imagine-video" in model.lower()
        )
        if is_video:
            # Resolve key
            key = (
                api_key
                or OpenRouterProvider.get_api_key_by_tier(starting_tier)
                or OpenRouterProvider.get_api_key_by_tier(1)
            )
            if not key:
                raise Exception(f"No API key found for OpenRouter video model: {model}")

            prompt = input_data.get("prompt", "")
            return await OpenRouterProvider.run_video_model(model, prompt, key)

        # 3. Standard Text or Image chat completions
        # If it's image generation, transform prompt payload into messages format
        if "prompt" in input_data and "messages" not in input_data:
            prompt = input_data.pop("prompt")
            input_data["messages"] = [{"role": "user", "content": prompt}]
            input_data["modalities"] = ["image"]

        endpoint = input_data.pop("endpoint", "https://openrouter.ai/api/v1/chat/completions")

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None

            # If we had a specific mapped key, try that first
            if api_key:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {"model": model, **input_data}
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code == 200:
                        return response.json()
                    last_error = f"Mapped key failed: {response.text}"
                except Exception as e:
                    last_error = str(e)

            # Otherwise, fall back to iterating through tiers
            for tier in range(starting_tier, 11):
                tier_key = OpenRouterProvider.get_api_key_by_tier(tier)
                if not tier_key or tier_key == api_key:
                    continue

                headers = {
                    "Authorization": f"Bearer {tier_key}",
                    "Content-Type": "application/json",
                }
                payload = {"model": model, **input_data}
                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"OpenRouter Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        input_data["endpoint"] = endpoint  # Restore for next loop
                        continue
                    if response.status_code != 200:
                        raise Exception(f"OpenRouter API error: {response.text}")
                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"OpenRouter Tier {tier} failed: {e}")
                    input_data["endpoint"] = endpoint  # Restore for next loop
                    continue
            raise Exception(f"All OpenRouter tiers exhausted. Last error: {last_error}")

    @staticmethod
    async def run_video_model(model: str, prompt: str, api_key: str) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            submit_url = "https://openrouter.ai/api/v1/videos"
            payload = {"model": model, "prompt": prompt}
            response = await client.post(submit_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise Exception(f"OpenRouter video submit failed: {response.text}")

            job_data = response.json()
            job_id = job_data.get("id")
            if not job_id:
                raise Exception(f"No job ID returned by OpenRouter: {job_data}")

            poll_url = f"https://openrouter.ai/api/v1/videos/{job_id}"
            for _ in range(24):  # 120 seconds timeout
                await asyncio.sleep(5)
                poll_resp = await client.get(poll_url, headers=headers)
                if poll_resp.status_code != 200:
                    continue
                poll_data = poll_resp.json()
                status = poll_data.get("status")
                if status == "completed":
                    if "video" in poll_data and isinstance(poll_data["video"], dict):
                        return poll_data["video"].get("url")
                    return f"https://openrouter.ai/api/v1/videos/{job_id}/content"
                elif status == "failed":
                    raise Exception(f"OpenRouter video generation failed: {poll_data.get('error')}")
            raise Exception("OpenRouter video generation timed out")
