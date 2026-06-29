"""
Dashboard Blueprint — /api/dashboard
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, g

from backend.database import get_conn
from backend.middleware.auth import require_auth

dashboard_bp = Blueprint("dashboard", __name__)


def _teacher_insights(conn, class_ids: list[int], placeholders: str) -> dict:
    assignment_count = conn.execute(
        f"SELECT COUNT(*) FROM assignments WHERE class_id IN ({placeholders})",
        class_ids,
    ).fetchone()[0]
    student_count = conn.execute(
        f"SELECT COUNT(DISTINCT cm.user_id) FROM class_members cm "
        f"JOIN users u ON u.id = cm.user_id "
        f"WHERE cm.class_id IN ({placeholders}) AND u.role = 'student'",
        class_ids,
    ).fetchone()[0]
    expected_submissions = conn.execute(
        f"""
        SELECT COALESCE(SUM((
            SELECT COUNT(*) FROM class_members cm
            JOIN users u ON u.id = cm.user_id
            WHERE cm.class_id = a.class_id AND u.role = 'student'
        )), 0)
        FROM assignments a
        WHERE a.class_id IN ({placeholders})
        """,
        class_ids,
    ).fetchone()[0]
    submitted_count = conn.execute(
        f"SELECT COUNT(*) FROM assignment_submissions s "
        f"JOIN assignments a ON a.id = s.assignment_id "
        f"WHERE a.class_id IN ({placeholders})",
        class_ids,
    ).fetchone()[0]
    graded_count = conn.execute(
        f"SELECT COUNT(*) FROM assignment_submissions s "
        f"JOIN assignments a ON a.id = s.assignment_id "
        f"WHERE a.class_id IN ({placeholders}) AND s.graded_at IS NOT NULL",
        class_ids,
    ).fetchone()[0]
    pending_count = max(int(expected_submissions) - int(submitted_count), 0)
    completion_rate = round(
        submitted_count * 100 / expected_submissions
    ) if expected_submissions else 0
    grading_rate = round(
        graded_count * 100 / submitted_count
    ) if submitted_count else 0

    progress_rows = conn.execute(
        f"""
        SELECT u.id, u.display_name, u.student_number,
               COUNT(DISTINCT a.id) AS assignment_count,
               COUNT(DISTINCT s.assignment_id) AS submitted_count,
               COUNT(DISTINCT CASE WHEN s.graded_at IS NOT NULL THEN s.assignment_id END)
                   AS graded_count,
               AVG(CASE WHEN s.graded_at IS NOT NULL THEN s.score END) AS average_score
        FROM class_members cm
        JOIN users u ON u.id = cm.user_id
        LEFT JOIN assignments a ON a.class_id = cm.class_id
        LEFT JOIN assignment_submissions s
          ON s.assignment_id = a.id AND s.student_id = u.id
        WHERE cm.class_id IN ({placeholders}) AND u.role = 'student'
        GROUP BY u.id, u.display_name, u.student_number
        ORDER BY
          CASE WHEN COUNT(DISTINCT a.id) = 0 THEN 0
               ELSE CAST(COUNT(DISTINCT s.assignment_id) AS REAL)
                    / COUNT(DISTINCT a.id) END ASC,
          u.display_name ASC
        LIMIT 8
        """,
        class_ids,
    ).fetchall()
    student_progress = []
    for row in progress_rows:
        item = dict(row)
        total = item["assignment_count"] or 0
        submitted = item["submitted_count"] or 0
        item["completion_rate"] = round(submitted * 100 / total) if total else 0
        if item["average_score"] is not None:
            item["average_score"] = round(float(item["average_score"]), 1)
        student_progress.append(item)

    feedback = conn.execute(
        f"""
        SELECT COUNT(*) AS response_count,
               AVG(e.helpfulness) AS helpfulness,
               AVG(e.usability) AS usability,
               AVG(e.suitability) AS suitability,
               AVG(e.practicality) AS practicality
        FROM evaluations e
        JOIN coursewares cw ON cw.id = e.courseware_id
        WHERE cw.class_id IN ({placeholders})
        """,
        class_ids,
    ).fetchone()
    feedback_dimensions = [
        {"key": key, "label": label, "value": round(float(feedback[key] or 0), 1)}
        for key, label in (
            ("helpfulness", "内容帮助度"),
            ("usability", "课件易用性"),
            ("suitability", "难度适配度"),
            ("practicality", "实践价值"),
        )
    ]

    return {
        "assignment_progress": {
            "assignment_count": assignment_count,
            "student_count": student_count,
            "expected_submissions": expected_submissions,
            "submitted_count": submitted_count,
            "graded_count": graded_count,
            "pending_count": pending_count,
            "completion_rate": completion_rate,
            "grading_rate": grading_rate,
        },
        "student_progress": student_progress,
        "feedback": {
            "response_count": feedback["response_count"] or 0,
            "dimensions": feedback_dimensions,
        },
    }


@dashboard_bp.route("/api/dashboard", methods=["GET"])
@require_auth
def dashboard():
    class_id = request.args.get("class_id", type=int)

    conn = get_conn()
    try:
        if g.current_user["role"] == "admin":
            stats = {
                "teachers": conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'teacher'"
                ).fetchone()[0],
                "students": conn.execute(
                    "SELECT COUNT(*) FROM users WHERE role = 'student'"
                ).fetchone()[0],
                "classes": conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0],
                "coursewares": conn.execute("SELECT COUNT(*) FROM coursewares").fetchone()[0],
            }
            return jsonify({"stats": stats}), 200

        if g.current_user["role"] == "teacher":
            classes = conn.execute(
                "SELECT id, name FROM classes WHERE teacher_id = ?", (g.current_user["id"],)
            ).fetchall()
        else:
            classes = conn.execute(
                "SELECT c.id, c.name FROM classes c JOIN class_members cm ON c.id = cm.class_id "
                "WHERE cm.user_id = ?", (g.current_user["id"],)
            ).fetchall()

        if not classes:
            return jsonify({"stats": {
                "coursewares": 0, "discussions": 0, "assignments": 0,
                "evaluations": 0, "unread_messages": 0,
            }}), 200

        if class_id is not None:
            classes = [c for c in classes if c["id"] == class_id]
            if not classes:
                return jsonify({"stats": {
                    "coursewares": 0, "discussions": 0, "assignments": 0,
                    "evaluations": 0, "unread_messages": 0,
                }}), 200

        class_ids = [c["id"] for c in classes]
        placeholders = ",".join("?" * len(class_ids))

        if g.current_user["role"] == "teacher":
            coursewares = conn.execute(
                f"SELECT COUNT(*) FROM coursewares WHERE class_id IN ({placeholders})",
                class_ids,
            ).fetchone()[0]
            evaluations = conn.execute(
                f"SELECT COUNT(*) FROM evaluations e JOIN coursewares cw ON e.courseware_id = cw.id "
                f"WHERE cw.class_id IN ({placeholders})",
                class_ids,
            ).fetchone()[0]
            discussions = conn.execute(
                f"SELECT COUNT(*) FROM discussions WHERE class_id IN ({placeholders})",
                class_ids,
            ).fetchone()[0]
            assignments = conn.execute(
                f"SELECT COUNT(*) FROM assignments WHERE class_id IN ({placeholders})",
                class_ids,
            ).fetchone()[0]
            insights = _teacher_insights(conn, class_ids, placeholders)
        else:
            coursewares = conn.execute(
                f"SELECT COUNT(*) FROM coursewares WHERE class_id IN ({placeholders})",
                class_ids,
            ).fetchone()[0]
            evaluations = conn.execute(
                f"SELECT COUNT(*) FROM evaluations e JOIN coursewares cw ON e.courseware_id = cw.id "
                f"WHERE e.student_id = ? AND cw.class_id IN ({placeholders})",
                (g.current_user["id"], *class_ids),
            ).fetchone()[0]
            discussions = conn.execute(
                f"SELECT COUNT(*) FROM discussions WHERE author_id = ? AND class_id IN ({placeholders})",
                (g.current_user["id"], *class_ids),
            ).fetchone()[0]
            assignments = conn.execute(
                f"SELECT COUNT(*) FROM assignments WHERE class_id IN ({placeholders})",
                class_ids,
            ).fetchone()[0]
            insights = None

        unread_messages = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE receiver_id = ? AND is_read = 0",
            (g.current_user["id"],),
        ).fetchone()[0]

        # --- 测验统计 ---
        quiz_count = 0
        quiz_avg_score = 0
        knowledge_gaps = []
        activity_trend = []
        if g.current_user["role"] == "teacher":
            quiz_count = conn.execute(
                f"SELECT COUNT(*) FROM quiz_templates WHERE class_id IN ({placeholders})",
                class_ids,
            ).fetchone()[0]
            quiz_rows = conn.execute(
                f"""SELECT AVG(qs.score * 1.0) as avg_score
                    FROM quiz_submissions qs
                    JOIN quiz_templates qt ON qs.quiz_id = qt.id
                    WHERE qt.class_id IN ({placeholders}) AND qs.score IS NOT NULL""",
                class_ids,
            ).fetchone()
            quiz_avg_score = round(float(quiz_rows[0] or 0), 1)

            # 知识薄弱点：从测验提交中找出低分题目
            gap_rows = conn.execute(
                f"""SELECT qt.title as quiz_title, qs.answers_json, qs.score, qt.questions_json, qs.id
                    FROM quiz_submissions qs
                    JOIN quiz_templates qt ON qs.quiz_id = qt.id
                    WHERE qt.class_id IN ({placeholders}) AND qs.score IS NOT NULL
                    ORDER BY qs.submitted_at DESC
                    LIMIT 30""",
                class_ids,
            ).fetchall()
            knowledge_gaps = _analyze_knowledge_gaps(gap_rows)

            # 活动趋势：最近14天每日活动统计
            trend_rows = conn.execute(
                f"""SELECT DATE(created_at) as dt, COUNT(*) as cnt, 'assignment' as kind
                    FROM assignments WHERE class_id IN ({placeholders})
                    AND created_at >= DATE('now', '-14 days')
                    GROUP BY dt
                    UNION ALL
                    SELECT DATE(created_at) as dt, COUNT(*) as cnt, 'quiz' as kind
                    FROM quiz_templates WHERE class_id IN ({placeholders})
                    AND created_at >= DATE('now', '-14 days')
                    GROUP BY dt
                    UNION ALL
                    SELECT DATE(submitted_at) as dt, COUNT(*) as cnt, 'submission' as kind
                    FROM quiz_submissions qs
                    JOIN quiz_templates qt ON qs.quiz_id = qt.id
                    WHERE qt.class_id IN ({placeholders})
                    AND qs.submitted_at >= DATE('now', '-14 days')
                    GROUP BY dt
                    ORDER BY dt ASC""",
                class_ids * 3,
            ).fetchall()
            activity_trend = _build_trend(trend_rows)

        payload = {"stats": {
            "coursewares": coursewares,
            "evaluations": evaluations,
            "discussions": discussions,
            "assignments": assignments,
            "quizzes": quiz_count,
            "unread_messages": unread_messages,
        }}
        if insights is not None:
            payload["insights"] = insights
            payload["insights"]["quiz_avg_score"] = quiz_avg_score
            payload["insights"]["knowledge_gaps"] = knowledge_gaps
            payload["insights"]["activity_trend"] = activity_trend
        return jsonify(payload), 200
    finally:
        conn.close()


def _analyze_knowledge_gaps(rows):
    """分析低分题目，提取知识薄弱点"""
    import json
    if not rows:
        return []
    gaps = []
    for row in rows:
        try:
            questions = json.loads(row[3] or '[]')
            answers = json.loads(row[1] or '[]')
            score = row[2] or 0
        except (json.JSONDecodeError, IndexError):
            continue

        # 构建答案映射
        ans_map = {}
        for a in answers:
            idx = a.get('question_index', -1)
            if idx >= 0:
                ans_map[idx] = a.get('answer', '')

        for i, q in enumerate(questions):
            expected = str(q.get('answer', '')).strip()
            given = str(ans_map.get(i, '')).strip()
            if expected and given and expected != given:
                gaps.append({
                    'quiz_title': row[0] or '',
                    'question': q.get('question', ''),
                    'expected': expected,
                    'common_mistake': given,
                    'type': q.get('type', ''),
                })

    # 去重合并同类错误
    seen = set()
    unique_gaps = []
    for g in gaps:
        key = g['question'][:30]
        if key not in seen:
            seen.add(key)
            g['frequency'] = sum(1 for x in gaps if x['question'][:30] == key)
            unique_gaps.append(g)

    return sorted(unique_gaps, key=lambda x: -x['frequency'])[:10]


def _build_trend(rows):
    """构建活动趋势时间序列"""
    from collections import defaultdict
    by_date = defaultdict(lambda: {'assignment': 0, 'quiz': 0, 'submission': 0})
    for row in rows:
        dt = row[0]
        kind = row[2]
        cnt = row[1]
        if kind in by_date[dt]:
            by_date[dt][kind] += cnt

    trend = []
    for dt in sorted(by_date.keys()):
        d = by_date[dt]
        trend.append({
            'date': dt,
            'assignments': d['assignment'],
            'quizzes': d['quiz'],
            'submissions': d['submission'],
            'total': d['assignment'] + d['quiz'] + d['submission'],
        })
    return trend
