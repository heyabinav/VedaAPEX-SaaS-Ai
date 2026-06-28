import httpx
import json
import base64
from typing import Any
from ...core.config import settings


class WixProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.WIX_API_KEY_TIER1,
            2: settings.WIX_API_KEY_TIER2,
            3: settings.WIX_API_KEY_TIER3,
            4: settings.WIX_API_KEY_TIER4,
            5: settings.WIX_API_KEY_TIER5,
            6: settings.WIX_API_KEY_TIER6,
            7: settings.WIX_API_KEY_TIER7,
            8: settings.WIX_API_KEY_TIER8,
            9: settings.WIX_API_KEY_TIER9,
        }
        return keys.get(tier) or ""

    @staticmethod
    def get_context_headers(api_key: str) -> dict:
        headers = {}
        try:
            parts = api_key.split(".")
            payload_b64 = None
            if len(parts) == 5:
                payload_b64 = parts[3]
            elif len(parts) == 3:
                payload_b64 = parts[1]

            if payload_b64:
                payload_b64 += "=" * (4 - len(payload_b64) % 4)
                payload_data = base64.b64decode(payload_b64).decode("utf-8", errors="ignore")

                tenant_id = None
                try:
                    payload_json = json.loads(payload_data)
                    inner_data_str = payload_json.get("data")
                    if inner_data_str:
                        inner_data = json.loads(inner_data_str)
                        tenant = inner_data.get("tenant") or {}
                        tenant_id = tenant.get("id")
                except Exception:
                    # Fallback to regex extraction if JSON is malformed
                    import re

                    # Look for tenant id pattern in the raw string
                    match = re.search(
                        r'\\?"tenant\\?":\s*\{[^{}]*\\?"id\\?":\s*\\?"([^"\\]+)\\?"',
                        payload_data,
                    )
                    if match:
                        tenant_id = match.group(1)
                    else:
                        tenant_idx = payload_data.find('"tenant"')
                        if tenant_idx == -1:
                            tenant_idx = payload_data.find('\\"tenant\\"')
                        if tenant_idx != -1:
                            id_match = re.search(
                                r'\\?"id\\?":\s*\\?"([^"\\]+)\\?"',
                                payload_data[tenant_idx:],
                            )
                            if id_match:
                                tenant_id = id_match.group(1)

                if tenant_id:
                    # Clean the tenant_id in case there are weird characters
                    tenant_id = tenant_id.strip()
                    headers["wix-account-id"] = tenant_id
                    headers["wix-site-id"] = tenant_id
        except Exception as e:
            print(f"Wix API key parsing error: {e}")
        return headers

    @staticmethod
    async def run_image_model(input_data: dict, starting_tier: int) -> Any:
        endpoint = "https://www.wixapis.com/openai/v1/images/generations"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 10):
                api_key = WixProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {"Authorization": api_key, "Content-Type": "application/json"}
                headers.update(WixProvider.get_context_headers(api_key))

                try:
                    response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"Wix Image Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Wix API error: {response.text}")

                    res_json = response.json()
                    data_list = res_json.get("data", [])
                    urls = [item.get("url") for item in data_list if item.get("url")]
                    if urls:
                        return urls
                    return res_json
                except Exception as e:
                    last_error = str(e)
                    print(f"Wix Image Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All Wix Image tiers exhausted. Last error: {last_error}")

    @staticmethod
    async def run_text_model(input_data: dict, starting_tier: int) -> Any:
        endpoint = "https://www.wixapis.com/openai/v1/chat/completions"

        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 10):
                api_key = WixProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {"Authorization": api_key, "Content-Type": "application/json"}
                headers.update(WixProvider.get_context_headers(api_key))

                try:
                    response = await client.post(endpoint, headers=headers, json=input_data)

                    if response.status_code in [401, 402, 403, 429]:
                        print(
                            f"Wix Text Tier {tier} exhausted ({response.status_code}). Switching..."
                        )
                        last_error = f"Tier {tier}: {response.text}"
                        continue

                    if response.status_code != 200:
                        raise Exception(f"Wix API error: {response.text}")

                    return response.json()
                except Exception as e:
                    last_error = str(e)
                    print(f"Wix Text Tier {tier} request error: {e}")
                    continue

            raise Exception(f"All Wix Text tiers exhausted. Last error: {last_error}")
