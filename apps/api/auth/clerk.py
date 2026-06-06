"""Clerk session-token verification.

Verification uses only the *public* JWKS (no secret key): the publishable key
encodes the Clerk Frontend API host, from which we derive the issuer + JWKS URL
and verify the RS256 session JWT. `sub` is the stable Clerk user id.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from apps.api.src.settings import settings


def _frontend_api_host() -> str | None:
    """Decode the Frontend API host from the publishable key, which is
    `pk_(test|live)_<base64url(host + '$')>`."""
    key = settings.clerk_publishable_key
    if not key or "_" not in key:
        return None
    try:
        b64 = key.split("_", 2)[2]
        decoded = base64.b64decode(b64 + "==").decode("utf-8")
        host = decoded.rstrip("$").strip()
        return host or None
    except Exception:
        return None


def clerk_configured() -> bool:
    """Whether accounts are enabled (a usable publishable key is set)."""
    return _frontend_api_host() is not None


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient | None:
    host = _frontend_api_host()
    return PyJWKClient(f"https://{host}/.well-known/jwks.json") if host else None


def verify_token(token: str) -> dict[str, Any] | None:
    """Return the verified claims (incl. `sub`) or None if invalid / unconfigured."""
    host = _frontend_api_host()
    client = _jwks_client()
    if host is None or client is None:
        return None
    try:
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=f"https://{host}",
            # Clerk session tokens carry no `aud`; `azp` is the origin (not checked).
            options={"verify_aud": False},
            leeway=10,
        )
    except Exception:
        return None
