#!/usr/bin/env python3
"""
AITAS Backend — main entry point (Flask version).

Run:  python backend/main.py [--port 8080]
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path for imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    port = 8080
    for i, arg in enumerate(sys.argv):
        if arg in ("--port", "-p") and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass

    from backend.app import create_app
    app = create_app()

    print(f"[AITAS] Starting Flask server on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)


if __name__ == "__main__":
    main()

