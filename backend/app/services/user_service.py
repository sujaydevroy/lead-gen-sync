from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserSettings
from app.schemas.user import UserSettingsOut, UserSettingsUpdate, UserUpdate


def update_profile(db: Session, user: User, payload: UserUpdate) -> User:
    user.full_name = payload.name
    user.job_title = payload.job_title
    user.phone = payload.phone
    db.commit()
    db.refresh(user)
    return user


def _settings_row(db: Session, user: User) -> UserSettings | None:
    return db.scalar(select(UserSettings).where(UserSettings.user_id == user.id))


def get_settings_for(db: Session, user: User) -> UserSettingsOut:
    row = _settings_row(db, user)
    if row is None or not row.is_active:
        return UserSettingsOut()
    return UserSettingsOut(
        default_page_size=row.default_page_size,
        apply_filters_instantly=row.apply_filters_instantly,
        desktop_dealer_view=row.desktop_dealer_view,
    )


def update_settings(db: Session, user: User, payload: UserSettingsUpdate) -> UserSettingsOut:
    row = _settings_row(db, user)
    if row is None:
        row = UserSettings(user_id=user.id)
        db.add(row)
    row.is_active = True
    row.default_page_size = payload.default_page_size
    row.apply_filters_instantly = payload.apply_filters_instantly
    row.desktop_dealer_view = payload.desktop_dealer_view
    db.commit()
    return get_settings_for(db, user)
