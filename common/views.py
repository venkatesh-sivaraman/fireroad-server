"""Defines views for the login flow and student model."""

import json
import re
import random

from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from dateutil.relativedelta import relativedelta

from catalog.models import Course, CourseFields
from fireroad.settings import RESTRICT_AUTH_REDIRECTS, MY_BASE_URL
from .models import *
from .decorators import logged_in_or_basicauth
from .oauth_client import *
from .token_gen import *

# One month for mobile, ~1 week for web
TOKEN_EXPIRY_MOBILE = 2.6e6
TOKEN_EXPIRY_WEB = 6e5

def login_oauth(request):
    """Performs different stages of the login procedure depending on the parameters
    passed. If a 'code' query parameter is passed, processes the second half of the
    authentication flow. If a 'redirect' query parameter is passed, starts the
    login flow to redirect to the given URL."""

    if request.GET.get('code', None) is None:
        redirect_url = request.GET.get('redirect', None)
        if 'next' in request.GET:
            redirect_url = MY_BASE_URL + '/' + request.GET['next']
        elif (RESTRICT_AUTH_REDIRECTS and redirect_url is not None and
              RedirectURL.objects.filter(url=redirect_url).count() == 0):
            return HttpResponse("Redirect URL not registered", status=403)
        return redirect(oauth_code_url(request, after_redirect=redirect_url))

    result, status, info = get_user_info(request)
    if result is None or status != 200:
        return login_error_response(request, 'Please try again later.')

    # Save the user's profile, check if there are any other accounts
    email = result.get(u'email', None)
    sub = result.get(u'sub', None)
    if sub is None:
        return login_error_response(
            request, 'Please try again and allow FireRoad to access your OpenID information.')

    try:
        student = Student.objects.get(unique_id=sub)
    except ObjectDoesNotExist:
        user = make_new_user()
        user.save()

        if email is None:
            email = "user{}@fireroad.mit.edu".format(user.username)
        student = Student(user=user, unique_id=sub,
                          academic_id=email, name=result.get(u'name', 'Anonymous'))
        student.current_semester = info.get('sem', '0')
        student.save()
    else:
        # Only set the current semester if there's a real new value
        if info.get('sem', '') and int(info['sem']) != 0:
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
    access_info = {'success': True,
                   'username': student.user.username,
                   'current_semester': int(student.current_semester),
                   'academic_id': student.academic_id,
                   'access_token': token,
                   'sub': sub}

    if "redirect" in info:
        # Redirect to the web application's page with a temporary code to get the access token
        return finish_login_redirect(access_info, info["redirect"])

    # Go to FireRoad's login success page, which is read by the mobile apps
    return render(request, 'common/login_success.html', {'access_info': json.dumps(access_info)})

def make_new_user():
    """Creates a new user using a random unique username and a long alphanumeric
    password."""
    password = generate_random_string(32)
    username = random.getrandbits(32)
    while User.objects.filter(username=username).exists(): # pylint: disable=no-member
        username = random.getrandbits(32)
    return User.objects.create_user(username=username, password=password)

def login_error_response(request, message):
    """Presents the user with a login error page with the given message."""
    params = {'message': message}
    sem = request.GET.get('sem', None)
    if sem is not None:
        params["sem"] = sem
    return render(request, 'common/login_fail.html', params)

@logged_in_or_basicauth
def verify(request):
    """Verify that the given request has a user."""
    user = request.user
    if user is None:
        raise PermissionDenied
    auto_increment_semester(user)
    return JsonResponse({'success': True,
                         'current_semester': int(user.student.current_semester)})

def new_user(request):
    """Generates a new user ID and returns it as JSON."""
    new_id = random.getrandbits(32)
    resp = {'u': new_id}
    return JsonResponse(resp)

def signup(request):
    """Shows an HTML page that describes the purpose of allowing recommendations
    for mobile users. If Yes is selected, continues to login. If No, goes to
    decline."""
    return render(request, 'common/signup.html', {'sem': request.GET.get('sem', '1')})

@csrf_exempt
@logged_in_or_basicauth
def set_semester(request):
    """API endpoint that sets the logged-in user's semester to the number
    encoded in the request body."""
    user = request.user
    try:
        info = json.loads(request.body)
    except BaseException:
        return HttpResponseBadRequest('<h1>Invalid JSON {}</h1>'.format(request.body))
    sem = str(info.get('semester', ''))
    if not sem:
        return HttpResponseBadRequest('<h1>Missing semester number</h1>')
    try:
        sem = int(sem)
    except ValueError:
        return HttpResponseBadRequest('<h1>Semester number is not an integer</h1>')
    s = user.student
    s.current_semester = str(sem)
    s.save()
    return JsonResponse({'success': True})

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
    if not code:
        return HttpResponseBadRequest("Please provide the temporary code")
    access_info = get_access_info_with_temporary_code(code)
    return JsonResponse({'success': True, 'access_info': access_info})

@logged_in_or_basicauth
def user_info(request):
    """Returns a JSON object containing the logged-in student's information."""
    student = request.user.student
    return JsonResponse({
        'academic_id': student.academic_id,
        'current_semester': int(student.current_semester),
        'name': student.name,
        'username': request.user.username})

### Semester calculation

def is_fall(date):
    """Determines whether the given datetime object is in the fall semester (at least
    May and at most November)."""
    return date.month >= 5 and date.month <= 11

def closest_semester_boundary(date):
    """Rounds to the beginning of the most recent semester period (i.e. the closest
    May 1 for fall or December 1 for spring)."""
    def closest_past_date(delta):
        """Returns the closest date that is the day of date + delta, and prior
        to date."""
        new = date + delta
        if new > date:
            new += relativedelta(years=-1)
        return new

    return max(closest_past_date(relativedelta(month=12, day=1)),
               closest_past_date(relativedelta(month=5, day=1)))

MAX_FALL = 13
MAX_SPRING = 15

def next_fall(semester, delta=1):
    """Returns the next semester number for the fall semester."""
    if semester >= MAX_FALL:
        return semester
    return min((((semester - 1) // 3) + delta) * 3 + 1, MAX_FALL)

def next_spring(semester, delta=1):
    """Returns the next semester number for the spring semester."""
    if semester >= MAX_SPRING:
        return semester
    return min(((semester // 3) + delta) * 3, MAX_SPRING)

def auto_increment_semester(user):
    """Increments and saves the current semester if the date at which the previous
    semester was set is sufficiently far back."""
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
def favorites(request):
    """API endpoint that returns the user's marked favorite courses."""
    value = request.user.student.favorites
    try:
        return JsonResponse({
            'success': True,
            'favorites': json.loads(value) if value else []})
    except BaseException:
        return JsonResponse({
            'success': False,
            'error': "Couldn't retrieve favorites"})

@csrf_exempt
@logged_in_or_basicauth
def set_favorites(request):
    """API endpoint that updates the user's marked favorite courses."""
    try:
        faves = json.loads(request.body)
    except BaseException:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    try:
        student = request.user.student
        student.favorites = json.dumps(faves)
        student.save()
        return JsonResponse({'success': True})
    except BaseException:
        return JsonResponse({'success': False, 'error': "Couldn't set favorites"})

@logged_in_or_basicauth
def progress_overrides(request):
    """API endpoint that returns the user's progress overrides. Deprecated in favor
    of storing progress overrides in each user's road."""
    value = request.user.student.progress_overrides
    try:
        return JsonResponse({
            'success': True,
            'progress_overrides': json.loads(value) if value else {}})
    except BaseException:
        return JsonResponse({
            'success': False,
            'error': "Couldn't retrieve progress_overrides"})

@csrf_exempt
@logged_in_or_basicauth
def set_progress_overrides(request):
    """API endpoint that updates the user's progress overrides. Deprecated in favor
    of storing progress overrides in each user's road."""
    try:
        overrides = json.loads(request.body)
    except BaseException:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    try:
        student = request.user.student
        student.progress_overrides = json.dumps(overrides)
        student.save()
        return JsonResponse({'success': True})
    except BaseException:
        return JsonResponse({
            'success': False,
            'error': "Couldn't set progress_overrides"})

@logged_in_or_basicauth
def notes(request):
    """API endpoint that returns the user's notes on each subject."""
    value = request.user.student.notes
    try:
        return JsonResponse({'success': True, 'notes': json.loads(value) if value else {}})
    except BaseException:
        return JsonResponse({'success': False, 'error': "Couldn't retrieve notes"})

@csrf_exempt
@logged_in_or_basicauth
def set_notes(request):
    """API endpoint that updates the user's notes on each subject."""
    try:
        new_notes = json.loads(request.body)
    except BaseException:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    try:
        student = request.user.student
        student.notes = json.dumps(new_notes)
        student.save()
        return JsonResponse({'success': True})
    except BaseException:
        return JsonResponse({'success': False, 'error': "Couldn't set notes"})

@logged_in_or_basicauth
def custom_courses(request):
    """API endpoint that returns the custom courses that the user has created."""
    value = request.user.student.custom_courses.all()
    try:
        return JsonResponse({
            'success': True,
            'custom_courses': [c.to_json_object() for c in value]})
    except BaseException:
        return JsonResponse({
            'success': False,
            'error': "Couldn't retrieve custom courses"})

@csrf_exempt
@logged_in_or_basicauth
def set_custom_course(request):
    """API endpoint that updates a user-created custom course."""
    try:
        course_json = json.loads(request.body)
    except BaseException:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    subject_id = course_json.get(CourseFields.subject_id, '')
    if not subject_id:
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
    return JsonResponse({'success': True})

@csrf_exempt
@logged_in_or_basicauth
def remove_custom_course(request):
    """API endpoint that deletes a user-created custom course."""
    try:
        course_json = json.loads(request.body)
    except BaseException:
        return HttpResponseBadRequest('<h1>JSON error</h1>')

    subject_id = course_json.get(CourseFields.subject_id, '')
    if not subject_id:
        return HttpResponseBadRequest('Nonempty subject ID required')

    try:
        course = Course.objects.get(creator=request.user.student, subject_id=subject_id)
        course.delete()
        return JsonResponse({'success': True})
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("Can't find custom course {}".format(subject_id))
