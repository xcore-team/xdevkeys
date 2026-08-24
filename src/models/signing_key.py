from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class SigningKey(Base):
    __tablename__ = "devkeys_signing_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    # Un seul signing key actif par user — remplacé à chaque POST
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    # Secret HMAC chiffré (XOR stream cipher + PBKDF2 — déchiffré côté serveur uniquement)
    secret_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_devkeys_signing_key_user", "user_id"),)
