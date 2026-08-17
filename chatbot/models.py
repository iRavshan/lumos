from django.db import models

class ChatErrorLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")
    platform = models.CharField(max_length=50, default='web', verbose_name="Platforma")
    endpoint = models.CharField(max_length=50, verbose_name="So'rov turi (Text/Voice)")
    user_input = models.TextField(blank=True, null=True, verbose_name="Foydalanuvchi so'rovi")
    error_message = models.TextField(verbose_name="Xatolik xabari")
    traceback = models.TextField(blank=True, null=True, verbose_name="Batafsil (Traceback)")

    class Meta:
        verbose_name = "Chat Xatolik"
        verbose_name_plural = "Chat Xatoliklari"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.endpoint} xatoligi - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

class UnansweredQuestion(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Kutilmoqda'),
        ('answered', 'Javob berildi'),
    )
    question = models.TextField(verbose_name="Savol")
    platform = models.CharField(max_length=50, default='web', verbose_name="Platforma")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    
    ticket_id = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Ticket ID")
    password = models.CharField(max_length=20, blank=True, null=True, verbose_name="Parol")
    answer = models.TextField(blank=True, null=True, verbose_name="Operator javobi")
    answered_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="Javob bergan operator")
    answered_at = models.DateTimeField(blank=True, null=True, verbose_name="Javob berilgan vaqt")
    
    FEEDBACK_CHOICES = (
        ('yes', 'Ha, qoniqdim'),
        ('partially', 'Qisman'),
        ('no', "Yo'q, qoniqmadim"),
    )
    feedback = models.CharField(max_length=20, choices=FEEDBACK_CHOICES, blank=True, null=True, verbose_name="Foydalanuvchi bahosi")

    class Meta:
        verbose_name = "Javobsiz Savol"
        verbose_name_plural = "Javobsiz Savollar"
        ordering = ['-timestamp']

    def __str__(self):
        if self.ticket_id:
            return f"[{self.ticket_id}] {self.question[:40]}..."
        return f"{self.question[:50]}..."

class ChatRequestLog(models.Model):
    question = models.TextField(verbose_name="Foydalanuvchi so'rovi")
    platform = models.CharField(max_length=50, default='web', verbose_name="Platforma")
    device = models.CharField(max_length=255, blank=True, null=True, verbose_name="Qurilma")
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name="IP Manzil")
    user_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Foydalanuvchi ID")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")

    class Meta:
        verbose_name = "Chat So'rov"
        verbose_name_plural = "Chat So'rovlari"
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.platform}] {self.question[:40]}..."
