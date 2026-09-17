"""
Scraping va embedding boshqaruvchi.
Onboarding dan chaqiriladi — saytni scrape qilib, embedding qilib bazaga saqlaydi.
"""

import logging

logger = logging.getLogger(__name__)


def scrape_and_embed(business):
    """
    Biznesning saytini scrape qilib, bilimlar bazasiga saqlaydi.

    Args:
        business: Business model instance (website maydoni to'ldirilgan bo'lishi kerak)

    Returns:
        int: Saqlangan chunk soni, yoki 0 agar xatolik bo'lsa
    """
    if not business.website:
        logger.info("Biznesda sayt URL yo'q, scraping o'tkazib yuborildi: %s", business.name)
        return 0

    try:
        from .scraper import scrape_website
        from .embeddings import embed_and_store

        logger.info("Scraping boshlandi: %s → %s", business.name, business.website)

        # 1. Saytni scrape qilish
        scraped_data = scrape_website(business.website)
        if not scraped_data:
            logger.warning("Saytdan hech qanday ma'lumot olinmadi: %s", business.website)
            return 0

        total_chunks = sum(len(page['chunks']) for page in scraped_data)
        logger.info("Scrape natijasi: %d sahifa, %d chunk (%s)",
                     len(scraped_data), total_chunks, business.name)

        # 2. Embedding qilib bazaga saqlash
        stored = embed_and_store(business, scraped_data)
        logger.info("Bilimlar bazasiga saqlandi: %d chunk (%s)", stored, business.name)

        return stored

    except Exception as e:
        logger.error("Scrape va embed xatolik (%s): %s", business.name, e, exc_info=True)
        return 0
