-- Migration: system_schema.few_shot_examples (Few-Shot Agent). Idempotent.

CREATE SCHEMA IF NOT EXISTS system_schema;

CREATE TABLE IF NOT EXISTS system_schema.few_shot_examples (
    id              SERIAL PRIMARY KEY,
    question_text   TEXT NOT NULL,
    sql_query       TEXT NOT NULL,
    query_type      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_few_shot_examples_query_type
    ON system_schema.few_shot_examples (query_type);
