"""User management inside one company, done by its Company Administrator.

Users are never hard-deleted: "remove" = deactivate (is_active = FALSE), which also ends their sessions.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, not_found
from app.core.roles import COMPANY_ROLES
from app.core.security import hash_password, now_utc
from app.models import Company, Role, User
from app.schemas.admin import ManagedUserOut, ManagedUserUpdate, UserCreate
from app.services import auth_service
from app.services.codes import next_code


def user_to_managed_out(user: User) -> ManagedUserOut:
    return ManagedUserOut(
        id=user.user_code,
        name=user.full_name,
        email=user.email,
        role=user.role.name,
        job_title=user.job_title,
        phone=user.phone,
        country=user.country.name if user.country else None,
        region=user.region.name if user.region else None,
        is_active=user.is_active,
        is_locked=bool(user.locked_until and user.locked_until > now_utc()),
        last_login_on=user.last_login_on,
        created_on=user.created_on,
    )


def assignable_roles(db: Session) -> list[str]:
    existing = set(db.scalars(select(Role.name).where(Role.is_active)))
    return [name for name in COMPANY_ROLES if name in existing]


def role_id_for(db: Session, name: str) -> int:
    if name not in COMPANY_ROLES:
        raise ApiError(422, f"Unknown role '{name}'. Choose one of: {', '.join(COMPANY_ROLES)}.")
    role_id = db.scalar(select(Role.id).where(Role.name == name, Role.is_active))
    if role_id is None:
        raise ApiError(422, f"Unknown role '{name}'.")
    return role_id


def _get(db: Session, company: Company, user_code: str) -> User:
    user = db.scalar(select(User).where(User.company_id == company.id, User.user_code == user_code))
    if user is None:
        raise not_found("User")
    return user


def list_users(db: Session, company: Company) -> list[ManagedUserOut]:
    users = db.scalars(select(User).where(User.company_id == company.id).order_by(func.lower(User.full_name)))
    return [user_to_managed_out(u) for u in users]


def create_user(db: Session, company: Company, payload: UserCreate) -> ManagedUserOut:
    if auth_service.find_user_by_email(db, str(payload.email)) is not None:
        raise ApiError(409, f"A user with the email {payload.email} already exists.")
    auth_service.validate_new_password(payload.password)
    user = User(
        company_id=company.id,
        role_id=role_id_for(db, payload.role),
        user_code=next_code(db, User.user_code, "USR", start=2001),
        full_name=payload.name,
        email=str(payload.email),
        job_title=payload.job_title,
        phone=payload.phone,
        country_id=company.country_id,
        region_id=company.region_id,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_managed_out(user)


def update_user(db: Session, company: Company, actor: User | None, user_code: str, payload: ManagedUserUpdate) -> ManagedUserOut:
    """Edit a user of `company`: name, email, job title, phone, role, active (only the fields sent change).

    `actor` is the signed-in administrator; nobody can change their own role or deactivate themselves.
    """
    user = _get(db, company, user_code)
    sent = payload.model_fields_set
    is_self = actor is not None and user.id == actor.id
    if is_self and ((payload.role is not None and payload.role != user.role.name) or payload.is_active is False):
        raise ApiError(409, "You cannot change your own role or deactivate your own account.")
    if "email" in sent and payload.email is not None and str(payload.email).lower() != user.email.lower():
        other = auth_service.find_user_by_email(db, str(payload.email))
        if other is not None and other.id != user.id:
            raise ApiError(409, f"A user with the email {payload.email} already exists.")
        user.email = str(payload.email)
    if "name" in sent and payload.name is not None:
        user.full_name = payload.name
    if "job_title" in sent:
        user.job_title = payload.job_title
    if "phone" in sent:
        user.phone = payload.phone
    if payload.role is not None and payload.role != user.role.name:
        user.role_id = role_id_for(db, payload.role)
    deactivated = payload.is_active is False and user.is_active
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    if deactivated:
        auth_service.revoke_all_sessions(db, user.id)
    db.refresh(user)
    return user_to_managed_out(user)


def unlock_user(db: Session, company: Company, user_code: str) -> ManagedUserOut:
    user = _get(db, company, user_code)
    user.locked_until = None
    user.failed_login_count = 0
    db.commit()
    db.refresh(user)
    return user_to_managed_out(user)


def set_user_password(db: Session, company: Company, user_code: str, password: str) -> ManagedUserOut:
    """Set a temporary password (the user can change it later); signs the user out everywhere."""
    user = _get(db, company, user_code)
    auth_service.set_password(db, user, password)
    auth_service.revoke_all_sessions(db, user.id)
    db.refresh(user)
    return user_to_managed_out(user)
