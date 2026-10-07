from __future__ import annotations

from sqlalchemy import select

from app.core.database import get_session_factory
from app.models import Company, Role, User
from app.services import auth_service


def make_user(email: str, password: str, *, role: str = "Viewer", company_code: str = "CMP-10045") -> None:
    """Create (or reset) a throwaway user so tests that lock / reset accounts don't affect others."""
    with get_session_factory()() as db:
        user = auth_service.find_user_by_email(db, email)
        if user is None:
            company = db.scalar(select(Company).where(Company.company_code == company_code))
            user = User(
                company_id=company.id,
                role_id=db.scalar(select(Role.id).where(Role.name == role)),
                user_code=f"USR-T{abs(hash(email)) % 100000}",
                full_name=email.split("@")[0].title(),
                email=email,
            )
            db.add(user)
            db.commit()
        user.locked_until = None
        user.failed_login_count = 0
        auth_service.set_password(db, user, password)
