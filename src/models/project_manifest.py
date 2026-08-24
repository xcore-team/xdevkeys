from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ProjectManifest(Base):
    """Manifeste déclaratif (en clair) d'un projet de déploiement — la liste
    des plugins/services que ce projet est censé installer, avec leur
    version. Ne remplace PAS l'artefact `.xdeploy` scellé lui-même (voir
    app/xdeploy) : le Hub ne voit jamais son contenu réel, chiffré de bout
    en bout par xcore-agent au moment du build. Ce manifeste est le plan de
    référence — éditable ici pour la visibilité et les liens vers les
    fiches marketplace des composants — pas une garantie cryptographique de
    ce qui est effectivement scellé dans l'artefact publié sous ce tag.

    Versionné par tag (même convention que les artefacts `.xdeploy`
    eux-mêmes, voir app/xdeploy/src/models/artifact.py) — immuable une fois
    créé, chaque enregistrement est une nouvelle version nommée plutôt
    qu'une ligne mutable.
    """

    __tablename__ = "devkeys_project_manifests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devkeys_projects.id"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(64), nullable=False)
    # [{"kind": "plugin"|"service", "slug": str, "version": str|None}, ...]
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("project_id", "tag", name="uq_devkeys_manifest_project_tag"),
        Index("ix_devkeys_manifest_project_created", "project_id", "created_at"),
    )
