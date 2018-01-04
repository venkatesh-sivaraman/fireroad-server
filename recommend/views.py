from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
from django.db.models import Q
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from .models import Rating, MAX_RATING_VALUE
from .decorators import secure_required
import json
import random

def verify(request):
    resp = { 'received': True }
    return HttpResponse(json.dumps(resp), content_type="application/json")

def new_user(request):
    password = request.POST.get('password', '')
    if len(password) == 0:
        return HttpResponseBadRequest('<h1>Need a password</h1>')
    new_id = random.getrandbits(32)
    while User.objects.exists(username=str(new_id)):
        print("Regenerating ID!")
        new_id = random.getrandbits(32)
    resp = { 'u': new_id }
    User.objects.create_user(username=str(new_id), password=password)
    return HttpResponse(json.dumps(resp), content_type="application/json")

def update_rating(user_id, subject_id, value):
    try:
        old_rating = Rating.objects.get(Q(user_id=user_id), Q(subject_id=subject_id))
        old_rating.delete()
    except:
        print("No existing rating!")

    r = Rating(user_id=user_id, subject_id=subject_id, value=value)
    r.save()

@csrf_exempt
@secure_required
def rate(request):
    batch = request.body
    if len(batch) > 0:
        batch_items = json.loads(batch)
        for item in batch_items:
            if item['u'] == None:
                return HttpResponseBadRequest('<h1>Missing user ID</h1>')
            if item['s'] == None:
                return HttpResponseBadRequest('<h1>Missing subject ID</h1>')
            if item['v'] == None:
                return HttpResponseBadRequest('<h1>Missing rating value</h1>')
            update_rating(int(item['u']), item['s'], int(item['v']))
        resp = { 'received': True }
    else:
        user_id = request.POST.get('u', '')
        subject_id = request.POST.get('s', '')
        value = request.POST.get('v', '')
        if len(user_id) == 0 or int(user_id) < 0:
            return HttpResponseBadRequest('<h1>Invalid user ID</h1><br/><p>{}</p>'.format(user_id))
        if len(subject_id) == 0:
            return HttpResponseBadRequest('<h1>Invalid subject ID</h1><br/><p>{}</p>'.format(subject_id))
        if len(value) == 0 or int(value) > MAX_RATING_VALUE:
            return HttpResponseBadRequest('<h1>Invalid rating value</h1><br/><p>{}</p>'.format(value))

        resp = { 'u': int(user_id), 's': subject_id, 'v': int(value), 'received': True }
    return HttpResponse(json.dumps(resp), content_type="application/json")
