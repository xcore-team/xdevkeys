from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from xcore.kernel.api import AuthPayload, get_current_user

from ..schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from ..services.api_key import ApiKeyService


def api_keys_router(db: Any) -> APIRouter:
    router = APIRouter(prefix="/api-keys", tags=["devkeys"])

    @router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
    async def create_api_key(
        body: ApiKeyCreate,
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        """
        Sans project_id : génère une clé "personnelle" (ApiKeyService.
        create_personal) — jusqu'ici réservée au flux xcli login, exposée
        ici pour ne plus obliger un détour par la CLI juste pour ça ; elle
        n'accorde rien qu'un `xcli login` n'accordait déjà (même self-service,
        aucune permission élevée des deux côtés).
        Avec project_id : clé rattachée à ce projet — ne pourra installer/
        déployer QUE sa cible. Le secret est affiché une seule fois.
        """
        async with db.session() as session:
            svc = ApiKeyService(session)
            try:
                if body.project_id:
                    record, raw_key, raw_credential = await svc.create(
                        user_id=user["sub"], name=body.name, project_id=body.project_id
                    )
                else:
                    record, raw_key = await svc.create_personal(user_id=user["sub"], name=body.name)
                    raw_credential = None
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
            await session.commit()
            await session.refresh(record)
            return ApiKeyCreated(
                id=record.id,
                name=record.name,
                project_id=record.project_id,
                prefix=record.prefix,
                is_active=record.is_active,
                is_personal=record.is_personal,
                created_at=record.created_at,
                last_used_at=record.last_used_at,
                key=raw_key,
                deployment_credential=raw_credential,
            )

    @router.get("", response_model=List[ApiKeyOut])
    async def list_api_keys(
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        """Liste les clés API actives du développeur connecté."""
        async with db.session() as session:
            return await ApiKeyService(session).list_by_user(user["sub"])

    @router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def revoke_api_key(
        key_id: str,
        user: AuthPayload = Depends(get_current_user),
    ) -> None:
        """Révoque (désactive) une clé API."""
        async with db.session() as session:
            revoked = await ApiKeyService(session).revoke(key_id, user["sub"])
            if not revoked:
                raise HTTPException(status_code=404, detail="Clé introuvable")
            await session.commit()

    return router
