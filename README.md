# xdevkeys

Gestion des clés API (`xdk_...`) et des clés de signature HMAC pour les
développeurs XCore. Authentifie le CLI xcore et signe les plugins publiés.
Consommé principalement en interne, via IPC, par `xdeploy` et
`xdeployments`.

## Fonctionnalités

- CRUD clés API développeur
- Clé de signature HMAC (publication de plugins)
- Projets rattachés à une clé
- Flow *device code* (authentification CLI sans navigateur)
- Actions IPC : authentification par clé brute, vérification de
  `deployment_credential`, vérification de propriété de projet, récupération
  du secret de signature

## Dépendances

| Plugin requis | Version |
|---|---|
| `auth` | `>=1.0.0` |

## Configuration — secret

```dotenv
DEVKEYS_MASTER_KEY=<clé maître déchiffrant les signing keys en base>
```

Doit résoudre à la même valeur que côté `xservices` (même variable
d'environnement plateforme).

Détail complet des routes et des actions IPC : [INTEGRATION.md](INTEGRATION.md).
