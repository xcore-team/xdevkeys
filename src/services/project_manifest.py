from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.project_manifest import ProjectManifest

_ITEM_KINDS = ("plugin", "service")


class ProjectManifestService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(
        self, project_id: str, tag: str, items: list[dict], created_by: str
    ) -> ProjectManifest:
        for item in items:
            if item.get("kind") not in _ITEM_KINDS:
                raise ValueError(f"kind doit être l'un de : {', '.join(_ITEM_KINDS)}")
            if not item.get("slug"):
                raise ValueError("slug requis pour chaque élément du manifeste")

        record = ProjectManifest(
            project_id=project_id, tag=tag, items=items, created_by=created_by
        )
        self._s.add(record)
        try:
            await self._s.flush()
        except IntegrityError as exc:
            raise ValueError(f"Le tag '{tag}' existe déjà pour ce projet.") from exc
        return record

    async def list_for_project(self, project_id: str) -> list[ProjectManifest]:
        result = await self._s.execute(
            select(ProjectManifest)
            .where(ProjectManifest.project_id == project_id)
            .order_by(ProjectManifest.created_at.desc())
        )
        return list(result.scalars().all())

    async def latest(self, project_id: str) -> ProjectManifest | None:
        return await self._s.scalar(
            select(ProjectManifest)
            .where(ProjectManifest.project_id == project_id)
            .order_by(ProjectManifest.created_at.desc())
            .limit(1)
        )
