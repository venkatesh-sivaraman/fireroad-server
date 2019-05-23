"""
This module relies on API credentials provided in the api_creds.txt file in this
directory. They should be of the form:
CLIENT_ID
CLIENT_SECRET

Without these credentials, the parser will not contribute any information.
"""

import json
import os
import requests
from utils.catalog_constants import *

BASE_URL = "https://mit-course-catalog-v2.cloudhub.io/coursecatalog/v2/terms/"
API_CREDS_PATH = os.path.join(os.path.dirname(__file__), "api_creds.txt")

if os.path.exists(API_CREDS_PATH):
    with open(API_CREDS_PATH, "r") as file:
        CLIENT_ID, CLIENT_SECRET = (line.strip() for line in file if len(line.strip()))
else:
    CLIENT_ID = None
    CLIENT_SECRET = None

    SHOWED_WARNING = False

class APIConstants:
    subject_id = "subjectId"
    title = "title"
    description = "description"

SEASONS = {'fall': 'FA', 'spring': 'SP'}

def semester_to_term_code(semester):
    """
    Returns a term code for the given semester name. For example, fall-2019 => 2019FA.
    """
    season, year = semester.split('-')
    assert season in SEASONS, "invalid season {}".format(season)
    return year + SEASONS[season]

def parse_from_api(semester, department, courses):
    """
    Extracts course information for the given department using the MIT developer
    API, and adds it to the appropriate courses.

    semester: the current semester name (e.g. fall-2019)
    department: a department code to read from the API
    courses: a dictionary of subject ID to course info dictionaries
    """

    if CLIENT_ID is None or CLIENT_SECRET is None:
        global SHOWED_WARNING
        if not SHOWED_WARNING:
            print("WARNING: no client ID or client secret provided for the MIT developer API.")
            SHOWED_WARNING = True
        return

    r = requests.get(BASE_URL + semester_to_term_code(semester) + "/subjects?dept={}".format(department), headers={'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET})
    if r.status_code != 200:
        print("MIT developer API request failed:", r.text)
        return

    results = json.loads(r.text).get('items', [])
    for result in results:
        subject_id = result.get(APIConstants.subject_id, '')
        if not len(subject_id) or subject_id not in courses: continue

        course = courses[subject_id]
        if APIConstants.title in result:
            if result[APIConstants.title] != course.get(CourseAttribute.title, ''):
                print("Changed title for", subject_id, "from", course.get(CourseAttribute.title, ''), "to", result[APIConstants.title])
            course[CourseAttribute.title] = result[APIConstants.title]
        if APIConstants.description in result:
            course[CourseAttribute.description] = result[APIConstants.description]
