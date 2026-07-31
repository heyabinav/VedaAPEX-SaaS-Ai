Owner/Model: krea/Krea-2
Provider routing: `krea/*` routes to `KreaProvider` with the `model_id` passed as first arg.

Usage example (POST to `/ai/generate/image`):

{
  "prompt": "a stylized portrait in watercolor",
  "provider": "krea/Krea-2",
  "num_outputs": 1,
  "aspect_ratio": "1:1",
  "tier": 1
}

Notes:
- Krea provider may require `KREA_API_KEY` or similar keys in `.env` depending on provider implementation.
- Krea outputs handling differs from Hugging Face; check `app/services/providers/krea_provider.py` for specifics.
