from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, get_auth
from app.core.database import get_db
from app.schemas.user import UserOut, UserSettingsOut, UserSettingsUpdate, UserUpdate
from app.services import user_service
from app.services.auth_service import user_to_out

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(auth: AuthContext = Depends(get_auth)):
    return user_to_out(auth.user)


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return user_to_out(user_service.update_profile(db, auth.user, payload))


@router.get("/me/settings", response_model=UserSettingsOut)
def get_settings(auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return user_service.get_settings_for(db, auth.user)


@router.put("/me/settings", response_model=UserSettingsOut)
def put_settings(payload: UserSettingsUpdate, auth: AuthContext = Depends(get_auth), db: Session = Depends(get_db)):
    return user_service.update_settings(db, auth.user, payload)
