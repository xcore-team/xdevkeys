from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator


class ManifestItem(BaseModel):
    kind: str  # "plugin" | "service"
    slug: str
    version: Optional[str] = None

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in ("plugin", "service"):
            raise ValueError("kind doit être 'plugin' ou 'service'")
        return v


class ManifestCreate(BaseModel):
    tag: str
    items: List[ManifestItem] = []


class ManifestOut(BaseModel):
    id: str
    project_id: str
    tag: str
    items: List[ManifestItem]
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
