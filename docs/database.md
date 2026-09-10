# Database Schema

Database: Supabase (PostgreSQL). Row Level Security (RLS) is enabled on
all public-facing tables.

## `profiles`

| Column     | Type        | Notes                                           |
| ---------- | ----------- | ----------------------------------------------- |
| id         | uuid        | Primary key, matches `auth.users(id)`           |
| name       | text        |                                                 |
| phone      | text        | Nullable — used for farmer phone login          |
| role       | text        | `admin` / `procurement` / `farmer`              |
| center_id  | uuid        | Nullable — set for staff, links to their centre |
| is_active  | boolean     |                                                 |
| created_at | timestamptz |                                                 |

## `procurement_centers`

| Column            | Type    | Notes                                 |
| ----------------- | ------- | ------------------------------------- |
| id                | uuid    | Primary key                           |
| name              | text    |                                       |
| location          | text    | Nullable                              |
| crop_type         | text    | Single crop accepted per centre       |
| msp_rate          | float   | Minimum Support Price                 |
| open_date         | date    | Nullable                              |
| close_date        | date    | Nullable                              |
| daily_capacity_kg | float   | Max kg the centre can process per day |
| is_active         | boolean |                                       |

## `tokens`

| Column         | Type        | Notes                                                                     |
| -------------- | ----------- | ------------------------------------------------------------------------- |
| id             | uuid        | Primary key                                                               |
| farmer_id      | uuid        | References `profiles.id`                                                  |
| center_id      | uuid        | References `procurement_centers.id`                                       |
| requested_date | date        |                                                                           |
| crop_type      | text        |                                                                           |
| quantity_kg    | float       |                                                                           |
| token_number   | int         | Nullable — assigned only on approval                                      |
| time_slot      | text        | Nullable — assigned only on approval                                      |
| status         | text        | `pending` / `waiting` / `called` / `completed` / `rejected` / `cancelled` |
| created_at     | timestamptz |                                                                           |
| updated_at     | timestamptz |                                                                           |

## Status Flow

\`\`\`
pending → waiting → called → completed
↓ ↓
rejected cancelled
\`\`\`
