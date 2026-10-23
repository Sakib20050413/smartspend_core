"""
WSGI config for smartspend project.

It exposes the WSGI callable as a module-level variable named ``application`` and ``app``.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartspend.settings')

application = get_wsgi_application()
app = application
