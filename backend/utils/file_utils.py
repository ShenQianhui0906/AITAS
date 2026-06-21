"""
File path and storage utilities.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from backend.config import UPLOAD_DIR


def get_display_file_title(file_path: Path) -> str:
    name = file_path.stem
    name = re.sub(r"^[0-9a-f]{12,}_", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^\d+[._-]+", "", name)
    return name or file_path.stem


def build_upload_url(file_name: str) -> str:
    from urllib.parse import quote
    return f"/uploads/{quote(file_name)}"


def delete_courseware_assets(stored_file_name: str):
    """Delete courseware files and clean up empty directories recursively."""
    stored_path = UPLOAD_DIR / stored_file_name
    if stored_path.exists():
        stored_path.unlink()

    # Clean up empty parent directories up to coursewares/{id}/
    parent = stored_path.parent
    while parent != UPLOAD_DIR and parent.parent != UPLOAD_DIR:
        try:
            if parent.exists() and not any(parent.iterdir()):
                shutil.rmtree(str(parent))
        except OSError:
            break
        parent = parent.parent


def get_file_suffix(file_path: Path) -> str:
    return file_path.suffix.lower()
