from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Project(Base):
    """Un projet de déploiement — la cible (plugin/service) qu'une clé API
    est autorisée à installer/déployer. Une clé API est rattachée à UN seul
    projet (voir ApiKey.project_id) : révoquer la clé coupe l'accès à ce
    projet précis, sans affecter les autres projets/clés du même développeur.

    (owner_id, kind, slug) plutôt que (kind, slug) seul : un plugin public
    peut être déployé par plusieurs opérateurs différents, chacun avec son
    propre projet et son propre suivi — mais un même développeur ne peut pas
    créer deux projets pour la même cible.
    """

    __tablename__ = "devkeys_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # "plugin" | "service"
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("owner_id", "kind", "slug", name="uq_devkeys_project_owner_target"),
        Index("ix_devkeys_project_owner", "owner_id"),
    )
