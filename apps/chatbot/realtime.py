import time
import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)


def notify_chat_update(business_id, session_id, message_id=None):
    """
    Registers an instantaneous chat update in Redis cache.
    Allows inbox clients to poll at low latency (<2ms) without hitting DB if no changes.
    """
    now_ts = time.time()
    try:
        if business_id:
            cache.set(f"lumos:act:{business_id}", now_ts, timeout=86400)
        if session_id and message_id:
            cache.set(f"lumos:last_msg:{session_id}", message_id, timeout=86400)
    except Exception as e:
        logger.warning("Redis notify_chat_update error: %s", e)


def get_business_last_activity(business_id):
    """
    Returns the latest activity timestamp for a business from Redis.
    """
    try:
        return cache.get(f"lumos:act:{business_id}")
    except Exception:
        return None


def get_session_last_msg_id(session_id):
    """
    Returns the latest message ID for a session from Redis.
    """
    try:
        return cache.get(f"lumos:last_msg:{session_id}")
    except Exception:
        return None
