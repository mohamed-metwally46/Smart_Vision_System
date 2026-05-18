"""
core/security.py
────────────────
Authentication and authorisation for the Smart Vision System.

Future implementation — Phase 4 (auth sprint)
──────────────────────────────────────────────
Authentication is NOT enabled in Phase 1 or 2 (api-reference.md §2).
This file contains placeholder interfaces that will be filled in Phase 4.

Planned implementation:
  - JWT access tokens (HS256, configurable secret + expiry)
  - Role-based access control: admin / operator / viewer
  - FastAPI security dependencies (OAuth2PasswordBearer)
  - Password hashing via passlib[bcrypt]

Planned public API
──────────────────
  create_access_token(data, expires_delta) → str
  decode_access_token(token) → dict
  get_current_user(token)    → UserOut  (FastAPI dependency)
  require_role(role)         → Callable  (FastAPI dependency factory)
  hash_password(plain)       → str
  verify_password(plain, hashed) → bool

Configuration (future, add to config.py):
  JWT_SECRET_KEY   — strong random string
  JWT_ALGORITHM    — "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES — default 60

Usage (future — not yet active):
    from backend.app.core.security import get_current_user
    @router.get("/protected")
    async def protected(user = Depends(get_current_user)):
        ...
"""

from __future__ import annotations


class AuthNotImplementedError(NotImplementedError):
    """Raised when auth helpers are called before Phase 4 implementation."""


def create_access_token(data: dict, expires_delta=None) -> str:
    raise AuthNotImplementedError("JWT auth not yet implemented.")


def decode_access_token(token: str) -> dict:
    raise AuthNotImplementedError("JWT auth not yet implemented.")


def hash_password(plain: str) -> str:
    raise AuthNotImplementedError("JWT auth not yet implemented.")


def verify_password(plain: str, hashed: str) -> bool:
    raise AuthNotImplementedError("JWT auth not yet implemented.")


async def get_current_user(token: str):
    raise AuthNotImplementedError("JWT auth not yet implemented.")
