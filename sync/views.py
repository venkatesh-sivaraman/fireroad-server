"""Views for the document sync module."""

import random
import json

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse

from common.models import *
from common.decorators import logged_in_or_basicauth
from .operations import *
from .models import *

def get_datetime(form_contents, key):
    """Parses a Django datetime from the given field of the given form. Returns None if no date
    could be found."""
    raw = form_contents.get(key, '')
    if not raw:
        return None
    return parse(raw)

def get_operation(request):
    """Returns a SyncOperation from the given request and None, or None and an
    HttpResponse error object."""
    try:
        form_contents = json.loads(request.body)
    except: #pylint: disable=bare-except
        return None, HttpResponseBadRequest('<h1>Invalid request</h1>')

    # Extract POST contents

    file_id = form_contents.get('id', 0)
    if file_id is None or file_id == 0:
        file_id = NEW_FILE_ID
    else:
        try:
            file_id = int(file_id)
        except ValueError:
            return HttpResponseBadRequest('<h1>Invalid ID</h1>')

    contents = form_contents.get('contents', {})
    if not contents:
        return None, HttpResponseBadRequest('<h1>Missing contents</h1>')

    change_date = get_datetime(form_contents, 'changed')
    if change_date is None:
        return None, HttpResponseBadRequest('<h1>Missing or invalid changed date</h1>')

    down_date = get_datetime(form_contents, 'downloaded')
    name = form_contents.get('name', '')
    agent = form_contents.get('agent', ANONYMOUS_AGENT)
    override = form_contents.get('override', False)

    return SyncOperation(file_id,
                         name,
                         contents,
                         change_date,
                         down_date,
                         agent,
                         override_conflict=override), None

def delete_helper(request, model_cls):
    """Performs a deletion using the given request on the given model class (Road or Schedule)."""
    try:
        form_contents = json.loads(request.body)
    except: #pylint: disable=bare-except
        return None, HttpResponseBadRequest('<h1>Invalid request</h1>')

    # Extract POST contents

    file_id = form_contents.get('id', 0)
    if file_id is None or file_id == 0:
        return HttpResponseBadRequest('<h1>Missing file ID</h1>')
    try:
        file_id = int(file_id)
    except ValueError:
        return HttpResponseBadRequest('<h1>Invalid file ID</h1>')

    resp = delete(request, model_cls, file_id)
    return JsonResponse(resp)

@csrf_exempt
@logged_in_or_basicauth
def sync_road(request):
    """Performs a sync operation with the given road."""
    operation, err_resp = get_operation(request)
    if operation is None:
        return err_resp

    resp = sync(request, Road, operation)
    return JsonResponse(resp)

@logged_in_or_basicauth
def roads(request):
    """Browses the logged-in user's roads, or returns information about a single road if the 'id'
    query parameter is passed."""
    road_id = request.GET.get('id', None)

    if road_id is not None:
        try:
            road_id = int(road_id)
        except ValueError:
            return HttpResponseBadRequest('<h1>Invalid road ID</h1>')

    resp = browse(request, Road, road_id)
    return JsonResponse(resp)

@csrf_exempt
@logged_in_or_basicauth
def delete_road(request):
    """Deletes the road specified in the request."""
    return delete_helper(request, Road)

@csrf_exempt
@logged_in_or_basicauth
def sync_schedule(request):
    """Performs a sync operation on the given schedule."""
    operation, err_resp = get_operation(request)
    if operation is None:
        return err_resp

    resp = sync(request, Schedule, operation)
    return JsonResponse(resp)

@logged_in_or_basicauth
def schedules(request):
    """Returns summary information about the user's schedules, or returns information about a
    particular schedule if the 'id' query parameter is provided."""
    schedule_id = request.GET.get('id', None)

    if schedule_id is not None:
        try:
            schedule_id = int(schedule_id)
        except ValueError:
            return HttpResponseBadRequest('<h1>Invalid schedule ID</h1>')

    resp = browse(request, Schedule, schedule_id)
    return JsonResponse(resp)

@csrf_exempt
@logged_in_or_basicauth
def delete_schedule(request):
    """Deletes the schedule specified in the request."""
    return delete_helper(request, Schedule)
