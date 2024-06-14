import os
import re
import django
import sys

django.setup()

from courseupdater.views import *
from courseupdater.models import CatalogUpdate
import catalog_parse as cp
from requirements.models import *
from syllabus.models import *
from catalog.models import *
from sync.models import *
from django.db import DatabaseError, transaction
from django import db
from common.models import *
from common.oauth_client import LOGIN_TIMEOUT
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import datetime
from django.core.mail import send_mail
from django.conf import settings
import traceback
import csv
import json
from django.core.exceptions import ObjectDoesNotExist
from catalog_parse.utils.catalog_constants import CourseAttribute
from django.utils import timezone
from analytics.models import RequestCount

REQUIREMENTS_INFO_KEY = "r_delta"
CATALOG_FILES_INFO_KEY = "delta"

# Filenames that contain these words will be skipped
EXCLUDED_FILENAMES = ["condensed", "courses", "features", "enrollment", "departments"]

### CATALOG UPDATE

def deploy_catalog_updates():
    """Deploys any staged catalog update if one exists."""
    for update in CatalogUpdate.objects.filter(is_staged=True, is_completed=False):
        # Commit this update
        new_path = os.path.join(settings.CATALOG_BASE_DIR, 'sem-' + update.semester + '-new')
        old_path = os.path.join(settings.CATALOG_BASE_DIR, 'sem-' + update.semester)

        delta = cp.make_delta(new_path, old_path)
        cp.commit_delta(new_path, old_path, os.path.join(settings.CATALOG_BASE_DIR, deltas_directory), delta)

        update.is_completed = True
        update.save()
        print("Successfully deployed {}".format(update))

def update_catalog_with_file(path, semester):
    """Updates the catalog database using the given CSV file path."""
    with open(path, 'r') as file:
        reader = csv.reader(file)
        headers = None
        for comps in reader:
            if CourseAttribute.subjectID in comps:
                headers = comps
                continue
            if headers is None:
                print("Can't read CSV file {} - no headers".format(path))
            info = dict(zip(headers, comps))
            try:
                course = Course.public_courses().get(subject_id=info[CourseAttribute.subjectID])
            except ObjectDoesNotExist:
                course = Course.objects.create(public=True, subject_id=info[CourseAttribute.subjectID])
            finally:
                course.catalog_semester = semester
                for key, val in info.items():
                    if key not in CSV_HEADERS: continue
                    prop, converter = CSV_HEADERS[key]
                    setattr(course, prop, converter(val.decode('utf-8')))
                course.save()

def parse_related_file(path):
    """Updates the catalog database with the related subjects file."""
    with open(path, 'r') as file:
        for line in file:
            comps = line.strip().replace("[J]", "").replace("J", "").split(",")
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

    related_path = None
    for path in catalog_files:
        filename = os.path.basename(path)
        if any(f in filename for f in EXCLUDED_FILENAMES): continue
        print(filename)
        if "related" in filename:
            # Save this for last
            related_path = path
        else:
            update_catalog_with_file(os.path.join(settings.CATALOG_BASE_DIR, path), semester)
    if related_path is not None:
        parse_related_file(os.path.join(settings.CATALOG_BASE_DIR, related_path))

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

def perform_requirement_deployments():
    """Performs any pending deployments of updated requirements files."""

    delta = set()

    for deployment in Deployment.objects.filter(date_executed=None).order_by('pk'):
        print(deployment)
        try:
            for edit_req in deployment.edit_requests.all().order_by('pk'):
                if len(edit_req.contents) == 0:
                    print("Edit request {} has no contents, skipping".format(edit_req))
                    continue

                with open(os.path.join(settings.CATALOG_BASE_DIR, requirements_dir, edit_req.list_id + ".reql"), 'w') as file:
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
        write_delta_file(sorted(delta), os.path.join(settings.CATALOG_BASE_DIR, "deltas", requirements_dir))

def perform_syllabus_deployments():
    """Performs any pending deployments of updated syllabi"""

    for deployment in SyllabusDeployment.objects.filter(date_executed=None).order_by('pk'):
        print(deployment)
        try:
            for syllabus_submission in deployment.syllabus_submissions.all().order_by('pk'):
                syllabus = Syllabus.objects.create(
                    semester = syllabus_submission.semester,
                    year = syllabus_submission.year,
                    subject_id = syllabus_submission.subject_id,
                    file = syllabus_submission.file,
                    timestamp = syllabus_submission.timestamp
                )

                syllabus.save()

            deployment.date_executed = timezone.now()
            deployment.save()
        except:
            print(traceback.format_exc())

def update_requirements():
    """Parses the current set of requirements and adds them to the database."""
    RequirementsList.objects.all().delete()
    RequirementsStatement.objects.all().delete()

    req_urls = compute_semester_delta(list_semesters()[-1].split('-'), 0, 0)
    for path_name in req_urls[REQUIREMENTS_INFO_KEY]:
        print(path_name)
        new_req = RequirementsList.objects.create(list_id=os.path.basename(path_name))
        with open(os.path.join(settings.CATALOG_BASE_DIR, path_name), 'rb') as file:
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
            message += unicode(req).encode("utf-8") + "\n"
        message += "\n"
    return message

### ANALYTICS

def log_analytics_summary(output_path, num_hours=26):
    """Logs basic summary statistics over the past num_hours hours."""
    if not os.path.exists(output_path):
        with open(output_path, "w") as file:
            file.write("UTC Time\tTotal Requests\tLogged-in Requests\tStudents\tUser Agents\n")

    # Count up total summary statistics over the past num_hours hours
    out_file = open(output_path, "a")
    for offset in reversed(range(1, 25)):
        early_time = timezone.now() - timezone.timedelta(hours=offset)
        early_time = early_time.replace(minute=0)
        late_time = timezone.now() - timezone.timedelta(hours=offset - 1)
        late_time = late_time.replace(minute=0)

        requests = RequestCount.objects.filter(timestamp__range=(early_time, late_time))
        total_count = requests.count()
        logged_in_count = requests.filter(is_authenticated=True).count()
        with_student_requests = requests.filter(student_unique_id__isnull=False)
        student_count = with_student_requests.values("student_unique_id").distinct().count()
        user_agent_count = requests.values("user_agent").distinct().count()
        out_file.write("{}\t{}\t{}\t{}\t{}\n".format(
            timezone.localtime(early_time).strftime("%m/%d/%Y %H:%M"),
            total_count, logged_in_count, student_count, user_agent_count
        ))
    out_file.close()

### BACKUPS

def document_contents_differ(old, new, threshold=20):
    """Returns whether the two document contents differ sufficiently to merit a new backup."""
    # In both the road and schedule file formats, the significant differences would occur in the
    # second level of the JSON object.
    if old == new:
        return False

    try:
        old_json = json.loads(old)
        new_json = json.loads(new)
    except:
        return True
    else:
        old_keys = set(old_json.keys())
        new_keys = set(new_json.keys())
        if old_keys != new_keys:
            return True

        for key in old_keys:
            old_elem = old_json[key]
            new_elem = new_json[key]
            if not isinstance(old_elem, list) or not isinstance(new_elem, list):
                continue

            # Compare the membership
            old_values = set(json.dumps(elem) for elem in old_elem)
            new_values = set(json.dumps(elem) for elem in new_elem)
            if max(len(old_values - new_values), len(new_values - old_values)) >= 2:
                return True
        return False

def save_backups_by_doc_type(doc_type, backup_type):
    """Saves backups for the given document class and backup class (e.g. Road and RoadBackup)."""
    num_new_backups = 0
    num_diff_backups = 0
    if backup_type.objects.all().count() > 0:
        yesterday = timezone.now() - timezone.timedelta(days=1)
        docs_to_check = doc_type.objects.filter(modified_date__gte=yesterday)
        print("Checking documents from {} to {}".format(yesterday, timezone.now()))
    else:
        print("Checking all documents")
        docs_to_check = doc_type.objects.all()
    for document in docs_to_check.iterator():
        # Check for backups
        try:
            latest_backup = backup_type.objects.filter(document=document).latest('timestamp')
        except ObjectDoesNotExist:
            # Create the backup
            new_backup = backup_type(document=document, timestamp=document.modified_date,
                                     name=document.name, last_agent=document.last_agent,
                                     contents=document.contents)
            new_backup.save()
            num_new_backups += 1
        else:
            # Check for differences between the current version and the backup
            if document_contents_differ(latest_backup.contents, document.contents):
                new_backup = backup_type(document=document, timestamp=document.modified_date,
                                         name=document.name, last_agent=document.last_agent,
                                         contents=document.contents)
                new_backup.save()
                num_diff_backups += 1
    print("{} backups created for new documents, {} for old documents".format(
            num_new_backups, num_diff_backups))

def save_backups():
    """Saves backups for any roads that don't have a backup yet or are significantly different
    from their last backup."""
    save_backups_by_doc_type(Road, RoadBackup)
    save_backups_by_doc_type(Schedule, ScheduleBackup)

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
        save_backups()
    except:
        message += "Saving backups:\n"
        message += traceback.format_exc()

    try:
        message += check_for_edits()
    except:
        message += "Checking for edits failed:\n"
        message += traceback.format_exc()

    try:
        perform_requirement_deployments()
    except:
        message += "Error performing requirements deployment:\n"
        message += traceback.format_exc()

    try:
        update_requirements()
    except:
        message += "Updating requirements DB failed:\n"
        message += traceback.format_exc()

    try:
        perform_syllabus_deployments()
    except:
        message += "Error performing syllabus deployment:\n"
        message += traceback.format_exc()

    try:
        deploy_catalog_updates()
    except:
        message += "Deploying catalog updates failed:\n"
        message += traceback.format_exc()

    try:
        update_catalog()
    except:
        message += "Updating catalog DB failed:\n"
        message += traceback.format_exc()

    if len(sys.argv) > 1:
        try:
            log_analytics_summary(sys.argv[1])
        except:
            message += "Logging analytics failed:\n"
            message += traceback.format_exc()

    if len(message) > 0 and len(sys.argv) > 2:
        email_results(message.decode("utf-8"), sys.argv[2:])
    print(message)
