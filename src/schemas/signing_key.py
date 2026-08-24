from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SigningKeySet(BaseModel):
    label: Optional[str] = "default"
    # Si absent → le serveur en génère un
    secret: Optional[str] = None


class SigningKeyOut(BaseModel):
    id: str
    label: str
    created_at: datetime
    updated_at: datetime
    configured: bool = True

    model_config = {"from_attributes": True}


class SigningKeyCreated(SigningKeyOut):
    """Retourné une seule fois à la création/rotation — contient le secret brut."""
    secret: str
