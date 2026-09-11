import time
import logging
import threading
from django.db import close_old_connections
from .models import ChatbotConfig
from .telegram_service import (
    make_telegram_request,
    handle_telegram_update,
)

logger = logging.getLogger('telegram_worker')

_worker_thread = None
_stop_event = threading.Event()
_offsets = {}


def _polling_loop():
    logger.info("[Telegram Worker] Background Long Polling thread started.")
    print("[+] Telegram bot avtomatik javob berish xizmati fonda ishga tushdi...")

    # Wait 2 seconds on startup for Django to finish initializing
    time.sleep(2)

    while not _stop_event.is_set():
        try:
            close_old_connections()

            # Find active bots that have a token
            active_bots = list(
                ChatbotConfig.objects.filter(
                    telegram_bot_active=True,
                    telegram_bot_token__isnull=False
                ).exclude(telegram_bot_token='').select_related('business')
            )

            if not active_bots:
                time.sleep(3)
                continue

            for bot in active_bots:
                token = bot.telegram_bot_token

                # If a public HTTPS webhook is registered on Telegram, skip polling for this bot
                wh_info = make_telegram_request(token, 'getWebhookInfo')
                wh_url = (wh_info.get('result') or {}).get('url', '')
                if wh_url and wh_url.startswith('https://'):
                    continue

                current_offset = _offsets.get(token, None)
                payload = {
                    'timeout': 2,
                    'allowed_updates': ['message', 'callback_query']
                }
                if current_offset is not None:
                    payload['offset'] = current_offset

                res = make_telegram_request(token, 'getUpdates', payload)
                if res.get('ok'):
                    updates = res.get('result', [])
                    for update in updates:
                        upd_id = update.get('update_id')
                        _offsets[token] = upd_id + 1

                        # Process update
                        try:
                            close_old_connections()
                            handle_telegram_update(bot.api_key, update)
                            close_old_connections()
                        except Exception as e:
                            logger.error(f"[Telegram Worker] Error processing update {upd_id}: {e}")

            time.sleep(1)

        except Exception as ex:
            logger.error(f"[Telegram Worker] Loop error: {ex}")
            time.sleep(3)


def start_telegram_polling_worker():
    global _worker_thread
    if _worker_thread is not None and _worker_thread.is_alive():
        return

    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_polling_loop,
        name='TelegramPollingWorker',
        daemon=True
    )
    _worker_thread.start()


def stop_telegram_polling_worker():
    global _worker_thread
    _stop_event.set()
    if _worker_thread is not None:
        _worker_thread.join(timeout=3)
        _worker_thread = None
