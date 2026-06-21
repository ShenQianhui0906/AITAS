"""
Evaluations router — /api/evaluations
"""
from __future__ import annotations

import json
from http import HTTPStatus

from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.evaluation import list_evaluations, create_evaluation
from backend.models.access import build_class_scope_clause, user_can_access_class


def handle_evaluation_routes(path: str, method: str, headers: dict, body: bytes, query_params: dict) -> tuple[dict | list, int] | None:
    if not path.startswith("/api/evaluations"):
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    # GET /api/evaluations
    if method == "GET" and path == "/api/evaluations":
        conn = get_conn()
        try:
            class_id = query_params.get("class_id")
            if class_id:
                class_id = int(class_id[0])
                if not user_can_access_class(conn, user, class_id):
                    return {"error": "当前账号无权查看该班级评价。"}, HTTPStatus.FORBIDDEN
            clause, params = build_class_scope_clause(user, class_id, "id")
            evaluations = list_evaluations(conn, clause, params)
            return {"evaluations": evaluations}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/evaluations
    if method == "POST" and path == "/api/evaluations":
        if user["role"] != "student":
            return {"error": "仅学生可提交课件评价。"}, HTTPStatus.FORBIDDEN
        data = json.loads(body) if body else {}
        try:
            courseware_id = int(data.get("courseware_id"))
            helpfulness = int(data.get("helpfulness", 0))
            usability = int(data.get("usability", 0))
            suitability = int(data.get("suitability", 3))
            practicality = int(data.get("practicality", 3))
        except (TypeError, ValueError):
            return {"error": "评价参数不合法。"}, HTTPStatus.BAD_REQUEST
        suggestion = (data.get("suggestion") or "").strip()

        conn = get_conn()
        try:
            courseware = conn.execute(
                "SELECT class_id FROM coursewares WHERE id = ?", (courseware_id,)
            ).fetchone()
            if not courseware:
                return {"error": "课件不存在。"}, HTTPStatus.NOT_FOUND
            if not user_can_access_class(conn, user, courseware["class_id"]):
                return {"error": "当前账号无权评价该课件。"}, HTTPStatus.FORBIDDEN

            result = create_evaluation(
                conn, courseware_id, user["id"], helpfulness, usability,
                suitability, practicality, suggestion,
            )
            conn.commit()
            return result, HTTPStatus.CREATED
        finally:
            conn.close()

    return None
