from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, HttpResponseBadRequest
import os
import json
import shutil
from .models import *
from catalog.models import Course
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.views.decorators import staff_member_required
from django.forms.models import model_to_dict
from django.conf import settings
from zipfile import ZipFile
from io import StringIO
from requirements.diff import *
import catalog_parse as cp

version_recursion_threshold = 100
separator = "#,#"
global_file_names = ["departments", "enrollment"]
requirements_dir = "requirements"
semester_dir_prefix = "sem-"
delta_file_prefix = "delta-"
deltas_directory = "deltas"

def index(request):
    return HttpResponse("Hello, world. You're at the courseupdater index.")

def read_delta(url):
    with open(url, 'r') as file:
        ret = []
        lines = file.readlines()
        if len(lines) > 0:
            ret.append(lines.pop(0).split(separator))
        else:
            ret.append([])
        if len(lines) > 0:
            version = lines.pop(0)
            ret.append(int(version))
        else:
            ret.append(0)
        updated_files = []
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 0:
                updated_files.append(stripped)
        ret.append(updated_files)
        return ret

def compute_updated_files(version, base_dir):
    updated_files = set()
    version_num = version + 1
    updated_version = version
    while version_num < version_recursion_threshold:
        url = os.path.join(base_dir, delta_file_prefix + '{}.txt'.format(version_num))
        if not os.path.exists(url):
            break
        semester, version, delta = read_delta(url)
        if version != version_num:
            print(("Wrong version number in {}".format(url)))
        updated_files.update(set(delta))
        updated_version = version_num
        version_num += 1
    return updated_files, updated_version

"""Returns the numerical version for the given semester, e.g. "fall-2017"."""
def current_version_for_catalog(catalog_name):
    catalog_dir = os.path.join(settings.CATALOG_BASE_DIR, deltas_directory, catalog_name)
    max_version = 0
    for path in os.listdir(catalog_dir):
        if path.find(delta_file_prefix) == 0:
            ext_index = path.find(".txt")
            version = int(path[len(delta_file_prefix):ext_index])
            if version > max_version:
                max_version = version
    return max_version

def compute_semester_delta(semester_comps, version_num, req_version_num=-1):
    # Walk through the delta files
    semester_dir = semester_dir_prefix + semester_comps[0] + '-' + semester_comps[1]
    updated_files, updated_version = compute_updated_files(version_num, os.path.join(settings.CATALOG_BASE_DIR, deltas_directory, semester_dir))

    # Write out the updated files to JSON
    def url_comp(x):
        if x in global_file_names:
            return x + '.txt'
        return semester_dir + '/' + x + '.txt'
    urls_to_update = list(map(url_comp, sorted(list(updated_files))))
    resp = {'v': updated_version, 'delta': urls_to_update}

    # Check requirements also, if necessary
    if req_version_num != -1:
        updated_files, updated_version = compute_updated_files(req_version_num,
                                                               os.path.join(settings.CATALOG_BASE_DIR, deltas_directory, requirements_dir))
        urls_to_update = list([requirements_dir + '/' + x + '.reql' for x in sorted(list(updated_files))])
        resp['rv'] = updated_version
        resp['r_delta'] = urls_to_update
    return resp

def list_semesters():
    sems = []
    for path in os.listdir(os.path.join(settings.CATALOG_BASE_DIR, deltas_directory)):
        if path.find(semester_dir_prefix) == 0:
            sems.append(path[len(semester_dir_prefix):])
    def semester_sort_key(x):
        comps = x.split('-')
        return int(comps[1]) * 10 + (5 if comps[0] == "fall" else 0)
    sems.sort(key=semester_sort_key)
    return sems

'''Return an HTTP Response indicating the static file URLs that need to be
downloaded. Every version of the course static file database will include a
'delta-x.txt' file that specifies the semester, the version number, and the file
names that changed from the previous version. This method will compute the total
set of files and return it.'''
def check(request):
    semester = request.GET.get('sem', '')
    comps = semester.split(',')
    if len(comps) != 2:
        return HttpResponseBadRequest('<h1>Invalid number of semester components</h1><br/><p>{}</p>'.format(semester))
    version = request.GET.get('v', '')
    try:
        version_num = int(version)
    except ValueError:
        return HttpResponseBadRequest('<h1>Invalid version</h1><br/><p>{}</p>'.format(version))
    req_version = request.GET.get('rv', '')
    if len(req_version) > 0:
        try:
            req_version_num = int(req_version)
        except ValueError:
            return HttpResponseBadRequest('<h1>Invalid requirements version</h1><br/><p>{}</p>'.format(req_version))
    else:
        req_version_num = -1

    resp = compute_semester_delta(comps, version_num, req_version_num)
    return HttpResponse(json.dumps(resp), content_type="application/json")

"""Return a list of semesters and the most up-to-date version of the catalog for
each one."""
def semesters(request):
    sems = list_semesters()
    resp = list([{"sem": x, "v": current_version_for_catalog(semester_dir_prefix + x)} for x in sems])
    return HttpResponse(json.dumps(resp), content_type="application/json")

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
                update = CatalogUpdate(semester=form.cleaned_data['semester'],
                                       designate_virtual_status=form.cleaned_data['designate_virtual_status'])
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

        diff_path = os.path.join(settings.CATALOG_BASE_DIR, "diff.txt")
        if os.path.exists(diff_path):
            with open(diff_path, 'r') as file:
                diffs = [line for line in file.readlines() if len(line)]
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
        return HttpResponse(json.dumps({'progress': 100.0, 'progress_message': 'No update pending.'}), content_type='application/json')
    return HttpResponse(json.dumps({'progress': current_update.progress, 'progress_message': current_update.progress_message}), content_type='application/json')

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
    for correction in list(CatalogCorrection.objects.order_by("subject_id").values()):
        subject_id = correction["subject_id"]
        changed_course = list(Course.public_courses().filter(subject_id=subject_id).values()).first()

        diff = {}
        if changed_course:
            for field in changed_course:
                if field in CORRECTION_DIFF_EXCLUDE or "ptr" in field: continue
                if field not in correction: continue
                if correction[field]:
                    diff[field] = (changed_course[field], correction[field])
        else:
            for field in correction:
                if field in CORRECTION_DIFF_EXCLUDE or "ptr" in field: continue
                if not correction[field]: continue
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
        except:
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
def edit_correction(request, id):
    """Allows the user to edit an existing catalog correction."""
    try:
        correction = CatalogCorrection.objects.get(id=id)
    except ObjectDoesNotExist:
        return redirect(reverse("catalog_corrections"))

    if request.method == 'POST':
        form = CatalogCorrectionForm(request.POST)
        # Save only the values that are different than the original correction
        fields = CatalogCorrectionForm._meta.fields
        for field in fields:
            if field not in form.data: continue
            existing = getattr(correction, field)
            new_value = get_field_value(form.data, field)
            if new_value != existing and new_value is not None:
                setattr(correction, field, new_value)
        try:
            correction.author = request.user.student.academic_id
        except:
            pass
        correction.save()
        return redirect(reverse("catalog_corrections"))
    else:
        form = CatalogCorrectionForm(data=model_to_dict(correction))

    return render(request, "courseupdater/edit_correction.html", {"is_new": False, "form": form})

@staff_member_required
def delete_correction(request, id):
    """Deletes the given catalog correction."""
    try:
        correction = CatalogCorrection.objects.get(id=id)
    except ObjectDoesNotExist:
        return redirect(reverse("catalog_corrections"))
    correction.delete()
    return redirect(reverse("catalog_corrections"))


### Downloading the Catalog

def write_data_and_deltas_to_zip(zf, dir_name, delta_header, base_path):
    semester_path = os.path.join(settings.CATALOG_BASE_DIR, dir_name)
    for path in os.listdir(semester_path):
        if path.startswith("."): continue
        with open(os.path.join(semester_path, path), "r") as file:
            zf.writestr(os.path.join(base_path, dir_name, path), file.read())
    
    # Write a delta file for it as well
    deltas_dir = os.path.join(settings.CATALOG_BASE_DIR,
                                deltas_directory,
                                dir_name)
    updated_files, _ = compute_updated_files(0, deltas_dir)
    zf.writestr(os.path.join(base_path,
                                deltas_directory,
                                dir_name,
                                delta_file_prefix + "1.txt"),
                "{}\n1\n{}".format(
                    delta_header, "\n".join(updated_files)
                ))

@staff_member_required
def download_catalog_data(request):
    """
    Downloads a ZIP file containing all of the necessary catalog data to start
    a local copy of the server.
    """
    buffer = StringIO()
    base_path = "catalogs"

    with ZipFile(buffer, 'w') as zf:
        semesters = list_semesters()
        if semesters:
            # First write the most recent semester's data
            cat_name = semester_dir_prefix + semesters[-1]
            write_data_and_deltas_to_zip(zf, cat_name, separator.join(semesters[-1].split("-")), base_path)

        write_data_and_deltas_to_zip(zf, requirements_dir, "", base_path)

        # Create a raw directory for future parses
        zf.writestr(os.path.join(base_path, "raw", ".sentinel"), "This directory will hold raw catalog data results")

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/force-download')
    response['Content-Disposition'] = 'attachment; filename="catalogs.zip"'
    return response
