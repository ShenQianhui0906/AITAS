"""
Coursewares Blueprint — /api/coursewares/*
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, request, jsonify, g

from backend.config import UPLOAD_DIR
from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.courseware import (
    list_coursewares, get_courseware_detail, create_courseware,
    update_courseware, delete_courseware,
)
from backend.models.access import build_class_scope_clause, user_can_access_class, user_can_manage_class
from backend.utils.file_utils import delete_courseware_assets, get_display_file_title
from backend.services.sync_service import publish_user_updates
from backend.services.notification_service import notify_courseware_uploaded

coursewares_bp = Blueprint("coursewares", __name__)


def _get_preview_display_name(file_name: str, display_title: str = "") -> str:
    suffix = Path(file_name).suffix
    title = (display_title or "").strip() or get_display_file_title(Path(file_name))
    title = re.sub(r'[\\/:*?"<>|]+', " ", title).strip().rstrip(".")
    title = re.sub(r"\s+", " ", title) or get_display_file_title(Path(file_name)) or "课件"
    if suffix and not title.lower().endswith(suffix.lower()):
        title = f"{title}{suffix}"
    return title


def _build_viewer_url(file_name: str, display_title: str = "") -> str:
    preview_name = _get_preview_display_name(file_name, display_title)
    return f"/preview/{quote(file_name)}/{quote(preview_name)}"


@coursewares_bp.route("/api/coursewares", methods=["GET"])
@require_auth
def get_coursewares():
    conn = get_conn()
    try:
        class_id = request.args.get("class_id", type=int)
        if class_id and not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权查看该班级课件。"}), 403
        clause, params = build_class_scope_clause(g.current_user, class_id, "c.class_id")
        coursewares = list_coursewares(conn, clause, params, _build_viewer_url)
        return jsonify({"coursewares": coursewares}), 200
    finally:
        conn.close()


@coursewares_bp.route("/api/coursewares/<int:courseware_id>", methods=["GET"])
@require_auth
def get_courseware(courseware_id: int):
    conn = get_conn()
    try:
        detail = get_courseware_detail(conn, courseware_id, _build_viewer_url)
        if not detail:
            return jsonify({"error": "课件不存在。"}), 404
        if not user_can_access_class(conn, g.current_user, detail["class_id"]):
            return jsonify({"error": "当前账号无权查看该课件。"}), 403
        return jsonify({"courseware": detail}), 200
    finally:
        conn.close()


@coursewares_bp.route("/api/coursewares", methods=["POST"])
@require_auth
def upload_courseware():
    if g.current_user["role"] not in ("teacher", "admin"):
        return jsonify({"error": "仅教师和管理员可上传课件。"}), 403

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "请选择要上传的文件。"}), 400

    title = (request.form.get("title") or "").strip()
    course_name = (request.form.get("course_name") or "").strip()
    description = (request.form.get("description") or "").strip()

    class_id_str = (request.form.get("class_id") or "").strip()
    try:
        class_id = int(class_id_str)
    except (TypeError, ValueError):
        return jsonify({"error": "班级编号不合法。"}), 400

    if not title:
        title = Path(file.filename).stem
    if not course_name:
        course_name = title

    conn = get_conn()
    try:
        if not user_can_manage_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权向该班级上传课件。"}), 403

        courseware = create_courseware(
            conn,
            title=title,
            course_name=course_name,
            description=description,
            file_obj=file,
            uploaded_by=g.current_user["id"],
            class_id=class_id,
            upload_dir=UPLOAD_DIR,
        )
        conn.commit()
        notify_courseware_uploaded(
            class_id,
            g.current_user.get("display_name") or g.current_user.get("username") or "教师",
            courseware["title"],
            courseware["id"],
        )
        return jsonify({"courseware": courseware}), 201
    finally:
        conn.close()


@coursewares_bp.route("/api/coursewares/<int:courseware_id>", methods=["PUT"])
@require_auth
def update_courseware_route(courseware_id: int):
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    course_name = (data.get("course_name") or "").strip()
    description = (data.get("description") or "").strip()
    if not title or not course_name:
        return jsonify({"error": "课件标题和课程名称不能为空。"}), 400

    conn = get_conn()
    try:
        existing = get_courseware_detail(conn, courseware_id, _build_viewer_url)
        if not existing:
            return jsonify({"error": "课件不存在。"}), 404
        if not user_can_manage_class(conn, g.current_user, existing["class_id"]):
            return jsonify({"error": "当前账号无权修改该课件。"}), 403
        updated = update_courseware(conn, courseware_id, title, course_name, description)
        return jsonify({"courseware": updated}), 200
    finally:
        conn.close()


@coursewares_bp.route("/api/coursewares/<int:courseware_id>", methods=["DELETE"])
@require_auth
def delete_courseware_route(courseware_id: int):
    conn = get_conn()
    try:
        existing = get_courseware_detail(conn, courseware_id, _build_viewer_url)
        if not existing:
            return jsonify({"error": "课件不存在。"}), 404
        if not user_can_manage_class(conn, g.current_user, existing["class_id"]):
            return jsonify({"error": "当前账号无权删除该课件。"}), 403
        result = delete_courseware(conn, courseware_id)
        conn.commit()
        if result:
            delete_courseware_assets(result["stored_file_name"])
        return jsonify({"message": "课件已删除。"}), 200
    finally:
        conn.close()
