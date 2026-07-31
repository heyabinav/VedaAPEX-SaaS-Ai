#!/usr/bin/env python3
"""
Run all configured owner/model spaces once and save JSON logs to `vedaapex-space/logs/`.
"""
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

MODELS = [
    "black-forest-labs/FLUX.2-dev",
    "black-forest-labs/FLUX.1-schnell",
    "black-forest-labs/flux-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "stabilityai/stable-diffusion-3.5-large",
    "Qwen/Qwen-Image",
    "krea/Krea-2",
]

LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def _sanitize(name: str) -> str:
    return name.replace("/", "_").replace(" ", "_")


async def run_model(model: str):
    prompt = f"Test generation for {model}"
    try:
        result = await AIToolsService.generate_image(
            prompt=prompt,
            aspect_ratio="1:1",
            num_outputs=1,
            tier=1,
            provider=model,
        )
        out = {"model": model, "ok": True, "result": result}
    except Exception as e:
        out = {"model": model, "ok": False, "error": str(e)}
    fname = os.path.join(LOG_DIR, f"{_sanitize(model)}.json")
    with open(fname, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {fname}: ok={out['ok']}")


async def main():
    for m in MODELS:
        await run_model(m)


if __name__ == "__main__":
    asyncio.run(main())
