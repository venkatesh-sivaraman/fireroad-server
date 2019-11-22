from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from .models import *
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from common.decorators import logged_in_or_basicauth
import json
import os
import requests
from courseupdater.views import *
from sync.models import Road
import re
from progress import RequirementsProgress
from catalog.models import Course, Attribute, HASSAttribute, GIRAttribute, CommunicationAttribute
import logging

REQUIREMENTS_EXT = ".reql"

SUBJECT_ID_KEY = "subject_id"
SUBJECT_ID_ALT_KEY = "id"

def get_json(request, list_id):
    """Returns the raw JSON for a given requirements list, without user
    course progress."""

    try:
        req = RequirementsList.objects.get(list_id=list_id + REQUIREMENTS_EXT)
        # to pretty-print, use these keyword arguments to json.dumps:
        # sort_keys=True, indent=4, separators=(',', ': ')
        return HttpResponse(json.dumps(req.to_json_object(full=True)), content_type="application/json")
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("the requirements list {} does not exist".format(list_id))

def compute_progress(request, list_id, course_list, progress_overrides, progress_assertions):
    """Utility function for road_progress and progress that computes and returns
    the progress on the given requirements list."""
    try:
        req = RequirementsList.objects.get(list_id=list_id + REQUIREMENTS_EXT)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("the requirements list {} does not exist".format(list_id))

    # Get Course objects
    course_objs = []
    #required to give generic courses unique id's so muliple can count towards requirement
    unique_generic_id = 0
    for subject_id in course_list:
        try:
            course_objs.append(Course.public_courses().get(subject_id=subject_id))
        except ObjectDoesNotExist:
            try:
                course_objs.append(Course.make_generic(subject_id,unique_generic_id))
                unique_generic_id += 1
            except ValueError:
                print("Warning: course {} does not exist in the catalog".format(subject_id))


    # Create a progress object for the requirements list
    prog = RequirementsProgress(req, list_id)
    prog.compute(course_objs, progress_overrides, progress_assertions)
    # to pretty-print, use these keyword arguments to json.dumps:
    # sort_keys=True, indent=4, separators=(',', ': ')
    return HttpResponse(json.dumps(prog.to_json_object(True)), content_type="application/json")

#@logged_in_or_basicauth
def road_progress_get(request, list_id):
    """Returns the raw JSON for a given requirements list including user
    progress. A 'road' query parameter should be passed that indicates the ID
    number of the road that is being checked."""
    road_id = request.GET.get("road", "")
    if road_id is None or len(road_id) == 0:
        return HttpResponseBadRequest("need a road ID")
    try:
        road_id = int(road_id)
    except:
        return HttpResponseBadRequest("road ID must be an integer")

    try:
        road = Road.objects.get(user=request.user, pk=road_id)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("the road does not exist on the server")

    try:
        contents = json.loads(Road.expand(road.contents))
    except:
        return HttpResponseBadRequest("badly formatted road contents")

    progress_overrides = contents.get("progressOverrides", {})
    progress_assertions = contents.get("progressAssertions", {})

    return compute_progress(request, list_id, read_subjects(contents), progress_overrides, progress_assertions)

def road_progress_post(request, list_id):
    """Returns the raw JSON for a given requirements list including user
    progress. The POST body should contain the JSON for the road."""
    try:
        contents = json.loads(request.body)
    except:
        return HttpResponseBadRequest("badly formatted road contents")

    progress_overrides = contents.get("progressOverrides", {})
    progress_assertions = contents.get("progressAssertions", {})
    result = compute_progress(request, list_id, read_subjects(contents), progress_overrides, progress_assertions)
    return result

def read_subjects(contents):
    """Extracts a list of subjects from a given road JSON object."""
    course_list = []
    for subj in contents.get("selectedSubjects", []):
        if SUBJECT_ID_KEY in subj:
            course_list.append(subj[SUBJECT_ID_KEY])
        elif SUBJECT_ID_ALT_KEY in subj:
            course_list.append(subj[SUBJECT_ID_ALT_KEY])
    return course_list

@csrf_exempt
def road_progress(request, list_id):
    """Returns the raw JSON for a given requirements list including user
    progress. If the method is POST, expects the road contents in the request
    body. If it is GET, expects an authorization token and a 'road' query
    parameter containing the ID number of the road to check."""

    if request.method == 'POST':
        return road_progress_post(request, list_id)
    elif 'road' in request.GET:
        return road_progress_get(request, list_id)
    else:
        # Empty course list
        return progress(request, list_id, "")

def progress(request, list_id, courses):
    """Returns the raw JSON for a given requirements list including user
    progress. The courses used to evaluate the requirements list are provided
    in courses as a comma-separated list of subject IDs."""
    return compute_progress(request, list_id, [c for c in courses.split(",") if len(c)], {}, {})

def list_reqs(request):
    """Return a JSON dictionary of all available requirements lists, with the
    basic metadata for those lists."""
    list_ids = { }
    for req in RequirementsList.objects.all():
        req_metadata = req.to_json_object(full=False)
        del req_metadata[JSONConstants.list_id]
        list_ids[req.list_id.replace(REQUIREMENTS_EXT, "")] = req_metadata
    return HttpResponse(json.dumps(list_ids), content_type="application/json")
