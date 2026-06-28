import httpx
from typing import Any
from app.core.config import settings
from app.services.providers.fal_provider import FalProvider
from app.services.providers.replicate_provider import ReplicateProvider
from app.services.providers.apexspeech_provider import ApexSpeechProvider


class TTSProvider:
    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.ELEVENLABS_API_KEY_TIER1,
            2: settings.ELEVENLABS_API_KEY_TIER2,
            3: settings.ELEVENLABS_API_KEY_TIER3,
            4: settings.ELEVENLABS_API_KEY_TIER4,
            5: settings.ELEVENLABS_API_KEY_TIER5,
            6: settings.ELEVENLABS_API_KEY_TIER6,
            7: settings.ELEVENLABS_API_KEY_TIER7,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def run_model(text: str, voice_id: str, starting_tier: int) -> Any:
        # 1. Try our completely free, no-key, premium human-like ApexSpeech first
        print("[TTS-ROUTER] Running premium free ApexSpeech model...")
        try:
            return await ApexSpeechProvider.run_model(text, voice_id)
        except Exception as e:
            print(f"[TTS-ROUTER] ApexSpeech free model failed: {e}. Falling back to API tiers...")

        # Standard default ElevenLabs voice (Rachel) if none provided
        selected_voice = voice_id or "21m00Tcm4TlvDq8ikWAM"

        async with httpx.AsyncClient(timeout=60.0) as client:
            last_error = None

            # 1. Try ElevenLabs Tiers
            for tier in range(starting_tier, 8):
                api_key = TTSProvider.get_api_key(tier)
                if not api_key:
                    continue

                headers = {"xi-api-key": api_key, "Content-Type": "application/json"}

                payload = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",  # Ultra premium monolingual
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                }

                endpoint = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice}"

                try:
                    response = await client.post(endpoint, headers=headers, json=payload)
                    if response.status_code in [401, 402, 403, 429]:
                        print(f"ElevenLabs Tier {tier} exhausted or invalid key. Switching...")
                        last_error = f"ElevenLabs Tier {tier}: {response.text}"
                        continue
                    if response.status_code == 200:
                        # Returns raw audio bytes
                        return response.content
                except Exception as e:
                    last_error = str(e)
                    continue

            # 2. Smart Fallback: If ElevenLabs is missing or exhausted, use Fal.ai F5-TTS
            print(
                "[TTS-FALLBACK] ElevenLabs failed or not configured. Falling back to Fal F5-TTS..."
            )
            try:
                # F5-TTS on Fal is highly realistic and has zero-shot human pauses.
                result = await FalProvider.run_model("fal-ai/f5-tts", {"gen_text": text}, tier=1)
                if result and "audio" in result:
                    # Fal usually returns a dict with audio url
                    return result["audio"]["url"]
            except Exception as e:
                print(f"[TTS-FALLBACK] Fal F5-TTS fallback failed: {e}")
                last_error = str(e)

            # 3. Last resort fallback: Replicate XTTS-v2
            print("[TTS-FALLBACK] Trying Replicate XTTS-v2...")
            try:
                result = await ReplicateProvider.run_model(
                    "lucataco",
                    "xtts-v2",
                    {
                        "text": text,
                        "speaker": "https://replicate.delivery/pbxt/JtIE45mG187GaCUF71zPjDL2ihU7Vf12Y46u2g2t0Gf1YF3M/en_sample.mp3",
                        "language": "en",
                    },
                    tier=1,
                )
                return result
            except Exception as e:
                print(f"[TTS-FALLBACK] Replicate XTTS-v2 failed: {e}")
                raise Exception(f"All human-like TTS pipelines failed. Last error: {last_error}")
