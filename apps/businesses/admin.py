from django.contrib import admin
from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'website', 'telegram', 'instagram', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description', 'user__username', 'telegram', 'instagram')
    prepopulated_fields = {'slug': ('name',)}
