#!/usr/bin/env python3
"""
Run a text generation Hugging Face space via local AIToolsService.
Usage:
  python vedaapex-text/run_text_space.py --model "huggingface/inference-playground" --prompt "Hello" [--tier 1]
"""

import argparse
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Ensure backend package path is available when running from the helper folder.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Load project .env
load_dotenv(dotenv_path=os.path.join(ROOT_DIR, '.env'))

from app.services.ai_service import AIToolsService


async def run_text(model: str, prompt: str, tier: int):
    result = await AIToolsService.generate_text(
        prompt=prompt,
        system_prompt="You are a helpful assistant.",
        tier=tier,
        provider=model,
    )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Provider model, e.g. huggingface/inference-playground")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--tier", type=int, default=1)
    args = parser.parse_args()

    try:
        result = asyncio.run(run_text(args.model, args.prompt, args.tier))
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print("Text generation error:", e)


if __name__ == "__main__":
    main()
