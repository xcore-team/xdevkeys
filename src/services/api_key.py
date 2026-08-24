from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.api_key import ApiKey
from ..models.project import Project


_PREFIX = "xdk_"


def _generate_raw() -> str:
    return _PREFIX + secrets.token_urlsafe(48)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _make_prefix(raw: str) -> str:
    # "xdk_" + les 8 premiers chars du token
    return raw[:12]


class ApiKeyService:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create(self, user_id: str, name: str, project_id: str) -> tuple[ApiKey, str, Optional[str]]:
        """Génère une clé rattachée à `project_id` et retourne (record, raw_key,
        raw_deployment_credential). raw_key (et le credential, s'il y en a un)
        affichés une seule fois. La clé ne pourra ensuite installer/déployer
        que la cible (kind, slug) de ce projet précis.

        Un projet kind="xdeploy" reçoit en plus un deployment_credential —
        voir ApiKey.deployment_credential_hash. Les projets plugin/service
        n'en ont pas besoin (pas de DEK à débloquer)."""
        project = await self._s.get(Project, project_id)
        if project is None or project.owner_id != user_id:
            raise ValueError("Projet introuvable.")

        raw = _generate_raw()
        raw_credential: Optional[str] = None
        credential_hash: Optional[str] = None
        if project.kind == "xdeploy":
            raw_credential = secrets.token_urlsafe(32)
            credential_hash = _hash_key(raw_credential)

        record = ApiKey(
            user_id=user_id,
            name=name,
            project_id=project_id,
            prefix=_make_prefix(raw),
            key_hash=_hash_key(raw),
            deployment_credential_hash=credential_hash,
        )
        self._s.add(record)
        await self._s.flush()
        return record, raw, raw_credential

    async def create_personal(self, user_id: str, name: str = "xcli login") -> tuple[ApiKey, str]:
        """Génère une clé "personnelle" — sans projet, obtenue uniquement via
        le flux device-code (routes/device.py), jamais via create() ci-dessus
        ni son endpoint POST /api-keys. Authentifie comme user_id seul et est
        acceptée par _resolve_api_key_for_plugin/_resolve_api_key_for_service
        pour n'importe quel plugin/service PUBLIC — le contrôle de visibilité
        privé, déjà basé sur user_id seul dans ces deux routes, continue de
        s'appliquer sans modification. Pas de deployment_credential : hors
        scope pour app/xdeploy, qui n'appelle jamais ces deux resolvers."""
        raw = _generate_raw()
        record = ApiKey(
            user_id=user_id,
            name=name,
            project_id=None,
            prefix=_make_prefix(raw),
            key_hash=_hash_key(raw),
            is_personal=True,
        )
        self._s.add(record)
        await self._s.flush()
        return record, raw

    async def verify_deployment_credential_for_project(
        self, project_slug: str, deployment_credential: str
    ) -> bool:
        """Vérifie `deployment_credential` par PROJET, pas par clé brute — au
        moment de POST /v1/deployments/authorize, le client xcore-agent ne
        renvoie plus le xdevkey (il a déjà été échangé contre un jeton de
        session à /v1/auth, voir services/token.py côté app/xdeploy), donc
        on ne peut pas re-hasher/comparer contre "la" clé sans la clé brute.
        On cherche plutôt une ApiKey active, de kind xdeploy, dont le
        deployment_credential_hash correspond, rattachée à ce project_id."""
        import hmac as _hmac

        given_hash = _hash_key(deployment_credential)
        project = await self._s.scalar(
            select(Project).where(Project.slug == project_slug, Project.kind == "xdeploy")
        )
        if project is None:
            return False
        candidates = await self._s.execute(
            select(ApiKey).where(
                ApiKey.project_id == project.id,
                ApiKey.is_active == True,  # noqa: E712
                ApiKey.deployment_credential_hash.is_not(None),
            )
        )
        return any(
            _hmac.compare_digest(given_hash, row.deployment_credential_hash)
            for row in candidates.scalars().all()
        )

    async def list_by_user(self, user_id: str) -> list[ApiKey]:
        result = await self._s.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id, ApiKey.is_active == True)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, key_id: str, user_id: str) -> bool:
        record = await self._s.scalar(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        if record is None:
            return False
        record.is_active = False
        return True

    async def authenticate(self, raw_key: str) -> Optional[ApiKey]:
        """Vérifie la clé brute — met à jour last_used_at si valide."""
        key_hash = _hash_key(raw_key)
        record = await self._s.scalar(
            select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        )
        if record:
            record.last_used_at = datetime.utcnow()
        return record
