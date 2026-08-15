from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chatbot_chat'),
    path('voice-chat/', views.voice_chat, name='chatbot_voice_chat'),
]
