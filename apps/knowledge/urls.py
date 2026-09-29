from django.urls import path
from .views import sync_knowledge_view, sync_status_view

app_name = 'knowledge'

urlpatterns = [
    path('api/sync/', sync_knowledge_view, name='sync'),
    path('api/sync/status/', sync_status_view, name='sync_status'),
]
