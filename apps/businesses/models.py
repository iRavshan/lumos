from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify


class Business(models.Model):
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='business',
        verbose_name="Foydalanuvchi"
    )
    name = models.CharField(
        max_length=200, 
        verbose_name="Biznes nomi"
    )
    slug = models.SlugField(
        max_length=250, 
        unique=True, 
        blank=True
    )
    category = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Biznes sohasi / Faoliyat turi",
        help_text="Masalan: IT, Ta'lim, Savdo, Restoran, Xizmat ko'rsatish"
    )
    website = models.URLField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Vebsayt manzili",
        help_text="https://misol.uz ko'rinishida"
    )
    telegram = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Telegram manzili",
        help_text="@username yoki havola shaklida"
    )
    instagram = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Instagram manzili",
        help_text="@username yoki havola shaklida"
    )
    phone = models.CharField(
        max_length=30, 
        blank=True, 
        verbose_name="Aloqa telefoni"
    )
    description = models.TextField(
        verbose_name="Biznes haqida ma'lumot",
        help_text="Biznesingiz, ko'rsatadigan xizmatlar yoki mahsulotlar haqida batafsil ma'lumot"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Yaratilgan sana"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name="Tahrirlangan sana"
    )

    class Meta:
        verbose_name = "Biznes"
        verbose_name_plural = "Bizneslar"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            if not base_slug:
                base_slug = f"business-{self.user_id}"
            slug = base_slug
            counter = 1
            while Business.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def telegram_link(self):
        if not self.telegram:
            return None
        tg = self.telegram.strip()
        if tg.startswith('http://') or tg.startswith('https://'):
            return tg
        if tg.startswith('@'):
            return f"https://t.me/{tg[1:]}"
        return f"https://t.me/{tg}"

    @property
    def instagram_link(self):
        if not self.instagram:
            return None
        ig = self.instagram.strip()
        if ig.startswith('http://') or ig.startswith('https://'):
            return ig
        if ig.startswith('@'):
            return f"https://instagram.com/{ig[1:]}"
        return f"https://instagram.com/{ig}"

    @property
    def completion_percentage(self):
        fields = [
            bool(self.name),
            bool(self.category),
            bool(self.website),
            bool(self.telegram),
            bool(self.instagram),
            bool(self.phone),
            bool(self.description and len(self.description) > 20),
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)
