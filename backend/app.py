"""
Flask application factory for AITAS backend.
"""
from __future__ import annotations

from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from backend.config import STATIC_DIR, MAX_ASSIGNMENT_REQUEST_BYTES, ensure_storage_dirs
from backend.database import init_db


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_ASSIGNMENT_REQUEST_BYTES

    # CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Ensure storage directories exist
    ensure_storage_dirs()

    # Initialize database
    init_db()

    @app.errorhandler(413)
    def assignment_upload_too_large(_error):
        return jsonify({"error": "上传内容过大，单个文件不能超过 20 MB，一次提交不能超过 60 MB"}), 413

    # ── Register API Blueprints ──
    from backend.routers.auth import auth_bp
    from backend.routers.users import users_bp
    from backend.routers.classes import classes_bp
    from backend.routers.coursewares import coursewares_bp
    from backend.routers.evaluations import evaluations_bp
    from backend.routers.discussions import discussions_bp
    from backend.routers.messages import messages_bp
    from backend.routers.ai_chat import ai_chat_bp
    from backend.routers.agent import agent_bp
    from backend.routers.rag import rag_bp
    from backend.routers.dashboard import dashboard_bp
    from backend.routers.assignments import assignments_bp
    from backend.routers.quiz import quiz_bp
    from backend.routers.notifications import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(coursewares_bp)
    app.register_blueprint(evaluations_bp)
    app.register_blueprint(discussions_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(ai_chat_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(rag_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(notifications_bp)

    # ── Static file serving ──
    from backend.services.file_server import register_static_routes
    register_static_routes(app)

    # ── SPA fallback ──
    @app.route("/", defaults={"catchall_path": ""})
    @app.route("/<path:catchall_path>")
    def spa_fallback(catchall_path: str):
        """Serve index.html for all non-API, non-static routes (Vue Router)."""
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return send_from_directory(str(STATIC_DIR), "index.html")
        return "<h1>AITAS</h1><p>Frontend not built. Run <code>cd frontend && npm run build</code></p>", 200

    return app
