from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from xcore.kernel.api import AuthPayload, get_current_user

from ..schemas.signing_key import SigningKeyCreated, SigningKeyOut, SigningKeySet
from ..services.signing_key import SigningKeyService


def signing_keys_router(db: Any, master_key: bytes) -> APIRouter:
    router = APIRouter(prefix="/signing-key", tags=["devkeys"])

    @router.post("", response_model=SigningKeyCreated, status_code=status.HTTP_201_CREATED)
    async def set_signing_key(
        body: SigningKeySet,
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        """
        Crée ou remplace le signing key HMAC.
        Si `secret` est absent, le serveur en génère un aléatoire.
        Le secret est retourné une seule fois — notez-le immédiatement.
        """
        secret = body.secret or SigningKeyService.generate_secret()
        async with db.session() as session:
            svc = SigningKeyService(session, master_key)
            record = await svc.set_key(user["sub"], secret, body.label or "default")
            await session.commit()
            await session.refresh(record)
            return SigningKeyCreated(
                id=record.id,
                label=record.label,
                created_at=record.created_at,
                updated_at=record.updated_at,
                secret=secret,
            )

    @router.get("", response_model=SigningKeyOut)
    async def get_signing_key(
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        """Statut du signing key (sans le secret)."""
        async with db.session() as session:
            record = await SigningKeyService(session, master_key).get_info(user["sub"])
            if record is None:
                raise HTTPException(status_code=404, detail="Aucune clé de signature configurée")
            return record

    @router.delete("", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_signing_key(
        user: AuthPayload = Depends(get_current_user),
    ) -> None:
        """Supprime le signing key."""
        async with db.session() as session:
            deleted = await SigningKeyService(session, master_key).delete(user["sub"])
            if not deleted:
                raise HTTPException(status_code=404, detail="Aucune clé de signature configurée")
            await session.commit()

    return router
