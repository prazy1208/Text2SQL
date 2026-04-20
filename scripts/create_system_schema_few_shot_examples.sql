-- Few-shot SQL pattern examples (generic) for the Few-Shot Agent.
-- Run against text2sql_db (or: python scripts/run_create_few_shot_examples_schema.py)

CREATE SCHEMA IF NOT EXISTS system_schema;

CREATE TABLE IF NOT EXISTS system_schema.few_shot_examples (
    id              SERIAL PRIMARY KEY,
    question_text   TEXT NOT NULL,
    sql_query       TEXT NOT NULL,
    query_type      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_few_shot_examples_query_type
    ON system_schema.few_shot_examples (query_type);

COMMENT ON SCHEMA system_schema IS 'Cross-cutting metadata (few-shot examples, etc.)';
COMMENT ON TABLE system_schema.few_shot_examples IS 'Curated question/SQL pairs for few-shot retrieval';
COMMENT ON COLUMN system_schema.few_shot_examples.query_type IS 'Pattern label (e.g. aggregation_groupby, join)';
