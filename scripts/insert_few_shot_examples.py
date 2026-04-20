"""Insert 20 generic few-shot examples into system_schema.few_shot_examples.

Requires: scripts/create_system_schema_few_shot_examples.sql applied.
Run from project root: python scripts/insert_few_shot_examples.py
"""

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
