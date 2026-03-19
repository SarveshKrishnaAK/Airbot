import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from app.core.config import settings


def _get_db_path() -> str:
    return settings.SQLITE_DB_PATH


@contextmanager
def get_connection():
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def initialize_database() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                picture TEXT,
                is_member INTEGER NOT NULL DEFAULT 0,
                preferred_mode TEXT NOT NULL DEFAULT 'general_chat',
                created_at TEXT NOT NULL,
                last_login_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                role TEXT NOT NULL,
                mode TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(email) REFERENCES users(email)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_history_email_created ON chat_history(email, created_at)"
        )
        conn.commit()


def upsert_user(email: str, name: str, picture: Optional[str], is_member: bool) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users(email, name, picture, is_member, preferred_mode, created_at, last_login_at)
            VALUES (?, ?, ?, ?, 'general_chat', ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                name=excluded.name,
                picture=excluded.picture,
                is_member=excluded.is_member,
                last_login_at=excluded.last_login_at
            """,
            (email, name, picture, 1 if is_member else 0, now, now),
        )
        conn.commit()


def get_user(email: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if not row:
            return None
        return dict(row)


def set_member_status(email: str, is_member: bool) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_member = ? WHERE email = ?", (1 if is_member else 0, email))
        conn.commit()


def get_user_settings(email: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT preferred_mode, is_member FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not row:
            return None
        return dict(row)


def update_user_preferred_mode(email: str, preferred_mode: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE users SET preferred_mode = ? WHERE email = ?", (preferred_mode, email)
        )
        conn.commit()


def add_chat_message(email: str, role: str, mode: str, message: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_history(email, role, mode, message, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email, role, mode, message, datetime.utcnow().isoformat()),
        )
        conn.commit()


def get_chat_history(email: str, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, mode, message, created_at
            FROM chat_history
            WHERE email = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (email, limit),
        ).fetchall()

    result = [dict(row) for row in rows]
    result.reverse()
    return result
