import secrets
from django.db import models
from django.utils import timezone
from apps.businesses.models import Business


def generate_staff_token():
    return f"staff_{secrets.token_urlsafe(24)}"


class StaffMember(models.Model):
    ROLE_CHOICES = (
        ('operator', 'Operator (Mijozlarga javob beruvchi)'),
        ('supervisor', 'Supervisor (Nazoratchi va Boshqaruvchi)'),
    )

    business = models.ForeignKey(
        Business, 
        on_delete=models.CASCADE, 
        related_name='staff_members',
        verbose_name="Biznes"
    )
    name = models.CharField(
        max_length=100, 
        verbose_name="Xodim ismi"
    )
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='operator',
        verbose_name="Xodim roli"
    )
    telegram_username = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Telegram @username",
        help_text="@username shaklida kiriting"
    )
    telegram_chat_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Telegram Chat ID"
    )
    auth_token = models.CharField(
        max_length=64, 
        unique=True, 
        default=generate_staff_token,
        verbose_name="TMA Kirish Tokeni"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Xodim faolmi?"
    )
    is_online = models.BooleanField(
        default=True, 
        verbose_name="Navbatchilikda / Onlayn"
    )
    sla_minutes = models.PositiveIntegerField(
        default=5, 
        verbose_name="SLA Javob berish vaqti (daqiqa)",
        help_text="Operator ushbu vaqt ichida javob bermasa, chat avtomatik ravishda Supervisorga eskalatsiya qilinadi"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan sana")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Xodim (Operator/Supervisor)"
        verbose_name_plural = "Xodimlar (Operatorlar & Supervisorlar)"
        ordering = ['role', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_role_display()}) - {self.business.name}"

    @property
    def clean_telegram(self):
        if not self.telegram_username:
            return ""
        tg = self.telegram_username.strip()
        return tg if tg.startswith('@') else f"@{tg}"

    @property
    def total_handled(self):
        return self.operator_escalations.count()

    @property
    def sla_breaches(self):
        return self.operator_escalations.filter(is_sla_breached=True).count()

    @property
    def on_time_rate(self):
        total = self.total_handled
        if total == 0:
            return 100
        breached = self.sla_breaches
        return int(((total - breached) / total) * 100)


class EscalationLog(models.Model):
    RESOLVED_CHOICES = (
        ('operator', 'Operator tomonidan'),
        ('supervisor', 'Supervisor tomonidan'),
        ('ai', 'AI tomonidan'),
    )

    session = models.ForeignKey(
        'chatbot.ChatSession', 
        on_delete=models.CASCADE, 
        related_name='escalation_logs',
        verbose_name="Suhbat"
    )
    operator = models.ForeignKey(
        StaffMember, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='operator_escalations',
        verbose_name="Biriktirilgan operator"
    )
    supervisor = models.ForeignKey(
        StaffMember, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='supervisor_escalations',
        verbose_name="Eskalatsiya qilingan supervisor"
    )
    escalation_reason = models.TextField(
        blank=True, 
        verbose_name="Eskalatsiya sababi"
    )
    escalated_to_operator_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Operatorga yuborilgan vaqt"
    )
    operator_first_replied_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Operatorning 1-javobi vaqti"
    )
    escalated_to_supervisor_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Supervisorga o'tgan vaqt"
    )
    is_sla_breached = models.BooleanField(
        default=False, 
        verbose_name="SLA buzilganmi (kechikkanmi)?"
    )
    resolved_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Hal qilingan vaqt"
    )
    resolved_by = models.CharField(
        max_length=20, 
        choices=RESOLVED_CHOICES, 
        blank=True, 
        verbose_name="Kim tomonidan hal qilindi"
    )

    class Meta:
        verbose_name = "Eskalatsiya Tarixi"
        verbose_name_plural = "Eskalatsiyalar Tarixi"
        ordering = ['-escalated_to_operator_at']

    def __str__(self):
        return f"Escalation for {self.session} (Operator: {self.operator})"
