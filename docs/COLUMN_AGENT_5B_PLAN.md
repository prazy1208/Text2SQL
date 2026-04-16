# Column Agent (5b) — Plan (simple version)

Single in-repo reference for Column Agent design: metadata shape, FAISS shortlist, LLM, DB, API. Aligns with [TABLE_AGENT_5A_PLAN.md](TABLE_AGENT_5A_PLAN.md).

---

## What we are building

1. User asks a question → **Intent Agent** cleans it and pulls keywords.
2. **Table Agent** picks which **tables** are needed (`schema.table`).
3. **Column Agent** picks which **columns** are needed **inside those tables only**.
4. We save the column result in a **new database table** linked to the table-agent row.

The Column Agent never sees real data rows—only **metadata**: column name, description, and **data type**.

---

## Keeping hierarchy: Schema → Table → Column (easy trace-back)

We need two views of the same facts. Both stay in sync when you run the build script.

**A) Nested file (human-friendly, matches the real world)**

- Keep (or improve) one JSON per domain schema, e.g. `metadata_store/{schema}_metadata.json`.
- Shape stays **nested**:
  - top level: one schema (the file is already per schema)
  - inside: a **list of tables**
  - each table: `schema_name`, `table_name`, `table_description`, `columns[]`
  - each column: `name`, `description`, `data_type`

So the path **Schema → Table → Columns** is obvious in the file.

**B) Flat list for FAISS (one row per column vector)**

- When building embeddings for columns, build a **list** where index `0, 1, 2, …` matches FAISS vector order **exactly**.
- **Every** item in that list must carry the full chain, for example:
  - `schema_name`
  - `table_name`
  - `column_name`
  - `data_type`
  - `description`
  - optional: `fqn` string `schema.table.column` as a single unique key for checks

**Rule:** If FAISS says “hit row 42”, you read `flat_columns[42]` and you immediately know schema, table, and column—no guessing.

**How A and B link**

- Build **B** by walking **A** in a fixed order (e.g. sort tables by name, then columns by name). Document that order in code comments so rebuilds stay stable.
- Optionally save `flat_columns` as `metadata_store/{schema}_columns_metadata.json` next to `faiss_indexes/{schema}_columns.index`.

**Table-level index (already there)**

- The existing per-table FAISS index stays as-is for the Table Agent. Column search uses the **column** index + **column** flat list only.

---

## How data types will be fetched (PostgreSQL) — use this only

Today we only read column **comments** for descriptions. When `build_vector_store.py` runs, extend the column extraction to load types from **`pg_catalog`** (not `information_schema` for this).

- **Query shape:** `pg_attribute` joined to `pg_class` and `pg_namespace` (same schema/table/column identity as today).
- **Type string:** `format_type(a.atttypid, a.atttypmod)` — Postgres-native spelling (e.g. `character varying(50)`, `numeric(10,2)`), including length/precision where it matters.
- **Filters:** unchanged from current column comment query: `attnum > 0`, not dropped, ordinary tables (`relkind = 'r'`).

**Where it lands**

- Each column in nested JSON gets `data_type` at extract time.
- The same string is copied onto every flat FAISS metadata row and into the embedding text (search + LLM both see it).

---

## Column threshold (when to use FAISS vs send everything)

- **Constant:** `COLUMN_SHORTLIST_THRESHOLD = 20`.
- **What we count:** total columns across **only** the tables in `selected_tables` (not the whole schema).
- **Behavior:**
  - If count **≤ 20:** put **all** those column metadata rows in the Column LLM prompt (no column FAISS step for that request).
  - If count **> 20:** run column FAISS with **K = 20** (constant e.g. `COLUMN_FAISS_TOP_K = 20` in the column metadata service—**separate** from the Table Agent’s `DEFAULT_TOP_K`, which remains 10 for table shortlist), then **filter** hits to selected tables, then pass that shortlist to the LLM.

**Why 20:** Keeps prompts small and pushes similarity search earlier when several tables are selected or tables are wide. The value lives in one config constant so you can tune without redesign.

---

## Small vs many columns

- Count columns **only for the tables the Table Agent selected**.
- **Few columns (≤ 20):** send all of those column metadata rows to the Column LLM.
- **Many columns (> 20):** embed the question + keywords, search the **column** FAISS index, take **top 20** hits, **then drop** anything not in the selected tables. Send that shorter list to the LLM.

If there are **no** selected tables, skip the Column Agent and save an empty result.

---

## Column LLM output

- Output is JSON only, grouped by table (e.g. `schema.table` → list of column names).
- After the model answers, **check** every column exists in the candidate list for that table.

---

## Database

- New table `column_agent_output` with a **foreign key** to `table_agent_output` (one column result per table-agent result).
- Store the chosen columns as **JSON** (JSONB is fine).

---

## API

**Implemented** (`backend/api/routes/query.py`):

- After `insert_table_agent_output` returns `table_agent_output_id`, if `selected_tables` is non-empty run `run_column_agent`, then `insert_column_agent_output(table_agent_output_id, selected_columns)`.
- If there are no selected tables, `selected_columns` stays `{}` and a column row is still saved as `{}` (1:1 with `table_agent_output`).
- Column LLM failure: `selected_columns` cleared to `{}`, error string appended; column row still inserted as `{}`.
- `QueryResponse` includes `selected_columns: dict[str, list[str]]` (table FQN → column names).

---

## Frontend

**Implemented:** `frontend/index.html`, `app.js`, `styles.css` — “Selected columns” section, grouped by table FQN.

---

## Build order (short)

1. Extend metadata extract: descriptions + **data types**; nested JSON updated. **Done**
2. Build flat column list + column FAISS index; keep row `i` ↔ vector `i`. **Done**
3. Column metadata service (threshold + search + filter). **Done**
4. Column agent + validation. **Done**
5. DB migration + insert helper. **Done**
6. API + UI. **Done**
7. This doc + `docs/PROJECT_STRUCTURE.md` in sync. **Done** (re-check when adding Gen-SQL, etc.)

---

## Things to watch

- Flat list length must equal FAISS vector count.
- Rebuild indexes after metadata changes.
