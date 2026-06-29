"""Assignment publishing, submission, attachment, and grading routes."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, g, jsonify, request, send_file

from backend.config import MAX_ASSIGNMENT_FILES, UPLOAD_DIR
from backend.database import get_conn
from backend.middleware.auth import require_auth
from backend.models.access import user_can_access_class, user_can_manage_class
from backend.models.assignment import (
    add_submission_file,
    clear_submission_files,
    create_assignment,
    delete_assignment_records,
    discard_ai_grading_draft,
    ensure_submission,
    finalize_submission,
    get_assignment,
    get_assignment_grading_rubric,
    get_student_submission,
    get_submission,
    get_submission_file,
    grade_submission,
    list_assignment_submissions,
    list_assignments,
    save_ai_grading_draft,
    save_assignment_grading_rubric,
)
from backend.services.assignment_service import (
    BROWSER_PREVIEW_SUFFIXES,
    build_assignment_file_preview_html,
    delete_assignment_assets,
    delete_submission_assets,
    read_submission_file,
    sanitize_submission_html,
    save_submission_file,
    submission_has_text,
)
from backend.services.assignment_grading_service import (
    AIGradingFormatError,
    RUBRIC_SOURCES,
    generate_ai_grading,
    generate_rubric_candidate,
    get_or_create_rubric,
)
from backend.services.notification_service import notify_assignment_published


assignments_bp = Blueprint("assignments", __name__)


def _get_accessible_file(conn, file_id: int):
    file_info = get_submission_file(conn, file_id)
    if not file_info:
        return None, None, (jsonify({"error": "文件不存在。"}), 404)
    can_manage = user_can_manage_class(conn, g.current_user, file_info["class_id"])
    is_owner = file_info["student_id"] == g.current_user["id"]
    if not can_manage and not is_owner:
        return None, None, (jsonify({"error": "当前账号无权访问该文件。"}), 403)
    file_path = (UPLOAD_DIR / file_info["stored_file_name"]).resolve()
    assignment_root = (UPLOAD_DIR / "assignments").resolve()
    if not str(file_path).startswith(str(assignment_root)) or not file_path.is_file():
        return None, None, (jsonify({"error": "文件不存在。"}), 404)
    return file_info, file_path, None


def _parse_due_at(raw_value: str) -> str | None:
    value = (raw_value or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _assignment_response(conn, assignment: dict) -> dict:
    item = dict(assignment)
    if g.current_user["role"] in {"teacher", "admin"}:
        item["submissions"] = list_assignment_submissions(conn, item["id"])
    else:
        item["my_submission"] = get_student_submission(
            conn, item["id"], g.current_user["id"]
        )
    return item


def _get_manageable_assignment(conn, assignment_id: int):
    assignment = get_assignment(conn, assignment_id)
    if not assignment:
        return None, (jsonify({"error": "作业不存在。"}), 404)
    if not user_can_manage_class(conn, g.current_user, assignment["class_id"]):
        return None, (jsonify({"error": "当前账号无权管理该作业。"}), 403)
    return assignment, None


@assignments_bp.route("/api/assignments", methods=["GET"])
@require_auth
def get_assignments():
    class_id = request.args.get("class_id", type=int)
    if not class_id:
        return jsonify({"error": "班级编号不合法。"}), 400
    conn = get_conn()
    try:
        if not user_can_access_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权查看该班级作业。"}), 403
        return jsonify({
            "assignments": list_assignments(conn, class_id, g.current_user)
        }), 200
    finally:
        conn.close()


@assignments_bp.route("/api/assignments", methods=["POST"])
@require_auth
def publish_assignment():
    if g.current_user["role"] not in {"teacher", "admin"}:
        return jsonify({"error": "仅教师和管理员可发布作业。"}), 403
    data = request.get_json(silent=True) or {}
    try:
        class_id = int(data.get("class_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "班级编号不合法。"}), 400
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    due_at = _parse_due_at(data.get("due_at") or "")
    if not title:
        return jsonify({"error": "请输入作业标题。"}), 400
    if not due_at:
        return jsonify({"error": "截止时间格式不合法。"}), 400

    conn = get_conn()
    try:
        if not user_can_manage_class(conn, g.current_user, class_id):
            return jsonify({"error": "当前账号无权向该班级发布作业。"}), 403
        assignment = create_assignment(
            conn, class_id, g.current_user["id"], title, description, due_at
        )
        conn.commit()
        notify_assignment_published(
            class_id,
            g.current_user.get("display_name") or g.current_user.get("username") or "教师",
            assignment["title"],
            assignment["id"],
            assignment["due_at"],
        )
        return jsonify({"assignment": assignment}), 201
    finally:
        conn.close()


@assignments_bp.route("/api/assignments/<int:assignment_id>", methods=["GET"])
@require_auth
def get_assignment_detail(assignment_id: int):
    conn = get_conn()
    try:
        assignment = get_assignment(conn, assignment_id)
        if not assignment:
            return jsonify({"error": "作业不存在。"}), 404
        if not user_can_access_class(conn, g.current_user, assignment["class_id"]):
            return jsonify({"error": "当前账号无权查看该作业。"}), 403
        return jsonify({
            "assignment": _assignment_response(conn, assignment)
        }), 200
    finally:
        conn.close()


@assignments_bp.route(
    "/api/assignments/<int:assignment_id>/rubric", methods=["GET", "PUT"]
)
@require_auth
def assignment_grading_rubric(assignment_id: int):
    if g.current_user["role"] not in {"teacher", "admin"}:
        return jsonify({"error": "仅教师和管理员可管理评价标准。"}), 403
    conn = get_conn()
    try:
        assignment, error = _get_manageable_assignment(conn, assignment_id)
        if error:
            return error
        if request.method == "GET":
            rubric = get_assignment_grading_rubric(conn, assignment["id"])
            return jsonify({"rubric": rubric}), 200

        data = request.get_json(silent=True) or {}
        content = (data.get("content") or "").strip()
        if not content:
            return jsonify({"error": "评价标准不能为空。"}), 400
        if len(content) > 8_000:
            return jsonify({"error": "评价标准不能超过 8000 个字符。"}), 400
        source = data.get("source")
        if source not in RUBRIC_SOURCES - {"teacher"}:
            source = "teacher"
        source_refs = data.get("source_refs")
        if not isinstance(source_refs, list):
            source_refs = []
        rubric = save_assignment_grading_rubric(
            conn, assignment["id"], content, source, source_refs
        )
        conn.commit()
        return jsonify({"rubric": rubric}), 200
    finally:
        conn.close()


@assignments_bp.route(
    "/api/assignments/<int:assignment_id>/rubric/regenerate", methods=["POST"]
)
@require_auth
def regenerate_assignment_grading_rubric(assignment_id: int):
    if g.current_user["role"] not in {"teacher", "admin"}:
        return jsonify({"error": "仅教师和管理员可生成评价标准。"}), 403
    conn = get_conn()
    try:
        assignment, error = _get_manageable_assignment(conn, assignment_id)
        if error:
            return error
        try:
            candidate = generate_rubric_candidate(conn, assignment)
        except AIGradingFormatError as exc:
            return jsonify({"error": str(exc)}), 502
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        return jsonify({"candidate": candidate}), 200
    finally:
        conn.close()


@assignments_bp.route("/api/assignments/<int:assignment_id>", methods=["DELETE"])
@require_auth
def delete_assignment(assignment_id: int):
    conn = get_conn()
    try:
        assignment = get_assignment(conn, assignment_id)
        if not assignment:
            return jsonify({"error": "作业不存在。"}), 404
        if not user_can_manage_class(conn, g.current_user, assignment["class_id"]):
            return jsonify({"error": "当前账号无权删除该作业。"}), 403
        delete_assignment_records(conn, assignment_id)
        conn.commit()
        delete_assignment_assets(assignment_id)
        return jsonify({"message": "作业已删除。"}), 200
    finally:
        conn.close()


@assignments_bp.route("/api/assignments/<int:assignment_id>/submit", methods=["POST"])
@require_auth
def submit_assignment(assignment_id: int):
    if g.current_user["role"] != "student":
        return jsonify({"error": "仅学生可提交作业。"}), 403

    raw_html = (request.form.get("content_html") or "").strip()
    inline_files = [file for file in request.files.getlist("inline_images") if file.filename]
    attachments = [file for file in request.files.getlist("attachments") if file.filename]
    if len(inline_files) + len(attachments) > MAX_ASSIGNMENT_FILES:
        return jsonify({"error": f"一次最多上传 {MAX_ASSIGNMENT_FILES} 个文件。"}), 400

    try:
        inline_payloads = [
            read_submission_file(file, inline=True) for file in inline_files
        ]
        attachment_payloads = [
            read_submission_file(file, inline=False) for file in attachments
        ]
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    if not submission_has_text(raw_html) and not inline_payloads and not attachment_payloads:
        return jsonify({"error": "请输入作业内容或选择要上传的文件。"}), 400

    conn = get_conn()
    submission_id = None
    try:
        assignment = get_assignment(conn, assignment_id)
        if not assignment:
            return jsonify({"error": "作业不存在。"}), 404
        if not user_can_access_class(conn, g.current_user, assignment["class_id"]):
            return jsonify({"error": "当前账号无权提交该作业。"}), 403

        try:
            submission_id, _created = ensure_submission(
                conn, assignment_id, g.current_user["id"]
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        delete_submission_assets(assignment_id, submission_id)
        clear_submission_files(conn, submission_id)

        inline_file_ids: dict[int, int] = {}
        for index, (original_name, body, mime_type) in enumerate(inline_payloads):
            stored_name = save_submission_file(
                assignment_id=assignment_id,
                submission_id=submission_id,
                original_name=original_name,
                body=body,
                inline=True,
            )
            file_info = add_submission_file(
                conn, submission_id, original_name, stored_name,
                mime_type, len(body), True,
            )
            inline_file_ids[index] = file_info["id"]

        for original_name, body, mime_type in attachment_payloads:
            stored_name = save_submission_file(
                assignment_id=assignment_id,
                submission_id=submission_id,
                original_name=original_name,
                body=body,
                inline=False,
            )
            add_submission_file(
                conn, submission_id, original_name, stored_name,
                mime_type, len(body), False,
            )

        content_html = sanitize_submission_html(raw_html, inline_file_ids)
        submission = finalize_submission(conn, submission_id, content_html)
        conn.commit()
        return jsonify({"submission": submission}), 200
    except OSError:
        conn.rollback()
        return jsonify({"error": "提交文件保存失败，请稍后重试。"}), 500
    finally:
        conn.close()


@assignments_bp.route(
    "/api/assignments/<int:assignment_id>/submissions/<int:submission_id>/grade",
    methods=["PUT"],
)
@require_auth
def grade_assignment_submission(assignment_id: int, submission_id: int):
    if g.current_user["role"] not in {"teacher", "admin"}:
        return jsonify({"error": "仅教师和管理员可批改作业。"}), 403
    data = request.get_json(silent=True) or {}
    try:
        score = float(data.get("score"))
    except (TypeError, ValueError):
        return jsonify({"error": "请输入有效分数。"}), 400
    if not 0 <= score <= 100:
        return jsonify({"error": "分数必须在 0 到 100 之间。"}), 400
    feedback = (data.get("feedback") or "").strip()

    conn = get_conn()
    try:
        assignment = get_assignment(conn, assignment_id)
        submission = get_submission(conn, submission_id)
        if not assignment or not submission or submission["assignment_id"] != assignment_id:
            return jsonify({"error": "作业提交记录不存在。"}), 404
        if not user_can_manage_class(conn, g.current_user, assignment["class_id"]):
            return jsonify({"error": "当前账号无权批改该作业。"}), 403
        updated = grade_submission(
            conn, submission_id, g.current_user["id"], score, feedback
        )
        conn.commit()
        return jsonify({"submission": updated}), 200
    finally:
        conn.close()


@assignments_bp.route(
    "/api/assignments/<int:assignment_id>/submissions/<int:submission_id>/ai-grade",
    methods=["POST", "DELETE"],
)
@require_auth
def ai_grade_assignment_submission(assignment_id: int, submission_id: int):
    if g.current_user["role"] not in {"teacher", "admin"}:
        return jsonify({"error": "仅教师和管理员可使用 AI 批改。"}), 403
    conn = get_conn()
    try:
        assignment, error = _get_manageable_assignment(conn, assignment_id)
        if error:
            return error
        submission = get_submission(conn, submission_id)
        if not submission or submission["assignment_id"] != assignment_id:
            return jsonify({"error": "作业提交记录不存在。"}), 404

        if request.method == "DELETE":
            discarded = discard_ai_grading_draft(conn, submission_id)
            conn.commit()
            return jsonify({
                "message": "AI 批改草稿已丢弃。" if discarded else "当前没有 AI 批改草稿。"
            }), 200

        try:
            rubric, created = get_or_create_rubric(conn, assignment)
            if created:
                conn.commit()
            suggestion = generate_ai_grading(assignment, submission, rubric)
        except AIGradingFormatError as exc:
            return jsonify({"error": str(exc)}), 502
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        draft = save_ai_grading_draft(
            conn,
            submission_id,
            suggestion["score"],
            suggestion["evaluation"],
            suggestion["evidence"],
            suggestion["feedback"],
            rubric["content"],
            rubric["source"],
            suggestion["model_name"],
        )
        conn.commit()
        return jsonify({
            "suggestion": {
                "score": suggestion["score"],
                "evaluation": suggestion["evaluation"],
                "evidence": suggestion["evidence"],
                "feedback": suggestion["feedback"],
            },
            "draft": draft,
            "rubric": rubric,
        }), 200
    finally:
        conn.close()


@assignments_bp.route("/api/assignments/files/<int:file_id>", methods=["GET"])
@require_auth
def get_assignment_file(file_id: int):
    conn = get_conn()
    try:
        file_info, file_path, error = _get_accessible_file(conn, file_id)
        if error:
            return error
        force_download = request.args.get("download", "").lower() in {
            "1", "true", "yes"
        }
        response = send_file(
            file_path,
            mimetype=file_info["mime_type"],
            as_attachment=force_download,
            download_name=file_info["original_file_name"],
        )
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        if not force_download:
            response.headers["Content-Security-Policy"] = "sandbox; default-src 'none'"
        return response
    finally:
        conn.close()


@assignments_bp.route("/api/assignments/files/<int:file_id>/preview", methods=["GET"])
@require_auth
def preview_assignment_file(file_id: int):
    conn = get_conn()
    try:
        file_info, file_path, error = _get_accessible_file(conn, file_id)
        if error:
            return error

        if file_path.suffix.lower() in BROWSER_PREVIEW_SUFFIXES:
            response = send_file(
                file_path,
                mimetype=file_info["mime_type"],
                as_attachment=False,
                download_name=file_info["original_file_name"],
            )
        else:
            preview_html = build_assignment_file_preview_html(
                file_path, file_info["original_file_name"]
            )
            response = Response(preview_html, content_type="text/html; charset=utf-8")

        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "sandbox; default-src 'none'; style-src 'unsafe-inline'"
        )
        return response
    finally:
        conn.close()
