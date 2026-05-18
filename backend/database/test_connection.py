#!/usr/bin/env python3
"""
Test Supabase connection and basic database access.
"""

import sys
from dotenv import load_dotenv
from src import Database

load_dotenv(override=True)


def main():
    print("Supabase Connection Test")
    print("=" * 50)

    try:
        db = Database()
        print("  Connected to Supabase")
    except Exception as e:
        print(f"  Failed to connect: {e}")
        print("\nCheck that SUPABASE_URL and SUPABASE_SERVICE_KEY are set in .env")
        sys.exit(1)

    # Check instrument count
    try:
        instruments = db.instruments.find_all()
        count = len(instruments)
        print(f"  Instruments in database: {count}")
        if count > 0:
            print(f"  Sample: {instruments[0]['symbol']} — {instruments[0]['name']}")
    except Exception as e:
        print(f"  Could not query instruments: {e}")
        print("  Run migrations first: uv run run_migrations.py")
        sys.exit(1)

    print("\nConnection test passed.")
    print("\nNext steps:")
    if count == 0:
        print("  Run migrations: uv run run_migrations.py")
        print("  Seed data:      uv run seed_data.py")
    else:
        print("  Verify database: uv run verify_database.py")


if __name__ == "__main__":
    main()
