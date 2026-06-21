"""
AI Chat model — CRUD for ai_chat_messages and rag_chat_messages.
"""
from __future__ import annotations

import sqlite3

from backend.database import now_iso


# ---- AI Chat (per-courseware) ----

def list_ai_messages(
    conn: sqlite3.Connection, courseware_id: int, user_id: int, max_messages: int = 50
) -> list[dict]:
    rows = conn.execute(
        "SELECT id, courseware_id, user_id, role, content, created_at "
        "FROM ai_chat_messages WHERE courseware_id = ? AND user_id = ? "
        "ORDER BY id ASC LIMIT ?",
        (courseware_id, user_id, max_messages),
    ).fetchall()
    return [dict(r) for r in rows]


def add_ai_message(
    conn: sqlite3.Connection, courseware_id: int, user_id: int, role: str, content: str
) -> dict:
    cursor = conn.execute(
        "INSERT INTO ai_chat_messages (courseware_id, user_id, role, content, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (courseware_id, user_id, role, content, now_iso()),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM ai_chat_messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def clear_ai_messages(conn: sqlite3.Connection, courseware_id: int, user_id: int):
    conn.execute(
        "DELETE FROM ai_chat_messages WHERE courseware_id = ? AND user_id = ?",
        (courseware_id, user_id),
    )
    conn.commit()


# ---- RAG Chat (per-class) ----

def list_rag_messages(
    conn: sqlite3.Connection, class_id: int, user_id: int, max_messages: int = 50
) -> list[dict]:
    rows = conn.execute(
        "SELECT id, class_id, user_id, role, content, sources, created_at "
        "FROM rag_chat_messages WHERE class_id = ? AND user_id = ? "
        "ORDER BY id ASC LIMIT ?",
        (class_id, user_id, max_messages),
    ).fetchall()
    return [dict(r) for r in rows]


def add_rag_message(
    conn: sqlite3.Connection, class_id: int, user_id: int, role: str, content: str, sources: str = "[]"
) -> dict:
    cursor = conn.execute(
        "INSERT INTO rag_chat_messages (class_id, user_id, role, content, sources, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (class_id, user_id, role, content, sources, now_iso()),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM rag_chat_messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def clear_rag_messages(conn: sqlite3.Connection, class_id: int, user_id: int):
    conn.execute(
        "DELETE FROM rag_chat_messages WHERE class_id = ? AND user_id = ?",
        (class_id, user_id),
    )
    conn.commit()
