"""
Rule-based validation for generated SQL (Gen-SQL pipeline).

Goals:
- Single read-oriented statement (SELECT or WITH ... SELECT; optional EXPLAIN prefix).
- Reject obvious DML/DDL/session/control keywords via bounded scan (not a full SQL parser).
- Optional: referenced schema.table in FROM/JOIN must be subset of selected_tables when provided.

Returns a flat dict suitable for API and DB columns (bools + strings).
"""

from __future__ import annotations

import re
from typing import Any

# Whole-word matches on a comment-stripped, uppercased scan string.
_FORBIDDEN_RE = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|MERGE|TRUNCATE|"
    r"DROP|CREATE|ALTER|RENAME|REPLACE|"
    r"GRANT|REVOKE|COPY|"
    r"CALL|EXECUTE|EXEC|"
    r"LISTEN|NOTIFY|LOAD|CLUSTER|"
    r"VACUUM|REINDEX|REFRESH\s+MATERIALIZED\s+VIEW|"
    r"DISCARD|RESET\b"
    r")\b",
    re.IGNORECASE,
)

# SELECT INTO ... TABLE is DDL-like; allow plain INTO in SELECT lists only when not this pattern.
_SELECT_INTO_TABLE_RE = re.compile(
    r"\bINTO\s+(TEMPORARY|TEMP|UNLOGGED|TABLE)\b",
    re.IGNORECASE,
)

_FROM_JOIN_TABLE_RE = re.compile(
    r"(?:\bFROM|\bJOIN)\s+([a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*)\b",
    re.IGNORECASE,
)


def _mask_single_quoted_strings(sql: str) -> str:
    """
    Replace characters inside single-quoted string literals with spaces
    (PostgreSQL-style '' escape). Reduces false positives when scanning for keywords.
    """
    out: list[str] = []
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if ch != "'":
            out.append(ch)
            i += 1
            continue
        out.append("'")
        i += 1
        while i < n:
            if sql[i] == "'":
                if i + 1 < n and sql[i + 1] == "'":
                    out.append("''")
                    i += 2
                    continue
                out.append("'")
                i += 1
                break
            out.append(" ")
            i += 1
    return "".join(out)


def _strip_sql_comments(sql: str) -> str:
    """Remove /* */ and -- line comments (best-effort; does not handle quotes inside comments)."""
    s = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    lines: list[str] = []
    for line in s.splitlines():
        lines.append(line.split("--", 1)[0])
    return " ".join(lines)


def _trim_trailing_semicolons(sql: str) -> str:
    s = sql.strip()
    while s.endswith(";"):
        s = s[:-1].strip()
    return s


def _is_single_statement(sql: str) -> bool:
    s = _mask_single_quoted_strings(_strip_sql_comments(sql))
    s = _trim_trailing_semicolons(s)
    return ";" not in s


def _starts_with_select_family(sql: str) -> bool:
    """
    True if SQL (after comments) begins with EXPLAIN?, then WITH or SELECT.

    EXPLAIN options are stripped explicitly so ``EXPLAIN ANALYZE SELECT`` does not
    treat the main ``SELECT`` as an EXPLAIN keyword (``(\\s+\\w+)+`` would consume it).
    """
    head = _mask_single_quoted_strings(_strip_sql_comments(sql))
    head = head.strip()
    if re.match(r"^\s*EXPLAIN\b", head, re.IGNORECASE):
        head = re.sub(r"^\s*EXPLAIN\s+", "", head, count=1, flags=re.IGNORECASE).lstrip()
        # Known EXPLAIN / planner tokens only (repeat until none match).
        explain_opt = re.compile(
            r"^\s*("
            r"ANALYZE|VERBOSE|BUFFERS|TIMING|SUMMARY|WAL|SETTINGS|COSTS|"
            r"FORMAT\s+\w+"
            r")\s+",
            re.IGNORECASE,
        )
        while True:
            m = explain_opt.match(head)
            if not m:
                break
            head = head[m.end() :].lstrip()
    return bool(re.match(r"^\s*(WITH|SELECT)\b", head, re.IGNORECASE))


def _forbidden_hits(scan_upper: str) -> list[str]:
    hits: list[str] = []
    for m in _FORBIDDEN_RE.finditer(scan_upper):
        kw = re.sub(r"\s+", " ", m.group(1).upper()).strip()
        if kw not in hits:
            hits.append(kw)
    return hits


def _referenced_fqns_from_from_join(sql: str) -> list[str]:
    """Extract schema.table tokens immediately after FROM or JOIN (best-effort)."""
    s = _mask_single_quoted_strings(_strip_sql_comments(sql))
    found: list[str] = []
    seen: set[str] = set()
    for m in _FROM_JOIN_TABLE_RE.finditer(s):
        fqn = m.group(1).lower()
        if fqn not in seen:
            seen.add(fqn)
            found.append(fqn)
    return found


def validate_generated_sql(
    sql: str | None,
    *,
    selected_tables: list[str] | None = None,
    selected_columns: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """
    Validate generated SQL for safe single-statement read queries.

    selected_columns is accepted for API symmetry; table/column-level proof
    without a parser is noisy, so only selected_tables participates in subset checks.

    Returns dict keys:
      validation_passed (bool)
      validation_error_codes (str)
      validation_error_message (str)
      blocked_keywords (str)
      is_single_statement (bool)
      is_select_only (bool)
    """
    raw = (sql or "").strip()
    codes: list[str] = []
    messages: list[str] = []

    if not raw:
        return {
            "validation_passed": False,
            "validation_error_codes": "EMPTY_SQL",
            "validation_error_message": "Generated SQL is empty.",
            "blocked_keywords": "",
            "is_single_statement": False,
            "is_select_only": False,
        }

    single = _is_single_statement(raw)
    if not single:
        codes.append("MULTIPLE_STATEMENTS")
        messages.append("Multiple statements are not allowed (found ';').")

    scan = _mask_single_quoted_strings(_strip_sql_comments(raw))
    scan_upper = scan.upper()

    if _SELECT_INTO_TABLE_RE.search(scan_upper):
        codes.append("SELECT_INTO_DDL")
        messages.append("SELECT INTO / CREATE TABLE forms are not allowed.")

    forbidden = _forbidden_hits(scan_upper)
    blocked_csv = ", ".join(forbidden) if forbidden else ""
    if forbidden:
        codes.append("FORBIDDEN_KEYWORD")
        messages.append(f"Disallowed keyword(s): {blocked_csv}.")

    select_family = _starts_with_select_family(raw)
    if not select_family:
        codes.append("NOT_SELECT")
        messages.append("Query must start with SELECT or WITH (optional EXPLAIN prefix).")

    # Optional: FROM/JOIN schema.table must be in selected_tables (lowercased set).
    if selected_tables:
        allowed = {t.strip().lower() for t in selected_tables if t and str(t).strip()}
        if allowed:
            refs = _referenced_fqns_from_from_join(raw)
            unknown = [r for r in refs if r not in allowed]
            if unknown:
                codes.append("TABLE_NOT_IN_SELECTION")
                messages.append(
                    "FROM/JOIN references table(s) not in the selected table list: "
                    + ", ".join(unknown)
                )

    # selected_columns reserved for future stricter checks
    _ = selected_columns

    passed = not codes
    select_into_hit = bool(_SELECT_INTO_TABLE_RE.search(scan_upper))
    is_select_shape = (
        single
        and select_family
        and not forbidden
        and not select_into_hit
    )
    return {
        "validation_passed": passed,
        "validation_error_codes": ";".join(codes) if codes else "",
        "validation_error_message": " ".join(messages).strip() if messages else "",
        "blocked_keywords": blocked_csv,
        "is_single_statement": single,
        "is_select_only": is_select_shape,
    }
