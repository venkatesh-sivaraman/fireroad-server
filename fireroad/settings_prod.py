"""
Django settings for fireroad project in prod environment only.
"""

import os
from .settings import *

# Location of catalog files on the server
CATALOG_BASE_DIR = "/var/www/html/catalogs"

# URL used to log in (e.g. to admin)
LOGIN_URL = "/login_touchstone"

# Security settings
RESTRICT_AUTH_REDIRECTS = True
DEBUG = False

# For building URLs and validating hosts 
ALLOWED_HOSTS = ['fireroad.mit.edu']
MY_BASE_URL = 'https://fireroad.mit.edu'

# MySQL database
import dbcreds

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': dbcreds.dbname, # For scripts: venkats+fireroad
        'USER': dbcreds.username,
        'PASSWORD': dbcreds.password,
        'HOST': dbcreds.host, # For scripts: sql.mit.edu
        'PORT': '3306',
    }
}


