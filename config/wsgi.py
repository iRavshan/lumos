import os
from django.core.wsgi import get_wsgi_application

print('Bismillāhi awwalahu wa ākhirahu')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()