from __future__ import annotations

import secrets

# Modélisé sur OAuth 2.0 Device Authorization Grant (RFC 8628) : un
# device_code long et aléatoire (jamais affiché, détenu uniquement par le
# CLI) et un user_code court, saisi à la main par l'utilisateur dans le
# navigateur. Pures fonctions, sans I/O — testables isolément, le stockage
# TTL (Redis via CacheService) vit dans routes/device.py.


def generate_device_code() -> str:
    return secrets.token_urlsafe(48)


def generate_user_code() -> str:
    """Exactement 6 chiffres, tel que demandé — ex: '042817'."""
    return f"{secrets.randbelow(1_000_000):06d}"


def device_cache_key(device_code: str) -> str:
    return f"devicecode:{device_code}"


def user_cache_key(user_code: str) -> str:
    return f"usercode:{user_code}"
