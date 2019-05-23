import re
from .catalog_constants import *
import json
import requests

class EvaluationConstants:
    rating = "rating"
    term = "term"
    in_class_hours = "ic_hours"
    out_of_class_hours = "oc_hours"
    eligible_raters = "eligible"
    responded_raters = "resp"
    iap_term = "IAP"

KEYS_TO_AVERAGE = {
    EvaluationConstants.rating: CourseAttribute.averageRating,
    EvaluationConstants.in_class_hours: CourseAttribute.averageInClassHours,
    EvaluationConstants.out_of_class_hours: CourseAttribute.averageOutOfClassHours,
    EvaluationConstants.eligible_raters: CourseAttribute.enrollment
}

def load_evaluation_data(eval_path):
    """
    Reads evaluation data from the given .js file.
    """

    with open(eval_path, 'r') as file:
        eval_contents = file.read()
    begin_range = eval_contents.find("{")
    end_range = eval_contents.rfind(";")
    return json.loads(eval_contents[begin_range:end_range])

def parse_evaluations(evals, courses):
    """
    Adds attributes to each course based on eval data in the given dictionary.
    """

    for i, course_attribs in enumerate(courses):
        subject_id = course_attribs[CourseAttribute.subjectID]
        if subject_id not in evals:
            continue

        averaging_data = {}
        for term_data in evals[subject_id]:
            # if course is offered fall/spring but an eval is for IAP, ignore
            if EvaluationConstants.iap_term in term_data[EvaluationConstants.term] and (course_attribs.get(CourseAttribute.offeredFall, False) or course_attribs.get(CourseAttribute.offeredSpring, False)):
                continue

            for key in KEYS_TO_AVERAGE:
                if key not in term_data:
                    continue
                value = term_data[key]
                averaging_data.setdefault(key, []).append(value)

        for eval_key, course_key in KEYS_TO_AVERAGE.items():
            if eval_key not in averaging_data: continue
            course_attribs[course_key] = sum(averaging_data[eval_key]) / len(averaging_data[eval_key])
