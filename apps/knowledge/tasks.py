"""
Scraping va embedding boshqaruvchi.
Onboarding dan chaqiriladi — saytni scrape qilib, embedding qilib bazaga saqlaydi.
"""

import time
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


def scrape_and_embed(business, triggered_by='manual'):
    """
    Biznesning manbalarini (vebsayt va telegram kanal) scrape qilib, bilimlar bazasiga saqlaydi.
    Har bir jarayon KnowledgeSyncLog ga yoziladi.

    Args:
        business: Business model instance
        triggered_by: 'manual', 'auto', yoki 'onboarding'

    Returns:
        int: Saqlangan chunk soni, yoki 0 agar xatolik bo'lsa
    """
    from .models import KnowledgeSyncLog

    has_website = bool(business.website and business.website.strip())
    has_telegram = bool(business.telegram and business.telegram.strip())

    if not has_website and not has_telegram:
        logger.info("Biznesda vebsayt yoki telegram manba yo'q: %s", business.name)
        return 0

    sources_list = []
    if has_website:
        sources_list.append(business.website.strip())
    if has_telegram:
        sources_list.append(f"Telegram: {business.telegram.strip()}")

    # Sync log yaratish
    sync_log = KnowledgeSyncLog.objects.create(
        business=business,
        status='running',
        source_url=", ".join(sources_list)[:500],
        triggered_by=triggered_by,
    )

    start_time = time.time()

    try:
        from .scraper import scrape_website, scrape_telegram_channel
        from .embeddings import embed_and_store

        scraped_data = []

        # 1. Saytni scrape qilish
        if has_website:
            logger.info("Vebsayt scraping boshlandi: %s → %s", business.name, business.website)
            site_data = scrape_website(business.website)
            if site_data:
                scraped_data.extend(site_data)

        # 2. Telegram kanalni scrape qilish
        if has_telegram:
            logger.info("Telegram kanal scraping boshlandi: %s → %s", business.name, business.telegram)
            tg_data = scrape_telegram_channel(business.telegram)
            if tg_data:
                scraped_data.extend(tg_data)

        if not scraped_data:
            logger.warning("Manbalardan hech qanday ma'lumot olinmadi: %s", business.name)
            duration = time.time() - start_time
            sync_log.status = 'no_data'
            sync_log.duration_seconds = round(duration, 2)
            sync_log.completed_at = timezone.now()
            sync_log.save()
            return 0

        total_chunks = sum(len(page['chunks']) for page in scraped_data)
        logger.info("Scrape natijasi: %d sahifa/manba, %d chunk (%s)",
                     len(scraped_data), total_chunks, business.name)

        # 3. Embedding qilib bazaga saqlash
        stored = embed_and_store(business, scraped_data)
        logger.info("Bilimlar bazasiga saqlandi: %d chunk (%s)", stored, business.name)

        # Sync log yangilash
        duration = time.time() - start_time
        sync_log.status = 'success'
        sync_log.pages_scraped = len(scraped_data)
        sync_log.chunks_stored = stored
        sync_log.duration_seconds = round(duration, 2)
        sync_log.completed_at = timezone.now()
        sync_log.save()

        return stored

    except Exception as e:
        logger.error("Scrape va embed xatolik (%s): %s", business.name, e, exc_info=True)
        duration = time.time() - start_time
        sync_log.status = 'failed'
        sync_log.error_message = str(e)[:500]
        sync_log.duration_seconds = round(duration, 2)
        sync_log.completed_at = timezone.now()
        sync_log.save()
        return 0


def scrape_all_businesses():
    """
    Barcha bizneslarning manbalarini (sayt va telegram kanal) qayta scrape qiladi.
    Cron yoki management command orqali 24 soatda bir marta chaqiriladi.

    Returns:
        dict: {business_name: chunks_stored}
    """
    from django.db.models import Q
    from apps.businesses.models import Business

    businesses = Business.objects.filter(
        (Q(website__isnull=False) & ~Q(website='')) |
        (Q(telegram__isnull=False) & ~Q(telegram=''))
    ).distinct()
    results = {}

    logger.info("Avtomatik sinxronizatsiya boshlandi: %d ta biznes", businesses.count())

    for business in businesses:
        try:
            stored = scrape_and_embed(business, triggered_by='auto')
            results[business.name] = stored
            logger.info("Sinxronlandi: %s → %d chunk", business.name, stored)
        except Exception as e:
            results[business.name] = 0
            logger.error("Sinxronlash xatolik (%s): %s", business.name, e)

    logger.info("Avtomatik sinxronizatsiya tugadi: %s", results)
    return results
