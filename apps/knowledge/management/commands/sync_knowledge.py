"""
Barcha bizneslarning bilimlar bazasini sinxronlash.
Har 24 soatda cron orqali ishga tushiriladi.

Foydalanish:
    python manage.py sync_knowledge

Cron misoli (har kuni soat 03:00 da):
    0 3 * * * cd /path/to/project && python manage.py sync_knowledge
"""

from django.core.management.base import BaseCommand
from apps.knowledge.tasks import scrape_all_businesses


class Command(BaseCommand):
    help = "Barcha bizneslarning saytlarini qayta scrape qilib, bilimlar bazasini yangilaydi"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Bilimlar bazasi sinxronizatsiyasi boshlandi..."))

        results = scrape_all_businesses()

        for name, chunks in results.items():
            if chunks > 0:
                self.stdout.write(self.style.SUCCESS(f"  [OK] {name}: {chunks} chunk yangilandi"))
            else:
                self.stdout.write(self.style.WARNING(f"  [--] {name}: ma'lumot topilmadi yoki xatolik"))

        total = sum(results.values())
        self.stdout.write(self.style.SUCCESS(
            f"\nSinxronizatsiya tugadi: {len(results)} biznes, {total} chunk yangilandi"
        ))
