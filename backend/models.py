from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date, datetime
import uuid

TokenStatus = Literal["pending", "waiting", "called", "completed", "rejected", "cancelled"]


class TokenCreate(BaseModel):
    """Farmer submits a procurement request. Goes to 'pending' — does NOT
    get a token_number or time_slot until staff approve it."""
    farmer_id: uuid.UUID
    center_id: uuid.UUID
    requested_date: date
    crop_type: str
    quantity_kg: float


class TokenOut(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    center_id: uuid.UUID
    requested_date: date
    crop_type: str
    quantity_kg: float
    token_number: Optional[int] = None  # NULL until approved
    time_slot: Optional[str] = None     # NULL until approved, "HH:MM" once set
    status: TokenStatus
    created_at: datetime
    updated_at: datetime


class TokenStatusUpdate(BaseModel):
    """Used only by PATCH /tokens/{id}/status — restricted to the
    waiting->called and called->completed steps. Use /approve, /reject,
    or /cancel for every other transition."""
    status: TokenStatus


class CenterOut(BaseModel):
    id: uuid.UUID
    name: str
    location: Optional[str] = None
    crop_type: str
    msp_rate: float
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    daily_capacity_kg: float
    is_active: bool


class CenterCreate(BaseModel):
    name: str
    location: Optional[str] = None
    crop_type: str
    msp_rate: float
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    daily_capacity_kg: float = 5000
    is_active: bool = True


class CenterUpdate(BaseModel):
    # All fields optional — PATCH only updates what's provided.
    name: Optional[str] = None
    location: Optional[str] = None
    crop_type: Optional[str] = None
    msp_rate: Optional[float] = None
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    daily_capacity_kg: Optional[float] = None
    is_active: Optional[bool] = None


Role = Literal["admin", "procurement", "farmer"]


class ProfileOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: Optional[str] = None
    role: Role
    center_id: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime


# =========================================================
# Voice (Vapi) — caller identification + context
# =========================================================

class ActiveTokenContext(BaseModel):
    """One of a farmer's active (pending/waiting/called) requests, with the
    procurement centre's name folded in so the voice assistant can read it
    out without a second lookup."""

    id: uuid.UUID
    center_id: uuid.UUID
    center_name: Optional[str] = None
    requested_date: date
    crop_type: str
    quantity_kg: float
    token_number: Optional[int] = None  # NULL until approved
    time_slot: Optional[str] = None     # NULL until approved
    status: TokenStatus


class VoiceContextOut(BaseModel):
    """Response for GET /voice/context — everything the Vapi assistant
    needs to greet the caller and discuss their existing requests."""

    demo_mode_used: bool
    caller_number: str  # normalized E.164
    farmer_id: uuid.UUID
    farmer_name: str
    active_tokens: list[ActiveTokenContext]

class ProfileUpdate(BaseModel):
    # All fields optional — PATCH only updates what's provided.
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[Role] = None
    center_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None
