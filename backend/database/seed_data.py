#!/usr/bin/env python3
"""
Seed 22 ETF instruments into the database.
"""

import sys
from pydantic import ValidationError
from dotenv import load_dotenv
from src import Database
from src.schemas import InstrumentCreate

load_dotenv(override=True)

INSTRUMENTS = [
    # Core US Equity
    {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "instrument_type": "etf",
        "current_price": 450.25,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {
            "technology": 28, "healthcare": 13, "financials": 13,
            "consumer_discretionary": 12, "industrials": 9, "communication": 9,
            "consumer_staples": 6, "energy": 4, "utilities": 3,
            "real_estate": 2, "materials": 1,
        },
        "allocation_asset_class": {"equity": 100},
    },
    {
        "symbol": "QQQ",
        "name": "Invesco QQQ Trust",
        "instrument_type": "etf",
        "current_price": 385.50,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {
            "technology": 50, "communication": 17, "consumer_discretionary": 15,
            "healthcare": 8, "consumer_staples": 5, "industrials": 3, "other": 2,
        },
        "allocation_asset_class": {"equity": 100},
    },
    {
        "symbol": "IWM",
        "name": "iShares Russell 2000 ETF",
        "instrument_type": "etf",
        "current_price": 205.75,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {
            "healthcare": 18, "financials": 17, "industrials": 16, "technology": 14,
            "consumer_discretionary": 12, "real_estate": 7, "energy": 6,
            "materials": 4, "consumer_staples": 3, "utilities": 2, "communication": 1,
        },
        "allocation_asset_class": {"equity": 100},
    },
    # International Equity
    {
        "symbol": "VEA",
        "name": "Vanguard FTSE Developed Markets ETF",
        "instrument_type": "etf",
        "current_price": 48.30,
        "allocation_regions": {"europe": 60, "asia": 35, "oceania": 5},
        "allocation_sectors": {
            "financials": 18, "industrials": 14, "healthcare": 12,
            "consumer_discretionary": 11, "technology": 10, "consumer_staples": 9,
            "materials": 8, "energy": 6, "communication": 5, "utilities": 4, "real_estate": 3,
        },
        "allocation_asset_class": {"equity": 100},
    },
    {
        "symbol": "VWO",
        "name": "Vanguard FTSE Emerging Markets ETF",
        "instrument_type": "etf",
        "current_price": 42.15,
        "allocation_regions": {"asia": 75, "latin_america": 10, "africa": 8, "europe": 7},
        "allocation_sectors": {
            "technology": 22, "financials": 20, "consumer_discretionary": 15,
            "communication": 10, "energy": 8, "materials": 7, "industrials": 6,
            "consumer_staples": 5, "healthcare": 4, "utilities": 2, "real_estate": 1,
        },
        "allocation_asset_class": {"equity": 100},
    },
    {
        "symbol": "EFA",
        "name": "iShares MSCI EAFE ETF",
        "instrument_type": "etf",
        "current_price": 75.80,
        "allocation_regions": {"europe": 65, "asia": 35},
        "allocation_sectors": {
            "financials": 17, "industrials": 15, "healthcare": 13,
            "consumer_discretionary": 12, "consumer_staples": 10, "technology": 9,
            "materials": 8, "energy": 5, "communication": 5, "utilities": 3, "real_estate": 3,
        },
        "allocation_asset_class": {"equity": 100},
    },
    # Fixed Income
    {
        "symbol": "AGG",
        "name": "iShares Core U.S. Aggregate Bond ETF",
        "instrument_type": "bond_fund",
        "current_price": 98.20,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {
            "treasury": 40, "corporate": 25, "mortgage": 28, "government_related": 7,
        },
        "allocation_asset_class": {"fixed_income": 100},
    },
    {
        "symbol": "BND",
        "name": "Vanguard Total Bond Market ETF",
        "instrument_type": "bond_fund",
        "current_price": 72.50,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {
            "treasury": 42, "corporate": 24, "mortgage": 27, "government_related": 7,
        },
        "allocation_asset_class": {"fixed_income": 100},
    },
    {
        "symbol": "TLT",
        "name": "iShares 20+ Year Treasury Bond ETF",
        "instrument_type": "bond_fund",
        "current_price": 92.30,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"treasury": 100},
        "allocation_asset_class": {"fixed_income": 100},
    },
    {
        "symbol": "HYG",
        "name": "iShares iBoxx High Yield Corporate Bond ETF",
        "instrument_type": "bond_fund",
        "current_price": 76.85,
        "allocation_regions": {"north_america": 95, "international": 5},
        "allocation_sectors": {"corporate": 100},
        "allocation_asset_class": {"fixed_income": 100},
    },
    # Sector ETFs
    {
        "symbol": "XLK",
        "name": "Technology Select Sector SPDR Fund",
        "instrument_type": "etf",
        "current_price": 175.40,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"technology": 100},
        "allocation_asset_class": {"equity": 100},
    },
    {
        "symbol": "XLV",
        "name": "Health Care Select Sector SPDR Fund",
        "instrument_type": "etf",
        "current_price": 135.60,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"healthcare": 100},
        "allocation_asset_class": {"equity": 100},
    },
    {
        "symbol": "XLF",
        "name": "Financial Select Sector SPDR Fund",
        "instrument_type": "etf",
        "current_price": 38.25,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"financials": 100},
        "allocation_asset_class": {"equity": 100},
    },
    {
        "symbol": "XLE",
        "name": "Energy Select Sector SPDR Fund",
        "instrument_type": "etf",
        "current_price": 85.90,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"energy": 100},
        "allocation_asset_class": {"equity": 100},
    },
    # Real Estate
    {
        "symbol": "VNQ",
        "name": "Vanguard Real Estate ETF",
        "instrument_type": "etf",
        "current_price": 82.45,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {"real_estate": 100},
        "allocation_asset_class": {"real_estate": 100},
    },
    # Commodities
    {
        "symbol": "GLD",
        "name": "SPDR Gold Shares",
        "instrument_type": "etf",
        "current_price": 195.70,
        "allocation_regions": {"global": 100},
        "allocation_sectors": {"commodities": 100},
        "allocation_asset_class": {"commodities": 100},
    },
    {
        "symbol": "SLV",
        "name": "iShares Silver Trust",
        "instrument_type": "etf",
        "current_price": 22.40,
        "allocation_regions": {"global": 100},
        "allocation_sectors": {"commodities": 100},
        "allocation_asset_class": {"commodities": 100},
    },
    # Mixed/Balanced
    {
        "symbol": "AOR",
        "name": "iShares Core Growth Allocation ETF",
        "instrument_type": "etf",
        "current_price": 48.90,
        "allocation_regions": {"north_america": 60, "international": 40},
        "allocation_sectors": {"diversified": 100},
        "allocation_asset_class": {"equity": 60, "fixed_income": 40},
    },
    {
        "symbol": "AOA",
        "name": "iShares Core Aggressive Allocation ETF",
        "instrument_type": "etf",
        "current_price": 65.15,
        "allocation_regions": {"north_america": 55, "international": 45},
        "allocation_sectors": {"diversified": 100},
        "allocation_asset_class": {"equity": 80, "fixed_income": 20},
    },
    # Growth
    {
        "symbol": "VUG",
        "name": "Vanguard Growth ETF",
        "instrument_type": "etf",
        "current_price": 312.80,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {
            "technology": 45, "consumer_discretionary": 18, "healthcare": 12,
            "industrials": 10, "communication": 8, "financials": 4, "other": 3,
        },
        "allocation_asset_class": {"equity": 100},
    },
    # Value
    {
        "symbol": "VTV",
        "name": "Vanguard Value ETF",
        "instrument_type": "etf",
        "current_price": 152.60,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {
            "financials": 20, "healthcare": 18, "industrials": 12,
            "consumer_staples": 11, "energy": 10, "utilities": 8,
            "communication": 7, "materials": 6, "technology": 5, "other": 3,
        },
        "allocation_asset_class": {"equity": 100},
    },
    # Dividend
    {
        "symbol": "VIG",
        "name": "Vanguard Dividend Appreciation ETF",
        "instrument_type": "etf",
        "current_price": 168.90,
        "allocation_regions": {"north_america": 100},
        "allocation_sectors": {
            "technology": 22, "healthcare": 16, "financials": 14,
            "consumer_staples": 13, "industrials": 12, "consumer_discretionary": 10,
            "utilities": 5, "materials": 4, "other": 4,
        },
        "allocation_asset_class": {"equity": 100},
    },
]


def main():
    print("Seeding instrument data")
    print("=" * 50)
    print(f"Loading {len(INSTRUMENTS)} instruments...")

    # Validate all first
    print("\nValidating allocation data...")
    for inst in INSTRUMENTS:
        try:
            InstrumentCreate(**inst)
        except ValidationError as e:
            print(f"  Validation error in {inst['symbol']}: {e}")
            sys.exit(1)
    print("  All allocations valid.")

    db = Database()

    print("\nInserting instruments...")
    success = 0
    for inst in INSTRUMENTS:
        instrument = InstrumentCreate(**inst)
        db.instruments.create_instrument(instrument)
        success += 1
        print(f"  [{success}/{len(INSTRUMENTS)}] {inst['symbol']}: {inst['name'][:40]}")

    # Verify
    all_instruments = db.instruments.find_all()
    print(f"\nDatabase now contains {len(all_instruments)} instruments.")
    print("\nSeed data loaded successfully.")
    print("\nNext steps:")
    print("1. Create test user: uv run reset_db.py --with-test-data")
    print("2. Verify database: uv run verify_database.py")


if __name__ == "__main__":
    main()
