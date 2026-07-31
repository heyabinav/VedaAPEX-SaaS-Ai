Owner/Model: stabilityai/stable-diffusion-3.5-large
Provider routing: treated as Hugging Face Space identifier and routed to `HuggingFaceProvider`.

Usage example (POST to `/ai/generate/image`):

{
  "prompt": "photorealistic portrait of a woman",
  "provider": "stabilityai/stable-diffusion-3.5-large",
  "num_outputs": 1,
  "aspect_ratio": "4:3",
  "tier": 1
}

Notes:
- Needs `HUGGING_FACE_API_KEY` in `.env` if the Space requires authentication.
- Outputs may require normalization depending on the Space response schema.
