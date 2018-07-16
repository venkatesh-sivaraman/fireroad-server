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

module_path = os.path.dirname(__file__)

REDIRECT_URI = 'http://lvh.me:8000/recommend/link_user'
ISSUER = 'https://oidc.mit.edu/'
LOGIN_TIMEOUT = 300

def generate_random_string(length):
    choices = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(random.choice(choices) for _ in range(length))

def oauth_code_url(request):
    # Create a state and nonce, and save them
    cache = OAuthCache(user=request.user, state=generate_random_string(32), nonce=generate_random_string(32))
    cache.save()
    return "https://oidc.mit.edu/authorize?response_type=code&client_id=895914d8-fc42-4188-a67e-db1aee77fee0&redirect_uri={}&scope=email%20openid%20profile&state={}&nonce={}".format(urllib.quote(REDIRECT_URI), cache.state, cache.nonce)

def get_user_info(request):
    code = request.GET.get('code', None)
    state = request.GET.get('state', None)

    caches = OAuthCache.objects.filter(user=request.user)
    found = False
    for cache in caches:
        if cache.state == state:
            found = True
            break
    if not found:
        raise PermissionDenied

    acc_token, status = get_oauth_id_token(request, code)
    if acc_token is None:
        return None, status

    return get_user_info_with_token(request, acc_token)

def get_oauth_id_token(request, code):
    with open(os.path.join(module_path, 'oidc.txt'), 'r') as file:
        contents = file.read().strip()
        id, secret = contents.split('\n')

    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    r = requests.post('https://oidc.mit.edu/token',auth=(id, secret), data=payload)
    if r.status_code != 200:
        return None, r.status_code

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
    caches = OAuthCache.objects.filter(user=request.user)
    found = False
    for cache in caches:
        if cache.nonce == nonce:
            current_date = timezone.now()
            if (current_date - cache.date).total_seconds() > LOGIN_TIMEOUT:
                return None, 408
            found = True
            break
    if not found:
        raise PermissionDenied
    caches.delete()

    access_token = r_json["access_token"]
    return access_token, r.status_code

def get_user_info_with_token(request, acc_token):
    headers = {"Authorization":"Bearer {}".format(acc_token)}
    r = requests.get('https://oidc.mit.edu/userinfo', headers=headers)
    return r.json(), r.status_code
