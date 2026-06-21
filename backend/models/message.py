"""
Message model — CRUD for messages, conversation_threads, conversation_members.
"""
from __future__ import annotations

import sqlite3

from backend.database import now_iso, normalize_user_pair


def get_or_create_thread(
    conn: sqlite3.Connection, user_a: int, user_b: int, visible_for_a: int = 1, visible_for_b: int = 1
) -> int:
    user_one, user_two = normalize_user_pair(user_a, user_b)
    row = conn.execute(
        "SELECT id FROM conversation_threads WHERE user_one_id = ? AND user_two_id = ?",
        (user_one, user_two),
    ).fetchone()
    if not row:
        cursor = conn.execute(
            "INSERT INTO conversation_threads (user_one_id, user_two_id, created_at, last_message_at) "
            "VALUES (?, ?, ?, ?)",
            (user_one, user_two, now_iso(), now_iso()),
        )
        thread_id = cursor.lastrowid
    else:
        thread_id = row["id"]

    conn.execute(
        "INSERT OR IGNORE INTO conversation_members (thread_id, user_id, visible, joined_at) VALUES (?, ?, ?, ?)",
        (thread_id, user_a, visible_for_a, now_iso()),
    )
    conn.execute(
        "INSERT OR IGNORE INTO conversation_members (thread_id, user_id, visible, joined_at) VALUES (?, ?, ?, ?)",
        (thread_id, user_b, visible_for_b, now_iso()),
    )
    return thread_id


def list_contacts(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """List all users the current user has messaged or shares a class with."""
    contact_ids = set()

    # Users from message threads
    msg_rows = conn.execute("""
        SELECT DISTINCT cm2.user_id
        FROM conversation_members cm1
        JOIN conversation_members cm2 ON cm2.thread_id = cm1.thread_id
        WHERE cm1.user_id = ? AND cm2.user_id != ? AND cm1.visible = 1 AND cm2.visible = 1
    """, (user_id, user_id)).fetchall()
    contact_ids.update(r["user_id"] for r in msg_rows)

    # Users from shared classes
    class_rows = conn.execute("""
        SELECT DISTINCT cm2.user_id
        FROM class_members cm1
        JOIN class_members cm2 ON cm2.class_id = cm1.class_id
        WHERE cm1.user_id = ? AND cm2.user_id != ?
    """, (user_id, user_id)).fetchall()
    contact_ids.update(r["user_id"] for r in class_rows)

    if not contact_ids:
        return []

    placeholders = ",".join("?" * len(contact_ids))
    rows = conn.execute(
        f"SELECT id, username, display_name, role, student_number FROM users WHERE id IN ({placeholders}) "
        "ORDER BY display_name",
        list(contact_ids),
    ).fetchall()
    return [dict(r) for r in rows]


def list_conversations(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute("""
        SELECT t.id AS thread_id, t.last_message_at,
               u.id AS other_user_id, u.username, u.display_name, u.role, u.student_number
        FROM conversation_threads t
        JOIN conversation_members cm ON cm.thread_id = t.id AND cm.user_id = ? AND cm.visible = 1
        JOIN conversation_members cm2 ON cm2.thread_id = t.id AND cm2.user_id != ?
        JOIN users u ON u.id = cm2.user_id
        ORDER BY t.last_message_at DESC
    """, (user_id, user_id)).fetchall()

    conversations = []
    for row in rows:
        item = dict(row)
        item["other_user"] = {
            "id": row["other_user_id"], "username": row["username"],
            "display_name": row["display_name"], "role": row["role"],
            "student_number": row["student_number"],
        }
        item["last_message"] = _get_last_message(conn, row["thread_id"])
        item["unread_count"] = _get_unread_count(conn, row["thread_id"], user_id)
        conversations.append(item)
    return conversations


def _get_last_message(conn: sqlite3.Connection, thread_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, sender_id, receiver_id, body, is_read, created_at "
        "FROM messages WHERE thread_id = ? ORDER BY id DESC LIMIT 1",
        (thread_id,),
    ).fetchone()
    return dict(row) if row else None


def _get_unread_count(conn: sqlite3.Connection, thread_id: int, user_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM messages WHERE thread_id = ? AND receiver_id = ? AND is_read = 0",
        (thread_id, user_id),
    ).fetchone()
    return row["count"] if row else 0


def list_thread_messages(conn: sqlite3.Connection, thread_id: int, user_id: int) -> list[dict]:
    rows = conn.execute("""
        SELECT id, sender_id, receiver_id, body, is_read, created_at
        FROM messages WHERE thread_id = ?
        ORDER BY id ASC
    """, (thread_id,)).fetchall()

    # Mark as read
    conn.execute(
        "UPDATE messages SET is_read = 1 WHERE thread_id = ? AND receiver_id = ? AND is_read = 0",
        (thread_id, user_id),
    )
    conn.commit()
    return [dict(r) for r in rows]


def send_message(
    conn: sqlite3.Connection, sender_id: int, receiver_id: int, body: str
) -> dict:
    thread_id = get_or_create_thread(conn, sender_id, receiver_id)

    cursor = conn.execute(
        "INSERT INTO messages (sender_id, receiver_id, body, is_read, created_at, thread_id) "
        "VALUES (?, ?, ?, 0, ?, ?)",
        (sender_id, receiver_id, body.strip(), now_iso(), thread_id),
    )
    conn.execute(
        "UPDATE conversation_threads SET last_message_at = ? WHERE id = ?",
        (now_iso(), thread_id),
    )
    conn.commit()

    row = conn.execute("SELECT * FROM messages WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def create_conversation(conn: sqlite3.Connection, user_a: int, user_b: int) -> int:
    return get_or_create_thread(conn, user_a, user_b)


def delete_conversation(conn: sqlite3.Connection, thread_id: int, user_id: int):
    conn.execute(
        "UPDATE conversation_members SET visible = 0 WHERE thread_id = ? AND user_id = ?",
        (thread_id, user_id),
    )
    conn.commit()


def get_unread_count(conn: sqlite3.Connection, user_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM messages WHERE receiver_id = ? AND is_read = 0",
        (user_id,),
    ).fetchone()
    return row["count"] if row else 0
