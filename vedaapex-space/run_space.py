#!/usr/bin/env python3
"""
Run a Hugging Face Space / Krea model via the local AIToolsService.
Usage:
  python vedaapex-space/run_space.py --model "owner/model" --prompt "a red fox" [--num 1] [--aspect 1:1] [--tier 1]

Note: activate the project's virtualenv and ensure relevant API keys are set in `.env` (e.g. `HUGGING_FACE_API_KEY`, `KREA_API_KEY_*`).
"""

import argparse
import asyncio
import json
from dotenv import load_dotenv
import os

# Load project .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

from app.services.ai_service import AIToolsService


async def run_generation(model: str, prompt: str, num: int, aspect: str, tier: int):
    result = await AIToolsService.generate_image(
        prompt=prompt,
        aspect_ratio=aspect,
        num_outputs=num,
        tier=tier,
        provider=model,
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Owner/model or provider (e.g. black-forest-labs/FLUX.2-dev or krea/Krea-2)")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--num", type=int, default=1)
    parser.add_argument("--aspect", default="1:1")
    parser.add_argument("--tier", type=int, default=1)
    args = parser.parse_args()

    try:
        result = asyncio.run(run_generation(args.model, args.prompt, args.num, args.aspect, args.tier))
        print(json.dumps(result, indent=2))
    except Exception as e:
        print("Generation error:", e)


if __name__ == "__main__":
    main()
