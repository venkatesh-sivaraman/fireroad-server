from django.shortcuts import render, redirect, reverse
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist

from .models import *
from catalog.models import Course


def is_staff(request):
    """Returns whether or not the request's user is an authenticated staff member."""
    return request.user is not None and request.user.is_staff and request.user.is_authenticated()

def save_syllabus_submission(form, committed):
    data = form.cleaned_data

    try:
        course = Course.objects.get(subject_id=data["subject_id"])
    except ObjectDoesNotExist:
        course = Course.objects.get(old_id=data["subject_id"])

    syllabus_submission = SyllabusSubmission.objects.create(email_address=data["email_address"],
                                                            semester=data["semester"],
                                                            year=data["year"],
                                                            subject=course,
                                                            file=data["file"],
                                                            committed=committed)
    syllabus_submission.save()

# Create your views here.
def index(request):
    params = {'active_id': 'index', 'is_staff': is_staff(request)}
    return render(request, 'syllabus/index.html', params)

def success(request):
    return render(request, 'syllabus/success.html')

def viewer(request):
    params = {'active_id': 'viewer', 'is_staff': is_staff(request)}
    return render(request, 'syllabus/viewer.html', params)

def create(request):
    if request.method == 'POST':
        form = SyllabusForm(request.POST, request.FILES)
        print(form.errors)

        if form.is_valid():
            should_commit = is_staff(request)
            save_syllabus_submission(form, committed=should_commit)
            if should_commit:
                return redirect('syllabus_review_all')
            return redirect('submit_success')
    else:
        form = SyllabusForm()

    params = {'active_id': 'new_doc', 'is_staff': is_staff(request), 'form': form}
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
            pass
            # deployment = Deployment.objects.create(author=form.cleaned_data['email_address'], summary=form.cleaned_data['summary'])
            # for edit_req in EditRequest.objects.filter(committed=True, resolved=False):
            #     # Resolve this edit request, and show when it was deployed
            #     edit_req.deployment = deployment
            #     edit_req.committed = True
            #     edit_req.resolved = True
            #     edit_req.save()
            # deployment.save()
            # Go back and re-render the same page
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
    return redirect(reverse('syllabus_review_all'))
