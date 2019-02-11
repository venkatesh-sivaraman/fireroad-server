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
from reqlist import *
from views import REQUIREMENTS_EXT

NEW_DOC_ID = "new_doc"
NEW_DOC_NAME = "new requirements list"
REQUEST_TYPE_EDIT = "Edit"
REQUEST_TYPE_CREATE = "Create"

KNOWN_DEPARTMENTS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "14", "15", "16", "17", "18", "20", "21", "21A", "21W", "CMS", "21G", "21H", "21L", "21M", "WGS", "22", "24", "CC", "CSB", "EC", "EM", "ES", "HST", "IDS", "MAS", "SCM", "STS", "SWE", "SP"]

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

def success(request):
    params = build_sidebar_info()
    return render(request, "requirements/success.html", params)

# Rendering

@csrf_exempt
def preview(request):
    """Takes as POST body the contents of a requirements list, and returns HTML
    to display the requirements list preview."""
    if request.method != 'POST':
        return HttpResponseBadRequest("Must use POST")

    req_contents = request.body.decode('utf-8')
    req_list = RequirementsList.objects.create()
    try:
        req_list.parse(req_contents, full=True)
        html = build_presentation_items(req_list)
        req_list.delete()
    except:
        req_list.delete()
        raise
    return HttpResponse(html)

def show_in_row(requirement):
    """Returns whether the given requirement should be displayed in a single row."""
    if requirement.minimum_nest_depth() <= 1:
        return True
    if not requirement.requirements.exists():
        return False
    if not any(r.requirement is not None for r in requirement.requirements.all()):
        return False
    if any(r.title is not None and len(r.title) > 0 for r in requirement.requirements.all()):
        return False
    return True

def make_row(requirement):
    """Returns HTML for displaying the given requirement in a row."""
    html = u"<div class=\"course-list\"><div class=\"course-list-inner\">"
    for req in requirement.requirements.all():
        html += "<div class=\"course-tile-outer\">"
        desc = req.short_description()

        tile_classes = "card hoverable white-text course-tile"
        dept = desc[:desc.find(".")] if "." in desc else "none"
        if dept not in KNOWN_DEPARTMENTS:
            dept = "none"
        html += "<div class=\"{} course-{}\">".format(tile_classes, dept)

        try:
            course = Course.public_courses().get(subject_id=desc)
            html += "<span class=\"course-id\">" + desc + "</span>"
            html += "<br/>"
            html += "<span class=\"course-title\">" + course.title + "</span>"
        except ObjectDoesNotExist:
            html += "<span class=\"course-id\">" + desc + "</span>"

        html += "</div></div>"
    html += "</div></div>"
    return html

def presentation_items(requirement, level, always_show_title=False):
    """Generates JSON presentation items for the given requirement at the given
    level."""
    items = []
    desc = requirement.threshold_description()
    if requirement.title is not None and len(requirement.title) > 0:
        tag = "h4"
        if level == 0: tag = "h2"
        elif level <= 2: tag = "h3"

        title_text = requirement.title
        if len(desc) > 0 and requirement.connection_type != CONNECTION_TYPE_ALL and not requirement.is_plain_string:
            title_text += " (" + desc + ")"
        items.append(u"<{} class=\"req-title\">{}</{}>".format(tag, title_text, tag))
    elif len(desc) > 0 and (requirement.connection_type != CONNECTION_TYPE_ALL or always_show_title) and not requirement.is_plain_string:
        items.append(u"<h4 class=\"req-title\">{}:</h4>".format(desc[0].upper() + desc[1:]))

    if requirement.description is not None and len(requirement.description) > 0:
        items.append(u"<p class=\"req\">{}</p>".format(requirement.description.replace("\n\n", "<br/><br/>")))

    if level == 0 and requirement.title is None and len(desc) > 0 and not (requirement.connection_type != CONNECTION_TYPE_ALL or always_show_title):
        items.append(u"<h4 class=\"req-title\">{}:</h4>".format(desc[0].upper() + desc[1:]))

    if show_in_row(requirement):
        # Show all the child requirements in a single row
        items.append(make_row(requirement))
    elif requirement.requirements.exists():
        # Show each child requirement as a separate row
        show_titles = any(r.connection_type == CONNECTION_TYPE_ALL and r.requirements.exists() and r.requirements.count() > 0 for r in requirement.requirements.all())
        for req in requirement.requirements.all():
            items += presentation_items(req, level + 1, show_titles)

    return items

def build_presentation_items(list):
    """Builds HTML for the given requirements list."""
    if not list.requirements.exists():
        return ""

    ret = []
    if list.maximum_nest_depth() <= 1:
        ret.append(presentation_items(list))
    else:
        if list.title is not None and len(list.title) > 0:
            ret.append(u"<h1 class=\"req-title\">{}</h1>".format(list.title))

        if list.description is not None and len(list.description) > 0:
            ret.append(u"<p class=\"req\">{}</p>".format(list.description.replace("\n\n", "<br/><br/>")))

        for top_req in list.requirements.all():
            rows = presentation_items(top_req, 0)
            ret += rows
    return "\n".join(ret)

def render_reqlist(req_list):
    """Returns JSON instructions for how to display the given requirements list."""
