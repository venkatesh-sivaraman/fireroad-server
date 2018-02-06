from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import *
import json
import random
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import PermissionDenied
from .decorators import logged_in_or_basicauth

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
            if int(item['u']) == None:
                return HttpResponseBadRequest('<h1>Missing user ID</h1>')
            if item['s'] == None:
                return HttpResponseBadRequest('<h1>Missing subject ID</h1>')
            if int(item['v']) == None:
                return HttpResponseBadRequest('<h1>Missing rating value</h1>')
            if request.user.username != str(item['u']):
                raise PermissionDenied
            update_rating(int(item['u']), item['s'], int(item['v']))
        resp = { 'received': True }
    else:
        user_id = request.POST.get('u', '')
        subject_id = request.POST.get('s', '')
        value = request.POST.get('v', '')
        if len(user_id) == 0 or int(user_id) < 0:
            return HttpResponseBadRequest('<h1>Invalid user ID</h1><br/><p>{}</p>'.format(user_id))
        if request.user.username != user_id:
            raise PermissionDenied
        if len(subject_id) == 0:
            return HttpResponseBadRequest('<h1>Invalid subject ID</h1><br/><p>{}</p>'.format(subject_id))
        if len(value) == 0 or int(value) > MAX_RATING_VALUE:
            return HttpResponseBadRequest('<h1>Invalid rating value</h1><br/><p>{}</p>'.format(value))

        resp = { 'u': int(user_id), 's': subject_id, 'v': int(value), 'received': True }
    return HttpResponse(json.dumps(resp), content_type="application/json")
