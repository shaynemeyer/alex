#!/usr/bin/env python3
"""
Database verification — counts rows and validates allocation sums.
"""

from dotenv import load_dotenv
from src import Database

load_dotenv(override=True)


def main():
    print("DATABASE VERIFICATION REPORT")
    print("=" * 60)

    db = Database()

    # Row counts
    tables = {
        "users":       lambda: db.client.table("users").select("clerk_user_id", count="exact").execute(),
        "instruments": lambda: db.client.table("instruments").select("symbol", count="exact").execute(),
        "accounts":    lambda: db.client.table("accounts").select("id", count="exact").execute(),
        "positions":   lambda: db.client.table("positions").select("id", count="exact").execute(),
        "jobs":        lambda: db.client.table("jobs").select("id", count="exact").execute(),
        "research_documents": lambda: db.client.table("research_documents").select("id", count="exact").execute(),
    }

    print("\nRecord counts:")
    all_pass = True
    for name, query_fn in tables.items():
        resp = query_fn()
        count = resp.count if resp.count is not None else len(resp.data)
        flag = "PASS" if not (name == "instruments" and count == 0) else "WARN"
        if flag == "WARN":
            all_pass = False
        print(f"  {flag}  {name:<22} {count:>6} rows")

    # Sample instruments
    instruments = db.instruments.find_all()
    print(f"\nSample instruments (first 5 of {len(instruments)}):")
    for inst in instruments[:5]:
        print(f"  {inst['symbol']:<6}  {inst['name'][:40]}")

    # Validate allocations on a sample
    print("\nAllocation validation (sample):")
    sample_symbols = ["SPY", "QQQ", "BND", "VEA", "GLD"]
    for symbol in sample_symbols:
        inst = db.instruments.find_by_symbol(symbol)
        if not inst:
            continue
        regions = sum((inst.get("allocation_regions") or {}).values())
        sectors = sum((inst.get("allocation_sectors") or {}).values())
        assets  = sum((inst.get("allocation_asset_class") or {}).values())
        ok = abs(regions - 100) <= 3 and abs(sectors - 100) <= 3 and abs(assets - 100) <= 3
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  {status}  {symbol:<6}  regions={regions:.0f}%  sectors={sectors:.0f}%  assets={assets:.0f}%")

    print("\n" + "=" * 60)
    if all_pass:
        print("PASS  All checks passed — database is ready.")
    else:
        print("WARN  Some checks need attention (see above).")


if __name__ == "__main__":
    main()
