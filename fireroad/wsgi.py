"""
WSGI config for fireroad project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

# Add the root path for the Django server to sys.path so WSGI can find the
# right settings module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fireroad.settings")

application = get_wsgi_application()
