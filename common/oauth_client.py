"""Implements an OAuth client for the OIDC server."""

import base64
import json
import os
import random
import urllib

import requests

from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.conf import settings

from .models import *

MODULE_PATH = os.path.dirname(__file__)

REDIRECT_URI = settings.MY_BASE_URL + '/login/'
ISSUER = 'https://oidc.mit.edu/'
AUTH_CODE_URL = 'https://oidc.mit.edu/authorize'
AUTH_TOKEN_URL = 'https://oidc.mit.edu/token'
AUTH_USER_INFO_URL = 'https://oidc.mit.edu/userinfo'

LOGIN_TIMEOUT = 600
AUTH_SCOPES = ['email', 'openid', 'profile', 'offline_access']
AUTH_RESPONSE_TYPE = 'code'

def get_client_info():
    """Reads the ID and secret from the oidc.txt file in this directory."""
    with open(os.path.join(MODULE_PATH, 'oidc.txt'), 'r') as cred_file:
        contents = cred_file.read().strip()
        auth_id, secret = contents.split('\n')
    return auth_id, secret

def generate_random_string(length):
    """Generates a random alphanumeric string of the given length."""
    choices = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.choice(choices) for _ in range(length))

def oauth_code_url(request, after_redirect=None):
    """after_redirect is used to redirect to an application site with a
    temporary code AFTER FireRoad has created the user's account. It should be
    None for mobile apps and a string for websites."""

    # Create a state and nonce, and save them
    cache = OAuthCache(state=generate_random_string(48),
                       nonce=generate_random_string(48),
                       redirect_uri=after_redirect)
    sem = request.GET.get('sem', '')
    if sem:
        cache.current_semester = sem
    cache.save()
    return "{}?response_type={}&client_id={}&redirect_uri={}&scope={}&state={}&nonce={}".format(
        AUTH_CODE_URL,
        AUTH_RESPONSE_TYPE,
        get_client_info()[0],
        urllib.quote(REDIRECT_URI),
        urllib.quote(' '.join(AUTH_SCOPES)),
        cache.state,
        cache.nonce)

def get_user_info(request):
    """Returns user information for the second half of the OAuth login flow (after
    receiving an initial code from the OAuth provider)."""
    code = request.GET.get('code', None)
    state = request.GET.get('state', None)

    caches = OAuthCache.objects.filter(state=state)
    if caches.count() == 0:
        raise PermissionDenied

    acc_token, info, all_json, status = get_oauth_id_token(request, code, state)
    if acc_token is None:
        return None, status, None

    result, status = get_user_info_with_token(request, acc_token)
    if result is not None:
        if "refresh_token" in all_json:
            result[u'refresh_token'] = all_json["refresh_token"]
    return result, status, info

def get_oauth_id_token(request, code, state, refresh=False):
    """Requests an OAuth token from the OAuth provider using the given login code."""
    auth_id, secret = get_client_info()

    if refresh:
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': code
        }
    else:
        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
    r = requests.post(AUTH_TOKEN_URL, auth=(auth_id, secret), data=payload)
    if r.status_code != 200:
        return None, None, None, r.status_code

    # Parse token
    r_json = r.json()

    id_token = r_json['id_token']
    _, body, _ = id_token.split('.')
    # header_text = base64.b64decode(header)
    body += "=" * ((4 - len(body) % 4) % 4)
    body_text = base64.b64decode(body)

    body = json.loads(body_text)
    if body['iss'] != ISSUER:
        raise PermissionDenied
    nonce = body['nonce']
    caches = OAuthCache.objects.filter(state=state)
    found = False
    info = {}
    for cache in caches:
        if cache.nonce == nonce:
            current_date = timezone.now()
            if (current_date - cache.date).total_seconds() > LOGIN_TIMEOUT:
                return None, None, None, 408
            found = True
            info["sem"] = cache.current_semester
            if cache.redirect_uri is not None:
                info["redirect"] = cache.redirect_uri
            break
    if not found:
        raise PermissionDenied
    caches.delete()

    access_token = r_json["access_token"]
    return access_token, info, r_json, r.status_code

def get_user_info_with_token(request, acc_token):
    """Sends the given access token to the OAuth provider and uses it to request user
    information."""
    headers = {"Authorization":"Bearer {}".format(acc_token)}
    r = requests.get(AUTH_USER_INFO_URL, headers=headers)
    return r.json(), r.status_code
