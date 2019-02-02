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
import re
from progress import RequirementsProgress
from catalog.models import Course, Attribute, HASSAttribute, GIRAttribute, CommunicationAttribute
import logging

REQUIREMENTS_EXT = ".reql"

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

def progress(request, list_id, courses):
    """Returns the raw JSON for a given requirements list including user
    progress. The courses used to evaluate the requirements list are provided
    in courses as a comma-separated list of subject IDs."""
    req = None

    progress_overrides = {}
    if request.user.is_authenticated():
        try:
            progress_overrides = json.loads(request.user.student.progress_overrides)
        except:
            print("Progress overrides json failed to load correctly")

    try:
        req = RequirementsList.objects.get(list_id=list_id + REQUIREMENTS_EXT)
    except ObjectDoesNotExist:
        return HttpResponseBadRequest("the requirements list {} does not exist".format(list_id))

    # Get Course objects
    course_objs = []
    #required to give generic courses unique id's so muliple can count towards requirement
    unique_generic_id = 0
    for subject_id in [c for c in courses.split(",") if len(c)]:
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
    prog.compute(course_objs, progress_overrides)
    # to pretty-print, use these keyword arguments to json.dumps:
    # sort_keys=True, indent=4, separators=(',', ': ')
    return HttpResponse(json.dumps(prog.to_json_object(True)), content_type="application/json")

def list_reqs(request):
    """Return a JSON dictionary of all available requirements lists, with the
    basic metadata for those lists."""
    list_ids = { }
    for req in RequirementsList.objects.all():
        req_metadata = req.to_json_object(full=False)
        del req_metadata[JSONConstants.list_id]
        list_ids[req.list_id.replace(REQUIREMENTS_EXT, "")] = req_metadata
    return HttpResponse(json.dumps(list_ids), content_type="application/json")
