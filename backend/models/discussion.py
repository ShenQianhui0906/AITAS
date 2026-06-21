"""
Discussion model — CRUD for discussions and discussion_replies.
"""
from __future__ import annotations

import sqlite3

from backend.database import now_iso


def list_discussions(
    conn: sqlite3.Connection,
    class_clause: str,
    class_params: list,
    class_id: int | None = None,
) -> list[dict]:
    rows = conn.execute(f"""
        SELECT d.id, d.title, d.body, d.author_id, d.created_at, d.class_id,
               u.display_name AS author_name,
               (SELECT COUNT(*) FROM discussion_replies WHERE discussion_id = d.id) AS reply_count
        FROM discussions d
        JOIN users u ON u.id = d.author_id
        WHERE {class_clause}
        ORDER BY d.created_at DESC
    """, class_params).fetchall()
    return [dict(r) for r in rows]


def get_discussion_detail(conn: sqlite3.Connection, discussion_id: int) -> dict | None:
    row = conn.execute("""
        SELECT d.id, d.title, d.body, d.author_id, d.created_at, d.class_id,
               u.display_name AS author_name
        FROM discussions d
        JOIN users u ON u.id = d.author_id
        WHERE d.id = ?
    """, (discussion_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["replies"] = list_replies(conn, discussion_id)
    return result


def list_replies(conn: sqlite3.Connection, discussion_id: int) -> list[dict]:
    rows = conn.execute("""
        SELECT r.id, r.discussion_id, r.body, r.author_id, r.created_at,
               u.display_name AS author_name
        FROM discussion_replies r
        JOIN users u ON u.id = r.author_id
        WHERE r.discussion_id = ?
        ORDER BY r.created_at ASC
    """, (discussion_id,)).fetchall()
    return [dict(r) for r in rows]


def create_discussion(
    conn: sqlite3.Connection, title: str, body: str, author_id: int, class_id: int
) -> dict:
    cursor = conn.execute(
        "INSERT INTO discussions (title, body, author_id, created_at, class_id) VALUES (?, ?, ?, ?, ?)",
        (title.strip(), body.strip(), author_id, now_iso(), class_id),
    )
    conn.commit()
    return get_discussion_detail(conn, cursor.lastrowid)


def create_reply(
    conn: sqlite3.Connection, discussion_id: int, body: str, author_id: int
) -> dict:
    cursor = conn.execute(
        "INSERT INTO discussion_replies (discussion_id, body, author_id, created_at) VALUES (?, ?, ?, ?)",
        (discussion_id, body.strip(), author_id, now_iso()),
    )
    conn.commit()
    row = conn.execute("""
        SELECT r.id, r.discussion_id, r.body, r.author_id, r.created_at,
               u.display_name AS author_name
        FROM discussion_replies r
        JOIN users u ON u.id = r.author_id
        WHERE r.id = ?
    """, (cursor.lastrowid,)).fetchone()
    return dict(row) if row else {}
