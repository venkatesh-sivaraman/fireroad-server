import base64

from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.conf import settings

from .oauth_client import *
from .models import Student, APIClient
import json
from .token_gen import *

ALWAYS_LOGIN = False

def user_has_student(user):
    try:
        s = user.student
        return s is not None
    except:
        return False

def view_or_basicauth(view, request, test_func, realm = "", *args, **kwargs):
    """
    This is a helper function used by both 'logged_in_or_basicauth' and
    'has_perm_or_basicauth' that does the nitty of determining if they
    are already logged in or if they have provided proper http-authorization
    and returning the view if all goes well, otherwise responding with a 401.
    """

    if request.user is None or not request.user.is_authenticated or not user_has_student(request.user) or ALWAYS_LOGIN:
        key = 'HTTP_AUTHORIZATION'
        if key not in request.META:
            key = 'REDIRECT_HTTP_AUTHORIZATION'
        if key not in request.META:
            key = 'HTTP_X_AUTHORIZATION'
        if key in request.META:
            auth = request.META[key].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    # Basic authentication - this is not an API client
                    uname, passwd = base64.b64decode(auth[1]).split(':')
                    user = authenticate(username=uname, password=passwd)
                    permissions = APIClient.universal_permission_flag()
                elif auth[0].lower() == "bearer":
                    # The client bears a FireRoad-issued token
                    user, permissions, error = extract_token_info(request, auth[1])
                    if error is not None:
                        return HttpResponse(json.dumps(error), status=401, content_type="application/json")
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                else:
                    raise PermissionDenied

                request.session['permissions'] = permissions
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        request.user = user
                        return view(request, *args, **kwargs)
        raise PermissionDenied
        #return redirect('login')
    else:
        if 'permissions' not in request.session:
            print("Setting universal permission flag - this should only occur in dev or from FireRoad-internal login.")
            request.session['permissions'] = APIClient.universal_permission_flag()
        return view(request, *args, **kwargs)

#############################################################################
#
def logged_in_or_basicauth(func, realm = ""):
    """
    A simple decorator that requires a user to be logged in. If they are not
    logged in the request is examined for a 'authorization' header.

    If the header is present it is tested for basic authentication and
    the user is logged in with the provided credentials.

    If the header is not present a http 401 is sent back to the
    requestor to provide credentials.

    The purpose of this is that in several django projects I have needed
    several specific views that need to support basic authentication, yet the
    web site as a whole used django's provided authentication.

    The uses for this are for urls that are access programmatically such as
    by rss feed readers, yet the view requires a user to be logged in. Many rss
    readers support supplying the authentication credentials via http basic
    auth (and they do NOT support a redirect to a form where they post a
    username/password.)

    Use is simple:

    @logged_in_or_basicauth
    def your_view:
        ...

    You can provide the name of the realm to ask for authentication within.
    """
    def wrapper(request, *args, **kwargs):
        # If it's a preflight request, don't even run the view
        if request.method == 'OPTIONS':
            return HttpResponse()
        return view_or_basicauth(func, request,
                                 lambda u: u.is_authenticated,
                                 realm, *args, **kwargs)
    return wrapper

#############################################################################
#
def has_perm_or_basicauth(perm, realm = ""):
    """
    This is similar to the above decorator 'logged_in_or_basicauth'
    except that it requires the logged in user to have a specific
    permission.

    Use:

    @logged_in_or_basicauth('asforums.view_forumcollection')
    def your_view:
        ...

    """
    def view_decorator(func):
        def wrapper(request, *args, **kwargs):
            return view_or_basicauth(func, request,
                                     lambda u: u.has_perm(perm),
                                     realm, *args, **kwargs)
        return wrapper
    return view_decorator

def require_token_permissions(*permission_names):
    """Decorator that makes sure that the request has a permissions flag that permits the
    given permission names."""
    def view_decorator(view_func):
        def wrapper(request, *args, **kwargs):
            # Passthrough for dev server and local testing
            if not settings.RESTRICT_AUTH_REDIRECTS and settings.DEBUG:
                return view_func(request, *args, **kwargs)

            if not request.session["permissions"]:
                print("Session object has no permissions set")
                raise PermissionDenied
            permissions = APIClient.from_permissions_flag(request.session["permissions"])
            for p_name in permission_names:
                try:
                    if not getattr(permissions, p_name):
                        raise PermissionDenied
                except AttributeError:
                    print("Attribute not found: " + p_name)
                    raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return view_decorator
