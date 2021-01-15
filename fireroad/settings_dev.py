"""
Django settings for fireroad project in dev server environment only.
"""

import os
from .settings import *

# Location of catalog files on the server
CATALOG_BASE_DIR = "/var/www/html/catalogs"

# URL used to log in
LOGIN_URL = "/login_touchstone"

# Security settings more relaxed on dev server
RESTRICT_AUTH_REDIRECTS = False
DEBUG = True

# For building URLs and validating hosts 
ALLOWED_HOSTS = ['fireroad-dev.mit.edu']
MY_BASE_URL = 'https://fireroad-dev.mit.edu'

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

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'analytics.request_counter.RequestCounterMiddleware'
]
