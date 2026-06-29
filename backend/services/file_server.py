"""
Static file server — Flask version: handles /static/*, /preview/*, /uploads/*,
/preview-quicklook/*, /preview-media
"""
from __future__ import annotations

import mimetypes
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, quote

from flask import Flask, request, send_from_directory, Response, abort

from backend.config import STATIC_DIR, UPLOAD_DIR, QUICKLOOK_PREVIEW_SUFFIXES
from backend.utils.file_utils import get_display_file_title
from backend.services.preview_service import (
    build_courseware_preview_html,
    build_browser_ready_quicklook_html,
    ensure_native_pdf_preview,
    ensure_quicklook_preview,
)


def _make_file_response(file_path: Path, download_name: str = "",
                        inline: bool = False) -> Response:
    """Send a file as a Flask response."""
    guessed_type, _ = mimetypes.guess_type(str(file_path))
    content_type = guessed_type or "application/octet-stream"
    disposition_type = "inline" if inline else "attachment"

    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(download_name).stem).strip("._-") or "preview"
    safe_suffix = Path(download_name).suffix
    fallback_name = f"{safe_stem}{safe_suffix}" if download_name else None

    response = Response(file_path.read_bytes(), content_type=content_type)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    if download_name:
        response.headers["Content-Disposition"] = (
            f'{disposition_type}; filename="{fallback_name}"; '
            f"filename*=UTF-8''{quote(download_name)}"
        )
    return response


def register_static_routes(app: Flask) -> None:
    """Register all static file serving routes on the Flask app."""

    # ── /static/* and /assets/* ──
    @app.route("/static/<path:filename>")
    @app.route("/assets/<path:filename>")
    def serve_static(filename: str):
        file_path = (STATIC_DIR / request.path.lstrip("/")).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())):
            abort(403)
        if not file_path.exists():
            abort(404)
        return send_from_directory(str(STATIC_DIR), str(file_path.relative_to(STATIC_DIR)))

    # ── /preview/<stored_name>/<display_name> ──
    @app.route("/preview/<path:subpath>")
    def serve_preview(subpath: str):
        relative = unquote(subpath).lstrip("/")
        parts = relative.rsplit("/", 1)
        stored_name = parts[0] if len(parts) == 2 else relative
        file_path = (UPLOAD_DIR / stored_name).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists():
            abort(404)

        if file_path.suffix.lower() == ".pdf":
            display_name = f"{get_display_file_title(file_path)}.pdf"
            return _make_file_response(file_path, download_name=display_name, inline=True)

        if file_path.suffix.lower() in QUICKLOOK_PREVIEW_SUFFIXES:
            native_preview = ensure_native_pdf_preview(file_path)
            if native_preview and native_preview.exists():
                display_name = f"{get_display_file_title(file_path)}.pdf"
                return _make_file_response(native_preview, download_name=display_name, inline=True)

        return build_courseware_preview_html(file_path), 200, {"Content-Type": "text/html; charset=utf-8"}

    # ── /uploads/<path:filename> ──
    @app.route("/uploads/<path:filename>")
    def serve_upload(filename: str):
        file_path = (UPLOAD_DIR / filename).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists():
            abort(404)
        return _make_file_response(file_path)

    # ── /preview-quicklook/<path:filename> ──
    @app.route("/preview-quicklook/<path:filename>")
    def serve_quicklook(filename: str):
        file_path = (UPLOAD_DIR / filename).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists():
            abort(404)
        preview_dir = ensure_quicklook_preview(file_path)
        preview_html = preview_dir / "Preview.html" if preview_dir else None
        if not preview_html or not preview_html.exists():
            abort(404)
        html = build_browser_ready_quicklook_html(file_path, preview_html)
        return html, 200, {"Content-Type": "text/html; charset=utf-8"}

    # ── /preview-media?file=...&asset=... ──
    @app.route("/preview-media")
    def serve_preview_media():
        file_name = (request.args.get("file", "") or "").strip()
        asset_name = Path(request.args.get("asset", "") or "").name
        if not file_name or not asset_name:
            abort(400)

        file_path = (UPLOAD_DIR / unquote(file_name)).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists():
            abort(404)

        media_path = f"ppt/media/{asset_name}"
        try:
            with zipfile.ZipFile(str(file_path)) as archive:
                body = archive.read(media_path)
        except (OSError, zipfile.BadZipFile, KeyError):
            abort(404)

        content_type, _ = mimetypes.guess_type(asset_name)
        return Response(body, content_type=content_type or "application/octet-stream")
