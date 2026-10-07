"""Passwords, tokens and auth cookies."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Response
from pwdlib import PasswordHash

from app.core.config import get_settings

ACCESS_COOKIE = "dcp_access"
REFRESH_COOKIE = "dcp_refresh"
CSRF_COOKIE = "dcp_csrf"
CSRF_HEADER = "X-CSRF-Token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

_password_hash = PasswordHash.recommended()  # Argon2id
# Verified against when the email is unknown, so response time doesn't reveal which emails exist.
_DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")

MIN_PASSWORD_LENGTH = 8


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:  # malformed hash
        return False


def new_token() -> str:
    """Random URL-safe token (256 bits)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Tokens are stored only as SHA-256 hashes."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def now_utc() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: int, company_id: int) -> tuple[str, datetime]:
    settings = get_settings()
    expires = now_utc() + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": str(user_id), "cid": company_id, "type": "access", "exp": expires, "iat": now_utc()}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), expires


def decode_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        return None
    return payload if payload.get("type") == "access" else None


def set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str, csrf_token: str, remember: bool, session_expires: datetime
) -> None:
    settings = get_settings()
    common = {"secure": settings.cookie_secure, "samesite": "lax"}
    # Without "Remember me" the refresh/CSRF cookies are browser-session cookies.
    persistent = {"expires": session_expires} if remember else {}
    response.set_cookie(
        ACCESS_COOKIE, access_token, httponly=True, path="/", max_age=settings.access_token_minutes * 60, **common
    )
    response.set_cookie(REFRESH_COOKIE, refresh_token, httponly=True, path=REFRESH_COOKIE_PATH, **persistent, **common)
    # Readable by the frontend so it can echo it in the X-CSRF-Token header (double-submit).
    response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, path="/", **persistent, **common)


def clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    for name, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, REFRESH_COOKIE_PATH), (CSRF_COOKIE, "/")):
        response.delete_cookie(name, path=path, secure=settings.cookie_secure, samesite="lax")
