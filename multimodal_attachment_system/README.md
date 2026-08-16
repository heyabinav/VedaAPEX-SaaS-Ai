# Multimodal Attachment System

This folder contains a production-oriented, backend-only attachment implementation that can be integrated into VedaApex without changing the existing text-only chat flow.

## Included modules
- `config.py` — centralized attachment settings
- `validator.py` — MIME, extension, size, and sanitization validation
- `storage.py` — secure temp-file handling and cleanup
- `processor.py` — image and document preprocessing logic
- `models.py` — attachment metadata models
- `ai_provider_base.py` — provider abstraction
- `providers/` — provider adapters for vision-capable models
- `chat_multimodal_service.py` — unified multimodal chat service

## Key principles
- Keep all file handling server-side
- Preserve backward compatibility with text-only chat
- Validate before trusting file content
- Clean up temporary files in finally blocks
- Support multipart form-data without replacing the existing auth or provider router
