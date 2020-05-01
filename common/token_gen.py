import jwt
import json
import os
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_aware, make_aware
from django.utils import timezone
import datetime
from oauth_client import generate_random_string, LOGIN_TIMEOUT
from .models import TemporaryCode, APIClient
from django.core.exceptions import PermissionDenied

FIREROAD_ISSUER = 'com.base12innovations.fireroad-server'

def get_aware_datetime(date_str):
    ret = parse_datetime(date_str)
    if not is_aware(ret):
        ret = make_aware(ret)
    return ret

def generate_token(request, user, expire_time, api_client=None):
    """Generates a JWT token for the given user that expires after the given
    number of seconds."""
    expiry_date = str(timezone.now() + datetime.timedelta(seconds=expire_time))
    # Specify which permissions this access token is allowed to authorize.
    # If no API client is given to this method, a universal permission is granted (this
    # corresponds to the mobile app use case!)
    payload = {
        'username': user.username,
        'permissions': (api_client.permissions_flag() if api_client else
                        APIClient.universal_permission_flag()),
        'iss': FIREROAD_ISSUER,
        'expires': expiry_date
    }
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return encoded

def extract_token_info(request, token):
    """Decodes the given JWT token and determines if it is valid. If so, returns
    the user associated with that token, an integer flag representing the permissions granted,
    and an error object of None. If not, returns None, None, and a dictionary explaining the error."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    except:
        return None, None, {'error': 'decode_error', 'error_description': 'The token could not be decoded'}
    try:
        if payload['iss'] != FIREROAD_ISSUER:
            return None, None, {'error': 'invalid_issuer', 'error_description': 'The issuer of this token does not have the correct value'}
        date = get_aware_datetime(payload['expires'])
        if date < timezone.now():
            return None, None, {'error': 'expired', 'error_description': 'The token has expired'}
        username = payload['username']

        permissions = payload['permissions']
    except KeyError:
        return None, None, {'error': 'incomplete_token', 'error_description': 'The token is missing one or more keys'}

    try:
        user = User.objects.get(username=username)
    except:
        return None, None, {'error': 'invalid_user', 'error_description': 'The token represents a non-existent user'}

    return user, permissions, None

def save_temporary_code(access_info):
    """Generates, saves, and returns a temporary code associated with the
    given access information JSON object."""

    code_storage = TemporaryCode.objects.create(access_info=json.dumps(access_info), code=generate_random_string(80))
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
