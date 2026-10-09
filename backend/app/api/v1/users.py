from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth, require_role
from app.core.database import get_db
from app.core.errors import ApiError
from app.core.roles import COMPANY_ADMIN
from app.core.security import verify_password
from app.schemas.admin import ManagedUserOut, ManagedUserUpdate, PasswordSet, UserCreate
from app.schemas.common import MessageResponse
from app.schemas.user import PasswordChange, UserOut, UserSettingsOut, UserSettingsUpdate, UserUpdate
from app.services import auth_service, company_user_service, user_service
from app.services.auth_service import user_to_out

router = APIRouter(prefix="/users", tags=["users"])
company_admin = require_role(COMPANY_ADMIN)


@router.get("/me", response_model=UserOut)
def me(auth: AuthContext = Depends(get_auth)):
    return user_to_out(auth.user)


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return user_to_out(user_service.update_profile(db, auth.user, payload))


@router.post("/me/password", response_model=MessageResponse)
def change_my_password(payload: PasswordChange, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    """Change your own password (e.g. the temporary one an administrator set)."""
    if not verify_password(payload.current_password, auth.user.password_hash):
        raise ApiError(400, "Your current password is not correct.")
    auth_service.set_password(db, auth.user, payload.new_password)
    return MessageResponse(message="Password changed.")


@router.get("/me/settings", response_model=UserSettingsOut)
def get_settings(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return user_service.get_settings_for(db, auth.user)


@router.put("/me/settings", response_model=UserSettingsOut)
def put_settings(payload: UserSettingsUpdate, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return user_service.update_settings(db, auth.user, payload)


# --- Company Administrators: the users of their own company ----------------------------------


@router.get("", response_model=list[ManagedUserOut])
def list_users(auth: AuthContext = Depends(company_admin), db: Session = Depends(get_db)):
    return company_user_service.list_users(db, auth.company)


@router.get("/roles", response_model=list[str])
def roles(_: AuthContext = Depends(company_admin), db: Session = Depends(get_db)):
    return company_user_service.assignable_roles(db)


@router.post("", response_model=ManagedUserOut, status_code=201)
def create_user(payload: UserCreate, auth: AuthContext = Depends(company_admin), db: Session = Depends(get_db)):
    return company_user_service.create_user(db, auth.company, payload)


@router.patch("/{user_code}", response_model=ManagedUserOut)
def update_user(
    user_code: str, payload: ManagedUserUpdate, auth: AuthContext = Depends(company_admin), db: Session = Depends(get_db)
):
    """Edit a user's details, role and / or status (isActive false = deactivate; their sessions end)."""
    return company_user_service.update_user(db, auth.company, auth.user, user_code, payload)


@router.post("/{user_code}/unlock", response_model=ManagedUserOut)
def unlock_user(user_code: str, auth: AuthContext = Depends(company_admin), db: Session = Depends(get_db)):
    return company_user_service.unlock_user(db, auth.company, user_code)


@router.post("/{user_code}/password", response_model=ManagedUserOut)
def set_user_password(
    user_code: str, payload: PasswordSet, auth: AuthContext = Depends(company_admin), db: Session = Depends(get_db)
):
    """Set a temporary password for a user (they are signed out everywhere)."""
    return company_user_service.set_user_password(db, auth.company, user_code, payload.password)
