#!/usr/bin/env python
"""
One-shot script to create a demo user and seed their data.

Usage (inside the API container or with the venv active):
    python scripts/create_demo_user.py
    python scripts/create_demo_user.py --email me@example.com --password secret123 --name "Jane Doe"

By default creates:
    email:    demo@finance.local
    password: demo1234
    name:     Demo User
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running from repo root or from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.db import get_database, ensure_indexes, assert_replica_set
from app.errors import ConflictError
from app.services import auth_service


async def create_demo_user(email: str, password: str, display_name: str) -> None:
    settings = get_settings()
    db = get_database()

    await assert_replica_set(db)
    await ensure_indexes(db)

    try:
        user = await auth_service.register(
            db,
            email=email,
            password=password,
            display_name=display_name,
            invite_code=settings.registration_invite_code or None,
            settings=settings,
        )
        print(f"\n✅  Demo user created successfully!")
        print(f"    ID:       {user.id}")
        print(f"    Email:    {user.email}")
        print(f"    Name:     {user.display_name}")
        print(f"\n    Log in at http://localhost:3000\n")
    except ConflictError:
        print(f"\n⚠️  A user with email '{email}' already exists. Use that account to log in.\n")
        sys.exit(0)
    except Exception as exc:
        print(f"\n❌  Failed to create user: {exc}\n")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a demo user for Finance Tracker")
    parser.add_argument("--email", default="demo@example.com", help="Email address")
    parser.add_argument("--password", default="demo1234", help="Password (min 8 chars)")
    parser.add_argument("--name", default="Demo User", dest="display_name", help="Display name")
    args = parser.parse_args()

    asyncio.run(create_demo_user(args.email, args.password, args.display_name))


if __name__ == "__main__":
    main()
