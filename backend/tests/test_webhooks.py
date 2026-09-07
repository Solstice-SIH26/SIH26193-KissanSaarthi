import json
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

import main
import routers.centers as centers
import routers.tokens as tokens_router
import routers.voice as voice
import routers.webhooks as webhooks
import services.voice_booking as voice_booking
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
    """Several reused helpers live in different modules (routers.voice,
    routers.webhooks, routers.centers, routers.tokens,
    services.voice_booking), each holding its own `supabase` name bound
    at import time. Patch all of them to the same fake instance so every
    reused code path -- including the Milestone 5 write path through
    create_token() -- sees consistent data."""
    fake = FakeSupabase(tables)
    monkeypatch.setattr(voice, "supabase", fake)
    monkeypatch.setattr(webhooks, "supabase", fake)
    monkeypatch.setattr(centers, "supabase", fake)
    monkeypatch.setattr(tokens_router, "supabase", fake)
    monkeypatch.setattr(voice_booking, "supabase", fake)
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


# =======================================================================
# Milestone 5 -- create_token_request
#
# Dates below are all computed relative to date.today() rather than
# hardcoded, so these tests keep passing regardless of when they're run
# (see voice_booking._parse_requested_date, which rejects past dates).
# =======================================================================
TODAY = date.today()
FUTURE_DATE = (TODAY + timedelta(days=5)).isoformat()
SECOND_FUTURE_DATE = (TODAY + timedelta(days=6)).isoformat()
THIRD_FUTURE_DATE = (TODAY + timedelta(days=7)).isoformat()
FAR_FUTURE_DATE = (TODAY + timedelta(days=300)).isoformat()
PAST_DATE = (TODAY - timedelta(days=1)).isoformat()

WINDOW_OPEN = (TODAY + timedelta(days=10)).isoformat()
WINDOW_CLOSE = (TODAY + timedelta(days=20)).isoformat()
BEFORE_WINDOW_DATE = (TODAY + timedelta(days=2)).isoformat()
WITHIN_WINDOW_DATE = (TODAY + timedelta(days=15)).isoformat()
AFTER_WINDOW_DATE = (TODAY + timedelta(days=25)).isoformat()

BOOKING_CENTER_ID = str(uuid.uuid4())  # active, crop "Bajra", no open/close window
WINDOW_CENTER_ID = str(uuid.uuid4())  # active, crop "Mustard", has an open/close window

_OMIT = object()  # sentinel: drop this key entirely rather than setting it to None


def _booking_tables():
    """_base_tables() plus two centres purpose-built for booking tests:
    one with no open_date/close_date (tests the nullable-boundary case),
    one with a real window (tests before/after rejection)."""
    tables = _base_tables()
    tables["procurement_centers"].append(
        {
            "id": BOOKING_CENTER_ID,
            "name": "Open Booking Center",
            "location": "Test Location",
            "crop_type": "Bajra",
            "msp_rate": 2900.00,
            "open_date": None,
            "close_date": None,
            "daily_capacity_kg": 5000,
            "is_active": True,
        }
    )
    tables["procurement_centers"].append(
        {
            "id": WINDOW_CENTER_ID,
            "name": "Windowed Center",
            "location": "Test Location",
            "crop_type": "Mustard",
            "msp_rate": 6200.00,
            "open_date": WINDOW_OPEN,
            "close_date": WINDOW_CLOSE,
            "daily_capacity_kg": 5000,
            "is_active": True,
        }
    )
    return tables


def _booking_args(**overrides):
    args = {
        "center_id": BOOKING_CENTER_ID,
        "crop_type": "Bajra",
        "quantity_kg": 500,
        "requested_date": FUTURE_DATE,
        "confirmed": True,
    }
    for key, value in overrides.items():
        if value is _OMIT:
            args.pop(key, None)
        else:
            args[key] = value
    return args


def _booking_body(arguments, call_id="book1", customer_number="+919876543210"):
    return _webhook_body(
        [_tool_call(call_id, "create_token_request", arguments)],
        customer_number=customer_number,
    )


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------
def test_create_token_request_valid_booking_succeeds(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())

    r = _post(_booking_body(_booking_args()))

    assert r.status_code == 200
    result = _result_json(r)
    assert result["success"] is True
    assert result["status"] == "pending"
    assert result["center_name"] == "Open Booking Center"
    assert result["crop_type"] == "Bajra"
    assert result["requested_date"] == FUTURE_DATE


def test_create_token_request_inserts_correct_pending_row(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args()))

    assert r.status_code == 200
    rows = fake._tables["tokens"]
    assert len(rows) == before + 1
    new_row = rows[-1]
    assert new_row["farmer_id"] == FARMER_ID
    assert new_row["center_id"] == BOOKING_CENTER_ID
    assert new_row["status"] == "pending"
    assert new_row["requested_date"] == FUTURE_DATE
    assert new_row["quantity_kg"] == 500
    # Not assigned until staff approval, regardless of what the caller sent.
    assert new_row.get("token_number") is None
    assert new_row.get("time_slot") is None


def test_create_token_request_crop_match_is_case_insensitive_and_stores_canonical_name(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())

    r = _post(_booking_body(_booking_args(crop_type="  bAjRa  ")))

    assert r.status_code == 200
    result = _result_json(r)
    assert result["success"] is True
    # Stored crop is the centre's canonical value, not the caller's spelling/casing.
    assert result["crop_type"] == "Bajra"
    assert fake._tables["tokens"][-1]["crop_type"] == "Bajra"


def test_create_token_request_result_matches_tool_call_id(monkeypatch):
    _patch_all_supabase(monkeypatch, _booking_tables())

    r = _post(_booking_body(_booking_args(), call_id="my-unique-call-id"))

    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 1
    assert results[0]["toolCallId"] == "my-unique-call-id"


# ---------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------
def test_create_token_request_missing_confirmation_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(confirmed=_OMIT)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "confirm" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_confirmed_false_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(confirmed=False)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_confirmed_as_string_embeds_error(monkeypatch):
    """Vapi must send a real Boolean; the literal string "true" must not
    be treated as confirmation."""
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(confirmed="true")))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert len(fake._tables["tokens"]) == before


# ---------------------------------------------------------------------
# Caller identification (shared _identify_farmer path)
# ---------------------------------------------------------------------
def test_create_token_request_missing_caller_phone_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(), customer_number=None))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "phone" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_explicit_phone_argument_succeeds(monkeypatch):
    """Dashboard/curl testing path: no live-call customer metadata, phone
    passed as a plain tool argument instead."""
    fake = _patch_all_supabase(monkeypatch, _booking_tables())

    r = _post(
        _booking_body(
            _booking_args(phone="9876543210"),
            customer_number=None,
        )
    )

    assert r.status_code == 200
    result = _result_json(r)
    assert result["success"] is True


def test_create_token_request_invalid_phone_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(), customer_number="12345"))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_unregistered_farmer_demo_off_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(), customer_number="+919999999999"))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_demo_fallback_when_enabled(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_FARMER_ID", DEMO_FARMER_ID)
    fake = _patch_all_supabase(monkeypatch, _booking_tables())

    r = _post(_booking_body(_booking_args(), customer_number="+919999999999"))

    assert r.status_code == 200
    result = _result_json(r)
    assert result["success"] is True
    assert fake._tables["tokens"][-1]["farmer_id"] == DEMO_FARMER_ID


# ---------------------------------------------------------------------
# center_id
# ---------------------------------------------------------------------
def test_create_token_request_missing_center_id_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(center_id=_OMIT)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "centre" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_malformed_center_id_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(center_id="not-a-uuid")))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_center_not_found_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(center_id=str(uuid.uuid4()))))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "find" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_inactive_center_embeds_error(monkeypatch):
    tables = _booking_tables()
    inactive_id = next(
        c["id"] for c in tables["procurement_centers"] if c["name"] == "Closed Center"
    )
    fake = _patch_all_supabase(monkeypatch, tables)
    before = len(fake._tables["tokens"])

    r = _post(
        _booking_body(
            _booking_args(center_id=inactive_id, crop_type="Paddy")
        )
    )

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "not currently accepting" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


# ---------------------------------------------------------------------
# crop_type
# ---------------------------------------------------------------------
def test_create_token_request_missing_crop_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(crop_type=_OMIT)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "crop" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_crop_mismatch_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(crop_type="Wheat")))  # centre grows Bajra

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "only accepts" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


# ---------------------------------------------------------------------
# quantity_kg
# ---------------------------------------------------------------------
def test_create_token_request_missing_quantity_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(quantity_kg=_OMIT)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "number" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_non_numeric_quantity_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(quantity_kg="lots")))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "number" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_zero_quantity_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(quantity_kg=0)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "greater than 0" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_negative_quantity_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(quantity_kg=-50)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "greater than 0" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


# ---------------------------------------------------------------------
# requested_date
# ---------------------------------------------------------------------
def test_create_token_request_missing_date_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(requested_date=_OMIT)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "required" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_malformed_date_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(requested_date="10 September 2026")))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "yyyy-mm-dd" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_past_date_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(_booking_body(_booking_args(requested_date=PAST_DATE)))

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "past" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_date_before_center_opening_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(
        _booking_body(
            _booking_args(
                center_id=WINDOW_CENTER_ID,
                crop_type="Mustard",
                requested_date=BEFORE_WINDOW_DATE,
            )
        )
    )

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "only accepts requests from" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_date_after_center_closing_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])

    r = _post(
        _booking_body(
            _booking_args(
                center_id=WINDOW_CENTER_ID,
                crop_type="Mustard",
                requested_date=AFTER_WINDOW_DATE,
            )
        )
    )

    assert r.status_code == 200
    result = _result_json(r)
    assert "error" in result
    assert "only accepts requests from" in result["error"].lower()
    assert len(fake._tables["tokens"]) == before


def test_create_token_request_within_center_window_succeeds(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())

    r = _post(
        _booking_body(
            _booking_args(
                center_id=WINDOW_CENTER_ID,
                crop_type="Mustard",
                requested_date=WITHIN_WINDOW_DATE,
            )
        )
    )

    assert r.status_code == 200
    result = _result_json(r)
    assert result["success"] is True


def test_create_token_request_nullable_center_dates_allow_any_future_date(monkeypatch):
    """BOOKING_CENTER_ID has open_date=None, close_date=None -- no window
    restriction should apply, even for a far-future date."""
    fake = _patch_all_supabase(monkeypatch, _booking_tables())

    r = _post(_booking_body(_booking_args(requested_date=FAR_FUTURE_DATE)))

    assert r.status_code == 200
    result = _result_json(r)
    assert result["success"] is True
    assert result["requested_date"] == FAR_FUTURE_DATE


# ---------------------------------------------------------------------
# Existing create_token() rules, reused unchanged: same-day + max-3-active
# ---------------------------------------------------------------------
def test_create_token_request_third_active_request_succeeds_fourth_rejected(monkeypatch):
    """The farmer already has one active (pending) token from the base
    fixture. Two more successful voice bookings bring that to 3 total
    (the max). A fourth must be rejected, and must not insert a row."""
    fake = _patch_all_supabase(monkeypatch, _booking_tables())

    r2 = _post(
        _booking_body(
            _booking_args(requested_date=SECOND_FUTURE_DATE), call_id="book2"
        )
    )
    assert r2.status_code == 200
    assert _result_json(r2, 0)["success"] is True

    r3 = _post(
        _booking_body(
            _booking_args(requested_date=THIRD_FUTURE_DATE), call_id="book3"
        )
    )
    assert r3.status_code == 200
    assert _result_json(r3, 0)["success"] is True

    before_fourth = len(fake._tables["tokens"])
    r4 = _post(
        _booking_body(
            _booking_args(requested_date=FAR_FUTURE_DATE), call_id="book4"
        )
    )
    assert r4.status_code == 200
    result4 = _result_json(r4, 0)
    assert "error" in result4
    assert "already have 3 active requests" in result4["error"].lower()
    assert len(fake._tables["tokens"]) == before_fourth


def test_create_token_request_duplicate_active_date_rejected(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())

    # Use WITHIN_WINDOW_DATE, not FUTURE_DATE: it needs to be valid for
    # BOTH centres involved below. BOOKING_CENTER_ID has no date window
    # at all, but WINDOW_CENTER_ID only accepts dates inside its own
    # open/close range -- FUTURE_DATE falls before that range opens.
    r1 = _post(_booking_body(_booking_args(requested_date=WITHIN_WINDOW_DATE), call_id="book1"))
    assert r1.status_code == 200
    assert _result_json(r1, 0)["success"] is True

    before_second = len(fake._tables["tokens"])
    r2 = _post(
        _booking_body(
            _booking_args(
                center_id=WINDOW_CENTER_ID,
                crop_type="Mustard",
                requested_date=WITHIN_WINDOW_DATE,  # same date as book1, different centre
            ),
            call_id="book2",
        )
    )
    assert r2.status_code == 200
    result2 = _result_json(r2, 0)
    assert "error" in result2
    assert "already have an active request" in result2["error"].lower()
    assert len(fake._tables["tokens"]) == before_second


# ---------------------------------------------------------------------
# Database failure during the write step
# ---------------------------------------------------------------------
class _FailingTokensSupabase:
    """Wraps a working FakeSupabase but simulates an outage specifically
    for the 'tokens' table -- lets the centre lookup inside
    services.voice_booking succeed normally, so the failure is isolated
    to the write step, the way a real transient Supabase outage during
    insert would behave."""

    def __init__(self, fake):
        self._fake = fake

    def table(self, name):
        if name == "tokens":
            raise RuntimeError("simulated supabase outage")
        return self._fake.table(name)


def test_create_token_request_database_failure_embeds_error(monkeypatch):
    fake = _patch_all_supabase(monkeypatch, _booking_tables())
    before = len(fake._tables["tokens"])
    monkeypatch.setattr(tokens_router, "supabase", _FailingTokensSupabase(fake))

    r = _post(_booking_body(_booking_args()))

    assert r.status_code == 200  # request itself doesn't fail
    result = _result_json(r)
    assert "error" in result
    assert len(fake._tables["tokens"]) == before