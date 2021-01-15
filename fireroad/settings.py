"""
Base Django settings for fireroad project. These defaults are set up to work
with the development server (which runs locally with python manage.py
runserver), and are imported and partially overwritten by settings_dev and
settings_prod.
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Unzip the catalog data into the data directory
CATALOG_BASE_DIR = "data/catalogs"

# Use the Django default login page for local debugging
LOGIN_URL = "/admin/login"

# Security settings

# If True, login redirects will be required to be registered as a RedirectURL
# Set to True in production!
RESTRICT_AUTH_REDIRECTS = False

with open(os.path.join(os.path.dirname(__file__), 'secret.txt')) as f:
    SECRET_KEY = f.read().strip()

DEBUG = True

# Constructing URLs

ALLOWED_HOSTS = ['localhost', 'lvh.me']

MY_BASE_URL = 'https://lvh.me:8000'

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admindocs',
    'recommend',
    'common',
    'sync',
    'requirements',
    'courseupdater',
    'catalog',
    'analytics'
]

MIDDLEWARE_CLASSES = [
    #'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'analytics.request_counter.RequestCounterMiddleware'
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend'
]

ROOT_URLCONF = 'fireroad.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fireroad.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Set up email if email_creds.txt file is present in this directory (format should be "host,email address,password")
email_creds_path = os.path.join(os.path.dirname(__file__), 'email_creds.txt')
if os.path.exists(email_creds_path):
    with open(email_creds_path, "r") as file:
        host, email, passwd = file.readline().strip().split(",")

        FR_EMAIL_ENABLED = True
        EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
        EMAIL_HOST = host # e.g. smtp.gmail.com
        EMAIL_USE_TLS = True
        EMAIL_PORT = 587
        EMAIL_HOST_USER = email
        EMAIL_HOST_PASSWORD = passwd
else:
    FR_EMAIL_ENABLED = False

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, "static")

'''STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "catalog-files")
]'''

LOGGING = {
    'version': 1,
    'handlers': {
        'console':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.request': {
            'handlers':['console'],
            'propagate': True,
            'level':'DEBUG',
        }
    },
}
