from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import *
import json
import random
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import PermissionDenied
from .decorators import logged_in_or_basicauth
from .oauth_client import *

def verify(request):
    user_id = request.GET.get('u', '')
    count = Rating.objects.filter(user_id=user_id).count()
    return HttpResponse(str(count), content_type="application/json")

def new_user(request):
    new_id = random.getrandbits(32)
    resp = { 'u': new_id }
    return HttpResponse(json.dumps(resp), content_type="application/json")

def update_rating(user_id, subject_id, value):
    Rating.objects.filter(user_id=user_id, subject_id=subject_id).delete()

    r = Rating(user_id=user_id, subject_id=subject_id, value=value)
    r.save()

def signup(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password')
            user = User.objects.create_user(username=username, password=raw_password)
            user.save()
            Recommendation.objects.create(user_id=username, rec_type=DEFAULT_RECOMMENDATION_TYPE, subjects='{}')
            resp = { 'received': True }
            return HttpResponse(json.dumps(resp), content_type="application/json")
    else:
        form = UserForm()
    return render(request, 'recommend/signup.html', {'form': form})

@logged_in_or_basicauth
def get(request):
    user_id = request.GET.get('u', '')
    if len(user_id) == 0:
        return HttpResponseBadRequest('<h1>Missing user ID</h1>')
    if request.user.username != user_id:
        raise PermissionDenied
    rec_type = request.GET.get('t', '')
    if len(rec_type) == 0:
        recs = Recommendation.objects.filter(user_id=user_id)
    else:
        recs = Recommendation.objects.filter(user_id=user_id, rec_type=rec_type)
    if recs.count() == 0:
        return HttpResponse('No recommendations yet. Try again tomorrow!')
    resp = {rec.rec_type: json.loads(rec.subjects) for rec in recs}
    return HttpResponse(json.dumps(resp), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
def rate(request):
    batch = request.body
    if len(batch) > 0:
        batch_items = json.loads(batch)
        for item in batch_items:
            try:
                user_id = int(item['u'])
                value = int(item['v'])
                if user_id is None or user_id < 0:
                    return HttpResponseBadRequest('<h1>Missing user ID</h1>')
                if item['s'] == None or len(item['s']) > 10:
                    return HttpResponseBadRequest('<h1>Missing subject ID</h1>')
                if value is None:
                    return HttpResponseBadRequest('<h1>Missing rating value</h1>')
                if request.user.username != str(user_id):
                    raise PermissionDenied
                update_rating(user_id, item['s'], value)
            except:
                return HttpResponseBadRequest('<h1>Bad input</h1>')
        resp = { 'received': True }
    else:
        user_id = request.POST.get('u', '')
        subject_id = request.POST.get('s', '')
        value = request.POST.get('v', '')
        try:
            user_id = int(user_id)
            value = int(value)
            if user_id is None or user_id < 0:
                return HttpResponseBadRequest('<h1>Missing user ID</h1>')
            if subject_id == None or len(subject_id) == 0 or len(subject_id) > 10:
                return HttpResponseBadRequest('<h1>Missing subject ID</h1>')
            if value is None:
                return HttpResponseBadRequest('<h1>Missing rating value</h1>')
            if request.user.username != str(user_id):
                raise PermissionDenied
            update_rating(user_id, subject_id, value)
            resp = { 'u': user_id, 's': subject_id, 'v': value, 'received': True }
        except:
            return HttpResponseBadRequest('<h1>Bad input</h1>')
    return HttpResponse(json.dumps(resp), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
def upload_road(request):
    if request.method == 'POST':
        form = RoadForm(request.POST)
        if form.is_valid():
            road_name = form.cleaned_data.get('name')
            if road_name is None or len(road_name) == 0:
                return HttpResponseBadRequest('<h1>Missing road name</h1>')
            contents = form.cleaned_data.get('contents')
            if contents is None or len(contents) == 0:
                return HttpResponseBadRequest('<h1>Missing road contents</h1>')

            try:
                j_contents = json.loads(contents)
            except:
                return HttpResponseBadRequest('<h1>Invalid JSON for road contents</h1>')
            try:
                r = Road.objects.get(user=request.user, name=road_name)
                r.contents = Road.compress_road(contents)
                r.save()
            except:
                r = Road(user=request.user, name=road_name, contents=Road.compress_road(contents))
                r.save()
            resp = { 'received': True }
            return HttpResponse(json.dumps(resp), content_type="application/json")
        else:
            return HttpResponseBadRequest('<h1>Bad Form Input</h1>')
    else:
        form = RoadForm()
    return render(request, 'recommend/upload_road.html', {'form': form})

@logged_in_or_basicauth
def roads(request):
    if request.user is None:
        raise PermissionDenied
    road_name = request.GET.get('n', None)
    print(road_name)
    if road_name is None:
        result = {}
        roads = Road.objects.filter(user=request.user)
        for road in roads:
            result[road.name] = json.loads(Road.expand_road(road.contents))
        return HttpResponse(json.dumps(result), content_type="application/json")
    else:
        try:
            road = Road.objects.get(user=request.user, name=road_name)
            return HttpResponse(Road.expand_road(road.contents), content_type="application/json")
        except:
            return HttpResponseBadRequest('<h1>No road named {}</h1>'.format(road_name))

### User Linking

@logged_in_or_basicauth
def link_user(request):
    code = request.GET.get('code', None)
    if code is None:
        return redirect(oauth_code_url(request))
    else:
        result, status = get_user_info(request)
        if result is None:
            return HttpResponse(status=status if status != 200 else 500)
        else:
            # Save the user's profile
            email = result.get(u'email', None)
            if email is None:
                return HttpResponse(json.dumps({'success': False, 'reason': 'Please try again and allow FireRoad to access your email address.'}))
            student = Student(user=request.user, academic_id=email, name=result.get(u'name', 'Anonymous'))
            student.save()
            return HttpResponse(json.dumps({'success': True}))
