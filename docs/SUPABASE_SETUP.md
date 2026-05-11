# Supabase setup for Text2SQL (from scratch)

Use this when you want a **hosted Postgres** instead of local PostgreSQL. The app reads **`DATABASE_URL`** from `.env` (see `backend/config.py`).

---

## 1. Create a Supabase project

1. Go to [https://supabase.com](https://supabase.com) and sign in.
2. **New project** → choose organization, name, region, and **database password**.

This password is the **`postgres` user password** for the default database. Store it in a password manager.

---

## 2. Change or reset the database password later

1. Open your project → **Project Settings** (gear) → **Database**.
2. Under **Database password**, use **Reset database password** (or set a new one if your UI offers it).
3. **Update `.env` immediately** with the new password in `DATABASE_URL` (or in `DB_PASSWORD` if you use split variables).

Any app or script using the old password will fail until you update `.env`.

**Password with special characters:** If the password contains `@`, `:`, `/`, `#`, etc., it must be **URL-encoded** inside the connection URI, or use the **Connection pooling** URI from the dashboard (Supabase often shows a copy-paste string that is already safe).

---

## 3. Connection string for this codebase

1. In Supabase: **Project Settings** → **Database**.
2. Find **Connection string** → **URI** (sometimes labeled “psql” or “SQLAlchemy”).
3. It looks like:

   `postgresql://postgres.[ref]:[YOUR-PASSWORD]@aws-0-[region].pooler.supabase.com:6543/postgres`  
   or direct:

   `postgresql://postgres:[YOUR-PASSWORD]@db.[project-ref].supabase.co:5432/postgres`

4. Put it in **`.env`** as a **single line** (no spaces around `=`):

   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.xxxxx.supabase.co:5432/postgres
   ```

5. **SSL:** Supabase requires TLS. Either:
   - append **`?sslmode=require`** to the URL yourself, or  
   - rely on **`backend.config.get_engine()`**, which appends `sslmode=require` automatically when the host is `*.supabase.co` or `*.pooler.supabase.com`.

6. **Prefer `DATABASE_URL`:** If `DATABASE_URL` is set, **`DB_*` variables are ignored**. Use one style only to avoid confusion.

---

## 4. Load the schema (tables the API expects)

The API uses **`app_schema`** (sessions, intent/table/column outputs) and domain schemas (`healthcare_schema`, etc.).

1. Supabase → **SQL Editor** → **New query**.
2. Paste the contents of **`scripts/complete_setup.sql`** from this repo and **Run**.

Confirm there are no errors. This creates schemas and tables the Stage 1 pipeline needs.

If you use optional features (e.g. few-shot examples in `system_schema`), run the matching scripts from `scripts/` and `docs/FEWSHOT_PIPELINE_IMPLEMENTATION.md` as needed.

---

## 5. Local `.env` checklist

- Copy **`.env.example`** to **`.env`** at the project root.
- Set **`DATABASE_URL`** (recommended for Supabase).
- Add at least one LLM key (**`GEMINI_API_KEY`** or **`OPENAI_API_KEY`**).
- Never commit **`.env`** (keep it gitignored).

---

## 6. Run the API

From the project root:

```bash
uvicorn backend.api.main:app --reload
```

If the DB URL is wrong, you will see errors on first request that touches the DB (e.g. creating a session).

---

## 7. Browser storage after switching databases

Chat **transcripts and session rows** live in Postgres (`app_schema.sessions`, `app_schema.chat_messages`). The UI only stores:

- `text2sql_client_id` — anonymous scope for listing “your” sessions (`GET /sessions`)
- `text2sql_active_session` — last opened session id (reload convenience)

If you **point the app to a new database** (new Supabase project or reset DB), old session UUIDs are invalid.

**Fix:** Clear site data for this origin (or remove those keys under DevTools → Application → Local Storage), then reload. The app will create or pick sessions via the API.

---

## 8. Optional: connection pooler vs direct

- **Direct** (`db.[ref].supabase.co:5432`): fine for the API and scripts.
- **Pooler** (port **6543**): useful for serverless/high concurrency; use the URI Supabase shows for your driver.

Use the exact string from the dashboard when possible.

---

## 9. Troubleshooting

| Symptom | What to check |
|--------|----------------|
| SSL / connection errors | `sslmode=require` on the URL (or use `get_engine()` as above). |
| Authentication failed | Wrong password in URI; reset in Supabase and update `.env`. |
| `Invalid or unknown session_id` | Stale session id vs current DB; clear site storage or pick another chat (see §7). |
| Table does not exist | Run `complete_setup.sql` (or migrations) on this Supabase project. |

For a full local Postgres walkthrough (pgAdmin, etc.), see **`Text2SQL_PostgreSQL_Setup_Guide.md`**.
