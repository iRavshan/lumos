from django.views.generic import TemplateView
from django.contrib import admin
from django.urls import path, include
from django.conf import settings 

admin.site.site_header = "Deepland Developers"
admin.site.site_title = "Deepland Developers"
admin.site.index_title = "Boshqaruv paneliga xush kelibsiz"

from apps.businesses.views import landing_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_view, name='home'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('', include('apps.businesses.urls', namespace='businesses')),
    path('', include('apps.chatbot.urls', namespace='chatbot')),
    path('', include('apps.team.urls', namespace='team')),
    path('humans.txt', TemplateView.as_view(template_name='humans.txt', content_type='text/plain')),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('llms.txt', TemplateView.as_view(template_name='llms.txt', content_type='text/plain')),
]

handler404 = 'config.views.custom_404'
handler500 = 'config.views.custom_500'
handler403 = 'config.views.custom_403'
handler400 = 'config.views.custom_400'