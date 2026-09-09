"""
Voice (Vapi) integration — Milestone 1: caller identification + context.

This router does NOT create, approve, reject, or change any token. It only
identifies the calling farmer (by phone, or via DEMO_MODE fallback) and
reports their currently active requests, so a Vapi assistant can greet the
caller and talk about what's already in flight.

All token-status vocabulary is imported from routers.tokens (ACTIVE_STATUSES)
rather than redefined here, per the "reuse existing token status
definitions" rule.
"""

import os
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from db import supabase
from models import ActiveTokenContext, VoiceContextOut
from routers.tokens import ACTIVE_STATUSES

router = APIRouter(prefix="/voice", tags=["voice"])

# Matches a 10-digit Indian mobile number, optionally prefixed with the
# country code (with or without a leading "+"). Separators (spaces/hyphens)
# are stripped before this is applied.
_PHONE_RE = re.compile(r"^(?:\+?91)?(\d{10})$")


def normalize_indian_phone(raw: str) -> Optional[str]:
    """
    Normalize a caller-supplied number to E.164 for India.

        9876543210     -> +919876543210
        919876543210   -> +919876543210
        +919876543210  -> +919876543210 (unchanged)

    Returns None if `raw` doesn't match any of these shapes.
    """
    if not raw:
        return None
    cleaned = re.sub(r"[\s\-]", "", raw.strip())
    match = _PHONE_RE.match(cleaned)
    if not match:
        return None
    return "+91" + match.group(1)


def _verify_webhook_secret(authorization: Optional[str]) -> None:
    """Server-to-server auth: Authorization: Bearer <VAPI_WEBHOOK_SECRET>.
    Deliberately not a farmer JWT — this endpoint is called by Vapi, not
    by a farmer's own client."""
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


def _find_farmer_by_phone(normalized_phone: str) -> Optional[dict]:
    """Look up a farmer profile by exact normalized phone match. Returns
    None (not an error) when nothing matches — that's an expected case
    that the caller decides how to handle (demo fallback or 404)."""
    res = (
        supabase.table("profiles")
        .select("*")
        .eq("phone", normalized_phone)
        .eq("role", "farmer")
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def _resolve_demo_farmer() -> dict:
    """Load and validate the configured demo farmer. Raises 500 if
    DEMO_MODE is on but misconfigured — this is a server setup problem,
    not something the caller can fix by trying again."""
    demo_farmer_id = os.environ.get("DEMO_FARMER_ID")
    if not demo_farmer_id:
        raise HTTPException(
            status_code=500,
            detail="DEMO_MODE is enabled but DEMO_FARMER_ID is not configured.",
        )
    try:
        uuid.UUID(demo_farmer_id)
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail="DEMO_FARMER_ID is not a valid UUID.",
        )

    res = (
        supabase.table("profiles")
        .select("*")
        .eq("id", demo_farmer_id)
        .eq("role", "farmer")
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        raise HTTPException(
            status_code=500,
            detail="DEMO_FARMER_ID does not match any farmer profile.",
        )
    return rows[0]


def _fetch_active_tokens(farmer_id: str) -> list[ActiveTokenContext]:
    """Active (pending/waiting/called) tokens for this farmer, each with
    the procurement centre's name embedded via the existing FK
    (tokens.center_id -> procurement_centers.id) — no schema change,
    no second round trip."""
    res = (
        supabase.table("tokens")
        .select("*, procurement_centers(name)")
        .eq("farmer_id", farmer_id)
        .in_("status", ACTIVE_STATUSES)
        .order("requested_date", desc=False)
        .execute()
    )
    rows = res.data or []
    tokens = []
    for row in rows:
        center = row.get("procurement_centers") or {}
        tokens.append(
            ActiveTokenContext(
                id=row["id"],
                center_id=row["center_id"],
                center_name=center.get("name"),
                requested_date=row["requested_date"],
                crop_type=row["crop_type"],
                quantity_kg=row["quantity_kg"],
                token_number=row.get("token_number"),
                time_slot=row.get("time_slot"),
                status=row["status"],
            )
        )
    return tokens


@router.get("/context", response_model=VoiceContextOut)
def get_voice_context(
    phone: str = Query(..., description="Caller's phone number (10-digit, 91-prefixed, or E.164)"),
    authorization: Optional[str] = Header(None),
):
    """
    Identify the calling farmer and return their active-request context.

    Resolution order:
      1. Normalize `phone` to E.164. 400 if it doesn't match a recognizable
         Indian phone number shape.
      2. Look up profiles.phone for a farmer with that number.
      3. If found -> use that farmer (demo_mode_used = False).
      4. If not found and DEMO_MODE=true -> use DEMO_FARMER_ID
         (demo_mode_used = True). Same permissions/limits as any farmer;
         no special-casing beyond identification.
      5. If not found and DEMO_MODE=false -> 404.
    """
    _verify_webhook_secret(authorization)

    normalized = normalize_indian_phone(phone)
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Could not recognize this as an Indian phone number.",
        )

    demo_mode_used = False
    farmer = _find_farmer_by_phone(normalized)

    if farmer is None:
        demo_mode = os.environ.get("DEMO_MODE", "false").strip().lower() == "true"
        if not demo_mode:
            raise HTTPException(
                status_code=404,
                detail="No farmer is registered with this number.",
            )
        farmer = _resolve_demo_farmer()
        demo_mode_used = True

    active_tokens = _fetch_active_tokens(str(farmer["id"]))

    return VoiceContextOut(
        demo_mode_used=demo_mode_used,
        caller_number=normalized,
        farmer_id=farmer["id"],
        farmer_name=farmer["name"],
        active_tokens=active_tokens,
    )