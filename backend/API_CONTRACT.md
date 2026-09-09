# API Contract — SIH PS26032 Backend (v3: pending/approve workflow)

Base URL during dev: `http://localhost:8000`

## Auth

**None implemented yet.** No headers, tokens, or cookies required on any
endpoint below — including admin ones. IDs are passed directly by the
client. JWT verification (Supabase Auth) is planned once login is working
on the auth side.

The one exception is the new voice endpoint in section 5, which is called
server-to-server by Vapi and is protected by a static bearer secret
(`VAPI_WEBHOOK_SECRET`) rather than a farmer JWT.

---

## 1. Token statuses (exact enum)

| Value | Meaning | Set by |
|---|---|---|
| `pending` | Farmer submitted a request, awaiting staff review | `POST /tokens` (default) |
| `waiting` | Staff approved it — has a `token_number` and `time_slot` now | `PATCH /tokens/{id}/approve` |
| `called` | Staff has called this token up | `PATCH /tokens/{id}/status` |
| `completed` | Transaction done | `PATCH /tokens/{id}/status` |
| `rejected` | Staff declined the pending request | `PATCH /tokens/{id}/reject` |
| `cancelled` | Farmer or staff cancelled (only from `pending`/`waiting`) | `PATCH /tokens/{id}/cancel` |

Flow: `pending → waiting → called → completed`, with `pending → rejected`
and `pending`/`waiting` → `cancelled` as off-ramps.

---

## 2. Endpoints

### `POST /tokens`
Farmer submits a procurement request. **Does not join the queue directly** — goes to `pending` for staff review.

**Request body** (all required):
```json
{
  "farmer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "center_id": "9c858901-8a57-4791-81fe-4c455b099bc9",
  "requested_date": "2026-09-10",
  "crop_type": "Wheat",
  "quantity_kg": 500
}
```
| Field | Type | Required |
|---|---|---|
| `farmer_id` | UUID string | yes |
| `center_id` | UUID string | yes |
| `requested_date` | date string `YYYY-MM-DD` | yes |
| `crop_type` | string | yes |
| `quantity_kg` | number | yes |

**Success response — `200 OK`:**
```json
{
  "id": "a1b2c3d4-...",
  "farmer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "center_id": "9c858901-8a57-4791-81fe-4c455b099bc9",
  "requested_date": "2026-09-10",
  "crop_type": "Wheat",
  "quantity_kg": 500,
  "token_number": null,
  "time_slot": null,
  "status": "pending",
  "created_at": "2026-08-28T09:15:00.123456+00:00",
  "updated_at": "2026-08-28T09:15:00.123456+00:00"
}
```
`token_number` and `time_slot` are **`null`** until approved — the frontend should handle this, not assume they're always populated.

**Error responses:**
- `400 Bad Request` — one of:
  - `{"detail": "farmer_id or center_id does not exist"}` (bad foreign key)
  - `{"detail": "You already have an active request for 2026-09-10."}` (one-per-day rule)
  - `{"detail": "You already have 3 active requests. Cancel one before submitting a new request."}` (max-3-active rule)
- `422 Unprocessable Entity` — missing/invalid field or wrong type
- `500 Internal Server Error` — `{"detail": "Could not create request"}`

---

### `GET /tokens/{id}`
Farmer checks their request/token status. Same response shape as `POST /tokens` above, reflecting current state (`token_number`/`time_slot` populated once approved).

**Errors:** `404` `{"detail": "Token not found"}`; `422` bad UUID.

---

### `PATCH /tokens/{id}/approve`
Staff approves a pending request. **No request body.**

**Success response — `200 OK`:** full token object with `status: "waiting"`, `token_number` and `time_slot` now populated, e.g.:
```json
{ "...": "...", "status": "waiting", "token_number": 3, "time_slot": "09:50" }
```

**Error responses:**
- `404 Not Found` — `{"detail": "Token not found"}`
- `400 Bad Request`:
  - `{"detail": "Only pending requests can be approved (current status: waiting)."}` — wrong current state
  - `{"detail": "Approving this request (500.0kg) would exceed the center's daily capacity (4800.0kg already approved / 5000.0kg limit for 2026-09-10)."}` — capacity exceeded

---

### `PATCH /tokens/{id}/reject`
Staff rejects a pending request. **No request body.**

**Success — `200 OK`:** token object with `status: "rejected"`.
**Errors:** `404` not found; `400` `{"detail": "Only pending requests can be rejected (current status: ...)."}`

---

### `PATCH /tokens/{id}/cancel`
Farmer or staff cancels. Works from `pending` or `waiting` only. **No request body.**

**Success — `200 OK`:** token object with `status: "cancelled"`.
**Errors:** `404` not found; `400` `{"detail": "Only pending or waiting requests can be cancelled (current status: ...)."}`

---

### `PATCH /tokens/{id}/status`
Staff progresses an **already-approved** token through the physical queue. **Only two transitions are accepted: `waiting→called` and `called→completed`.** Everything else (approve/reject/cancel) must use the dedicated endpoints above.

**Request body:**
```json
{ "status": "called" }
```

**Success — `200 OK`:** updated token object.
**Errors:**
- `404` not found
- `400` `{"detail": "Cannot move token from 'pending' to 'called' via this endpoint. Use /approve, /reject, or /cancel for other transitions."}`

---

### `GET /centers`
Unchanged behavior. Optional `?crop_type=` filter. Response now includes `daily_capacity_kg`:
```json
[
  {
    "id": "9c858901-...",
    "name": "Karnal Mandi Center 3",
    "location": "Karnal, Haryana",
    "crop_type": "Wheat",
    "msp_rate": 2425.00,
    "open_date": "2026-09-01",
    "close_date": "2026-09-15",
    "daily_capacity_kg": 5000,
    "is_active": true
  }
]
```

### `GET /centers/{id}`
Same shape as one item above. `404` if not found.

### `POST /centers` / `PATCH /centers/{id}`
Admin center management — body accepts/returns `daily_capacity_kg` (defaults to `5000` if omitted on create). `PATCH` handles crop-price updates too — send just `{"msp_rate": 2450}`, no separate price endpoint exists.

### `DELETE /centers/{id}`
Admin: permanently delete a center. **No request body.**

**Success — `204 No Content`.**

**Errors:**
- `404 Not Found` — `{"detail": "Center not found"}`
- `400 Bad Request` — `{"detail": "Can't delete a center with existing tokens or assigned staff. Use PATCH with {\"is_active\": false} to deactivate it instead."}`

### `GET /centers/{id}/queue`
Unchanged URL. `?status=` now accepts any of the 6 statuses — e.g. `?status=pending` to see the approval queue, `?status=waiting` to see who's up next. Ordered by `token_number` (approved tokens first, in order), then `created_at` (pending requests, oldest first).

### `GET /users`
Unchanged. `?role=admin|procurement|farmer` optional filter. Response now includes `is_active`.

### `PATCH /users/{id}`
Admin: edit a profile, or deactivate one. **This is how you "remove" a user without breaking their token history** — set `{"is_active": false}` instead of deleting.

**Request body (all optional):**
```json
{ "is_active": false }
```

**Success — `200 OK`:** updated profile.
**Errors:** `400` empty body, or bad `center_id`; `404` not found.

### `DELETE /users/{id}`
Admin: **permanently deletes the person's Supabase Auth account** (not just the profile row) — this removes their ability to log in entirely. Their profile is removed automatically via cascade; any of their existing tokens remain in the database but will reference a `farmer_id` with no profile attached. **No request body.**

**Success — `204 No Content`.**
**Errors:** `404` if the auth user doesn't exist; `500` on other auth API failures.

---

## 3. Capacity check — exact logic

On `PATCH /tokens/{id}/approve`:
1. Sum `quantity_kg` of all tokens for the same `center_id` + `requested_date` that are already in `waiting`, `called`, or `completed` (i.e. already approved — `pending` requests don't count yet).
2. If `sum + this_request.quantity_kg > center.daily_capacity_kg` → `400`, nothing changes.
3. Otherwise → token gets `token_number = (count of already-approved) + 1`, `time_slot` assigned by that same position (see below), status → `waiting`.

Rejecting or cancelling a token removes it from this sum automatically — no separate "freeing" step exists or is needed.

## 4. Time slot assignment — exact logic

Fixed-interval spacing in **approval order**, not a scheduling algorithm:
- First approval for a given center+date → `09:00`
- Second → `09:25`
- Third → `09:50`
- ... i.e. `09:00 + (approval_position - 1) × 25 minutes`

Not configurable per center yet. If your team wants different spacing or center-specific hours, that's a small follow-up change — ask.

---

## 5. Voice (Vapi) — caller identification & context

**Milestone 1 only.** This endpoint identifies the calling farmer and
reports their active requests. It does **not** create, approve, reject,
or change any token — that's a later milestone. It's called by the Vapi
server/webhook layer, not directly by farmers or the frontend.

### `GET /voice/context`

**Auth:** `Authorization: Bearer <VAPI_WEBHOOK_SECRET>` — a server-to-server
secret, distinct from farmer JWTs (which aren't implemented yet anyway).
Missing/wrong header → `401`. If the server itself has no
`VAPI_WEBHOOK_SECRET` configured → `500`.

**Query parameters:**

| Param | Type | Required | Notes |
|---|---|---|---|
| `phone` | string | yes | Caller's number. Accepts a bare 10-digit Indian mobile number, a `91`-prefixed number, or full E.164 (`+91...`). Normalized server-side. |

**Phone normalization examples:**
9876543210 -> +919876543210
919876543210 -> +919876543210
+919876543210 -> +919876543210 (unchanged)

Anything that doesn't match one of these shapes → `400`.

**Resolution logic:**
1. Normalize `phone` to E.164.
2. Look up `profiles` for a row with that `phone` and `role = 'farmer'`.
3. **Match found** → use that farmer. `demo_mode_used: false`.
4. **No match, `DEMO_MODE=true`** → use the farmer identified by
   `DEMO_FARMER_ID`. `demo_mode_used: true`. The demo farmer is a normal
   `profiles` row with `role='farmer'` — it goes through the exact same
   `POST /tokens` limits (max 3 active, one per day) as any real farmer;
   nothing about those rules is bypassed for demo calls.
5. **No match, `DEMO_MODE=false`** → `404`.

**Success response — `200 OK`:**
```json
{
  "demo_mode_used": false,
  "caller_number": "+919876543210",
  "farmer_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "farmer_name": "Ramesh Kumar",
  "active_tokens": [
    {
      "id": "a1b2c3d4-...",
      "center_id": "9c858901-...",
      "center_name": "Karnal Mandi Center 3",
      "requested_date": "2026-09-10",
      "crop_type": "Wheat",
      "quantity_kg": 500,
      "token_number": null,
      "time_slot": null,
      "status": "pending"
    }
  ]
}
```
`active_tokens` includes only `pending`, `waiting`, and `called` requests
(same `ACTIVE_STATUSES` used by `POST /tokens`'s own limit checks) — a
farmer with none gets an empty list, not an error. `center_name` is
pulled in via the existing `tokens.center_id -> procurement_centers.id`
relationship, so the caller doesn't need a second lookup.

**Error responses:**
- `400 Bad Request` — `{"detail": "Could not recognize this as an Indian phone number."}`
- `401 Unauthorized` — `{"detail": "Missing or invalid Authorization header"}`
- `404 Not Found` — `{"detail": "No farmer is registered with this number."}` (only when `DEMO_MODE=false`)
- `500 Internal Server Error` — server misconfiguration, e.g.:
  - `{"detail": "VAPI_WEBHOOK_SECRET is not configured on the server."}`
  - `{"detail": "DEMO_MODE is enabled but DEMO_FARMER_ID is not configured."}`
  - `{"detail": "DEMO_FARMER_ID is not a valid UUID."}`
  - `{"detail": "DEMO_FARMER_ID does not match any farmer profile."}`

**Out of scope for this milestone:** the `POST /webhooks/vapi` event/tool-call handler (documented in Section 6 below), token cancellation through voice, and call analytics/transcript storage. Voice token *creation* is documented in Section 6 (Milestone 5).

---

## 6. Voice (Vapi) — tool-call webhook

**Milestone 2** added three read-only tools. **Milestone 5** adds one write tool, `create_token_request`, which creates a single new `pending` token request — nothing else. This endpoint still never approves, rejects, cancels, or changes the status of a token, and never creates or updates a procurement centre. Every other write continues to go exclusively through the existing `/tokens` and `/centers` endpoints, and `create_token_request` itself creates its row by calling the same `create_token()` function `POST /tokens` uses — not a separate insert path.

### `POST /webhooks/vapi`

**Authentication:**

```text
Authorization: Bearer <VAPI_WEBHOOK_SECRET>
```

- Missing or incorrect authorization header → `401`
- `VAPI_WEBHOOK_SECRET` not configured on the server → `500`

### Request body

The endpoint accepts a Vapi `tool-calls` server message:

```json
{
  "message": {
    "type": "tool-calls",
    "toolCallList": [
      {
        "id": "call_abc123",
        "function": {
          "name": "get_farmer_context",
          "arguments": {}
        }
      }
    ],
    "call": {
      "customer": {
        "number": "+919876543210"
      }
    }
  }
}
```

The caller’s phone number is checked in this order:

1. `message.customer.number`
2. `message.call.customer.number`
3. The `phone` tool argument

The `phone` argument allows local testing through curl or the Vapi dashboard without making a real call.

### Supported tools

| Tool | Arguments | Behaviour |
|---|---|---|
| `get_farmer_context` | None | Identifies the registered or demo farmer and returns their name and active `pending`, `waiting`, or `called` tokens. |
| `get_token_status` | `token_id` (optional), `token_number` (optional) | Returns the identified farmer’s tokens in any status. With no arguments, it returns all tokens. `token_id` selects one exact token. `token_number` returns matching tokens belonging to that farmer. |
| `list_active_centres` | `crop_type` (optional) | Returns active procurement centres containing `id`, `name`, `location`, `crop_type`, and `msp_rate`. Caller identification is not required. |
| `create_token_request` | `center_id` (required), `crop_type` (required), `quantity_kg` (required), `requested_date` (required, `YYYY-MM-DD`), `confirmed` (required, boolean) | Creates one new `pending` token request for the identified farmer, after every check below passes. **The only tool that writes to the database.** |

The centre `id` returned by `list_active_centres` is what the assistant should pass back as `center_id` to `create_token_request`. The assistant does not need to read the UUID aloud to the farmer.

`token_number` is a real database column. It remains `null` while a request is pending and is assigned when staff approves the request — `create_token_request` never sets it.

### `create_token_request` — validation order

1. `confirmed` must be exactly `true`. Anything else (missing, `false`, a string) is rejected — the assistant must have already read the details back and gotten explicit agreement before calling this tool.
2. `center_id` must be a real procurement centre.
3. That centre must have `is_active: true`.
4. `crop_type` must match that centre’s `crop_type` (case-insensitive). Each centre grows exactly one crop, matching `GET /centers`.
5. `quantity_kg` must be a positive number.
6. `requested_date` must be a valid `YYYY-MM-DD` date, not in the past, and — only when the centre has `open_date`/`close_date` set — inside that window.
7. Only after all of the above: the existing `routers.tokens.create_token()` rules run unchanged — one active request per farmer per date, and a maximum of 3 active (`pending`/`waiting`/`called`) requests per farmer.

The row is stored with the *centre's* canonical `crop_type` value, not necessarily the exact word the farmer used, so spelling/casing differences on the call don't create inconsistent data.

### Success response

Once authentication and the top-level payload structure are valid, the endpoint returns `200 OK`:

```json
{
  "results": [
    {
      "toolCallId": "call_abc123",
      "result": "{\"demo_mode_used\": false, \"caller_number\": \"+919876543210\", \"farmer_name\": \"Ramesh Kumar\", \"active_tokens\": []}"
    }
  ]
}
```

`result` is a JSON-encoded string. One result is returned for every incoming tool call and matched using `toolCallId`.

### Error handling

#### Top-level HTTP errors

These errors prevent the complete request from being processed:

- `400` — malformed JSON
- `400` — missing `message` object
- `400` — missing or empty `toolCallList`
- `400` — a tool call is missing its `id`
- `401` — missing or incorrect authorization header
- `500` — `VAPI_WEBHOOK_SECRET` is not configured on the server

#### Tool-level errors

These errors are returned inside that tool call’s `result`. The overall HTTP response remains `200`:

```json
{
  "results": [
    {
      "toolCallId": "call_abc123",
      "result": "{\"error\": \"Missing caller phone number.\"}"
    }
  ]
}
```

Tool-level errors include:

- Unsupported tool name
- Missing caller phone number
- Invalid Indian phone number
- Caller not registered while `DEMO_MODE=false`
- Missing, invalid or unknown `DEMO_FARMER_ID`
- No token matching the supplied `token_id` or `token_number`
- Unexpected Supabase error

`create_token_request` additionally embeds an error for:

- `confirmed` missing or not `true`
- Missing or malformed `center_id`
- Centre not found
- Centre not currently active (`is_active: false`)
- `crop_type` missing, or not matching the centre’s crop
- `quantity_kg` missing, non-numeric, zero, or negative
- `requested_date` missing or not `YYYY-MM-DD`
- `requested_date` in the past
- `requested_date` outside the centre’s `open_date`/`close_date` window (when set)
- Farmer already has an active request for that date
- Farmer already has 3 active requests

The last two re-use `routers.tokens.create_token()`’s existing messages unchanged.

Returning errors per tool call allows other tool calls in the same request to complete independently.

### Write scope

`create_token_request` is the only tool call that writes to the database, and it can only ever insert one new `pending` token row. This endpoint still never:

- Approves or rejects requests
- Changes token status (`waiting`/`called`/`completed`)
- Cancels tokens
- Creates or updates procurement centres
- Stores call transcripts or analytics

### Out of scope for Milestone 5

- Vapi assistant configuration and Twilio phone-number connection (Milestones 3–4)
- Token cancellation through voice (planned for Milestone 6)
- An idempotency key for retried tool calls — not added in this milestone; see the concurrency note in `services/voice_booking.py`. A retried booking for the same date is caught by the existing same-day-active-request rule instead.
- Notifications or daily calls
- Call analytics or transcript storage

For Vapi browser/web calls, caller-number metadata may be absent.

- Missing phone with `DEMO_MODE=true` uses `DEMO_FARMER_ID` and returns `caller_number: null`.
- Missing phone with `DEMO_MODE=false` returns an embedded missing-phone error.
- This behaviour applies only to `POST /webhooks/vapi`.
- `GET /voice/context` continues to require a phone number.