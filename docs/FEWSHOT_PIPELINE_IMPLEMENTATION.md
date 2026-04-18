# Few-Shot Example Storage — Implementation Pack

This document contains **ready-to-add** artifacts for the Few-Shot Agent pipeline.  
**Plan mode** prevented writing `.sql` / `.py` files directly; copy sections into new files as named, or switch to **Agent mode** and ask to apply this pack.

**Storage (v1):** Postgres is the source of truth; a **build script** writes **`metadata_store/few_shot_examples_metadata.json`** (same idea as [`metadata_store/relationships_*_metadata.json`](metadata_store/) — list of objects for agents). Objects are **`{ id, question_text, sql_query, query_type }`** with **no** `embedding` field in v1 (text-only catalog).

**Retrieval:** **`fewshot_retrieval.py`** loads the catalog from **that JSON file** (optional fallback: read from DB if the file is missing). **`few_shot_agent.py`** uses an **LLM** to pick the **top `k`** examples (default 2). No FAISS.

---

## 1. SQL — `scripts/create_system_schema_few_shot_examples.sql`

```sql
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
```

**Migration (idempotent):** `scripts/migration_add_system_schema_few_shot_examples.sql` — same `CREATE TABLE IF NOT EXISTS` block without comments.

---

## 2. Schema runner — `scripts/run_create_few_shot_examples_schema.py`

```python
"""Apply scripts/create_system_schema_few_shot_examples.sql. Run from project root."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()


def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "text2sql_db")
    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def main():
    sql_file = PROJECT_ROOT / "scripts" / "create_system_schema_few_shot_examples.sql"
    if not sql_file.exists():
        print(f"SQL file not found: {sql_file}")
        sys.exit(1)
    sql = sql_file.read_text(encoding="utf-8")
    engine = get_engine()
    raw_conn = engine.raw_connection()
    try:
        cur = raw_conn.cursor()
        cur.execute(sql)
        raw_conn.commit()
    finally:
        raw_conn.close()
    print("Done. system_schema.few_shot_examples created.")


if __name__ == "__main__":
    main()
```

---

## 3. Insert script — `scripts/insert_few_shot_examples.py`

- Deletes existing rows (optional) then inserts 20 curated rows.
- Run after the table exists: `python scripts/insert_few_shot_examples.py`

```python
"""Insert 20 generic few-shot examples into system_schema.few_shot_examples."""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.chdir(PROJECT_ROOT)

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

EXAMPLES = [
    {"question": "Retrieve specific columns from a dataset", "sql": "SELECT column1, column2 FROM table_name;", "query_type": "select"},
    {"question": "Filter records based on a specific condition", "sql": "SELECT * FROM table_name WHERE column = value;", "query_type": "filter"},
    {"question": "Filter records using multiple conditions", "sql": "SELECT * FROM table_name WHERE column1 = value1 AND column2 = value2;", "query_type": "filter_multiple"},
    {"question": "Retrieve records where a column value falls within a range", "sql": "SELECT * FROM table_name WHERE column BETWEEN value1 AND value2;", "query_type": "filter_range"},
    {"question": "Calculate the total value of a numeric column", "sql": "SELECT SUM(numeric_column) FROM table_name;", "query_type": "aggregation_sum"},
    {"question": "Count the number of records", "sql": "SELECT COUNT(*) FROM table_name;", "query_type": "aggregation_count"},
    {"question": "Calculate average value of a numeric column", "sql": "SELECT AVG(numeric_column) FROM table_name;", "query_type": "aggregation_avg"},
    {"question": "Group data by a category and calculate total values", "sql": "SELECT category, SUM(numeric_column) FROM table_name GROUP BY category;", "query_type": "aggregation_groupby"},
    {"question": "Filter grouped results based on aggregated values", "sql": "SELECT category, SUM(numeric_column) FROM table_name GROUP BY category HAVING SUM(numeric_column) > threshold;", "query_type": "having"},
    {"question": "Sort records in descending order based on a metric", "sql": "SELECT * FROM table_name ORDER BY metric DESC;", "query_type": "ordering"},
    {"question": "Retrieve top N records based on a metric", "sql": "SELECT column_name FROM table_name ORDER BY metric DESC LIMIT 5;", "query_type": "ranking_limit"},
    {"question": "Retrieve distinct values from a column", "sql": "SELECT DISTINCT column_name FROM table_name;", "query_type": "distinct"},
    {"question": "Join two related datasets using a common identifier", "sql": "SELECT a.column1, b.column2 FROM table_a a JOIN table_b b ON a.id = b.id;", "query_type": "join"},
    {"question": "Combine multiple related datasets through chained joins", "sql": "SELECT a.column1, b.column2, c.column3 FROM table_a a JOIN table_b b ON a.id = b.id JOIN table_c c ON b.id = c.id;", "query_type": "multi_join"},
    {"question": "Filter records based on a date range", "sql": "SELECT * FROM table_name WHERE date_column >= 'start_date' AND date_column <= 'end_date';", "query_type": "time_filter"},
    {"question": "Compare aggregated values across two time periods", "sql": "SELECT SUM(CASE WHEN date_column >= period1_start AND date_column <= period1_end THEN value END) AS period1_total, SUM(CASE WHEN date_column >= period2_start AND date_column <= period2_end THEN value END) AS period2_total FROM table_name;", "query_type": "time_comparison"},
    {"question": "Create conditional labels based on column values", "sql": "SELECT column_name, CASE WHEN condition THEN 'Category A' ELSE 'Category B' END FROM table_name;", "query_type": "case_when"},
    {"question": "Use a subquery to filter results", "sql": "SELECT * FROM table_name WHERE column IN (SELECT column FROM another_table);", "query_type": "subquery"},
    {"question": "Rank records within groups based on a metric", "sql": "SELECT column_name, ROW_NUMBER() OVER (PARTITION BY group_column ORDER BY metric DESC) FROM table_name;", "query_type": "window_function"},
    {"question": "Handle missing values in a column", "sql": "SELECT COALESCE(column_name, default_value) FROM table_name;", "query_type": "null_handling"},
]


def get_engine():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return create_engine(database_url)
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    dbname = os.getenv("DB_NAME", "text2sql_db")
    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)


def main():
    engine = get_engine()
    insert_sql = text("""
        INSERT INTO system_schema.few_shot_examples (question_text, sql_query, query_type)
        VALUES (:question_text, :sql_query, :query_type)
    """)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM system_schema.few_shot_examples"))
        for ex in EXAMPLES:
            conn.execute(
                insert_sql,
                {
                    "question_text": ex["question"],
                    "sql_query": ex["sql"],
                    "query_type": ex["query_type"],
                },
            )
    print(f"Inserted {len(EXAMPLES)} row(s) into system_schema.few_shot_examples.")


if __name__ == "__main__":
    main()
```

---

## 4. Export to metadata store — `build_few_shot_metadata_store.py` (project root)

- Read all rows: `SELECT id, question_text, sql_query, query_type FROM system_schema.few_shot_examples ORDER BY id`.
- Write **`metadata_store/few_shot_examples_metadata.json`** as a JSON array (one object per row).
- Register **`FEWSHOT_METADATA_NAME`** in `backend/config.py` (same pattern as `RELATIONSHIP_METADATA_NAMES` / `METADATA_STORE_DIR`).
- **Run after** insert whenever the table changes.

---

## 5. Catalog load — `backend/services/fewshot_retrieval.py`

**No vector search.** Single function:

- `list_all_few_shot_examples() -> list[dict]` — **`json.load`** from `METADATA_STORE_DIR / FEWSHOT_METADATA_NAME`. Optional: if file missing, `SELECT ...` from Postgres and log once.
- Returns `[]` if no data.

---

## 6. Few-Shot Agent — `backend/agents/few_shot_agent.py`

- Call `list_all_few_shot_examples()`; if empty, return `{ "few_shot_examples": [] }`.
- Build a **prompt** (`FEW_SHOT_AGENT_PROMPT`) listing candidates with **`question`** and **`query_type` only** (no SQL in the LLM prompt; Gen-SQL receives SQL from resolved rows).
- Include **rephrased_question** and **keywords** in the user message.
- Ask the LLM (`chat_completion`) to return **JSON** `{"selected_examples": [{ "question", "query_type" }, ...]}` — **all** examples it considers relevant (no fixed cap).
- Map each pair back to catalog rows by matching `question_text` and `query_type`; return full `{ "few_shot_examples": [ {...}, ... ] }` with `id`, `question_text`, `sql_query`, `query_type` for downstream Gen-SQL.

---

## 7. Run order

1. `python scripts/run_create_few_shot_examples_schema.py` (or run SQL in pgAdmin)
2. `python scripts/insert_few_shot_examples.py`
3. `python build_few_shot_metadata_store.py` — generates `metadata_store/few_shot_examples_metadata.json`
4. From API or Gen-SQL: call `run_few_shot_agent(rephrased, keywords, business_insights)` (retrieval reads JSON)

---

## 8. Switch to Agent mode

To have these files **created automatically** in the repo, switch to **Agent mode** and ask: *“Implement the Few-Shot pipeline from docs/FEWSHOT_PIPELINE_IMPLEMENTATION.md”*.
