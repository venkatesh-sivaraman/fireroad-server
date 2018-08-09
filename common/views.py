from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import *
import random
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import PermissionDenied
from .decorators import logged_in_or_basicauth
from .oauth_client import *
import base64
import json
from token_gen import *
from django.utils import timezone
from dateutil.relativedelta import relativedelta

# One month
TOKEN_EXPIRY_TIME = 2.6e6

def login_oauth(request):
    if request.GET.get('code', None) is None:
        code = request.GET.get('code', None)
        return redirect(oauth_code_url(request))

    result, status, info = get_user_info(request)
    if result is None or status != 200:
        return HttpResponse(status=status if status != 200 else 500)
    else:
        # Save the user's profile, check if there are any other accounts
        email = result.get(u'email', None)
        if email is None:
            return None, HttpResponse(json.dumps({'success': False, 'reason': 'Please try again and allow FireRoad to access your email address.'}))

        password = generate_random_string(32)
        try:
            student = Student.objects.get(academic_id=email)
            student.current_semester = info.get('sem', '0')
            if student.user is None:
                user = User.objects.create_user(username=random.getrandbits(32), password=password)
                user.save()
                student.user = user
                student.save()
        except:
            user = User.objects.create_user(username=random.getrandbits(32), password=password)
            user.save()
            #Recommendation.objects.create(user=user, rec_type=DEFAULT_RECOMMENDATION_TYPE, subjects='{}')
            student = Student(user=user, academic_id=email, name=result.get(u'name', 'Anonymous'))
            student.current_semester = info.get('sem', '0')
            student.save()
        student.user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, student.user)

        token = generate_token(request, student.user, TOKEN_EXPIRY_TIME)
        print(token)
        return render(request, 'recommend/login_success.html', {'access_info': json.dumps({'success': True, 'username': student.user.username, 'current_semester': int(student.current_semester), 'academic_id': student.academic_id, 'access_token': token})})

@logged_in_or_basicauth
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
    """DEPRECATED"""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password')
            user = User.objects.create_user(username=username, password=raw_password)
            user.save()
            #Recommendation.objects.create(user_id=username, rec_type=DEFAULT_RECOMMENDATION_TYPE, subjects='{}')
            resp = { 'received': True }
            return HttpResponse(json.dumps(resp), content_type="application/json")
    else:
        form = UserForm()
    return render(request, 'recommend/signup.html', {'form': form})

@csrf_exempt
@logged_in_or_basicauth
def set_semester(request):
    user = request.user
    info = json.loads(request.body)
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

# Semester calculation

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
