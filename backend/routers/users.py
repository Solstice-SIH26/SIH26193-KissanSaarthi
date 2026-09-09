from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import uuid

from postgrest.exceptions import APIError
from supabase_auth.errors import AuthApiError

from models import ProfileOut, ProfileUpdate, Role
from db import supabase

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[ProfileOut])
def list_users(role: Optional[Role] = Query(None)):
    """
    Admin: list profiles, optionally filtered by role
    (?role=admin|procurement|farmer).

    TEMPORARY: no auth check yet — same caveat as the center admin
    endpoints. This reads the `profiles` table, not Supabase's internal
    `auth.users` — it only returns the app-specific fields (name, phone,
    role, center_id, is_active), not login/identity data.
    """
    query = supabase.table("profiles").select("*")
    if role:
        query = query.eq("role", role)
    res = query.execute()
    return res.data


@router.patch("/{user_id}", response_model=ProfileOut)
def update_user(user_id: uuid.UUID, payload: ProfileUpdate):
    """
    Admin: edit a profile, or deactivate one with {"is_active": false}.

    Deactivating (rather than deleting) keeps the person's auth login and
    their token history intact — they just can't be treated as an active
    farmer/staff member anymore. Use DELETE below only when you actually
    want to remove their account entirely.

    TEMPORARY: no role check yet — same caveat as the other admin endpoints.
    """
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    try:
        res = (
            supabase.table("profiles")
            .update(updates)
            .eq("id", str(user_id))
            .select("*")
            .execute()
        )
    except APIError as e:
        if e.code == "23503":  # foreign key violation, e.g. bad center_id
            raise HTTPException(status_code=400, detail="center_id does not exist")
        raise HTTPException(status_code=500, detail="Could not update user")

    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")
    return res.data[0]


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: uuid.UUID):
    """
    Admin: permanently delete a user's account.

    This does NOT just delete the profiles row — it deletes the underlying
    Supabase Auth user via the Admin API. profiles.id has an
    `on delete cascade` foreign key to auth.users, so removing the auth
    user automatically removes their profile too. Deleting only the
    profiles row directly would leave a broken half-state: a working
    login with no role/data attached to it.

    A farmer/staff member with existing tokens can still be deleted (their
    tokens aren't tied to auth.users, only to profiles, and profiles rows
    disappear via cascade) — their historical tokens will remain in the
    tokens table but now reference a farmer_id that no longer has a
    profile. Prefer PATCH .../is_active=false if you want to preserve a
    clean, queryable history instead.
    """
    try:
        supabase.auth.admin.delete_user(str(user_id))
    except AuthApiError as e:
        if e.status == 404 or "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="User not found")
        raise HTTPException(status_code=500, detail=f"Could not delete user: {e}")
    return None
