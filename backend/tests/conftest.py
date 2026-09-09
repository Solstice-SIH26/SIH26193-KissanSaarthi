import os
import sys
from pathlib import Path

# The app's modules use flat imports (`from db import supabase`, etc.),
# which assumes the app is run from inside backend/ (e.g. `uvicorn main:app`
# from that directory). Make tests behave the same way regardless of where
# pytest is invoked from.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# db.py calls create_client(SUPABASE_URL, SUPABASE_KEY) at import time and
# raises RuntimeError if either is missing. These are dummy values only —
# no real network call is made by create_client() itself, and every test
# below replaces the `supabase` object voice.py actually uses with an
# in-memory fake before exercising any endpoint logic.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")