from django.urls import path
from .views import (
    landing_view,
    onboarding_view,
    dashboard_view,
    edit_business_view,
    business_analytics_view,
    favicon_proxy_view,
    help_view,
    terms_view,
    privacy_view,
    feedback_view,
    subscription_view,
    notifications_view,
)

app_name = 'businesses'

urlpatterns = [
    path('onboarding/', onboarding_view, name='onboarding'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/edit/', edit_business_view, name='edit'),
    path('dashboard/analytics/', business_analytics_view, name='analytics'),
    path('subscription/', subscription_view, name='subscription'),
    path('dashboard/subscription/', subscription_view),
    path('notifications/', notifications_view, name='notifications'),
    path('dashboard/notifications/', notifications_view),
    path('help/', help_view, name='help'),
    path('dashboard/help/', help_view),
    path('feedback/', feedback_view, name='feedback'),
    path('dashboard/feedback/', feedback_view),
    path('terms/', terms_view, name='terms'),
    path('privacy/', privacy_view, name='privacy'),
    path('api/favicon/<int:business_id>/', favicon_proxy_view, name='favicon_proxy'),
]

