from django.contrib import admin
from .models import Business


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category', 'website', 'telegram', 'instagram', 'created_at')
    list_filter = ('category', 'created_at')
    search_fields = ('name', 'description', 'user__username', 'telegram', 'instagram')
    prepopulated_fields = {'slug': ('name',)}
