-- SIH PS26032 — Procurement Center System
-- Schema for Supabase (Postgres)
-- Run this in the Supabase SQL editor, or via `supabase db push` if using migrations.
--
-- v3: farmer requests now go to PENDING first; staff approve/reject; only
-- approval assigns token_number + time_slot. See routers/tokens.py for the
-- business logic (capacity check, per-farmer limits, slot assignment).

create extension if not exists "pgcrypto"; -- for gen_random_uuid()

-- =========================================================
-- PROCUREMENT CENTERS
-- One row per physical procurement center.
-- =========================================================
create table if not exists procurement_centers (
    id                uuid primary key default gen_random_uuid(),
    name              text not null,
    location          text,
    crop_type         text not null,          -- e.g. 'Wheat', 'Paddy'
    msp_rate          numeric(10,2) not null, -- MSP price per quintal (or whatever unit you standardize on)
    open_date         date,                   -- next/current procurement window start
    close_date        date,                   -- procurement window end
    daily_capacity_kg numeric(10,2) not null default 5000, -- max kg this center can process per day
    is_active         boolean not null default true,
    created_at        timestamptz not null default now()
);

-- =========================================================
-- PROFILES
-- Supabase Auth owns login/identity (auth.users). This table only adds
-- app-specific fields (role, phone, center assignment) on top of the
-- user Supabase already knows about. id is NOT auto-generated here —
-- it must equal the corresponding auth.users(id), typically inserted
-- right after a user signs up (e.g. via a Supabase trigger or from the
-- signup handler on the frontend/auth side).
-- =========================================================
create table if not exists profiles (
    id          uuid primary key references auth.users(id) on delete cascade,
    name        text not null,
    phone       text unique,
    role        text not null check (role in ('admin', 'procurement', 'farmer')),
    center_id   uuid references procurement_centers(id), -- set only when role = 'procurement'
    is_active   boolean not null default true, -- admin can deactivate without deleting the auth login
    created_at  timestamptz not null default now()
);

-- =========================================================
-- TOKENS
-- One row per farmer's procurement request/token.
--
-- Flow: pending -> waiting (=approved) -> called -> completed
--                \-> rejected (staff declines a pending request)
--       pending or waiting -> cancelled (farmer/staff cancels)
--
-- token_number and time_slot are NULL until a staff member approves the
-- request — they're assigned at approval time, not at creation.
-- =========================================================
create table if not exists tokens (
    id             uuid primary key default gen_random_uuid(),
    farmer_id      uuid not null references profiles(id),
    center_id      uuid not null references procurement_centers(id),
    requested_date date not null,               -- date the farmer wants to bring their crop
    crop_type      text not null,
    quantity_kg    numeric(10,2) not null,
    token_number   int,                          -- NULL until approved
    time_slot      text,                         -- NULL until approved; stored as "HH:MM"
    status         text not null default 'pending'
                   check (status in ('pending', 'waiting', 'called', 'completed', 'rejected', 'cancelled')),
    created_at     timestamptz not null default now(),
    updated_at     timestamptz not null default now()
);

create index if not exists idx_tokens_center_created on tokens (center_id, created_at);
create index if not exists idx_tokens_center_status on tokens (center_id, status);
create index if not exists idx_tokens_center_date_status on tokens (center_id, requested_date, status);
create index if not exists idx_tokens_farmer_status on tokens (farmer_id, status);
create index if not exists idx_tokens_farmer_date on tokens (farmer_id, requested_date);
