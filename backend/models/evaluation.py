"""
Evaluation model — CRUD for evaluations table.
"""
from __future__ import annotations

import sqlite3

from backend.database import now_iso


def list_evaluations(
    conn: sqlite3.Connection,
    class_clause: str,
    class_params: list,
) -> list[dict]:
    rows = conn.execute(f"""
        SELECT e.id, e.courseware_id, e.student_id, e.helpfulness, e.usability,
               e.suitability, e.practicality, e.suggestion, e.created_at,
               u.display_name AS student_name,
               c.title AS courseware_title
        FROM evaluations e
        JOIN users u ON u.id = e.student_id
        JOIN coursewares c ON c.id = e.courseware_id
        WHERE c.class_id IN (
            SELECT id FROM classes WHERE {class_clause}
        )
        ORDER BY e.created_at DESC
    """, class_params).fetchall()
    return [dict(r) for r in rows]


def create_evaluation(
    conn: sqlite3.Connection,
    courseware_id: int,
    student_id: int,
    helpfulness: int,
    usability: int,
    suitability: int = 3,
    practicality: int = 3,
    suggestion: str = "",
) -> dict:
    conn.execute(
        "INSERT OR REPLACE INTO evaluations "
        "(courseware_id, student_id, helpfulness, usability, suitability, practicality, suggestion, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (courseware_id, student_id, helpfulness, usability, suitability, practicality, suggestion.strip(), now_iso()),
    )
    conn.commit()
    return {"message": "评价已提交。"}


def get_user_evaluation(conn: sqlite3.Connection, courseware_id: int, student_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM evaluations WHERE courseware_id = ? AND student_id = ?",
        (courseware_id, student_id),
    ).fetchone()
    return dict(row) if row else None
