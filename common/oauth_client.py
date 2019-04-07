from .models import *
import json
from django.core.exceptions import PermissionDenied
import requests
import os
import base64
import urllib
from .models import OAuthCache
import random
from django.utils import timezone
from django.conf import settings

module_path = os.path.dirname(__file__)

REDIRECT_URI = settings.MY_BASE_URL + '/login/'
ISSUER = 'https://oidc.mit.edu/'
AUTH_CODE_URL = 'https://oidc.mit.edu/authorize'
AUTH_TOKEN_URL = 'https://oidc.mit.edu/token'
AUTH_USER_INFO_URL = 'https://oidc.mit.edu/userinfo'

LOGIN_TIMEOUT = 600
AUTH_SCOPES = ['email', 'openid', 'profile', 'offline_access']
AUTH_RESPONSE_TYPE = 'code'

def get_client_info():
    with open(os.path.join(module_path, 'oidc.txt'), 'r') as file:
        contents = file.read().strip()
        id, secret = contents.split('\n')
    return id, secret

def generate_random_string(length):
    choices = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.choice(choices) for _ in range(length))

def oauth_code_url(request, after_redirect=None):
    """after_redirect is used to redirect to an application site with a
    temporary code AFTER FireRoad has created the user's account. It should be
    None for mobile apps and a string for websites."""

    # Create a state and nonce, and save them
    cache = OAuthCache(state=generate_random_string(48), nonce=generate_random_string(48), redirect_uri=after_redirect)
    sem = request.GET.get('sem', '')
    if len(sem) > 0:
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
    id, secret = get_client_info()

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
    r = requests.post(AUTH_TOKEN_URL, auth=(id, secret), data=payload)
    if r.status_code != 200:
        return None, None, None, r.status_code

    # Parse token
    r_json = r.json()

    id_token = r_json['id_token']
    header, body, signature = id_token.split('.')
    header_text = base64.b64decode(header)
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
    headers = {"Authorization":"Bearer {}".format(acc_token)}
    r = requests.get(AUTH_USER_INFO_URL, headers=headers)
    return r.json(), r.status_code
