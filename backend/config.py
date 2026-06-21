"""
Shared configuration for AITAS backend.
All file-system paths and settings are centralised here.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Storage root — all runtime data lives under storage/
# ---------------------------------------------------------------------------
STORAGE_DIR = ROOT_DIR / "storage"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_DIR = STORAGE_DIR / "db"
DB_PATH = DB_DIR / "ai_tutor.sqlite3"

# ---------------------------------------------------------------------------
# Uploads — original courseware files
# ---------------------------------------------------------------------------
UPLOAD_DIR = STORAGE_DIR / "uploads"

# ---------------------------------------------------------------------------
# Processed results — extracted text, chunks, metadata
# ---------------------------------------------------------------------------
PROCESSED_DIR = STORAGE_DIR / "processed"

# ---------------------------------------------------------------------------
# Browser previews — system-generated HTML / assets
# ---------------------------------------------------------------------------
PREVIEW_DIR = STORAGE_DIR / "previews"

# ---------------------------------------------------------------------------
# Vector stores — ChromaDB
# ---------------------------------------------------------------------------
VECTORSTORE_DIR = STORAGE_DIR / "vectorstores"
CHROMA_DIR = VECTORSTORE_DIR / "chroma"

# ---------------------------------------------------------------------------
# Temporary files — safe to delete at any time
# ---------------------------------------------------------------------------
TMP_DIR = STORAGE_DIR / "tmp"

# ---------------------------------------------------------------------------
# Static front-end — Vue 3 build output
# ---------------------------------------------------------------------------
STATIC_DIR = ROOT_DIR / "frontend" / "dist"

# ---------------------------------------------------------------------------
# Environment variables from ENV file
# ---------------------------------------------------------------------------
_ENV_FILE = ROOT_DIR / "ENV"
if _ENV_FILE.exists():
    with _ENV_FILE.open(encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _, _val = _line.partition("=")
            os.environ.setdefault(_key.strip(), _val.strip())

# ---------------------------------------------------------------------------
# AI / LLM settings
# ---------------------------------------------------------------------------
BIGMODEL_API_URL = os.environ.get(
    "BIGMODEL_API_URL",
    "https://open.bigmodel.cn/api/paas/v4/chat/completions",
).strip() or "https://open.bigmodel.cn/api/paas/v4/chat/completions"

BIGMODEL_MODEL = os.environ.get("BIGMODEL_MODEL", "glm-4.7-flash").strip() or "glm-4.7-flash"

MAX_AI_CONTEXT_CHARS = 12000
MAX_AI_HISTORY_MESSAGES = 8

# ---------------------------------------------------------------------------
# Admin defaults
# ---------------------------------------------------------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "2026"
ADMIN_DISPLAY_NAME = "系统管理员"

# ---------------------------------------------------------------------------
# Preview settings
# ---------------------------------------------------------------------------
QUICKLOOK_PREVIEW_SUFFIXES = {".ppt", ".pptx"}
NATIVE_PREVIEW_SUFFIX = ".native-preview.pdf"

# ---------------------------------------------------------------------------
# Ensure storage directories exist
# ---------------------------------------------------------------------------
def ensure_storage_dirs():
    """Create all storage subdirectories on startup."""
    for directory in [
        STORAGE_DIR,
        DB_DIR,
        UPLOAD_DIR,
        PROCESSED_DIR,
        PREVIEW_DIR,
        VECTORSTORE_DIR,
        CHROMA_DIR,
        TMP_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
