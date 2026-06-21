"""
Access control helpers — class access checks and scope clause builder.
"""
from __future__ import annotations

import sqlite3


def user_can_access_class(conn: sqlite3.Connection, user: dict, class_id: int | None) -> bool:
    if not class_id:
        return False
    if user["role"] == "admin":
        return True
    if user["role"] == "teacher":
        row = conn.execute(
            "SELECT id FROM classes WHERE id = ? AND teacher_id = ?",
            (class_id, user["id"]),
        ).fetchone()
        if row:
            return True
    member = conn.execute(
        "SELECT 1 FROM class_members WHERE class_id = ? AND user_id = ?",
        (class_id, user["id"]),
    ).fetchone()
    return bool(member)


def user_can_manage_class(conn: sqlite3.Connection, user: dict, class_id: int) -> bool:
    if user["role"] == "admin":
        return True
    row = conn.execute(
        "SELECT id FROM classes WHERE id = ? AND teacher_id = ?",
        (class_id, user["id"]),
    ).fetchone()
    return bool(row)


def users_share_class(conn: sqlite3.Connection, user_a: int, user_b: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM class_members cm1 JOIN class_members cm2 ON cm2.class_id = cm1.class_id "
        "WHERE cm1.user_id = ? AND cm2.user_id = ? LIMIT 1",
        (user_a, user_b),
    ).fetchone()
    return bool(row)


def build_class_scope_clause(user: dict, class_id: int | None, column_name: str) -> tuple[str, list]:
    if class_id is not None:
        return f"{column_name} = ?", [class_id]
    if user["role"] == "admin":
        return "1 = 1", []
    if user["role"] == "teacher":
        return f"{column_name} IN (SELECT id FROM classes WHERE teacher_id = ?)", [user["id"]]
    return f"{column_name} IN (SELECT class_id FROM class_members WHERE user_id = ?)", [user["id"]]
