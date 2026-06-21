"""
Coursewares router — /api/coursewares/*
"""
from __future__ import annotations

import json
import re
from http import HTTPStatus
from pathlib import Path
from urllib.parse import quote

from backend.database import get_conn
from backend.middleware.auth import require_user_from_header
from backend.models.courseware import (
    list_coursewares, get_courseware_detail, create_courseware,
    update_courseware, delete_courseware,
)
from backend.models.access import build_class_scope_clause, user_can_access_class, user_can_manage_class
from backend.utils.file_utils import delete_courseware_assets, get_display_file_title
from backend.services.sync_service import publish_user_updates


def get_preview_display_name(file_name: str, display_title: str = "") -> str:
    suffix = Path(file_name).suffix
    title = (display_title or "").strip() or get_display_file_title(Path(file_name))
    title = re.sub(r'[\\/:*?"<>|]+', " ", title).strip().rstrip(".")
    title = re.sub(r"\s+", " ", title) or get_display_file_title(Path(file_name)) or "课件"
    if suffix and not title.lower().endswith(suffix.lower()):
        title = f"{title}{suffix}"
    return title


def _build_viewer_url(file_name: str, display_title: str = "") -> str:
    preview_name = get_preview_display_name(file_name, display_title)
    return f"/preview/{quote(file_name)}/{quote(preview_name)}"


def handle_courseware_routes(path: str, method: str, headers: dict, body: bytes, query_params: dict) -> tuple[dict | list, int] | None:
    if not path.startswith("/api/coursewares"):
        return None
    user, error = require_user_from_header(headers.get("Authorization"))
    if error:
        return {"error": error}, HTTPStatus.UNAUTHORIZED

    # GET /api/coursewares
    if method == "GET" and path == "/api/coursewares":
        conn = get_conn()
        try:
            class_id = query_params.get("class_id")
            if class_id:
                class_id = int(class_id[0])
                if not user_can_access_class(conn, user, class_id):
                    return {"error": "当前账号无权查看该班级课件。"}, HTTPStatus.FORBIDDEN
            clause, params = build_class_scope_clause(user, class_id, "c.class_id")
            coursewares = list_coursewares(conn, clause, params, _build_viewer_url)
            return {"coursewares": coursewares}, HTTPStatus.OK
        finally:
            conn.close()

    # GET /api/coursewares/{id}
    if method == "GET" and path.startswith("/api/coursewares/") and path.count("/") == 3:
        parts = path.split("/")
        try:
            courseware_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "课件编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            detail = get_courseware_detail(conn, courseware_id, _build_viewer_url)
            if not detail:
                return {"error": "课件不存在。"}, HTTPStatus.NOT_FOUND
            if not user_can_access_class(conn, user, detail["class_id"]):
                return {"error": "当前账号无权查看该课件。"}, HTTPStatus.FORBIDDEN
            return {"courseware": detail}, HTTPStatus.OK
        finally:
            conn.close()

    # POST /api/coursewares
    if method == "POST" and path == "/api/coursewares":
        if user["role"] not in ("teacher", "admin"):
            return {"error": "仅教师和管理员可上传课件。"}, HTTPStatus.FORBIDDEN

        # Parse multipart form data - simplified: expect JSON with file_path for now
        # Multipart handling is done in the main handler
        return {"error": "请使用 multipart/form-data 上传课件。"}, HTTPStatus.BAD_REQUEST

    # PUT /api/coursewares/{id}
    if method == "PUT" and path.startswith("/api/coursewares/"):
        parts = path.split("/")
        try:
            courseware_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "课件编号不合法。"}, HTTPStatus.BAD_REQUEST
        data = json.loads(body) if body else {}
        title = (data.get("title") or "").strip()
        course_name = (data.get("course_name") or "").strip()
        description = (data.get("description") or "").strip()
        if not title or not course_name:
            return {"error": "课件标题和课程名称不能为空。"}, HTTPStatus.BAD_REQUEST

        conn = get_conn()
        try:
            existing = get_courseware_detail(conn, courseware_id, _build_viewer_url)
            if not existing:
                return {"error": "课件不存在。"}, HTTPStatus.NOT_FOUND
            if not user_can_manage_class(conn, user, existing["class_id"]):
                return {"error": "当前账号无权修改该课件。"}, HTTPStatus.FORBIDDEN
            updated = update_courseware(conn, courseware_id, title, course_name, description)
            return {"courseware": updated}, HTTPStatus.OK
        finally:
            conn.close()

    # DELETE /api/coursewares/{id}
    if method == "DELETE" and path.startswith("/api/coursewares/"):
        parts = path.split("/")
        try:
            courseware_id = int(parts[3])
        except (IndexError, ValueError):
            return {"error": "课件编号不合法。"}, HTTPStatus.BAD_REQUEST
        conn = get_conn()
        try:
            existing = get_courseware_detail(conn, courseware_id, _build_viewer_url)
            if not existing:
                return {"error": "课件不存在。"}, HTTPStatus.NOT_FOUND
            if not user_can_manage_class(conn, user, existing["class_id"]):
                return {"error": "当前账号无权删除该课件。"}, HTTPStatus.FORBIDDEN
            result = delete_courseware(conn, courseware_id)
            conn.commit()
            if result:
                delete_courseware_assets(result["stored_file_name"])
            return {"message": "课件已删除。"}, HTTPStatus.OK
        finally:
            conn.close()

    return None
