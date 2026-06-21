"""
Sync service — SSE-based real-time update notifications.
"""
from __future__ import annotations

import threading

SYNC_CONDITION = threading.Condition()
SYNC_CURSOR = 0
USER_SYNC_CURSORS: dict[int, int] = {}


def publish_user_updates(*user_ids: int):
    global SYNC_CURSOR
    listeners = {int(uid) for uid in user_ids if uid}
    if not listeners:
        return
    with SYNC_CONDITION:
        SYNC_CURSOR += 1
        for user_id in listeners:
            USER_SYNC_CURSORS[user_id] = SYNC_CURSOR
        SYNC_CONDITION.notify_all()


def get_user_sync_cursor(user_id: int) -> int:
    return USER_SYNC_CURSORS.get(user_id, 0)


def wait_for_user_update(user_id: int, cursor: int, timeout: float = 25.0) -> int | None:
    deadline = None
    with SYNC_CONDITION:
        while get_user_sync_cursor(user_id) <= cursor:
            if deadline is None:
                deadline = SYNC_CONDITION._time() + timeout
            remaining = deadline - SYNC_CONDITION._time()
            if remaining <= 0:
                return None
            SYNC_CONDITION.wait(timeout=min(remaining, 5.0))
        return get_user_sync_cursor(user_id)
