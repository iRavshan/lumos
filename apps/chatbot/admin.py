from django.contrib import admin
from .models import ChatbotConfig, ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'created_at')


@admin.register(ChatbotConfig)
class ChatbotConfigAdmin(admin.ModelAdmin):
    list_display = ('business', 'bot_name', 'api_key', 'is_active', 'created_at')
    search_fields = ('business__name', 'bot_name', 'api_key')
    list_filter = ('is_active', 'created_at')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'chatbot', 'created_at', 'updated_at')
    search_fields = ('session_id', 'chatbot__business__name')
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('chatbot', 'session', 'role', 'content_preview', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'chatbot__business__name')

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = "Xabar mazmuni"
