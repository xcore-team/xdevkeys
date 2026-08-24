# Intégration — xdevkeys

## 1. Rôle

Gestion des clés API (`xdk_...`) et des clés de signature HMAC pour les
développeurs XCore. Authentifie le CLI xcore et signe les plugins publiés.
Consommé principalement en interne, via IPC, par `xdeploy` et
`xdeployments` — pas de dépendance déclarée dans son propre `plugin.yaml`
au-delà de `auth`.

## 2. Dépendances (`plugin.yaml` → `requires`)

| Plugin requis | Version |
|---|---|
| `auth` | `>=1.0.0` |

## 3. Routes exposées (préfixe `/xdevkeys`)

| Sous-préfixe | Fichier | Domaine |
|---|---|---|
| `/api-keys` | `routes/api_keys.py` | CRUD clés API développeur |
| `/signing-key` | `routes/signing_keys.py` | Clé de signature HMAC (publication de plugins) |
| `/projects` | `routes/projects.py` | Projets rattachés à une clé (xdeploy, xdevkeys) |
| `/device` | `routes/device.py` | Flow *device code* (auth CLI sans navigateur) |

## 4. Actions IPC (`call_plugin("xdevkeys", action, payload)`)

```python
await self.call_plugin("xdevkeys", "devkeys.authenticate", {"raw_key": "xdk_..."})
# → {"user_id", "key_id", "project_id", "project_kind", "project_slug", "is_personal"}
```

| Action | Payload | Usage |
|---|---|---|
| `devkeys.authenticate` | `raw_key` | Résout une clé API brute en identité + projet |
| `devkeys.verify_deployment_credential` | `project_id, deployment_credential` | Utilisé par `xdeploy` (`POST /v1/deployments/authorize`) — second secret distinct du xdevkey |
| `devkeys.check_project_owner` | `project_slug, user_id` | Utilisé par `xdeploy` (`routes/dev.py`) — vérifie la propriété avant de lister/supprimer des artefacts |
| `devkeys.get_signing_secret` | `user_id` | Récupère le secret de signature HMAC configuré |

## 5. Variables d'environnement — ⚠️ secret

```dotenv
DEVKEYS_MASTER_KEY=<clé maître déchiffrant les signing keys en base>
```

Doit résoudre à la **même valeur** que côté `xservices` (même variable
d'environnement plateforme, référencée deux fois — voir leurs `plugin.yaml`
respectifs). Injectée par `docker-entrypoint.sh` depuis `.env.template` au
démarrage — **ne jamais committer `.env`**.
