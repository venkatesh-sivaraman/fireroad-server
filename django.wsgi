import os, sys

path='/mit/venkats/Scripts/django/fireroad'

if path not in sys.path:
	sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'fireroad.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
