"""
serializers/serializers.py — Pydantic serializers (DRF-style).

Purpose:
  - Input validation:   incoming request body / query params
  - Output serialization: domain dicts → JSON response
  - OpenAPI schema generation: Swagger UI type information

Named "serializers" (not schemas) to match Django REST Framework convention
where the primary job is converting data between Python objects and JSON.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Node Serializers ──────────────────────────────────────────────────────────

class NodeCreateSerializer(BaseModel):
    """Validates POST /nodes request body."""
    name: str = Field(..., min_length=1, max_length=255, examples=["ServerA"])

    @field_validator("name")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Node name cannot be blank.")
        return v


class NodeSerializer(BaseModel):
    """Serializes a node for API response."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: datetime


# ── Edge Serializers ──────────────────────────────────────────────────────────

class EdgeCreateSerializer(BaseModel):
    """Validates POST /edges request body."""
    source: str = Field(..., min_length=1, max_length=255, examples=["ServerA"])
    destination: str = Field(..., min_length=1, max_length=255, examples=["ServerB"])
    latency: float = Field(..., gt=0, description="Latency in milliseconds (must be > 0)", examples=[12.5])

    @field_validator("source", "destination")
    @classmethod
    def strip_names(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Node name cannot be blank.")
        return v

    @field_validator("destination")
    @classmethod
    def must_differ_from_source(cls, v: str, info) -> str:
        if info.data.get("source") == v:
            raise ValueError("Source and destination must be different nodes.")
        return v


class EdgeSerializer(BaseModel):
    """Serializes an edge for API response."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    destination: str
    latency: float
    created_at: datetime


# ── Route Serializers ─────────────────────────────────────────────────────────

class RouteRequestSerializer(BaseModel):
    """Validates POST /routes/shortest/ request body."""
    source: str = Field(..., min_length=1, max_length=255, examples=["ServerA"])
    destination: str = Field(..., min_length=1, max_length=255, examples=["ServerD"])

    @field_validator("source", "destination")
    @classmethod
    def strip_names(cls, v: str) -> str:
        return v.strip()


class RouteResponseSerializer(BaseModel):
    """Serializes a route result for API response."""
    path: list[str]
    total_latency: float
    hops: int


class RouteHistorySerializer(BaseModel):
    """Serializes a single history record."""
    id: int
    source: str
    destination: str
    path: list[str]
    total_latency: float | None
    success: bool
    algorithm_used: str
    created_at: datetime


# ── Error Serializer ──────────────────────────────────────────────────────────

class ErrorSerializer(BaseModel):
    """Standard error response envelope."""
    detail: str
