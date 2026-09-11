import os
import sys
from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chatbot'
    verbose_name = 'AI Chatbot Tizimi'

    def ready(self):
        # Prevent starting during management commands or migrations
        ignored_commands = {'makemigrations', 'migrate', 'collectstatic', 'check', 'test', 'shell', 'run_telegram_bot'}
        args = set(sys.argv)
        if any(cmd in args for cmd in ignored_commands):
            return

        # In runserver, only start in the child process to avoid duplicate threads
        is_runserver = 'runserver' in args
        if is_runserver and os.environ.get('RUN_MAIN') != 'true':
            return

        try:
            from .telegram_worker import start_telegram_polling_worker
            start_telegram_polling_worker()
        except Exception:
            pass
