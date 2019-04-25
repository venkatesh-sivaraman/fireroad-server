import os
import re
import django
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
django.setup()

from courseupdater.views import *
from requirements.models import *
from catalog.models import *
from django.db import DatabaseError, transaction
from django import db
from fireroad.settings import CATALOG_BASE_DIR
from common.models import *
from common.oauth_client import LOGIN_TIMEOUT
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import datetime
from django.core.mail import send_mail
from django.conf import settings
import traceback
import csv
from django.core.exceptions import ObjectDoesNotExist

REQUIREMENTS_INFO_KEY = "r_delta"
CATALOG_FILES_INFO_KEY = "delta"

# Filenames that contain these words will be skipped
EXCLUDED_FILENAMES = ["condensed", "courses", "features", "enrollment", "departments"]

### CATALOG UPDATE

def update_catalog_with_file(path, semester):
    """Updates the catalog database using the given CSV file path."""
    with open(path, 'r') as file:
        reader = csv.reader(file)
        headers = None
        for comps in reader:
            if "Subject Id" in comps:
                headers = comps
                continue
            if headers is None:
                print("Can't read CSV file {} - no headers".format(path))
            info = dict(zip(headers, comps))
            try:
                course = Course.public_courses().get(subject_id=info["Subject Id"])
            except ObjectDoesNotExist:
                course = Course.objects.create(public=True, subject_id=info["Subject Id"])
            finally:
                course.catalog_semester = semester
                for key, val in info.items():
                    if key not in CSV_HEADERS: continue
                    prop, converter = CSV_HEADERS[key]
                    setattr(course, prop, converter(val))
                course.save()

def parse_related_file(path):
    """Updates the catalog database with the related subjects file."""
    with open(path, 'r') as file:
        for line in file:
            comps = line.strip().replace("[J]", "").split(",")
            try:
                course = Course.public_courses().get(subject_id=comps[0])
                course.related_subjects = ",".join(comps[1:])
                course.save()
            except ObjectDoesNotExist:
                continue

def update_catalog():
    """Parses all files in the current semester catalog, replacing the existing Course objects."""
    Course.public_courses().delete()

    semester = list_semesters()[-1]
    catalog_files = compute_semester_delta(semester.split("-"), 0, 0)[CATALOG_FILES_INFO_KEY]
    print(catalog_files)
    related_path = None
    for path in catalog_files:
        filename = os.path.basename(path)
        if any(f in filename for f in EXCLUDED_FILENAMES): continue
        print(filename)
        if "related" in filename:
            # Save this for last
            related_path = path
        else:
            update_catalog_with_file(os.path.join(CATALOG_BASE_DIR, path), semester)
    if related_path is not None:
        parse_related_file(os.path.join(CATALOG_BASE_DIR, related_path))

### REQUIREMENTS UPDATE

delta_prefix = "delta-"
delta_separator = "#,#"

def write_delta_file(delta, outpath):
    """Writes a delta file in the appropriate format in the given directory."""

    # Determine version number
    version_num = 1
    if os.path.exists(outpath):
        while os.path.exists(os.path.join(outpath, delta_prefix + str(version_num) + ".txt")):
            version_num += 1
    else:
        os.mkdir(outpath)

    delta_file_path = os.path.join(outpath, delta_prefix + str(version_num) + ".txt")
    with open(delta_file_path, 'w') as file:
        file.write("\n")
        file.write(str(version_num) + "\n")
        file.write("\n".join(delta))

    print("Delta file written to {}.".format(delta_file_path))

def perform_deployments():
    """Performs any pending deployments of updated requirements files."""

    delta = set()

    for deployment in Deployment.objects.filter(date_executed=None).order_by('pk'):
        print(deployment)
        try:
            for edit_req in deployment.edit_requests.all().order_by('pk'):
                if len(edit_req.contents) == 0:
                    print("Edit request {} has no contents, skipping".format(edit_req))
                    continue

                with open(os.path.join(CATALOG_BASE_DIR, requirements_dir, edit_req.list_id + ".reql"), 'w') as file:
                    file.write(edit_req.contents.encode('utf-8'))

                edit_req.committed = False
                edit_req.save()
                delta.add(edit_req.list_id)

            deployment.date_executed = timezone.now()
            deployment.save()
        except:
            print(traceback.format_exc())

    # Write delta file
    if len(delta) > 0:
        write_delta_file(sorted(delta), os.path.join(os.path.dirname(__file__), "courseupdater", requirements_dir))


def update_requirements():
    """Parses the current set of requirements and adds them to the database."""
    RequirementsList.objects.all().delete()
    RequirementsStatement.objects.all().delete()

    req_urls = compute_semester_delta(list_semesters()[-1].split('-'), 0, 0)
    for path_name in req_urls[REQUIREMENTS_INFO_KEY]:
        print(path_name)
        new_req = RequirementsList.objects.create(list_id=os.path.basename(path_name))
        with open(os.path.join(CATALOG_BASE_DIR, path_name), 'rb') as file:
            new_req.parse(file.read().decode('utf-8'))
        new_req.save()

    print("The database was successfully updated with {} requirements files.".format(len(req_urls[REQUIREMENTS_INFO_KEY])))

### EDIT REQUESTS

def check_for_edits():
    """
    Checks for unresolved edit requests, and appends their descriptions to
    the returned message if present.
    """
    edit_requests = EditRequest.objects.filter(resolved=False)
    message = ""
    if edit_requests.count() > 0:
        message += "You have {} unresolved edit requests:\n".format(edit_requests.count())
        for req in edit_requests:
            message += str(req) + "\n"
        message += "\n"
    return message

### CLEAN UP

def clean_db():
    """Removes expired OAuth caches and temporary codes from the database."""

    # Time before which all tokens and codes will be expired
    expired_threshold = timezone.now() - datetime.timedelta(seconds=LOGIN_TIMEOUT)

    num_objs = 0
    for obj in OAuthCache.objects.all():
        if obj.date < expired_threshold:
            num_objs += 1
            obj.delete()
    print("{} OAuth caches deleted".format(num_objs))

    num_objs = 0
    for obj in TemporaryCode.objects.all():
        if obj.date < expired_threshold:
            num_objs += 1
            obj.delete()
    print("{} temporary codes deleted".format(num_objs))


def email_results(message, recipients):
    """
    Sends an email to the given recipients with the given message. Prints to
    the console if email is not set up.
    """
    if not settings.FR_EMAIL_ENABLED:
        print("Email not configured.")
        return

    email_from = "FireRoad <{}>".format(settings.EMAIL_HOST_USER)
    send_mail("Daily update", message, email_from, recipients)


if __name__ == '__main__':
    message = ""
    try:
        clean_db()
    except:
        message += "Database cleaning failed:\n"
        message += traceback.format_exc()

    try:
        message += check_for_edits()
    except:
        message += "Checking for edits failed:\n"
        message += traceback.format_exc()

    try:
        perform_deployments()
    except:
        message += "Error performing requirements deployment:\n"
        message += traceback.format_exc()

    try:
        update_requirements()
    except:
        message += "Updating requirements DB failed:\n"
        message += traceback.format_exc()

    try:
        update_catalog()
    except:
        message += "Updating catalog DB failed:\n"
        message += traceback.format_exc()

    if len(message) > 0 and len(sys.argv) > 1:
        email_results(message, sys.argv[1:])
    print(message)
