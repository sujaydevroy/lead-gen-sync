"""Management commands.

python -m app.cli setup                                # first-time setup: tables + data + demo user password
python -m app.cli set-password john.smith@abc.com     # prompts for the password (never pass it as an argument)
python -m app.cli seed                                 # runs database/03_seed.sql (idempotent)
python -m app.cli seed-demo-communications             # demo history like the frontend mock (only if none exist)
python -m app.cli remap-products                       # rebuild product -> sub-sector links
python -m app.cli backfill-sales-uploads               # fill column/row detail for older sales uploads
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import timedelta

from pydantic import ValidationError
from sqlalchemy import func, inspect, select, text

from app.core.config import BACKEND_DIR, PROJECT_ROOT, SCHEMA, get_settings
from app.core.database import get_engine, get_session_factory, run_sql_script
from app.core.errors import ApiError
from app.core.security import now_utc
from app.models import (
    Communication,
    CommunicationStatus,
    CommunicationType,
    Company,
    Dealer,
    Product,
    ProductSubSector,
    SubSector,
    User,
)
from app.services import auth_service
from app.services.analytics.sector_matching import product_matches_sub_sector
from app.services.communication_service import dealer_party

DEMO_COMMUNICATIONS = [
    # dealer, type, direction, subject, hours ago, status, body  (mirrors frontend/src/data/communications.js)
    (
        "DLR-1006",
        "Email",
        "outbound",
        "Q4 Product Availability",
        2,
        "Delivered",
        "Sharing the Q4 availability list for MCB, MCCB and RMU lines. Please confirm your forecast quantities by Friday.",
    ),
    (
        "DLR-1012",
        "Message",
        "inbound",
        "New Product Inquiry",
        26,
        "Received",
        "We would like pricing for the new modular switch range for a residential project in Mumbai.",
    ),
    (
        "DLR-1009",
        "Meeting",
        "outbound",
        "Partner Meeting",
        50,
        "Completed",
        "Quarterly partner review covering sell-out, stock ageing and the 2027 incentive scheme.",
    ),
    (
        "DLR-1013",
        "Email",
        "outbound",
        "Price List Revision - November",
        54,
        "Read",
        "Attached is the revised price list effective 1 November. Copper-linked SKUs move by 3.2%.",
    ),
    (
        "DLR-1001",
        "Call",
        "outbound",
        "Order follow-up: RMU dispatch",
        75,
        "Completed",
        "Confirmed the RMU dispatch date and transport arrangements to Agra.",
    ),
    (
        "DLR-1014",
        "Message",
        "inbound",
        "New Order Request",
        98,
        "Received",
        "Please process an order for 40 distribution boards and 200 MCBs for the Chicago warehouse.",
    ),
    (
        "DLR-1018",
        "Email",
        "outbound",
        "Warranty claim acknowledgement",
        120,
        "Delivered",
        "We have registered warranty claim WC-3381 and a field engineer will contact you within 48 hours.",
    ),
    (
        "DLR-1024",
        "Email",
        "inbound",
        "Stock transfer request",
        140,
        "Received",
        "Requesting a stock transfer of 25 contactors from the Frankfurt hub.",
    ),
    (
        "DLR-1002",
        "Meeting",
        "outbound",
        "Annual business plan",
        170,
        "Completed",
        "Agreed annual targets for control products and motors for FY27.",
    ),
    (
        "DLR-1029",
        "Message",
        "outbound",
        "Training invitation",
        190,
        "Read",
        "Invitation to the switchgear product training in Lyon on 22 October.",
    ),
    (
        "DLR-1033",
        "Email",
        "outbound",
        "Partner portal onboarding",
        215,
        "Delivered",
        "Welcome to the partner programme. Your onboarding checklist is attached.",
    ),
    (
        "DLR-1006",
        "Message",
        "inbound",
        "Delivery schedule query",
        240,
        "Received",
        "Could you share the delivery schedule for last week's cable order?",
    ),
    (
        "DLR-1037",
        "Call",
        "outbound",
        "Credit limit review",
        260,
        "Completed",
        "Discussed an increase in credit limit subject to the latest audited financials.",
    ),
    (
        "DLR-1041",
        "Email",
        "outbound",
        "Marketing co-op funds",
        300,
        "Read",
        "Co-op marketing funds for Q4 are now available. Submit campaign plans by month end.",
    ),
    (
        "DLR-1045",
        "Message",
        "inbound",
        "Installation support",
        330,
        "Received",
        "Need on-site support for commissioning a 630 kVA transformer.",
    ),
    (
        "DLR-1003",
        "Email",
        "outbound",
        "Product catalogue 2027",
        360,
        "Delivered",
        "The 2027 product catalogue is attached, including new LED and power quality ranges.",
    ),
    (
        "DLR-1049",
        "Meeting",
        "outbound",
        "Regional dealer meet",
        410,
        "Completed",
        "Hosted the regional dealer meet with 12 attendees.",
    ),
    (
        "DLR-1053",
        "Email",
        "inbound",
        "Quotation request: UPS systems",
        450,
        "Received",
        "Requesting a quotation for 15 UPS units for a data centre retrofit.",
    ),
    (
        "DLR-1010",
        "Email",
        "outbound",
        "Partner Meeting",
        500,
        "Read",
        "Confirming our partner meeting next Tuesday at your office.",
    ),
    (
        "DLR-1016",
        "Call",
        "inbound",
        "Pricing clarification",
        540,
        "Completed",
        "Dealer called to clarify volume discount tiers for contactors.",
    ),
]


def cmd_set_password(email: str) -> int:
    password = getpass.getpass("New password: ")
    if password != getpass.getpass("Repeat password: "):
        print("Passwords do not match.", file=sys.stderr)
        return 1
    with get_session_factory()() as db:
        user = auth_service.find_user_by_email(db, email)
        if user is None:
            print(f"No user with email {email}.", file=sys.stderr)
            return 1
        try:
            auth_service.set_password(db, user, password)
        except ApiError as exc:
            print(exc.detail, file=sys.stderr)
            return 1
    print(f"Password set for {email}.")
    return 0


def cmd_seed() -> int:
    sql = (PROJECT_ROOT / "database" / "03_seed.sql").read_text(encoding="utf-8")
    with get_engine().begin() as connection:
        run_sql_script(connection, sql)
    print("Seed data applied (database/03_seed.sql).")
    return 0


def cmd_seed_demo_communications() -> int:
    with get_session_factory()() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == "john.smith@abc.com"))
        if user is None:
            print("Run the seed first (demo user john.smith@abc.com not found).", file=sys.stderr)
            return 1
        company: Company = user.company
        existing = db.scalar(select(func.count(Communication.id)).where(Communication.company_id == company.id))
        if existing:
            print(f"{existing} communications already exist; nothing to do.")
            return 0
        types = {t.name: t.id for t in db.scalars(select(CommunicationType))}
        statuses = {s.name: s.id for s in db.scalars(select(CommunicationStatus))}
        dealers = {d.dealer_code: d for d in db.scalars(select(Dealer).where(Dealer.company_id == company.id))}
        now = now_utc()
        added = 0
        for code, kind, direction, subject, hours, status, body in DEMO_COMMUNICATIONS:
            dealer = dealers.get(code)
            if dealer is None:
                continue
            party = dealer_party(dealer)
            outbound = direction == "outbound"
            db.add(
                Communication(
                    company_id=company.id,
                    dealer_id=dealer.id,
                    communication_type_id=types[kind],
                    communication_status_id=statuses[status],
                    direction=direction,
                    sender_user_id=user.id if outbound else None,
                    sender_name=user.full_name if outbound else party,
                    recipient_name=party if outbound else user.full_name,
                    subject=subject,
                    body=body,
                    occurred_on=now - timedelta(hours=hours),
                )
            )
            added += 1
        db.commit()
    print(f"Added {added} demo communications.")
    return 0


def cmd_remap_products() -> int:
    """Recompute product -> sub-sector links for every product against every sub-sector."""
    with get_session_factory()() as db:
        products = list(db.scalars(select(Product).where(Product.is_active)))
        sub_sectors = list(db.scalars(select(SubSector).where(SubSector.is_active)))
        existing = {(link.product_id, link.sub_sector_id): link for link in db.scalars(select(ProductSubSector))}
        wanted = {(p.id, s.id) for p in products for s in sub_sectors if product_matches_sub_sector(p.name, s.name)}
        added = removed = 0
        for key in wanted:
            link = existing.get(key)
            if link is None:
                db.add(ProductSubSector(product_id=key[0], sub_sector_id=key[1]))
                added += 1
            elif not link.is_active:
                link.is_active = True
                added += 1
        for key, link in existing.items():
            if key not in wanted and link.is_active:
                link.is_active = False
                removed += 1
        db.commit()
    print(f"Product/sub-sector links: {added} added, {removed} deactivated, {len(wanted)} active.")
    return 0


def cmd_backfill_sales_uploads(indent: str = "") -> int:
    """Fill dcp.sales_upload_columns / dcp.sales_upload_rows and the file details for older uploads."""
    from app.services.sales_upload_details import backfill_all

    with get_session_factory()() as db:
        results = backfill_all(db)
    if not results:
        print(f"{indent}OK Every sales upload already has its column and row detail.")
    for upload_id, name, outcome in results:
        print(f"{indent}OK Upload {upload_id} ({name}): {outcome}")
    return 0


def _migrate() -> str:
    """Create the schema with Alembic, or record it as applied if 02_schema.sql was already run by hand."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    inspector = inspect(get_engine())
    schema_exists = SCHEMA in inspector.get_schema_names()
    tables = set(inspector.get_table_names(schema=SCHEMA)) if schema_exists else set()
    if "dealers" in tables and "alembic_version" not in tables:
        # 02_schema.sql was run by hand: record the baseline, then apply later (idempotent) migrations.
        command.stamp(config, "0001_baseline")
        command.upgrade(config, "head")
        return "Tables already existed (02_schema.sql was run manually) - recorded them and applied newer migrations."
    command.upgrade(config, "head")
    return "Tables created / up to date (database/02_schema.sql + database/migrations)."


def cmd_setup(demo_data: bool | None, ask_password: bool) -> int:
    """One-shot database setup: connection check, migrations, seed, demo data, admin password."""
    print("\n=== Dealer Portal API: database setup ===\n")
    print("1/6 Checking the database connection...")
    try:
        with get_engine().connect() as connection:
            version = connection.execute(text("select current_setting('server_version')")).scalar()
    except Exception as exc:
        print(f"  ERROR: Could not connect: {exc}\n  -> Run 'python setup_env.py' again to fix the connection settings.")
        return 1
    print(f"  OK PostgreSQL {version}")

    print("2/6 Creating tables...")
    print(f"  OK {_migrate()}")

    print("3/6 Loading reference data, company, user and dealers (database/03_seed.sql)...")
    cmd_seed()

    print("4/6 Completing stored sales uploads (columns + rows detail)...")
    cmd_backfill_sales_uploads(indent="  ")

    print("5/6 Demo communication history...")
    if demo_data is None:
        demo_data = input("  Add the demo messages/calls/meetings shown in the app? (y/n) [y]: ").strip().lower() in (
            "",
            "y",
            "yes",
        )
    if demo_data:
        cmd_seed_demo_communications()
    else:
        print("  Skipped.")

    print("6/6 Password for the demo user john.smith@abc.com...")
    with get_session_factory()() as db:
        has_password = bool(auth_service.find_user_by_email(db, "john.smith@abc.com").password_hash)
    if has_password:
        print("  OK Already set (change it with: python -m app.cli set-password john.smith@abc.com).")
    elif ask_password:
        print("  Choose a password (at least 8 characters). Nothing appears while you type.")
        while cmd_set_password("john.smith@abc.com") != 0:
            print("  Please try again.")
    else:
        print("  Skipped. Set it later with: python -m app.cli set-password john.smith@abc.com")

    print("\nOK Database setup complete. Start the API with:")
    print("    .venv\\Scripts\\python -m uvicorn app.main:app --reload --port 8000")
    print("  then open http://localhost:8000/docs\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="Create tables, load data and set the demo user's password")
    setup.add_argument("--demo-data", dest="demo_data", action="store_true", default=None, help="Add demo history")
    setup.add_argument("--no-demo-data", dest="demo_data", action="store_false", help="Skip demo history")
    setup.add_argument("--no-password", dest="ask_password", action="store_false", help="Don't ask for a password")
    set_pw = sub.add_parser("set-password", help="Set a user's password (prompted)")
    set_pw.add_argument("email")
    sub.add_parser("seed", help="Apply database/03_seed.sql")
    sub.add_parser("seed-demo-communications", help="Insert demo communication history")
    sub.add_parser("remap-products", help="Rebuild product -> sub-sector links")
    sub.add_parser("backfill-sales-uploads", help="Fill column/row detail for uploads made before migration 0002")
    args = parser.parse_args(argv)
    try:
        get_settings()
    except ValidationError:
        print(
            "backend/.env is missing or incomplete. Create it first with:  .venv\\Scripts\\python setup_env.py", file=sys.stderr
        )
        return 1
    if args.command == "setup":
        return cmd_setup(args.demo_data, args.ask_password)
    if args.command == "set-password":
        return cmd_set_password(args.email)
    if args.command == "seed":
        return cmd_seed()
    if args.command == "seed-demo-communications":
        return cmd_seed_demo_communications()
    if args.command == "backfill-sales-uploads":
        return cmd_backfill_sales_uploads()
    return cmd_remap_products()


if __name__ == "__main__":
    raise SystemExit(main())
