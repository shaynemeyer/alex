"""
Database models using the supabase-py query builder.
Public interface is identical to the Aurora Data API version.
"""

from typing import Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal

from .client import SupabaseClient
from .schemas import InstrumentCreate


class Users:
    def __init__(self, db: SupabaseClient):
        self.db = db

    def find_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict]:
        rows = self.db.table("users").select("*").eq("clerk_user_id", clerk_user_id).execute().data
        return rows[0] if rows else None

    def create_user(
        self,
        clerk_user_id: str,
        display_name: str = None,
        years_until_retirement: int = None,
        target_retirement_income: Decimal = None,
    ) -> str:
        data = {"clerk_user_id": clerk_user_id}
        if display_name is not None:
            data["display_name"] = display_name
        if years_until_retirement is not None:
            data["years_until_retirement"] = years_until_retirement
        if target_retirement_income is not None:
            data["target_retirement_income"] = float(target_retirement_income)
        self.db.table("users").insert(data).execute()
        return clerk_user_id

    def update_user(self, clerk_user_id: str, data: Dict) -> None:
        self.db.table("users").update(data).eq("clerk_user_id", clerk_user_id).execute()


class Instruments:
    def __init__(self, db: SupabaseClient):
        self.db = db

    def find_all(self, limit: int = None, offset: int = 0) -> List[Dict]:
        return self.db.table("instruments").select("*").order("symbol").execute().data

    def find_by_symbol(self, symbol: str) -> Optional[Dict]:
        rows = self.db.table("instruments").select("*").eq("symbol", symbol).execute().data
        return rows[0] if rows else None

    def find_by_type(self, instrument_type: str) -> List[Dict]:
        return (
            self.db.table("instruments")
            .select("*")
            .eq("instrument_type", instrument_type)
            .order("symbol")
            .execute()
            .data
        )

    def search(self, query: str) -> List[Dict]:
        q = query.replace("%", "")  # sanitize
        return (
            self.db.table("instruments")
            .select("*")
            .or_(f"symbol.ilike.%{q}%,name.ilike.%{q}%")
            .limit(20)
            .execute()
            .data
        )

    def create_instrument(self, instrument: InstrumentCreate) -> str:
        validated = instrument.model_dump()
        data = {
            "symbol": validated["symbol"],
            "name": validated["name"],
            "instrument_type": validated["instrument_type"],
            "current_price": float(validated["current_price"]) if validated.get("current_price") else None,
            "allocation_regions": validated["allocation_regions"],
            "allocation_sectors": validated["allocation_sectors"],
            "allocation_asset_class": validated["allocation_asset_class"],
        }
        self.db.table("instruments").upsert(data, on_conflict="symbol").execute()
        return validated["symbol"]


class Accounts:
    def __init__(self, db: SupabaseClient):
        self.db = db

    def find_by_user(self, clerk_user_id: str) -> List[Dict]:
        return (
            self.db.table("accounts")
            .select("*")
            .eq("clerk_user_id", clerk_user_id)
            .order("created_at", desc=True)
            .execute()
            .data
        )

    def find_by_id(self, account_id: str) -> Optional[Dict]:
        rows = self.db.table("accounts").select("*").eq("id", account_id).execute().data
        return rows[0] if rows else None

    def create_account(
        self,
        clerk_user_id: str,
        account_name: str,
        account_purpose: str = None,
        cash_balance: Decimal = Decimal("0"),
        cash_interest: Decimal = Decimal("0"),
    ) -> str:
        data = {
            "clerk_user_id": clerk_user_id,
            "account_name": account_name,
            "account_purpose": account_purpose,
            "cash_balance": float(cash_balance),
            "cash_interest": float(cash_interest),
        }
        rows = self.db.table("accounts").insert(data).execute().data
        return rows[0]["id"]

    def update_account(self, account_id: str, data: Dict) -> None:
        self.db.table("accounts").update(data).eq("id", account_id).execute()

    def delete(self, account_id: str) -> None:
        self.db.table("accounts").delete().eq("id", account_id).execute()


class Positions:
    def __init__(self, db: SupabaseClient):
        self.db = db

    def find_by_account(self, account_id: str) -> List[Dict]:
        rows = (
            self.db.table("positions")
            .select("*, instruments(name, instrument_type, current_price)")
            .eq("account_id", account_id)
            .order("symbol")
            .execute()
            .data
        )
        # Flatten the nested instruments embed to match the original interface
        for row in rows:
            inst = row.pop("instruments", None) or {}
            row["instrument_name"] = inst.get("name")
            row["instrument_type"] = inst.get("instrument_type")
            row["current_price"] = inst.get("current_price")
        return rows

    def get_portfolio_value(self, account_id: str) -> Dict:
        rows = (
            self.db.table("positions")
            .select("quantity, instruments(current_price)")
            .eq("account_id", account_id)
            .execute()
            .data
        )
        total = sum(
            float(r["quantity"]) * float((r.get("instruments") or {}).get("current_price") or 0)
            for r in rows
        )
        total_shares = sum(float(r["quantity"]) for r in rows)
        return {
            "num_positions": len(rows),
            "total_value": total,
            "total_shares": total_shares,
        }

    def find_by_id(self, position_id: str) -> Optional[Dict]:
        rows = self.db.table("positions").select("*").eq("id", position_id).execute().data
        return rows[0] if rows else None

    def update(self, position_id: str, data: Dict) -> None:
        self.db.table("positions").update(data).eq("id", position_id).execute()

    def delete(self, position_id: str) -> None:
        self.db.table("positions").delete().eq("id", position_id).execute()

    def add_position(self, account_id: str, symbol: str, quantity: Decimal) -> Optional[str]:
        data = {
            "account_id": account_id,
            "symbol": symbol,
            "quantity": float(quantity),
            "as_of_date": date.today().isoformat(),
        }
        rows = (
            self.db.table("positions")
            .upsert(data, on_conflict="account_id,symbol")
            .execute()
            .data
        )
        return rows[0]["id"] if rows else None


class Jobs:
    def __init__(self, db: SupabaseClient):
        self.db = db

    def find_by_id(self, job_id: str) -> Optional[Dict]:
        rows = self.db.table("jobs").select("*").eq("id", job_id).execute().data
        return rows[0] if rows else None

    def find_by_user(self, clerk_user_id: str, status: str = None, limit: int = 20) -> List[Dict]:
        q = self.db.table("jobs").select("*").eq("clerk_user_id", clerk_user_id)
        if status:
            q = q.eq("status", status)
        return q.order("created_at", desc=True).limit(limit).execute().data

    def create_job(self, clerk_user_id: str, job_type: str, request_payload: Dict = None) -> str:
        data = {
            "clerk_user_id": clerk_user_id,
            "job_type": job_type,
            "status": "pending",
            "request_payload": request_payload,
        }
        rows = self.db.table("jobs").insert(data).execute().data
        return rows[0]["id"]

    def update_status(self, job_id: str, status: str, error_message: str = None) -> None:
        data: Dict = {"status": status}
        if status == "running":
            data["started_at"] = datetime.utcnow().isoformat()
        elif status in ("completed", "failed"):
            data["completed_at"] = datetime.utcnow().isoformat()
        if error_message:
            data["error_message"] = error_message
        self.db.table("jobs").update(data).eq("id", job_id).execute()

    def update_report(self, job_id: str, report_payload: Dict) -> None:
        self.db.table("jobs").update({"report_payload": report_payload}).eq("id", job_id).execute()

    def update_charts(self, job_id: str, charts_payload: Dict) -> None:
        self.db.table("jobs").update({"charts_payload": charts_payload}).eq("id", job_id).execute()

    def update_retirement(self, job_id: str, retirement_payload: Dict) -> None:
        self.db.table("jobs").update({"retirement_payload": retirement_payload}).eq("id", job_id).execute()

    def update_summary(self, job_id: str, summary_payload: Dict) -> None:
        self.db.table("jobs").update({"summary_payload": summary_payload}).eq("id", job_id).execute()

    def delete(self, job_id: str) -> None:
        self.db.table("jobs").delete().eq("id", job_id).execute()


class Database:
    """Main database interface — identical public API to the Aurora Data API version."""

    def __init__(self):
        self.client = SupabaseClient()
        self.users = Users(self.client)
        self.instruments = Instruments(self.client)
        self.accounts = Accounts(self.client)
        self.positions = Positions(self.client)
        self.jobs = Jobs(self.client)
