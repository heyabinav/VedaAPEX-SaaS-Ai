from dataclasses import dataclass
from typing import Any, Callable

FREE_PROVIDER_CHAINS = {
    "text": [
        "free",
        "openrouter",
        "huggingface",
        "groq",
        "cloudflare",
        "together",
        "bytez",
        "nvidia",
    ],
    "image": [
        "cloudflare",
        "segmind",
        "krea",
        "tensor",
        "freepik",
        "imagenart",
        "pollinations",
    ],
    "video": ["segmind", "bytez", "chutes", "nvidia"],
}

PREMIUM_PROVIDER_CHAINS = {
    "text": ["fireworks", "wix", "superapi", "aimlapi", "replicate"],
    "image": [
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
    ],
    "video": [
        "fal",
        "replicate",
        "kling",
        "pixverse",
        "heygen",
        "d-id",
        "luma",
        "hailuo",
        "wan",
        "sora",
        "veo",
        "seedance",
        "hunyuan",
        "openrouter",
    ],
}


@dataclass
class RoutedGenerationResult:
    result: Any
    provider: str | None
    route_mode: str


class SmartGenerationService:
    @staticmethod
    def supports_free_first(gen_type: str, kwargs: dict[str, Any]) -> bool:
        return gen_type.lower() in FREE_PROVIDER_CHAINS and "provider" in kwargs

    @staticmethod
    def _ordered_providers(
        gen_type: str,
        providers: list[str],
        preferred_provider: str | None,
    ) -> list[str]:
        if not preferred_provider or preferred_provider.lower() == "auto":
            return providers

        preferred = preferred_provider.lower()
        if preferred in providers:
            return [preferred] + [provider for provider in providers if provider != preferred]
        return providers

    @staticmethod
    async def run_route(
        gen_type: str,
        generation_func: Callable[..., Any],
        kwargs: dict[str, Any],
        route_mode: str,
        preferred_provider: str | None = None,
    ) -> RoutedGenerationResult:
        providers = (
            FREE_PROVIDER_CHAINS.get(gen_type.lower(), [])
            if route_mode == "free"
            else PREMIUM_PROVIDER_CHAINS.get(gen_type.lower(), [])
        )
        providers = SmartGenerationService._ordered_providers(
            gen_type,
            list(providers),
            preferred_provider,
        )

        last_error = None
        for provider in providers:
            try:
                result = await generation_func(**{**kwargs, "provider": provider})
                return RoutedGenerationResult(
                    result=result, provider=provider, route_mode=route_mode
                )
            except Exception as exc:
                last_error = exc
                continue

        if (
            route_mode == "premium"
            and preferred_provider
            and preferred_provider.lower() not in {"auto", ""}
        ):
            result = await generation_func(**{**kwargs, "provider": preferred_provider})
            return RoutedGenerationResult(
                result=result,
                provider=preferred_provider.lower(),
                route_mode=route_mode,
            )

        raise Exception(
            f"All {route_mode} providers failed for {gen_type}. " f"Last error: {last_error}"
        )
