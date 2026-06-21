"""
Class model — CRUD for classes, class_members, class_join_requests.
"""
from __future__ import annotations

import sqlite3

from backend.database import now_iso


def build_class_summary(conn: sqlite3.Connection, class_id: int) -> dict | None:
    row = conn.execute("""
        SELECT
            c.id, c.name, c.description, c.teacher_id, c.created_at,
            u.display_name AS teacher_name,
            (SELECT COUNT(*) FROM class_members cm
             JOIN users member_user ON member_user.id = cm.user_id
             WHERE cm.class_id = c.id AND member_user.role = 'student') AS student_count,
            (SELECT COUNT(*) FROM class_join_requests r
             WHERE r.class_id = c.id AND r.status = 'pending') AS pending_request_count
        FROM classes c
        JOIN users u ON u.id = c.teacher_id
        WHERE c.id = ?
    """, (class_id,)).fetchone()
    return dict(row) if row else None


def list_classes_for_user(conn: sqlite3.Connection, user: dict) -> list[dict]:
    if user["role"] == "admin":
        rows = conn.execute("SELECT id FROM classes ORDER BY created_at DESC, id DESC").fetchall()
    elif user["role"] == "teacher":
        rows = conn.execute(
            "SELECT id FROM classes WHERE teacher_id = ? ORDER BY created_at DESC, id DESC",
            (user["id"],),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT c.id FROM classes c JOIN class_members cm ON cm.class_id = c.id "
            "WHERE cm.user_id = ? ORDER BY c.created_at DESC, c.id DESC",
            (user["id"],),
        ).fetchall()

    classes = []
    for row in rows:
        item = build_class_summary(conn, row["id"])
        if item:
            item["is_owner"] = user["role"] == "admin" or item["teacher_id"] == user["id"]
            classes.append(item)
    return classes


def list_available_classes(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute("""
        SELECT c.id, r.id AS request_id, r.status AS join_request_status,
               r.requested_at, r.reviewed_at
        FROM classes c
        LEFT JOIN class_join_requests r ON r.class_id = c.id AND r.student_id = ? AND r.status != 'approved'
        WHERE c.id NOT IN (SELECT class_id FROM class_members WHERE user_id = ?)
        ORDER BY c.created_at DESC, c.id DESC
    """, (user_id, user_id)).fetchall()

    classes = []
    for row in rows:
        item = build_class_summary(conn, row["id"])
        if item:
            item["join_request_id"] = row["request_id"]
            item["join_request_status"] = row["join_request_status"]
            item["join_requested_at"] = row["requested_at"]
            item["join_reviewed_at"] = row["reviewed_at"]
            classes.append(item)
    return classes


def create_class(
    conn: sqlite3.Connection, name: str, description: str, teacher_id: int
) -> dict:
    cursor = conn.execute(
        "INSERT INTO classes (name, description, teacher_id, created_at) VALUES (?, ?, ?, ?)",
        (name, description, teacher_id, now_iso()),
    )
    class_id = cursor.lastrowid
    conn.execute(
        "INSERT OR IGNORE INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
        (class_id, teacher_id, now_iso()),
    )
    conn.commit()
    return build_class_summary(conn, class_id)


def update_class(
    conn: sqlite3.Connection, class_id: int, name: str, description: str, teacher_id: int | None = None
) -> dict | None:
    if teacher_id:
        conn.execute(
            "UPDATE classes SET name=?, description=?, teacher_id=? WHERE id=?",
            (name, description, teacher_id, class_id),
        )
    else:
        conn.execute(
            "UPDATE classes SET name=?, description=? WHERE id=?", (name, description, class_id)
        )
    conn.commit()
    return build_class_summary(conn, class_id)


def delete_class(conn: sqlite3.Connection, class_id: int) -> dict:
    """Delete a class and all cascading data. Returns affected info."""
    # Collect courseware files
    courseware_rows = conn.execute(
        "SELECT stored_file_name FROM coursewares WHERE class_id = ?", (class_id,)
    ).fetchall()
    stored_files = [r["stored_file_name"] for r in courseware_rows]

    # Collect affected users
    member_rows = conn.execute(
        "SELECT user_id FROM class_members WHERE class_id = ?", (class_id,)
    ).fetchall()
    affected_users = [r["user_id"] for r in member_rows]

    # Cascade delete
    conn.execute("DELETE FROM class_members WHERE class_id = ?", (class_id,))
    conn.execute("DELETE FROM class_join_requests WHERE class_id = ?", (class_id,))
    conn.execute("DELETE FROM rag_chat_messages WHERE class_id = ?", (class_id,))

    # Delete discussions and their replies
    discussion_rows = conn.execute(
        "SELECT id FROM discussions WHERE class_id = ?", (class_id,)
    ).fetchall()
    for d in discussion_rows:
        conn.execute("DELETE FROM discussion_replies WHERE discussion_id = ?", (d["id"],))
    conn.execute("DELETE FROM discussions WHERE class_id = ?", (class_id,))

    conn.execute("DELETE FROM coursewares WHERE class_id = ?", (class_id,))
    conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
    conn.commit()

    return {"stored_file_names": stored_files, "affected_user_ids": affected_users}


def get_class_members(conn: sqlite3.Connection, class_id: int) -> list[dict]:
    rows = conn.execute("""
        SELECT u.id, u.username, u.display_name, u.role, u.student_number, u.created_at,
               cm.joined_at
        FROM class_members cm
        JOIN users u ON u.id = cm.user_id
        WHERE cm.class_id = ?
        ORDER BY u.role, u.display_name
    """, (class_id,)).fetchall()
    return [
        {
            "id": r["id"], "username": r["username"], "display_name": r["display_name"],
            "role": r["role"], "student_number": r["student_number"],
            "created_at": r["created_at"], "joined_at": r["joined_at"],
        }
        for r in rows
    ]


def add_class_member(conn: sqlite3.Connection, class_id: int, user_id: int) -> bool:
    conn.execute(
        "INSERT OR IGNORE INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
        (class_id, user_id, now_iso()),
    )
    conn.execute(
        "DELETE FROM class_join_requests WHERE class_id = ? AND student_id = ?",
        (class_id, user_id),
    )
    conn.commit()
    return True


def remove_class_member(conn: sqlite3.Connection, class_id: int, user_id: int):
    conn.execute(
        "DELETE FROM class_members WHERE class_id = ? AND user_id = ?", (class_id, user_id)
    )
    conn.commit()


def request_join_class(conn: sqlite3.Connection, class_id: int, student_id: int) -> dict | None:
    existing = conn.execute(
        "SELECT id, status FROM class_join_requests WHERE class_id = ? AND student_id = ?",
        (class_id, student_id),
    ).fetchone()
    if existing and existing["status"] in ("pending", "approved"):
        return {"id": existing["id"], "status": existing["status"]}

    if existing:
        conn.execute(
            "UPDATE class_join_requests SET status='pending', requested_at=?, reviewed_at=NULL, reviewed_by=NULL "
            "WHERE id=?", (now_iso(), existing["id"])
        )
    else:
        conn.execute(
            "INSERT INTO class_join_requests (class_id, student_id, status, requested_at) "
            "VALUES (?, ?, 'pending', ?)",
            (class_id, student_id, now_iso()),
        )
    conn.commit()
    return None


def review_join_request(
    conn: sqlite3.Connection, request_id: int, decision: str, reviewer_id: int
) -> dict | None:
    req = conn.execute(
        "SELECT * FROM class_join_requests WHERE id = ?", (request_id,)
    ).fetchone()
    if not req or req["status"] != "pending":
        return None

    conn.execute(
        "UPDATE class_join_requests SET status=?, reviewed_at=?, reviewed_by=? WHERE id=?",
        (decision, now_iso(), reviewer_id, request_id),
    )
    if decision == "approved":
        conn.execute(
            "INSERT OR IGNORE INTO class_members (class_id, user_id, joined_at) VALUES (?, ?, ?)",
            (req["class_id"], req["student_id"], now_iso()),
        )
    conn.commit()
    return dict(req)
