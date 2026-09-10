# Architecture

## System Overview

KisanSaarthi follows a three-tier architecture: a React frontend, a
FastAPI backend, and a Supabase (PostgreSQL) database, with a separate
Vapi-based voice layer for phone access.

[ADD YOUR ARCHITECTURE DIAGRAM IMAGE HERE — e.g. ![architecture](../assets/screenshots/architecture-diagram.png)]

## Components

### Frontend (React + Vite)

- Role-based routing: `/`, `/login`, `/farmer`, `/staff`, `/admin`
- Protected routes enforce role-based access using Supabase session + `profiles` table lookup
- Deployed on Netlify

### Backend (FastAPI)

- REST API handling authentication support, request validation, token
  generation, slot allocation, and business logic
- Enforces capacity checks and active-request limits at the approval step
- Deployed on Railway

### Database (Supabase / PostgreSQL)

- Tables: `profiles`, `procurement_centers`, `tokens`
- Row Level Security (RLS) enabled on all public-facing tables
- Supabase Auth handles farmer/staff/admin login (email + phone)

### Voice Layer (Vapi)

- Handles inbound calls, identifies the farmer by phone number
- Falls back to a demo profile if the caller's number isn't registered
- Communicates with the backend via a dedicated `/voice/context` endpoint

## Request Flow

1. Farmer submits a request (centre, date, crop, quantity) → status `pending`
2. Staff reviews the request against the centre's remaining daily capacity
3. On approval, backend assigns a `token_number` and `time_slot` → status `waiting`
4. Staff calls the token forward → status `called` → `completed`
5. Farmer sees live status updates on their dashboard (auto-refresh) or via a phone call
