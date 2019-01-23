from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
import os
import json
from .models import Course
from django.db.models import Q

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
        c = Course.public_courses().get(subject_id=subject_id)
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
    courses = Course.public_courses().filter(subject_id__startswith=dept + ".").order_by("subject_id")
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
    return HttpResponse(json.dumps([c.to_json_object(full=full) for c in Course.public_courses().order_by("subject_id")]), content_type="application/json")

def offered_filter(offered_value):
    """Constructs a Q filter based on the given offered value, or throws a
    ValueError if the value is inappropriate."""
    offered_value = offered_value.lower()
    if offered_value == "off":
        return None
    elif offered_value == "fall":
        return Q(offered_fall=True)
    elif offered_value == "spring":
        return Q(offered_spring=True)
    elif offered_value == "iap":
        return Q(offered_IAP=True)
    elif offered_value == "summer":
        return Q(offered_summer=True)
    else:
        raise ValueError

def level_filter(level_value):
    """Constructs a Q filter based on the given level value, or throws a
    ValueError if the value is inappropriate."""
    level_value = level_value.lower()
    if level_value == "off":
        return None
    elif level_value == "undergrad":
        return Q(level="U")
    elif level_value == "grad":
        return Q(level="G")
    else:
        raise ValueError

def ci_filter(ci_value):
    """Constructs a Q filter based on the given CI value, or throws a
    ValueError if the value is inappropriate."""
    ci_value = ci_value.lower()
    if ci_value == "off":
        return None
    elif ci_value == "cih":
        return Q(communication_requirement="CI-H")
    elif ci_value == "cihw":
        return Q(communication_requirement="CI-HW")
    elif ci_value == "not-ci":
        return Q(communication_requirement__isnull=True) | Q(communication_requirement="")
    else:
        raise ValueError

def hass_filter(hass_value):
    """Constructs a Q filter based on the given HASS value, or throws a
    ValueError if the value is inappropriate."""
    hass_value = hass_value.lower()
    if hass_value == "off":
        return None
    elif hass_value == "any":
        return ~Q(hass_attribute="")
    elif hass_value in {"a", "s", "h"}:
        return Q(hass_attribute="HASS-" + hass_value.upper())
    else:
        raise ValueError

def gir_filter(gir_value):
    """Constructs a Q filter based on the given GIR value, or throws a
    ValueError if the value is inappropriate."""
    gir_value = gir_value.lower()
    if gir_value == "off":
        return None
    elif gir_value == "any":
        return ~Q(gir_attribute="")
    elif gir_value in {"lab", "rest"}:
        return Q(gir_attribute=gir_value.upper())
    else:
        raise ValueError

def construct_search_query(search_term, type):
    """Constructs a Q filter based on the given search term, using the given
    search type (contains, matches, etc.)."""
    if type == "contains":
        return Q(subject_id__icontains=search_term) | Q(title__icontains=search_term)
    elif type == "matches":
        return Q(subject_id__iexact=search_term) | Q(title__iexact=search_term)
    elif type == "starts":
        return Q(subject_id__istartswith=search_term) | Q(title__istartswith=search_term)
    elif type == "ends":
        return Q(subject_id__iendswith=search_term) | Q(title__iendswith=search_term)
    else:
        raise ValueError


def search(request, search_term=None):
    """
    Searches the catalog database for courses matching the given search term.
    The following case-insensitive GET parameter options are available:

    type: The match type to use with the search term. Possible values: "contains"
        (default), "matches", "starts", "ends"
    gir: Whether to filter by GIR. Possible values: "off" (default), "any", "lab",
        "rest"
    hass: Whether to filter by HASS fulfillment. Possible values: "off" (default),
        "any", "a", "s", "h"
    ci: Whether to filter by CI fulfillment. Possible values: "off" (default),
        "cih", "cihw", "not-ci"
    offered: Which semester the course is offered. Possible values: "off"
        (default), "fall", "spring", "IAP", "summer"
    level: The level of the course. Possible values: "off" (default), "undergrad",
        "grad"
    full: Boolean indicating whether to return the full course description.
        Possible values: "n" (default), "y"

    TODO: search fields, schedule conflicts
    """
    if search_term is None:
        return HttpResponseBadRequest("Must provide a search term.")

    try:
        # Construct query
        query = construct_search_query(search_term, request.GET.get("type", "contains"))
        if "offered" in request.GET:
            filter = offered_filter(request.GET["offered"])
            if filter is not None: query &= filter
        if "level" in request.GET:
            filter = level_filter(request.GET["level"])
            if filter is not None: query &= filter
        if "gir" in request.GET:
            filter = gir_filter(request.GET["gir"])
            if filter is not None: query &= filter
        if "hass" in request.GET:
            filter = hass_filter(request.GET["hass"])
            if filter is not None: query &= filter
        if "ci" in request.GET:
            filter = ci_filter(request.GET["ci"])
            if filter is not None: query &= filter
    except ValueError:
        return HttpResponseBadRequest("Invalid filter value")

    # Search by query
    results = Course.public_courses().filter(query)
    if "full" in request.GET:
        full = request.GET["full"].lower() in TRUE_SET
    else:
        full = False
    return HttpResponse(json.dumps([c.to_json_object(full=full) for c in results]), content_type="application/json")
