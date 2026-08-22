import httpx
from typing import Any
from ...core.config import settings


class GeminiProvider:
    @staticmethod
    def get_api_key(tier: int = 1) -> str:
        """Get the Gemini API key from settings for a specific tier or fallback to default key"""
        keys = {
            1: getattr(settings, "GEMINI_API_KEY_TIER1", None) or getattr(settings, "GEMINI_API_KEY", None) or getattr(settings, "VISION_API_KEY", None),
            2: getattr(settings, "GEMINI_API_KEY_TIER2", None),
            3: getattr(settings, "GEMINI_API_KEY_TIER3", None),
            4: getattr(settings, "GEMINI_API_KEY_TIER4", None),
            5: getattr(settings, "GEMINI_API_KEY_TIER5", None),
            6: getattr(settings, "GEMINI_API_KEY_TIER6", None),
        }
        return keys.get(tier) or getattr(settings, "GEMINI_API_KEY", None) or getattr(settings, "VISION_API_KEY", "") or ""

    @staticmethod
    async def run_model(model: str, input_data: dict, starting_tier: int = 1) -> Any:
        """
        Run a model using the Gemini API with tier fallback
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            headers = {"Content-Type": "application/json"}

            last_error = None

            for tier in range(starting_tier, 7):
                api_key = GeminiProvider.get_api_key(tier)
                if not api_key:
                    continue

                params = {"key": api_key}
                try:
                    response = await client.post(
                        endpoint, headers=headers, json=input_data, params=params
                    )

                    if response.status_code in (401, 403, 429):
                        print(f"Gemini Tier {tier} exhausted or unauthorized ({response.status_code}). Switching to next tier...")
                        last_error = f"Tier {tier}: {response.text}"
                        continue
                    if response.status_code != 200:
                        raise Exception(f"Gemini API error ({response.status_code}): {response.text}")

                    return response.json()

                except httpx.TimeoutException:
                    last_error = f"Tier {tier} timed out"
                    print(f"Gemini Tier {tier} request timed out")
                    continue
                except Exception as e:
                    last_error = str(e)
                    print(f"Gemini Tier {tier} failed: {e}")
                    continue

            raise Exception(f"All Gemini tiers exhausted. Last error: {last_error}")

    @staticmethod
    async def generate_text(prompt: str, model: str = "gemini-2.0-flash", starting_tier: int = 1, **kwargs) -> str:
        """
        Convenience method for simple text generation with tier fallback
        """
        generation_config = {
            "temperature": kwargs.get("temperature", 1),
            "top_p": kwargs.get("top_p", 0.95),
            "top_k": kwargs.get("top_k", 40),
            "max_output_tokens": kwargs.get("max_output_tokens", 8192),
        }

        request_body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generation_config": generation_config,
        }

        if "system_instruction" in kwargs:
            request_body["system_instruction"] = {"parts": [{"text": kwargs["system_instruction"]}]}

        response = await GeminiProvider.run_model(model, request_body, starting_tier=starting_tier)

        if "candidates" in response and len(response["candidates"]) > 0:
            candidate = response["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]

        return ""
