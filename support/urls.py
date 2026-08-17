from django.urls import path
from . import views

urlpatterns = [
    path('operator/', views.operator_panel, name='operator_panel'),
    path('operator/answer/<int:pk>/', views.operator_answer, name='operator_answer'),
    path('supervisor/', views.supervisor_panel, name='supervisor_panel'),
]
