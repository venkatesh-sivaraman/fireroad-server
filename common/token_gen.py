"""Generates tokens that authorize users to access FireRoad."""

import datetime
import json
import jwt

from django.contrib.auth.models import User
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware, make_aware
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from .oauth_client import generate_random_string, LOGIN_TIMEOUT
from .models import TemporaryCode

FIREROAD_ISSUER = 'com.base12innovations.fireroad-server'

def get_aware_datetime(date_str):
    """Parses a date string and returns it as a time zone-aware datetime object."""
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
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except BaseException:
        return None, {
            'error': 'decode_error',
            'error_description': 'The token could not be decoded'
        }
    try:
        if payload['iss'] != FIREROAD_ISSUER:
            return None, {
                'error': 'invalid_issuer',
                'error_description': 'The issuer of this token does not have the correct value'
            }
        date = get_aware_datetime(payload['expires'])
        if date < timezone.now():
            return None, {
                'error': 'expired',
                'error_description': 'The token has expired'
            }
        username = payload['username']
    except KeyError:
        return None, {
            'error': 'incomplete_token',
            'error_description': 'The token is missing one or more keys'
        }

    try:
        user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        return None, {
            'error': 'invalid_user',
            'error_description': 'The token represents a non-existent user'
        }

    return user, None

def save_temporary_code(access_info):
    """Generates, saves, and returns a temporary code associated with the
    given access information JSON object."""

    code_storage = TemporaryCode.objects.create(
        access_info=json.dumps(access_info),
        code=generate_random_string(80))
    code_storage.save()
    return code_storage.code

def get_access_info_with_temporary_code(code):
    """Validates the given temporary code and retrieves the access info associated
    with it as a JSON object, deleting the code storage afterward. Raises
    PermissionDenied if the code is not found or is expired."""

    try:
        code_storage = TemporaryCode.objects.get(code=code)
        expiry_date = code_storage.date + datetime.timedelta(seconds=LOGIN_TIMEOUT)
        if expiry_date < timezone.now():
            raise PermissionDenied
        ret = json.loads(code_storage.access_info)
        code_storage.delete()
        return ret
    except:
        raise PermissionDenied
