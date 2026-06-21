"""
Shared configuration for AITAS project.
All file-system paths are centralised here so that business logic
never hard-codes directory or file names.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent

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
# Uploads — original courseware files kept forever
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
# Vector stores — ChromaDB (and future vector DBs)
# ---------------------------------------------------------------------------
VECTORSTORE_DIR = STORAGE_DIR / "vectorstores"
CHROMA_DIR = VECTORSTORE_DIR / "chroma"

# ---------------------------------------------------------------------------
# Temporary files — safe to delete at any time
# ---------------------------------------------------------------------------
TMP_DIR = STORAGE_DIR / "tmp"

# ---------------------------------------------------------------------------
# Static front-end (legacy, kept for compatibility)
# ---------------------------------------------------------------------------
VITE_DIST_DIR = ROOT_DIR / "frontend" / "dist"
STATIC_DIR = (
    VITE_DIST_DIR
    if (VITE_DIST_DIR / "index.html").exists()
    else (ROOT_DIR / "static")
)

# ---------------------------------------------------------------------------
# Boot helpers
# ---------------------------------------------------------------------------

_ALL_DIRS = [
    DB_DIR,
    UPLOAD_DIR,
    PROCESSED_DIR,
    PREVIEW_DIR,
    VECTORSTORE_DIR,
    CHROMA_DIR,
    TMP_DIR,
]


def ensure_storage_dirs() -> None:
    """Create every required storage directory on start-up."""
    for path in _ALL_DIRS:
        path.mkdir(parents=True, exist_ok=True)
