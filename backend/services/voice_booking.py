"""
Voice (Vapi) integration -- Milestone 5: confirmed token booking.

create_voice_token_request() is the single entry point the webhook uses
for the `create_token_request` tool. It performs every check that is
specific to *voice* input -- a centre that actually exists, is active,
and grows the crop the farmer named out loud; a real, parseable, future,
in-window date; a positive quantity; and an explicit confirmation -- and
then hands off to the existing routers.tokens.create_token() for the two
rules that are already enforced there (one active request per day, max
three active requests per farmer) plus the actual insert.

Nothing here re-implements those two rules. Duplicating them would risk
the voice path and the web path silently drifting apart over time.

Error handling: every failure raises fastapi.HTTPException, exactly like
routers/tokens.py and routers/voice.py already do. routers/webhooks.py's
existing _process_tool_call() already knows how to catch an HTTPException
from a tool handler and embed it as {"error": "..."} in that tool call's
result -- reusing that machinery rather than inventing a second error
convention here.

Concurrency / idempotency note (documented rather than "solved" -- see
API_CONTRACT.md): a Vapi tool call can in principle be retried with the
same toolCallId. This module does not add a schema migration to make
that retry idempotent -- there is no idempotency-key column, and adding
one is a bigger change than this milestone calls for. In practice, a
retried booking for the *same* requested_date will already be turned
away by the same-day-active-request rule in create_token(), so the
realistic exposure is a repeated attempt getting a friendly "you already
have an active request for that date" message rather than a duplicate
row. Two different farmers hitting the max-3 boundary at the exact same
instant is the same race that already exists on the web form today --
Milestone 5 does not change that.
"""

import uuid
from datetime import date, datetime
from typing import Any, Optional

from fastapi import HTTPException

from db import supabase
from models import TokenCreate
from routers.tokens import create_token

DATE_FORMAT = "%Y-%m-%d"


# ---------------------------------------------------------------------
# Small lookups / parsers -- each raises HTTPException with a short,
# voice-friendly message on failure.
# ---------------------------------------------------------------------
def _find_center(center_id: str) -> Optional[dict]:
    res = (
        supabase.table("procurement_centers")
        .select("*")
        .eq("id", center_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def _parse_quantity(raw: Any) -> float:
    try:
        quantity = float(raw)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Quantity must be a number, in kilograms.",
        )
    if quantity <= 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity must be greater than 0 kg.",
        )
    return quantity


def _parse_requested_date(raw: Any, center: dict) -> date:
    if not raw or not isinstance(raw, str):
        raise HTTPException(
            status_code=400,
            detail="A requested date is required, in YYYY-MM-DD format.",
        )
    try:
        parsed = datetime.strptime(raw.strip(), DATE_FORMAT).date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Requested date must be in YYYY-MM-DD format.",
        )

    if parsed < date.today():
        raise HTTPException(
            status_code=400,
            detail="Requested date cannot be in the past.",
        )

    open_date = center.get("open_date")
    close_date = center.get("close_date")
    if open_date and parsed < datetime.strptime(open_date, DATE_FORMAT).date():
        raise HTTPException(
            status_code=400,
            detail=(
                f"{center.get('name', 'This centre')} only accepts requests "
                f"from {open_date} to {close_date}."
            ),
        )
    if close_date and parsed > datetime.strptime(close_date, DATE_FORMAT).date():
        raise HTTPException(
            status_code=400,
            detail=(
                f"{center.get('name', 'This centre')} only accepts requests "
                f"from {open_date} to {close_date}."
            ),
        )
    return parsed


# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------
def create_voice_token_request(farmer_id: str, arguments: dict) -> dict:
    """
    Validates a voice-sourced booking request and, once every check
    passes and `confirmed` is true, creates it through the existing
    routers.tokens.create_token() -- the same function POST /tokens uses.

    `arguments` is the Vapi tool call's `function.arguments` dict, with
    keys: center_id, crop_type, quantity_kg, requested_date, confirmed.
    """
    if arguments.get("confirmed") is not True:
        raise HTTPException(
            status_code=400,
            detail="Please confirm the request details out loud before I can book it.",
        )

    raw_center_id = arguments.get("center_id")
    if not raw_center_id:
        raise HTTPException(
            status_code=400,
            detail="Which procurement centre is this request for?",
        )
    try:
        center_uuid = uuid.UUID(str(raw_center_id))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="That doesn't look like a valid procurement centre.",
        )

    center = _find_center(str(center_uuid))
    if center is None:
        raise HTTPException(
            status_code=404,
            detail="I couldn't find that procurement centre.",
        )
    if not center.get("is_active"):
        raise HTTPException(
            status_code=400,
            detail=f"{center.get('name', 'That centre')} is not currently accepting requests.",
        )

    raw_crop = arguments.get("crop_type")
    if not raw_crop or not str(raw_crop).strip():
        raise HTTPException(
            status_code=400,
            detail="Which crop is this request for?",
        )
    center_crop = center.get("crop_type", "")
    if str(raw_crop).strip().lower() != center_crop.strip().lower():
        raise HTTPException(
            status_code=400,
            detail=f"{center.get('name', 'This centre')} only accepts {center_crop}, not {raw_crop}.",
        )

    quantity = _parse_quantity(arguments.get("quantity_kg"))
    requested_date = _parse_requested_date(arguments.get("requested_date"), center)

    payload = TokenCreate(
        farmer_id=uuid.UUID(str(farmer_id)),
        center_id=center_uuid,
        requested_date=requested_date,
        crop_type=center_crop,  # store the centre's canonical crop name
        quantity_kg=quantity,
    )

    # Reuses the existing same-day / max-3-active / insert logic verbatim.
    # Raises HTTPException (400/500) on any of those existing rules.
    token = create_token(payload)

    return {
        "success": True,
        "message": (
            f"Aapka {center_crop} ka request {requested_date.isoformat()} ke liye "
            f"{center.get('name')} mein book ho gaya hai. Status: pending -- "
            "staff isko jald hi review karenge."
        ),
        "center_name": center.get("name"),
        "crop_type": center_crop,
        "quantity_kg": quantity,
        "requested_date": requested_date.isoformat(),
        "status": token["status"],
    }