from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.project import Project

_KINDS = ("plugin", "service", "xdeploy")


def _generate_xdeploy_slug() -> str:
    """`prj_<hex>` — format attendu par xcore-agent's ProjectManifest/InstallPlan
    (schema/manifest.py: `^prj_[A-Za-z0-9]{10,40}$`). Contrairement à un projet
    plugin/service (slug = celui déjà choisi côté marketplace/xservices), un
    projet xdeploy n'a pas de slug "naturel" préexistant — le Hub en émet un,
    comme le prévoyait le contrat original (identifiants opaques émis par le Hub)."""
    return f"prj_{secrets.token_hex(16)}"


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, owner_id: str, name: str, kind: str, slug: str) -> Project:
        if kind not in _KINDS:
            raise ValueError(f"kind doit être l'un de : {', '.join(_KINDS)}")
        if kind == "xdeploy":
            # Le slug demandé (s'il y en a un) est ignoré — voir _generate_xdeploy_slug.
            slug = _generate_xdeploy_slug()
        record = Project(owner_id=owner_id, name=name, kind=kind, slug=slug)
        self._s.add(record)
        try:
            await self._s.flush()
        except IntegrityError as exc:
            raise ValueError(
                f"Vous avez déjà un projet pour {kind} '{slug}'."
            ) from exc
        return record

    async def list_by_owner(self, owner_id: str) -> list[Project]:
        result = await self._s.execute(
            select(Project).where(Project.owner_id == owner_id).order_by(Project.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, project_id: str) -> Project | None:
        return await self._s.get(Project, project_id)

    async def get_by_slug(self, slug: str) -> Project | None:
        """Les artefacts .xdeploy référencent le projet par slug (prj_<hex>,
        opaque, émis par le Hub — voir _generate_xdeploy_slug), pas par id
        (XDeployArtifact.project_id, référence molle inter-plugin) — d'où ce
        lookup distinct de get()."""
        return await self._s.scalar(select(Project).where(Project.slug == slug))

    async def delete(self, project_id: str, owner_id: str) -> bool:
        """Supprime le projet — échoue (False) si des clés API y sont encore
        rattachées, pour ne jamais laisser une ApiKey.project_id orpheline."""
        record = await self._s.scalar(
            select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
        )
        if record is None:
            return False

        from ..models.api_key import ApiKey

        active_key = await self._s.scalar(
            select(ApiKey.id).where(ApiKey.project_id == project_id, ApiKey.is_active == True)  # noqa: E712
        )
        if active_key is not None:
            raise ValueError(
                "Ce projet a encore des clés API actives — révoquez-les d'abord."
            )

        await self._s.delete(record)
        return True
