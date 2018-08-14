import numpy as np
import sys
import django
import scipy.sparse
from sklearn.linear_model import LinearRegression
from scipy.spatial.distance import cosine
import json
import os
import time
import csv
import re
os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
django.setup()
from recommend.models import Rating, Recommendation, DEFAULT_RECOMMENDATION_TYPE
from django.db import DatabaseError, transaction
from django import db

max_rating = 5

"""
Patterns which, if the subject ID matches, will be excluded from recommendations.
"""
EXCLUDED_PATTERNS = [
    r'\.S'
]

def convert_user_to_input_ratings(user_ratings):
    input_ratings = []
    for i, user in enumerate(user_ratings):
        max_value = max(np.abs(rating) for item, rating in user)
        for item, rating in user:
            input_ratings.append((i, item, rating / max_value * max_rating))
    return input_ratings

### Getting data from SQlite
def get_rating_data(subjects=None, coalesced=True):
    '''subjects should be a dictionary of subject IDs to the indexes that should be
    used in the returned data. If coalesced is True, the method returns (input_ratings,
    user_ids dictionary, subjects dictionary) where input_ratings is a list of
    tuples. If coalesced is False, the method returns input_data instead of input_ratings,
    where input_data is a list of lists and each inner list corresponds to a user. The
    index of each user can be obtained from the value keyed to the user's ID in
    the user_ids dictionary.'''
    input_data = []
    user_ids = {}   # Dictionary of user ID to index in input data
    user_list = []  # List of user IDs indexed equivalently to input data
    if subjects is None:
        subjects = {}   # Dictionary of subject IDs to label in input data
    subject_list = []   # List of subject IDs given their label in input data
    for entry in Rating.objects.all():
        if entry.value is None or entry.subject_id is None or entry.user_id is None: continue
        if coalesced:
            if entry.subject_id not in subjects:
                subj = len(subject_list)
                subjects[entry.subject_id] = subj
                subject_list.append(entry.subject_id)
            else:
                subj = subjects[entry.subject_id]
        else:
            subj = entry.subject_id
        if entry.user_id in user_ids:
            input_data[user_ids[entry.user_id]].append((subj, entry.value))
        else:
            user_ids[entry.user_id] = len(input_data)
            user_list.append(entry.user_id)
            input_data.append([(subj, entry.value)])

    if coalesced:
        input_ratings = convert_user_to_input_ratings(input_data)
        return input_ratings, user_ids, subjects
    else:
        return input_data, user_ids, subjects

### Generating feature vectors
def generate_subject_features(features_path):
    subjects = {}
    department_indexes = {}
    keyword_indexes = {}
    exclusions = [re.compile(x) for x in EXCLUDED_PATTERNS]
    with open(features_path, 'r') as file:
        for line in file:
            comps = line.split(',')
            if len(comps) == 0: continue
            subject_id = comps[0]
            if next((x for x in exclusions if x.search(subject_id) is not None), None):
                continue
            if comps[1] not in department_indexes:
                department_indexes[comps[1]] = len(department_indexes)
            department = department_indexes[comps[1]]
            keyword_set = set()
            if len(comps) >= 3:
                for keyword in comps[2:]:
                    if keyword not in keyword_indexes:
                        keyword_indexes[keyword] = len(keyword_indexes)
                    keyword_set.add(keyword_indexes[keyword])
            subjects[subject_id] = (department, keyword_set)

    subject_arrays = {}
    dim = len(department_indexes) + len(keyword_indexes)
    keywords_start = len(department_indexes)
    print("Dimension of vectors: 1 by {}".format(dim))
    for subject_id, (department, keywords) in subjects.items():
        mat = scipy.sparse.dok_matrix((1, dim))
        mat[0,department] = 1
        for k in keywords:
            mat[0,keywords_start + k] = 1
        subject_arrays[subject_id] = mat
    return subject_arrays

def determine_user_regressions(subject_arrays, input_data):
    ret = []
    for user_data in input_data:
        X = scipy.sparse.vstack([subject_arrays[subj] for subj, value in user_data if subj in subject_arrays])
        Y = np.array([[value for subj, value in user_data if subj in subject_arrays]]).T
        model = LinearRegression(fit_intercept=False)
        model.fit(X, Y)
        ret.append(model.coef_)
    return ret

def similar_users(user_regressions, k=20):
    similars = []
    for i, user in enumerate(user_regressions):
        cosines = [(id, cosine(user, user_2)) for id, user_2 in enumerate(user_regressions)]
        # Remove the user itself
        cosines.sort(key=lambda x: x[1])
        similars.append([item for item in cosines if id != i][:min(len(cosines), k)])
    return similars

class RankList(object):
    def __init__(self, capacity, maximize=True):
        self.list = [(None, -9999999 * (1 if maximize else -1)) for i in range(capacity)]
        self.maximize = maximize

    def add(self, object, value):
        insertion_index = None
        for i, (_, other_value) in enumerate(self.list):
            if (self.maximize and value > other_value) or (not self.maximize and value < other_value):
                insertion_index = i
                break
        if insertion_index is not None:
            self.list.insert(i, (object, value))
            self.list.pop()

    def objects(self):
        return [x[0] for x in self.list]

    def items(self):
        return self.list

equiv_subject_keys = [
    "Equivalent Subjects",
    "Joint Subjects",
    "Meets With Subjects"
]

def subject_already_taken(subject, course_data, user_data):
    for other_subject, _ in user_data:
        if other_subject == subject:
            return True
        if other_subject not in course_data: continue
        for key in equiv_subject_keys:
            if key not in course_data[other_subject]: continue
            if subject in course_data[other_subject][key]:
                return True
    return False

def subject_is_in_set(subject, course_data, other_subjects):
    if subject not in course_data:
        return subject in other_subjects
    for key in equiv_subject_keys:
        if key not in course_data[subject]: continue
        for item in course_data[subject][key]:
            if item in other_subjects:
                return True
    return False


def generate_predicted_experiences(user_regressions, subject_arrays, course_data=None, input_data=None, max_predictions=20):
    '''Pass course_data and input_data to check from the equivalent subjects lists to make sure none
    of the predicted experiences overlap with the previously taken courses.'''
    predicted_data = []
    for i, user in enumerate(user_regressions):
        predictions = RankList(max_predictions)
        for subject, vector in subject_arrays.items():
            if course_data is not None and input_data is not None:
                if subject_already_taken(subject, course_data, input_data[i]):
                    continue
            predicted_rating = vector.dot(user.T).item()
            predictions.add(subject, predicted_rating)
        predicted_data.append([p for p in predictions.items() if p[1] > 0])
    return predicted_data

def store_social_prediction(user_id, predicted_courses, rec_type=DEFAULT_RECOMMENDATION_TYPE):
    existing = Recommendation.objects.filter(user_id=user_id, rec_type=rec_type)
    if existing.count() == 1:
        first = existing.first()
        first.subjects = json.dumps(predicted_courses)
        first.save()
    else:
        if existing.count() > 1:
            Recommendation.objects.filter(user_id=user_id, rec_type=rec_type).delete()
        Recommendation.objects.create(user_id=user_id, rec_type=rec_type, subjects=json.dumps(predicted_courses))

# A system-predicted course will be worth the approval of 25% of the user's neighbors
system_prediction_weight = 0.25

def generate_social_predictions(input_data, predicted_data, user_ids, similars, course_data=None, max_predictions=20):
    '''Pass course_data to check from the equivalent subjects lists to make sure none
    of the predicted experiences overlap with the previously taken courses.'''
    total_preds = 0
    with transaction.atomic():
        for id, user_index in user_ids.items():
            viewed_courses = set()
            for subj, _ in input_data[user_index]:
                viewed_courses.add(subj)

            neighbors = similars[user_index]
            relevances = {}
            system_weight = system_prediction_weight * sum(1.0 - x[1] for x in neighbors)
            for subj, value in predicted_data[user_index]:
                if subj in viewed_courses: continue
                if course_data is not None and (subject_already_taken(subj, course_data, input_data[user_index]) or subject_is_in_set(subj, course_data, relevances)):
                    continue
                if subj in relevances:
                    relevances[subj] += value * system_weight
                else:
                    relevances[subj] = value * system_weight

            # Use similar users' data as well
            for similar_user_idx, distance in neighbors:
                similarity = 1.0 - distance
                for subj, value in input_data[user_index] + predicted_data[user_index]:
                    if subj in viewed_courses: continue
                    if course_data is not None and (subject_already_taken(subj, course_data, input_data[user_index]) or subject_is_in_set(subj, course_data, relevances)):
                        continue
                    if subj in relevances:
                        relevances[subj] += value * similarity
                    else:
                        relevances[subj] = value * similarity

            predictions = RankList(max_predictions)
            for subject, relevance in relevances.items():
                predictions.add(subject, relevance)
            store_social_prediction(id, {subj: (round(value * 2.0) / 2.0) for subj, value in predictions.items()})
            total_preds += len(predictions.items())
    return total_preds

def read_condensed_courses(source):
    keys = {}
    reverse_keys = {}
    courses = {}
    with open(source, "r") as file:
        reader = csv.reader(file, delimiter=',', quotechar='"')
        for line in reader:
            if "Subject Id" in line:
                key_list = line
                for i, comp in enumerate(key_list):
                    keys[comp] = i
                    reverse_keys[i] = comp
            else:
                id = line[keys["Subject Id"]]
                def course_dict_value(key):
                    val = line[keys[key]].replace('[J]', '')
                    if key in equiv_subject_keys:
                        return re.findall(r'[A-z0-9.]+', val)
                    return val
                courses[id] = {key: course_dict_value(key) for key in keys}
    return courses

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Not enough arguments.")
    else:
        features_path = sys.argv[1]
        subjects = generate_subject_features(features_path)
        if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
            condensed_path = sys.argv[2]
            course_data = read_condensed_courses(condensed_path)
        else:
            course_data = None
        input_data, user_ids, _ = get_rating_data(coalesced=False)
        if len(sys.argv) > 3 and sys.argv[3] == '-v':
            for user_id in user_ids:
                print(user_id, input_data[user_ids[user_id]])
        # Close the connection because computation will take a while
        db.close_connection()

        regressions = determine_user_regressions(subjects, input_data)
        similars = similar_users(regressions)
        if len(sys.argv) > 3 and sys.argv[3] == '-v':
            for user_id in user_ids:
                print(user_id, similars[user_ids[user_id]])
        predicted_data = generate_predicted_experiences(regressions, subjects, course_data=course_data, input_data=input_data)
        num_preds = generate_social_predictions(input_data, predicted_data, user_ids, similars, course_data=course_data)
        print("Successfully generated {} predictions for {} users.".format(num_preds, len(user_ids)))
