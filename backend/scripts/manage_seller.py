#!/usr/bin/env python3
"""CLI tool for managing sellers."""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import get_settings
from app.core.crypto import encrypt
from app.core.security import hash_password
from app.database import Base
from app.models.seller import Seller


async def get_db_session():
    """Create database session."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return session_factory()


async def create_seller(args):
    """Create a new seller."""
    password = args.password or getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        print("Error: Passwords do not match")
        return 1

    async with await get_db_session() as db:
        # Check if username exists
        result = await db.execute(select(Seller).where(Seller.username == args.username))
        if result.scalar_one_or_none():
            print(f"Error: Username '{args.username}' already exists")
            return 1

        seller = Seller(
            name=args.name,
            username=args.username,
            password_hash=hash_password(password),
            tiktok_unique_id=args.tiktok_id,
            tiktok_session_id_encrypted=encrypt(args.session_id),
            tiktok_target_idc_encrypted=encrypt(args.target_idc),
        )
        db.add(seller)
        await db.commit()
        await db.refresh(seller)

        print(f"Created seller: {seller.name} (id={seller.id})")
        return 0


async def set_password(args):
    """Set/reset password for existing seller."""
    async with await get_db_session() as db:
        result = await db.execute(select(Seller).where(Seller.username == args.username))
        seller = result.scalar_one_or_none()

        if not seller:
            print(f"Error: Seller '{args.username}' not found")
            return 1

        password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("Error: Passwords do not match")
            return 1

        seller.password_hash = hash_password(password)
        await db.commit()

        print(f"Password updated for seller: {seller.username}")
        return 0


async def list_sellers(args):
    """List all sellers."""
    async with await get_db_session() as db:
        result = await db.execute(select(Seller).order_by(Seller.created_at.desc()))
        sellers = result.scalars().all()

        if not sellers:
            print("No sellers found")
            return 0

        print(f"{'ID':<36} {'Username':<20} {'Name':<30} {'Active':<8} {'TikTok ID':<20}")
        print("-" * 120)
        for s in sellers:
            active = "Yes" if s.is_active else "No"
            username = s.username or "(not set)"
            print(f"{s.id:<36} {username:<20} {s.name:<30} {active:<8} {s.tiktok_unique_id:<20}")

        return 0


async def disable_seller(args):
    """Disable a seller account."""
    async with await get_db_session() as db:
        result = await db.execute(select(Seller).where(Seller.username == args.username))
        seller = result.scalar_one_or_none()

        if not seller:
            print(f"Error: Seller '{args.username}' not found")
            return 1

        seller.is_active = False
        await db.commit()

        print(f"Disabled seller: {seller.username}")
        return 0


async def enable_seller(args):
    """Enable a seller account."""
    async with await get_db_session() as db:
        result = await db.execute(select(Seller).where(Seller.username == args.username))
        seller = result.scalar_one_or_none()

        if not seller:
            print(f"Error: Seller '{args.username}' not found")
            return 1

        seller.is_active = True
        await db.commit()

        print(f"Enabled seller: {seller.username}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Seller management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create
    create_parser = subparsers.add_parser("create", help="Create a new seller")
    create_parser.add_argument("--username", required=True, help="Login username")
    create_parser.add_argument("--password", help="Password (will prompt if not provided)")
    create_parser.add_argument("--name", required=True, help="Display name")
    create_parser.add_argument(
        "--tiktok-id", required=True, help="TikTok unique ID (e.g. @username)"
    )
    create_parser.add_argument("--session-id", required=True, help="TikTok session ID")
    create_parser.add_argument("--target-idc", required=True, help="TikTok target IDC")

    # set-password
    setpw_parser = subparsers.add_parser("set-password", help="Set/reset seller password")
    setpw_parser.add_argument("--username", required=True, help="Seller username")

    # list
    subparsers.add_parser("list", help="List all sellers")

    # disable
    disable_parser = subparsers.add_parser("disable", help="Disable a seller account")
    disable_parser.add_argument("--username", required=True, help="Seller username")

    # enable
    enable_parser = subparsers.add_parser("enable", help="Enable a seller account")
    enable_parser.add_argument("--username", required=True, help="Seller username")

    args = parser.parse_args()

    commands = {
        "create": create_seller,
        "set-password": set_password,
        "list": list_sellers,
        "disable": disable_seller,
        "enable": enable_seller,
    }

    exit_code = asyncio.run(commands[args.command](args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
