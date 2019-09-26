"""Views for the courseupdater module which handle updating the catalog,
serving the latest catalog files to the mobile apps, and allowing staff users
to update and validate newly-parsed catalogs."""

import os
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.views.decorators import staff_member_required
from django.forms.models import model_to_dict
from fireroad.settings import CATALOG_BASE_DIR
from requirements.diff import *
from catalog.models import Course
from .models import *

VERSION_RECURSION_THRESHOLD = 100
SEPARATOR = "#,#"
GLOBAL_FILE_NAMES = ["departments", "enrollment"]
REQUIREMENTS_DIR = "requirements"
SEMESTER_DIR_PREFIX = "sem-"
DELTA_FILE_PREFIX = "delta-"
DELTAS_DIRECTORY = "deltas"

def index(request):
    """Dummy view that does nothing"""
    return HttpResponse("Hello, world. You're at the courseupdater index.")

def read_delta(url):
    """Reads a delta file at the given path, and returns it as a list
    containing the semester identifier, the version number, and the list of
    changed files."""
    with open(url, 'r') as delta_file:
        lines = delta_file.readlines()
        if lines:
            semester = lines.pop(0).split(SEPARATOR)
        else:
            semester = []
        if lines:
            version = int(lines.pop(0))
        else:
            version = 0
        updated_files = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                updated_files.append(stripped)
        return semester, version, updated_files

def compute_updated_files(version, base_dir):
    """Determines the list of files that need updating, given a version in the
    past. Takes the union of all the delta files from the given version to the
    present and returns that as the list of changed files.

    Args:
        version: The version number from which the current contents should be
        compared.
        base_dir: The directory in which the delta files are located.

    Returns:
        A tuple containing the list of updated files, as well as the newest
        version number.
    """
    updated_files = set()
    version_num = version + 1
    updated_version = version
    while version_num < VERSION_RECURSION_THRESHOLD:
        url = os.path.join(base_dir, DELTA_FILE_PREFIX + '{}.txt'.format(version_num))
        if not os.path.exists(url):
            break
        _, version, delta = read_delta(url)
        if version != version_num:
            print("Wrong version number in {}".format(url))
        updated_files.update(set(delta))
        updated_version = version_num
        version_num += 1
    return updated_files, updated_version

def current_version_for_semester(semester):
    """Returns the numerical version for the given semester, e.g. "fall-2017"."""
    semester_dir = os.path.join(CATALOG_BASE_DIR, DELTAS_DIRECTORY, SEMESTER_DIR_PREFIX + semester)
    max_version = 0
    for path in os.listdir(semester_dir):
        if path.find(DELTA_FILE_PREFIX) == 0:
            ext_index = path.find(".txt")
            version = int(path[len(DELTA_FILE_PREFIX):ext_index])
            if version > max_version:
                max_version = version
    return max_version

def compute_semester_delta(semester_comps, version_num, req_version_num=-1):
    """Computes both the course catalog and requirements deltas given a
    snapshot version of the catalog and requirements.

    Args:
        semester_comps: A tuple containing the semester and the year for the
            catalog.
        version_num: The snapshot version number of the catalog to compare the
            current version to.
        req_version_num: The snapshot version number of the requirements.

    Returns:
        A JSON-compliant dictionary describing the changed files and the new
        versions of the catalog and requirements relative to the version
        numbers given.
    """
    # Walk through the delta files
    semester_dir = SEMESTER_DIR_PREFIX + semester_comps[0] + '-' + semester_comps[1]
    updated_files, updated_version = compute_updated_files(version_num,
                                                           os.path.join(CATALOG_BASE_DIR,
                                                                        DELTAS_DIRECTORY,
                                                                        semester_dir))

    # Write out the updated files to JSON
    def url_comp(x):
        """Builds a relative URL for the given file path in the catalog."""
        if x in GLOBAL_FILE_NAMES:
            return x + '.txt'
        return semester_dir + '/' + x + '.txt'
    urls_to_update = list(map(url_comp, sorted(list(updated_files))))
    resp = {'v': updated_version, 'delta': urls_to_update}

    # Check requirements also, if necessary
    if req_version_num != -1:
        updated_files, updated_version = compute_updated_files(req_version_num,
                                                               os.path.join(CATALOG_BASE_DIR,
                                                                            DELTAS_DIRECTORY,
                                                                            REQUIREMENTS_DIR))
        urls_to_update = [REQUIREMENTS_DIR + '/' + x + '.reql' for x in
                          sorted(list(updated_files))]
        resp['rv'] = updated_version
        resp['r_delta'] = urls_to_update
    return resp

def list_semesters():
    """Returns a list of semesters for which there is catalog data
    available."""
    sems = []
    for path in os.listdir(os.path.join(CATALOG_BASE_DIR, DELTAS_DIRECTORY)):
        if path.find(SEMESTER_DIR_PREFIX) == 0:
            sems.append(path[len(SEMESTER_DIR_PREFIX):])
    def semester_sort_key(x):
        """Sorts by year and places fall after spring."""
        comps = x.split('-')
        return int(comps[1]) * 10 + (5 if comps[0] == "fall" else 0)
    sems.sort(key=semester_sort_key)
    return sems

def check(request):
    """Return an HTTP Response indicating the static file URLs that need to be
    downloaded. Every version of the course static file database will include a
    'delta-x.txt' file that specifies the semester, the version number, and the file
    names that changed from the previous version. This method will compute the total
    set of files and return it."""
    semester = request.GET.get('sem', '')
    comps = semester.split(',')
    if len(comps) != 2:
        return HttpResponseBadRequest(('<h1>Invalid number of semester '
                                       'components</h1><br/><p>{}</p>').format(semester))
    version = request.GET.get('v', '')
    try:
        version_num = int(version)
    except ValueError:
        return HttpResponseBadRequest('<h1>Invalid version</h1><br/><p>{}</p>'.format(version))
    req_version = request.GET.get('rv', '')
    if req_version:
        try:
            req_version_num = int(req_version)
        except ValueError:
            return HttpResponseBadRequest(('<h1>Invalid requirements'
                                           'version</h1><br/><p>{}</p>').format(req_version))
    else:
        req_version_num = -1

    resp = compute_semester_delta(comps, version_num, req_version_num)
    return JsonResponse(resp)

def semesters(request):
    """Return a list of semesters and the most up-to-date version of the catalog for
    each one."""
    sems = list_semesters()
    resp = [{"sem": x, "v": current_version_for_semester(x)} for x in sems]
    return JsonResponse(resp)

### Catalog parser UI

def get_current_update():
    """Gets the current catalog update if one is currently uncompleted, otherwise
    returns None."""
    try:
        return CatalogUpdate.objects.filter(is_completed=False).latest('creation_date')
    except ObjectDoesNotExist:
        return None

@staff_member_required
def update_catalog(request):
    """
    Shows a page that allows the user to start a catalog update, view the
    progress of the current update, or commit the completed update.
    """
    current_update = get_current_update()
    if current_update is None:
        if request.method == 'POST':
            form = CatalogUpdateStartForm(request.POST)
            if form.is_valid():
                update = CatalogUpdate(semester=form.cleaned_data['semester'])
                update.save()
                return render(request, 'courseupdater/update_progress.html', {'update': update})
        else:
            form = CatalogUpdateStartForm()
        return render(request, 'courseupdater/start_update.html', {'form': form})
    elif current_update.is_staged:
        return render(request, 'courseupdater/update_success.html')
    elif current_update.progress == 100.0:
        if request.method == 'POST':
            form = CatalogUpdateDeployForm(request.POST)
            if form.is_valid():
                current_update.is_staged = True
                current_update.save()
                return render(request, 'courseupdater/update_success.html')
        else:
            form = CatalogUpdateDeployForm()

        diff_path = os.path.join(CATALOG_BASE_DIR, "diff.txt")
        if os.path.exists(diff_path):
            with open(diff_path, 'r') as diff_file:
                diffs = [line for line in diff_file.readlines() if len(line)]
        else:
            diffs = []
        if len(diffs) > 1000:
            message = "<p class=\"center\">{} more lines not shown</p>".format(len(diffs) - 1000)
            diffs = diffs[:1000]
            diffs.append(message)
        return render(request, 'courseupdater/review_update.html', {'diffs': diffs, 'form': form})
    else:
        print(current_update)
        return render(request, 'courseupdater/update_progress.html', {'update': current_update})

def update_progress(request):
    """Returns the current update progress as a JSON."""
    current_update = get_current_update()
    if current_update is None:
        return JsonResponse({'progress': 100.0, 'progress_message': 'No update pending.'})
    return JsonResponse({'progress': current_update.progress,
                         'progress_message': current_update.progress_message})

@staff_member_required
def reset_update(request):
    """Removes the current update's results."""
    current_update = get_current_update()
    if current_update is not None:
        current_update.is_completed = True
        current_update.save()
    return redirect(reverse('update_catalog'))

### Corrections

def get_field_value(form_data, field):
    """Gets a form value in the appropriate type (uses the field name)."""
    new_value = form_data[field]
    if "offered" in field or "is_" in field:
        new_value = True if new_value == "on" else False
    elif field.endswith("units"):
        try:
            new_value = int(new_value)
        except ValueError:
            return None
    return new_value

CORRECTION_DIFF_EXCLUDE = set(["id", "subject_id", "author", "date_added", "offered_this_year"])

@staff_member_required
def view_corrections(request):
    """Creates the page that displays all current catalog corrections."""
    diffs = []
    for correction in CatalogCorrection.objects.order_by("subject_id").values():
        subject_id = correction["subject_id"]
        changed_course = Course.public_courses().filter(subject_id=subject_id).values().first()

        diff = {}
        if changed_course:
            for field in changed_course:
                if field in CORRECTION_DIFF_EXCLUDE or "ptr" in field:
                    continue
                if field not in correction:
                    continue
                if correction[field]:
                    diff[field] = (changed_course[field], correction[field])
        else:
            for field in correction:
                if field in CORRECTION_DIFF_EXCLUDE or "ptr" in field:
                    continue
                if not correction[field]:
                    continue
                diff[field] = (None, correction[field])
        diffs.append({"subject_id": subject_id, "id": correction["id"], "diff": diff})

    return render(request, "courseupdater/corrections.html", {"diffs": diffs})

@staff_member_required
def new_correction(request):
    """Allows the user to create a new catalog correction."""
    if request.method == 'POST':
        form = CatalogCorrectionForm(request.POST)
        correction = CatalogCorrection.objects.create()
        try:
            correction.author = request.user.student.academic_id
        except ObjectDoesNotExist:
            pass
        fields = CatalogCorrectionForm._meta.fields
        for field in fields:
            new_value = get_field_value(form.data, field)
            if new_value:
                setattr(correction, field, new_value)
        correction.save()
        return redirect(reverse("catalog_corrections"))
    else:
        form = CatalogCorrectionForm()

    return render(request, "courseupdater/edit_correction.html", {"is_new": True, "form": form})

@staff_member_required
def edit_correction(request, correction_id):
    """Allows the user to edit an existing catalog correction."""
    try:
        correction = CatalogCorrection.objects.get(id=correction_id)
    except ObjectDoesNotExist:
        return redirect(reverse("catalog_corrections"))

    if request.method == 'POST':
        form = CatalogCorrectionForm(request.POST)
        # Save only the values that are different than the original correction
        fields = CatalogCorrectionForm._meta.fields
        for field in fields:
            if field not in form.data:
                continue
            existing = getattr(correction, field)
            new_value = get_field_value(form.data, field)
            if new_value != existing and new_value is not None:
                setattr(correction, field, new_value)
        try:
            correction.author = request.user.student.academic_id
        except ObjectDoesNotExist:
            pass
        correction.save()
        return redirect(reverse("catalog_corrections"))
    else:
        form = CatalogCorrectionForm(data=model_to_dict(correction))

    return render(request, "courseupdater/edit_correction.html", {"is_new": False, "form": form})

@staff_member_required
def delete_correction(request, correction_id):
    """Deletes the given catalog correction."""
    try:
        correction = CatalogCorrection.objects.get(id=correction_id)
    except ObjectDoesNotExist:
        return redirect(reverse("catalog_corrections"))
    correction.delete()
    return redirect(reverse("catalog_corrections"))
