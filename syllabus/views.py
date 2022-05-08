from django.shortcuts import render, redirect, reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.db.models import Q

import os

from .models import *
from catalog.models import Course


def is_staff(request):
    """Returns whether or not the request's user is an authenticated staff member."""
    return request.user is not None and request.user.is_staff and request.user.is_authenticated()

def save_syllabus_submission(form, committed, copy_file):
    data = form.cleaned_data

    syllabus_submission = SyllabusSubmission.objects.create(email_address=data["email_address"],
                                                            semester=data["semester"],
                                                            year=data["year"],
                                                            subject_id=data["subject_id"],
                                                            file=data["file"],
                                                            committed=committed)

    syllabus_submission.save()
    syllabus_submission.update_file_name(copy=copy_file)

# Create your views here.
def index(request):
    params = {'active_id': 'index', 'is_staff': is_staff(request)}
    return render(request, 'syllabus/index.html', params)

def success(request):
    return render(request, 'syllabus/success.html')

def syllabus_sortkey(syllabus):
    year_start = int(syllabus.year)
    semester_val = 0

    if syllabus.semester != 'Fall':
        year_start -= 1

    if syllabus.semester == 'IAP':
        semester_val = 1
    elif syllabus.semester == 'Spring':
        semester_val = 2
    elif syllabus.semester == 'Summer':
        semester_val = 3

    return (str(syllabus.subject_id), year_start, semester_val, syllabus.pk)

def viewer(request):
    params = {
        'active_id': 'viewer',
        'is_staff': is_staff(request)
    }

    if 'subject_id' in request.GET:
        subject_id = request.GET['subject_id']

        query = Q(subject_id__istartswith=subject_id)
        syllabi = Syllabus.objects.filter(query)
        params['search_query'] = subject_id
    else:
        syllabi = Syllabus.objects.all()
        params['search_query'] = ''

    syllabi_by_subject = {}
    for syllabus in syllabi:
        if syllabus.subject_id in syllabi_by_subject:
            syllabi_by_subject[syllabus.subject_id].append(syllabus)
        else:
            syllabi_by_subject[syllabus.subject_id] = [syllabus]

    for subject_id in syllabi_by_subject:
        syllabi_by_subject[subject_id] = sorted(syllabi_by_subject[subject_id], key=syllabus_sortkey, reverse=True)

    params['syllabi_by_subject'] = sorted(syllabi_by_subject.items())

    return render(request, 'syllabus/viewer.html', params)

def create(request):
    params = {
        'active_id': 'new_doc',
        'is_staff': is_staff(request)
    }

    if request.method == 'POST':
        copy_file = False
        if "file" in request.FILES:
            form = SyllabusForm(request.POST, request.FILES)
        else:
            syllabus_sub = request.POST["syllabus_sub"]
            syllabus_submission = SyllabusSubmission.objects.get(pk=syllabus_sub)
            form = SyllabusForm(request.POST, {"file": syllabus_submission.file})
            copy_file = True
        print(form.errors)

        if form.is_valid():
            should_commit = is_staff(request)
            save_syllabus_submission(form, committed=should_commit, copy_file=copy_file)
            if should_commit:
                return redirect('syllabus_review_all')
            return redirect('submit_success')
    else:
        form = SyllabusForm()

        if 'like' in request.GET:
            try:
                syllabus_sub_id = int(request.GET['like'])
                syllabus_submission = SyllabusSubmission.objects.get(pk=syllabus_sub_id)
                params['syllabus_sub'] = syllabus_submission.pk
                form = SyllabusForm({
                    "is_committing": is_staff(request),
                    "email_address": syllabus_submission.email_address,
                    "semester": syllabus_submission.semester,
                    "year": syllabus_submission.year,
                    "subject_id": syllabus_submission.subject_id
                }, {
                    "file": syllabus_submission.file
                })
            except ValueError:
                pass

    params['form'] = form

    return render(request, 'syllabus/create.html', params)


@staff_member_required
def review(request, syllabus_sub):
    """
    Allow admin users to review a particular syllabus submission, commit it to the list
    of changes to be added or revise and resubmit.
    """
    try:
        syllabus_submission = SyllabusSubmission.objects.get(pk=int(syllabus_sub))
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        return redirect(reverse('syllabus_index'))

    params = {
        'syllabus_submission': syllabus_submission,
        'is_staff': is_staff(request),
        'active_id': 'review'
    }

    return render(request, 'syllabus/review.html', params)

@staff_member_required
def review_all(request):
    """Displays all available syllabus submissions and allows the user to commit them."""
    params = {'active_id': 'review_all', 'is_staff': is_staff(request)}

    if request.method == 'POST':
        form = DeploySyllabusForm(request.POST)
        if form.is_valid():
            deployment = SyllabusDeployment.objects.create(author=form.cleaned_data['email_address'], summary=form.cleaned_data['summary'])

            for syllabus_submission in SyllabusSubmission.objects.filter(committed=True, resolved=False):
                syllabus_submission.deployment = deployment
                syllabus_submission.committed = True
                syllabus_submission.resolved = True
                syllabus_submission.save()
            deployment.save()

            form = DeploySyllabusForm()
    else:
        form = DeploySyllabusForm()

    params['form'] = form
    params['active_id'] = 'review_all'
    params['num_to_deploy'] = SyllabusSubmission.objects.filter(committed=True, resolved=False).count()
    params['committed'] = SyllabusSubmission.objects.filter(committed=True, resolved=False).order_by('pk')
    params['pending'] = SyllabusSubmission.objects.filter(committed=False, resolved=False).order_by('pk')
    params['deployments'] = SyllabusDeployment.objects.filter(date_executed=None).count()

    return render(request, 'syllabus/review_all.html', params)

@staff_member_required
def commit(request, syllabus_sub):
    """
    "Commits" the given syllabus submission by setting its 'committed' flag to True.
    """
    try:
        syllabus_submission = SyllabusSubmission.objects.get(pk=int(syllabus_sub))
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        return redirect(reverse('syllabus_review_all'))

    syllabus_submission.committed = True
    syllabus_submission.save()
    return redirect(reverse('syllabus_review_all'))

@staff_member_required
def uncommit(request, syllabus_sub):
    """
    Removes the committed flag from the given edit request.
    """
    try:
        syllabus_submission = SyllabusSubmission.objects.get(pk=int(syllabus_sub))
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        return redirect(reverse('syllabus_review_all'))

    syllabus_submission.committed = False
    syllabus_submission.save()
    return redirect(reverse('syllabus_review_all'))

@staff_member_required
def resolve(request, syllabus_sub):
    """
    Marks the given syllabus submission as resolved.
    """
    try:
        syllabus_submission = SyllabusSubmission.objects.get(pk=int(syllabus_sub))
    except ObjectDoesNotExist:
        raise Http404
    except ValueError:
        return redirect(reverse('syllabus_review_all'))

    syllabus_submission.committed = False
    syllabus_submission.resolved = True
    syllabus_submission.save()
    syllabus_submission.remove_file()
    return redirect(reverse('syllabus_review_all'))

@staff_member_required
def ignore_edit(request):
    return redirect(reverse('syllabus_review_all'))
