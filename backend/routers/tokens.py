from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, time, timedelta
import uuid

from postgrest.exceptions import APIError

from models import TokenCreate, TokenOut, TokenStatusUpdate
from db import supabase

router = APIRouter(prefix="/tokens", tags=["tokens"])

# Statuses that count as "active" for the one-request-per-day and
# max-3-active-tokens checks below. Deliberately excludes completed,
# rejected, and cancelled — those free up both the farmer's slot and the
# center's capacity automatically, just by being excluded from these sums.
ACTIVE_STATUSES = ("pending", "waiting", "called")

# Statuses that count toward a center's daily capacity — only requests
# that have actually been approved (or moved further along), not ones
# still sitting in 'pending'.
APPROVED_STATUSES = ("waiting", "called", "completed")

MAX_ACTIVE_TOKENS_PER_FARMER = 3

# Time-slot assignment: simple fixed-interval spacing in approval order.
# Not a real scheduling algorithm — good enough for a demo.
SLOT_START = time(9, 0)
SLOT_INTERVAL_MINUTES = 25


def _format_slot(slot_index: int) -> str:
    """slot_index is 0-based position in today's approval order for this center+date."""
    dummy_date = datetime(2000, 1, 1, SLOT_START.hour, SLOT_START.minute)
    slot_time = dummy_date + timedelta(minutes=SLOT_INTERVAL_MINUTES * slot_index)
    return slot_time.strftime("%H:%M")


@router.post("", response_model=TokenOut)
def create_token(payload: TokenCreate):
    """
    Farmer submits a procurement request. Goes to 'pending' — NOT directly
    into the queue. Staff approve or reject it; only approval assigns a
    token_number and time_slot (see /approve below).

    Enforces two farmer-side limits before the request is even created:
    - one active request per requested_date (any center)
    - max 3 active (pending/waiting/called) requests total
    """
    farmer_id = str(payload.farmer_id)
    center_id = str(payload.center_id)
    requested_date = payload.requested_date.isoformat()

    # Rule: one request per day, across any center
    same_day = (
        supabase.table("tokens")
        .select("id")
        .eq("farmer_id", farmer_id)
        .eq("requested_date", requested_date)
        .in_("status", ACTIVE_STATUSES)
        .execute()
    )
    if same_day.data:
        raise HTTPException(
            status_code=400,
            detail=f"You already have an active request for {requested_date}.",
        )

    # Rule: max 3 active tokens per farmer, across all dates
    active_count = (
        supabase.table("tokens")
        .select("id", count="exact")
        .eq("farmer_id", farmer_id)
        .in_("status", ACTIVE_STATUSES)
        .execute()
    )
    if (active_count.count or 0) >= MAX_ACTIVE_TOKENS_PER_FARMER:
        raise HTTPException(
            status_code=400,
            detail=f"You already have {MAX_ACTIVE_TOKENS_PER_FARMER} active requests. "
            "Cancel one before submitting a new request.",
        )

    row = {
        "farmer_id": farmer_id,
        "center_id": center_id,
        "requested_date": requested_date,
        "crop_type": payload.crop_type,
        "quantity_kg": payload.quantity_kg,
        "status": "pending",
        # token_number and time_slot are left unset -> NULL until approved
    }
    try:
        res = supabase.table("tokens").insert(row).execute()
    except APIError as e:
        if e.code == "23503":  # foreign key violation
            raise HTTPException(
                status_code=400,
                detail="farmer_id or center_id does not exist",
            )
        raise HTTPException(status_code=500, detail="Could not create request")

    if not res.data:
        raise HTTPException(status_code=500, detail="Could not create request")
    return res.data[0]


@router.get("/{token_id}", response_model=TokenOut)
def get_token(token_id: uuid.UUID):
    """Farmer checks the current status of their request/token."""
    res = supabase.table("tokens").select("*").eq("id", str(token_id)).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Token not found")
    return res.data


@router.patch("/{token_id}/approve", response_model=TokenOut)
def approve_token(token_id: uuid.UUID):
    """
    Staff approves a pending request.

    - Only works on tokens currently in 'pending' status.
    - Capacity check: sums quantity_kg of already-approved tokens
      (status in waiting/called/completed) for this center+requested_date.
      If adding this request would exceed the center's daily_capacity_kg,
      the approval is rejected with a 400 and nothing changes.
    - On success: assigns a sequential token_number and a time_slot
      (fixed-interval spacing in approval order), and moves status to
      'waiting'.
    """
    token_res = supabase.table("tokens").select("*").eq("id", str(token_id)).single().execute()
    if not token_res.data:
        raise HTTPException(status_code=404, detail="Token not found")
    token = token_res.data

    if token["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending requests can be approved (current status: {token['status']}).",
        )

    center_res = (
        supabase.table("procurement_centers")
        .select("daily_capacity_kg")
        .eq("id", token["center_id"])
        .single()
        .execute()
    )
    if not center_res.data:
        raise HTTPException(status_code=404, detail="Center not found")
    daily_capacity_kg = float(center_res.data["daily_capacity_kg"])

    # Sum quantity_kg already approved for this center+date
    approved_res = (
        supabase.table("tokens")
        .select("quantity_kg")
        .eq("center_id", token["center_id"])
        .eq("requested_date", token["requested_date"])
        .in_("status", APPROVED_STATUSES)
        .execute()
    )
    approved_rows = approved_res.data or []
    already_approved_kg = sum(float(r["quantity_kg"]) for r in approved_rows)
    this_request_kg = float(token["quantity_kg"])

    if already_approved_kg + this_request_kg > daily_capacity_kg:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Approving this request ({this_request_kg}kg) would exceed the center's "
                f"daily capacity ({already_approved_kg}kg already approved / "
                f"{daily_capacity_kg}kg limit for {token['requested_date']})."
            ),
        )

    # token_number and time_slot: sequential in approval order for this
    # center+date. already_approved count (before this one) determines
    # both the next number and the next slot index.
    token_number = len(approved_rows) + 1
    time_slot = _format_slot(len(approved_rows))

    update_res = (
        supabase.table("tokens")
        .update({
            "status": "waiting",
            "token_number": token_number,
            "time_slot": time_slot,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", str(token_id))
        .select("*")
        .execute()
    )
    if not update_res.data:
        raise HTTPException(status_code=500, detail="Could not approve request")
    return update_res.data[0]


@router.patch("/{token_id}/reject", response_model=TokenOut)
def reject_token(token_id: uuid.UUID):
    """Staff rejects a pending request. Only works from 'pending'."""
    token_res = supabase.table("tokens").select("status").eq("id", str(token_id)).single().execute()
    if not token_res.data:
        raise HTTPException(status_code=404, detail="Token not found")
    if token_res.data["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Only pending requests can be rejected (current status: {token_res.data['status']}).",
        )

    res = (
        supabase.table("tokens")
        .update({"status": "rejected", "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(token_id))
        .select("*")
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=500, detail="Could not reject request")
    return res.data[0]


@router.patch("/{token_id}/cancel", response_model=TokenOut)
def cancel_token(token_id: uuid.UUID):
    """
    Farmer or staff cancels a request. Only works from 'pending' or
    'waiting' — once called/completed it's too late to cancel.
    Freeing up capacity/the farmer's day-slot needs no extra code: both
    checks exclude 'cancelled' automatically.
    """
    token_res = supabase.table("tokens").select("status").eq("id", str(token_id)).single().execute()
    if not token_res.data:
        raise HTTPException(status_code=404, detail="Token not found")
    if token_res.data["status"] not in ("pending", "waiting"):
        raise HTTPException(
            status_code=400,
            detail=f"Only pending or waiting requests can be cancelled (current status: {token_res.data['status']}).",
        )

    res = (
        supabase.table("tokens")
        .update({"status": "cancelled", "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(token_id))
        .select("*")
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=500, detail="Could not cancel request")
    return res.data[0]


@router.patch("/{token_id}/status", response_model=TokenOut)
def update_token_status(token_id: uuid.UUID, payload: TokenStatusUpdate):
    """
    Staff progresses an already-approved token through the physical
    queue: waiting -> called -> completed. This endpoint deliberately does
    NOT accept any other transition — use /approve, /reject, or /cancel
    for pending/rejected/cancelled changes. This is a behavior change from
    the previous version of this endpoint, which allowed any status.
    """
    token_res = supabase.table("tokens").select("status").eq("id", str(token_id)).single().execute()
    if not token_res.data:
        raise HTTPException(status_code=404, detail="Token not found")
    current = token_res.data["status"]
    target = payload.status

    allowed = {"waiting": "called", "called": "completed"}
    if allowed.get(current) != target:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot move token from '{current}' to '{target}' via this endpoint. "
                "Use /approve, /reject, or /cancel for other transitions."
            ),
        )

    res = (
        supabase.table("tokens")
        .update({"status": target, "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(token_id))
        .select("*")
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Token not found")
    return res.data[0]
