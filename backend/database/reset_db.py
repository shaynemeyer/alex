#!/usr/bin/env python3
"""
Database reset: truncates all tables, re-seeds instruments,
and optionally creates a test user with sample portfolio.

Usage:
    uv run reset_db.py
    uv run reset_db.py --with-test-data
"""

import sys
import argparse
import subprocess
from decimal import Decimal
from dotenv import load_dotenv
from src import Database
from src.schemas import UserCreate, AccountCreate, PositionCreate

load_dotenv(override=True)


def truncate_tables(db: Database) -> None:
    """Delete all rows in FK-safe order."""
    print("Truncating tables...")
    tables = ["positions", "jobs", "accounts", "users", "instruments", "research_documents"]
    for table in tables:
        # delete().neq with a dummy condition deletes all rows
        db.client.table(table).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print(f"  Cleared {table}")
    # users and research_documents have text PKs
    db.client.table("users").delete().neq("clerk_user_id", "").execute()
    db.client.table("research_documents").delete().neq("vector_id", "").execute()
    print("  Cleared users")
    print("  Cleared research_documents")


def create_test_data(db: Database) -> None:
    """Create a test user with sample accounts and positions."""
    print("\nCreating test user and portfolio...")

    existing = db.users.find_by_clerk_id("test_user_001")
    if existing:
        print("  Test user already exists")
    else:
        user = UserCreate(
            clerk_user_id="test_user_001",
            display_name="Test User",
            years_until_retirement=25,
            target_retirement_income=Decimal("100000"),
        )
        v = user.model_dump()
        db.users.create_user(
            clerk_user_id=v["clerk_user_id"],
            display_name=v["display_name"],
            years_until_retirement=v["years_until_retirement"],
            target_retirement_income=v["target_retirement_income"],
        )
        print("  Created test user")

    user_accounts = db.accounts.find_by_user("test_user_001")
    if user_accounts:
        print(f"  User already has {len(user_accounts)} accounts")
        account_ids = [a["id"] for a in user_accounts]
    else:
        accounts_data = [
            AccountCreate(account_name="401(k)", account_purpose="Primary retirement savings",
                          cash_balance=Decimal("5000"), cash_interest=Decimal("0.045")),
            AccountCreate(account_name="Roth IRA", account_purpose="Tax-free retirement savings",
                          cash_balance=Decimal("1000"), cash_interest=Decimal("0.04")),
            AccountCreate(account_name="Taxable Brokerage", account_purpose="General investment account",
                          cash_balance=Decimal("2500"), cash_interest=Decimal("0.035")),
        ]
        account_ids = []
        for acc in accounts_data:
            v = acc.model_dump()
            acc_id = db.accounts.create_account(
                "test_user_001",
                account_name=v["account_name"],
                account_purpose=v["account_purpose"],
                cash_balance=v["cash_balance"],
                cash_interest=v["cash_interest"],
            )
            account_ids.append(acc_id)
            print(f"  Created account: {v['account_name']}")

    if account_ids:
        existing_positions = db.positions.find_by_account(account_ids[0])
        if existing_positions:
            print(f"  Account already has {len(existing_positions)} positions")
        else:
            positions = [
                ("SPY", Decimal("100")),
                ("QQQ", Decimal("50")),
                ("BND", Decimal("200")),
                ("VEA", Decimal("150")),
                ("GLD", Decimal("25")),
            ]
            for symbol, quantity in positions:
                db.positions.add_position(account_ids[0], symbol, quantity)
                print(f"  Added position: {quantity} shares of {symbol}")


def main():
    parser = argparse.ArgumentParser(description="Reset Alex database")
    parser.add_argument("--with-test-data", action="store_true",
                        help="Create test user with sample portfolio")
    parser.add_argument("--skip-drop", action="store_true",
                        help="Skip truncating tables (useful for seeding test data without wiping existing data)")
    args = parser.parse_args()

    print("Database Reset")
    print("=" * 50)

    db = Database()

    if not args.skip_drop:
        truncate_tables(db)

    # Re-seed instruments
    print("\nLoading seed data...")
    result = subprocess.run(["uv", "run", "seed_data.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Seed data failed:")
        print(result.stderr)
        sys.exit(1)
    print("  Instruments seeded")

    if args.with_test_data:
        create_test_data(db)

    # Final counts
    print("\nFinal record counts:")
    pk = {"users": "clerk_user_id", "instruments": "symbol"}
    for table in ["users", "instruments", "accounts", "positions", "jobs"]:
        col = pk.get(table, "id")
        resp = db.client.table(table).select(col, count="exact").execute()
        count = resp.count if resp.count is not None else len(resp.data)
        print(f"  {table:<20} {count:>6} rows")

    print("\n" + "=" * 50)
    print("Database reset complete.")

    if args.with_test_data:
        print("\nTest data:")
        print("  User ID: test_user_001")
        print("  3 accounts (401k, Roth IRA, Taxable)")
        print("  5 positions in 401k account")


if __name__ == "__main__":
    main()
