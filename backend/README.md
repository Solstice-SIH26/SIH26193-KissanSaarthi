# SIH PS26032 — Procurement Center API (backend, WIP)

Token queue + schedule + MSP price endpoints for the farmer/procurement/admin app.
This covers **schema + token/queue/schedule/price endpoints only**. Admin UI,
auth, and the React frontend are being built by teammates.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in SUPABASE_URL and SUPABASE_KEY
```

Run `schema.sql` in the Supabase SQL editor (or via migrations) to create the tables.

```bash
uvicorn main:app --reload
```

Interactive API docs: http://localhost:8000/docs

## Endpoints

| Method | Path                        | Who calls it        | Body / Query                          | Returns |
|--------|-----------------------------|----------------------|----------------------------------------|---------|
| POST   | `/tokens`                   | Farmer (submit request) | `{farmer_id, center_id, requested_date, crop_type, quantity_kg}` | New token, `status: pending` |
| GET    | `/tokens/{token_id}`        | Farmer (check status)| —                                       | Token object |
| PATCH  | `/tokens/{token_id}/approve`| Procurement staff     | — (no body)                             | Token with `status: waiting`, `token_number`, `time_slot` assigned |
| PATCH  | `/tokens/{token_id}/reject` | Procurement staff     | — (no body)                             | Token with `status: rejected` |
| PATCH  | `/tokens/{token_id}/cancel` | Farmer or staff       | — (no body)                             | Token with `status: cancelled` |
| PATCH  | `/tokens/{token_id}/status` | Procurement staff     | `{status}` — only `waiting→called` or `called→completed` | Updated token |
| GET    | `/centers`                  | Farmer (browse)      | optional `?crop_type=`                 | List of centers |
| GET    | `/centers/{center_id}`      | Farmer / staff        | —                                       | Single center object |
| POST   | `/centers`                  | Admin (create center) | full center fields incl. `daily_capacity_kg` | New center object |
| PATCH  | `/centers/{center_id}`      | Admin (edit center, incl. price) | any subset of center fields (e.g. just `{"msp_rate": 2450}`) | Updated center object |
| DELETE | `/centers/{center_id}`      | Admin (remove center) | —                                       | `204 No Content` |
| GET    | `/centers/{center_id}/queue`| Procurement staff     | optional `?status=`                    | List of tokens for that center |
| GET    | `/users`                    | Admin (manage users)  | optional `?role=admin\|procurement\|farmer` | List of profiles |
| PATCH  | `/users/{user_id}`          | Admin (edit/deactivate) | any subset (e.g. `{"is_active": false}`) | Updated profile |
| DELETE | `/users/{user_id}`          | Admin (remove account) | —                                       | `204 No Content` |
| GET    | `/health`                   | anyone                | —                                       | `{"status": "ok"}` |

Full request/response schemas are auto-generated at `/docs`.

## Farmer request → approval workflow (v3)

1. Farmer submits `POST /tokens` with `center_id`, `requested_date`, `crop_type`, `quantity_kg` → status `pending`, no `token_number`/`time_slot` yet.
2. Staff view pending requests: `GET /centers/{id}/queue?status=pending`.
3. Staff call `PATCH /tokens/{id}/approve` — this checks the center's `daily_capacity_kg` isn't exceeded for that date, then assigns `token_number` + `time_slot` and moves status to `waiting`. Fails with `400` if capacity would be exceeded.
4. Or staff call `PATCH /tokens/{id}/reject` — moves to `rejected`, no side effects.
5. From `waiting`, staff progress the token via `PATCH /tokens/{id}/status` (`waiting→called`, then `called→completed`).
6. `PATCH /tokens/{id}/cancel` works from `pending` or `waiting` — capacity and the farmer's day-slot free up automatically since capacity/limit checks only count `pending`/`waiting`/`called`.

**Limits enforced at request time (`POST /tokens`):**
- One active request per farmer per `requested_date`, across any center
- Max 3 active (`pending`/`waiting`/`called`) requests per farmer at once

## Deployment (Railway)

`Procfile` and `railway.json` are both included — Railway should auto-detect
the Python app via Nixpacks and use either one to start it. You'll need to
set `SUPABASE_URL` and `SUPABASE_KEY` as environment variables in the
Railway project dashboard (not from `.env` — that file isn't committed).

## Incomplete / temporary — flag before demo day

- **No auth yet.** All endpoints — including admin ones — trust whatever the client sends, with no role check. JWT verification is planned once login is working on the auth side.
- **DELETE endpoints do real, permanent deletion** — `DELETE /centers/{id}` fails cleanly (400) if the center has existing tokens or assigned staff; prefer `PATCH .../is_active=false` to deactivate instead. `DELETE /users/{id}` removes the actual Supabase Auth account (via Admin API), which cascades to remove their profile — their historical tokens remain in the `tokens` table but will reference a `farmer_id` with no profile attached. Prefer `PATCH /users/{id}` with `{"is_active": false}` if you want to keep clean history.
- **`token_number` and `time_slot` assignment has no locking** — two staff approving simultaneously for the same center+date could theoretically race. Fine for demo load.
- **Time slots are fixed 25-min spacing from 9:00 AM**, not configurable per center yet — flagged for team lead to confirm.
- **CORS is wide open** (`allow_origins=["*"]`) — narrow this once the real frontend URL (Vercel) is known.
- **No pagination** on `/centers`, `/centers/{id}/queue`, or `/users` — assumes small demo dataset.
- **`profiles.id` is not auto-generated** — it must match a real `auth.users(id)` row.
