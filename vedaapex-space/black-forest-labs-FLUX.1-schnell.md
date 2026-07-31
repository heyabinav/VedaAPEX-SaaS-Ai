Owner/Model: black-forest-labs/FLUX.1-schnell
Provider routing: treated as Hugging Face Space identifier and routed to `HuggingFaceProvider` (or other providers where mapped).

Usage example (POST to `/ai/generate/image`):

{
  "prompt": "high-res landscape",
  "provider": "black-forest-labs/FLUX.1-schnell",
  "num_outputs": 1,
  "aspect_ratio": "1:1",
  "tier": 1
}

Notes:
- This model is used elsewhere as `flux-schnell` across providers; check `ai_service` mappings.
