-- Per-domain FK metadata: one table_relationships per business schema.
-- Requires healthcare_schema, retail_schema, finance_schema to exist (see Text2SQL_PostgreSQL_Setup_Guide.md).
-- Run against text2sql_db (pgAdmin or: python scripts/run_create_domain_schema_table_relationships.py)

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

COMMENT ON TABLE healthcare_schema.table_relationships IS 'Foreign keys with referencing tables in healthcare_schema; target_schema for referenced side';
COMMENT ON COLUMN healthcare_schema.table_relationships.target_schema IS 'Schema of the referenced (target) table';
COMMENT ON COLUMN healthcare_schema.table_relationships.relationship_text IS 'Canonical line for LLM context';

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

COMMENT ON TABLE retail_schema.table_relationships IS 'Foreign keys with referencing tables in retail_schema; target_schema for referenced side';
COMMENT ON COLUMN retail_schema.table_relationships.target_schema IS 'Schema of the referenced (target) table';
COMMENT ON COLUMN retail_schema.table_relationships.relationship_text IS 'Canonical line for LLM context';

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

COMMENT ON TABLE finance_schema.table_relationships IS 'Foreign keys with referencing tables in finance_schema; target_schema for referenced side';
COMMENT ON COLUMN finance_schema.table_relationships.target_schema IS 'Schema of the referenced (target) table';
COMMENT ON COLUMN finance_schema.table_relationships.relationship_text IS 'Canonical line for LLM context';
