"""IPC actions exposées par xdevkeys aux autres plugins."""
from __future__ import annotations

from xcore.sdk import AutoDispatchMixin, action, error, ok, validate_payload

_AUTH_SCHEMA = {"raw_key": (str, ...)}
_SECRET_SCHEMA = {"user_id": (str, ...)}
_DEPLOYMENT_CREDENTIAL_SCHEMA = {"project_id": (str, ...), "deployment_credential": (str, ...)}
_PROJECT_OWNER_SCHEMA = {"project_slug": (str, ...), "user_id": (str, ...)}


class IPCCommands(AutoDispatchMixin):
    """
    Actions disponibles via call_plugin("xdevkeys", action, payload).

        await self.call_plugin("xdevkeys", "devkeys.authenticate", {"raw_key": "xdk_..."})
        await self.call_plugin("xdevkeys", "devkeys.get_signing_secret", {"user_id": "..."})
    """

    @action("devkeys.authenticate")
    @validate_payload(_AUTH_SCHEMA, type_response="model", unset=False)
    async def _ipc_authenticate(self, payload) -> dict:
        try:
            async with self._db.session() as session:
                from .models.project import Project
                from .services.api_key import ApiKeyService
                record = await ApiKeyService(session).authenticate(payload.raw_key)
                if record is None:
                    return error("Clé API invalide ou révoquée", code="unauthorized")
                await session.commit()
                # Une clé sans projet (émise avant l'introduction des projets)
                # reste authentifiable mais project_id/kind/slug restent None —
                # aux appelants scopés-projet (install, deployments/report) de
                # décider s'ils l'acceptent ou l'exigent explicitement.
                project_kind = None
                project_slug = None
                if record.project_id:
                    project = await session.get(Project, record.project_id)
                    if project:
                        project_kind = project.kind
                        project_slug = project.slug
                return ok(
                    user_id=record.user_id,
                    key_id=record.id,
                    project_id=record.project_id,
                    project_kind=project_kind,
                    project_slug=project_slug,
                    is_personal=record.is_personal,
                )
        except Exception as exc:
            return error(str(exc), code="error")

    @action("devkeys.verify_deployment_credential")
    @validate_payload(_DEPLOYMENT_CREDENTIAL_SCHEMA, type_response="model", unset=False)
    async def _ipc_verify_deployment_credential(self, payload) -> dict:
        """Utilisé par app/xdeploy (POST /v1/deployments/authorize) — vérifie
        le second secret (deployment_credential) d'un projet xdeploy, distinct
        du xdevkey. Par project_id, pas par clé brute : à ce point du flux
        xcore-agent a déjà échangé son xdevkey contre un jeton de session
        (POST /v1/auth), il ne le renvoie plus — voir ApiKeyService.
        verify_deployment_credential_for_project pour le raisonnement complet."""
        try:
            async with self._db.session() as session:
                from .services.api_key import ApiKeyService
                valid = await ApiKeyService(session).verify_deployment_credential_for_project(
                    payload.project_id, payload.deployment_credential
                )
                return ok(valid=valid)
        except Exception as exc:
            return error(str(exc), code="error")

    @action("devkeys.check_project_owner")
    @validate_payload(_PROJECT_OWNER_SCHEMA, type_response="model", unset=False)
    async def _ipc_check_project_owner(self, payload) -> dict:
        """Utilisé par app/xdeploy (routes/dev.py, gestion navigateur des
        artefacts .xdeploy) — vérifie que l'utilisateur JWT courant possède
        bien le projet référencé par slug (prj_<hex>) avant de lister/
        supprimer ses artefacts. xdeploy ne référence les projets que par
        slug (référence molle inter-plugin, voir models/artifact.py), d'où
        project_slug plutôt que project_id ici."""
        try:
            async with self._db.session() as session:
                from .services.project import ProjectService
                project = await ProjectService(session).get_by_slug(payload.project_slug)
                if project is None:
                    return error("Projet introuvable", code="not_found")
                return ok(owned=project.owner_id == payload.user_id)
        except Exception as exc:
            return error(str(exc), code="error")

    @action("devkeys.get_signing_secret")
    @validate_payload(_SECRET_SCHEMA, type_response="model", unset=False)
    async def _ipc_get_signing_secret(self, payload) -> dict:
        try:
            async with self._db.session() as session:
                from .services.signing_key import SigningKeyService
                secret = await SigningKeyService(session, self._master_key).get_secret(payload.user_id)
                if secret is None:
                    return error("Aucune clé de signature configurée", code="not_found")
                return ok(secret=secret)
        except Exception as exc:
            return error(str(exc), code="error")
