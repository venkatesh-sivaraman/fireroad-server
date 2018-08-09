import jwt
import json
import os
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware, make_aware
from django.utils import timezone
import datetime

FIREROAD_ISSUER = 'com.base12innovations.fireroad-server'

def get_aware_datetime(date_str):
    ret = parse_datetime(date_str)
    if not is_aware(ret):
        ret = make_aware(ret)
    return ret

def generate_token(request, user, expire_time):
    """Generates a JWT token for the given user that expires after the given
    number of seconds."""
    expiry_date = str(timezone.now() + datetime.timedelta(seconds=expire_time))
    payload = {
        'username': user.username,
        'iss': FIREROAD_ISSUER,
        'expires': expiry_date
    }
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return encoded

def get_user_for_token(request, token):
    """Decodes the given JWT token and determines if it is valid. If so, returns
    the user associated with that token and None. If not, returns None and a
    dictionary explaining the error."""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    try:
        if payload['iss'] != FIREROAD_ISSUER:
            return None, {'error': 'invalid_issuer', 'error_description': 'The issuer of this token does not have the correct value'}
        date = get_aware_datetime(payload['expires'])
        if date < timezone.now():
            return None, {'error': 'expired', 'error_description': 'The token has expired'}
        username = payload['username']
    except KeyError:
        return None, {'error': 'incomplete_token', 'error_description': 'The token is missing one or more keys'}

    try:
        user = User.objects.get(username=username)
    except:
        return None, {'error': 'invalid_user', 'error_description': 'The token represents a non-existent user'}

    return user, None
