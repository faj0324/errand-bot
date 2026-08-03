"""SQLite storage for errand items."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).with_name("errands.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    text       TEXT    NOT NULL,
    category   TEXT    NOT NULL,
    deadline   TEXT,               -- ISO 8601, NULL if none mentioned
    created_at TEXT    NOT NULL,
    done       INTEGER NOT NULL DEFAULT 0,
    done_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_user_done ON items(user_id, done);
"""


@contextmanager
def connect(path=DB_PATH):
    """Open a connection, commit on success, and always close it.

    sqlite3's own `with` block commits but does *not* close, which leaks a
    file handle per call in a long-running process.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db(path=DB_PATH):
    with connect(path) as conn:
        conn.executescript(SCHEMA)


def add_item(user_id, text, category, deadline, now=None, path=DB_PATH):
    """Insert one item. `deadline` is a datetime or None. Returns the new row id."""
    now = now or datetime.now()
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO items (user_id, text, category, deadline, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                text,
                category,
                deadline.isoformat(timespec="minutes") if deadline else None,
                now.isoformat(timespec="seconds"),
            ),
        )
        return cur.lastrowid


def open_items(user_id, path=DB_PATH):
    """All not-yet-done items, oldest first."""
    with connect(path) as conn:
        return conn.execute(
            "SELECT * FROM items WHERE user_id = ? AND done = 0 ORDER BY id",
            (user_id,),
        ).fetchall()
