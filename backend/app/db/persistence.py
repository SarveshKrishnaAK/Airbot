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
        conn.execute("PRAGMA foreign_keys = ON")
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
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                mode TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(email) REFERENCES users(email)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                conversation_id INTEGER,
                role TEXT NOT NULL,
                mode TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(email) REFERENCES users(email),
                FOREIGN KEY(conversation_id) REFERENCES chat_conversations(id)
            )
            """
        )
        existing_columns = conn.execute("PRAGMA table_info(chat_history)").fetchall()
        existing_column_names = {row["name"] for row in existing_columns}
        if "conversation_id" not in existing_column_names:
            conn.execute("ALTER TABLE chat_history ADD COLUMN conversation_id INTEGER")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_history_email_created ON chat_history(email, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_history_email_mode_conversation ON chat_history(email, mode, conversation_id, id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_conversations_email_mode_updated ON chat_conversations(email, mode, updated_at DESC)"
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


def _build_conversation_title(first_message: str) -> str:
    normalized = " ".join((first_message or "").strip().split())
    if not normalized:
        return "New Chat"
    if len(normalized) <= 80:
        return normalized
    return f"{normalized[:77]}..."


def create_conversation(email: str, mode: str, first_message: str) -> int:
    now = datetime.utcnow().isoformat()
    title = _build_conversation_title(first_message)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO chat_conversations(email, mode, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email, mode, title, now, now),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_conversation(email: str, conversation_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, email, mode, title, created_at, updated_at
            FROM chat_conversations
            WHERE email = ? AND id = ?
            """,
            (email, conversation_id),
        ).fetchone()
        return dict(row) if row else None


def list_conversations(email: str, mode: Optional[str] = None, limit: int = 50) -> list[dict]:
    safe_limit = max(1, min(limit, 200))
    with get_connection() as conn:
        if mode:
            rows = conn.execute(
                """
                SELECT id, mode, title, created_at, updated_at
                FROM chat_conversations
                WHERE email = ? AND mode = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (email, mode, safe_limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, mode, title, created_at, updated_at
                FROM chat_conversations
                WHERE email = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (email, safe_limit),
            ).fetchall()
    return [dict(row) for row in rows]


def touch_conversation(email: str, conversation_id: int) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE chat_conversations
            SET updated_at = ?
            WHERE email = ? AND id = ?
            """,
            (datetime.utcnow().isoformat(), email, conversation_id),
        )
        conn.commit()


def add_chat_message(
    email: str,
    role: str,
    mode: str,
    message: str,
    conversation_id: Optional[int] = None
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_history(email, conversation_id, role, mode, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email, conversation_id, role, mode, message, datetime.utcnow().isoformat()),
        )
        if conversation_id is not None:
            conn.execute(
                """
                UPDATE chat_conversations
                SET updated_at = ?
                WHERE email = ? AND id = ?
                """,
                (datetime.utcnow().isoformat(), email, conversation_id),
            )
        conn.commit()


def get_chat_history(email: str, limit: int = 50) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, mode, message, created_at, conversation_id
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


def get_conversation_history(email: str, conversation_id: int, limit: int = 200) -> list[dict]:
    safe_limit = max(1, min(limit, 500))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, mode, message, created_at, conversation_id
            FROM chat_history
            WHERE email = ? AND conversation_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (email, conversation_id, safe_limit),
        ).fetchall()
    result = [dict(row) for row in rows]
    result.reverse()
    return result
