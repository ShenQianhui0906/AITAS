"""
User model — CRUD operations for the users table.
"""
from __future__ import annotations

import secrets
import sqlite3

from backend.database import now_iso, hash_password, verify_password, row_to_user


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_user(row) if row else None


def get_user_by_username(conn: sqlite3.Connection, username: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return row_to_user(row) if row else None


def get_user_by_token(conn: sqlite3.Connection, token: str) -> dict | None:
    row = conn.execute(
        "SELECT u.* FROM users u JOIN sessions s ON s.user_id = u.id WHERE s.token = ?",
        (token,),
    ).fetchone()
    return row_to_user(row) if row else None


def list_users(conn: sqlite3.Connection, role: str | None = None) -> list[dict]:
    if role:
        rows = conn.execute(
            "SELECT * FROM users WHERE role = ? ORDER BY created_at DESC, id DESC", (role,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC, id DESC").fetchall()
    return [row_to_user(r) for r in rows]


def create_user(
    conn: sqlite3.Connection,
    username: str,
    display_name: str,
    role: str,
    password: str,
    student_number: str | None = None,
) -> tuple[dict, str]:
    salt, password_hash = hash_password(password)
    cursor = conn.execute(
        "INSERT INTO users (username, display_name, role, student_number, salt, password_hash, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (username, display_name, role, student_number, salt, password_hash, now_iso()),
    )
    token = secrets.token_hex(24)
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, cursor.lastrowid, now_iso()),
    )
    user = get_user_by_id(conn, cursor.lastrowid)
    return user, token


def update_user(
    conn: sqlite3.Connection,
    user_id: int,
    username: str,
    display_name: str,
    role: str,
    student_number: str | None = None,
    password: str | None = None,
) -> dict | None:
    if password:
        salt, password_hash = hash_password(password)
        conn.execute(
            "UPDATE users SET username=?, display_name=?, role=?, student_number=?, salt=?, password_hash=? WHERE id=?",
            (username, display_name, role, student_number, salt, password_hash, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET username=?, display_name=?, role=?, student_number=? WHERE id=?",
            (username, display_name, role, student_number, user_id),
        )
    return get_user_by_id(conn, user_id)


def authenticate_user(conn: sqlite3.Connection, username: str, password: str) -> tuple[dict | None, str | None]:
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not row or not verify_password(password, row["salt"], row["password_hash"]):
        return None, None
    token = secrets.token_hex(24)
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, row["id"], now_iso()),
    )
    return row_to_user(row), token


def logout_user(conn: sqlite3.Connection, token: str):
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def delete_user(conn: sqlite3.Connection, user_id: int) -> dict:
    """Delete a user and all cascading data. Returns affected info."""
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return {"stored_file_names": [], "affected_user_ids": []}

    # Collect courseware files to delete
    courseware_rows = conn.execute(
        "SELECT stored_file_name FROM coursewares WHERE uploaded_by = ?", (user_id,)
    ).fetchall()
    stored_file_names = [r["stored_file_name"] for r in courseware_rows]
    assignment_file_rows = conn.execute(
        "SELECT f.stored_file_name FROM assignment_submission_files f "
        "JOIN assignment_submissions s ON s.id = f.submission_id "
        "WHERE s.student_id = ?",
        (user_id,),
    ).fetchall()
    assignment_file_names = [row["stored_file_name"] for row in assignment_file_rows]

    # Collect affected user IDs for notifications
    affected = set()

    # Collect discussion IDs to delete replies
    discussion_ids = [
        r["id"] for r in conn.execute(
            "SELECT id FROM discussions WHERE author_id = ?", (user_id,)
        ).fetchall()
    ]
    if discussion_ids:
        placeholders = ",".join("?" * len(discussion_ids))
        reply_rows = conn.execute(
            f"SELECT DISTINCT author_id FROM discussion_replies WHERE discussion_id IN ({placeholders})",
            discussion_ids,
        ).fetchall()
        affected.update(r["author_id"] for r in reply_rows)
        conn.execute(
            f"DELETE FROM discussion_replies WHERE discussion_id IN ({placeholders})", discussion_ids
        )

    # Collect affected users from conversations
    conv_rows = conn.execute(
        "SELECT DISTINCT user_one_id, user_two_id FROM conversation_threads "
        "WHERE user_one_id = ? OR user_two_id = ?",
        (user_id, user_id),
    ).fetchall()
    for r in conv_rows:
        if r["user_one_id"] != user_id:
            affected.add(r["user_one_id"])
        if r["user_two_id"] != user_id:
            affected.add(r["user_two_id"])

    # Delete all related records
    conn.execute("DELETE FROM class_join_requests WHERE student_id = ?", (user_id,))
    conn.execute("DELETE FROM class_join_requests WHERE reviewed_by = ?", (user_id,))

    # Remove from class memberships (affect classmates)
    member_rows = conn.execute(
        "SELECT DISTINCT cm2.user_id FROM class_members cm1 "
        "JOIN class_members cm2 ON cm2.class_id = cm1.class_id "
        "WHERE cm1.user_id = ? AND cm2.user_id != ?",
        (user_id, user_id),
    ).fetchall()
    affected.update(r["user_id"] for r in member_rows)
    conn.execute("DELETE FROM class_members WHERE user_id = ?", (user_id,))

    # Clear messages and conversations
    conn.execute("DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?", (user_id, user_id))
    conn.execute("DELETE FROM conversation_members WHERE user_id = ?", (user_id,))
    conn.execute(
        "DELETE FROM conversation_threads WHERE user_one_id = ? OR user_two_id = ?",
        (user_id, user_id),
    )

    # Delete user's content
    conn.execute("DELETE FROM evaluations WHERE student_id = ?", (user_id,))
    conn.execute("DELETE FROM ai_chat_messages WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM rag_chat_messages WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM agent_chat_messages WHERE user_id = ?", (user_id,))
    submission_ids = [
        row["id"] for row in conn.execute(
            "SELECT id FROM assignment_submissions WHERE student_id = ?",
            (user_id,),
        ).fetchall()
    ]
    for submission_id in submission_ids:
        conn.execute(
            "DELETE FROM assignment_ai_grading_records WHERE submission_id = ?",
            (submission_id,),
        )
        conn.execute(
            "DELETE FROM assignment_submission_files WHERE submission_id = ?",
            (submission_id,),
        )
    conn.execute("DELETE FROM assignment_submissions WHERE student_id = ?", (user_id,))
    conn.execute("UPDATE assignment_submissions SET graded_by = NULL WHERE graded_by = ?", (user_id,))
    conn.execute("DELETE FROM discussion_replies WHERE author_id = ?", (user_id,))
    conn.execute("DELETE FROM discussions WHERE author_id = ?", (user_id,))
    conn.execute("DELETE FROM coursewares WHERE uploaded_by = ?", (user_id,))
    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    return {
        "stored_file_names": stored_file_names,
        "assignment_file_names": assignment_file_names,
        "affected_user_ids": [uid for uid in affected if uid != user_id],
    }


def check_username_exists(conn: sqlite3.Connection, username: str, exclude_id: int | None = None) -> bool:
    if exclude_id:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ? AND id != ?", (username, exclude_id)
        ).fetchone()
    else:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    return bool(row)


def check_student_number_exists(conn: sqlite3.Connection, student_number: str, exclude_id: int | None = None) -> bool:
    if exclude_id:
        row = conn.execute(
            "SELECT id FROM users WHERE student_number = ? AND id != ?",
            (student_number, exclude_id),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM users WHERE student_number = ?", (student_number,)
        ).fetchone()
    return bool(row)
