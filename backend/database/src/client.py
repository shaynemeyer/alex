"""
Supabase client wrapper for Alex database operations.
"""

import os
from supabase import create_client

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass


class SupabaseClient:
    """Thin wrapper around the supabase-py client."""

    def __init__(self):
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        self.client = create_client(url, key)

    def table(self, name: str):
        return self.client.table(name)
