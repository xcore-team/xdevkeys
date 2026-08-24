from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from xcore.kernel.api import AuthPayload, get_current_user

from ..schemas.device import DeviceConfirmIn, DevicePollOut, DeviceStartOut
from ..services.api_key import ApiKeyService
from ..services.device_code import (
    device_cache_key,
    generate_device_code,
    generate_user_code,
    user_cache_key,
)
from ..services.signing_key import SigningKeyService

# Modélisé sur OAuth 2.0 Device Authorization Grant (RFC 8628) : `xcli login`
# ouvre `verification_uri` avec le user_code pré-rempli, l'utilisateur
# confirme dans le navigateur (déjà authentifié là-bas), le CLI poll jusqu'à
# obtenir la clé personnelle + le signing key. Aucune table SQL — l'état est
# entièrement éphémère (TTL) dans le service `cache` partagé (Redis), pas en
# mémoire process (server.workers: 4 dans integration.yaml — un state en
# mémoire locale ne serait visible que d'un worker sur quatre).
_TTL_PENDING = 600   # 10 min pour compléter l'étape navigateur
_TTL_CONFIRMED = 120  # fenêtre courte pour que le CLI récupère au prochain poll
_POLL_INTERVAL = 3


def device_router(db: Any, master_key: bytes, cache: Any, web_app_url: str) -> APIRouter:
    router = APIRouter(prefix="/device", tags=["devkeys-device"])

    @router.post("/start", response_model=DeviceStartOut)
    async def start() -> Any:
        device_code = generate_device_code()
        user_code = generate_user_code()
        # Garde-fou anti-collision — improbable avec seulement 1M de codes à
        # 6 chiffres et un TTL court, mais coût négligeable à vérifier.
        for _ in range(5):
            if not await cache.exists(user_cache_key(user_code)):
                break
            user_code = generate_user_code()

        record = {"status": "pending", "user_code": user_code, "user_id": None}
        await cache.set(device_cache_key(device_code), record, ttl=_TTL_PENDING)
        await cache.set(user_cache_key(user_code), device_code, ttl=_TTL_PENDING)

        return DeviceStartOut(
            device_code=device_code,
            user_code=user_code,
            verification_uri=f"{web_app_url}/cli/confirm",
            expires_in=_TTL_PENDING,
            interval=_POLL_INTERVAL,
        )

    @router.post("/confirm")
    async def confirm(
        body: DeviceConfirmIn,
        user: AuthPayload = Depends(get_current_user),
    ) -> Any:
        """Redemande explicite du navigateur, déjà authentifié — associe le
        user_code saisi à cet utilisateur et fait naître la clé personnelle.
        Doit rester un clic explicite côté frontend, jamais auto-soumis au
        chargement de la page (sinon un simple lien piégé, ouvert dans un
        onglet où l'utilisateur est déjà connecté, suffirait à détourner un
        `xcli login` en cours)."""
        device_code = await cache.get(user_cache_key(body.user_code))
        if device_code is None:
            raise HTTPException(status_code=404, detail="Code invalide ou expiré.")

        record = await cache.get(device_cache_key(device_code))
        if record is None or record.get("status") != "pending":
            raise HTTPException(status_code=409, detail="Ce code a déjà été utilisé ou a expiré.")

        async with db.session() as session:
            key_service = ApiKeyService(session)
            signing_service = SigningKeyService(session, master_key)

            _, raw_key = await key_service.create_personal(user["sub"])

            signing_secret = await signing_service.get_secret(user["sub"])
            if signing_secret is None:
                signing_secret = SigningKeyService.generate_secret()
                await signing_service.set_key(user["sub"], signing_secret)

            await session.commit()

        record.update({
            "status": "confirmed",
            "user_id": user["sub"],
            "api_key": raw_key,
            "signing_key": signing_secret,
        })
        await cache.set(device_cache_key(device_code), record, ttl=_TTL_CONFIRMED)
        await cache.delete(user_cache_key(body.user_code))  # à usage unique

        return {"status": "ok"}

    @router.get("/poll", response_model=DevicePollOut)
    async def poll(device_code: str = Query(...)) -> Any:
        """Le device_code lui-même est le secret porteur (long, aléatoire,
        jamais affiché) — pas d'authentification supplémentaire nécessaire
        ici, comme dans tout flux device-code OAuth."""
        record = await cache.get(device_cache_key(device_code))
        if record is None:
            raise HTTPException(status_code=404, detail="Requête expirée ou introuvable.")

        if record.get("status") == "pending":
            return DevicePollOut(status="pending")

        # Révélé une seule fois — même sous polling, un second appel après
        # une confirmation réussie doit 404, jamais re-servir le secret.
        await cache.delete(device_cache_key(device_code))
        return DevicePollOut(
            status="confirmed",
            api_key=record["api_key"],
            signing_key=record["signing_key"],
        )

    return router
