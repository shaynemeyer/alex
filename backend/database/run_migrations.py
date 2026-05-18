#!/usr/bin/env python3
"""
Run SQL migration files against the Supabase database.
Requires DATABASE_URL in .env (Settings > Database > Connection string > Direct).
"""

import os
import sys
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(override=True)

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    print("Missing DATABASE_URL in environment.")
    print("Find it in Supabase dashboard: Settings > Database > Connection string > Direct")
    sys.exit(1)

migration_dir = Path("migrations")
sql_files = sorted(migration_dir.glob("*.sql"))

if not sql_files:
    print("No migration files found in migrations/")
    sys.exit(1)

print("Running database migrations...")
print("=" * 50)

conn = psycopg2.connect(database_url)
conn.autocommit = True
cur = conn.cursor()

for sql_file in sql_files:
    print(f"\nApplying {sql_file.name}...")
    sql = sql_file.read_text()
    try:
        cur.execute(sql)
        print(f"  Done")
    except Exception as e:
        print(f"  Error: {e}")
        conn.close()
        sys.exit(1)

cur.close()
conn.close()

print("\n" + "=" * 50)
print("All migrations completed successfully.")
print("\nNext steps:")
print("1. Load seed data: uv run seed_data.py")
print("2. Test connection: uv run test_connection.py")
