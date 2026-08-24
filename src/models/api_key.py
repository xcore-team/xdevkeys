from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ApiKey(Base):
    __tablename__ = "devkeys_api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # Projet de déploiement auquel cette clé est rattachée — une clé ne peut
    # installer/déployer QUE la cible (kind, slug) de ce projet (voir
    # routes/install.py, app/xdeployments/src/routes/deployments.py).
    # Nullable au niveau DB pour ne pas casser les clés déjà émises avant
    # l'introduction des projets (create_all() n'altère pas les tables
    # existantes) — mais requis désormais à la création (ApiKeyService.create).
    # Une clé project_id=NULL reste utilisable pour l'auth générique (IPC
    # devkeys.authenticate) mais est refusée par tout endpoint scopé projet.
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("devkeys_projects.id"), nullable=True, index=True
    )
    # Affiché dans les listes : "xdk_ab12cd34"
    prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    # SHA-256 de la clé complète
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Second secret, distinct de la clé elle-même — uniquement pour un projet
    # kind="xdeploy" (voir app/xdeploy). Vérifié à POST /v1/deployments/authorize,
    # séparément de xdevkey (POST /v1/auth) : une défense en profondeur
    # délibérée — voir agent/hub_client.py's docstring côté xcore-agent, "the
    # Hub is the only party that ever holds the KEK ... a revoked XDevKey or
    # expired deployment credential must be rejected here, before any bytes
    # are decrypted". NULL pour les projets plugin/service.
    deployment_credential_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Clé "personnelle" — pas de projet, obtenue uniquement via le flux
    # xcli login (routes/device.py), jamais via POST /api-keys. Authentifie
    # comme un user_id nu et est acceptée par _resolve_api_key_for_plugin/
    # _resolve_api_key_for_service pour N'IMPORTE QUEL plugin/service public
    # (le contrôle de visibilité privé, déjà basé sur user_id seul, continue
    # de s'appliquer normalement). Ne pas confondre avec project_id=NULL
    # ci-dessus : ce cas legacy reste explicitement refusé, is_personal=False
    # par défaut sur toute clé existante.
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_devkeys_api_key_hash", "key_hash"),
        Index("ix_devkeys_api_key_user", "user_id"),
    )
