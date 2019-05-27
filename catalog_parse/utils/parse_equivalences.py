import json
from .catalog_constants import *

def parse_equivalences(equiv_path, courses):
    """
    Reads equivalences from the given path, and adds them to the "Parent" and
    "Children" attributes of the appropriate courses.

    equiv_path: path to a JSON file containing equivalences, for example:
        [[["6.0001", "6.0002"], "6.00"], ...]
    courses: a dictionary of subject IDs to courses
    """

    with open(equiv_path, 'r') as file:
        equiv_data = json.loads(file.read())

    for equivalence in equiv_data:
        children, parent = equivalence
        for child in children:
            if child not in courses: continue
            courses[child][CourseAttribute.parent] = parent
        if parent in courses:
            courses[parent][CourseAttribute.children] = ','.join(children)
