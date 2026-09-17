from django.contrib import admin
from .models import BusinessKnowledge


@admin.register(BusinessKnowledge)
class BusinessKnowledgeAdmin(admin.ModelAdmin):
    list_display = ('business', 'title', 'source_url', 'chunk_index', 'created_at')
    list_filter = ('business',)
    search_fields = ('title', 'content', 'source_url')
    readonly_fields = ('created_at',)
    ordering = ('business', 'source_url', 'chunk_index')
