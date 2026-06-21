"""
Text extraction service — extracts text from courseware files.
"""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from backend.config import MAX_AI_CONTEXT_CHARS


def normalize_text_content(text: str) -> str:
    text = html.unescape(text or "")
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_xml_text(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""
    texts = [node.text for node in root.iter() if node.text and node.text.strip()]
    return normalize_text_content("\n".join(texts))


def extract_pdf_text_fallback(file_path: Path) -> str:
    data = file_path.read_bytes()
    chunks = []
    for match in re.finditer(rb"\(([^()]{2,400})\)", data):
        try:
            text = match.group(1).decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = match.group(1).decode("latin-1")
            except UnicodeDecodeError:
                continue
        if any(char.isalpha() or "\u4e00" <= char <= "\u9fff" for char in text):
            chunks.append(text)
    return normalize_text_content("\n".join(chunks))


def extract_pdf_text(file_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return extract_pdf_text_fallback(file_path)

    try:
        reader = PdfReader(str(file_path))
        texts = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                texts.append(page_text)
        parsed = normalize_text_content("\n\n".join(texts))
        if parsed:
            return parsed
    except Exception:
        pass
    return extract_pdf_text_fallback(file_path)


def extract_courseware_text(file_path: Path) -> str:
    """Extract text from a courseware file. Supports txt, md, docx, pptx, pdf."""
    if not file_path.exists():
        return ""

    suffix = file_path.suffix.lower()
    text_like = {".txt", ".md", ".csv", ".json", ".py", ".js", ".ts", ".html", ".htm"}
    if suffix in text_like:
        raw = file_path.read_text(encoding="utf-8", errors="ignore")
        if suffix in {".html", ".htm"}:
            raw = re.sub(r"<[^>]+>", " ", raw)
        return normalize_text_content(raw)

    if suffix == ".docx":
        try:
            with zipfile.ZipFile(file_path) as archive:
                return extract_xml_text(archive.read("word/document.xml"))
        except (KeyError, zipfile.BadZipFile, OSError):
            return ""

    if suffix == ".pptx":
        try:
            texts = []
            with zipfile.ZipFile(file_path) as archive:
                slide_names = sorted(
                    name for name in archive.namelist()
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                )
                for name in slide_names:
                    slide_text = extract_xml_text(archive.read(name))
                    if slide_text:
                        texts.append(slide_text)
            return normalize_text_content("\n\n".join(texts))
        except (zipfile.BadZipFile, OSError):
            return ""

    if suffix == ".pdf":
        return extract_pdf_text(file_path)

    return ""


def crop_ai_context(text: str, limit: int = MAX_AI_CONTEXT_CHARS) -> str:
    text = normalize_text_content(text)
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}\n\n[以下内容已截断]"
