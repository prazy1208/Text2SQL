# Backfill session `title` and `client_id`

The chat sidebar calls **`GET /sessions?client_id=…`** and only returns rows where **`sessions.client_id`** equals that UUID **and** the session has at least one **`chat_messages`** row. Legacy rows with **`client_id` NULL** do **not** appear until you backfill.

## 1. Title backfill

[`scripts/backfill_session_metadata.sql`](../scripts/backfill_session_metadata.sql) sets **`sessions.title`** from the **first user** message in **`chat_messages`** (whitespace collapsed, max 60 characters). It only updates rows where **`title` IS NULL or blank**.

## 2. `client_id` backfill (so old chats show in your browser)

Use the **same UUID** as in the browser: **DevTools → Application → Local Storage → `text2sql_client_id`**.

```bash
python scripts/run_backfill_session_metadata.py --client-id "YOUR-UUID-HERE"
```

Or set in **`.env`** (not committed):

```env
BACKFILL_CLIENT_ID=YOUR-UUID-HERE
```

Then:

```bash
python scripts/run_backfill_session_metadata.py
```

That updates every session that **has at least one chat message** and **`client_id` IS NULL**, assigning your browser id. New sessions created by the app already set `client_id` from the UI.

**Shared database:** only run this UUID for sessions that **should** belong to that browser. Do not assign one person’s UUID to everyone’s historical rows.

## What the Python script does

1. Runs the SQL file above (**titles**).
2. If **`--client-id`** or **`BACKFILL_CLIENT_ID`** is set, runs a parameterized **`UPDATE`** for **`client_id`** on NULL rows that have messages.

## Manual SQL

You can still paste section **1** from the `.sql` file in pgAdmin / Supabase. For **`client_id`**, prefer the Python command so you do not edit UUIDs inside the SQL file.

Section **3** in the SQL file (commented) deletes empty shell sessions if you want to clean those rows.

## After backfill

Restart the API if needed, hard-refresh the UI, and confirm the sidebar lists your chats.
