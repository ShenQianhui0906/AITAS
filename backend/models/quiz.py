"""智能测验模型 - QuizTemplate / QuizSubmission"""

import json
import sqlite3


def _loads_json(raw_value, fallback):
    try:
        return json.loads(raw_value or "")
    except (TypeError, json.JSONDecodeError):
        return fallback


def _submission_dict(row: sqlite3.Row | None) -> dict | None:
    if not row:
        return None
    item = dict(row)
    item["answers"] = _loads_json(item.get("answers_json"), [])
    item["details"] = _loads_json(item.get("ai_feedback"), [])
    if not isinstance(item["answers"], list):
        item["answers"] = []
    if not isinstance(item["details"], list):
        item["details"] = []
    return item


def create_template(conn: sqlite3.Connection, teacher_id: int, class_id: int,
                    title: str, questions: list, settings: dict | None = None) -> int:
    """创建测验模板（教师发布测验）"""
    conn.execute(
        """INSERT INTO quiz_templates (teacher_id, class_id, title, questions_json, is_published,
           created_at, updated_at)
           VALUES (?, ?, ?, ?, 1, datetime('now'), datetime('now'))""",
        (teacher_id, class_id, title, json.dumps(questions, ensure_ascii=False))
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_template(conn: sqlite3.Connection, quiz_id: int) -> dict | None:
    """获取单个测验模板"""
    row = conn.execute("SELECT * FROM quiz_templates WHERE id = ?", (quiz_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d['questions'] = json.loads(d.get('questions_json', '[]'))
    return d


def list_templates_by_class(conn: sqlite3.Connection, class_id: int) -> list[dict]:
    """列出某班级下所有测验模板"""
    rows = conn.execute(
        """SELECT qt.*, u.display_name as teacher_name,
                  (SELECT COUNT(*) FROM quiz_submissions qs
                   WHERE qs.quiz_id = qt.id) AS submission_count
           FROM quiz_templates qt
           LEFT JOIN users u ON qt.teacher_id = u.id
           WHERE qt.class_id = ?
           ORDER BY qt.created_at DESC""",
        (class_id,)
    ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d['questions'] = json.loads(d.get('questions_json', '[]'))
        result.append(d)
    return result


def list_templates_by_teacher(conn: sqlite3.Connection, teacher_id: int) -> list[dict]:
    """列出教师创建的所有测验"""
    rows = conn.execute(
        """SELECT qt.*, c.name as class_name,
                  (SELECT COUNT(*) FROM quiz_submissions qs
                   WHERE qs.quiz_id = qt.id) AS submission_count
           FROM quiz_templates qt
           LEFT JOIN classes c ON qt.class_id = c.id
           WHERE qt.teacher_id = ?
           ORDER BY qt.created_at DESC""",
        (teacher_id,)
    ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d['questions'] = json.loads(d.get('questions_json', '[]'))
        result.append(d)
    return result


def delete_template(conn: sqlite3.Connection, quiz_id: int) -> None:
    """删除测验模板及其所有提交"""
    conn.execute("DELETE FROM quiz_submissions WHERE quiz_id = ?", (quiz_id,))
    conn.execute("DELETE FROM quiz_templates WHERE id = ?", (quiz_id,))
    conn.commit()


# --- Submissions ---

def submit_answers(conn: sqlite3.Connection, quiz_id: int, student_id: int,
                   answers: list) -> int:
    """学生提交测验答案"""
    conn.execute(
        """INSERT INTO quiz_submissions (quiz_id, student_id, answers_json, submitted_at)
           VALUES (?, ?, ?, datetime('now'))""",
        (quiz_id, student_id, json.dumps(answers, ensure_ascii=False))
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_submission(conn: sqlite3.Connection, quiz_id: int, student_id: int) -> dict | None:
    """获取某学生对某测验的提交"""
    row = conn.execute(
        "SELECT * FROM quiz_submissions WHERE quiz_id = ? AND student_id = ?",
        (quiz_id, student_id)
    ).fetchone()
    return _submission_dict(row)


def get_submission_by_id(conn: sqlite3.Connection, submission_id: int) -> dict | None:
    """按提交编号获取一份答卷。"""
    row = conn.execute(
        "SELECT * FROM quiz_submissions WHERE id = ?", (submission_id,)
    ).fetchone()
    return _submission_dict(row)


def list_submissions(conn: sqlite3.Connection, quiz_id: int) -> list[dict]:
    """列出某测验所有提交（含学生信息）"""
    rows = conn.execute(
        """SELECT qs.*, u.display_name as student_name, u.student_number as student_code
           FROM quiz_submissions qs
           LEFT JOIN users u ON qs.student_id = u.id
           WHERE qs.quiz_id = ?
           ORDER BY qs.submitted_at ASC""",
        (quiz_id,)
    ).fetchall()
    result = []
    for row in rows:
        result.append(_submission_dict(row))
    return result


def grade_submission(conn: sqlite3.Connection, submission_id: int, score: float,
                     feedback: list | dict | None = None) -> None:
    """批改某份提交（自动评分）"""
    conn.execute(
        """UPDATE quiz_submissions
           SET score = ?, ai_feedback = ?, graded_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (score, json.dumps(feedback, ensure_ascii=False) if feedback else '{}',
         submission_id)
    )
    conn.commit()
