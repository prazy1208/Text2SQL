-- Migration: add table_relationships in healthcare_schema, retail_schema, finance_schema.
-- Safe to run if tables already exist (CREATE TABLE IF NOT EXISTS).
-- See create_domain_schema_table_relationships.sql for full comments.

-- healthcare_schema
CREATE TABLE IF NOT EXISTS healthcare_schema.table_relationships (
    id                  SERIAL PRIMARY KEY,
    source_table        TEXT NOT NULL,
    source_column       TEXT NOT NULL,
    target_schema       TEXT NOT NULL,
    target_table        TEXT NOT NULL,
    target_column       TEXT NOT NULL,
    relationship_text   TEXT NOT NULL,
    constraint_name     VARCHAR(256),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_healthcare_table_relationships_edge
        UNIQUE (source_table, source_column, target_schema, target_table, target_column)
);

CREATE INDEX IF NOT EXISTS idx_healthcare_table_relationships_source
    ON healthcare_schema.table_relationships (source_table);

CREATE INDEX IF NOT EXISTS idx_healthcare_table_relationships_source_col
    ON healthcare_schema.table_relationships (source_table, source_column);

-- retail_schema
CREATE TABLE IF NOT EXISTS retail_schema.table_relationships (
    id                  SERIAL PRIMARY KEY,
    source_table        TEXT NOT NULL,
    source_column       TEXT NOT NULL,
    target_schema       TEXT NOT NULL,
    target_table        TEXT NOT NULL,
    target_column       TEXT NOT NULL,
    relationship_text   TEXT NOT NULL,
    constraint_name     VARCHAR(256),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_retail_table_relationships_edge
        UNIQUE (source_table, source_column, target_schema, target_table, target_column)
);

CREATE INDEX IF NOT EXISTS idx_retail_table_relationships_source
    ON retail_schema.table_relationships (source_table);

CREATE INDEX IF NOT EXISTS idx_retail_table_relationships_source_col
    ON retail_schema.table_relationships (source_table, source_column);

-- finance_schema
CREATE TABLE IF NOT EXISTS finance_schema.table_relationships (
    id                  SERIAL PRIMARY KEY,
    source_table        TEXT NOT NULL,
    source_column       TEXT NOT NULL,
    target_schema       TEXT NOT NULL,
    target_table        TEXT NOT NULL,
    target_column       TEXT NOT NULL,
    relationship_text   TEXT NOT NULL,
    constraint_name     VARCHAR(256),
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_finance_table_relationships_edge
        UNIQUE (source_table, source_column, target_schema, target_table, target_column)
);

CREATE INDEX IF NOT EXISTS idx_finance_table_relationships_source
    ON finance_schema.table_relationships (source_table);

CREATE INDEX IF NOT EXISTS idx_finance_table_relationships_source_col
    ON finance_schema.table_relationships (source_table, source_column);
