from django.urls import path
from .views import (
    api_chatbot_config,
    api_chat_message,
    api_poll_widget,
    widget_iframe_view,
    demo_page_view,
    chatbot_settings_view,
    chatbot_history_view,
    inbox_view,
    update_lead_view,
    telegram_bot_settings_view,
    api_telegram_webhook,
)

app_name = 'chatbot'

urlpatterns = [
    # Public APIs for Widgets
    path('api/v1/<str:api_key>/config/', api_chatbot_config, name='api_config'),
    path('api/v1/<str:api_key>/chat/', api_chat_message, name='api_chat'),
    path('api/v1/<str:api_key>/poll/', api_poll_widget, name='api_poll'),
    path('api/v1/telegram/webhook/<str:api_key>/', api_telegram_webhook, name='telegram_webhook'),

    # Standalone Embed Iframe & Demo
    path('widget/<str:api_key>/', widget_iframe_view, name='widget_iframe'),
    path('widget/<str:api_key>/demo/', demo_page_view, name='demo_page'),

    # Dashboard Management
    path('dashboard/inbox/', inbox_view, name='inbox'),
    path('dashboard/inbox/<str:session_id>/', inbox_view, name='inbox_detail'),
    path('dashboard/inbox/<str:session_id>/update/', update_lead_view, name='update_lead'),
    path('dashboard/chatbot/settings/', chatbot_settings_view, name='settings'),
    path('dashboard/chatbot/telegram/', telegram_bot_settings_view, name='telegram_settings'),
    path('dashboard/chatbot/history/', chatbot_history_view, name='history'),
]
