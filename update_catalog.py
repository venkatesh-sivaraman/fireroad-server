import os
import re
import sys
import shutil
import django
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

from django.conf import settings
from django.core.mail import send_mail
import traceback
from django.core.exceptions import ObjectDoesNotExist
import catalog_parse as cp
from requirements.diff import *
from courseupdater.models import CatalogCorrection
from catalog.models import FIELD_TO_CSV

def email_results(message, recipients):
    """
    Sends an email to the given recipients with the given message. Prints to
    the console if email is not set up.
    """
    if not settings.FR_EMAIL_ENABLED:
        print("Email not configured. Message:")
        print(message)
        return

    email_from = "FireRoad <{}>".format(settings.EMAIL_HOST_USER)
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

def get_corrections():
    """Gets the corrections from the CatalogCorrection table and formats them
    appropriately."""
    raw_corrections = list(CatalogCorrection.objects.all().values())
    corrections = []
    def format(value):
        if isinstance(value, bool):
            return "Y" if value else None
        return value if value else None

    for corr in raw_corrections:
        new_corr = {}
        for k, v in list(corr.items()):
            if k in FIELD_TO_CSV and k != "offered_this_year" and format(v):
                new_corr[FIELD_TO_CSV[k]] = format(v)
        corrections.append(new_corr)
    return corrections

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

    old_contents = old_file.read()
    new_contents = new_file.read()

    old_lines = old_contents.split('\n')
    new_lines = new_contents.split('\n')

    # Subject ID comes first
    old_headings = old_lines[0].split(",")[1:]
    new_headings = new_lines[0].split(",")[1:]

    old_courses = {line[:line.find(",")]: line for line in old_lines[1:]}
    new_courses = {line[:line.find(",")]: line for line in new_lines[1:]}
    ids = sorted(set(old_courses.keys()) | set(new_courses.keys()))
    wrote_to_file = False
    for i, id in enumerate(ids):
        if i % 100 == 0:
            print((i, "of", len(ids)))
        old_course = old_courses.get(id, "")
        new_course = new_courses.get(id, "")

        if old_course != new_course:
            if abs(len(new_course) - len(old_course)) >= 40:
                diff = delete_insert_diff_line(old_course, new_course)
            else:
                diff = build_diff_line(old_course, new_course, max_delta=40)
            diff_file.write(diff)
            wrote_to_file = True

    if not wrote_to_file:
        diff_file.write("No files changed due to this update.")

    old_file.close()
    new_file.close()
    diff_file.close()

if __name__ == '__main__':
    # update is loaded at the top of the script for efficiency
    try:
        semester = 'sem-' + update.semester
        out_path = os.path.join(settings.CATALOG_BASE_DIR, "raw", semester)
        evaluations_path = os.path.join(settings.CATALOG_BASE_DIR, "evaluations.js")
        if not os.path.exists(evaluations_path):
            print("No evaluations file found - consider adding one (see catalog_parse/utils/parse_evaluations.py).")
            evaluations_path = None
        equivalences_path = os.path.join(settings.CATALOG_BASE_DIR, "equivalences.json")
        if not os.path.exists(equivalences_path):
            print("No equivalences file found - consider adding one (see catalog_parse/utils/parse_equivalences.py).")
            equivalences_path = None

        cp.parse(out_path, evaluations_path, equivalences_path,
                 progress_callback=update_progress,
                 write_virtual_status=update.designate_virtual_status)

        consensus_path = os.path.join(settings.CATALOG_BASE_DIR, semester + "-new")
        if os.path.exists(consensus_path):
            shutil.rmtree(consensus_path)

        # Get corrections and convert from field names to CSV headings
        cp.build_consensus(os.path.join(settings.CATALOG_BASE_DIR, "raw"), consensus_path, corrections=get_corrections())

        # Write a diff so it's easier to visualize changes
        update_progress(95.0, "Finding differences...")
        print("Finding differences...")

        old_path = os.path.join(settings.CATALOG_BASE_DIR, semester, "courses.txt")
        new_path = os.path.join(settings.CATALOG_BASE_DIR, semester + "-new", "courses.txt")
        write_diff(old_path, new_path, os.path.join(settings.CATALOG_BASE_DIR, "diff.txt"))

        # Make delta for informative purposes
        delta = cp.make_delta(consensus_path, os.path.join(settings.CATALOG_BASE_DIR, semester))
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
