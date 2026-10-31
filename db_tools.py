"""Database tools the agent may call. Everything here is read-only by design.

Defense in depth (any one of these would stop a write on its own):
  1. The connection is opened read-only (SQLite URI mode=ro).
  2. A SQLite authorizer allows only SELECT-type operations.
  3. A text check rejects anything that is not a single SELECT/WITH statement.
  4. A row limit and a time limit stop runaway queries.
"""
import re
import sqlite3
import time

DB_PATH = "university.db"
MAX_ROWS = 200
MAX_SECONDS = 3.0

_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
                    sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|replace|attach|detach|pragma|vacuum|reindex)\b",
    re.IGNORECASE)


class QueryRejected(Exception):
    """Raised when a query breaks a safety rule. The message is safe to show the model."""


def _authorizer(action, arg1, arg2, db_name, source):
    return sqlite3.SQLITE_OK if action in _ALLOWED_ACTIONS else sqlite3.SQLITE_DENY


def _connect():
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.set_authorizer(_authorizer)
    return con


def get_schema() -> dict:
    """Return tables, columns, and a few sample rows so the model knows what exists."""
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)  # unrestricted reads for schema only
    schema = {}
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        cols = [{"name": r[1], "type": r[2]} for r in con.execute(f"PRAGMA table_info({table})")]
        sample = [list(r) for r in con.execute(f"SELECT * FROM {table} LIMIT 2")]
        schema[table] = {"columns": cols, "sample_rows": sample}
    con.close()
    return schema


def check_sql(sql: str) -> str:
    """Return a cleaned single statement or raise QueryRejected."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        raise QueryRejected("Empty query.")
    if ";" in cleaned:
        raise QueryRejected("Only one SQL statement is allowed.")
    if not re.match(r"^(select|with)\b", cleaned, re.IGNORECASE):
        raise QueryRejected("Only SELECT queries are allowed.")
    if _FORBIDDEN.search(cleaned):
        raise QueryRejected("Query contains a forbidden keyword. Only read-only SELECT queries are allowed.")
    return cleaned


def run_query(sql: str) -> dict:
    """Run a guarded, read-only query. Returns columns, rows, and whether rows were cut off."""
    cleaned = check_sql(sql)
    con = _connect()
    start = time.monotonic()

    def too_slow():
        return 1 if time.monotonic() - start > MAX_SECONDS else 0

    con.set_progress_handler(too_slow, 10000)
    try:
        cur = con.execute(cleaned)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS + 1)
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e).lower():
            raise QueryRejected(f"Query took longer than {MAX_SECONDS} seconds and was stopped.")
        raise QueryRejected(f"SQL error: {e}")
    except sqlite3.DatabaseError as e:
        raise QueryRejected(f"Query not permitted: {e}")
    finally:
        con.close()
    truncated = len(rows) > MAX_ROWS
    return {"columns": columns, "rows": [list(r) for r in rows[:MAX_ROWS]], "truncated": truncated}
