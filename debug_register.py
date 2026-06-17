import os
import django
from django.test import Client
import traceback

os.environ['DJANGO_SETTINGS_MODULE'] = 'elimuvise_project.settings'
django.setup()

client = Client()
for path in ['/register/', '/register/?role=advisor', '/']:
    try:
        response = client.get(path)
        print('PATH', path, 'STATUS', response.status_code)
        if response.status_code >= 400:
            print(response.content.decode('utf-8', errors='replace'))
    except Exception:
        print('PATH', path, 'EXCEPTION')
        traceback.print_exc()
