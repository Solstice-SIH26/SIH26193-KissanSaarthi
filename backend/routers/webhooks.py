"""
Voice (Vapi) integration — Milestone 2: read-only webhook.

POST /webhooks/vapi handles Vapi's "tool-calls" server messages for three
read-only tools:

    get_farmer_context   - identify caller, return name + active tokens
    get_token_status      - return the farmer's token(s), any status
    list_active_centres   - list active procurement centres

This endpoint does NOT create, approve, reject, cancel, or otherwise
mutate anything. All Supabase writes still go exclusively through the
existing /tokens and /centers routers.

Reuse:
    - normalize_indian_phone, _find_farmer_by_phone, _resolve_demo_farmer,
      _fetch_active_tokens are imported directly from routers.voice
      (Milestone 1) rather than reimplemented here.
    - list_active_centres calls routers.centers.list_centers() directly
      instead of re-querying procurement_centers.

Error handling model:
    - Missing/wrong VAPI_WEBHOOK_SECRET, or a structurally malformed
      payload (no `message`, no `toolCallList`, or a tool call missing
      `id`) -> real HTTP error (401 / 400). Nothing can be salvaged in
      these cases.
    - Everything else (unsupported tool name, missing/invalid caller
      phone, farmer not found with demo mode off, misconfigured demo
      farmer, unexpected Supabase errors) is embedded as
      {"error": "..."} inside that specific tool call's `result` string,
      with the HTTP response staying 200. Vapi sends one matched result
      per toolCallId; failing the whole HTTP request over one bad tool
      call in a batch would silence the assistant for every other tool
      call in the same request too.
"""

import json
import logging
import os
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, Request

from db import supabase
from routers.centers import list_centers as _list_centers_query
from routers.voice import (
    _fetch_active_tokens,
    _find_farmer_by_phone,
    _resolve_demo_farmer,
    normalize_indian_phone,
)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)

SUPPORTED_TOOLS = ("get_farmer_context", "get_token_status", "list_active_centres")


# ---------------------------------------------------------------------
# Auth (same secret/scheme as GET /voice/context)
# ---------------------------------------------------------------------
def _verify_webhook_secret(authorization: Optional[str]) -> None:
    expected = os.environ.get("VAPI_WEBHOOK_SECRET")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="VAPI_WEBHOOK_SECRET is not configured on the server.",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[len("Bearer "):].strip()
    if token != expected:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")


# ---------------------------------------------------------------------
# Caller identification (shared by get_farmer_context and get_token_status)
# ---------------------------------------------------------------------
def _extract_caller_phone(message: dict, arguments: dict) -> Optional[str]:
    """Checks the usual Vapi locations for the caller's number, then falls
    back to an explicit `phone` tool argument — useful for testing via
    curl or the Vapi dashboard's test console without a live call."""
    customer = message.get("customer") or {}
    if customer.get("number"):
        return customer["number"]

    call = message.get("call") or {}
    call_customer = call.get("customer") or {}
    if call_customer.get("number"):
        return call_customer["number"]

    if arguments.get("phone"):
        return arguments["phone"]

    return None


def _identify_farmer(message: dict, arguments: dict) -> dict:
    raw_phone = _extract_caller_phone(message, arguments)

    # Vapi browser/web calls do not contain telephone caller metadata.
    # In prototype demo mode, use the dedicated demo farmer.
    if not raw_phone:
        demo_mode = (
            os.environ.get("DEMO_MODE", "false")
            .strip()
            .lower()
            == "true"
        )

        if not demo_mode:
            raise HTTPException(
                status_code=400,
                detail="Missing caller phone number.",
            )

        farmer = _resolve_demo_farmer()

        return {
            "farmer": farmer,
            "normalized_phone": None,
            "demo_mode_used": True,
        }

    normalized = normalize_indian_phone(raw_phone)

    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Could not recognize this as an Indian phone number.",
        )

    demo_mode_used = False
    farmer = _find_farmer_by_phone(normalized)

    if farmer is None:
        demo_mode = (
            os.environ.get("DEMO_MODE", "false")
            .strip()
            .lower()
            == "true"
        )

        if not demo_mode:
            raise HTTPException(
                status_code=404,
                detail="No farmer is registered with this number.",
            )

        farmer = _resolve_demo_farmer()
        demo_mode_used = True

    return {
        "farmer": farmer,
        "normalized_phone": normalized,
        "demo_mode_used": demo_mode_used,
    }

# ---------------------------------------------------------------------
# get_token_status — all-status token fetch (not just active).
# Same embedding technique as voice._fetch_active_tokens, but without the
# ACTIVE_STATUSES filter, and with optional narrowing to one token.
# ---------------------------------------------------------------------
def _fetch_all_tokens(
    farmer_id: str,
    token_id: Optional[str] = None,
    token_number: Optional[int] = None,
) -> list[dict]:
    query = (
        supabase.table("tokens")
        .select("*, procurement_centers(name)")
        .eq("farmer_id", farmer_id)
    )
    if token_id:
        query = query.eq("id", token_id)
    if token_number is not None:
        query = query.eq("token_number", token_number)
    query = query.order("created_at", desc=True)

    res = query.execute()
    rows = res.data or []

    results = []
    for row in rows:
        center = row.get("procurement_centers") or {}
        results.append(
            {
                "id": row["id"],
                "center_id": row["center_id"],
                "center_name": center.get("name"),
                "requested_date": row["requested_date"],
                "crop_type": row["crop_type"],
                "quantity_kg": row["quantity_kg"],
                "token_number": row.get("token_number"),
                "time_slot": row.get("time_slot"),
                "status": row["status"],
            }
        )
    return results


# ---------------------------------------------------------------------
# Tool handlers — each returns a plain JSON-serializable dict.
# ---------------------------------------------------------------------
def _handle_get_farmer_context(message: dict, arguments: dict) -> dict:
    ctx = _identify_farmer(message, arguments)
    farmer = ctx["farmer"]
    active_tokens = _fetch_active_tokens(str(farmer["id"]))
    return {
        "demo_mode_used": ctx["demo_mode_used"],
        "caller_number": ctx["normalized_phone"],
        "farmer_name": farmer["name"],
        "active_tokens": [t.model_dump(mode="json") for t in active_tokens],
    }


def _handle_get_token_status(message: dict, arguments: dict) -> dict:
    ctx = _identify_farmer(message, arguments)
    farmer = ctx["farmer"]

    token_id = arguments.get("token_id")
    token_number = arguments.get("token_number")

    tokens = _fetch_all_tokens(str(farmer["id"]), token_id=token_id, token_number=token_number)

    if (token_id or token_number is not None) and not tokens:
        raise HTTPException(status_code=404, detail="No matching token found for this farmer.")

    return {"farmer_name": farmer["name"], "tokens": tokens}


def _handle_list_active_centres(message: dict, arguments: dict) -> dict:
    crop_type = arguments.get("crop_type")
    centres = _list_centers_query(crop_type=crop_type)
    summary = [
        {
            "id": c["id"],
            "name": c["name"],
            "location": c.get("location"),
            "crop_type": c["crop_type"],
            "msp_rate": c["msp_rate"],
        }
        for c in centres
    ]
    return {"centres": summary}


_TOOL_HANDLERS = {
    "get_farmer_context": _handle_get_farmer_context,
    "get_token_status": _handle_get_token_status,
    "list_active_centres": _handle_list_active_centres,
}


# ---------------------------------------------------------------------
# Per-tool-call dispatch — always returns a {"toolCallId", "result"} pair.
# ---------------------------------------------------------------------
def _process_tool_call(message: dict, tool_call: dict) -> dict:
    tool_call_id = tool_call["id"]  # presence already validated by the caller
    function = tool_call.get("function") or {}
    tool_name = function.get("name")
    arguments = function.get("arguments") or {}
    if not isinstance(arguments, dict):
        arguments = {}

    if tool_name not in _TOOL_HANDLERS:
        payload: dict[str, Any] = {"error": f"Unsupported tool: {tool_name!r}"}
        return {"toolCallId": tool_call_id, "result": json.dumps(payload)}

    try:
        payload = _TOOL_HANDLERS[tool_name](message, arguments)
    except HTTPException as exc:
        payload = {"error": exc.detail}
    except Exception:
        # Anything unexpected from Supabase or elsewhere — log the real
        # cause server-side, tell the caller something generic. Never let
        # one bad tool call take down the rest of the batch.
        logger.exception("Unexpected error handling Vapi tool call %r (%s)", tool_call_id, tool_name)
        payload = {"error": "Something went wrong while processing this request."}

    return {"toolCallId": tool_call_id, "result": json.dumps(payload)}


@router.post("/vapi")
async def vapi_webhook(request: Request, authorization: Optional[str] = Header(None)):
    """
    Entry point for Vapi's tool-calls server messages. Read-only: never
    creates, approves, rejects, cancels, or otherwise changes a token.
    """
    _verify_webhook_secret(authorization)

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON payload.")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Malformed payload: expected a JSON object.")

    message = body.get("message")
    if not isinstance(message, dict):
        raise HTTPException(status_code=400, detail="Malformed payload: missing 'message' object.")

    tool_call_list = message.get("toolCallList")
    if not isinstance(tool_call_list, list) or not tool_call_list:
        raise HTTPException(
            status_code=400,
            detail="Malformed payload: missing or empty 'toolCallList'.",
        )

    for tool_call in tool_call_list:
        if not isinstance(tool_call, dict) or not tool_call.get("id"):
            raise HTTPException(
                status_code=400,
                detail="Malformed payload: a tool call is missing 'id'.",
            )

    results = [_process_tool_call(message, tool_call) for tool_call in tool_call_list]
    return {"results": results}