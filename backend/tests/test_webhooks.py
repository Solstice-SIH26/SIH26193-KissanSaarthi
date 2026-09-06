import json
import uuid

import pytest
from fastapi.testclient import TestClient

import main
import routers.centers as centers
import routers.voice as voice
import routers.webhooks as webhooks
from fakes import FakeSupabase

client = TestClient(main.app)

WEBHOOK_SECRET = "unit-test-secret"
AUTH_HEADERS = {"Authorization": f"Bearer {WEBHOOK_SECRET}"}

FARMER_ID = str(uuid.uuid4())
DEMO_FARMER_ID = str(uuid.uuid4())
CENTER_ID = str(uuid.uuid4())


def _base_tables(farmer_phone="+919876543210"):
    """Shared fixture data: one registered farmer, one demo farmer, a
    handful of tokens across different statuses, and two centres (one
    active, one inactive) for list_active_centres."""
    return {
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
        "tokens": [
            {
                "id": str(uuid.uuid4()),
                "farmer_id": FARMER_ID,
                "center_id": CENTER_ID,
                "requested_date": "2026-09-10",
                "crop_type": "Wheat",
                "quantity_kg": 500,
                "token_number": None,
                "time_slot": None,
                "status": "pending",
                "created_at": "2026-09-01T09:00:00+00:00",
                "procurement_centers": {"name": "Karnal Mandi Center 3"},
            },
            {
                "id": str(uuid.uuid4()),
                "farmer_id": FARMER_ID,
                "center_id": CENTER_ID,
                "requested_date": "2026-08-01",
                "crop_type": "Wheat",
                "quantity_kg": 300,
                "token_number": 5,
                "time_slot": "09:50",
                "status": "completed",
                "created_at": "2026-07-25T09:00:00+00:00",
                "procurement_centers": {"name": "Karnal Mandi Center 3"},
            },
            {
                "id": str(uuid.uuid4()),
                "farmer_id": FARMER_ID,
                "center_id": CENTER_ID,
                "requested_date": "2026-07-01",
                "crop_type": "Wheat",
                "quantity_kg": 100,
                "token_number": None,
                "time_slot": None,
                "status": "rejected",
                "created_at": "2026-06-25T09:00:00+00:00",
                "procurement_centers": {"name": "Karnal Mandi Center 3"},
            },
        ],
        "procurement_centers": [
            {
                "id": CENTER_ID,
                "name": "Karnal Mandi Center 3",
                "location": "Karnal, Haryana",
                "crop_type": "Wheat",
                "msp_rate": 2425.00,
                "open_date": "2026-09-01",
                "close_date": "2026-09-15",
                "daily_capacity_kg": 5000,
                "is_active": True,
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Closed Center",
                "location": "Sonipat, Haryana",
                "crop_type": "Paddy",
                "msp_rate": 2300.00,
                "open_date": "2026-01-01",
                "close_date": "2026-01-15",
                "daily_capacity_kg": 4000,
                "is_active": False,
            },
        ],
    }


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.delenv("DEMO_FARMER_ID", raising=False)
    yield


def _patch_all_supabase(monkeypatch, tables):
    """Several reused helpers live in different router modules
    (routers.voice, routers.webhooks, routers.centers), each holding its
    own `supabase` name bound at import time. Patch all three to the same
    fake instance so every reused code path sees consistent data."""
    fake = FakeSupabase(tables)
    monkeypatch.setattr(voice, "supabase", fake)
    monkeypatch.setattr(webhooks, "supabase", fake)
    monkeypatch.setattr(centers, "supabase", fake)
    return fake


def _tool_call(call_id, name, arguments=None):
    return {"id": call_id, "function": {"name": name, "arguments": arguments or {}}}


def _webhook_body(tool_calls, customer_number=None):
    message = {"type": "tool-calls", "toolCallList": tool_calls}
    if customer_number:
        message["customer"] = {"number": customer_number}
    return {"message": message}


def _post(body, headers=AUTH_HEADERS):
    return client.post("/webhooks/vapi", json=body, headers=headers)


def _result_json(response, index=0):
    return json.loads(response.json()["results"][index]["result"])


# ---------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------
def test_missing_authorization_header(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body([_tool_call("c1", "list_active_centres")])

    r = client.post("/webhooks/vapi", json=body)  # no headers

    assert r.status_code == 401


def test_wrong_authorization_secret(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body([_tool_call("c1", "list_active_centres")])

    r = _post(body, headers={"Authorization": "Bearer wrong-secret"})

    assert r.status_code == 401


# ---------------------------------------------------------------------
# Malformed payload / missing toolCallId
# ---------------------------------------------------------------------
def test_malformed_payload_missing_message(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())

    r = _post({"not_message": {}})

    assert r.status_code == 400


def test_malformed_payload_missing_tool_call_list(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())

    r = _post({"message": {"type": "tool-calls"}})

    assert r.status_code == 400


def test_tool_call_missing_id(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [{"function": {"name": "list_active_centres", "arguments": {}}}],
        }
    }

    r = _post(body)

    assert r.status_code == 400


# ---------------------------------------------------------------------
# get_farmer_context
# ---------------------------------------------------------------------
def test_get_farmer_context_registered_caller(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [_tool_call("c1", "get_farmer_context")],
        customer_number="+919876543210",
    )

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    assert result["farmer_name"] == "Ramesh Kumar"
    assert result["demo_mode_used"] is False
    # Only pending is "active" -> completed/rejected excluded here
    assert len(result["active_tokens"]) == 1
    assert result["active_tokens"][0]["status"] == "pending"


def test_get_farmer_context_demo_mode_enabled(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_FARMER_ID", DEMO_FARMER_ID)
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [_tool_call("c1", "get_farmer_context")],
        customer_number="+919999999999",  # not registered
    )

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    assert result["demo_mode_used"] is True
    assert result["farmer_name"] == "Demo Farmer"


def test_get_farmer_context_unregistered_demo_off_embeds_error(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [_tool_call("c1", "get_farmer_context")],
        customer_number="+919999999999",
    )

    r = _post(body)

    assert r.status_code == 200  # HTTP succeeds; error is embedded
    result = _result_json(r)
    assert "error" in result
    assert "not registered" in result["error"].lower() or "no farmer" in result["error"].lower()


def test_get_farmer_context_missing_caller_number(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body([_tool_call("c1", "get_farmer_context")])  # no customer, no phone arg

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "phone" in result["error"].lower()


def test_get_farmer_context_invalid_phone_number(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [_tool_call("c1", "get_farmer_context")],
        customer_number="12345",
    )

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result


def test_get_farmer_context_via_explicit_phone_argument(monkeypatch):
    """Fallback path for manual/dashboard testing without a live call."""
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [_tool_call("c1", "get_farmer_context", {"phone": "9876543210"})]
    )

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    assert result["farmer_name"] == "Ramesh Kumar"


# ---------------------------------------------------------------------
# get_token_status
# ---------------------------------------------------------------------
def test_get_token_status_returns_all_statuses(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [_tool_call("c1", "get_token_status")],
        customer_number="+919876543210",
    )

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    statuses = {t["status"] for t in result["tokens"]}
    assert statuses == {"pending", "completed", "rejected"}
    # centre name should be included where available
    assert all(t["center_name"] == "Karnal Mandi Center 3" for t in result["tokens"])


def test_get_token_status_filtered_by_token_number(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [_tool_call("c1", "get_token_status", {"token_number": 5})],
        customer_number="+919876543210",
    )

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    assert len(result["tokens"]) == 1
    assert result["tokens"][0]["status"] == "completed"


def test_get_token_status_unregistered_demo_off_embeds_error(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [_tool_call("c1", "get_token_status")],
        customer_number="+919999999999",
    )

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result


# ---------------------------------------------------------------------
# list_active_centres
# ---------------------------------------------------------------------
def test_list_active_centres_returns_only_active(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body([_tool_call("c1", "list_active_centres")])

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    names = [c["name"] for c in result["centres"]]
    assert "Karnal Mandi Center 3" in names
    assert "Closed Center" not in names
    # Centre ID is retained internally for the future booking tool.
    assert set(result["centres"][0].keys()) == {
        "id",
        "name",
        "location",
        "crop_type",
        "msp_rate",
    }


# ---------------------------------------------------------------------
# Unsupported tool name
# ---------------------------------------------------------------------
def test_unsupported_tool_name_embeds_error(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body([_tool_call("c1", "approve_token")])  # not a supported read-only tool

    r = _post(body)

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "unsupported tool" in result["error"].lower()


# ---------------------------------------------------------------------
# Multiple tool calls in one request
# ---------------------------------------------------------------------
def test_multiple_tool_calls_in_one_request(monkeypatch):
    _patch_all_supabase(monkeypatch, _base_tables())
    body = _webhook_body(
        [
            _tool_call("c1", "list_active_centres"),
            _tool_call("c2", "get_farmer_context", {"phone": "9876543210"}),
        ]
    )

    r = _post(body)

    assert r.status_code == 200
    results = r.json()["results"]
    assert {res["toolCallId"] for res in results} == {"c1", "c2"}


# ---------------------------------------------------------------------
# Supabase errors handled gracefully
# ---------------------------------------------------------------------
class _RaisingSupabase:
    def table(self, name):
        raise RuntimeError("simulated supabase outage")


def test_supabase_error_is_handled_gracefully(monkeypatch):
    monkeypatch.setattr(centers, "supabase", _RaisingSupabase())
    body = _webhook_body([_tool_call("c1", "list_active_centres")])

    r = _post(body)

    assert r.status_code == 200  # request itself doesn't fail
    result = _result_json(r)
    assert "error" in result

def test_get_farmer_context_missing_phone_uses_demo_farmer(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_FARMER_ID", DEMO_FARMER_ID)
    _patch_all_supabase(monkeypatch, _base_tables())

    body = _webhook_body([
        _tool_call("c1", "get_farmer_context")
    ])

    response = _post(body)

    assert response.status_code == 200

    result = _result_json(response)

    assert result["demo_mode_used"] is True
    assert result["caller_number"] is None
    assert result["farmer_name"] == "Demo Farmer"

def test_get_token_status_missing_phone_uses_demo_farmer(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_FARMER_ID", DEMO_FARMER_ID)

    tables = _base_tables()

    # Give one token to the demo farmer.
    tables["tokens"][0]["farmer_id"] = DEMO_FARMER_ID

    _patch_all_supabase(monkeypatch, tables)

    body = _webhook_body([
        _tool_call("c1", "get_token_status")
    ])

    response = _post(body)

    assert response.status_code == 200

    result = _result_json(response)

    assert result["farmer_name"] == "Demo Farmer"
    assert len(result["tokens"]) == 1