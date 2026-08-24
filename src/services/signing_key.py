from __future__ import annotations

import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.signing_key import SigningKey
from .crypto import decrypt_secret, encrypt_secret


class SigningKeyService:
    def __init__(self, session: AsyncSession, master_key: bytes) -> None:
        self._s = session
        self._master = master_key

    async def set_key(self, user_id: str, secret: str, label: str = "default") -> SigningKey:
        """Crée ou remplace le signing key du développeur."""
        encrypted = encrypt_secret(secret, self._master, user_id)
        existing = await self._s.scalar(
            select(SigningKey).where(SigningKey.user_id == user_id)
        )
        if existing:
            existing.secret_encrypted = encrypted
            existing.label = label
            existing.updated_at = datetime.utcnow()
            return existing
        record = SigningKey(user_id=user_id, label=label, secret_encrypted=encrypted)
        self._s.add(record)
        await self._s.flush()
        return record

    async def get_info(self, user_id: str) -> Optional[SigningKey]:
        return await self._s.scalar(
            select(SigningKey).where(SigningKey.user_id == user_id)
        )

    async def get_secret(self, user_id: str) -> Optional[str]:
        """Retourne le secret déchiffré (usage interne pipeline uniquement)."""
        record = await self.get_info(user_id)
        if record is None:
            return None
        return decrypt_secret(record.secret_encrypted, self._master, user_id)

    async def delete(self, user_id: str) -> bool:
        record = await self._s.scalar(
            select(SigningKey).where(SigningKey.user_id == user_id)
        )
        if record is None:
            return False
        await self._s.delete(record)
        return True

    @staticmethod
    def generate_secret() -> str:
        """Génère un secret HMAC aléatoire de 32 octets (hex)."""
        return secrets.token_hex(32)
