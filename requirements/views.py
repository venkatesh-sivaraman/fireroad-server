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
from catalog.models import Course, CourseAttributeLists
import logging

REQUIREMENTS_EXT = ".reql"
NEW_DOC_ID = "new_doc"
NEW_DOC_NAME = "new requirements list"
REQUEST_TYPE_EDIT = "Edit"
REQUEST_TYPE_CREATE = "Create"

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split('(\d+)', text) ]

def build_sidebar_info():
    discovered = set()

    majors = []
    for reqlist in RequirementsList.objects.filter(list_id__contains="major"):
        discovered.add(reqlist.list_id)
        majors.append({'id': reqlist.list_id.replace(REQUIREMENTS_EXT, ""), 'short': reqlist.medium_title, 'long': reqlist.title_no_degree})
    majors.sort(key=lambda x: natural_keys(x['short']))

    minors = []
    for reqlist in RequirementsList.objects.filter(list_id__contains="minor"):
        discovered.add(reqlist.list_id)
        minors.append({'id': reqlist.list_id.replace(REQUIREMENTS_EXT, ""), 'short': reqlist.medium_title, 'long': reqlist.title_no_degree})
    minors.sort(key=lambda x: natural_keys(x['short']))

    other = []
    for reqlist in RequirementsList.objects.all():
        if reqlist.list_id in discovered: continue
        other.append({'id': reqlist.list_id.replace(REQUIREMENTS_EXT, ""), 'short': reqlist.medium_title, 'long': reqlist.title_no_degree})
    other.sort(key=lambda x: natural_keys(x['short']))

    return {'majors': majors, 'minors': minors, 'other': other}

# Create your views here.
def index(request):
    params = build_sidebar_info()
    params['active_id'] = 'index'
    params['exists'] = False
    return render(request, "requirements/index.html", params)

def save_change_request(form, type):
    data = form.cleaned_data
    edit_req = EditRequest.objects.create(email_address=data["email_address"],
                                          reason=data["reason"],
                                          type=type,
                                          contents=data["contents"])
    edit_req.save()

def create(request):
    if request.method == 'POST':
        form = EditForm(request.POST)
        if form.is_valid():
            save_change_request(form, REQUEST_TYPE_CREATE)
            return redirect('submit_success')

    params = build_sidebar_info()
    req = RequirementsList(list_id=NEW_DOC_ID,
                           short_title=NEW_DOC_NAME,
                           medium_title=NEW_DOC_NAME,
                           title=NEW_DOC_NAME)
    req.contents = "X#,#X Major#,#Title No Degree#,#Title With Degree\nDescription\n\nsection_1\nDescription of section 1\n...\n\n%% Variable declarations\n\nsection_1, \"Section 1\" := ..."
    form = EditForm()
    params['form'] = form
    params['req'] = req
    params['active_id'] = params['req'].list_id
    params['action'] = REQUEST_TYPE_CREATE
    params['exists'] = False
    return render(request, "requirements/edit.html", params)

def edit(request, list_id):
    req = RequirementsList.objects.get(list_id=list_id + REQUIREMENTS_EXT)
    if request.method == 'POST':
        form = EditForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["contents"] != req.contents:
                save_change_request(form, REQUEST_TYPE_EDIT)
            return redirect('submit_success')

    form = EditForm()
    params = build_sidebar_info()
    params['active_id'] = list_id
    params['req'] = req
    params['action'] = REQUEST_TYPE_EDIT
    params['form'] = form
    params['exists'] = True
    return render(request, "requirements/edit.html", params)

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
        progress_overrides = json.loads(request.user.student.progress_overrides)

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
            is_generic_course = False
            if("." not in subject_id):
                #potential a generic course
                #generic course could have more than one attribute, e.g. CI-H HASS-A
                subject_ids = subject_id.split(" ")
                #dict of attributes and values to add to created Course object
                attribute_dict = dict()
                #attributes to test for in generic course (gets a list of CourseAttributeLists properties that aren't hidden)
                tested_attributes = [attr for attr in CourseAttributeLists.__dict__.keys() if "__" not in attr]

                is_generic_course = True
                for subject_attribute in subject_ids:
                    #each spaced delimited subject attribute must be sensical
                    subject_attribute_exists = False
                    for attr in tested_attributes:
                        #if the course matches a generic attribute, it is a generic course with that attribute
                        if subject_attribute in CourseAttributeLists.__dict__[attr]:
                            attribute_dict[attr] = subject_attribute
                            subject_attribute_exists = True

                    if not subject_attribute_exists:
                        is_generic_course = False

                #add all matching attributes to generic course
                if is_generic_course:
                    generic_course = Course(id=subject_id+str(unique_generic_id),subject_id=subject_id)
                    unique_generic_id += 1
                    for attr in tested_attributes:
                        if attr in attribute_dict:
                            generic_course.__dict__[attr] = attribute_dict[attr]
                    course_objs.append(generic_course)
            if not is_generic_course:
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

def success(request):
    params = build_sidebar_info()
    return render(request, "requirements/success.html", params)
