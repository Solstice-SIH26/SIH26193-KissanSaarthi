from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import uuid

from postgrest.exceptions import APIError

from models import CenterOut, TokenOut, CenterCreate, CenterUpdate
from db import supabase

router = APIRouter(prefix="/centers", tags=["centers"])


@router.get("", response_model=List[CenterOut])
def list_centers(crop_type: Optional[str] = None):
    """
    Farmer-facing: browse all active centers, with their crop_type, msp_rate,
    and open/close schedule all in one response (no separate /schedule or
    /price endpoint — kept as one call since the fields all live on the same
    row). Optional ?crop_type= filter.
    """
    query = supabase.table("procurement_centers").select("*").eq("is_active", True)
    if crop_type:
        query = query.eq("crop_type", crop_type)
    res = query.execute()
    return res.data


@router.get("/{center_id}", response_model=CenterOut)
def get_center(center_id: uuid.UUID):
    """Single center detail — same shape as list_centers items."""
    res = (
        supabase.table("procurement_centers")
        .select("*")
        .eq("id", str(center_id))
        .single()
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Center not found")
    return res.data


@router.post("", response_model=CenterOut)
def create_center(payload: CenterCreate):
    """
    Admin: create a new procurement center.

    TEMPORARY: no role check yet — anyone who can reach the API can call
    this. Once JWT auth is wired in, this should be restricted to
    role == 'admin' (read from the verified token, not trusted from the
    client). Flag this to whoever finishes the auth integration.
    """
    row = payload.model_dump(mode="json")
    res = supabase.table("procurement_centers").insert(row).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Could not create center")
    return res.data[0]


@router.patch("/{center_id}", response_model=CenterOut)
def update_center(center_id: uuid.UUID, payload: CenterUpdate):
    """
    Admin: update an existing center. Only fields provided in the request
    body are changed — omitted fields are left as-is. This is also how
    you update crop price: PATCH with just {"msp_rate": 2450} — there's
    no separate price-only endpoint, this one already covers it.

    TEMPORARY: same no-role-check caveat as create_center above.
    """
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    res = (
        supabase.table("procurement_centers")
        .update(updates)
        .eq("id", str(center_id))
        .select("*")
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Center not found")
    return res.data[0]


@router.delete("/{center_id}", status_code=204)
def delete_center(center_id: uuid.UUID):
    """
    Admin: permanently delete a center.

    A center with existing tokens or assigned staff (profiles.center_id)
    can't be deleted — the foreign keys block it. That's caught below and
    returned as a clear 400 instead of a raw Postgres error. In most
    cases you want PATCH .../is_active=false (deactivate) instead of a
    real delete, since deleting loses the center's history entirely.
    """
    try:
        res = (
            supabase.table("procurement_centers")
            .delete()
            .eq("id", str(center_id))
            .execute()
        )
    except APIError as e:
        if e.code == "23503":  # foreign key violation
            raise HTTPException(
                status_code=400,
                detail=(
                    "Can't delete a center with existing tokens or assigned staff. "
                    "Use PATCH with {\"is_active\": false} to deactivate it instead."
                ),
            )
        raise HTTPException(status_code=500, detail="Could not delete center")

    if not res.data:
        raise HTTPException(status_code=404, detail="Center not found")
    return None


@router.get("/{center_id}/queue", response_model=List[TokenOut])
def get_queue(center_id: uuid.UUID, status: Optional[str] = Query(None)):
    """
    Staff-facing: a center's requests/tokens, ordered by token_number
    (nulls last — i.e. approved tokens in queue order first, pending
    requests without a number yet trail at the end, tie-broken by
    created_at). Optional ?status=pending|waiting|called|completed|
    rejected|cancelled to filter to one stage, e.g. ?status=pending to see
    the approval queue, or ?status=waiting to see who's up next.
    """
    query = supabase.table("tokens").select("*").eq("center_id", str(center_id))
    if status:
        query = query.eq("status", status)
    query = query.order("token_number", desc=False).order("created_at", desc=False)
    res = query.execute()
    return res.data
