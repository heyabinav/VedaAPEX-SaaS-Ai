#!/usr/bin/env python3
"""Check NVIDIA API key configuration and optionally call the local backend endpoint."""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent / ".env"
KEY_PREFIX = "NVIDIA_API_KEY_TIER"
KEY_COUNT = 8


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


def check_nvidia_keys(env_values: dict[str, str]) -> dict[int, str | None]:
    keys: dict[int, str | None] = {}
    for tier in range(1, KEY_COUNT + 1):
        key_name = f"{KEY_PREFIX}{tier}"
        keys[tier] = env_values.get(key_name)
    return keys


def print_key_summary(keys: dict[int, str | None]) -> None:
    print("NVIDIA API key summary:")
    print("----------------------")
    for tier, value in keys.items():
        status = "SET" if value else "MISSING"
        masked = None
        if value:
            masked = value[:6] + "..." + value[-4:]
        print(f"Tier {tier}: {status}" + (f" (value={masked})" if masked else ""))
    present = [tier for tier, value in keys.items() if value]
    missing = [tier for tier, value in keys.items() if not value]
    print()
    print(f"Total NVIDIA keys found: {len(present)} / {KEY_COUNT}")
    if missing:
        print(f"Missing tiers: {', '.join(str(t) for t in missing)}")


def call_backend_image_endpoint(
    base_url: str = "http://localhost:7860",
    prompt: str = "Test NVIDIA image generation",
    tier: int = 1,
    provider: str = "nvidia",
):
    endpoint = urllib.parse.urljoin(base_url, "/api/v1/ai/generate/image")
    payload = {
        "prompt": prompt,
        "aspect_ratio": "16:9",
        "num_outputs": 1,
        "tier": tier,
        "provider": provider,
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"Calling backend: {endpoint}")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            print("Response status:", response.status)
            print("Response body:")
            print(body)
    except urllib.error.HTTPError as exc:
        print("Backend returned HTTP error:", exc.code)
        try:
            body = exc.read().decode("utf-8")
            print(body)
        except Exception:
            pass
    except urllib.error.URLError as exc:
        print("Failed to reach backend:", exc)


def main() -> int:
    try:
        env_values = parse_env_file(ENV_FILE)
    except FileNotFoundError as exc:
        print(exc)
        return 1

    keys = check_nvidia_keys(env_values)
    print_key_summary(keys)

    if len(sys.argv) > 1 and sys.argv[1] in {"--test", "test"}:
        tier = 1
        if len(sys.argv) > 2:
            try:
                tier = int(sys.argv[2])
            except ValueError:
                print("Invalid tier value, defaulting to 1")
        call_backend_image_endpoint(tier=tier)
    else:
        print()
        print("Run this script with 'python check_nvidia_keys.py test [tier]' to call the local NVIDIA image endpoint.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
