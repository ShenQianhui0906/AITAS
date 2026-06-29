"""Data access for assignments, submissions, attachments, and grading."""
from __future__ import annotations

import json
import sqlite3

from backend.database import now_iso


def _file_dict(row) -> dict:
    item = dict(row)
    item["url"] = f"/api/assignments/files/{item['id']}"
    item["is_inline"] = bool(item["is_inline"])
    return item


def list_submission_files(conn: sqlite3.Connection, submission_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, submission_id, original_file_name, stored_file_name, "
        "mime_type, file_size, is_inline, created_at "
        "FROM assignment_submission_files WHERE submission_id = ? ORDER BY id ASC",
        (submission_id,),
    ).fetchall()
    return [_file_dict(row) for row in rows]


def _submission_dict(conn: sqlite3.Connection, row) -> dict:
    item = dict(row)
    item["status"] = "graded" if item.get("graded_at") else "submitted"
    item["is_late"] = bool(
        item.get("due_at") and item.get("submitted_at") > item.get("due_at")
    )
    item["files"] = list_submission_files(conn, item["id"])
    item["ai_draft"] = get_ai_grading_draft(conn, item["id"])
    return item


def _rubric_dict(row) -> dict | None:
    if not row:
        return None
    item = dict(row)
    try:
        item["source_refs"] = json.loads(item.get("source_refs") or "[]")
    except (TypeError, json.JSONDecodeError):
        item["source_refs"] = []
    return item


def get_assignment_grading_rubric(
    conn: sqlite3.Connection, assignment_id: int
) -> dict | None:
    row = conn.execute(
        "SELECT id, assignment_id, content, source, source_refs, created_at, updated_at "
        "FROM assignment_grading_rubrics WHERE assignment_id = ?",
        (assignment_id,),
    ).fetchone()
    return _rubric_dict(row)


def save_assignment_grading_rubric(
    conn: sqlite3.Connection,
    assignment_id: int,
    content: str,
    source: str,
    source_refs: list | None = None,
) -> dict:
    current = now_iso()
    refs_json = json.dumps(source_refs or [], ensure_ascii=False)
    existing = conn.execute(
        "SELECT id FROM assignment_grading_rubrics WHERE assignment_id = ?",
        (assignment_id,),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE assignment_grading_rubrics SET content = ?, source = ?, "
            "source_refs = ?, updated_at = ? WHERE assignment_id = ?",
            (content, source, refs_json, current, assignment_id),
        )
    else:
        conn.execute(
            "INSERT INTO assignment_grading_rubrics "
            "(assignment_id, content, source, source_refs, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (assignment_id, content, source, refs_json, current, current),
        )
    return get_assignment_grading_rubric(conn, assignment_id)


def list_class_grading_history(
    conn: sqlite3.Connection, class_id: int, limit: int = 30
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT a.title AS assignment_title, a.description AS assignment_description,
               s.score, s.feedback, s.graded_at
        FROM assignment_submissions s
        JOIN assignments a ON a.id = s.assignment_id
        WHERE a.class_id = ? AND s.graded_at IS NOT NULL AND s.score IS NOT NULL
        ORDER BY s.graded_at DESC, s.id DESC
        LIMIT ?
        """,
        (class_id, limit),
    ).fetchall()
    return [dict(row) for row in rows]


def _ai_grading_dict(row) -> dict | None:
    return dict(row) if row else None


def get_ai_grading_draft(
    conn: sqlite3.Connection, submission_id: int
) -> dict | None:
    row = conn.execute(
        "SELECT id, submission_id, score, evaluation, evidence, feedback, "
        "rubric_snapshot, rubric_source, model_name, status, generated_at, resolved_at "
        "FROM assignment_ai_grading_records "
        "WHERE submission_id = ? AND status = 'draft' ORDER BY id DESC LIMIT 1",
        (submission_id,),
    ).fetchone()
    return _ai_grading_dict(row)


def save_ai_grading_draft(
    conn: sqlite3.Connection,
    submission_id: int,
    score: float,
    evaluation: str,
    evidence: str,
    feedback: str,
    rubric_snapshot: str,
    rubric_source: str,
    model_name: str,
) -> dict:
    current = now_iso()
    conn.execute(
        "UPDATE assignment_ai_grading_records SET status = 'discarded', resolved_at = ? "
        "WHERE submission_id = ? AND status = 'draft'",
        (current, submission_id),
    )
    cursor = conn.execute(
        "INSERT INTO assignment_ai_grading_records "
        "(submission_id, score, evaluation, evidence, feedback, rubric_snapshot, "
        "rubric_source, model_name, status, generated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)",
        (
            submission_id, score, evaluation, evidence, feedback,
            rubric_snapshot, rubric_source, model_name, current,
        ),
    )
    row = conn.execute(
        "SELECT * FROM assignment_ai_grading_records WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return _ai_grading_dict(row)


def discard_ai_grading_draft(
    conn: sqlite3.Connection, submission_id: int
) -> bool:
    cursor = conn.execute(
        "UPDATE assignment_ai_grading_records SET status = 'discarded', resolved_at = ? "
        "WHERE submission_id = ? AND status = 'draft'",
        (now_iso(), submission_id),
    )
    return cursor.rowcount > 0


def delete_submission_ai_grading_records(
    conn: sqlite3.Connection, submission_id: int
) -> None:
    conn.execute(
        "DELETE FROM assignment_ai_grading_records WHERE submission_id = ?",
        (submission_id,),
    )


def list_assignments(
    conn: sqlite3.Connection, class_id: int, user: dict
) -> list[dict]:
    if user["role"] in {"teacher", "admin"}:
        rows = conn.execute(
            """
            SELECT a.id, a.class_id, a.teacher_id, a.title, a.description,
                   a.due_at, a.created_at, a.updated_at,
                   u.display_name AS teacher_name,
                   (SELECT COUNT(*) FROM class_members cm
                    JOIN users su ON su.id = cm.user_id
                    WHERE cm.class_id = a.class_id AND su.role = 'student') AS student_count,
                   (SELECT COUNT(*) FROM assignment_submissions s
                    WHERE s.assignment_id = a.id) AS submission_count,
                   (SELECT COUNT(*) FROM assignment_submissions s
                    WHERE s.assignment_id = a.id AND s.graded_at IS NOT NULL) AS graded_count
            FROM assignments a
            JOIN users u ON u.id = a.teacher_id
            WHERE a.class_id = ?
            ORDER BY a.due_at ASC, a.id DESC
            """,
            (class_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    rows = conn.execute(
        """
        SELECT a.id, a.class_id, a.teacher_id, a.title, a.description,
               a.due_at, a.created_at, a.updated_at,
               u.display_name AS teacher_name,
               s.id AS submission_id, s.submitted_at, s.updated_at AS submission_updated_at,
               s.score, s.feedback, s.graded_at
        FROM assignments a
        JOIN users u ON u.id = a.teacher_id
        LEFT JOIN assignment_submissions s
          ON s.assignment_id = a.id AND s.student_id = ?
        WHERE a.class_id = ?
        ORDER BY a.due_at ASC, a.id DESC
        """,
        (user["id"], class_id),
    ).fetchall()
    assignments = []
    current = now_iso()
    for row in rows:
        item = dict(row)
        if item["submission_id"]:
            item["submission_status"] = "graded" if item["graded_at"] else "submitted"
            item["is_late"] = item["submitted_at"] > item["due_at"]
        else:
            item["submission_status"] = "pending"
            item["is_late"] = current > item["due_at"]
        assignments.append(item)
    return assignments


def get_assignment(conn: sqlite3.Connection, assignment_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT a.id, a.class_id, a.teacher_id, a.title, a.description,
               a.due_at, a.created_at, a.updated_at,
               u.display_name AS teacher_name, c.name AS class_name
        FROM assignments a
        JOIN users u ON u.id = a.teacher_id
        JOIN classes c ON c.id = a.class_id
        WHERE a.id = ?
        """,
        (assignment_id,),
    ).fetchone()
    return dict(row) if row else None


def get_submission(
    conn: sqlite3.Connection, submission_id: int
) -> dict | None:
    row = conn.execute(
        """
        SELECT s.id, s.assignment_id, s.student_id, s.content_html,
               s.submitted_at, s.updated_at, s.score, s.feedback,
               s.graded_at, s.graded_by, a.due_at,
               u.display_name AS student_name, u.student_number,
               grader.display_name AS grader_name
        FROM assignment_submissions s
        JOIN assignments a ON a.id = s.assignment_id
        JOIN users u ON u.id = s.student_id
        LEFT JOIN users grader ON grader.id = s.graded_by
        WHERE s.id = ?
        """,
        (submission_id,),
    ).fetchone()
    return _submission_dict(conn, row) if row else None


def get_student_submission(
    conn: sqlite3.Connection, assignment_id: int, student_id: int
) -> dict | None:
    row = conn.execute(
        "SELECT id FROM assignment_submissions "
        "WHERE assignment_id = ? AND student_id = ?",
        (assignment_id, student_id),
    ).fetchone()
    return get_submission(conn, row["id"]) if row else None


def list_assignment_submissions(
    conn: sqlite3.Connection, assignment_id: int
) -> list[dict]:
    rows = conn.execute(
        "SELECT id FROM assignment_submissions WHERE assignment_id = ? "
        "ORDER BY CASE WHEN graded_at IS NULL THEN 0 ELSE 1 END ASC, "
        "submitted_at DESC, id DESC",
        (assignment_id,),
    ).fetchall()
    return [get_submission(conn, row["id"]) for row in rows]


def create_assignment(
    conn: sqlite3.Connection,
    class_id: int,
    teacher_id: int,
    title: str,
    description: str,
    due_at: str,
) -> dict:
    created_at = now_iso()
    cursor = conn.execute(
        "INSERT INTO assignments "
        "(class_id, teacher_id, title, description, due_at, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (class_id, teacher_id, title, description, due_at, created_at, created_at),
    )
    return get_assignment(conn, cursor.lastrowid)


def ensure_submission(
    conn: sqlite3.Connection, assignment_id: int, student_id: int
) -> tuple[int, bool]:
    existing = conn.execute(
        "SELECT id, graded_at FROM assignment_submissions "
        "WHERE assignment_id = ? AND student_id = ?",
        (assignment_id, student_id),
    ).fetchone()
    if existing:
        if existing["graded_at"]:
            raise ValueError("该作业已经批改，不能再次提交。")
        return existing["id"], False

    created_at = now_iso()
    cursor = conn.execute(
        "INSERT INTO assignment_submissions "
        "(assignment_id, student_id, content_html, submitted_at, updated_at) "
        "VALUES (?, ?, '', ?, ?)",
        (assignment_id, student_id, created_at, created_at),
    )
    return cursor.lastrowid, True


def clear_submission_files(conn: sqlite3.Connection, submission_id: int) -> None:
    conn.execute(
        "DELETE FROM assignment_submission_files WHERE submission_id = ?",
        (submission_id,),
    )


def add_submission_file(
    conn: sqlite3.Connection,
    submission_id: int,
    original_file_name: str,
    stored_file_name: str,
    mime_type: str,
    file_size: int,
    is_inline: bool,
) -> dict:
    cursor = conn.execute(
        "INSERT INTO assignment_submission_files "
        "(submission_id, original_file_name, stored_file_name, mime_type, "
        "file_size, is_inline, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            submission_id, original_file_name, stored_file_name, mime_type,
            file_size, 1 if is_inline else 0, now_iso(),
        ),
    )
    row = conn.execute(
        "SELECT * FROM assignment_submission_files WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return _file_dict(row)


def finalize_submission(
    conn: sqlite3.Connection, submission_id: int, content_html: str
) -> dict:
    current = now_iso()
    delete_submission_ai_grading_records(conn, submission_id)
    conn.execute(
        "UPDATE assignment_submissions SET content_html = ?, submitted_at = ?, "
        "updated_at = ?, score = NULL, feedback = '', graded_at = NULL, graded_by = NULL "
        "WHERE id = ?",
        (content_html, current, current, submission_id),
    )
    return get_submission(conn, submission_id)


def grade_submission(
    conn: sqlite3.Connection,
    submission_id: int,
    grader_id: int,
    score: float,
    feedback: str,
) -> dict | None:
    current = now_iso()
    conn.execute(
        "UPDATE assignment_submissions SET score = ?, feedback = ?, "
        "graded_at = ?, graded_by = ? WHERE id = ?",
        (score, feedback, current, grader_id, submission_id),
    )
    conn.execute(
        "UPDATE assignment_ai_grading_records SET status = 'confirmed', resolved_at = ? "
        "WHERE submission_id = ? AND status = 'draft'",
        (current, submission_id),
    )
    return get_submission(conn, submission_id)


def delete_assignment_records(conn: sqlite3.Connection, assignment_id: int) -> None:
    submission_ids = [
        row["id"] for row in conn.execute(
            "SELECT id FROM assignment_submissions WHERE assignment_id = ?",
            (assignment_id,),
        ).fetchall()
    ]
    for submission_id in submission_ids:
        delete_submission_ai_grading_records(conn, submission_id)
        clear_submission_files(conn, submission_id)
    conn.execute(
        "DELETE FROM assignment_submissions WHERE assignment_id = ?",
        (assignment_id,),
    )
    conn.execute(
        "DELETE FROM assignment_grading_rubrics WHERE assignment_id = ?",
        (assignment_id,),
    )
    conn.execute("DELETE FROM assignments WHERE id = ?", (assignment_id,))


def get_submission_file(conn: sqlite3.Connection, file_id: int) -> dict | None:
    row = conn.execute(
        """
        SELECT f.id, f.submission_id, f.original_file_name, f.stored_file_name,
               f.mime_type, f.file_size, f.is_inline, f.created_at,
               s.student_id, s.assignment_id, a.class_id
        FROM assignment_submission_files f
        JOIN assignment_submissions s ON s.id = f.submission_id
        JOIN assignments a ON a.id = s.assignment_id
        WHERE f.id = ?
        """,
        (file_id,),
    ).fetchone()
    return dict(row) if row else None
