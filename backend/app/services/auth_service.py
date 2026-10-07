"""Login, sessions (refresh-token rotation), lockout and password reset."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import get_email_sender
from app.core.errors import ApiError
from app.core.security import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    hash_token,
    new_token,
    now_utc,
    verify_password,
)
from app.models import PasswordResetToken, User, UserSession
from app.schemas.user import UserOut

logger = logging.getLogger("app.auth")
INVALID_CREDENTIALS = "Invalid email or password."


@dataclass
class IssuedSession:
    user: User
    session: UserSession
    refresh_token: str
    csrf_token: str


def user_to_out(user: User) -> UserOut:
    return UserOut(
        id=user.user_code,
        name=user.full_name,
        email=user.email,
        role=user.role.name,
        job_title=user.job_title,
        phone=user.phone,
        company_id=user.company.company_code,
        country=user.country.name if user.country else None,
        region=user.region.name if user.region else None,
    )


def find_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def get_active_user(db: Session, user_id: int) -> User | None:
    user = db.get(User, user_id)
    if user is None or not user.is_active or not user.company.is_active:
        return None
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """Verify credentials with lockout after repeated failures. Raises ApiError on failure."""
    settings = get_settings()
    user = find_user_by_email(db, email)
    if user is None or not user.is_active or not user.company.is_active:
        verify_password(password, None)  # same cost as a real check
        raise ApiError(401, INVALID_CREDENTIALS)

    now = now_utc()
    if user.locked_until and user.locked_until > now:
        minutes = max(1, int((user.locked_until - now).total_seconds() // 60) + 1)
        raise ApiError(423, f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes > 1 else ''}.")

    if not verify_password(password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= settings.login_max_failed_attempts:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_count = 0
            logger.warning("User %s locked after repeated failed logins", user.user_code)
        db.commit()
        raise ApiError(401, INVALID_CREDENTIALS)

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_on = now
    return user


def create_session(
    db: Session, user: User, *, remember: bool, user_agent: str | None, ip: str | None, expires_on: datetime | None = None
) -> IssuedSession:
    settings = get_settings()
    refresh_token = new_token()
    if expires_on is None:
        lifetime = (
            timedelta(days=settings.refresh_token_days_remember) if remember else timedelta(hours=settings.refresh_token_hours)
        )
        expires_on = now_utc() + lifetime
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hash_token(refresh_token),
        remember_me=remember,
        expires_on=expires_on,
        user_agent=(user_agent or "")[:500] or None,
        ip_address=ip,
        created_by=user.id,
        modified_by=user.id,
    )
    db.add(session)
    db.commit()
    return IssuedSession(user=user, session=session, refresh_token=refresh_token, csrf_token=new_token())


def rotate_session(db: Session, refresh_token: str | None, *, user_agent: str | None, ip: str | None) -> IssuedSession | None:
    """Exchange a refresh token for a new one. Reuse of a revoked token revokes all the user's sessions."""
    if not refresh_token:
        return None
    session = db.scalar(select(UserSession).where(UserSession.refresh_token_hash == hash_token(refresh_token)))
    if session is None:
        return None
    now = now_utc()
    if session.revoked_on is not None or not session.is_active:
        logger.warning("Refresh token reuse detected for user id %s; revoking all sessions", session.user_id)
        revoke_all_sessions(db, session.user_id)
        return None
    if session.expires_on <= now:
        return None
    user = get_active_user(db, session.user_id)
    if user is None:
        return None
    session.revoked_on = now
    session.is_active = False
    # Keep the original absolute expiry: rotation must not extend a session forever.
    return create_session(db, user, remember=session.remember_me, user_agent=user_agent, ip=ip, expires_on=session.expires_on)


def revoke_session(db: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    session = db.scalar(select(UserSession).where(UserSession.refresh_token_hash == hash_token(refresh_token)))
    if session is not None and session.revoked_on is None:
        session.revoked_on = now_utc()
        session.is_active = False
        db.commit()


def revoke_all_sessions(db: Session, user_id: int) -> None:
    db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_on.is_(None))
        .values(revoked_on=now_utc(), is_active=False)
    )
    db.commit()


def active_session_expiry(db: Session, refresh_token: str | None) -> datetime | None:
    if not refresh_token:
        return None
    session = db.scalar(select(UserSession).where(UserSession.refresh_token_hash == hash_token(refresh_token)))
    if session and session.revoked_on is None and session.expires_on > now_utc():
        return session.expires_on
    return None


def request_password_reset(db: Session, email: str) -> None:
    """Always succeeds from the caller's point of view (no account enumeration)."""
    settings = get_settings()
    user = find_user_by_email(db, email)
    if user is None or not user.is_active:
        return
    token = new_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_on=now_utc() + timedelta(minutes=settings.password_reset_minutes),
        )
    )
    db.commit()
    link = f"{settings.frontend_origin.rstrip('/')}/reset-password?token={token}"
    get_email_sender().send(
        user.email,
        "Reset your Dealer Communication Portal password",
        f"Hello {user.full_name},\n\nUse this link within {settings.password_reset_minutes} minutes to set a new "
        f"password:\n{link}\n\nIf you did not request this, you can ignore this email.",
    )


def validate_new_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ApiError(422, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if password.strip() != password or len(set(password)) < 4:
        raise ApiError(422, "Choose a stronger password.")


def reset_password(db: Session, token: str, new_password: str) -> None:
    validate_new_password(new_password)
    record = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token)))
    if record is None or record.used_on is not None or not record.is_active or record.expires_on <= now_utc():
        raise ApiError(400, "This reset link is invalid or has expired.")
    user = get_active_user(db, record.user_id)
    if user is None:
        raise ApiError(400, "This reset link is invalid or has expired.")
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None
    record.used_on = now_utc()
    record.is_active = False
    db.commit()
    revoke_all_sessions(db, user.id)


def set_password(db: Session, user: User, new_password: str) -> None:
    validate_new_password(new_password)
    user.password_hash = hash_password(new_password)
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
