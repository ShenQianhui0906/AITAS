"""
Request/response utilities.
"""
from __future__ import annotations

import json
from http import HTTPStatus


def parse_json_body(raw_body: bytes) -> dict:
    """Parse a JSON request body, returning {} on failure."""
    try:
        return json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def make_json_response(data: dict | list, status: int = HTTPStatus.OK) -> tuple[dict, int]:
    """Standard JSON response tuple used by FastAPI-compatible endpoints."""
    return data, status
