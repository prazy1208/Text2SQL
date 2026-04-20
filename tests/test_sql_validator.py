"""Unit tests for backend.services.sql_validator."""

import pytest

from backend.services.sql_validator import validate_generated_sql


def test_empty_sql_fails():
    r = validate_generated_sql("")
    assert r["validation_passed"] is False
    assert "EMPTY_SQL" in r["validation_error_codes"]


def test_select_single_statement_passes():
    sql = "SELECT a FROM public.orders WHERE id = 1"
    r = validate_generated_sql(
        sql,
        selected_tables=["public.orders"],
    )
    assert r["validation_passed"] is True
    assert r["is_single_statement"] is True
    assert r["is_select_only"] is True


def test_with_select_passes():
    sql = "WITH x AS (SELECT 1 AS n) SELECT n FROM x"
    r = validate_generated_sql(sql, selected_tables=None)
    assert r["validation_passed"] is True


def test_explain_analyze_select_passes():
    sql = "EXPLAIN ANALYZE SELECT 1"
    r = validate_generated_sql(sql)
    assert r["validation_passed"] is True


def test_multiple_statements_fails():
    sql = "SELECT 1; SELECT 2"
    r = validate_generated_sql(sql)
    assert r["validation_passed"] is False
    assert "MULTIPLE_STATEMENTS" in r["validation_error_codes"]


@pytest.mark.parametrize(
    "snippet",
    [
        "INSERT INTO t VALUES (1)",
        "UPDATE t SET a = 1",
        "DELETE FROM t",
        "DROP TABLE t",
        "CREATE TABLE t (id int)",
        "TRUNCATE t",
    ],
)
def test_forbidden_keyword_fails(snippet):
    r = validate_generated_sql(snippet)
    assert r["validation_passed"] is False
    assert "FORBIDDEN_KEYWORD" in r["validation_error_codes"]
    assert r["blocked_keywords"]


def test_keyword_in_string_literal_ignored():
    sql = "SELECT 'DELETE' AS x FROM public.t"
    r = validate_generated_sql(sql, selected_tables=["public.t"])
    assert r["validation_passed"] is True


def test_select_into_temp_fails():
    sql = "SELECT 1 INTO TEMP foo"
    r = validate_generated_sql(sql)
    assert r["validation_passed"] is False
    assert "SELECT_INTO_DDL" in r["validation_error_codes"]


def test_table_not_in_selection_fails():
    sql = "SELECT 1 FROM other.orders"
    r = validate_generated_sql(
        sql,
        selected_tables=["public.orders"],
    )
    assert r["validation_passed"] is False
    assert "TABLE_NOT_IN_SELECTION" in r["validation_error_codes"]


def test_from_join_table_must_match_selected():
    sql = "SELECT 1 FROM retail.customers c JOIN retail.orders o ON c.id = o.customer_id"
    r = validate_generated_sql(
        sql,
        selected_tables=["retail.customers", "retail.orders"],
    )
    assert r["validation_passed"] is True
