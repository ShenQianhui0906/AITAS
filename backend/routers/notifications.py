"""通知路由"""

from flask import Blueprint, request, jsonify, g
from backend.middleware.auth import require_auth
from backend.database import get_conn
from backend.models.notification import (
    list_notifications, unread_count, mark_read, mark_all_read
)

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.route('/api/notifications', methods=['GET'])
@require_auth
def get_notifications():
    """获取通知列表"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    conn = get_conn()
    try:
        notifs = list_notifications(conn, g.current_user['id'], limit, offset)
        return jsonify({'notifications': notifs}), 200
    finally:
        conn.close()


@notifications_bp.route('/api/notifications/unread-count', methods=['GET'])
@require_auth
def get_unread_count():
    """获取未读通知数"""
    conn = get_conn()
    try:
        count = unread_count(conn, g.current_user['id'])
        return jsonify({'count': count}), 200
    finally:
        conn.close()


@notifications_bp.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@require_auth
def read_notification(notif_id):
    """标记单条已读"""
    conn = get_conn()
    try:
        mark_read(conn, notif_id, g.current_user['id'])
        return jsonify({'ok': True}), 200
    finally:
        conn.close()


@notifications_bp.route('/api/notifications/read-all', methods=['POST'])
@require_auth
def read_all_notifications():
    """全部标记已读"""
    conn = get_conn()
    try:
        mark_all_read(conn, g.current_user['id'])
        return jsonify({'ok': True}), 200
    finally:
        conn.close()
