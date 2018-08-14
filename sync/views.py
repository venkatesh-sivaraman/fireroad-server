from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import *
from common.models import *
import random
from common.decorators import logged_in_or_basicauth
import json
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from django.core.exceptions import ObjectDoesNotExist
from .operations import *

def get_datetime(form_contents, key):
    raw = form_contents.get(key, '')
    if len(raw) == 0:
        return None
    return parse(raw)

def get_operation(request):
    """Returns a SyncOperation from the given request and None, or None and an
    HttpResponse error object."""
    try:
        form_contents = json.loads(request.body)
    except:
        return None, HttpResponseBadRequest('<h1>Invalid request</h1>')

    # Extract POST contents

    id = form_contents.get('id', 0)
    if id is None or id == 0:
        id = NEW_FILE_ID
    else:
        try:
            id = int(id)
        except ValueError:
            return HttpResponseBadRequest('<h1>Invalid ID</h1>')

    contents = form_contents.get('contents', {})
    if contents is None or len(contents) == 0:
        return None, HttpResponseBadRequest('<h1>Missing contents</h1>')

    change_date = get_datetime(form_contents, 'changed')
    if change_date is None:
        return None, HttpResponseBadRequest('<h1>Missing or invalid changed date</h1>')

    down_date = get_datetime(form_contents, 'downloaded')
    name = form_contents.get('name', '')
    agent = form_contents.get('agent', ANONYMOUS_AGENT)
    override = form_contents.get('override', False)

    return SyncOperation(id, name, contents, change_date, down_date, agent, override_conflict=override), None

def delete_helper(request, model_cls):
    try:
        form_contents = json.loads(request.body)
    except:
        return None, HttpResponseBadRequest('<h1>Invalid request</h1>')

    # Extract POST contents

    id = form_contents.get('id', 0)
    if id is None or id == 0:
        return HttpResponseBadRequest('<h1>Missing file ID</h1>')
    try:
        id = int(id)
    except ValueError:
        return HttpResponseBadRequest('<h1>Invalid file ID</h1>')

    resp = delete(request, model_cls, id)
    return HttpResponse(json.dumps(resp), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
def sync_road(request):
    operation, err_resp = get_operation(request)
    if operation is None:
        return err_resp

    resp = sync(request, Road, operation)
    return HttpResponse(json.dumps(resp), content_type="application/json")

@logged_in_or_basicauth
def roads(request):
    road_id = request.GET.get('id', None)

    if road_id is not None:
        try:
            road_id = int(road_id)
        except ValueError:
            return HttpResponseBadRequest('<h1>Invalid road ID</h1>')

    resp = browse(request, Road, road_id)
    return HttpResponse(json.dumps(resp), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
def delete_road(request):
    return delete_helper(request, Road)

@csrf_exempt
@logged_in_or_basicauth
def sync_schedule(request):
    operation, err_resp = get_operation(request)
    if operation is None:
        return err_resp

    resp = sync(request, Schedule, operation)
    return HttpResponse(json.dumps(resp), content_type="application/json")

@logged_in_or_basicauth
def schedules(request):
    schedule_id = request.GET.get('id', None)

    if schedule_id is not None:
        try:
            schedule_id = int(schedule_id)
        except ValueError:
            return HttpResponseBadRequest('<h1>Invalid schedule ID</h1>')

    resp = browse(request, Schedule, schedule_id)
    return HttpResponse(json.dumps(resp), content_type="application/json")

@csrf_exempt
@logged_in_or_basicauth
def delete_schedule(request):
    return delete_helper(request, Schedule)
