import httpx
import asyncio
from typing import Any, Optional
from ...core.config import settings


class PiAPIProvider:
    BASE_URL = "https://api.piapi.ai/api/v1"

    @staticmethod
    def get_api_key(tier: int) -> str:
        keys = {
            1: settings.PIAPI_API_KEY_TIER1,
            2: settings.PIAPI_API_KEY_TIER2,
            3: settings.PIAPI_API_KEY_TIER3,
            4: settings.PIAPI_API_KEY_TIER4,
            5: settings.PIAPI_API_KEY_TIER5,
            6: settings.PIAPI_API_KEY_TIER6,
            7: settings.PIAPI_API_KEY_TIER7,
            8: settings.PIAPI_API_KEY_TIER8,
        }
        return keys.get(tier) or ""

    @staticmethod
    async def _create_and_poll_task(payload: dict, starting_tier: int = 1) -> dict:
        """Core method: Creates a task on PiAPI and polls until completion. Returns full output dict."""
        async with httpx.AsyncClient(timeout=180.0) as client:
            last_error = None
            service = payload.pop("_service", None)
            for tier in range(starting_tier, 9):
                api_key = PiAPIProvider.get_api_key(tier)
                if not api_key and service == "video" and tier == 1:
                    api_key = settings.VIDEO_GENERATION_API_KEY or ""
                if not api_key:
                    continue

                headers = {"x-api-key": api_key, "Content-Type": "application/json"}

                # 1. Create Task
                response = await client.post(
                    f"{PiAPIProvider.BASE_URL}/task", headers=headers, json=payload
                )

                if response.status_code in [401, 402, 403, 429]:
                    print(f"[PiAPI] Tier {tier} exhausted ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                if response.status_code != 200:
                    print(f"[PiAPI] Tier {tier} failed ({response.status_code}). Switching...")
                    last_error = f"Tier {tier}: {response.text}"
                    continue

                data = response.json()
                task_id = data.get("data", {}).get("task_id")

                if not task_id:
                    raise Exception(f"No task_id returned from PiAPI: {data}")

                # 2. Poll Task Status (max 5 minutes)
                max_polls = 100
                for _ in range(max_polls):
                    await asyncio.sleep(3)
                    poll_resp = await client.get(
                        f"{PiAPIProvider.BASE_URL}/task/{task_id}", headers=headers
                    )
                    poll_data = poll_resp.json()
                    status = poll_data.get("data", {}).get("status")

                    if status == "completed":
                        return poll_data.get("data", {}).get("output", {})
                    elif status in ["failed", "error"]:
                        err_msg = str(poll_data.get("data", {}).get("error", ""))
                        if any(
                            w in err_msg.lower()
                            for w in ["credit", "payment", "balance", "insufficient"]
                        ):
                            print(f"[PiAPI] Tier {tier} out of credits. Switching...")
                            last_error = err_msg
                            break  # Go to next tier
                        raise Exception(f"PiAPI task failed: {err_msg}")
                else:
                    raise Exception(f"PiAPI task timed out after polling {max_polls} times.")

            raise Exception(f"All PiAPI tiers exhausted. Last error: {last_error}")

    # =============================================
    #   IMAGE GENERATION MODELS
    # =============================================

    @staticmethod
    async def generate_image(
        prompt: str,
        starting_tier: int = 1,
        aspect_ratio: str = "1:1",
        model: str = "flux1-schnell",
    ) -> str:
        """Generate image using Flux Schnell, Flux Dev, GPT-Image, Seedream etc."""
        payload = {
            "model": model,
            "task_type": "txt2img",
            "input": {"prompt": prompt, "aspect_ratio": aspect_ratio},
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        # Extract image URL from output
        if isinstance(output, dict):
            return output.get("image_url") or output.get("image_urls", [None])[0] or str(output)
        return str(output)

    @staticmethod
    async def generate_image_flux_dev(
        prompt: str, starting_tier: int = 1, aspect_ratio: str = "1:1"
    ) -> str:
        """Higher quality Flux Dev model"""
        return await PiAPIProvider.generate_image(
            prompt, starting_tier, aspect_ratio, model="flux-dev"
        )

    @staticmethod
    async def generate_image_gpt(
        prompt: str, starting_tier: int = 1, aspect_ratio: str = "1:1"
    ) -> str:
        """GPT Image generation (GPT-Image 1.5 / 2)"""
        return await PiAPIProvider.generate_image(
            prompt, starting_tier, aspect_ratio, model="gpt-image-1"
        )

    @staticmethod
    async def generate_image_seedream(
        prompt: str, starting_tier: int = 1, aspect_ratio: str = "1:1"
    ) -> str:
        """Seedream image model"""
        return await PiAPIProvider.generate_image(
            prompt, starting_tier, aspect_ratio, model="seedream"
        )

    # =============================================
    #   VIDEO GENERATION MODELS
    # =============================================

    @staticmethod
    async def generate_video_kling(prompt: str, starting_tier: int = 1, duration: str = "5") -> str:
        """Kling 3.0 text-to-video"""
        payload = {
            "model": "kling-3",
            "task_type": "txt2video",
            "input": {"prompt": prompt, "duration": duration, "aspect_ratio": "16:9"},
            "_service": "video",
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return (
                output.get("video_url")
                or output.get("works", [{}])[0].get("video", {}).get("url")
                or str(output)
            )
        return str(output)

    @staticmethod
    async def generate_video_luma(prompt: str, starting_tier: int = 1) -> str:
        """Luma Dream Machine text-to-video"""
        payload = {
            "model": "luma",
            "task_type": "txt2video",
            "input": {"prompt": prompt, "aspect_ratio": "16:9"},
            "_service": "video",
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("video_url") or output.get("video") or str(output)
        return str(output)

    @staticmethod
    async def generate_video_hailuo(prompt: str, starting_tier: int = 1) -> str:
        """Hailuo / MiniMax text-to-video"""
        payload = {
            "model": "hailuo",
            "task_type": "txt2video",
            "input": {"prompt": prompt},
            "_service": "video",
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("video_url") or str(output)
        return str(output)

    @staticmethod
    async def generate_video_wan(prompt: str, starting_tier: int = 1) -> str:
        """Wan 2.1 text-to-video"""
        payload = {
            "model": "wan-2.1",
            "task_type": "txt2video",
            "input": {"prompt": prompt, "aspect_ratio": "16:9"},
            "_service": "video",
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("video_url") or str(output)
        return str(output)

    @staticmethod
    async def generate_video_sora(prompt: str, starting_tier: int = 1) -> str:
        """Sora 2 Pro text-to-video"""
        payload = {
            "model": "sora2-pro",
            "task_type": "txt2video",
            "input": {"prompt": prompt, "aspect_ratio": "16:9", "duration": "5"},
            "_service": "video",
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("video_url") or str(output)
        return str(output)

    @staticmethod
    async def generate_video_veo(prompt: str, starting_tier: int = 1) -> str:
        """Google Veo 3.1 text-to-video"""
        payload = {
            "model": "veo-3.1",
            "task_type": "txt2video",
            "input": {"prompt": prompt, "aspect_ratio": "16:9"},
            "_service": "video",
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("video_url") or str(output)
        return str(output)

    @staticmethod
    async def generate_video_seedance(prompt: str, starting_tier: int = 1) -> str:
        """Seedance 2 text-to-video"""
        payload = {
            "model": "seedance-2",
            "task_type": "txt2video",
            "input": {"prompt": prompt},
            "_service": "video",
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("video_url") or str(output)
        return str(output)

    @staticmethod
    async def generate_video_hunyuan(prompt: str, starting_tier: int = 1) -> str:
        """Hunyuan Video text-to-video"""
        payload = {
            "model": "hunyuan-video",
            "task_type": "txt2video",
            "input": {"prompt": prompt, "aspect_ratio": "16:9"},
            "_service": "video",
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("video_url") or str(output)
        return str(output)

    # =============================================
    #   3D MODEL GENERATION
    # =============================================

    @staticmethod
    async def generate_3d_trellis(prompt: str, starting_tier: int = 1) -> str:
        """Trellis 2 - 3D model generation from text"""
        payload = {
            "model": "trellis-2",
            "task_type": "txt2model",
            "input": {"prompt": prompt},
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("model_url") or output.get("glb_url") or str(output)
        return str(output)

    # =============================================
    #   MUSIC / AUDIO GENERATION
    # =============================================

    @staticmethod
    async def generate_music_suno(prompt: str, starting_tier: int = 1) -> str:
        """Suno - AI music generation"""
        payload = {
            "model": "suno",
            "task_type": "txt2music",
            "input": {"prompt": prompt, "make_instrumental": False},
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("audio_url") or str(output)
        return str(output)

    @staticmethod
    async def generate_music_udio(prompt: str, starting_tier: int = 1) -> str:
        """Udio - AI music generation"""
        payload = {
            "model": "udio",
            "task_type": "txt2music",
            "input": {"prompt": prompt},
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("audio_url") or str(output)
        return str(output)

    @staticmethod
    async def generate_tts(text: str, starting_tier: int = 1) -> str:
        """F5-TTS text-to-speech via PiAPI"""
        payload = {
            "model": "f5-tts",
            "task_type": "txt2speech",
            "input": {"text": text},
        }
        output = await PiAPIProvider._create_and_poll_task(payload, starting_tier)
        if isinstance(output, dict):
            return output.get("audio_url") or str(output)
        return str(output)
