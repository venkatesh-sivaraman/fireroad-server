from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from .models import *
from django.contrib.auth import login, authenticate, logout
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.utils.html import escape
from common.decorators import logged_in_or_basicauth
import json
import os
import requests
from courseupdater.views import *
import re
from .progress import RequirementsProgress
from catalog.models import Course, Attribute, HASSAttribute, GIRAttribute, CommunicationAttribute
import logging
from .reqlist import *
from .views import REQUIREMENTS_EXT
from django.http import Http404
from .diff import build_diff

NEW_DOC_ID = "new_doc"
NEW_DOC_NAME = "new requirements list"

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

def build_sidebar_info(request):
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

    return {'majors': majors, 'minors': minors, 'other': other, 'is_staff': is_staff(request)}

# Create your views here.
def index(request):
    params = build_sidebar_info(request)
    params['active_id'] = 'index'
    params['exists'] = False
    return render(request, "requirements/index.html", params)

def save_change_request(form, type, list_id="", committed=False):
    data = form.cleaned_data
    original_contents = None
    if type == REQUEST_TYPE_EDIT and len(list_id) > 0:
        try:
            req = RequirementsList.objects.get(list_id=list_id + REQUIREMENTS_EXT)
            original_contents = req.contents
        except:
            pass

    edit_req = EditRequest.objects.create(email_address=data["email_address"],
                                          reason=data["reason"],
                                          list_id=list_id,
                                          type=type,
                                          original_contents=original_contents,
                                          contents=data["contents"],
                                          committed=committed)
    edit_req.save()

def is_staff(request):
    """Returns whether or not the request's user is an authenticated staff member."""
    return request.user is not None and request.user.is_staff and request.user.is_authenticated

def populate_initial_text(request, params, edit_req):
    params['initial_text'] = edit_req.contents

    if 'like' in request.GET:
        # Get the edit request for initial text population
        try:
            edit_req_id = int(request.GET['like'])
            edit_req = EditRequest.objects.get(pk=edit_req_id)
            params['initial_text'] = edit_req.contents
        except:
            pass

def create(request):
    if request.method == 'POST':
        form = EditForm(request.POST)
        print((form.errors))
        if form.is_valid():
            should_commit = is_staff(request)
            save_change_request(form, REQUEST_TYPE_CREATE, list_id=form.cleaned_data['new_list_id'], committed=should_commit)
            if should_commit:
                return redirect('review_all')
            return redirect('submit_success')

    params = build_sidebar_info(request)
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
    populate_initial_text(request, params, req)
    return render(request, "requirements/edit.html", params)

def edit(request, list_id):
    req = RequirementsList.objects.get(list_id=list_id + REQUIREMENTS_EXT)
    if request.method == 'POST':
        form = EditForm(request.POST)
        if form.is_valid():
            should_commit = is_staff(request)
            save_change_request(form, REQUEST_TYPE_EDIT, list_id=list_id, committed=should_commit)
            if should_commit:
                return redirect('review_all')
            return redirect('submit_success')

    form = EditForm()
    params = build_sidebar_info(request)
    params['active_id'] = list_id
    params['req'] = req
    params['action'] = REQUEST_TYPE_EDIT
    params['form'] = form
    params['exists'] = True
    populate_initial_text(request, params, req)
    return render(request, "requirements/edit.html", params)

def success(request):
    params = build_sidebar_info(request)
    return render(request, "requirements/success.html", params)

# Rendering

@csrf_exempt
def preview(request):
    """Takes as POST body the contents of a requirements list, and returns HTML
    to display the requirements list preview."""
    if request.method != 'POST':
        return HttpResponseBadRequest("Must use POST")

    req_contents = request.body
    req_list = RequirementsList.objects.create()
    try:
        req_list.parse(req_contents, full=True)
        html = build_presentation_items(req_list)
        req_list.delete()
    except:
        req_list.delete()
        return HttpResponse("<p>An error occurred while generating the preview. Please double-check your syntax!</p>")
    return HttpResponse(html)

def show_in_row(requirement):
    """Returns whether the given requirement should be displayed in a single row."""
    if requirement.minimum_nest_depth() < 1:
        return True
    if not requirement.requirements.exists():
        return True
    if not any(r.requirement is not None for r in requirement.requirements.all()):
        return False
    if any(r.title is not None and len(r.title) > 0 for r in requirement.requirements.all()):
        return False
    return True

def make_row(requirement):
    """Returns HTML for displaying the given requirement in a row."""
    html = "<div class=\"course-list\"><div class=\"course-list-inner\">"

    if requirement.requirements.exists():
        reqs = requirement.requirements.all()
    else:
        reqs = [requirement]

    for req in reqs:
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
        items.append("<{} class=\"req-title\">{}</{}>".format(tag, title_text, tag))
    elif len(desc) > 0 and (requirement.connection_type != CONNECTION_TYPE_ALL or always_show_title) and not requirement.is_plain_string:
        items.append("<h4 class=\"req-title\">{}:</h4>".format(desc[0].upper() + desc[1:]))

    if requirement.description is not None and len(requirement.description) > 0:
        items.append("<p class=\"req\">{}</p>".format(requirement.description.replace("\n\n", "<br/><br/>")))

    if level == 0 and requirement.title is None and len(desc) > 0 and not (requirement.connection_type != CONNECTION_TYPE_ALL or always_show_title):
        items.append("<h4 class=\"req-title\">{}:</h4>".format(desc[0].upper() + desc[1:]))

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
        ret = presentation_items(list, 0)
    else:
        if list.title is not None and len(list.title) > 0:
            ret.append("<h1 class=\"req-title\">{}</h1>".format(list.title))

        if list.description is not None and len(list.description) > 0:
            ret.append("<p class=\"req\">{}</p>".format(list.description.replace("\n\n", "<br/><br/>")))

        for top_req in list.requirements.all():
            rows = presentation_items(top_req, 0)
            ret += rows
    return "\n".join(ret)

# Review and commit (admin only)

@staff_member_required
def review(request, edit_req):
    """
    Allow admin users to review a particular edit request, commit it to the list
    of changes to be added or revise and resubmit.
    """
    try:
        edit_request = EditRequest.objects.get(pk=int(edit_req))
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        return redirect(reverse('requirements_index'))

    params = build_sidebar_info(request)
    params['edit_req'] = edit_request
    params['action'] = "Review"

    req_list = RequirementsList.objects.create()
    try:
        req_list.parse(edit_request.contents, full=False)
        params['medium_title'] = req_list.medium_title
        req_list.delete()
    except:
        req_list.delete()
        params['medium_title'] = '<could not parse>'

    if edit_request.type == REQUEST_TYPE_EDIT:
        try:
            req_list = RequirementsList.objects.get(list_id=edit_request.list_id + REQUIREMENTS_EXT)
            params['diff'] = build_diff(req_list.contents, edit_request.contents)
        except ObjectDoesNotExist:
            params['diff'] = 'The edit request refers to a non-existent requirements list.'
    else:
        params['diff'] = '\n'.join(['<p class="diff-line">' + escape(line) + '</p>' for line in edit_request.contents.split('\n')])

    return render(request, 'requirements/review.html', params)

def count_conflicts(reqs_to_deploy):
    """Counts the number of committed changes that would override a previous pending deployment."""
    conflicts = set()
    list_ids = set(req.list_id for req in reqs_to_deploy.all())
    print(list_ids)
    for deployment in Deployment.objects.filter(date_executed=None):
        for other_req in deployment.edit_requests.all():
            print(other_req)
            if other_req.list_id in list_ids:
                conflicts.add(other_req.list_id)
    return len(conflicts)

@staff_member_required
def review_all(request):
    """Displays all available edit requests and allows the user to commit them."""
    if request.method == 'POST':
        form = DeployForm(request.POST)
        if form.is_valid():
            deployment = Deployment.objects.create(author=form.cleaned_data['email_address'], summary=form.cleaned_data['summary'])
            for edit_req in EditRequest.objects.filter(committed=True, resolved=False):
                # Resolve this edit request, and show when it was deployed
                edit_req.deployment = deployment
                edit_req.committed = True
                edit_req.resolved = True
                edit_req.save()
            deployment.save()
            # Go back and re-render the same page

    params = build_sidebar_info(request)
    form = DeployForm()
    params['form'] = form
    params['active_id'] = 'review_all'
    params['num_to_deploy'] = EditRequest.objects.filter(committed=True, resolved=False).count()
    params['committed'] = EditRequest.objects.filter(committed=True, resolved=False).order_by('pk')
    params['pending'] = EditRequest.objects.filter(committed=False, resolved=False).order_by('pk')
    params['deployments'] = Deployment.objects.filter(date_executed=None).count()
    params['conflicts'] = count_conflicts(params['committed'])
    return render(request, 'requirements/review_all.html', params)

@staff_member_required
def commit(request, edit_req):
    """
    "Commits" the given edit request by setting its 'committed' flag to True.
    """
    try:
        edit_request = EditRequest.objects.get(pk=int(edit_req))
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        return redirect(reverse('review_all'))

    edit_request.committed = True
    edit_request.save()
    return redirect(reverse('review_all'))

@staff_member_required
def uncommit(request, edit_req):
    """
    Removes the committed flag from the given edit request.
    """
    try:
        edit_request = EditRequest.objects.get(pk=int(edit_req))
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        return redirect(reverse('review_all'))

    edit_request.committed = False
    edit_request.save()
    return redirect(reverse('review_all'))

@staff_member_required
def ignore_edit(request, edit_req):
    return redirect(reverse('review_all'))

@staff_member_required
def resolve(request, edit_req):
    """
    Marks the given edit request as resolved.
    """
    try:
        edit_request = EditRequest.objects.get(pk=int(edit_req))
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        return redirect(reverse('review_all'))

    edit_request.committed = False
    edit_request.resolved = True
    edit_request.save()
    return redirect(reverse('review_all'))
