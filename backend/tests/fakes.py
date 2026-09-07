"""
A minimal in-memory stand-in for the real Supabase client, just enough to
drive the query chains used across routers/voice.py, routers/webhooks.py,
routers/centers.py, routers/tokens.py, and services/voice_booking.py
(select/eq/in_/order/limit/single/insert/update + execute, plus
count="exact" on select). Filters are applied for real against the
in-memory rows so tests can express "what's in the table" rather than
"what the mock returns for this specific call".

Milestone 5 note: insert()/update() mutate the *same* list object that
FakeSupabase stores for a table (not a copy), so a token inserted by one
`supabase.table("tokens")...` call is visible to the very next one within
the same test -- this is what lets the max-3-active-tokens and
same-day-active-request checks in routers.tokens.create_token() be
exercised realistically across a sequence of booking calls.
"""

import uuid
from datetime import datetime, timezone


class FakeResult:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    def __init__(self, table_rows):
        # table_rows is the actual list stored inside FakeSupabase for
        # this table name -- kept as a reference (not copied) so insert()
        # can append to it and update() can mutate rows in place, and
        # have both be visible to later `.table(...)` calls.
        self._table_rows = table_rows
        self._rows = list(table_rows)
        self._count_mode = None
        self._single = False
        self._pending_update = None
        self._pending_insert_rows = None

    def select(self, *args, **kwargs):
        self._count_mode = kwargs.get("count")
        return self

    def eq(self, field, value):
        self._rows = [r for r in self._rows if r.get(field) == value]
        return self

    def in_(self, field, values):
        self._rows = [r for r in self._rows if r.get(field) in values]
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, n):
        self._rows = self._rows[:n]
        return self

    def single(self):
        self._single = True
        return self

    def insert(self, row):
        """Appends to the *actual* table list (self._table_rows), not
        just the locally filtered self._rows, so it persists across
        subsequent `.table(...)` calls in the same test."""
        rows = row if isinstance(row, list) else [row]
        inserted = []
        now = datetime.now(timezone.utc).isoformat()
        for r in rows:
            new_row = dict(r)
            new_row.setdefault("id", str(uuid.uuid4()))
            new_row.setdefault("created_at", now)
            new_row.setdefault("updated_at", now)
            self._table_rows.append(new_row)
            inserted.append(new_row)
        self._pending_insert_rows = inserted
        self._rows = inserted
        return self

    def update(self, fields):
        """Stores the fields to apply; the actual mutation happens in
        execute(), after any .eq()/.in_() filters narrow self._rows down
        to the rows that should actually change -- matching the real
        supabase-py call order of `.update(...).eq(...).execute()`."""
        self._pending_update = fields
        return self

    def execute(self):
        if self._pending_update is not None:
            for r in self._rows:
                r.update(self._pending_update)
            return FakeResult(list(self._rows))

        if self._pending_insert_rows is not None:
            return FakeResult(list(self._pending_insert_rows))

        if self._single:
            data = self._rows[0] if len(self._rows) == 1 else None
            return FakeResult(data)

        count = len(self._rows) if self._count_mode else None
        return FakeResult(list(self._rows), count=count)


class FakeSupabase:
    def __init__(self, tables: dict):
        # Each table is stored as its own real (mutable) list, so writes
        # made through one FakeQuery are visible to the next .table(...)
        # call against the same FakeSupabase instance.
        self._tables = {name: list(rows) for name, rows in tables.items()}

    def table(self, name):
        self._tables.setdefault(name, [])
        return FakeQuery(self._tables[name])