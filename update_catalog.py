import os
import re
import django
import csv
from django.core.exceptions import ObjectDoesNotExist

os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
django.setup()

from courseupdater.views import *
from catalog.models import *
from django.db import DatabaseError, transaction
from django import db
from fireroad.settings import CATALOG_BASE_DIR

CATALOG_FILES_INFO_KEY = "delta"

# Filenames that contain these words will be skipped
EXCLUDED_FILENAMES = ["condensed", "courses", "features", "enrollment", "departments"]

def update_with_file(path, semester):
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
                course = Course.objects.get(subject_id=info["Subject Id"])
            except ObjectDoesNotExist:
                course = Course.objects.create(subject_id=info["Subject Id"])
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
                course = Course.objects.get(subject_id=comps[0])
                course.related_subjects = ",".join(comps[1:])
                course.save()
            except ObjectDoesNotExist:
                continue

def update_db():
    Course.objects.all().delete()

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
            update_with_file(os.path.join(CATALOG_BASE_DIR, path), semester)
    if related_path is not None:
        parse_related_file(os.path.join(CATALOG_BASE_DIR, related_path))

if __name__ == '__main__':
    update_db()
