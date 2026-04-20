-- Migration: add app_schema.gen_sql_agent_output (Gen-SQL Agent persistence).
-- Run once on databases created before this table existed.
-- Safe if the table already exists.

CREATE TABLE IF NOT EXISTS app_schema.gen_sql_agent_output (
    id                         SERIAL PRIMARY KEY,
    intent_output_id           INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    generated_sql              TEXT NOT NULL DEFAULT '',
    reasoning_summary          TEXT,
    validation_passed          BOOLEAN NOT NULL DEFAULT FALSE,
    validation_error_codes     TEXT NOT NULL DEFAULT '',
    validation_error_message   TEXT NOT NULL DEFAULT '',
    blocked_keywords           TEXT NOT NULL DEFAULT '',
    is_single_statement        BOOLEAN NOT NULL DEFAULT FALSE,
    is_select_only             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                 TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

COMMENT ON TABLE app_schema.gen_sql_agent_output IS 'Gen-SQL Agent: generated SQL and validation fields for one intent_agent_output row';
