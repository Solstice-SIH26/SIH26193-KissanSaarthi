# Architecture

## System Overview

KisanSaarthi follows a three-tier architecture consisting of a React frontend, FastAPI backend, and Supabase PostgreSQL database. A separate Vapi-based voice layer provides phone-based access to farmer services.

## Components

### Frontend — React + Vite

- Role-based interfaces for Farmers, Staff, and Admins
- Protected routes using Supabase authentication and profile-based role verification
- Handles user interaction, request submission, token tracking, and status updates
- Deployed on Netlify

### Backend — FastAPI

- REST API responsible for request handling and business logic
- Handles request validation, token generation, slot allocation, and procurement workflows
- Performs capacity checks and active-request validation before approval
- Provides a dedicated `/voice/context` endpoint for the voice layer
- API documentation available through FastAPI Swagger UI
- Deployed on Railway

### Database — Supabase / PostgreSQL

- Stores user profiles, procurement centers, requests, and token information
- Supabase Auth manages user authentication
- Row Level Security (RLS) protects database access
- Supports role-based access for Farmer, Staff, and Admin users

### Voice Layer — Vapi

- Provides phone-based access for farmers
- Identifies farmers using their registered phone number
- Provides a fallback demo profile for unregistered numbers
- Retrieves farmer and token information through the backend

## Request Flow

1. Farmer submits a procurement request with centre, date, crop, and quantity.
2. Backend validates the request and stores it with `pending` status.
3. Staff reviews the request based on centre capacity and availability.
4. On approval, the backend assigns a `token_number` and `time_slot`.
5. The request moves to `waiting` status.
6. Staff calls the next token, changing its status to `called`.
7. After procurement, the token is marked `completed`.
8. Farmer can view the latest status through the dashboard or access it through the voice system.

## Deployment

```text
React + Vite
     │
     ▼
  Netlify
     │
     ▼
 FastAPI Backend
     │
     ├──────────► Vapi Voice Layer
     │
     ▼
Supabase PostgreSQL
```

- **Frontend:** Netlify
- **Backend:** Railway
- **Database & Authentication:** Supabase
- **Voice Interface:** Vapi
