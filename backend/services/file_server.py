"""
Static file server — handles /, /static/*, /preview/*, /uploads/*, /preview-quicklook/*, /preview-media
"""
from __future__ import annotations

import mimetypes
import re
import zipfile
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote

from backend.config import STATIC_DIR, UPLOAD_DIR, QUICKLOOK_PREVIEW_SUFFIXES
from backend.utils.file_utils import get_display_file_title
from backend.services.preview_service import (
    build_courseware_preview_html,
    build_browser_ready_quicklook_html,
    ensure_native_pdf_preview,
    ensure_quicklook_preview,
)


def _send_file(file_path: Path, download_name: str = "",
               inline: bool = False, handler=None) -> None:
    """Send a file response through the HTTP handler."""
    if handler is None:
        return
    guessed_type, _ = mimetypes.guess_type(str(file_path))
    content_type = guessed_type or "application/octet-stream"
    data = file_path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    if download_name:
        safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", Path(download_name).stem).strip("._-") or "preview"
        safe_suffix = Path(download_name).suffix
        fallback_name = f"{safe_stem}{safe_suffix}"
        from urllib.parse import quote
        disposition_type = "inline" if inline else "attachment"
        handler.send_header(
            "Content-Disposition",
            f'{disposition_type}; filename="{fallback_name}"; filename*=UTF-8\'\'{quote(download_name)}',
        )
    handler.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
    handler.send_header("Pragma", "no-cache")
    handler.send_header("Expires", "0")
    handler.end_headers()
    handler.wfile.write(data)


def _send_html(content: str, handler) -> None:
    data = content.encode("utf-8")
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def _send_bytes(data: bytes, content_type: str, handler) -> None:
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def try_serve_static(path: str, handler) -> bool:
    """Try to serve a static file or preview or upload. Returns True if handled."""
    # --- SPA fallback: /, /index.html ---
    if path in ("", "/", "/index.html"):
        file_path = STATIC_DIR / "index.html"
        if file_path.exists():
            _send_file(file_path, handler=handler)
        else:
            _send_html("<h1>AITAS</h1><p>Frontend not built. Run <code>cd frontend && npm run build</code></p>", handler)
        return True

    # --- /static/* ---
    if path.startswith("/static/") or path.startswith("/assets/"):
        relative = path.lstrip("/")
        file_path = (STATIC_DIR / relative).resolve()
        if not str(file_path).startswith(str(STATIC_DIR.resolve())):
            _send_html("<h1>403 Forbidden</h1>", handler)
        elif file_path.exists():
            _send_file(file_path, handler=handler)
        else:
            handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
        return True

    # --- /preview/{stored_name}/{display_name} ---
    if path.startswith("/preview/"):
        relative = unquote(path[len("/preview/"):]).lstrip("/")
        parts = relative.rsplit("/", 1)
        stored_name = parts[0] if len(parts) == 2 else relative
        file_path = (UPLOAD_DIR / stored_name).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists():
            handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return True

        # PDF inline
        if file_path.suffix.lower() == ".pdf":
            display_name = f"{get_display_file_title(file_path)}.pdf"
            _send_file(file_path, download_name=display_name, inline=True, handler=handler)
            return True

        # Presentation native PDF preview
        if file_path.suffix.lower() in QUICKLOOK_PREVIEW_SUFFIXES:
            native_preview = ensure_native_pdf_preview(file_path)
            if native_preview and native_preview.exists():
                display_name = f"{get_display_file_title(file_path)}.pdf"
                _send_file(native_preview, download_name=display_name, inline=True, handler=handler)
                return True

        # Full HTML preview
        _send_html(build_courseware_preview_html(file_path), handler)
        return True

    # --- /uploads/* ---
    if path.startswith("/uploads/"):
        relative = unquote(path[len("/uploads/"):]).lstrip("/")
        file_path = (UPLOAD_DIR / relative).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists():
            handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
        else:
            _send_file(file_path, handler=handler)
        return True

    # --- /preview-quicklook/* ---
    if path.startswith("/preview-quicklook/"):
        relative = unquote(path[len("/preview-quicklook/"):]).lstrip("/")
        file_path = (UPLOAD_DIR / relative).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists():
            handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return True
        preview_dir = ensure_quicklook_preview(file_path)
        preview_html = preview_dir / "Preview.html" if preview_dir else None
        if not preview_html or not preview_html.exists():
            handler.send_error(HTTPStatus.NOT_FOUND, "Preview not found")
            return True
        _send_html(build_browser_ready_quicklook_html(file_path, preview_html), handler)
        return True

    # --- /preview-media?file=...&asset=... ---
    if path.startswith("/preview-media"):
        from urllib.parse import parse_qs, urlparse
        query = parse_qs(handler.path.split("?", 1)[1] if "?" in handler.path else "")
        file_name = (query.get("file", [""])[0] or "").strip()
        asset_name = Path(query.get("asset", [""])[0] or "").name
        if not file_name or not asset_name:
            handler.send_error(HTTPStatus.BAD_REQUEST, "Invalid preview asset request")
            return True

        file_path = (UPLOAD_DIR / unquote(file_name)).resolve()
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())) or not file_path.exists():
            handler.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return True

        media_path = f"ppt/media/{asset_name}"
        try:
            with zipfile.ZipFile(str(file_path)) as archive:
                body = archive.read(media_path)
        except (OSError, zipfile.BadZipFile, KeyError):
            handler.send_error(HTTPStatus.NOT_FOUND, "Preview asset not found")
            return True

        content_type, _ = mimetypes.guess_type(asset_name)
        _send_bytes(body, content_type or "application/octet-stream", handler)
        return True

    # --- /preview-listener (QuickLook resource) ---
    if path.startswith("/preview-listener"):
        handler.send_error(HTTPStatus.NOT_FOUND, "Not found")
        return True

    return False
