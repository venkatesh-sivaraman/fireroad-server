"""Views for the rating and recommendation system."""

import random
import json

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from common.decorators import logged_in_or_basicauth
from common.models import *
from .models import *

def update_rating(user, subject_id, value):
    """Replaces the rating for the given user and subject ID with a new Rating object with the
    given value."""
    Rating.objects.filter(user=user, subject_id=subject_id).delete()

    r = Rating(user=user, subject_id=subject_id, value=value)
    r.save()

@logged_in_or_basicauth
def get(request):
    """Returns the recommendations for the logged-in user, optionally filtering by the specified
    recommendation type."""
    rec_type = request.GET.get('t', '')
    if rec_type:
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
    """Saves a rating for the logged-in user with the given subject ID and value.

    If the request body is nonempty, it should be a JSON-formatted list containing objects that
    have the key 'v' (for the value) and 's' (for the subject ID). Otherwise, the POST parameters
    for the request should contain the 's' and 'v' keys for a single rating."""

    batch = request.body
    if batch:
        batch_items = json.loads(batch)
        for item in batch_items:
            try:
                value = int(item['v'])
                if item['s'] is None or len(item['s']) > 10:
                    return HttpResponseBadRequest('<h1>Missing subject ID</h1>')
                if value is None:
                    return HttpResponseBadRequest('<h1>Missing rating value</h1>')
                update_rating(request.user, item['s'], value)
            except ValueError:
                return HttpResponseBadRequest('<h1>Bad input</h1>')
        resp = {'received': True}
    else:
        subject_id = request.POST.get('s', '')
        value = request.POST.get('v', '')
        try:
            value = int(value)
            if subject_id is None or not subject_id or len(subject_id) > 10:
                return HttpResponseBadRequest('<h1>Missing subject ID</h1>')
            if value is None:
                return HttpResponseBadRequest('<h1>Missing rating value</h1>')
            update_rating(request.user, subject_id, value)
            resp = {
                'u': request.user.username,
                's': subject_id,
                'v': value,
                'received': True
            }
        except ValueError:
            return HttpResponseBadRequest('<h1>Bad input</h1>')
    return JsonResponse(resp)
