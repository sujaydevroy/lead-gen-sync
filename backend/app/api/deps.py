"""Request dependencies: database session, authenticated user, CSRF and role checks."""

from __future__ import annotations

import ipaddress
import secrets
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.security import ACCESS_COOKIE, CSRF_COOKIE, CSRF_HEADER, decode_access_token
from app.models import Company, User
from app.services.auth_service import get_active_user

# Lets the Swagger UI "Authorize" button obtain a bearer token from /auth/token.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass
class AuthContext:
    user: User
    company: Company


def get_auth(request: Request, db: Session = Depends(get_db), bearer: str | None = Depends(oauth2_scheme)) -> AuthContext:
    token = bearer or request.cookies.get(ACCESS_COOKIE)
    payload = decode_access_token(token) if token else None
    if payload is None:
        raise ApiError(401, "Not authenticated.", headers={"WWW-Authenticate": "Bearer"})

    # Cookie-authenticated, state-changing requests must echo the CSRF cookie in a header.
    if bearer is None and request.method not in SAFE_METHODS:
        cookie, header = request.cookies.get(CSRF_COOKIE), request.headers.get(CSRF_HEADER)
        if not cookie or not header or not secrets.compare_digest(cookie, header):
            raise ApiError(403, "Missing or invalid CSRF token.")

    user = get_active_user(db, int(payload["sub"]))
    if user is None or user.company_id != payload.get("cid"):
        raise ApiError(401, "Not authenticated.", headers={"WWW-Authenticate": "Bearer"})
    db.info["user_id"] = user.id  # read by the audit-column hook in app/models/base.py
    return AuthContext(user=user, company=user.company)


def require_role(*roles: str):
    def checker(auth: AuthContext = Depends(get_auth)) -> AuthContext:
        if auth.user.role.name not in roles:
            raise ApiError(403, "You do not have permission to perform this action.")
        return auth

    return checker


def client_ip(request: Request) -> str | None:
    """Peer IP address, or None when the host isn't a valid IP (it is stored in an INET column)."""
    host = request.client.host if request.client else None
    try:
        return str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        return None
