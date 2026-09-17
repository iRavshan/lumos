"""
Gemini Embedding API orqali matn vektorlash va pgvector da similarity search.
"""

import os
import logging

logger = logging.getLogger(__name__)


def _get_genai_client():
    """Google GenAI client yaratadi."""
    from google import genai
    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        raise ValueError("GEMINI_API_KEY .env faylida sozlanmagan")
    return genai.Client(api_key=api_key)


def get_embedding(text):
    """
    Matnning 768-o'lchovli embedding vektorini qaytaradi.
    Gemini gemini-embedding-001 modelidan 768 o'lcham bilan foydalanadi.

    Args:
        text: Vektorlanadigan matn

    Returns:
        list[float]: 768 o'lchovli vektor
    """
    from google.genai import types
    client = _get_genai_client()
    # Matnni cheklash (embedding model max token)
    truncated = text[:8000]
    result = client.models.embed_content(
        model='models/gemini-embedding-001',
        contents=truncated,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    return result.embeddings[0].values


def get_embeddings_batch(texts):
    """
    Bir nechta matnni batch da embedding qiladi.

    Args:
        texts: list[str] — matnlar ro'yxati

    Returns:
        list[list[float]]: Vektorlar ro'yxati
    """
    from google.genai import types
    client = _get_genai_client()
    # Har bir matnni cheklash
    truncated = [t[:8000] for t in texts]
    result = client.models.embed_content(
        model='models/gemini-embedding-001',
        contents=truncated,
        config=types.EmbedContentConfig(output_dimensionality=768)
    )
    return [e.values for e in result.embeddings]


def embed_and_store(business, scraped_data):
    """
    Scrape qilingan ma'lumotlarni embedding qilib, BusinessKnowledge jadvaliga saqlaydi.

    Args:
        business: Business model instance
        scraped_data: list[dict] — scraper.scrape_website() natijasi
            Har bir dict: {'url': str, 'title': str, 'chunks': list[str]}
    """
    from .models import BusinessKnowledge

    # Avvalgi bilimlarni tozalash (qayta scrape qilganda)
    old_count = BusinessKnowledge.objects.filter(business=business).count()
    if old_count > 0:
        BusinessKnowledge.objects.filter(business=business).delete()
        logger.info("Eski %d ta chunk o'chirildi (business=%s)", old_count, business.name)

    # Barcha chunklar va metadatalarni yig'ish
    all_chunks = []
    for page in scraped_data:
        for idx, chunk_text in enumerate(page['chunks']):
            all_chunks.append({
                'url': page['url'],
                'title': page['title'],
                'content': chunk_text,
                'chunk_index': idx,
            })

    if not all_chunks:
        logger.warning("Scrape natijasida hech qanday chunk topilmadi (business=%s)", business.name)
        return 0

    # Batch embedding (10 talab chunklarni guruhlab)
    batch_size = 10
    knowledge_objects = []

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i + batch_size]
        texts = [c['content'] for c in batch]

        try:
            embeddings = get_embeddings_batch(texts)
        except Exception as e:
            logger.error("Embedding xatolik (batch %d-%d): %s", i, i + len(batch), e)
            # Embedding olishda xato bo'lsa, vektorsiz saqlash
            embeddings = [None] * len(batch)

        for chunk_data, emb in zip(batch, embeddings):
            knowledge_objects.append(
                BusinessKnowledge(
                    business=business,
                    source_url=chunk_data['url'],
                    title=chunk_data['title'],
                    content=chunk_data['content'],
                    embedding=emb,
                    chunk_index=chunk_data['chunk_index'],
                )
            )

    # Bulk create
    BusinessKnowledge.objects.bulk_create(knowledge_objects)
    logger.info("Saqlandi: %d chunk (business=%s)", len(knowledge_objects), business.name)

    return len(knowledge_objects)


def search_similar(business_id, query, top_k=5):
    """
    Savol matniga eng o'xshash chunkalarni pgvector cosine similarity bilan qidiradi.
    Faqat berilgan business_id ga tegishli chunklar ichidan qidiradi.

    Args:
        business_id: int — Biznes ID
        query: str — Foydalanuvchi savoli
        top_k: int — Nechta natija qaytarish

    Returns:
        list[str]: Eng o'xshash chunk matnlari
    """
    from .models import BusinessKnowledge
    from pgvector.django import CosineDistance

    # Biznes uchun chunklar bormi?
    if not BusinessKnowledge.objects.filter(business_id=business_id, embedding__isnull=False).exists():
        return []

    try:
        query_embedding = get_embedding(query)
    except Exception as e:
        logger.error("Savol embedding xatolik: %s", e)
        return []

    results = (
        BusinessKnowledge.objects
        .filter(business_id=business_id, embedding__isnull=False)
        .annotate(distance=CosineDistance('embedding', query_embedding))
        .order_by('distance')
        [:top_k]
    )

    return [r.content for r in results]
