from django.contrib import admin
from .models import StaffMember, EscalationLog


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'role', 'telegram_username', 'is_active', 'is_online', 'sla_minutes')
    list_filter = ('role', 'is_active', 'is_online')
    search_fields = ('name', 'telegram_username', 'business__name')


@admin.register(EscalationLog)
class EscalationLogAdmin(admin.ModelAdmin):
    list_display = ('session', 'operator', 'supervisor', 'is_sla_breached', 'escalated_to_operator_at', 'resolved_at')
    list_filter = ('is_sla_breached', 'resolved_by')
    search_fields = ('session__session_id', 'operator__name', 'supervisor__name')
