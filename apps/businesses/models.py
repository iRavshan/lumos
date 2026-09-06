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
    def telegram_username(self):
        tg = (self.telegram or '').strip()
        if not tg and hasattr(self, 'chatbot_config') and self.chatbot_config.telegram_bot_username:
            tg = self.chatbot_config.telegram_bot_username
        if not tg:
            return None
        tg = tg.replace('https://t.me/', '').replace('http://t.me/', '').replace('@', '').strip('/')
        return tg if tg else None

    @property
    def telegram_avatar_url(self):
        username = self.telegram_username
        if username:
            return f"https://t.me/i/userpic/320/{username}.jpg"
        return None

    @property
    def domain(self):
        if not self.website:
            return None
        ws = self.website.strip()
        if not ws.startswith('http://') and not ws.startswith('https://'):
            ws = f"https://{ws}"
        try:
            from urllib.parse import urlparse
            return urlparse(ws).netloc.lower().replace('www.', '')
        except Exception:
            return None

    @property
    def favicon_url(self):
        dom = self.domain
        if dom:
            return f"https://www.google.com/s2/favicons?domain={dom}&sz=128"
        return None

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
            bool(self.website),
            bool(self.telegram),
            bool(self.instagram),
            bool(self.phone),
            bool(self.description and len(self.description) > 20),
        ]
        filled = sum(1 for f in fields if f)
        return int((filled / len(fields)) * 100)
