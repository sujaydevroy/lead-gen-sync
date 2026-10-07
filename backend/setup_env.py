"""Interactive helper that creates backend/.env for you.

    .venv\\Scripts\\python setup_env.py          (Windows)
    .venv/bin/python setup_env.py              (macOS / Linux)

It asks for your database connection string and password, URL-encodes the password correctly,
tests the connection, generates a JWT secret and writes backend/.env. The password is typed
hidden and only stored in backend/.env (which git ignores).

Optional (for automation): --connection-string "postgresql://user@host:5432/db" --yes, and the
password in the DB_PASSWORD environment variable.
"""

from __future__ import annotations

import argparse
import getpass
import os
import re
import secrets
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"
PLACEHOLDERS = {"[YOUR-PASSWORD]", "YOUR-PASSWORD", "[PASSWORD]", "PASSWORD", ""}


def parse_connection_string(text: str) -> dict:
    """Split postgresql://user[:password]@host[:port]/db[?query] (password may itself contain '@' or ':')."""
    text = text.strip().strip('"').strip("'")
    match = re.match(r"^postgres(?:ql)?(?:\+\w+)?://(?P<rest>.+)$", text)
    if not match:
        raise ValueError("It should start with postgresql://")
    rest = match.group("rest")
    if "@" not in rest:
        raise ValueError("It should look like postgresql://USER:[YOUR-PASSWORD]@HOST:PORT/DATABASE")
    userinfo, _, location = rest.rpartition("@")
    user, _, password = userinfo.partition(":")
    location, _, query = location.partition("?")
    hostport, _, database = location.partition("/")
    host, _, port = hostport.partition(":")
    if not user or not host:
        raise ValueError("The user name or host is missing.")
    return {
        "user": user,
        "password": None if password in PLACEHOLDERS else password,
        "host": host,
        "port": port or "5432",
        "database": database or "postgres",
        "query": query,
    }


def build_url(parts: dict, password: str) -> str:
    local = parts["host"] in ("localhost", "127.0.0.1", "::1")
    query = parts["query"]
    if not local and "sslmode=" not in query:
        query = f"{query}&sslmode=require" if query else "sslmode=require"
    url = (
        f"postgresql://{quote(parts['user'], safe='')}:{quote(password, safe='')}"
        f"@{parts['host']}:{parts['port']}/{parts['database']}"
    )
    return f"{url}?{query}" if query else url


def explain_error(message: str, parts: dict) -> str:
    text = message.lower()
    if "password authentication failed" in text:
        return "The password was rejected. Check it in Supabase: Project Settings -> Database -> Reset database password."
    if "tenant or user not found" in text:
        return (
            "The pooler didn't recognise the user/host. Copy the Session pooler string again from Supabase "
            "(Connect button); the user must look like postgres.<project-ref>."
        )
    if "could not translate host name" in text or "nodename nor servname" in text or "getaddrinfo" in text:
        return "The host name could not be found. Check for typos in the connection string."
    if "timeout" in text or "timed out" in text or "network is unreachable" in text or "no route" in text:
        hint = "The server could not be reached."
        if parts["host"].startswith("db.") and parts["host"].endswith(".supabase.co"):
            hint += (
                " This 'db.<ref>.supabase.co' address only works over IPv6, which this network doesn't have. "
                "Use the 'Session pooler' connection string from Supabase instead (Connect button)."
            )
        return hint
    return "See the error above."


def test_connection(url: str) -> tuple[bool, str]:
    try:
        import psycopg
    except ImportError:
        return False, 'psycopg is not installed. Run: .venv\\Scripts\\python -m pip install -e ".[dev]"'
    try:
        with psycopg.connect(url, connect_timeout=15) as conn:
            version = conn.execute("select current_setting('server_version'), current_user").fetchone()
        return True, f"Connected: PostgreSQL {version[0]} as {version[1]}"
    except Exception as exc:  # show the driver's message to the user
        return False, str(exc).strip()


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or (default or "")


def read_existing_env() -> dict[str, str]:
    values = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip()
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Create backend/.env")
    parser.add_argument("--connection-string", help="postgresql://USER@HOST:PORT/DB (no password needed)")
    parser.add_argument("--yes", action="store_true", help="Overwrite an existing .env without asking")
    args = parser.parse_args()

    print("\n=== Dealer Portal API: database settings ===\n")
    if not args.connection_string:
        print("In Supabase open your project, click 'Connect' (top bar) and copy the 'Session pooler' string.")
        print("It looks like: postgresql://postgres.<ref>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres")
        print("Leave [YOUR-PASSWORD] as it is; you'll type the password in the next step.\n")

    parts = None
    while parts is None:
        raw = args.connection_string or ask("Paste the connection string")
        try:
            parts = parse_connection_string(raw)
        except ValueError as exc:
            print(f"  ERROR: {exc}")
            if args.connection_string:
                return 1

    if parts["host"].startswith("db.") and parts["host"].endswith(".supabase.co"):
        print("\n  ! Note: db.<ref>.supabase.co only works over IPv6. If the test below times out, re-run this")
        print("    script with the 'Session pooler' string instead.")

    password = parts["password"]
    if password:
        print("\nUsing the password included in the connection string.")
    attempts = 0
    while True:
        attempts += 1
        if not password:
            password = os.environ.get("DB_PASSWORD") or getpass.getpass(
                "\nDatabase password (nothing appears while you type; press Enter when done): "
            )
        url = build_url(parts, password)
        print("Testing the connection...")
        ok, message = test_connection(url)
        if ok:
            print(f"  OK {message}")
            break
        print(f"  ERROR: {message}\n  -> {explain_error(message, parts)}")
        if os.environ.get("DB_PASSWORD") or attempts >= 3:
            return 1
        password = None  # ask again

    existing = read_existing_env()
    replace_prompt = "\nbackend/.env already exists. Replace it? (a backup is kept as .env.bak) y/n"
    if ENV_FILE.exists() and not args.yes and ask(replace_prompt, "y").lower() != "y":
        print("Nothing changed.")
        return 0
    if ENV_FILE.exists():
        shutil.copyfile(ENV_FILE, ENV_FILE.with_name(".env.bak"))

    jwt_secret = existing.get("JWT_SECRET") if len(existing.get("JWT_SECRET", "")) >= 32 else secrets.token_urlsafe(48)
    transaction_pooler = parts["port"] == "6543"
    ENV_FILE.write_text(
        "# Created by setup_env.py - contains secrets, never commit this file.\n"
        "ENVIRONMENT=development\n"
        f"DATABASE_URL={url}\n"
        f"DB_DISABLE_PREPARED_STATEMENTS={'true' if transaction_pooler else 'false'}\n"
        f"JWT_SECRET={jwt_secret}\n"
        "# false only because local development uses http://localhost; set true in production (HTTPS).\n"
        "COOKIE_SECURE=false\n"
        "FRONTEND_ORIGIN=http://localhost:3000\n",
        encoding="utf-8",
    )
    print(f"\n  OK Saved {ENV_FILE}")
    print("\nNext step - create the tables and load the data:")
    print("    .venv\\Scripts\\python -m app.cli setup\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
