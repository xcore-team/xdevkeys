from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    # Absent/null → clé "personnelle" (voir ApiKeyService.create_personal) :
    # jusqu'ici réservée au flux xcli login (routes/device.py), maintenant
    # aussi possible directement depuis POST /api-keys — voir routes/
    # api_keys.py::create_api_key pour le routage entre create()/
    # create_personal() selon la présence de ce champ.
    project_id: Optional[str] = None


class ApiKeyOut(BaseModel):
    id: str
    name: str
    project_id: Optional[str] = None
    prefix: str
    is_active: bool
    is_personal: bool = False
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyOut):
    """Retourné une seule fois à la création — contient la clé brute."""
    key: str
    # Uniquement pour un projet kind="xdeploy" — voir ApiKey.deployment_credential_hash.
    deployment_credential: Optional[str] = None
