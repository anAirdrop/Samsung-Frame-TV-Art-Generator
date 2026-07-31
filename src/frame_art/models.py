"""Pydantic request/response models for the API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request body for the /api/generate endpoint."""

    description: str = Field(..., min_length=3, description="Image description")
    room: str = Field(..., min_length=1, description="Room name / TV location")
    api_key: str = Field(..., min_length=1, description="Webhook API key")
    model: Optional[str] = Field(
        None, description="Override the configured fal.ai model endpoint"
    )

    model_config = {"extra": "forbid"}


class GenerateResponse(BaseModel):
    """Successful response from the /api/generate endpoint."""

    status: str = "success"
    message: str
    image_description: str
    tv: str
    duration_seconds: float


class ErrorResponse(BaseModel):
    """Error response body."""

    status: str = "error"
    message: str
    code: str
