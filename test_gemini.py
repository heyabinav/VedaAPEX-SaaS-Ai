"""
Test file for Gemini provider integration
This script demonstrates how to use the Gemini API provider
"""

import asyncio
from app.services.providers.gemini_provider import GeminiProvider


async def test_gemini_text_generation():
    """Test basic text generation with Gemini"""
    try:
        # Simple text generation example
        prompt = "Explain what artificial intelligence is in one paragraph"
        result = await GeminiProvider.generate_text(
            prompt=prompt,
            model="gemini-2.0-flash",
            temperature=0.7,
            max_output_tokens=1024,
        )

        print("=== Gemini Text Generation Test ===")
        print(f"Prompt: {prompt}")
        print(f"Response: {result}")
        print("✓ Test passed!")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def test_gemini_raw_request():
    """Test raw API request to Gemini"""
    try:
        request_body = {
            "contents": [{"parts": [{"text": "What is the capital of France?"}]}],
            "generation_config": {"temperature": 0.7, "max_output_tokens": 512},
        }

        result = await GeminiProvider.run_model("gemini-2.0-flash", request_body)

        print("\n=== Gemini Raw Request Test ===")
        print(f"Full API Response: {result}")
        print("✓ Test passed!")

    except Exception as e:
        print(f"✗ Test failed: {e}")


async def main():
    """Run all tests"""
    print("Starting Gemini Provider Tests...\n")

    # Verify API key is configured
    api_key = GeminiProvider.get_api_key()
    if not api_key:
        print("✗ GEMINI_API_KEY is not configured in .env file")
        return

    print(f"✓ GEMINI_API_KEY is configured (length: {len(api_key)})")
    print()

    # Run tests
    await test_gemini_text_generation()
    await test_gemini_raw_request()


if __name__ == "__main__":
    asyncio.run(main())
