from django.db import models
from pgvector.django import VectorField, HnswIndex
from apps.businesses.models import Business


class BusinessKnowledge(models.Model):
    """
    Biznes saytidan scrape qilingan ma'lumotlar chunklari va ularning vektorlari.
    Har bir yozuv bitta biznesga tegishli — business_id orqali izolyatsiya qilingan.
    """
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='knowledge_chunks',
        verbose_name="Biznes",
        db_index=True,
    )
    source_url = models.URLField(
        max_length=500,
        verbose_name="Manba sahifa URL",
        help_text="Qaysi sahifadan scrape qilingan",
    )
    title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Sahifa sarlavhasi",
    )
    content = models.TextField(
        verbose_name="Chunk matni",
        help_text="500-1000 so'zlik matn bo'lagi",
    )
    embedding = VectorField(
        dimensions=768,
        null=True,
        blank=True,
        verbose_name="Embedding vektori (768-d)",
    )
    chunk_index = models.PositiveIntegerField(
        default=0,
        verbose_name="Chunk tartib raqami",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan sana",
    )

    class Meta:
        verbose_name = "Bilim Chunki"
        verbose_name_plural = "Bilimlar Bazasi"
        ordering = ['business', 'source_url', 'chunk_index']
        indexes = [
            HnswIndex(
                name='knowledge_embedding_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]

    def __str__(self):
        return f"[{self.business.name}] {self.title or self.source_url} (#{self.chunk_index})"
