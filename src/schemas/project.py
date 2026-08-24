from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator


class ProjectCreate(BaseModel):
    name: str
    kind: str  # "plugin" | "service" | "xdeploy"
    # Ignoré pour kind="xdeploy" — le Hub émet un identifiant opaque
    # (prj_<hex>), voir ProjectService._generate_xdeploy_slug.
    slug: str = ""

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in ("plugin", "service", "xdeploy"):
            raise ValueError("kind doit être 'plugin', 'service' ou 'xdeploy'")
        return v


class ProjectOut(BaseModel):
    id: str
    name: str
    kind: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}
