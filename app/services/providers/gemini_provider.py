import httpx
from typing import Any
from ...core.config import settings


class GeminiProvider:
    @staticmethod
    def get_api_key() -> str:
        """Get the Gemini API key from settings"""
        return settings.GEMINI_API_KEY or ""

    @staticmethod
    async def run_model(model: str, input_data: dict) -> Any:
        """
        Run a model using the Gemini API

        Args:
            model: The model name (e.g., "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash")
            input_data: Dictionary containing the request data
                - For text generation: {"contents": [{"parts": [{"text": "prompt"}]}]}
                - Can also include system_instruction, generation_config, etc.

        Returns:
            The API response as a dictionary
        """
        api_key = GeminiProvider.get_api_key()
        if not api_key:
            raise Exception("GEMINI_API_KEY is not configured")

        async with httpx.AsyncClient(timeout=120.0) as client:
            # Gemini API endpoint
            endpoint = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            )

            headers = {"Content-Type": "application/json"}

            # Add API key as query parameter
            params = {"key": api_key}

            try:
                response = await client.post(
                    endpoint, headers=headers, json=input_data, params=params
                )

                if response.status_code == 401:
                    raise Exception(f"Gemini API: Invalid API key. Status: {response.status_code}")
                elif response.status_code == 403:
                    raise Exception(f"Gemini API: Access forbidden. Status: {response.status_code}")
                elif response.status_code == 429:
                    raise Exception(
                        f"Gemini API: Rate limit exceeded. Status: {response.status_code}"
                    )
                elif response.status_code != 200:
                    error_text = response.text
                    raise Exception(f"Gemini API error: {response.status_code} - {error_text}")

                return response.json()

            except httpx.TimeoutException:
                raise Exception("Gemini API request timed out")
            except Exception as e:
                print(f"Gemini API failed: {e}")
                raise

    @staticmethod
    async def generate_text(prompt: str, model: str = "gemini-2.0-flash", **kwargs) -> str:
        """
        Convenience method for simple text generation

        Args:
            prompt: The text prompt
            model: The model to use (default: gemini-2.0-flash)
            **kwargs: Additional parameters for generation_config

        Returns:
            The generated text
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

        # Add system instruction if provided
        if "system_instruction" in kwargs:
            request_body["system_instruction"] = {"parts": [{"text": kwargs["system_instruction"]}]}

        response = await GeminiProvider.run_model(model, request_body)

        # Extract the generated text from the response
        if "candidates" in response and len(response["candidates"]) > 0:
            candidate = response["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"]:
                parts = candidate["content"]["parts"]
                if len(parts) > 0 and "text" in parts[0]:
                    return parts[0]["text"]

        return ""
