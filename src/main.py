"""xdevkeys — API Keys & Signing Keys pour les développeurs xcore."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from xcore.sdk import AutoDispatchMixin, TrustedBase
from xcore.services.database.migrations import MigrationRunner

from .ipc import IPCCommands
from .models import Base
from .routes import api_keys_router, device_router, projects_router, signing_keys_router

logger = logging.getLogger("hub.xdevkeys")


class Plugin(IPCCommands, AutoDispatchMixin, TrustedBase):
    async def on_load(self) -> None:
        self.app = APIRouter()
        db = self.get_service("db")
        cache = self.get_service("cache")
        env = self.ctx.env

        # Repris tel quel de app/auth/src/main.py — même convention, même
        # variable d'env (déjà déployée pour les liens d'invitation/reset).
        app_base_url = env.get("APP_BASE_URL", "http://localhost:8000")
        web_app_url = env.get("WEB_APP_URL") or app_base_url

        master_key_hex = env.get("DEVKEYS_MASTER_KEY", "")
        if not master_key_hex:
            logger.warning("[xdevkeys] DEVKEYS_MASTER_KEY absent — clés de signature non chiffrées !")
            master_key = b"insecure-dev-key-change-in-prod!"
        else:
            master_key = bytes.fromhex(master_key_hex) if len(master_key_hex) == 64 else master_key_hex.encode()

        # Tables
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("[xdevkeys] Tables créées / vérifiées")

        # Expose master_key to IPC handlers
        self._master_key = master_key
        self._db = db
        self._cache = cache

        # Routes
        self.app.include_router(projects_router(db))
        self.app.include_router(api_keys_router(db))
        self.app.include_router(signing_keys_router(db, master_key))
        self.app.include_router(device_router(db, master_key, cache, web_app_url))

        logger.info("[xdevkeys] Prêt — /projects  /api-keys  /signing-key  /device")

    async def on_unload(self) -> None:
        logger.info("[xdevkeys] Déchargé")

    def get_router(self) -> APIRouter | None:
        return self.app
