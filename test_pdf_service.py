import asyncio
import os
import sys

# Add the project root to sys.path to allow imports from 'app'
sys.path.append(os.getcwd())

from app.services.document_service import DocumentService
from app.core.config import settings


async def main():
    print("Testing PDF Generation via DocumentService...")

    # Ensure static/generated directory exists
    os.makedirs("static/generated", exist_ok=True)

    prompt = "Create a professional report about the future of AI in 2026."
    base_url = "http://localhost:8000/"

    # We will try 'groq' since it has a key in .env
    # Provider: 'groq'
    # Tier: 1

    try:
        print(f"Calling generate_pdf with provider='groq'...")
        pdf_url = await DocumentService.generate_pdf(
            prompt=prompt, base_url=base_url, provider="groq", tier=1
        )
        print(f"Success! PDF generated at: {pdf_url}")

        # Verify the file exists locally
        filename = pdf_url.split("/")[-1]
        local_path = os.path.join("static/generated", filename)
        if os.path.exists(local_path):
            print(
                f"Verified: File exists at {local_path} (Size: {os.path.getsize(local_path)} bytes)"
            )
        else:
            print(f"Error: File {local_path} was not found!")

    except Exception as e:
        print(f"Failed to generate PDF: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
