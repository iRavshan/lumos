from django.urls import path
from .views import (
    landing_view,
    onboarding_view,
    dashboard_view,
    edit_business_view,
    business_analytics_view,
)

app_name = 'businesses'

urlpatterns = [
    path('onboarding/', onboarding_view, name='onboarding'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/edit/', edit_business_view, name='edit'),
    path('dashboard/analytics/', business_analytics_view, name='analytics'),
]

