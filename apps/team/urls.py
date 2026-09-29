from django.urls import path
from .views import (
    team_list_view,
    team_create_view,
    team_edit_view,
    team_delete_view,
    team_analytics_view,
    staff_setup_password_view,
    tma_operator_view,
    tma_supervisor_view,
    tma_toggle_status_api,
    tma_send_reply_api,
    tma_resolve_chat_api,
    tma_poll_messages_api,
)

app_name = 'team'

urlpatterns = [
    # Web Dashboard
    path('dashboard/team/', team_list_view, name='team_list'),
    path('dashboard/team/add/', team_create_view, name='team_create'),
    path('dashboard/team/<int:staff_id>/edit/', team_edit_view, name='team_edit'),
    path('dashboard/team/<int:staff_id>/delete/', team_delete_view, name='team_delete'),
    path('dashboard/team/analytics/', team_analytics_view, name='team_analytics'),

    # Staff Web Setup (Set Password)
    path('team/setup/<str:token>/', staff_setup_password_view, name='staff_setup'),

    # Telegram Mini App (TMA)
    path('tma/operator/<str:token>/', tma_operator_view, name='tma_operator'),
    path('tma/supervisor/<str:token>/', tma_supervisor_view, name='tma_supervisor'),

    # TMA APIs
    path('api/tma/<str:token>/toggle-status/', tma_toggle_status_api, name='tma_toggle_status'),
    path('api/tma/<str:token>/<str:session_id>/reply/', tma_send_reply_api, name='tma_reply'),
    path('api/tma/<str:token>/<str:session_id>/resolve/', tma_resolve_chat_api, name='tma_resolve'),
    path('api/tma/<str:token>/<str:session_id>/messages/', tma_poll_messages_api, name='tma_messages'),
]
