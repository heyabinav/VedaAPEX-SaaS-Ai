Owner/Model: black-forest-labs/FLUX.2-dev
Provider routing: treated as Hugging Face Space identifier and routed to `HuggingFaceProvider`.

Usage example (POST to `/ai/generate/image`):

{
  "prompt": "a fantasy landscape",
  "provider": "black-forest-labs/FLUX.2-dev",
  "num_outputs": 1,
  "aspect_ratio": "1:1",
  "tier": 1
}

Notes:
- Ensure `HUGGING_FACE_API_KEY` is present in `.env` for Hugging Face API access.
- Model outputs may be returned as base64 or URLs depending on the Space implementation.
