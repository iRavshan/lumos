import time
import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.chatbot.models import ChatbotConfig
from apps.chatbot.telegram_service import make_telegram_request, handle_telegram_update, delete_telegram_webhook


class Command(BaseCommand):
    help = "Runs real-time Long Polling for all active Telegram bots registered by business owners"

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Fetch updates only once and exit',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("[+] Lumos Telegram Bot Polling xizmati ishga tushdi..."))
        self.stdout.write("Barcha faol Telegram botlar uchun xabarlar tekshirilmoqda (To'xtatish uchun Ctrl+C bosing)\n")

        # Track offset per bot token
        offsets = {}

        # Reset webhook for polling if needed
        active_bots = ChatbotConfig.objects.filter(
            telegram_bot_active=True,
            telegram_bot_token__isnull=False
        ).exclude(telegram_bot_token='')

        for bot in active_bots:
            # Delete webhook so Telegram allows getUpdates polling
            delete_telegram_webhook(bot.telegram_bot_token)
            self.stdout.write(self.style.SUCCESS(f"  * [@{bot.telegram_bot_username or bot.bot_name}] botiga ulanildi"))

        while True:
            try:
                # Reload active bots dynamically
                bots = ChatbotConfig.objects.filter(
                    telegram_bot_active=True,
                    telegram_bot_token__isnull=False
                ).exclude(telegram_bot_token='')

                if not bots.exists():
                    self.stdout.write(self.style.WARNING("Hozirda faol Telegram botlar mavjud emas. Kutilmoqda..."))
                    time.sleep(5)
                    continue

                for bot in bots:
                    token = bot.telegram_bot_token
                    current_offset = offsets.get(token, None)

                    payload = {
                        'timeout': 3,
                        'allowed_updates': ['message', 'callback_query']
                    }
                    if current_offset is not None:
                        payload['offset'] = current_offset

                    res = make_telegram_request(token, 'getUpdates', payload)
                    if res.get('ok'):
                        updates = res.get('result', [])
                        for update in updates:
                            update_id = update.get('update_id')
                            offsets[token] = update_id + 1

                            msg = update.get('message', {})
                            user_from = msg.get('from', {})
                            user_name = user_from.get('first_name', 'Foydalanuvchi')
                            msg_text = msg.get('text', '')

                            self.stdout.write(f"-> [@{bot.telegram_bot_username}] {user_name}: {msg_text}")

                            # Process update with AI RAG
                            try:
                                result = handle_telegram_update(bot.api_key, update)
                                self.stdout.write(self.style.SUCCESS(f"   [OK] AI Javob berildi!"))
                            except Exception as ex:
                                self.stdout.write(self.style.ERROR(f"   [X] Xatolik: {ex}"))

                if options['once']:
                    break

                time.sleep(1)

            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n[!] Telegram Bot Polling xizmati to'xtatildi."))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Kutilmagan xatolik: {e}"))
                time.sleep(3)
