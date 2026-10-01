# Frontend Guide — SIH PS26193

## 1. Overview

The frontend is a React + Vite application for the Farmer Procurement Management Platform.

### Current status

- **Farmer UI:** Implemented and integrated with the current backend API.
- **Staff UI:** Next major frontend task; staff queue management and "call next" flow are still to be implemented.

---

## 2. Current Pages

### Farmer Dashboard

**File:** `src/pages/farmer/FarmerDashboard.jsx`

The farmer dashboard currently allows farmers to:

- View available procurement centers
- Select a procurement center
- Request a procurement token
- View their token number and status
- Refresh their token status
- View procurement center schedule/details
- View crop MSP prices
- Handle loading, error, and empty states

### Staff Dashboard

**Status:** Not implemented yet.

Planned functionality:

- View the token queue for a procurement center
- View/filter waiting tokens
- Implement the "Call Next" workflow
- Update token status

---

## 3. Backend API Mapping

### `src/services/api.js`

Centralized HTTP wrapper used by the frontend service modules.

- Uses native `fetch`
- Reads the API base URL from `VITE_API_BASE_URL`
- Falls back to `http://localhost:8000`
- Handles non-2xx responses using `ApiError`
- Parses JSON responses

---

### `src/services/tokenService.js`

Handles procurement token operations.

| Function              | Method | Endpoint              | Purpose                              |
| --------------------- | ------ | --------------------- | ------------------------------------ |
| `requestToken()`      | POST   | `/tokens`             | Create a new procurement token       |
| `getToken()`          | GET    | `/tokens/{id}`        | Get the current token details/status |
| `updateTokenStatus()` | PATCH  | `/tokens/{id}/status` | Update a token's status              |

**Currently used by:** Farmer Dashboard for token creation and status refresh.

---

### `src/services/scheduleService.js`

Handles procurement center and queue-related API calls.

| Function               | Method | Endpoint                 | Purpose                            |
| ---------------------- | ------ | ------------------------ | ---------------------------------- |
| `getCenters()`         | GET    | `/centers`               | Get all active procurement centers |
| `getCenters(cropType)` | GET    | `/centers?crop_type=...` | Get centers filtered by crop type  |
| `getCenter()`          | GET    | `/centers/{id}`          | Get details of a specific center   |
| `getCenterQueue()`     | GET    | `/centers/{id}/queue`    | Get the token queue for a center   |

`getCenterQueue()` can also pass a status filter:

`GET /centers/{id}/queue?status=waiting`

**Currently used by:** Farmer Dashboard uses `getCenters()`.  
**Planned use:** Staff Dashboard will use `getCenterQueue()`.

---

### `src/services/priceService.js`

There is currently no dedicated `/prices` endpoint in the backend.

`getCropPrices()` calls:

`GET /centers`

and extracts:

- `crop_type`
- `msp_rate`

from the returned center objects.

The service de-duplicates crops so the farmer UI can display one MSP entry per crop.

**Currently used by:** Farmer Dashboard.

---

## 4. Temporary / Stubbed Items

### Hardcoded Farmer ID

Authentication/identity integration with the backend is not complete yet.

The Farmer Dashboard currently uses:

`DEMO_FARMER_ID`

This is a temporary hardcoded UUID used when calling:

`POST /tokens`

The hardcoded ID must be replaced with the authenticated farmer's actual ID once the authentication/profile flow is finalized.

---

### Login Role Stub

**File:** `src/LoginPage.jsx`

The login page currently contains:

```js
const fakeRole = "farmer";
```

The intended role-based flow is:

- `/farmer` → Farmer Dashboard
- `/staff` → Staff Dashboard
- `/admin` → Admin Dashboard

Role-based routing is not wired yet.

---

## 5. Route Structure

### Current

The frontend does not currently have React Router configured.

`src/App.jsx` currently renders:

```jsx
<LoginPage />
```

So there are **no active `/farmer`, `/staff`, or `/admin` routes yet**.

### Planned

The agreed role-based structure is:

| Role   | Route     | Page             |
| ------ | --------- | ---------------- |
| Farmer | `/farmer` | Farmer Dashboard |
| Staff  | `/staff`  | Staff Dashboard  |
| Admin  | `/admin`  | Admin Dashboard  |

Once authentication/profile integration is completed, the login flow should determine the user's role and redirect to the appropriate route.

---

## 6. Authentication Status

Authentication is partially present through Supabase.

**File:** `src/LoginPage.jsx`

Currently:

- Supabase email/password login is implemented.
- The authenticated user's session can be obtained.
- Role lookup from the `profiles` table is not wired yet.
- Role-based routing is not implemented yet.
- Backend authentication is not implemented yet.

Therefore, the farmer ID used by the Farmer Dashboard is still temporarily hardcoded.

---

## 7. Staff UI — Next Work

The next major frontend task is the Staff Dashboard.

The backend already supports the required queue operations:

1. `GET /centers/{id}/queue?status=waiting`
2. Take the first waiting token from the returned array.
3. `PATCH /tokens/{id}/status` with:

```json
{
  "status": "called"
}
```

This is the current "Call Next" flow.

There is **no dedicated `/call-next` backend endpoint**.

The Staff UI should eventually provide:

- Center selection
- Queue display
- Waiting-token view
- Call Next button
- Token status updates
- Appropriate loading, error, and empty states

---

## 8. Important Backend Notes

The frontend should follow the current backend contract in:

`backend/API_CONTRACT.md`

Important points:

- Backend base URL during development: `http://localhost:8000`
- No backend authentication yet
- Valid token statuses are:
  - `waiting`
  - `called`
  - `completed`
  - `cancelled`
- `GET /centers` returns only active centers.
- `/centers` can return an empty array (`[]`) when no centers match.
- There is no dedicated `/prices` endpoint.
- MSP data comes from the center objects.
- There is no dedicated `/call-next` endpoint.

---

## 9. Frontend Structure

Current relevant structure:

```text
frontend/
└── src/
    ├── pages/
    │   └── farmer/
    │       ├── FarmerDashboard.jsx
    │       └── FarmerDashboard.css
    │
    ├── services/
    │   ├── api.js
    │   ├── tokenService.js
    │   ├── scheduleService.js
    │   ├── priceService.js
    │   └── README.md
    │
    ├── App.jsx
    ├── LoginPage.jsx
    ├── main.jsx
    └── supabaseClient.js
```

---

## 10. Quick Reference

| Area                   | Current State             |
| ---------------------- | ------------------------- |
| Farmer Dashboard       | Implemented               |
| Farmer API integration | Implemented               |
| Staff Dashboard        | Not implemented           |
| Call Next UI           | Not implemented           |
| Admin UI               | Not implemented           |
| Supabase login         | Implemented               |
| Role-based routing     | Not implemented           |
| Backend authentication | Not implemented           |
| Farmer ID              | Temporary hardcoded UUID  |
| API wrapper            | Implemented               |
| API contract           | `backend/API_CONTRACT.md` |

---

**Last updated:** August 2026
