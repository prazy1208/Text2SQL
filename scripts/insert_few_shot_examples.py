"""Upsert few-shot examples into system_schema.few_shot_examples (additive, no DELETE).

Inserts ids 1–50 with ON CONFLICT (id) DO NOTHING so reruns are safe and existing rows
are not removed. After inserts, resets the id sequence to MAX(id).

Requires: scripts/create_system_schema_few_shot_examples.sql applied.
Run from project root: python scripts/insert_few_shot_examples.py
"""

from __future__ import annotations

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

# Baseline examples (ids 1–20); text matches prior catalog.
_BASELINE = [
    {"question_text": "Retrieve specific columns from a dataset", "sql_query": "SELECT column1, column2 FROM table_name;", "query_type": "select"},
    {"question_text": "Filter records based on a specific condition", "sql_query": "SELECT * FROM table_name WHERE column = value;", "query_type": "filter"},
    {"question_text": "Filter records using multiple conditions", "sql_query": "SELECT * FROM table_name WHERE column1 = value1 AND column2 = value2;", "query_type": "filter_multiple"},
    {"question_text": "Retrieve records where a column value falls within a range", "sql_query": "SELECT * FROM table_name WHERE column BETWEEN value1 AND value2;", "query_type": "filter_range"},
    {"question_text": "Calculate the total value of a numeric column", "sql_query": "SELECT SUM(numeric_column) FROM table_name;", "query_type": "aggregation_sum"},
    {"question_text": "Count the number of records", "sql_query": "SELECT COUNT(*) FROM table_name;", "query_type": "aggregation_count"},
    {"question_text": "Calculate average value of a numeric column", "sql_query": "SELECT AVG(numeric_column) FROM table_name;", "query_type": "aggregation_avg"},
    {"question_text": "Group data by a category and calculate total values", "sql_query": "SELECT category, SUM(numeric_column) FROM table_name GROUP BY category;", "query_type": "aggregation_groupby"},
    {"question_text": "Filter grouped results based on aggregated values", "sql_query": "SELECT category, SUM(numeric_column) FROM table_name GROUP BY category HAVING SUM(numeric_column) > threshold;", "query_type": "having"},
    {"question_text": "Sort records in descending order based on a metric", "sql_query": "SELECT * FROM table_name ORDER BY metric DESC;", "query_type": "ordering"},
    {"question_text": "Retrieve top N records based on a metric", "sql_query": "SELECT column_name FROM table_name ORDER BY metric DESC LIMIT 5;", "query_type": "ranking_limit"},
    {"question_text": "Retrieve distinct values from a column", "sql_query": "SELECT DISTINCT column_name FROM table_name;", "query_type": "distinct"},
    {"question_text": "Join two related datasets using a common identifier", "sql_query": "SELECT a.column1, b.column2 FROM table_a a JOIN table_b b ON a.id = b.id;", "query_type": "join"},
    {"question_text": "Combine multiple related datasets through chained joins", "sql_query": "SELECT a.column1, b.column2, c.column3 FROM table_a a JOIN table_b b ON a.id = b.id JOIN table_c c ON b.id = c.id;", "query_type": "multi_join"},
    {"question_text": "Filter records based on a date range", "sql_query": "SELECT * FROM table_name WHERE date_column >= 'start_date' AND date_column <= 'end_date';", "query_type": "time_filter"},
    {"question_text": "Compare aggregated values across two time periods", "sql_query": "SELECT SUM(CASE WHEN date_column >= period1_start AND date_column <= period1_end THEN value END) AS period1_total, SUM(CASE WHEN date_column >= period2_start AND date_column <= period2_end THEN value END) AS period2_total FROM table_name;", "query_type": "time_comparison"},
    {"question_text": "Create conditional labels based on column values", "sql_query": "SELECT column_name, CASE WHEN condition THEN 'Category A' ELSE 'Category B' END FROM table_name;", "query_type": "case_when"},
    {"question_text": "Use a subquery to filter results", "sql_query": "SELECT * FROM table_name WHERE column IN (SELECT column FROM another_table);", "query_type": "subquery"},
    {"question_text": "Rank records within groups based on a metric", "sql_query": "SELECT column_name, ROW_NUMBER() OVER (PARTITION BY group_column ORDER BY metric DESC) FROM table_name;", "query_type": "window_function"},
    {"question_text": "Handle missing values in a column", "sql_query": "SELECT COALESCE(column_name, default_value) FROM table_name;", "query_type": "null_handling"},
]

_APPEND = [
    {"id": 21, "question_text": "Calculate running total of a metric over time", "sql_query": "SELECT date_column, value, SUM(value) OVER (ORDER BY date_column) AS running_total FROM table_name;", "query_type": "cumulative_sum"},
    {"id": 22, "question_text": "Find records that exist in one table but not another", "sql_query": "SELECT * FROM table_a WHERE NOT EXISTS (SELECT 1 FROM table_b WHERE table_b.id = table_a.id);", "query_type": "anti_join"},
    {"id": 23, "question_text": "Calculate percentage of total for each category", "sql_query": "SELECT category, value, ROUND(100.0 * value / SUM(value) OVER (), 2) AS percentage FROM table_name;", "query_type": "percentage_calculation"},
    {"id": 24, "question_text": "Pivot data to show values across different categories", "sql_query": "SELECT id, SUM(CASE WHEN category = 'A' THEN value ELSE 0 END) AS category_a, SUM(CASE WHEN category = 'B' THEN value ELSE 0 END) AS category_b FROM table_name GROUP BY id;", "query_type": "pivot"},
    {"id": 25, "question_text": "Find duplicate records based on specific columns", "sql_query": "SELECT column1, column2, COUNT(*) FROM table_name GROUP BY column1, column2 HAVING COUNT(*) > 1;", "query_type": "find_duplicates"},
    {"id": 26, "question_text": "Calculate moving average over a window of records", "sql_query": "SELECT date_column, value, AVG(value) OVER (ORDER BY date_column ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg FROM table_name;", "query_type": "moving_average"},
    {"id": 27, "question_text": "Combine results from multiple queries", "sql_query": "SELECT column1 FROM table_a UNION SELECT column1 FROM table_b;", "query_type": "union"},
    {"id": 28, "question_text": "Combine results including duplicates", "sql_query": "SELECT column1 FROM table_a UNION ALL SELECT column1 FROM table_b;", "query_type": "union_all"},
    {"id": 29, "question_text": "Extract year from a date column", "sql_query": "SELECT EXTRACT(YEAR FROM date_column) AS year, COUNT(*) FROM table_name GROUP BY EXTRACT(YEAR FROM date_column);", "query_type": "date_extraction"},
    {"id": 30, "question_text": "Calculate difference between current and previous row values", "sql_query": "SELECT date_column, value, value - LAG(value) OVER (ORDER BY date_column) AS difference FROM table_name;", "query_type": "lag_function"},
    {"id": 31, "question_text": "Find the most recent record for each group", "sql_query": "SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY group_id ORDER BY date_column DESC) AS rn FROM table_name) sub WHERE rn = 1;", "query_type": "latest_record_per_group"},
    {"id": 32, "question_text": "Calculate median value of a numeric column", "sql_query": "SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY numeric_column) AS median FROM table_name;", "query_type": "median"},
    {"id": 33, "question_text": "Split a string column into multiple parts", "sql_query": "SELECT SPLIT_PART(string_column, delimiter, 1) AS part1, SPLIT_PART(string_column, delimiter, 2) AS part2 FROM table_name;", "query_type": "string_split"},
    {"id": 34, "question_text": "Concatenate multiple columns into one", "sql_query": "SELECT CONCAT(first_name, ' ', last_name) AS full_name FROM table_name;", "query_type": "string_concatenation"},
    {"id": 35, "question_text": "Filter records using pattern matching", "sql_query": "SELECT * FROM table_name WHERE column_name LIKE '%pattern%';", "query_type": "pattern_matching"},
    {"id": 36, "question_text": "Filter records using regular expressions", "sql_query": "SELECT * FROM table_name WHERE column_name ~ 'regex_pattern';", "query_type": "regex_filter"},
    {"id": 37, "question_text": "Calculate year-over-year growth rate", "sql_query": "SELECT year, value, ROUND(100.0 * (value - LAG(value) OVER (ORDER BY year)) / LAG(value) OVER (ORDER BY year), 2) AS yoy_growth FROM table_name;", "query_type": "yoy_growth"},
    {"id": 38, "question_text": "Create a common table expression for reusable logic", "sql_query": "WITH cte AS (SELECT category, SUM(value) AS total FROM table_name GROUP BY category) SELECT * FROM cte WHERE total > threshold;", "query_type": "cte"},
    {"id": 39, "question_text": "Use multiple CTEs in a single query", "sql_query": "WITH cte1 AS (SELECT * FROM table_a), cte2 AS (SELECT * FROM table_b) SELECT * FROM cte1 JOIN cte2 ON cte1.id = cte2.id;", "query_type": "multiple_cte"},
    {"id": 40, "question_text": "Calculate the difference in days between two dates", "sql_query": "SELECT date_column1, date_column2, date_column2 - date_column1 AS days_diff FROM table_name;", "query_type": "date_difference"},
    {"id": 41, "question_text": "Round numeric values to specific decimal places", "sql_query": "SELECT ROUND(numeric_column, 2) AS rounded_value FROM table_name;", "query_type": "numeric_rounding"},
    {"id": 42, "question_text": "Convert column values to uppercase", "sql_query": "SELECT UPPER(text_column) AS uppercase_text FROM table_name;", "query_type": "text_uppercase"},
    {"id": 43, "question_text": "Trim whitespace from text columns", "sql_query": "SELECT TRIM(text_column) AS trimmed_text FROM table_name;", "query_type": "text_trim"},
    {"id": 44, "question_text": "Find records where a column is null", "sql_query": "SELECT * FROM table_name WHERE column_name IS NULL;", "query_type": "null_check"},
    {"id": 45, "question_text": "Calculate standard deviation of a numeric column", "sql_query": "SELECT STDDEV(numeric_column) AS standard_deviation FROM table_name;", "query_type": "standard_deviation"},
    {"id": 46, "question_text": "Find the minimum and maximum values simultaneously", "sql_query": "SELECT MIN(numeric_column) AS min_value, MAX(numeric_column) AS max_value FROM table_name;", "query_type": "min_max"},
    {"id": 47, "question_text": "Use CASE expression for multiple conditions", "sql_query": "SELECT column_name, CASE WHEN value < 10 THEN 'Low' WHEN value BETWEEN 10 AND 50 THEN 'Medium' ELSE 'High' END AS category FROM table_name;", "query_type": "case_multiple"},
    {"id": 48, "question_text": "Calculate correlation between two numeric columns", "sql_query": "SELECT CORR(column1, column2) AS correlation FROM table_name;", "query_type": "correlation"},
    {"id": 49, "question_text": "Generate a sequence of numbers", "sql_query": "SELECT generate_series(1, 10) AS number;", "query_type": "generate_series"},
    {"id": 50, "question_text": "Create dense rank for records within groups", "sql_query": "SELECT category, value, DENSE_RANK() OVER (PARTITION BY category ORDER BY value DESC) AS dense_rank FROM table_name;", "query_type": "dense_rank"},
]


def _all_rows() -> list[dict]:
    baseline_rows = [
        {"id": i, **row} for i, row in enumerate(_BASELINE, start=1)
    ]
    return baseline_rows + _APPEND


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


def main() -> None:
    rows = _all_rows()
    insert_sql = text("""
        INSERT INTO system_schema.few_shot_examples (id, question_text, sql_query, query_type)
        VALUES (:id, :question_text, :sql_query, :query_type)
        ON CONFLICT (id) DO NOTHING
    """)
    setval_sql = text("""
        SELECT setval(
            pg_get_serial_sequence('system_schema.few_shot_examples', 'id'),
            COALESCE((SELECT MAX(id) FROM system_schema.few_shot_examples), 1),
            true
        )
    """)
    engine = get_engine()
    inserted = 0
    with engine.begin() as conn:
        for ex in rows:
            result = conn.execute(
                insert_sql,
                {
                    "id": ex["id"],
                    "question_text": ex["question_text"],
                    "sql_query": ex["sql_query"],
                    "query_type": ex["query_type"],
                },
            )
            if result.rowcount and result.rowcount > 0:
                inserted += 1
        conn.execute(setval_sql)
    print(
        f"Upserted catalog: attempted {len(rows)} row(s); "
        f"{inserted} new insert(s) into system_schema.few_shot_examples "
        f"(conflicts skipped). Sequence synced to MAX(id)."
    )


if __name__ == "__main__":
    main()
