-- Migration: add app_schema.few_shot_agent_output (Few-Shot Agent output persistence).
-- Run once on databases created before this table existed.
-- Safe if the table already exists.

CREATE TABLE IF NOT EXISTS app_schema.few_shot_agent_output (
    id                  SERIAL PRIMARY KEY,
    intent_output_id    INT NOT NULL REFERENCES app_schema.intent_agent_output(id) ON DELETE CASCADE,
    few_shot_examples   JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (intent_output_id)
);

COMMENT ON TABLE app_schema.few_shot_agent_output IS 'Few-Shot Agent: selected few_shot_examples for one intent_agent_output row';
