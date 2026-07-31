"""
Database models for AI-generated assets, usage logs, error logs, and system metrics.
"""

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class AIAsset(SQLModel, table=True):
    """Metadata for every AI-generated asset stored in Cloudflare R2."""
    __tablename__ = "ai_asset"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)

    asset_type: str = Field(index=True)  # images, videos, audio, documents
    provider: str = Field(index=True)
    model: Optional[str] = None

    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    resolution: Optional[str] = None
    seed: Optional[int] = None

    original_url: Optional[str] = None  # Third-party URL (never exposed to frontend)
    r2_object_key: str = Field(index=True)
    r2_bucket: Optional[str] = None
    proxy_url: str  # Own domain URL: /api/v1/assets/{id}

    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    file_hash: Optional[str] = None  # SHA-256 for dedup

    generation_time_ms: Optional[int] = None
    status: str = Field(default="completed")  # pending, completed, failed
    error_message: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AIProviderUsageLog(SQLModel, table=True):
    """Log every AI provider API call for tracking, billing, and debugging."""
    __tablename__ = "ai_provider_usage_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    request_id: Optional[str] = Field(default=None, index=True)

    provider: str = Field(index=True)
    model: Optional[str] = None
    endpoint: Optional[str] = None
    generation_type: Optional[str] = None  # IMAGE, VIDEO, TEXT, TTS, etc.

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None

    status: str = Field(default="success")  # success, failed, timeout
    error_message: Optional[str] = None
    status_code: Optional[int] = None

    duration_ms: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    request_payload_hash: Optional[str] = None  # Hash of request payload for dedup
    response_size_bytes: Optional[int] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ErrorLog(SQLModel, table=True):
    """Structured error logging for monitoring and alerting."""
    __tablename__ = "error_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    request_id: Optional[str] = Field(default=None, index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)

    error_code: str = Field(index=True)
    error_type: str
    message: str
    detail: Optional[str] = None

    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    stack_trace: Optional[str] = None
    status_code: int = 500

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SystemMetrics(SQLModel, table=True):
    """System-level metrics for the admin dashboard."""
    __tablename__ = "system_metrics"

    id: Optional[int] = Field(default=None, primary_key=True)
    metric_name: str = Field(index=True)
    metric_value: float
    metric_unit: Optional[str] = None
    tags: Optional[str] = None  # JSON string for additional context
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


AIAsset.model_rebuild()
AIProviderUsageLog.model_rebuild()
ErrorLog.model_rebuild()
SystemMetrics.model_rebuild()
