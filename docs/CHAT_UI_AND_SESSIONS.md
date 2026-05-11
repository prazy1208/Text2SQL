# Chat UI, sessions, and multi-chat API

The Stage 1 web UI is a single-page chat served by FastAPI from [`frontend/`](../frontend/). Conversations are **stored in Postgres**; the browser keeps only a **client id** (anonymous scope) and **last active session id**.

---

## Project layout (frontend + session-related backend)

| Path | Role |
|------|------|
| [`frontend/index.html`](../frontend/index.html) | Shell: header, **sidebar** (chat list + **New chat**), chat column, composer. |
| [`frontend/app.js`](../frontend/app.js) | Loads use cases, lists sessions, switches chats, calls `/query`; legacy chat HTML storage removed. |
| [`frontend/styles.css`](../frontend/styles.css) | Sidebar + main column layout. |
| [`backend/api/routes/query.py`](../backend/api/routes/query.py) | `GET /sessions`, `GET /sessions/{id}/messages`, `POST /session`, `POST /query`. |
| [`backend/api/db.py`](../backend/api/db.py) | `sessions`, `chat_messages`, list/filter helpers, title/use_case updates. |
| [`scripts/create_app_schema.sql`](../scripts/create_app_schema.sql) | Defines `app_schema.sessions` (incl. `title`, `client_id`, `use_case`) and `chat_messages`. |

---

## HTTP API (session + chat)

Base URL: same origin as the UI when using the bundled static server (`uvicorn backend.api.main:app`).

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/use-cases` | Domain dropdown values. |
| `POST` | `/session` | Create a new session. Optional **`client_id`** query param or **`X-Client-Id`** header (UUID). |
| `GET` | `/sessions?client_id=<uuid>&limit=...` | List sessions where **`client_id` equals that UUID** (strict — NULL `client_id` rows are omitted). **Only sessions with at least one `chat_messages` row** are returned. Backfill NULL `client_id` for your browser: [`BACKFILL_SESSIONS.md`](BACKFILL_SESSIONS.md). |
| `GET` | `/sessions/{session_id}/messages` | Full transcript (ordered). If the session has **`client_id`**, pass the same UUID via **`X-Client-Id`** or **`client_id`** query (required). |
| `GET` | `/sessions/{session_id}/pipeline-turns` | One object per **`intent_agent_output`** row, joined to table/column/few-shot/gen-sql outputs (same client guard as messages). The UI uses this with **`messages`** to rebuild rich assistant bubbles after switching chats. |
| `DELETE` | `/sessions/{session_id}?client_id=` | Deletes the session and cascaded app data. Requires **`X-Client-Id`** or **`client_id`** matching **`sessions.client_id`**; sessions with NULL `client_id` cannot be deleted via this route. |
| `POST` | `/query` | Pipeline request. Body includes `message`, `use_case`, optional `session_id`, `message_type`, `confirmation`, optional **`client_id`** (used when the server creates a new session). |

Session **title** is set **once** on the server from the first user message of type `new_query` or `intent_correction` (trimmed / length-capped); it is **not** overwritten later.

---

## Database (`app_schema`)

**`sessions`**

- `session_id` (UUID, PK)
- `created_at`, `updated_at`
- `title` (TEXT, nullable until first qualifying user message)
- `client_id` (UUID, nullable — anonymous scope for `/sessions` listing)
- `use_case` (VARCHAR(64), nullable — updated when queries run)

**`chat_messages`**

- `id`, `session_id`, `role`, `message_type`, `content`, `created_at`

Inserts bump `sessions.updated_at` (see `insert_chat_message` in `backend/api/db.py`).

---

## “New chat” behavior

**New chat** clears the composer area and clears the active session id until you **Send**. The first message runs `POST /query` **without** `session_id`; the API creates the session (with `client_id`) and sets the title from that question. That avoids creating many empty sessions that all showed as **New chat** in the sidebar.

## Browser `localStorage`

| Key | Purpose |
|-----|---------|
| `text2sql_client_id` | Generated once per browser profile; identifies rows for `GET /sessions`. |
| `text2sql_active_session` | Last selected `session_id` so reload returns to the same chat when it still exists. |

Removed on load if present (legacy): `text2sql_chat_history`, `text2sql_session_id`.

---

## Operational notes

- After **database reset** or pointing `.env` at a new Postgres instance, old session UUIDs are invalid. Clear site storage or open the app fresh; the UI creates or selects sessions via the API.
- For Supabase or hosted Postgres, apply [`scripts/create_app_schema.sql`](../scripts/create_app_schema.sql) (or your combined setup script) so `sessions` includes `title`, `client_id`, and `use_case`.

**Backfill** old `sessions.title` or `client_id`: [`BACKFILL_SESSIONS.md`](BACKFILL_SESSIONS.md).

See also: [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md), [`SUPABASE_SETUP.md`](SUPABASE_SETUP.md).
