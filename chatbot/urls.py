from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chatbot_chat'),
    path('voice-chat/', views.voice_chat, name='chatbot_voice_chat'),
    path('errors/', views.get_errors, name='chatbot_errors'),
    path('log-error/', views.log_error, name='chatbot_log_error'),
    path('statistics/', views.statistics_dashboard, name='chatbot_statistics'),
    path('log-request/', views.log_request, name='chatbot_log_request'),
    path('check-ticket/', views.check_ticket, name='chatbot_check_ticket'),
    path('submit-feedback/', views.submit_feedback, name='chatbot_submit_feedback'),
]
