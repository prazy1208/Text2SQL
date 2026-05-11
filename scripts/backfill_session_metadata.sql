-- Backfill session metadata for legacy rows (run once against text2sql_db).
-- Safe to re-run for title backfill: only fills sessions where title IS NULL or blank.
--
-- Usage:
--   psql "$DATABASE_URL" -f scripts/backfill_session_metadata.sql
--   or: python scripts/run_backfill_session_metadata.py
--   or paste sections into pgAdmin / Supabase SQL Editor.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Title from first user message (matches app derive_session_title logic:
--    collapse whitespace, max 60 chars, ellipsis)
-- ---------------------------------------------------------------------------
WITH first_user AS (
  SELECT DISTINCT ON (session_id)
    session_id,
    regexp_replace(trim(content), '\s+', ' ', 'g') AS normalized
  FROM app_schema.chat_messages
  WHERE lower(trim(role)) = 'user'
  ORDER BY session_id, id ASC
),
titles AS (
  SELECT
    session_id,
    CASE
      WHEN normalized IS NULL OR normalized = '' THEN 'New chat'
      WHEN char_length(normalized) <= 60 THEN normalized
      ELSE (left(normalized, 59) || E'…')
    END AS new_title
  FROM first_user
)
UPDATE app_schema.sessions s
SET title = t.new_title,
    updated_at = CURRENT_TIMESTAMP
FROM titles t
WHERE s.session_id = t.session_id
  AND (s.title IS NULL OR trim(s.title) = '');

-- ---------------------------------------------------------------------------
-- 2) client_id: use Python runner (parameterized) instead of pasting UUID here:
--    python scripts/run_backfill_session_metadata.py --client-id "<text2sql_client_id>"
--    Or uncomment and replace the UUID below (sessions with messages, NULL client_id only).
-- ---------------------------------------------------------------------------
-- UPDATE app_schema.sessions s
-- SET client_id = '00000000-0000-0000-0000-000000000000'::uuid,
--     updated_at = CURRENT_TIMESTAMP
-- WHERE s.client_id IS NULL
--   AND EXISTS (
--     SELECT 1 FROM app_schema.chat_messages m WHERE m.session_id = s.session_id
--   );

-- ---------------------------------------------------------------------------
-- 3) OPTIONAL: Remove empty shell sessions (no messages). Uncomment to run.
-- ---------------------------------------------------------------------------
-- DELETE FROM app_schema.sessions s
-- WHERE NOT EXISTS (
--   SELECT 1 FROM app_schema.chat_messages m WHERE m.session_id = s.session_id
-- );

COMMIT;
