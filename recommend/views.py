from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import *
from common.models import *
import random
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import PermissionDenied
from common.decorators import logged_in_or_basicauth
import json
from django.utils import timezone
from dateutil.relativedelta import relativedelta

def update_rating(user, subject_id, value):
    Rating.objects.filter(user=user, subject_id=subject_id).delete()

    r = Rating(user=user, subject_id=subject_id, value=value)
    r.save()

@logged_in_or_basicauth
def get(request):
    rec_type = request.GET.get('t', '')
    if len(rec_type) == 0:
        recs = Recommendation.objects.filter(user=request.user)
    else:
        recs = Recommendation.objects.filter(user=request.user, rec_type=rec_type)
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
                value = int(item['v'])
                if item['s'] == None or len(item['s']) > 10:
                    return HttpResponseBadRequest('<h1>Missing subject ID</h1>')
                if value is None:
                    return HttpResponseBadRequest('<h1>Missing rating value</h1>')
                update_rating(request.user, item['s'], value)
            except:
                return HttpResponseBadRequest('<h1>Bad input</h1>')
        resp = { 'received': True }
    else:
        subject_id = request.POST.get('s', '')
        value = request.POST.get('v', '')
        try:
            value = int(value)
            if subject_id == None or len(subject_id) == 0 or len(subject_id) > 10:
                return HttpResponseBadRequest('<h1>Missing subject ID</h1>')
            if value is None:
                return HttpResponseBadRequest('<h1>Missing rating value</h1>')
            if request.user.username != str(user_id):
                raise PermissionDenied
            update_rating(request.user, subject_id, value)
            resp = { 'u': request.user.username, 's': subject_id, 'v': value, 'received': True }
        except:
            return HttpResponseBadRequest('<h1>Bad input</h1>')
    return HttpResponse(json.dumps(resp), content_type="application/json")
