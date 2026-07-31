from pydantic import BaseModel
from typing import Optional, Any


class CanvaDesignRequest(BaseModel):
    prompt: Optional[str] = None
    voice_transcript: Optional[str] = None
    input_type: Optional[str] = "text"  # text or voice
    title: Optional[str] = None
    template_id: Optional[str] = None
    style: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    design_payload: Optional[dict[str, Any]] = None

    def get_prompt(self) -> str:
        if self.prompt:
            return self.prompt
        if self.voice_transcript:
            return self.voice_transcript
        raise ValueError("Either prompt or voice_transcript must be provided.")
