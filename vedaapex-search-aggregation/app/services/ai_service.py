from .providers.fal_provider import FalProvider
from .providers.replicate_provider import ReplicateProvider
from .providers.tensor_provider import TensorProvider
from .providers.krea_provider import KreaProvider
from .providers.bfl_provider import BFLProvider
from .providers.getimg_provider import GetImgProvider
from .providers.freepik_provider import FreepikProvider
from .providers.free_provider import FreeProvider
from .providers.segmind_provider import SegmindProvider
from .providers.together_provider import TogetherProvider
from .providers.fireworks_provider import FireworksProvider
from .providers.cloudflare_provider import CloudflareProvider
from .providers.pollinations_provider import PollinationsProvider
from .providers.tts_provider import TTSProvider
from .providers.apexspeech_provider import ApexSpeechProvider
from .providers.pixverse_provider import PixverseProvider
from .providers.imagenart_provider import ImagenartProvider
from .providers.heygen_provider import HeyGenProvider
from .providers.did_provider import DIDProvider
from .providers.deepai_provider import DeepAIProvider
from .providers.fotor_provider import FotorProvider
from .providers.wix_provider import WixProvider
from .providers.zoviz_provider import ZovizProvider
from .providers.piapi_provider import PiAPIProvider
from .providers.kling_provider import KlingProvider
from .providers.ollama_provider import OllamaProvider
from .providers.chutes_provider import ChutesProvider
from .providers.groq_provider import GroqProvider
from .providers.genspark_provider import GensparkProvider
from .providers.tripo3d_provider import Tripo3DProvider
from .providers.gemini_provider import GeminiProvider
from .providers.bytez_provider import BytezProvider
from .providers.openrouter_provider import OpenRouterProvider
from .providers.rapidapi_provider import RapidAPIProvider
from .providers.aimlapi_provider import AIMLAPIProvider
from .providers.nvidia_provider import NVIDIAProvider
from .providers.huggingface_provider import HuggingFaceProvider
from .providers.superapi_provider import SuperAPIProvider
from .providers.logodev_provider import LogoDevProvider
from .providers.claid_provider import ClaidProvider


class AIToolsService:
    @staticmethod
    async def generate_enhancement(task: str, payload: dict, tier: int = 1):
        # Maps the user prompt/task to the Claid.ai enhancement endpoint
        endpoint = "image/enhance" if task == "image_enhancement" else "video/enhance"
        return await ClaidProvider.run_model(endpoint, payload, tier)

    @staticmethod
    async def generate_image(
        prompt: str,
        aspect_ratio: str,
        num_outputs: int,
        tier: int = 1,
        provider: str = "auto",
    ):
        provider = (provider or "auto").strip().lower() or "auto"

        # Auto-Routing Logic (Daily First, then Backup)
        if provider == "auto":
            daily_providers = [
                "cloudflare",
                "segmind",
                "krea",
                "tensor",
                "freepik",
                "imagenart",
            ]
            backup_providers = [
                "fireworks",
                "together",
                "fal",
                "getimg",
                "bfl",
                "replicate",
                "free",
                "fotor",
                "wix",
                "zoviz",
                "huggingface",
            ]
            last_error = None

            for prov in daily_providers:
                try:
                    print(f"[AUTO-ROUTER] Trying Daily Provider: {prov}")
                    return await AIToolsService.generate_image(
                        prompt, aspect_ratio, num_outputs, tier, provider=prov
                    )
                except Exception as e:
                    print(f"[AUTO-ROUTER] {prov} failed: {e}")
                    last_error = e
                    continue

            for prov in backup_providers:
                try:
                    print(f"[AUTO-ROUTER] Trying Backup Provider: {prov}")
                    return await AIToolsService.generate_image(
                        prompt, aspect_ratio, num_outputs, tier, provider=prov
                    )
                except Exception as e:
                    print(f"[AUTO-ROUTER] {prov} failed: {e}")
                    last_error = e
                    continue

            # Ultimate Failsafe Priority (Unlimited Free)
            try:
                print("[AUTO-ROUTER] ALL ELSE FAILED! Trying Ultimate Failsafe: pollinations")
                return await AIToolsService.generate_image(
                    prompt, aspect_ratio, num_outputs, tier=1, provider="pollinations"
                )
            except Exception as e:
                last_error = e

            raise Exception(
                f"CRITICAL: ALL 13 PLATFORMS (DAILY + BACKUP + FAILSAFE) EXHAUSTED! Last error: {last_error}"
            )

        # Provider-Specific Image Generation Routes
        image_size = "square"
        if aspect_ratio == "16:9":
            image_size = "landscape_16_9"
        elif aspect_ratio == "9:16":
            image_size = "portrait_16_9"

        if provider.lower() == "fal":
            result = await FalProvider.run_model(
                "fal-ai/flux/schnell",
                {"prompt": prompt, "image_size": image_size, "num_images": num_outputs},
                tier,
            )
            return result.get("images", [])

        elif provider.lower() == "replicate":
            return await ReplicateProvider.run_model(
                "black-forest-labs",
                "flux-schnell",
                {
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "num_outputs": num_outputs,
                },
                tier,
            )

        elif provider.lower() == "krea":
            return await KreaProvider.run_model(
                "krea-image-gen-v1",  # Replace with actual Krea image model ID
                {"prompt": prompt, "aspect_ratio": aspect_ratio},
                tier,
            )

        elif provider.lower() == "bfl":
            return await BFLProvider.run_model(
                "flux-pro",  # Can be flux-pro, flux-dev, or flux-schnell
                {
                    "prompt": prompt,
                    "width": 1024,  # You can map aspect_ratio to width/height
                    "height": 1024,
                },
                tier,
            )

        elif provider.lower() == "getimg":
            return await GetImgProvider.run_model(
                "essential-v2",  # Default essential model for getimg
                {"prompt": prompt, "output_format": "jpeg"},
                tier,
            )

        elif provider.lower() == "freepik":
            return await FreepikProvider.run_model(
                {
                    "prompt": prompt,
                    "styling": {
                        "color": "default",
                        "framing": "default",
                        "lighting": "default",
                        "style": "default",
                    },
                },
                tier,
            )

        elif provider.lower() == "free":
            result = await FreeProvider.run_model(
                "dall-e-3",  # Example model for Free.ai
                {"prompt": prompt, "n": num_outputs},
                tier,
            )
            return result.get("data", [])

        elif provider.lower() == "segmind":
            # Segmind default to SDXL or Flux if available
            return await SegmindProvider.run_model(
                "sdxl1.0-txt2img",
                {
                    "prompt": prompt,
                    "samples": num_outputs,
                    "scheduler": "dpmpp_2m",
                    "num_inference_steps": 25,
                    "base64": True,  # Get base64 string back
                },
                tier,
            )

        elif provider.lower() == "together":
            result = await TogetherProvider.run_model(
                "black-forest-labs/FLUX.1-schnell-Free",  # Together has Flux Free endpoint
                {"prompt": prompt, "n": num_outputs, "steps": 4},
                tier,
            )
            return result.get("data", [])

        elif provider.lower() == "fireworks":
            result = await FireworksProvider.run_model(
                "accounts/fireworks/models/flux-1-schnell",  # Fast Flux model on Fireworks
                {"prompt": prompt, "aspect_ratio": aspect_ratio},
                tier,
            )
            # Fireworks usually returns an array of objects with base64 images
            return result

        elif provider.lower() == "cloudflare":
            # Cloudflare uses @cf/stabilityai/stable-diffusion-xl-base-1.0
            result = await CloudflareProvider.run_model(
                "@cf/stabilityai/stable-diffusion-xl-base-1.0", {"prompt": prompt}, tier
            )
            return result

        elif provider.lower() == "pollinations":
            # Pollinations defaults to flux or midjourney-style
            result = await PollinationsProvider.run_model(
                "flux", {"prompt": prompt, "width": 1024, "height": 1024}, tier
            )
            return result

        elif provider.lower() == "imagenart":
            return await ImagenartProvider.run_model(
                {
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "num_outputs": num_outputs,
                },
                tier,
            )
        elif provider.lower() == "fotor":
            fotor_aspect_ratio = aspect_ratio or "1:1"
            fotor_resolution = "1024x1024"
            if fotor_aspect_ratio == "16:9":
                fotor_resolution = "1024x576"
            elif fotor_aspect_ratio == "9:16":
                fotor_resolution = "576x1024"
            elif fotor_aspect_ratio == "3:4":
                fotor_resolution = "768x1024"
            elif fotor_aspect_ratio == "4:3":
                fotor_resolution = "1024x768"

            return await FotorProvider.run_model(
                {
                    "prompt": prompt,
                    "aspectRatio": fotor_aspect_ratio,
                    "resolution": fotor_resolution,
                    "format": "jpg",
                },
                tier,
            )

        elif provider.lower() == "wix":
            wix_size = "1024x1024"
            if aspect_ratio == "16:9":
                wix_size = "1024x576"
            elif aspect_ratio == "9:16":
                wix_size = "576x1024"
            return await WixProvider.run_image_model(
                {"prompt": prompt, "n": num_outputs, "size": wix_size}, tier
            )

        elif provider.lower() == "zoviz":
            return await ZovizProvider.run_model({"prompt": prompt}, tier)

        elif provider.lower() == "deepai":
            result = await DeepAIProvider.run_model({"text": prompt}, tier)
            if isinstance(result, dict) and "output_url" in result:
                return [result["output_url"]]
            return result

        elif provider.lower() == "piapi":
            result = await PiAPIProvider.generate_image(prompt, tier, aspect_ratio)
            # Standardize output to a list of urls for consistency
            if isinstance(result, str):
                return [result]
            return result

        elif provider.lower() == "chutes":
            result = await ChutesProvider.run_model(
                "black-forest-labs/flux-schnell",
                {
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "num_outputs": num_outputs,
                },
                tier,
            )
            if isinstance(result, dict) and "data" in result:
                return [img.get("url") for img in result["data"] if img.get("url")]
            return result

        elif provider.lower() == "bytez":
            result = await BytezProvider.run_model(
                "stabilityai/stable-diffusion-xl-base-1.0",
                {"prompt": prompt, "aspect_ratio": aspect_ratio},
                tier,
            )
            if isinstance(result, dict) and "output" in result:
                return [result["output"]]
            return result

        elif provider.lower() == "openrouter":
            result = await OpenRouterProvider.run_model(
                "black-forest-labs/flux.2-pro",
                {"prompt": prompt, "aspect_ratio": aspect_ratio},
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                content = result["choices"][0]["message"]["content"]
                return [content]
            return result

        elif provider.lower() == "rapidapi":
            result = await RapidAPIProvider.run_model(
                "image-generation",
                {
                    "prompt": prompt,
                    "endpoint": "https://midjourney-api.p.rapidapi.com/imagine",
                    "host": "midjourney-api.p.rapidapi.com",
                },
                tier,
            )
            return result

        elif provider.lower() == "aimlapi":
            result = await AIMLAPIProvider.run_model(
                "stabilityai/stable-diffusion-xl-base-1.0",
                {"prompt": prompt, "aspect_ratio": aspect_ratio, "n": num_outputs},
                tier,
            )
            if isinstance(result, dict) and "data" in result:
                return [img.get("url") for img in result["data"] if img.get("url")]
            return result

        elif provider.lower() == "nvidia":
            result = await NVIDIAProvider.run_model(
                "nvidia/sdxl",
                {"prompt": prompt, "aspect_ratio": aspect_ratio, "n": num_outputs},
                tier,
            )
            if isinstance(result, dict) and "data" in result:
                return [img.get("url") for img in result["data"] if img.get("url")]
            return result

        elif provider.lower() == "huggingface":
            # Using Flux Schnell on Hugging Face as a high-quality default
            result = await HuggingFaceProvider.run_model(
                "black-forest-labs/FLUX.1-schnell",
                {
                    "inputs": prompt,
                },
                tier,
            )
            return result

        else:  # Default to Tensor.art
            # Map standard aspect ratios to Tensor.art format if needed
            result = await TensorProvider.run_model(
                "flux-schnell-model-id",  # Replace with actual Tensor model ID
                {"prompt": prompt, "aspectRatio": aspect_ratio, "count": num_outputs},
                tier,
            )
            return result

    @staticmethod
    async def generate_video(
        prompt: str,
        tier: int,
        provider: str = "fal",
        avatar_id: str = None,
        voice_id: str = None,
    ):
        provider = (provider or "fal").strip().lower() or "fal"

        if provider == "krea":
            return await KreaProvider.run_model("krea-video-gen-v1", {"prompt": prompt}, tier)

        elif provider.lower() == "kling":
            # Kling AI Video Generation (Direct Provider)
            result = await KlingProvider.generate_video(
                {
                    "prompt": prompt,
                    "mode": "text2video",
                    "duration": 5,
                    "aspect_ratio": "16:9",
                },
                starting_tier=tier,
            )
            return result

        elif provider.lower() == "segmind":
            # Segmind AnimateDiff (Free daily text-to-video)
            return await SegmindProvider.run_model(
                "animatediff",
                {"prompt": prompt, "num_inference_steps": 25, "guidance_scale": 7.5},
                tier,
            )

        elif provider.lower() == "fal":
            # Fal Wan2.1 (Sora-level ultra-realistic video generation)
            result = await FalProvider.run_model(
                "fal-ai/wan/wan2.1/t2v/1.3b", {"prompt": prompt}, tier
            )
            # Returns a dictionary with the video URL
            if isinstance(result, dict) and "video" in result:
                return result["video"]["url"]
            return result

        elif provider.lower() == "genspark":
            return await GensparkProvider.generate_video(prompt, tier)

        elif provider.lower() == "pixverse":
            # Pixverse Video Generation
            return await PixverseProvider.run_model(
                {
                    "model": "pixverse/v5/image-to-video",  # Update based on pixverse actual requirements
                    "prompt": prompt,
                },
                tier,
            )

        elif provider.lower() == "heygen":
            selected_avatar = avatar_id or "josh_lite_20230714"
            selected_voice = voice_id or "2d5a6e6cca974c128d022b7d2ab67f78"
            payload = {
                "video_inputs": [
                    {
                        "character": {
                            "avatar_id": selected_avatar,
                            "avatar_style": "normal",
                        },
                        "voice": {
                            "type": "text",
                            "input_text": prompt,
                            "voice_id": selected_voice,
                        },
                    }
                ],
                "dimension": {"width": 1280, "height": 720},
                "title": "API Avatar Video",
            }
            return await HeyGenProvider.run_model(payload, tier)

        elif provider.lower() == "d-id":
            selected_source_url = (
                avatar_id
                if (avatar_id and avatar_id.startswith("http"))
                else "https://d-id-public-bucket.s3.amazonaws.com/or-roman.jpg"
            )
            selected_voice = voice_id or "en-US-JennyNeural"
            payload = {
                "source_url": selected_source_url,
                "script": {
                    "type": "text",
                    "subtitles": "false",
                    "provider": {"type": "microsoft", "voice_id": selected_voice},
                    "input": prompt,
                },
                "config": {"fluent": "false", "pad_audio": "0.0"},
            }
            return await DIDProvider.run_model(payload, tier)

        # ---- PiAPI Video Models ----
        elif provider.lower() == "kling":
            return await PiAPIProvider.generate_video_kling(prompt, tier)

        elif provider.lower() == "luma":
            return await PiAPIProvider.generate_video_luma(prompt, tier)

        elif provider.lower() == "hailuo":
            return await PiAPIProvider.generate_video_hailuo(prompt, tier)

        elif provider.lower() == "wan":
            return await PiAPIProvider.generate_video_wan(prompt, tier)

        elif provider.lower() == "sora":
            return await PiAPIProvider.generate_video_sora(prompt, tier)

        elif provider.lower() == "veo":
            return await PiAPIProvider.generate_video_veo(prompt, tier)

        elif provider.lower() == "seedance":
            return await PiAPIProvider.generate_video_seedance(prompt, tier)

        elif provider.lower() == "hunyuan":
            return await PiAPIProvider.generate_video_hunyuan(prompt, tier)

        elif provider.lower() == "openrouter":
            return await OpenRouterProvider.run_model(
                "x-ai/grok-imagine-video", {"prompt": prompt}, tier
            )

        elif provider.lower() == "chutes":
            return await ChutesProvider.run_model("ltx-video", {"prompt": prompt}, tier)

        elif provider.lower() == "bytez":
            return await BytezProvider.run_model(
                "bytedance/animatediff-lightning-rect-4step", {"prompt": prompt}, tier
            )

        elif provider.lower() == "nvidia":
            return await NVIDIAProvider.run_model("nvidia/cosmos-1.0", {"prompt": prompt}, tier)

        # Default Video Generation routes to Replicate Provider
        return await ReplicateProvider.run_model("luma", "ray", {"prompt": prompt}, tier)

    @staticmethod
    def _normalize_text_generation_result(result):
        if isinstance(result, list):
            return "".join(result)
        if isinstance(result, dict) and "choices" in result:
            return result["choices"][0]["message"]["content"]
        return result

    @staticmethod
    async def _generate_text_with_provider(
        provider_name: str,
        provider_value: str,
        prompt: str,
        system_prompt: str,
        tier: int,
    ):
        if provider_name == "free":
            endpoint = "https://api.free.ai/v1/chat/completions"
            return await FreeProvider.run_model(
                "gpt-4o-mini",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "endpoint": endpoint,
                },
                tier,
            )

        if provider_name == "together":
            endpoint = "https://api.together.xyz/v1/chat/completions"
            return await TogetherProvider.run_model(
                "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "endpoint": endpoint,
                    "max_tokens": 1024,
                },
                tier,
            )

        if provider_name == "fireworks":
            endpoint = "https://api.fireworks.ai/inference/v1/chat/completions"
            return await FireworksProvider.run_model(
                "accounts/fireworks/models/llama-v3p1-8b-instruct",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "endpoint": endpoint,
                    "max_tokens": 1024,
                },
                tier,
            )

        if provider_name == "cloudflare":
            return await CloudflareProvider.run_model(
                "@cf/meta/llama-3-8b-instruct",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                },
                tier,
            )

        if provider_name == "wix":
            return await WixProvider.run_text_model(
                {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1024,
                },
                tier,
            )

        if provider_name == "ollama":
            result = await OllamaProvider.run_model(
                "llama3",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        if provider_name == "chutes":
            result = await ChutesProvider.run_model(
                "meta-llama/meta-llama-3.1-8b-instruct",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1024,
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        if provider_name == "huggingface":
            result = await HuggingFaceProvider.run_model(
                "meta-llama/Llama-3.2-3B-Instruct",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1024,
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        if provider_name == "superapi":
            result = await SuperAPIProvider.run_model(
                "https://api.superapi.ai/v1/chat/completions",
                {
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        if provider_name == "groq":
            result = await GroqProvider.run_model(
                "llama3-8b-8192",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1024,
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        if provider_name == "bytez":
            result = await BytezProvider.run_model(
                "meta-llama/Llama-3-8b",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        if provider_name == "openrouter":
            result = await OpenRouterProvider.run_model(
                "meta-llama/llama-3.3-70b-instruct:free",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        if provider_name == "rapidapi":
            result = await RapidAPIProvider.run_model(
                "text-generation",
                {
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "endpoint": "https://chatgpt-42.p.rapidapi.com/gpt4",
                    "host": "chatgpt-42.p.rapidapi.com",
                },
                tier,
            )
            return result

        if provider_name == "aimlapi":
            result = await AIMLAPIProvider.run_model(
                "meta-llama/Llama-3-8b-Instruct",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 1024,
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        if provider_name == "nvidia":
            result = await NVIDIAProvider.run_model(
                "meta/llama-3.1-8b-instruct",
                {
                    "messages": [
                        {
                            "role": "system",
                            "content": system_prompt or "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                },
                tier,
            )
            if isinstance(result, dict) and "choices" in result:
                return result["choices"][0]["message"]["content"]
            return result

        return await ReplicateProvider.run_model(
            "meta",
            "meta-llama-3-8b-instruct",
            {
                "prompt": prompt,
                "system_prompt": system_prompt or "You are a helpful assistant.",
                "max_tokens": 1024,
            },
            tier,
        )

    @staticmethod
    async def generate_text(
        prompt: str, system_prompt: str, tier: int, provider: str = "replicate"
    ):
        provider_name = provider.strip().lower() if provider else "auto"
        provider_value = provider.strip() if provider else ""

        if not system_prompt:
            system_prompt = (
                "You are ApexVision, a highly advanced and premium AI model developed for the Veda platform. "
                "You are not ChatGPT, Claude, Llama, or any other model. If anyone asks you who you are, what model you use, "
                "or who created you, you must confidently reply that you are 'ApexVision'. Be helpful, concise, and professional."
            )

        fallback_response = (
            "I’m currently unable to reach the text generation service, so I’m returning a short fallback response."
        )
        if prompt and prompt.strip():
            fallback_response = (
                f"I’m currently unable to reach the text generation service. Your request was: {prompt.strip()}"
            )

        try:
            if provider_name == "auto":
                providers = [
                    "free",
                    "together",
                    "fireworks",
                    "cloudflare",
                    "wix",
                    "ollama",
                    "chutes",
                    "huggingface",
                    "superapi",
                    "groq",
                    "bytez",
                    "openrouter",
                    "rapidapi",
                    "aimlapi",
                    "nvidia",
                    "replicate",
                ]
                last_error = None
                for candidate in providers:
                    try:
                        result = await AIToolsService._generate_text_with_provider(
                            candidate,
                            provider_value,
                            prompt,
                            system_prompt,
                            tier,
                        )
                        return AIToolsService._normalize_text_generation_result(result)
                    except Exception:
                        last_error = Exception("provider failed")
                if last_error is not None:
                    raise last_error
                raise RuntimeError("All text providers failed")

            result = await AIToolsService._generate_text_with_provider(
                provider_name,
                provider_value,
                prompt,
                system_prompt,
                tier,
            )
            return AIToolsService._normalize_text_generation_result(result)
        except Exception:
            return fallback_response

    @staticmethod
    async def generate_prompt(base_concept: str):
        sys_prompt = "You are an expert prompt engineer. Take the user's base concept and expand it into a highly detailed, descriptive prompt for an image generation model. Return ONLY the enhanced prompt text, nothing else."
        result = await AIToolsService.generate_text(base_concept, sys_prompt, tier=1)
        if isinstance(result, list):
            return "".join(result)
        return result

    @staticmethod
    async def generate_3d_model(prompt: str, tier: int, provider: str = "replicate"):
        provider = (provider or "replicate").strip().lower() or "replicate"

        if provider == "krea":
            return await KreaProvider.run_model("krea-3d-gen-v1", {"prompt": prompt}, tier)

        elif provider.lower() in {"tripo", "tripo3d", "tripo3d.ai"}:
            return await Tripo3DProvider.generate_model(prompt, tier)

        elif provider.lower() == "piapi" or provider.lower() == "trellis":
            return await PiAPIProvider.generate_3d_trellis(prompt, tier)

        return await ReplicateProvider.run_model("lumaai", "genie", {"prompt": prompt}, tier)

    @staticmethod
    async def generate_music(prompt: str, tier: int, provider: str = "suno"):
        """AI Music Generation via PiAPI (Suno / Udio)"""
        provider = (provider or "suno").strip().lower() or "suno"

        if provider == "udio":
            return await PiAPIProvider.generate_music_udio(prompt, tier)
        # Default to Suno
        return await PiAPIProvider.generate_music_suno(prompt, tier)

    @staticmethod
    async def generate_tts(text: str, voice: str, tier: int, provider: str = "auto"):
        provider = (provider or "auto").strip().lower() or "auto"

        # If user explicitly requests apexspeech
        if provider == "apexspeech":
            return await ApexSpeechProvider.run_model(text, voice)

        # If user explicitly requests fal or replicate, bypass TTSProvider custom routing
        elif provider.lower() == "fal":
            return await FalProvider.run_model("fal-ai/f5-tts", {"gen_text": text}, tier)
        elif provider.lower() == "replicate":
            return await ReplicateProvider.run_model(
                "lucataco",
                "xtts-v2",
                {
                    "text": text,
                    "speaker": voice
                    or "https://replicate.delivery/pbxt/JtIE45mG187GaCUF71zPjDL2ihU7Vf12Y46u2g2t0Gf1YF3M/en_sample.mp3",
                    "language": "en",
                },
                tier,
            )

        # Default 'auto' routes through the new ultra-realistic TTSProvider (ElevenLabs -> Fal F5 -> Replicate XTTS)
        return await TTSProvider.run_model(text, voice, tier)

    @staticmethod
    async def generate_wedding_card(
        groom_name: str, bride_name: str, date: str, venue: str, theme: str, tier: int
    ):
        base_prompt = f"A beautiful, elegant wedding invitation card design for {bride_name} and {groom_name}. Date: {date}. Venue: {venue}. "
        if theme:
            base_prompt += f"Theme: {theme}. "
        base_prompt += "High quality, professional graphic design, elegant typography, intricate borders, watercolor elements, masterpiece."

        return await AIToolsService.generate_image(base_prompt, "3:4", 1, tier)

    @staticmethod
    async def generate_logo(
        brand_name: str, niche: str, style: str, tier: int, provider: str = "auto"
    ):
        provider = (provider or "auto").strip().lower() or "auto"

        if provider == "logodev":
            return await LogoDevProvider.generate_logo(brand_name, niche, tier)

        prompt = f"A professional minimalist vector logo design for a {niche} brand named '{brand_name}'. "
        if style:
            prompt += f"Style: {style}. "
        prompt += "White background, simple, clean, corporate, scalable, modern, highly detailed, 8k resolution, flat vector art."

        return await AIToolsService.generate_image(prompt, "1:1", 1, tier)

    @staticmethod
    async def enhance_image(image_url: str, prompt: str, tier: int):
        return await ReplicateProvider.run_model(
            "tencentarc", "gfpgan", {"img": image_url, "scale": 2}, tier
        )

    @staticmethod
    async def generate_animation(
        prompt: str,
        image_url: str = None,
        video_url: str = None,
        tier: int = 1,
        provider: str = "fal",
    ):
        """VedaCLI: Advanced Animation Studio logic."""
        if provider == "fal":
            # Using AnimateDiff or similar via Fal
            result = await FalProvider.run_model(
                "fal-ai/animatediff", {"prompt": prompt, "image_url": image_url}, tier
            )
            return result.get("video", {}).get("url")
        elif provider == "kling":
            return await PiAPIProvider.generate_video_kling(prompt, tier)
        elif provider == "luma":
            return await PiAPIProvider.generate_video_luma(prompt, tier)

        # Default fallback
        return await AIToolsService.generate_video(prompt, tier, provider)

    @staticmethod
    async def generate_code(
        prompt: str, language: str = "python", tier: int = 1, provider: str = "groq"
    ):
        provider = (provider or "groq").strip().lower() or "groq"
        """VedaCLI: AI Code Generator logic."""
        system_prompt = f"You are an expert {language} developer. Return ONLY high-quality, documented code. Use markdown code blocks."
        return await AIToolsService.generate_text(prompt, system_prompt, tier, provider)

    @staticmethod
    async def generate_design(prompt: str, tier: int = 1, provider: str = "tensor"):
        """VedaCLI: AI Design Generator logic."""
        design_prompt = f"Professional modern graphic design for: {prompt}. High resolution, vector style, clean aesthetic, 8k."
        return await AIToolsService.generate_image(design_prompt, "1:1", 1, tier, provider)

    @staticmethod
    async def generate_ads(
        product_name: str,
        description: str,
        target_audience: str = None,
        tier: int = 1,
        provider: str = "groq",
    ):
        provider = (provider or "groq").strip().lower() or "groq"
        """VedaCLI: Apex Ads Generator logic."""
        target = f" targeting {target_audience}" if target_audience else ""
        prompt = f"Create a high-converting ad copy for {product_name}. Product Description: {description}.{target}"
        system_prompt = "You are a world-class ad copywriter. Create compelling, emotional, and persuasive ad copies that drive sales."
        return await AIToolsService.generate_text(prompt, system_prompt, tier, provider)

    @staticmethod
    async def generate_home_design(
        prompt: str, image_url: str = None, tier: int = 1, provider: str = "replicate"
    ):
        provider = (provider or "replicate").strip().lower() or "replicate"
        """VedaCLI Ultra: AI Home Design logic."""
        full_prompt = f"A professional architectural exterior design for a home: {prompt}. High resolution, photorealistic, 8k, architectural masterpiece."
        if image_url:
            # Using Image-to-Image for refinement
            return await ReplicateProvider.run_model(
                "stability-ai",
                "sdxl",  # Placeholder for actual architectural model
                {"prompt": full_prompt, "image": image_url, "prompt_strength": 0.7},
                tier,
            )
        return await AIToolsService.generate_image(full_prompt, "16:9", 1, tier, provider)

    @staticmethod
    async def generate_interior_design(
        prompt: str,
        room_type: str,
        style: str = "modern",
        image_url: str = None,
        tier: int = 1,
        provider: str = "replicate",
    ):
        provider = (provider or "replicate").strip().lower() or "replicate"
        """VedaCLI Ultra: AI Interior Design logic."""
        full_prompt = f"Professional {style} interior design for a {room_type}: {prompt}. High resolution, luxury aesthetic, photorealistic, 8k."
        if image_url:
            return await ReplicateProvider.run_model(
                "stability-ai",
                "sdxl",
                {"prompt": full_prompt, "image": image_url, "prompt_strength": 0.6},
                tier,
            )
        return await AIToolsService.generate_image(full_prompt, "16:9", 1, tier, provider)

    @staticmethod
    async def generate_home_map(
        prompt: str, plot_size: str = None, tier: int = 1, provider: str = "replicate"
    ):
        provider = (provider or "replicate").strip().lower() or "replicate"
        """VedaCLI Ultra: AI Home Map Generator logic."""
        plot_info = f" on a {plot_size} plot" if plot_size else ""
        full_prompt = f"A detailed professional 2D architectural floor plan / home map for: {prompt}{plot_info}. Blueprints style, technical drawing, high resolution."
        return await AIToolsService.generate_image(full_prompt, "4:3", 1, tier, provider)

    @staticmethod
    async def generate_color_suggestions(prompt: str, tier: int = 1, provider: str = "groq"):
        provider = (provider or "groq").strip().lower() or "groq"
        """VedaCLI Ultra: AI Color Suggestions for Home/Design."""
        system_prompt = "You are a professional interior designer and architectural color consultant. Provide a detailed color palette (with HEX codes) and styling advice based on the user's description. Return ONLY a structured JSON response."
        return await AIToolsService.generate_text(prompt, system_prompt, tier, provider)

    @staticmethod
    async def edit_3d_model(model_url: str, prompt: str, tier: int = 1, provider: str = "meshy"):
        """VedaCLI Max/Ultra: AI 3D Model Edit logic."""
        if provider == "meshy":
            from ..connectors.meshy_provider import MeshyProvider

            return await MeshyProvider.edit_model(model_url, prompt, tier)
        # Default to a generic error or placeholder
        return "3D Model editing currently only supported via Meshy provider."
