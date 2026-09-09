import uuid

import pytest
from fastapi.testclient import TestClient

import main
import routers.voice as voice
from fakes import FakeSupabase

client = TestClient(main.app)

WEBHOOK_SECRET = "unit-test-secret"
AUTH_HEADERS = {"Authorization": f"Bearer {WEBHOOK_SECRET}"}

FARMER_ID = str(uuid.uuid4())
DEMO_FARMER_ID = str(uuid.uuid4())
CENTER_ID = str(uuid.uuid4())
TOKEN_ID = str(uuid.uuid4())


def _base_tables(farmer_phone="+919876543210", include_token=True):
    tables = {
        "profiles": [
            {
                "id": FARMER_ID,
                "name": "Ramesh Kumar",
                "phone": farmer_phone,
                "role": "farmer",
                "center_id": None,
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "id": DEMO_FARMER_ID,
                "name": "Demo Farmer",
                "phone": "+910000000000",
                "role": "farmer",
                "center_id": None,
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        ],
        "tokens": [],
    }
    if include_token:
        tables["tokens"].append(
            {
                "id": TOKEN_ID,
                "farmer_id": FARMER_ID,
                "center_id": CENTER_ID,
                "requested_date": "2026-09-10",
                "crop_type": "Wheat",
                "quantity_kg": 500,
                "token_number": None,
                "time_slot": None,
                "status": "pending",
                "procurement_centers": {"name": "Karnal Mandi Center 3"},
            }
        )
    return tables


@pytest.fixture(autouse=True)
def env(monkeypatch):
    """Sane defaults for every test; individual tests override as needed."""
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.delenv("DEMO_FARMER_ID", raising=False)
    yield


def _patch_supabase(monkeypatch, tables):
    monkeypatch.setattr(voice, "supabase", FakeSupabase(tables))


# ---------------------------------------------------------------------
# 1. Registered caller
# ---------------------------------------------------------------------
def test_registered_caller_returns_farmer_and_active_tokens(monkeypatch):
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get("/voice/context", params={"phone": "9876543210"}, headers=AUTH_HEADERS)

    assert r.status_code == 200
    body = r.json()
    assert body["demo_mode_used"] is False
    assert body["caller_number"] == "+919876543210"
    assert body["farmer_id"] == FARMER_ID
    assert body["farmer_name"] == "Ramesh Kumar"
    assert len(body["active_tokens"]) == 1
    assert body["active_tokens"][0]["center_name"] == "Karnal Mandi Center 3"
    assert body["active_tokens"][0]["status"] == "pending"


# ---------------------------------------------------------------------
# 2. Unregistered caller, demo mode enabled
# ---------------------------------------------------------------------
def test_unregistered_caller_demo_mode_enabled(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_FARMER_ID", DEMO_FARMER_ID)

    tables = _base_tables(include_token=False)
    tables["tokens"].append(
        {
            "id": str(uuid.uuid4()),
            "farmer_id": DEMO_FARMER_ID,
            "center_id": CENTER_ID,
            "requested_date": "2026-09-11",
            "crop_type": "Paddy",
            "quantity_kg": 200,
            "token_number": 2,
            "time_slot": "09:25",
            "status": "waiting",
            "procurement_centers": {"name": "Demo Center"},
        }
    )
    _patch_supabase(monkeypatch, tables)

    r = client.get("/voice/context", params={"phone": "9123456789"}, headers=AUTH_HEADERS)

    assert r.status_code == 200
    body = r.json()
    assert body["demo_mode_used"] is True
    assert body["farmer_id"] == DEMO_FARMER_ID
    assert body["farmer_name"] == "Demo Farmer"
    assert len(body["active_tokens"]) == 1
    assert body["active_tokens"][0]["status"] == "waiting"


# ---------------------------------------------------------------------
# 3. Unregistered caller, demo mode disabled
# ---------------------------------------------------------------------
def test_unregistered_caller_demo_mode_disabled(monkeypatch):
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get("/voice/context", params={"phone": "9123456789"}, headers=AUTH_HEADERS)

    assert r.status_code == 404


# ---------------------------------------------------------------------
# 4. Invalid phone number
# ---------------------------------------------------------------------
@pytest.mark.parametrize(
    "bad_phone", ["12345", "abcdefghij", "+1234567890123", "98765432100", ""]
)
def test_invalid_phone_number(monkeypatch, bad_phone):
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get("/voice/context", params={"phone": bad_phone}, headers=AUTH_HEADERS)

    assert r.status_code == 400


# ---------------------------------------------------------------------
# 5. Missing / invalid authorization header
# ---------------------------------------------------------------------
def test_missing_authorization_header(monkeypatch):
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get("/voice/context", params={"phone": "9876543210"})

    assert r.status_code == 401


def test_wrong_authorization_secret(monkeypatch):
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get(
        "/voice/context",
        params={"phone": "9876543210"},
        headers={"Authorization": "Bearer wrong-secret"},
    )

    assert r.status_code == 401


def test_malformed_authorization_header_missing_bearer_prefix(monkeypatch):
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get(
        "/voice/context",
        params={"phone": "9876543210"},
        headers={"Authorization": WEBHOOK_SECRET},  # no "Bearer " prefix
    )

    assert r.status_code == 401


# ---------------------------------------------------------------------
# 6. Demo farmer id missing or invalid
# ---------------------------------------------------------------------
def test_demo_mode_enabled_but_demo_farmer_id_missing(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("DEMO_FARMER_ID", raising=False)
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get("/voice/context", params={"phone": "9123456789"}, headers=AUTH_HEADERS)

    assert r.status_code == 500


def test_demo_mode_enabled_but_demo_farmer_id_not_a_uuid(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_FARMER_ID", "not-a-uuid")
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get("/voice/context", params={"phone": "9123456789"}, headers=AUTH_HEADERS)

    assert r.status_code == 500


def test_demo_mode_enabled_but_demo_farmer_id_not_found(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_FARMER_ID", str(uuid.uuid4()))  # valid UUID, no matching row
    _patch_supabase(monkeypatch, _base_tables())

    r = client.get("/voice/context", params={"phone": "9123456789"}, headers=AUTH_HEADERS)

    assert r.status_code == 500


# ---------------------------------------------------------------------
# 7. Farmer with no active tokens
# ---------------------------------------------------------------------
def test_farmer_with_no_active_tokens(monkeypatch):
    _patch_supabase(monkeypatch, _base_tables(include_token=False))

    r = client.get("/voice/context", params={"phone": "+919876543210"}, headers=AUTH_HEADERS)

    assert r.status_code == 200
    assert r.json()["active_tokens"] == []