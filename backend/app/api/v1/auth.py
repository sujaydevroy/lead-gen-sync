from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import client_ip
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.rate_limit import RateLimiter
from app.core.security import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    clear_auth_cookies,
    create_access_token,
    decode_access_token,
    set_auth_cookies,
)
from app.schemas.auth import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest, TokenResponse
from app.schemas.common import MessageResponse
from app.schemas.user import SessionResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@lru_cache
def login_limiter() -> RateLimiter:
    return RateLimiter(get_settings().login_rate_limit_per_minute, 60)


def _check_rate_limit(request: Request, email: str) -> None:
    limiter = login_limiter()
    if not (limiter.allow(f"ip:{client_ip(request)}") and limiter.allow(f"email:{email}")):
        raise ApiError(429, "Too many login attempts. Please wait a minute and try again.")


def _issue(response: Response, issued: auth_service.IssuedSession) -> SessionResponse:
    access, _ = create_access_token(issued.user.id, issued.user.company_id)
    set_auth_cookies(
        response,
        access_token=access,
        refresh_token=issued.refresh_token,
        csrf_token=issued.csrf_token,
        remember=issued.session.remember_me,
        session_expires=issued.session.expires_on,
    )
    return SessionResponse(user=auth_service.user_to_out(issued.user), expires_at=issued.session.expires_on)


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    """Cookie login used by the web app. Response: {user, expiresAt} (same as the mock)."""
    _check_rate_limit(request, payload.email)
    user = auth_service.authenticate(db, payload.email, payload.password)
    issued = auth_service.create_session(
        db, user, remember=payload.remember, user_agent=request.headers.get("user-agent"), ip=client_ip(request)
    )
    return _issue(response, issued)


@router.post("/token", response_model=TokenResponse)
def token(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 password flow for API clients and the Swagger "Authorize" button (bearer token, no cookies)."""
    email = form.username.strip().lower()
    _check_rate_limit(request, email)
    user = auth_service.authenticate(db, email, form.password)
    db.commit()
    access, _ = create_access_token(user.id, user.company_id)
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=SessionResponse)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    issued = auth_service.rotate_session(
        db, request.cookies.get(REFRESH_COOKIE), user_agent=request.headers.get("user-agent"), ip=client_ip(request)
    )
    if issued is None:
        clear_auth_cookies(response)
        raise ApiError(401, "Session expired. Please sign in again.")
    return _issue(response, issued)


@router.get("/session", response_model=SessionResponse)
def session(request: Request, response: Response, db: Session = Depends(get_db)):
    """Who am I? Returns {user: null} when signed out (not an error). Silently refreshes expired access tokens."""
    payload = decode_access_token(request.cookies.get(ACCESS_COOKIE) or "")
    if payload:
        user = auth_service.get_active_user(db, int(payload["sub"]))
        if user is not None:
            expires = auth_service.active_session_expiry(db, request.cookies.get(REFRESH_COOKIE))
            return SessionResponse(user=auth_service.user_to_out(user), expires_at=expires)
    issued = auth_service.rotate_session(
        db, request.cookies.get(REFRESH_COOKIE), user_agent=request.headers.get("user-agent"), ip=client_ip(request)
    )
    if issued is None:
        return SessionResponse(user=None)
    return _issue(response, issued)


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    auth_service.revoke_session(db, request.cookies.get(REFRESH_COOKIE))
    clear_auth_cookies(response)
    return MessageResponse(message="Signed out.")


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED, response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    _check_rate_limit(request, payload.email.strip().lower())
    auth_service.request_password_reset(db, payload.email)
    return MessageResponse(message="If an account exists for this email, a reset link has been sent.")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password(db, payload.token, payload.new_password)
    return MessageResponse(message="Your password has been changed. Please sign in.")
