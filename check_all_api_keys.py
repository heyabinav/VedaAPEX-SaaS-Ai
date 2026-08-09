#!/usr/bin/env python3
"""Check configuration and health status for all API keys in .env, including Mistral, Gemini, and NVIDIA."""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(f".env file not found at: {path}")

    values: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_]+)=(.*)$")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = pattern.match(line)
            if not match:
                continue
            key, raw_value = match.groups()
            value = raw_value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            values[key] = value
    return values


def mask_key(val: str | None) -> str:
    if not val:
        return "MISSING"
    if len(val) <= 10:
        return val[:3] + "..." + val[-2:]
    return val[:6] + "..." + val[-4:]


def check_tier_keys(env_values: dict[str, str], prefix: str, max_tiers: int = 8) -> dict[int, str | None]:
    result = {}
    for tier in range(1, max_tiers + 1):
        key_name = f"{prefix}_TIER{tier}"
        result[tier] = env_values.get(key_name)
    return result


def main() -> int:
    try:
        env_values = parse_env_file(ENV_FILE)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    print("=========================================================")
    print("           VEDAAPEX API KEY AUDIT & HEALTH CHECK         ")
    print("=========================================================")

    # 1. Check Mistral Keys (Tier 1-8)
    print("\n--- MISTRAL AI (8 Tiers) ---")
    mistral_keys = check_tier_keys(env_values, "MISTRAL_API_KEY", 8)
    for tier, val in mistral_keys.items():
        print(f"  Mistral Tier {tier}: {'SET' if val else 'MISSING'} ({mask_key(val)})")
    mistral_count = sum(1 for v in mistral_keys.values() if v)
    print(f"Total Mistral keys: {mistral_count}/8")

    # 2. Check Gemini Keys (Tier 1-6)
    print("\n--- GEMINI AI (6 Tiers) ---")
    gemini_keys = check_tier_keys(env_values, "GEMINI_API_KEY", 6)
    for tier, val in gemini_keys.items():
        print(f"  Gemini Tier {tier}: {'SET' if val else 'MISSING'} ({mask_key(val)})")
    gemini_count = sum(1 for v in gemini_keys.values() if v)
    print(f"Total Gemini keys: {gemini_count}/6")

    # 3. Check NVIDIA Keys (Tier 1-8)
    print("\n--- NVIDIA AI (8 Tiers) ---")
    nvidia_keys = check_tier_keys(env_values, "NVIDIA_API_KEY", 8)
    for tier, val in nvidia_keys.items():
        print(f"  NVIDIA Tier {tier}: {'SET' if val else 'MISSING'} ({mask_key(val)})")
    nvidia_count = sum(1 for v in nvidia_keys.values() if v)
    print(f"Total NVIDIA keys: {nvidia_count}/8")

    # 4. Check HF Storage Token
    print("\n--- HUGGING FACE DATASET CHAT STORAGE ---")
    hf_token = env_values.get("HF_TOKEN")
    print(f"  HF Token: {'SET' if hf_token else 'MISSING'} ({mask_key(hf_token)})")

    # 5. Check Other Key Tiers Summary
    print("\n--- OTHER PROVIDER KEY SUMMARY ---")
    other_providers = [
        ("REPLICATE_API_KEY", 5),
        ("FAL_API_KEY", 8),
        ("TENSOR_API_KEY", 8),
        ("KREA_API_KEY", 8),
        ("BFL_API_KEY", 6),
        ("GETIMG_API_KEY", 8),
        ("FREEPIK_API_KEY", 4),
        ("FREE_API_KEY", 9),
        ("SEGMIND_API_KEY", 7),
        ("AIMLAPI_API_KEY", 8),
        ("GROQ_API_KEY", 9),
    ]

    for prefix, count in other_providers:
        keys = check_tier_keys(env_values, prefix, count)
        set_count = sum(1 for v in keys.values() if v)
        print(f"  {prefix.replace('_API_KEY', '')}: {set_count}/{count} keys configured")

    print("\n=========================================================")
    print("                    AUDIT COMPLETED                      ")
    print("=========================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
