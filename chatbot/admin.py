from django.contrib import admin
from .models import ChatErrorLog, UnansweredQuestion, ChatRequestLog

@admin.register(ChatErrorLog)
class ChatErrorLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'platform', 'endpoint', 'error_message')
    list_filter = ('platform', 'endpoint', 'timestamp')
    search_fields = ('user_input', 'error_message', 'traceback')
    readonly_fields = ('timestamp', 'platform', 'endpoint', 'user_input', 'error_message', 'traceback')

@admin.register(UnansweredQuestion)
class UnansweredQuestionAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'platform', 'status', 'question')
    list_filter = ('status', 'platform', 'timestamp')
    search_fields = ('question',)
    list_editable = ('status',)

@admin.register(ChatRequestLog)
class ChatRequestLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'platform', 'ip_address', 'user_id', 'question')
    list_filter = ('platform', 'timestamp')
    search_fields = ('question', 'ip_address', 'user_id', 'device')
    readonly_fields = ('timestamp', 'platform', 'device', 'ip_address', 'user_id', 'question')
