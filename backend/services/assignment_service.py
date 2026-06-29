"""Helpers for safe assignment rich-text content and submission files."""
from __future__ import annotations

import html
import mimetypes
import re
import shutil
import subprocess
import uuid
import zipfile
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET

from backend.config import (
    INLINE_IMAGE_SUFFIXES,
    MAX_ASSIGNMENT_FILE_BYTES,
    UPLOAD_DIR,
)
from backend.services.text_service import extract_courseware_text


ALLOWED_CONTENT_TAGS = {
    "p", "div", "br", "strong", "b", "em", "i", "u",
    "ul", "ol", "li", "blockquote",
}

BROWSER_PREVIEW_SUFFIXES = {
    ".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
    ".mp3", ".wav", ".ogg", ".mp4", ".webm",
}


def _build_docx_preview_via_textutil(file_path: Path) -> str | None:
    """Use macOS's document converter to preserve DOCX paragraph formatting."""
    textutil_path = shutil.which("textutil")
    if not textutil_path:
        return None
    try:
        result = subprocess.run(
            [textutil_path, "-convert", "html", "-stdout", str(file_path)],
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0 or not result.stdout:
        return None

    converted_html = result.stdout.decode("utf-8", errors="replace")
    # The converter produces static HTML, but the attachment is untrusted input.
    converted_html = re.sub(
        r"<script\b[^>]*>.*?</script>", "", converted_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    converted_html = re.sub(
        r"\s+on[a-z]+\s*=\s*(['\"]).*?\1", "", converted_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    preview_head = """
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; object-src 'none'; base-uri 'none'; form-action 'none'">
  <style type="text/css">
    html { background: #eef2f7; }
    body { box-sizing: border-box; width: min(960px, calc(100% - 40px)); min-height: calc(100vh - 40px);
      margin: 20px auto !important; padding: 64px 72px !important; background: #fff;
      color: #0f172a; box-shadow: 0 14px 42px rgba(15, 23, 42, .10); }
    p, li { overflow-wrap: anywhere; }
    table { max-width: 100%; border-collapse: collapse; }
    img { max-width: 100%; height: auto; }
    @media (max-width: 720px) {
      body { width: 100%; min-height: 100vh; margin: 0 !important; padding: 28px 22px !important; box-shadow: none; }
    }
  </style>
"""
    if "</head>" in converted_html.lower():
        close_index = converted_html.lower().find("</head>")
        converted_html = (
            converted_html[:close_index] + preview_head + converted_html[close_index:]
        )
    else:
        converted_html = f"<head>{preview_head}</head>{converted_html}"
    return converted_html


def _extract_xlsx_text(file_path: Path) -> str:
    """Extract readable cell values from an XLSX file without extra dependencies."""
    try:
        with zipfile.ZipFile(file_path) as archive:
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in archive.namelist():
                shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in shared_root.iter():
                    if item.tag.rsplit("}", 1)[-1] == "si":
                        value = "".join(
                            node.text or "" for node in item.iter()
                            if node.tag.rsplit("}", 1)[-1] == "t"
                        )
                        shared_strings.append(value)

            lines: list[str] = []
            sheet_names = sorted(
                name for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            )
            for sheet_index, sheet_name in enumerate(sheet_names, start=1):
                lines.append(f"工作表 {sheet_index}")
                root = ET.fromstring(archive.read(sheet_name))
                for row in root.iter():
                    if row.tag.rsplit("}", 1)[-1] != "row":
                        continue
                    values: list[str] = []
                    for cell in row:
                        if cell.tag.rsplit("}", 1)[-1] != "c":
                            continue
                        cell_type = cell.attrib.get("t", "")
                        value = ""
                        for node in cell.iter():
                            local_name = node.tag.rsplit("}", 1)[-1]
                            if local_name in {"v", "t"} and node.text is not None:
                                value += node.text
                        if cell_type == "s" and value.isdigit():
                            index = int(value)
                            value = shared_strings[index] if index < len(shared_strings) else value
                        if value:
                            values.append(value)
                    if values:
                        lines.append("\t".join(values))
                lines.append("")
            return "\n".join(lines).strip()
    except (OSError, ET.ParseError, zipfile.BadZipFile):
        return ""


def build_assignment_file_preview_html(file_path: Path, display_name: str) -> str:
    """Build a self-contained and escaped browser preview for document attachments."""
    suffix = file_path.suffix.lower()
    if suffix == ".docx":
        converted_docx = _build_docx_preview_via_textutil(file_path)
        if converted_docx:
            return converted_docx
    text = _extract_xlsx_text(file_path) if suffix == ".xlsx" else extract_courseware_text(file_path)
    safe_name = html.escape(display_name or file_path.name)
    if text:
        content = f'<pre class="preview-text">{html.escape(text)}</pre>'
        label = "文档内容预览"
    else:
        content = (
            '<div class="preview-empty">'
            '<strong>此文件暂不支持在线解析</strong>'
            '<p>请关闭当前预览页，并使用作业界面的“下载”按钮查看原文件。</p>'
            '</div>'
        )
        label = "附件预览"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_name}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 24px; background: #f8fafc; color: #0f172a;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    .preview-shell {{ max-width: 1080px; margin: 0 auto; display: grid; gap: 16px; }}
    .preview-head {{ display: flex; justify-content: space-between; gap: 16px; padding: 18px 20px;
      border: 1px solid #e2e8f0; border-radius: 18px; background: #fff; }}
    .preview-head strong {{ overflow-wrap: anywhere; }}
    .preview-head span {{ flex: 0 0 auto; color: #4f46e5; font-size: 13px; font-weight: 700; }}
    .preview-text {{ margin: 0; min-height: calc(100vh - 130px); padding: 24px; border: 1px solid #e2e8f0;
      border-radius: 18px; background: #fff; white-space: pre-wrap; overflow-wrap: anywhere;
      font: 14px/1.75 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .preview-empty {{ padding: 64px 24px; border: 1px solid #e2e8f0; border-radius: 18px;
      background: #fff; text-align: center; }}
    .preview-empty p {{ color: #64748b; }}
  </style>
</head>
<body>
  <main class="preview-shell">
    <header class="preview-head"><strong>{safe_name}</strong><span>{label}</span></header>
    {content}
  </main>
</body>
</html>"""


class _SubmissionHtmlSanitizer(HTMLParser):
    def __init__(self, inline_file_ids: dict[int, int]):
        super().__init__(convert_charrefs=True)
        self.inline_file_ids = inline_file_ids
        self.output: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag = tag.lower()
        if tag in ALLOWED_CONTENT_TAGS:
            self.output.append("<br>" if tag == "br" else f"<{tag}>")
            return
        if tag != "img":
            return
        attr_map = {key.lower(): value for key, value in attrs}
        try:
            index = int(attr_map.get("data-inline-index") or "")
        except ValueError:
            return
        file_id = self.inline_file_ids.get(index)
        if file_id:
            self.output.append(
                f'<img data-assignment-file-id="{file_id}" alt="提交图片">'
            )

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in ALLOWED_CONTENT_TAGS and tag != "br":
            self.output.append(f"</{tag}>")

    def handle_data(self, data: str):
        self.output.append(html.escape(data))

    def get_html(self) -> str:
        return "".join(self.output).strip()


def sanitize_submission_html(raw_html: str, inline_file_ids: dict[int, int]) -> str:
    parser = _SubmissionHtmlSanitizer(inline_file_ids)
    parser.feed((raw_html or "")[:100_000])
    parser.close()
    return parser.get_html()


def submission_has_text(content_html: str) -> bool:
    text = submission_html_to_text(content_html)
    return bool(re.sub(r"\s+", "", text))


def submission_html_to_text(content_html: str) -> str:
    value = re.sub(r"<(?:br|/p|/div|/li)>\s*", "\n", content_html or "", flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value).replace("\xa0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def extract_assignment_attachment_text(file_path: Path) -> str:
    if file_path.suffix.lower() == ".xlsx":
        return _extract_xlsx_text(file_path)
    return extract_courseware_text(file_path)


def _safe_suffix(file_name: str) -> str:
    suffix = Path(file_name or "").suffix.lower()
    return suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""


def read_submission_file(file_obj, *, inline: bool) -> tuple[str, bytes, str]:
    original_name = Path(file_obj.filename or "file").name
    suffix = _safe_suffix(original_name)
    if inline and suffix not in INLINE_IMAGE_SUFFIXES:
        raise ValueError("正文图片仅支持 PNG、JPG、GIF 或 WebP 格式。")

    body = file_obj.read(MAX_ASSIGNMENT_FILE_BYTES + 1)
    if len(body) > MAX_ASSIGNMENT_FILE_BYTES:
        raise ValueError("单个作业文件不能超过 20MB。")
    if not body:
        raise ValueError(f"文件“{original_name}”内容为空。")

    mime_type = mimetypes.guess_type(original_name)[0] or "application/octet-stream"
    if inline and mime_type not in {
        "image/png", "image/jpeg", "image/gif", "image/webp"
    }:
        raise ValueError("正文图片格式不受支持。")
    return original_name, body, mime_type


def save_submission_file(
    *,
    assignment_id: int,
    submission_id: int,
    original_name: str,
    body: bytes,
    inline: bool,
) -> str:
    suffix = _safe_suffix(original_name)
    folder = "inline" if inline else "attachments"
    target_dir = (
        UPLOAD_DIR / "assignments" / str(assignment_id)
        / "submissions" / str(submission_id) / folder
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target_path = target_dir / stored_name
    target_path.write_bytes(body)
    return str(target_path.relative_to(UPLOAD_DIR))


def delete_stored_assignment_file(stored_file_name: str) -> None:
    target = (UPLOAD_DIR / stored_file_name).resolve()
    assignment_root = (UPLOAD_DIR / "assignments").resolve()
    if str(target).startswith(str(assignment_root)) and target.is_file():
        target.unlink()


def delete_submission_assets(assignment_id: int, submission_id: int) -> None:
    target = (
        UPLOAD_DIR / "assignments" / str(assignment_id)
        / "submissions" / str(submission_id)
    )
    if target.exists():
        shutil.rmtree(target)


def delete_assignment_assets(assignment_id: int) -> None:
    target = UPLOAD_DIR / "assignments" / str(assignment_id)
    if target.exists():
        shutil.rmtree(target)
