import os
import re
import sys
import shutil
import django
os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
django.setup()

from courseupdater.views import get_current_update
if __name__ == '__main__':
    if len(sys.argv) > 1:
        from courseupdater.models import CatalogUpdate
        update = CatalogUpdate(semester=sys.argv[1])
    else:
        update = get_current_update()
    if update is None or update.is_started or update.is_completed:
        exit(0)
    update.is_started = True
    update.save()

from fireroad.settings import CATALOG_BASE_DIR, FR_EMAIL_ENABLED, EMAIL_HOST_USER
from django.core.mail import send_mail
import traceback
from django.core.exceptions import ObjectDoesNotExist
import catalog_parse as cp
from requirements.diff import *

def email_results(message, recipients):
    """
    Sends an email to the given recipients with the given message. Prints to
    the console if email is not set up.
    """
    if not FR_EMAIL_ENABLED:
        print("Email not configured. Message:")
        print(message)
        return

    email_from = "FireRoad <{}>".format(EMAIL_HOST_USER)
    send_mail("Catalog update", message, email_from, recipients)

def update_progress(progress, message):
    update = get_current_update()
    if update is not None:
        update.progress = progress
        update.progress_message = message
        update.save()
    else:
        # The update was canceled
        raise KeyboardInterrupt

def write_diff(old_path, new_path, diff_path):
    if not os.path.exists(old_path):
        with open(diff_path, 'w') as file:
            file.write("<p>This is a new catalog version, so no diff is available.</p>")
        return
    elif not os.path.exists(new_path):
        with open(diff_path, 'w') as file:
            file.write("<p>The new version of the catalog has no files - something might have gone wrong?</p>")
        return

    diff_file = open(diff_path, 'w')
    old_file = open(old_path, 'r')
    new_file = open(new_path, 'r')

    old_contents = old_file.read().decode('utf-8')
    new_contents = new_file.read().decode('utf-8')

    old_courses = {line[:line.find(",")]: line for line in old_contents.split('\n')}
    new_courses = {line[:line.find(",")]: line for line in new_contents.split('\n')}
    ids = sorted(set(old_courses.keys()) | set(new_courses.keys()))
    for i, id in enumerate(ids):
        if i % 100 == 0:
            print(i, "of", len(ids))
        old_course = old_courses.get(id, "")
        new_course = new_courses.get(id, "")

        if old_course != new_course:
            if abs(len(new_course) - len(old_course)) >= 25:
                diff = delete_insert_diff_line(old_course.encode('utf-8'), new_course.encode('utf-8'))
            else:
                diff = build_diff_line(old_course, new_course, max_delta=20).encode('utf-8')
            diff_file.write(diff)

    old_file.close()
    new_file.close()
    diff_file.close()

if __name__ == '__main__':
    # update is loaded at the top of the script for efficiency
    try:
        semester = 'sem-' + update.semester
        out_path = os.path.join(CATALOG_BASE_DIR, "raw", semester)
        evaluations_path = os.path.join(CATALOG_BASE_DIR, "evaluations.js")
        if not os.path.exists(evaluations_path):
            print("No evaluations file found - consider adding one (see catalog_parse/utils/parse_evaluations.py).")
            evaluations_path = None
        equivalences_path = os.path.join(CATALOG_BASE_DIR, "equivalences.json")
        if not os.path.exists(equivalences_path):
            print("No equivalences file found - consider adding one (see catalog_parse/utils/parse_equivalences.py).")
            equivalences_path = None

        cp.parse(out_path, evaluations_path, equivalences_path, progress_callback=update_progress)

        consensus_path = os.path.join(CATALOG_BASE_DIR, semester + "-new")
        if os.path.exists(consensus_path):
            shutil.rmtree(consensus_path)
        cp.build_consensus(os.path.join(CATALOG_BASE_DIR, "raw"), consensus_path)

        # Write a diff so it's easier to visualize changes
        update_progress(95.0, "Finding differences...")
        print("Finding differences...")

        old_path = os.path.join(CATALOG_BASE_DIR, semester, "courses.txt")
        new_path = os.path.join(CATALOG_BASE_DIR, semester + "-new", "courses.txt")
        write_diff(old_path, new_path, os.path.join(CATALOG_BASE_DIR, "diff.txt"))

        # Make delta for informative purposes
        delta = cp.make_delta(consensus_path, os.path.join(CATALOG_BASE_DIR, semester))
        if len(delta) > 0:
            message = "The following {} files changed: ".format(len(delta)) + ", ".join(sorted(delta))
        else:
            message = "No files changed due to the catalog update - no action required."
        if len(sys.argv) > 2:
            email_results(message, sys.argv[2:])
        else:
            print(message)

    except:
        print("An error occurred while executing the update:")
        traceback.print_exc()

    update = get_current_update()
    if update is not None:
        update.progress = 100.0
        update.progress_message = "Done processing."
        update.save()
