from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
import os
import json
from .models import Course

# Create your views here.
TRUE_SET = {"true", "yes", "y", "t", "1"}

def lookup(request, subject_id=None):
    """
    Provides a full JSON description of the course specified by the given subject
    ID.
    """
    if subject_id is None:
        return HttpResponseBadRequest("Provide a subject ID to look up a course.")
    try:
        c = Course.objects.get(subject_id=subject_id)
        return HttpResponse(json.dumps(c.to_json_object()), content_type="application/json")
    except ObjectDoesNotExist:
        return HttpResponseNotFound("No subject found with the given ID")

def department(request, dept=None):
    """
    Provides a list of JSON descriptions of the courses whose subject IDs begin
    with the given department code. If a boolean GET parameter for "full" is
    specified, it will indicate whether the full JSON description is included.
    """
    if dept is None:
        return HttpResponseBadRequest("Provide a department to look up its courses.")
    if "full" in request.GET:
        full = request.GET["full"].lower() in TRUE_SET
    else:
        full = False
    courses = Course.objects.filter(subject_id__startswith=dept + ".").order_by("subject_id")
    return HttpResponse(json.dumps([c.to_json_object(full=full) for c in courses]), content_type="application/json")

def list_all(request):
    """
    Provides a list of JSON descriptions of all courses in the database. If a
    boolean GET parameter for "full" is specified, it will indicate whether the
    full JSON description is included.
    """
    if "full" in request.GET:
        full = request.GET["full"].lower() in TRUE_SET
    else:
        full = False
    return HttpResponse(json.dumps([c.to_json_object(full=full) for c in Course.objects.order_by("subject_id")]), content_type="application/json")
