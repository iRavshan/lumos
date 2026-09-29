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


class KnowledgeSyncLog(models.Model):
    """
    Bilimlar bazasi sinxronizatsiya tarixi.
    Har bir scrape jarayoni haqida yozuv saqlaydi.
    """
    STATUS_CHOICES = [
        ('running', 'Jarayonda'),
        ('success', 'Muvaffaqiyatli'),
        ('failed', 'Xatolik'),
        ('no_data', 'Ma\'lumot topilmadi'),
    ]

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='sync_logs',
        verbose_name="Biznes",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='running',
        verbose_name="Holat",
    )
    pages_scraped = models.PositiveIntegerField(
        default=0,
        verbose_name="Scrape qilingan sahifalar",
    )
    chunks_stored = models.PositiveIntegerField(
        default=0,
        verbose_name="Saqlangan chunklar soni",
    )
    source_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Manba URL",
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Xatolik xabari",
    )
    duration_seconds = models.FloatField(
        default=0,
        verbose_name="Davomiyligi (soniya)",
    )
    triggered_by = models.CharField(
        max_length=30,
        default='manual',
        verbose_name="Kim tomonidan",
        help_text="manual, auto, onboarding",
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Boshlangan vaqt",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Tugagan vaqt",
    )

    class Meta:
        verbose_name = "Sinxronizatsiya Logi"
        verbose_name_plural = "Sinxronizatsiya Loglari"
        ordering = ['-started_at']

    def __str__(self):
        return f"[{self.business.name}] {self.get_status_display()} — {self.started_at:%Y-%m-%d %H:%M}"
