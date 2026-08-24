from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    project_id: str


class ApiKeyOut(BaseModel):
    id: str
    name: str
    project_id: Optional[str] = None
    prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyOut):
    """Retourné une seule fois à la création — contient la clé brute."""
    key: str
    # Uniquement pour un projet kind="xdeploy" — voir ApiKey.deployment_credential_hash.
    deployment_credential: Optional[str] = None
