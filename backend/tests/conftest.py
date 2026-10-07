"""Test setup.

Unit tests need nothing. Integration tests (tests/integration) need a DISPOSABLE PostgreSQL database
whose name ends in "_test"; its "dcp" schema is dropped and recreated from database/*.sql:

    set TEST_DATABASE_URL=postgresql://postgres@localhost:5432/dealer_portal_test
    pytest
"""

from __future__ import annotations

import os
import secrets
import tempfile
from urllib.parse import urlparse

import pytest

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

# Settings are read when app modules are imported, so configure the environment first.
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or "postgresql://unused@localhost:1/unused_test"
os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
os.environ["COOKIE_SECURE"] = "false"
os.environ["LOGIN_RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["STORAGE_LOCAL_DIR"] = tempfile.mkdtemp(prefix="dcp-test-storage-")

DEMO_PASSWORD = "Test-Password-2026"
VIEWER_PASSWORD = "Viewer-Password-2026"
OTHER_PASSWORD = "Other-Password-2026"


def pytest_collection_modifyitems(config, items):
    if TEST_DATABASE_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL is not set (integration tests need a disposable database)")
    for item in items:
        if "integration" in item.nodeid.replace("\\", "/").split("/"):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def database():
    """Recreate schema + seed once per test session, plus extra users/companies used by the tests."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    db_name = urlparse(TEST_DATABASE_URL).path.lstrip("/")
    if not db_name.endswith("_test"):
        pytest.exit(f"Refusing to reset database '{db_name}': its name must end with '_test'.")

    from sqlalchemy import select, text

    from app.cli import cmd_seed, cmd_seed_demo_communications
    from app.core.config import PROJECT_ROOT
    from app.core.database import get_engine, get_session_factory, run_sql_script
    from app.models import Company, Country, Region, Role, Sector, User
    from app.services import auth_service

    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS dcp CASCADE"))
        run_sql_script(connection, (PROJECT_ROOT / "database" / "02_schema.sql").read_text(encoding="utf-8"))
    cmd_seed()
    cmd_seed_demo_communications()

    with get_session_factory()() as db:
        john = auth_service.find_user_by_email(db, "john.smith@abc.com")
        auth_service.set_password(db, john, DEMO_PASSWORD)
        viewer_role = db.scalar(select(Role).where(Role.name == "Viewer"))
        india = db.scalar(select(Country).where(Country.name == "India"))
        north = db.scalar(select(Region).where(Region.name == "North"))
        viewer = User(
            company_id=john.company_id,
            role_id=viewer_role.id,
            user_code="USR-2002",
            full_name="Vera Viewer",
            email="vera.viewer@abc.com",
            country_id=india.id,
            region_id=north.id,
        )
        other_company = Company(
            company_code="CMP-20001",
            name="Other Industries",
            sector_id=db.scalar(select(Sector.id).where(Sector.name == "Electrical & Electrical Equipment")),
        )
        db.add_all([viewer, other_company])
        db.flush()
        other_user = User(
            company_id=other_company.id,
            role_id=viewer_role.id,
            user_code="USR-3001",
            full_name="Omar Other",
            email="omar@other.example",
        )
        db.add(other_user)
        db.commit()
        auth_service.set_password(db, viewer, VIEWER_PASSWORD)
        auth_service.set_password(db, other_user, OTHER_PASSWORD)
    return engine


@pytest.fixture()
def client(database):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def login(client, email="john.smith@abc.com", password=DEMO_PASSWORD, remember=False):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password, "remember": remember})
    assert response.status_code == 200, response.text
    # Echo the CSRF cookie like the frontend will (double-submit).
    client.headers["X-CSRF-Token"] = client.cookies.get("dcp_csrf")
    return response.json()


@pytest.fixture()
def auth_client(client):
    login(client)
    return client
