import httpx
import asyncio
from typing import Any
from ...core.config import settings


class SkillbossProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.SKILLBOSS_API_KEY_TIER1,
            2: settings.SKILLBOSS_API_KEY_TIER2,
            3: settings.SKILLBOSS_API_KEY_TIER3,
            4: settings.SKILLBOSS_API_KEY_TIER4,
            5: settings.SKILLBOSS_API_KEY_TIER5,
            6: settings.SKILLBOSS_API_KEY_TIER6,
            7: settings.SKILLBOSS_API_KEY_TIER7,
            8: settings.SKILLBOSS_API_KEY_TIER8,
        }
        return keys.get(tier) or (settings.PPT_GENERATION_API_KEY if tier == 1 else "") or ""

    @staticmethod
    async def generate_ppt(prompt: str, starting_tier: int = 1) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            last_error = None
            for tier in range(starting_tier, 9):
                api_key = SkillbossProvider.get_api_key(tier)
                if not api_key:
                    continue

                # SkillBoss acts as an OpenAI-compatible gateway
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": "skillboss/gamma-ppt",  # Using a common skillboss model id for PPT
                    "messages": [{"role": "user", "content": prompt}],
                }

                response = await client.post(
                    "https://api.skillboss.co/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code in [401, 402, 403, 429]:
                    print(f"SkillBoss Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                if response.status_code != 200 and response.status_code != 201:
                    print(f"SkillBoss Tier {tier} failed ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                data = response.json()

                # Extract URL from standard OpenAI chat completion response format
                try:
                    content = data["choices"][0]["message"]["content"]
                    # Skillboss Gamma endpoints typically return the URL of the generated presentation directly in the content
                    return content.strip()
                except (KeyError, IndexError) as e:
                    raise Exception(f"Failed to parse SkillBoss response: {data}")

            raise Exception(f"All SkillBoss tiers exhausted. Last error: {last_error}")
