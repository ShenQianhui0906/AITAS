"""
Evaluations Blueprint — /api/evaluations
"""
from __future__ import annotations

from flask import Blueprint, request, jsonify, g

from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.evaluation import list_evaluations, create_evaluation
from backend.models.access import build_class_scope_clause, user_can_access_class
from backend.services.notification_service import notify_feedback_received

evaluations_bp = Blueprint("evaluations", __name__)


@evaluations_bp.route("/api/evaluations", methods=["GET"])
@require_auth
def get_evaluations():
    conn = get_conn()
    try:
        class_id = request.args.get("class_id", type=int)
        if class_id and not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权查看该班级评价。"}), 403
        clause, params = build_class_scope_clause(g.current_user, class_id, "id")
        evaluations = list_evaluations(conn, clause, params)
        return jsonify({"evaluations": evaluations}), 200
    finally:
        conn.close()


@evaluations_bp.route("/api/evaluations", methods=["POST"])
@require_auth
def submit_evaluation():
    if g.current_user["role"] != "student":
        return jsonify({"error": "仅学生可提交课件评价。"}), 403
    data = request.get_json(silent=True) or {}
    try:
        courseware_id = int(data.get("courseware_id"))
        helpfulness = int(data.get("helpfulness", 0))
        usability = int(data.get("usability", 0))
        suitability = int(data.get("suitability", 3))
        practicality = int(data.get("practicality", 3))
    except (TypeError, ValueError):
        return jsonify({"error": "评价参数不合法。"}), 400
    suggestion = (data.get("suggestion") or "").strip()

    conn = get_conn()
    try:
        courseware = conn.execute(
            "SELECT c.class_id, c.title, cls.teacher_id "
            "FROM coursewares c JOIN classes cls ON cls.id = c.class_id "
            "WHERE c.id = ?",
            (courseware_id,),
        ).fetchone()
        if not courseware:
            return jsonify({"error": "课件不存在。"}), 404
        if not user_can_access_class(conn, g.current_user, courseware["class_id"]):
            return jsonify({"error": "当前账号无权评价该课件。"}), 403

        result = create_evaluation(
            conn, courseware_id, g.current_user["id"], helpfulness, usability,
            suitability, practicality, suggestion,
        )
        conn.commit()
        notify_feedback_received(
            courseware["teacher_id"],
            g.current_user.get("display_name") or g.current_user.get("username") or "学生",
            courseware["title"],
            courseware_id,
            suggestion,
        )
        return jsonify(result), 201
    finally:
        conn.close()
