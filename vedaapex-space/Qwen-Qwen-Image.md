Owner/Model: Qwen/Qwen-Image
Provider routing: treated as Hugging Face Space identifier and routed to `HuggingFaceProvider`.

Usage example (POST to `/ai/generate/image`):

{
  "prompt": "illustration of a robot reading a book",
  "provider": "Qwen/Qwen-Image",
  "num_outputs": 1,
  "aspect_ratio": "1:1",
  "tier": 1
}

Notes:
- Add `HUGGING_FACE_API_KEY` to `.env` if required.
