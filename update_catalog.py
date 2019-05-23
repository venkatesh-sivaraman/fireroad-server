import os
import re
import sys
import shutil
import django
os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
django.setup()

from fireroad.settings import CATALOG_BASE_DIR, FR_EMAIL_ENABLED, EMAIL_HOST_USER
from django.core.mail import send_mail
import traceback
from django.core.exceptions import ObjectDoesNotExist
import catalog_parse as cp
from courseupdater.views import get_current_update
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
    if sys.version_info < (3, 0):
        old_contents = old_contents.decode('utf-8')
        new_contents = new_contents.decode('utf-8')

    diff = build_diff(old_contents, new_contents, max_line_delta=10)
    diff_file.write(diff)
    old_file.close()
    new_file.close()
    diff_file.close()

if __name__ == '__main__':
    update = get_current_update()
    update.is_started = True
    update.save()

    try:
        semester = update.semester
        out_path = os.path.join(CATALOG_BASE_DIR, "raw", semester)
        evaluations_path = os.path.join(CATALOG_BASE_DIR, "evaluations.js")
        cp.parse(out_path, evaluations_path, progress_callback=update_progress)

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
        print("An error occurred while executing the update.")

    update = get_current_update()
    update.progress = 100.0
    update.progress_message = "Done processing."
    update.save()
