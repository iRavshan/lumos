import secrets
from django.db import models
from apps.businesses.models import Business


def generate_api_key():
    return f"lumos_{secrets.token_hex(16)}"


class ChatbotConfig(models.Model):
    business = models.OneToOneField(
        Business, 
        on_delete=models.CASCADE, 
        related_name='chatbot_config',
        verbose_name="Biznes"
    )
    api_key = models.CharField(
        max_length=64, 
        unique=True, 
        db_index=True,
        default=generate_api_key,
        verbose_name="Vidjet API Kaliti"
    )
    bot_name = models.CharField(
        max_length=100, 
        default="AI Yordamchi",
        verbose_name="Bot nomi"
    )
    welcome_message = models.TextField(
        default="Assalomu alaykum! Sizga qanday yordam bera olaman?",
        verbose_name="Salomlashish matni"
    )
    theme_color = models.CharField(
        max_length=20, 
        default="#4f46e5",
        verbose_name="Asosiy rang kodi (Hex)"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Chatbot faolmi?"
    )
    extra_knowledge = models.TextField(
        blank=True, 
        verbose_name="Qo'shimcha ma'lumotlar va FAQ",
        help_text="Masalan: Ish vaqti: 09:00 - 18:00, Toshkent bo'yicha yetkazib berish bepul, To'lov usullari: Click, Payme, Naqd."
    )
    suggested_questions = models.TextField(
        blank=True, 
        default="Xizmatlaringiz haqida ma'lumot bering\nQanday bog'lansam bo'ladi?\nIsh vaqtingiz qachon?",
        verbose_name="Tavsiya etilgan tezkor savollar",
        help_text="Har bir qatorda 1 ta tezkor savol yozing"
    )
    # Telegram Bot Integration fields
    telegram_bot_token = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        verbose_name="Telegram Bot Tokeni",
        help_text="@BotFather dan olingan HTTP API Token"
    )
    telegram_bot_username = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Telegram Bot Username"
    )
    telegram_bot_name = models.CharField(
        max_length=150, 
        blank=True, 
        null=True, 
        verbose_name="Telegram Bot Nomi"
    )
    telegram_bot_active = models.BooleanField(
        default=False, 
        verbose_name="Telegram Bot faolmi?"
    )
    # Human-like delay and split messages settings
    response_delay_enabled = models.BooleanField(
        default=True,
        verbose_name="Inson kabi kechiktirib javob berish (Human-like delay)"
    )
    first_message_delay_seconds = models.IntegerField(
        default=5,
        verbose_name="Birinchi xabarga kechikish (soniya)"
    )
    subsequent_message_delay_seconds = models.IntegerField(
        default=10,
        verbose_name="Keyingi xabarlarga kechikish (soniya)"
    )
    response_delay_seconds = models.IntegerField(
        default=5,
        verbose_name="Kechikish davomiyligi"
    )
    split_messages = models.BooleanField(
        default=True,
        verbose_name="Matnlarni bo'laklarga ajratib yuborish"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Chatbot Sozlamasi"
        verbose_name_plural = "Chatbot Sozlamalari"

    def __str__(self):
        return f"{self.business.name} - {self.bot_name}"

    def get_suggested_questions_list(self):
        if not self.suggested_questions:
            return []
        return [q.strip() for q in self.suggested_questions.split('\n') if q.strip()]


class ChatSession(models.Model):
    STATUS_CHOICES = (
        ('new', 'Yangi'),
        ('in_progress', 'Jarayonda'),
        ('completed', 'Yakunlangan'),
        ('archived', 'Arxiv'),
    )
    chatbot = models.ForeignKey(
        ChatbotConfig, 
        on_delete=models.CASCADE, 
        related_name='sessions'
    )
    session_id = models.CharField(max_length=100, db_index=True)
    visitor_name = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Murojaatchi ismi"
    )
    visitor_phone = models.CharField(
        max_length=50, 
        blank=True, 
        verbose_name="Telefon raqami"
    )
    visitor_email = models.EmailField(
        blank=True, 
        verbose_name="Email"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new',
        verbose_name="Holat"
    )
    notes = models.TextField(
        blank=True, 
        verbose_name="Izoh / Eslatma"
    )
    visitor_ip = models.GenericIPAddressField(
        null=True, 
        blank=True, 
        verbose_name="IP manzil"
    )
    # Escalation & Staff assignment fields
    assigned_staff = models.ForeignKey(
        'team.StaffMember', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_sessions',
        verbose_name="Biriktirilgan xodim"
    )
    ESCALATION_CHOICES = (
        ('ai', 'AI Javob bermoqda'),
        ('waiting_operator', 'Operator javobi kutilmoqda'),
        ('operator_active', 'Operator muloqotda'),
        ('escalated_supervisor', 'Supervisorga kechiktirildi'),
        ('resolved', 'Hal qilindi'),
    )
    escalation_status = models.CharField(
        max_length=30, 
        choices=ESCALATION_CHOICES, 
        default='ai',
        verbose_name="Eskalatsiya holati"
    )
    is_escalated = models.BooleanField(
        default=False, 
        verbose_name="Operatorga uzatilganmi?"
    )
    escalated_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Eskalatsiya vaqti"
    )
    sla_deadline = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="SLA muddati"
    )
    last_message_at = models.DateTimeField(
        auto_now=True, 
        db_index=True, 
        verbose_name="So'nggi xabar vaqti"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Birinchi murojaat")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Murojaat Sessiyasi"
        verbose_name_plural = "Murojaatlar (Leads)"
        ordering = ['-last_message_at', '-created_at']

    def __str__(self):
        return f"{self.display_name} ({self.chatbot.business.name})"

    @property
    def display_name(self):
        if self.visitor_name:
            return self.visitor_name
        if self.visitor_phone:
            return self.visitor_phone
        if self.visitor_email:
            return self.visitor_email
        short_id = self.session_id.replace('sess_', '')[:6].upper()
        return f"Murojaatchi #{short_id}"

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()

    @property
    def user_messages_count(self):
        return self.messages.filter(role='user').count()

    @property
    def is_sla_breached(self):
        if self.escalation_status == 'waiting_operator' and self.sla_deadline:
            from django.utils import timezone
            return timezone.now() > self.sla_deadline
        return False


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ('user', 'Mijoz'),
        ('assistant', 'AI Bot'),
        ('staff', 'Xodim (Operator/Supervisor)'),
    )
    chatbot = models.ForeignKey(
        ChatbotConfig, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    session = models.ForeignKey(
        ChatSession, 
        on_delete=models.CASCADE, 
        related_name='messages',
        null=True,
        blank=True
    )
    sender_staff = models.ForeignKey(
        'team.StaffMember', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='sent_messages',
        verbose_name="Yuborgan xodim"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:40]}..."

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.session_id:
            from django.utils import timezone
            ChatSession.objects.filter(pk=self.session_id).update(last_message_at=self.created_at or timezone.now())
            try:
                from django.core.cache import cache
                if self.chatbot and self.chatbot.business_id:
                    biz_key = f"biz:v:{self.chatbot.business_id}"
                    try:
                        cache.incr(biz_key)
                    except Exception:
                        cache.set(biz_key, 1, timeout=86400)
                if self.session and self.session.session_id:
                    cache.set(f"sess:last_id:{self.session.session_id}", self.id, timeout=86400)
            except Exception:
                pass

    @property
    def formatted_content(self):
        """
        Returns safe HTML formatted content for display in inbox/templates.
        """
        if not self.content:
            return ""
        if self.role == 'user':
            import html
            return html.escape(self.content)
        from .telegram_service import sanitize_for_telegram
        return sanitize_for_telegram(self.content)

    @property
    def date_divider(self):
        """
        Returns a Telegram-style date label: 'Bugun', 'Kecha', or formatted date.
        """
        from django.utils import timezone
        now = timezone.localtime(timezone.now())
        msg_time = timezone.localtime(self.created_at)

        delta_days = (now.date() - msg_time.date()).days
        if delta_days == 0:
            return "Bugun"
        elif delta_days == 1:
            return "Kecha"
        else:
            months = [
                '', 'yanvar', 'fevral', 'mart', 'aprel', 'may', 'iyun',
                'iyul', 'avgust', 'sentyabr', 'oktyabr', 'noyabr', 'dekabr'
            ]
            if now.year == msg_time.year:
                return f"{msg_time.day}-{months[msg_time.month]}"
            return f"{msg_time.day}-{months[msg_time.month]}, {msg_time.year}"


