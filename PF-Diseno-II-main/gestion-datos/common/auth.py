"""Validación de JWT para SSO (Keycloak, Microsoft Entra, Google, etc.)."""
from __future__ import annotations
import os
from typing import Optional
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from jwt import PyJWKClient
except ImportError:
    PyJWKClient = getattr(jwt, "PyJWKClient", None)

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
JWKS_URL = os.getenv("JWKS_URL", "")
ISSUER = os.getenv("OIDC_ISSUER") or None

_bearer = HTTPBearer(auto_error=False)
_jwks_client: Optional[PyJWKClient] = None


def get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None and JWKS_URL and PyJWKClient:
        _jwks_client = PyJWKClient(JWKS_URL, cache_keys=True)
    return _jwks_client


def get_user(cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)) -> str:
    if not AUTH_ENABLED:
        # En modo desarrollo sin auth obligatoria, permite pasar usuario en header o usa 'dev-user'
        if cred and cred.credentials:
            try:
                unverified = jwt.decode(cred.credentials, options={"verify_signature": False})
                return (
                    unverified.get("preferred_username")
                    or unverified.get("name")
                    or unverified.get("email")
                    or "sso-user"
                )
            except Exception:
                pass
        return "dev-user"

    if not cred or not cred.credentials:
        raise HTTPException(401, "Falta el token de autenticación (Bearer Token SSO requerido)")

    client = get_jwks_client()
    if not client:
        raise HTTPException(500, "El servicio de autenticación SSO no está configurado (falta JWKS_URL)")

    try:
        signing_key = client.get_signing_key_from_jwt(cred.credentials)
        decode_opts = {"verify_aud": False}
        if not ISSUER:
            decode_opts["verify_iss"] = False

        claims = jwt.decode(
            cred.credentials,
            signing_key.key,
            algorithms=["RS256"],
            issuer=ISSUER,
            options=decode_opts
        )
    except Exception as exc:
        raise HTTPException(401, f"Token SSO inválido o vencido: {exc}")

    return claims.get("preferred_username") or claims.get("name") or claims.get("email") or claims.get("sub", "sso-user")
