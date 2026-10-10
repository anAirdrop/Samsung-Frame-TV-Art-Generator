"""Validated API request and response models."""

from __future__ import annotations

from pydantic import BaseModel, Field, IPvAnyAddress

from .storage import JobStatus


class GenerateRequest(BaseModel):
    """Request body for a queued image generation."""

    description: str = Field(min_length=3, max_length=2000)
    room: str = Field(min_length=1, max_length=100)

    model_config = {"extra": "forbid"}


class JobAcceptedResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    description: str
    room: str
    created_at: str
    updated_at: str


class SetupRequest(BaseModel):
    fal_key: str = Field(
        min_length=8,
        max_length=500,
        pattern=r"^[^\r\n]+$",
    )
    room_name: str = Field(min_length=1, max_length=100)
    tv_host: IPvAnyAddress
    tv_port: int = Field(default=8002, ge=1, le=65535)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    test_prompt: str = Field(
        default="a peaceful landscape at golden hour",
        min_length=3,
        max_length=2000,
    )

    model_config = {"extra": "forbid"}


class SetupResponse(BaseModel):
    status: str
    room: str
    api_key: str
    test_prompt: str


class DiscoveredTV(BaseModel):
    host: str
    name: str
    model: str
    frame_support: bool
