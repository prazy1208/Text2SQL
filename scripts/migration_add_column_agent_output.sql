-- Migration: add app_schema.column_agent_output (Column Agent 5b).
-- Run once on databases created before this table existed.
-- Safe if the table already exists.

CREATE TABLE IF NOT EXISTS app_schema.column_agent_output (
    id                      SERIAL PRIMARY KEY,
    table_agent_output_id   INT NOT NULL REFERENCES app_schema.table_agent_output(id) ON DELETE CASCADE,
    selected_columns        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (table_agent_output_id)
);

COMMENT ON TABLE app_schema.column_agent_output IS 'Column Agent: selected_columns (per table) for one table_agent_output row';
