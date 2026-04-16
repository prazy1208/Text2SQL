-- Migration: add app_schema.table_agent_output (Table Agent 5a).
-- Run once on databases that were created with an older create_app_schema.sql
-- (before table_agent_output existed). Safe to run if table already exists.

CREATE TABLE IF NOT EXISTS app_schema.table_agent_output (
    id                 SERIAL PRIMARY KEY,
    intent_output_id   INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    selected_tables    TEXT[] NOT NULL DEFAULT '{}',
    created_at         TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

COMMENT ON TABLE app_schema.table_agent_output IS 'Table Agent: selected_tables for one intent_agent_output row';
