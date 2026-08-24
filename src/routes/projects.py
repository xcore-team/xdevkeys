from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from xcore.kernel.api import AuthPayload, get_current_user

from ..schemas.project import ProjectCreate, ProjectOut
from ..schemas.project_manifest import ManifestCreate, ManifestOut
from ..services.project import ProjectService
from ..services.project_manifest import ProjectManifestService


def projects_router(db: Any) -> APIRouter:
    router = APIRouter(prefix="/projects", tags=["devkeys"])

    @router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
    async def create_project(
        body: ProjectCreate,
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        """Crée un projet de déploiement — la cible qu'une clé API pourra
        ensuite être seule à pouvoir installer/déployer (une clé = un projet)."""
        async with db.session() as session:
            try:
                project = await ProjectService(session).create(
                    owner_id=user["sub"], name=body.name, kind=body.kind, slug=body.slug
                )
                await session.commit()
                await session.refresh(project)
                return project
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc))

    @router.get("", response_model=List[ProjectOut])
    async def list_projects(
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        """Liste les projets de déploiement du développeur connecté."""
        async with db.session() as session:
            return await ProjectService(session).list_by_owner(user["sub"])

    @router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_project(
        project_id: str,
        user: AuthPayload = Depends(get_current_user),
    ) -> None:
        """Supprime un projet — refusé tant que des clés API actives y sont rattachées."""
        async with db.session() as session:
            try:
                deleted = await ProjectService(session).delete(project_id, user["sub"])
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc))
            if not deleted:
                raise HTTPException(status_code=404, detail="Projet introuvable")
            await session.commit()

    # ── Manifeste déclaratif (plan des plugins/services à installer) ────────
    #
    # Ne remplace pas l'artefact .xdeploy scellé (le Hub ne voit jamais son
    # contenu réel) — juste une référence en clair, éditable ici, avec des
    # liens vers les fiches marketplace des composants. Voir
    # models/project_manifest.py.

    @router.post(
        "/{project_id}/manifests", response_model=ManifestOut, status_code=status.HTTP_201_CREATED
    )
    async def create_manifest(
        project_id: str,
        body: ManifestCreate,
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        """Enregistre une nouvelle version (tag) du manifeste — immuable une
        fois créée, comme les artefacts .xdeploy eux-mêmes."""
        async with db.session() as session:
            project = await ProjectService(session).get(project_id)
            if project is None or project.owner_id != user["sub"]:
                raise HTTPException(status_code=404, detail="Projet introuvable")
            try:
                manifest = await ProjectManifestService(session).create(
                    project_id=project_id,
                    tag=body.tag,
                    items=[i.model_dump() for i in body.items],
                    created_by=user["sub"],
                )
                await session.commit()
                await session.refresh(manifest)
                return manifest
            except ValueError as exc:
                raise HTTPException(status_code=409, detail=str(exc))

    @router.get("/{project_id}/manifests", response_model=List[ManifestOut])
    async def list_manifests(
        project_id: str,
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        async with db.session() as session:
            project = await ProjectService(session).get(project_id)
            if project is None or project.owner_id != user["sub"]:
                raise HTTPException(status_code=404, detail="Projet introuvable")
            return await ProjectManifestService(session).list_for_project(project_id)

    @router.get("/{project_id}/manifests/latest", response_model=ManifestOut)
    async def latest_manifest(
        project_id: str,
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        async with db.session() as session:
            project = await ProjectService(session).get(project_id)
            if project is None or project.owner_id != user["sub"]:
                raise HTTPException(status_code=404, detail="Projet introuvable")
            manifest = await ProjectManifestService(session).latest(project_id)
            if manifest is None:
                raise HTTPException(status_code=404, detail="Aucun manifeste pour ce projet")
            return manifest

    return router
