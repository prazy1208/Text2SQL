# FK relationships pipeline

Foreign-key metadata for the Table and Column agents lives in **one table per domain schema**: `healthcare_schema.table_relationships`, `retail_schema.table_relationships`, and `finance_schema.table_relationships`. There is no central `system_schema` table for this feature.

## Flow

1. **DDL** — Create the three tables (same shape in each schema). See `scripts/create_domain_schema_table_relationships.sql` or `python scripts/run_create_domain_schema_table_relationships.py`. For databases that predate this feature, use `scripts/migration_add_domain_schema_table_relationships.sql` once.
2. **Load** — `python scripts/extract_and_load_relationships.py` reads FKs from `pg_catalog` and upserts into `{source_schema}.table_relationships` (only schemas listed in `DOMAIN_SCHEMAS` in `backend/config.py`).
3. **Embeddings + agent metadata** — `python build_relationship_embeddings.py` writes `metadata_store/relationships_{schema}_metadata.json` (SentenceTransformer `all-MiniLM-L6-v2`). **`POST /query` loads FK rows from these JSON files** via `list_relationships_from_metadata` (embeddings stripped at read time). The database tables are still the source of truth for extract/build scripts.
4. **API** — `POST /query` resolves `use_case` → `schema_name`, loads rows from metadata JSON, and passes them into the table, column, and Gen-SQL agents.

If you ever used the old centralized `system_schema.table_relationships`, drop it using the rollback snippet in `Text2SQL_PostgreSQL_Setup_Guide.md` §7b before relying on per-domain tables.

## Key files

| Purpose | Location |
| --- | --- |
| Domain list | `DOMAIN_SCHEMAS`, `RELATIONSHIP_METADATA_NAMES` in `backend/config.py` |
| DDL + migration | `scripts/create_domain_schema_table_relationships.sql`, `scripts/migration_add_domain_schema_table_relationships.sql` |
| Extract + upsert | `scripts/extract_and_load_relationships.py` |
| Embedding build | `build_relationship_embeddings.py` |
| Runtime load (API) | `list_relationships_from_metadata` in `backend/services/relationship_retrieval.py` |
| HTTP wiring | `backend/api/routes/query.py` |
| Prompts | `backend/agents/table_agent.py`, `backend/agents/column_agent.py` |

## Environment

Scripts and `get_engine()` use the same variables as the rest of the project: `DATABASE_URL` or `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (default database name `text2sql_db` in backend config).

## Operations

- **Order:** Domain schemas and business tables must exist before creating `table_relationships`. Then extract/load; embeddings are optional and can be run after load.
- **Logging:** If the metadata JSON file is missing or unreadable, `query.py` logs a warning and continues with an empty relationship list so the pipeline still responds.
