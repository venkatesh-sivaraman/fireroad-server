from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import *
import random
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import PermissionDenied
from .decorators import logged_in_or_basicauth, require_token_permissions
from .oauth_client import *
import base64
import json
import re
from token_gen import *
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from catalog.models import Course, CourseFields
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

# One month for mobile, ~1 week for web
TOKEN_EXPIRY_MOBILE = 2.6e6
TOKEN_EXPIRY_WEB = 6e5

def login_oauth(request):
    if request.GET.get('code', None) is None:
        code = request.GET.get('code', None)
        redirect_URL = request.GET.get('redirect', None)
        if 'next' in request.GET:
            redirect_URL = settings.MY_BASE_URL + '/' + request.GET['next']
        elif settings.RESTRICT_AUTH_REDIRECTS and redirect_URL is not None and RedirectURL.objects.filter(url=redirect_URL).count() == 0:
            return HttpResponse("Redirect URL not registered", status=403)
        return redirect(oauth_code_url(request, after_redirect=redirect_URL))

    result, status, info = get_user_info(request)
    if result is None or status != 200:
        return login_error_response(request, 'Please try again later.')

    # Save the user's profile, check if there are any other accounts
    email = result.get(u'email', None)
    sub = result.get(u'sub', None)
    if sub is None:
        return login_error_response(request, 'Please try again and allow FireRoad to access your OpenID information.')

    try:
        student = Student.objects.get(unique_id=sub)
    except:
        user = make_new_user()
        user.save()

        if email is None:
            email = "user{}@fireroad.mit.edu".format(user.username)
        student = Student(user=user, unique_id=sub, academic_id=email, name=result.get(u'name', 'Anonymous'))
        student.current_semester = info.get('sem', '0')
        student.save()
    else:
        # Only set the current semester if there's a real new value
        if len(info.get('sem', '')) > 0 and int(info['sem']) != 0:
            student.current_semester = info['sem']
        if student.user is None:
            user = make_new_user()
            user.save()
            student.user = user

        if email is not None: # In case the student's email has appeared now
            student.academic_id = email

        student.save()

    student.user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, student.user)

    # Generate access token for the user
    lifetime = TOKEN_EXPIRY_WEB if "redirect" in info else TOKEN_EXPIRY_MOBILE
    token = generate_token(request, student.user, lifetime)
    access_info = {'success': True, 'username': student.user.username, 'current_semester': int(student.current_semester), 'academic_id': student.academic_id, 'access_token': token, 'sub': sub}

    if "redirect" in info:
        # Redirect to the web application's page with a temporary code to get the access token
        return finish_login_redirect(access_info, info["redirect"])
    else:
        # Go to FireRoad's login success page, which is read by the mobile apps
        return render(request, 'common/login_success.html', {'access_info': json.dumps(access_info)})

def login_touchstone(request):
    """Logs in with Touchstone. This endpoint requires Touchstone authentication through the server
    host, so the user will be redirected automatically to the appropriate login screen. When this
    view is called, the request.META dictionary should contain REMOTE_USER and displayName fields
    that specify user information."""
    email_address = request.META.get("REMOTE_USER", None)
    student_name = request.META.get("displayName", None)
    if not email_address or not student_name:
        return HttpResponseBadRequest(("User information was missing from the Touchstone "
                                       "authentication process."))

    try:
        student = Student.objects.get(academic_id=email_address)
    except:
        user = make_new_user()
        user.save()

        student = Student(user=user, academic_id=email_address, name=student_name)
        student.current_semester = request.GET.get('sem', '0')
        student.save()
    else:
        # Only set the current semester if there's a real new value
        if request.GET.get('sem', '') and int(request.GET['sem']) != 0:
            student.current_semester = request.GET['sem']
        if student.user is None:
            user = make_new_user()
            user.save()
            student.user = user

        if email_address is not None: # In case the student's email has appeared now
            student.academic_id = email_address

        student.save()

    student.user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, student.user)

    # Generate access token for the user
    lifetime = TOKEN_EXPIRY_WEB if "redirect" in request.GET else TOKEN_EXPIRY_MOBILE
    api_client = get_api_client(request)
    token = generate_token(request, student.user, lifetime, api_client=api_client)
    access_info = {'success': True, 'username': student.user.username, 'current_semester':
                   int(student.current_semester), 'academic_id': student.academic_id,
                   'access_token': token}

    if "redirect" in request.GET:
        # Redirect to the web application's page with a temporary code to get the access token
        redirect_url = request.GET["redirect"]
        if (settings.RESTRICT_AUTH_REDIRECTS and redirect_url is not None and
            RedirectURL.objects.filter(url=redirect_url).count() == 0):
            return HttpResponse("Redirect URL not registered", status=403)
        return finish_login_redirect(access_info, redirect_url)
    elif "next" in request.GET:
        # Redirect to the given page in FireRoad
        redirect_dest = request.GET.get("next", "")
        if not redirect_dest:
            redirect_dest = "/"
        return redirect(redirect_dest)
    else:
        # Go to FireRoad's login success page, which is read by the mobile apps
        return render(request, 'common/login_success.html', {'access_info': json.dumps(access_info)})

def get_api_client(request):
    """Determines the API client from the request's redirect URL."""
    redirect_url = request.GET.get("redirect", None)
    if not redirect_url:
        return None
    try:
        redirect = RedirectURL.objects.get(url=redirect_url)
    except ObjectDoesNotExist:
        return None
    else:
        return redirect.client

def make_new_user():
    """Creates a new user using a random unique username and a long alphanumeric
    password."""
    password = generate_random_string(32)
    username = random.getrandbits(32)
    while User.objects.filter(username=username).exists():
        username = random.getrandbits(32)
    return User.objects.create_user(username=username, password=password)

def login_error_response(request, message):
    params = {'message': message}
    sem = request.GET.get('sem', None)
    if sem is not None:
        params["sem"] = sem
    return render(request, 'common/login_fail.html', params)

@logged_in_or_basicauth
@require_token_permissions("can_view_academic_id", "can_view_student_info")
def verify(request):
    """Verify that the given request has a user."""
    user = request.user
    if user is None:
        raise PermissionDenied
    auto_increment_semester(user)
    return HttpResponse(json.dumps({'success': True, 'current_semester': int(user.student.current_semester)}), content_type="application/json")

def new_user(request):
    new_id = random.getrandbits(32)
    resp = { 'u': new_id }
    return HttpResponse(json.dumps(resp), content_type="application/json")

def signup(request):
    """Shows an HTML page that describes the purpose of allowing recommendations
    for mobile users. If Yes is selected, continues to login. If No, goes to
    decline."""
    return render(request, 'common/signup.html', {'sem': request.GET.get('sem', '1')})

@csrf_exempt
@logged_in_or_basicauth
@require_token_permissions("can_edit_student_info")
def set_semester(request):
    user = request.user
    try:
        info = json.loads(request.body)
    except:
        return HttpResponseBadRequest('<h1>Invalid JSON {}</h1>'.format(request.body))
    sem = str(info.get('semester', ''))
    if len(sem) == 0:
        return HttpResponseBadRequest('<h1>Missing semester number</h1>')
    try:
        sem = int(sem)
    except:
        return HttpResponseBadRequest('<h1>Semester number is not an integer</h1>')
    s = user.student
    s.current_semester = str(sem)
    s.save()
    return HttpResponse(json.dumps({'success': True}), content_type="application/json")

### Application Server Login

def finish_login_redirect(access_info, uri):
    """
    Saves a temporary code that can be used by an application server to
    retrieve the access token and associated info, and redirects to the given
    URI passing the code as a "code" query parameter.
    """
    code = save_temporary_code(access_info)
    if not re.search(r'^https?://', uri): # Redirect requires a protocol
        uri = 'https://' + uri
    return redirect(uri + "?code=" + code)

def fetch_token(request):
    """
    Takes and validates a temporary code in the "code" query parameter, and
    returns a JSON response containing the access token. Raises PermissionDenied
    if the code is expired.
    """
    code = request.GET.get('code', '')
    if len(code) == 0:
        return HttpResponseBadRequest("Please provide the temporary code")
    access_info = get_access_info_with_temporary_code(code)
    return HttpResponse(json.dumps({'success': True, 'access_info': access_info}), content_type="application/json")

@logged_in_or_basicauth
@require_token_permissions("can_view_student_info", "can_view_academic_id")
def user_info(request):
    """Returns a JSON object containing the logged-in student's information."""
    student = request.user.student
    return HttpResponse(json.dumps({
        'academic_id': student.academic_id,
        'current_semester': int(student.current_semester),
        'name': student.name,
        'username': request.user.username}), content_type="application/json")

### Semester calculation

def is_fall(date):
    return date.month >= 5 and date.month <= 11

def closest_semester_boundary(date):
    """Rounds to the beginning of the most recent semester period (i.e. the closest
    May 1 for fall or December 1 for spring)."""
    def closest_past_date(delta):
        new = date + delta
        if new > date:
            new += relativedelta(years=-1)
        return new

    return max(closest_past_date(relativedelta(month=12, day=1)), closest_past_date(relativedelta(month=5, day=1)))

MAX_FALL = 13
MAX_SPRING = 15

def next_fall(semester, delta=1):
    if semester >= MAX_FALL:
        return semester
    return min((((semester - 1) // 3) + delta) * 3 + 1, MAX_FALL)

def next_spring(semester, delta=1):
    if semester >= MAX_SPRING:
        return semester
    return min(((semester // 3) + delta) * 3, MAX_SPRING)

def auto_increment_semester(user):
    current = int(user.student.current_semester)
    update_date = closest_semester_boundary(user.student.semester_update_date)
    now = timezone.now()

    difference_in_years = relativedelta(now, update_date).years
    new = current

    if (not is_fall(update_date) or difference_in_years > 0) and is_fall(now):
        # Change to next fall
        new = next_fall(current, delta=max(1, difference_in_years))
    elif (is_fall(update_date) or difference_in_years > 0) and not is_fall(now):
        # Change to next spring
        new = next_spring(current, delta=max(1, difference_in_years))

    if new != current:
        user.student.current_semester = str(new)
        user.student.save()

### Preference Syncing

@logged_in_or_basicauth
@require_token_permissions("can_view_student_info")
def favorites(request):
    value = request.user.student.favorites
    try:
        return HttpResponse(json.dumps({'success': True, 'favorites': json.loads(value) if len(value) else []}), content_type="application/json")
    except:
        return HttpResponse(json.dumps({'success': False, 'error': "Couldn't retrieve favorites"}), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
@require_token_permissions("can_edit_student_info")
def set_favorites(request):
    try:
        favorites = json.loads(request.body)
    except:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    try:
        student = request.user.student
        student.favorites = json.dumps(favorites)
        student.save()
        return HttpResponse(json.dumps({'success': True}), content_type="application/json")
    except:
        return HttpResponse(json.dumps({'success': False, 'error': "Couldn't set favorites"}), content_type="application/json")

@logged_in_or_basicauth
@require_token_permissions("can_view_student_info")
def progress_overrides(request):
    value = request.user.student.progress_overrides
    try:
        return HttpResponse(json.dumps({'success': True, 'progress_overrides': json.loads(value) if len(value) else {}}), content_type="application/json")
    except:
        return HttpResponse(json.dumps({'success': False, 'error': "Couldn't retrieve progress_overrides"}), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
@require_token_permissions("can_edit_student_info")
def set_progress_overrides(request):
    try:
        progress_overrides = json.loads(request.body)
    except:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    try:
        student = request.user.student
        student.progress_overrides = json.dumps(progress_overrides)
        student.save()
        return HttpResponse(json.dumps({'success': True}), content_type="application/json")
    except:
        return HttpResponse(json.dumps({'success': False, 'error': "Couldn't set progress_overrides"}), content_type="application/json")

@logged_in_or_basicauth
@require_token_permissions("can_view_student_info")
def notes(request):
    value = request.user.student.notes
    try:
        return HttpResponse(json.dumps({'success': True, 'notes': json.loads(value) if len(value) else {}}), content_type="application/json")
    except:
        return HttpResponse(json.dumps({'success': False, 'error': "Couldn't retrieve notes"}), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
@require_token_permissions("can_edit_student_info")
def set_notes(request):
    try:
        notes = json.loads(request.body)
    except:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    try:
        student = request.user.student
        student.notes = json.dumps(notes)
        student.save()
        return HttpResponse(json.dumps({'success': True}), content_type="application/json")
    except:
        return HttpResponse(json.dumps({'success': False, 'error': "Couldn't set notes"}), content_type="application/json")

@logged_in_or_basicauth
@require_token_permissions("can_view_student_info")
def custom_courses(request):
    value = request.user.student.custom_courses.all()
    try:
        return HttpResponse(json.dumps({'success': True, 'custom_courses': [c.to_json_object() for c in value]}), content_type="application/json")
    except:
        return HttpResponse(json.dumps({'success': False, 'error': "Couldn't retrieve custom courses"}), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
@require_token_permissions("can_edit_student_info")
def set_custom_course(request):
    try:
        course_json = json.loads(request.body)
    except:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    subject_id = course_json.get(CourseFields.subject_id, '')
    if len(subject_id) == 0:
        return HttpResponseBadRequest('Nonempty subject ID required')

    try:
        course = Course.objects.get(creator=request.user.student, subject_id=subject_id)
    except ObjectDoesNotExist:
        course = Course.objects.create(creator=request.user.student, subject_id=subject_id)

    course.title = course_json.get(CourseFields.title, '')
    course.description = course_json.get(CourseFields.description, '')
    course.total_units = course_json.get(CourseFields.total_units, 0)
    course.in_class_hours = course_json.get(CourseFields.in_class_hours, 0)
    course.out_of_class_hours = course_json.get(CourseFields.out_of_class_hours, 0)
    course.schedule = course_json.get(CourseFields.schedule, None)
    course.public = course_json.get(CourseFields.public, False)
    course.offered_fall = course_json.get(CourseFields.offered_fall, True)
    course.offered_IAP = course_json.get(CourseFields.offered_IAP, True)
    course.offered_spring = course_json.get(CourseFields.offered_spring, True)
    course.offered_summer = course_json.get(CourseFields.offered_summer, True)
    course.custom_color = course_json.get(CourseFields.custom_color, None)

    course.save()
    return HttpResponse(json.dumps({'success': True}), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
@require_token_permissions("can_edit_student_info")
def remove_custom_course(request):
    try:
        course_json = json.loads(request.body)
    except:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    subject_id = course_json.get(CourseFields.subject_id, '')
    if len(subject_id) == 0:
        return HttpResponseBadRequest('Nonempty subject ID required')

    try:
        course = Course.objects.get(creator=request.user.student, subject_id=subject_id)
        course.delete()
        return HttpResponse(json.dumps({'success': True}), content_type="application/json")
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Can't find custom course {}".format(subject_id))
