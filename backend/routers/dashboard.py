"""
Dashboard router — /api/dashboard
"""
from __future__ import annotations

from http import HTTPStatus

from backend.database import get_conn
from backend.middleware.auth import require_user_from_header


def handle_dashboard_routes(path: str, method: str, headers: dict, body: bytes) -> tuple[dict | list, int] | None:
    if method != "GET" or path != "/api/dashboard":
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    conn = get_conn()
    try:
        stats = {}

        if user["role"] == "admin":
            # Users overview
            stats["total_users"] = conn.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'").fetchone()[0]
            stats["total_teachers"] = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'teacher'"
            ).fetchone()[0]
            stats["total_students"] = conn.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'student'"
            ).fetchone()[0]

            # Classes overview
            stats["total_classes"] = conn.execute("SELECT COUNT(*) FROM classes").fetchone()[0]

            # Coursewares overview
            stats["total_coursewares"] = conn.execute("SELECT COUNT(*) FROM coursewares").fetchone()[0]

            # Evaluations overview
            stats["total_evaluations"] = conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
            row = conn.execute(
                "SELECT AVG(helpfulness), AVG(usability), AVG(suitability), AVG(practicality) FROM evaluations"
            ).fetchone()
            stats["avg_helpfulness"] = round(row[0] or 0, 1)
            stats["avg_usability"] = round(row[1] or 0, 1)
            stats["avg_suitability"] = round(row[2] or 0, 1)
            stats["avg_practicality"] = round(row[3] or 0, 1)

            # Recent discussions
            discussions = conn.execute(
                "SELECT d.id, d.title, d.created_at, u.display_name as author_name, c.name as class_name "
                "FROM discussions d JOIN users u ON d.author_id = u.id "
                "JOIN classes c ON d.class_id = c.id "
                "ORDER BY d.created_at DESC LIMIT 5"
            ).fetchall()
            stats["recent_discussions"] = [dict(d) for d in discussions]

        elif user["role"] == "teacher":
            # Teacher's classes
            classes = conn.execute(
                "SELECT id, name FROM classes WHERE teacher_id = ?", (user["id"],)
            ).fetchall()
            class_ids = [c["id"] for c in classes]
            stats["total_classes"] = len(classes)

            if class_ids:
                placeholders = ",".join("?" * len(class_ids))
                stats["total_coursewares"] = conn.execute(
                    f"SELECT COUNT(*) FROM coursewares WHERE class_id IN ({placeholders})",
                    class_ids,
                ).fetchone()[0]
                stats["total_students"] = conn.execute(
                    f"SELECT COUNT(DISTINCT user_id) FROM class_members WHERE class_id IN ({placeholders})",
                    class_ids,
                ).fetchone()[0]
                stats["total_evaluations"] = conn.execute(
                    f"SELECT COUNT(*) FROM evaluations e JOIN coursewares cw ON e.courseware_id = cw.id "
                    f"WHERE cw.class_id IN ({placeholders})",
                    class_ids,
                ).fetchone()[0]
                stats["pending_requests"] = conn.execute(
                    f"SELECT COUNT(*) FROM class_join_requests WHERE class_id IN ({placeholders}) AND status = 'pending'",
                    class_ids,
                ).fetchone()[0]
                row = conn.execute(
                    f"SELECT AVG(e.helpfulness), AVG(e.usability), AVG(e.suitability), AVG(e.practicality) "
                    f"FROM evaluations e JOIN coursewares cw ON e.courseware_id = cw.id "
                    f"WHERE cw.class_id IN ({placeholders})",
                    class_ids,
                ).fetchone()
                stats["avg_helpfulness"] = round(row[0] or 0, 1)
                stats["avg_usability"] = round(row[1] or 0, 1)
                stats["avg_suitability"] = round(row[2] or 0, 1)
                stats["avg_practicality"] = round(row[3] or 0, 1)
            else:
                stats.update({"total_coursewares": 0, "total_students": 0, "total_evaluations": 0,
                              "pending_requests": 0, "avg_helpfulness": 0, "avg_usability": 0,
                              "avg_suitability": 0, "avg_practicality": 0})

        else:  # student
            # Student's classes
            class_rows = conn.execute(
                "SELECT c.id, c.name FROM classes c JOIN class_members cm ON c.id = cm.class_id "
                "WHERE cm.user_id = ?", (user["id"],)
            ).fetchall()
            class_ids = [c["id"] for c in class_rows]
            stats["total_classes"] = len(class_rows)

            if class_ids:
                placeholders = ",".join("?" * len(class_ids))
                stats["total_coursewares"] = conn.execute(
                    f"SELECT COUNT(*) FROM coursewares WHERE class_id IN ({placeholders})",
                    class_ids,
                ).fetchone()[0]
                stats["my_evaluations"] = conn.execute(
                    "SELECT COUNT(*) FROM evaluations WHERE student_id = ?", (user["id"],)
                ).fetchone()[0]
                stats["total_evaluations"] = conn.execute(
                    f"SELECT COUNT(*) FROM evaluations e JOIN coursewares cw ON e.courseware_id = cw.id "
                    f"WHERE cw.class_id IN ({placeholders})",
                    class_ids,
                ).fetchone()[0]
                stats["my_discussions"] = conn.execute(
                    f"SELECT COUNT(*) FROM discussions WHERE author_id = ? AND class_id IN ({placeholders})",
                    (user["id"], *class_ids),
                ).fetchone()[0]
            else:
                stats.update({"total_coursewares": 0, "my_evaluations": 0, "total_evaluations": 0,
                              "my_discussions": 0})

            # Available classes count
            stats["available_classes"] = conn.execute(
                "SELECT COUNT(*) FROM classes c WHERE c.id NOT IN "
                "(SELECT class_id FROM class_members WHERE user_id = ?)",
                (user["id"],),
            ).fetchone()[0]

        return {"stats": stats}, HTTPStatus.OK
    finally:
        conn.close()
