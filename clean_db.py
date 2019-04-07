"""
This script is responsible for day-to-day maintenance of the server, which
currently consists of removing expired OAuth caches and temporary codes.
"""
import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
django.setup()

from common.models import *
from common.oauth_client import LOGIN_TIMEOUT
from django.db import DatabaseError, transaction
from django import db
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import datetime

def clean_db():
    # Time before which all tokens and codes will be expired
    expired_threshold = timezone.now() - datetime.timedelta(seconds=LOGIN_TIMEOUT)

    num_objs = 0
    for obj in OAuthCache.objects.all():
        if obj.date < expired_threshold:
            num_objs += 1
            obj.delete()
    print("{} OAuth caches deleted".format(num_objs))
    
    num_objs = 0
    for obj in TemporaryCode.objects.all():
        if obj.date < expired_threshold:
            num_objs += 1
            obj.delete()
    print("{} temporary codes deleted".format(num_objs))

if __name__ == '__main__':
    clean_db()
