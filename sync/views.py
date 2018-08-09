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

@csrf_exempt
@logged_in_or_basicauth
def upload_road(request):
    try:
        form_contents = json.loads(request.body)
    except:
        return HttpResponseBadRequest('<h1>Invalid request</h1>')

    road_name = form_contents.get('name', '')
    if road_name is None or len(road_name) == 0:
        return HttpResponseBadRequest('<h1>Missing road name</h1>')
    contents = form_contents.get('contents', {})
    if contents is None or len(contents) == 0:
        return HttpResponseBadRequest('<h1>Missing road contents</h1>')

    try:
        j_contents = json.dumps(contents)
    except:
        return HttpResponseBadRequest('<h1>Invalid JSON for road contents</h1>')
    try:
        r = Road.objects.get(user=request.user, name=road_name)
        r.contents = Road.compress_road(j_contents)
        r.save()
    except:
        r = Road(user=request.user, name=road_name, contents=Road.compress_road(j_contents))
        r.save()
    resp = { 'received': True }
    return HttpResponse(json.dumps(resp), content_type="application/json")

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
