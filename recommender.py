import numpy as np
import sys
import django
import scipy.sparse
from sklearn.ensemble import RandomForestRegressor
from scipy.spatial.distance import cosine
import json
import os
import time
import csv
import re
os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
django.setup()
from recommend.models import Rating, Recommendation, Road, DEFAULT_RECOMMENDATION_TYPE
from django.contrib.auth.models import User
from django.db import DatabaseError, transaction
from django import db

max_rating = 5

"""
Patterns which, if the subject ID matches, will be excluded from recommendations.
"""
EXCLUDED_PATTERNS = [
    r'\.S'
]

equiv_subject_keys = [
    "Equivalent Subjects",
    "Joint Subjects",
    "Meets With Subjects"
]

ROAD_SELECTED_SUBJECTS_KEY = u"selectedSubjects"
ROAD_SUBJECT_ID_KEY = u"id"
ROAD_SEMESTER_KEY = u"semester"
ROAD_COURSES_KEY = u"coursesOfStudy"

### Building input data

def generate_subject_features(features_path):
    """
    Reads the features.txt file that comes generated from the catalog data
    scrubber tool, and produces a dictionary that keys subject IDs to sparse
    matrices that describe each subject.
    """
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

def read_condensed_courses(source):
    """
    Reads a courses text file for information relevant to course recommendation.
    """
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

def get_rating_data():
    """
    Returns a dictionary where each element keyed by username corresponds to
    a list of (subject, rating) pairs.
    """
    input_data = {}
    for entry in Rating.objects.all():
        if entry.value is None or entry.subject_id is None or entry.user is None:
            continue
        try:
            if entry.user.student is None: continue
        except:
            continue

        if entry.user.username not in input_data:
            input_data[entry.user.username] = {}

        input_data[entry.user.username][entry.subject_id] = entry.value

    return input_data

def get_road_data():
    """
    Returns a dictionary where each element corresponds to a user (keyed by
    username) and contains two items: 1) a dictionary mapping
    courses to sets of semester numbers, and 2) a dictionary mapping semester
    numbers to sets of courses. Also returns a dictionary of usernames to sets of
    courses of study that each user has selected.
    """
    road_data = {}
    courses_of_study = {}
    for road in Road.objects.all():
        try:
            if road.user is None or road.user.student is None: continue
        except:
            continue

        try:
            contents = json.loads(Road.expand_road(road.contents))
            if road.user.username not in road_data:
                road_data[road.user.username] = ({}, {})

            selected_subjs = contents[ROAD_SELECTED_SUBJECTS_KEY]
            course_to_sem, sem_to_course = road_data[road.user.username]
            for subj in selected_subjs:
                if subj[ROAD_SUBJECT_ID_KEY] not in course_to_sem:
                    course_to_sem[subj[ROAD_SUBJECT_ID_KEY]] = set()
                course_to_sem[subj[ROAD_SUBJECT_ID_KEY]].add(subj[ROAD_SEMESTER_KEY])

                if subj[ROAD_SEMESTER_KEY] not in sem_to_course:
                    sem_to_course[subj[ROAD_SEMESTER_KEY]] = set()
                sem_to_course[subj[ROAD_SEMESTER_KEY]].add(subj[ROAD_SUBJECT_ID_KEY])

            if road.user.username not in courses_of_study:
                courses_of_study[road.user.username] = set()
            courses_of_study[road.user.username] |= set(contents[ROAD_COURSES_KEY])
        except:
            continue
    return road_data, courses_of_study

### Characterize user preferences

class UserRecommenderProfile(object):
    """
    Describes a user in the recommender system. Should be used to store any
    information that can be used to provide recommendations, such as the user's
    current semester, courses of study, saved roads, and eventually schedules and
    favorites.
    """
    def __init__(self, username, ratings, roads, courses_of_study, semester):
        self.username = username
        self.ratings = ratings
        self.roads = roads
        self.courses_of_study = courses_of_study
        self.semester = semester

    def compute_regression_predictions(self, subject_arrays, all_subject_features):
        """
        Computes regression predictions by running a random forest regressor
        on the (subject, rating) pairs stored in self.ratings. Once finished, sets
        the value of self.regression_predictions to a numpy array of predicted
        ratings for every course, in the order specified by all_subject_features.
        subject_arrays should be a dictionary or set keyed by subject IDs;
        all_subject_features should be a matrix of subject features where each
        row is a subject.
        """
        ratings_keys = sorted(self.ratings.keys())
        X = scipy.sparse.vstack([subject_arrays[subj] for subj in ratings_keys if subj in subject_arrays])
        Y = np.array([self.ratings[subj] for subj in ratings_keys if subj in subject_arrays])

        model = RandomForestRegressor()
        model.fit(X, Y)
        self.regression_predictions = model.predict(all_subject_features)

    @staticmethod
    def build(username, subject_arrays, all_subject_features, ratings, roads, courses_of_study, semester):
        """Builds a UserRecommenderProfile object."""
        profile = UserRecommenderProfile(username, ratings, roads, courses_of_study, semester)
        profile.compute_regression_predictions(subject_arrays, all_subject_features)
        return profile

### Helpers

class RankList(object):
    """
    Stores a list of ranked quantities and allows the top n values to be
    computed without sorting a list. Only the top n objects are stored at any
    given time, where n is the capacity of the RankList.
    """

    def __init__(self, capacity, maximize=True):
        self.list = [(None, -9999999 * (1 if maximize else -1)) for i in range(capacity)]
        self.maximize = maximize

    def update(self, iterable):
        for i in iterable:
            self.add(*i)

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
        """Returns the objects without their corresponding numerical values."""
        return [x[0] for x in self.list if x[0] is not None]

    def items(self):
        """Returns the objects in tuples with their corresponding numerical values."""
        return [x for x in self.list if x[0] is not None]

def subject_already_taken(subject, profile, course_data=None):
    """Determines whether the given subject (or one of its equivalent subjects)
    is already present in the user profile."""
    for other_subject in list(profile.roads[0].keys()) + list(profile.ratings.keys()):
        if other_subject == subject:
            return True
        if course_data is None or other_subject not in course_data: continue
        for key in equiv_subject_keys:
            if key not in course_data[other_subject]: continue
            if subject in course_data[other_subject][key]:
                return True
    return False

def user_similarities(profiles):
    """Returns an nxn matrix, where n is the number of profiles, indicating the
    similarity between each pair of users."""
    # Assemble pairwise user similarities
    similarities = np.zeros((len(profiles), len(profiles)))
    for i, prof1 in enumerate(profiles):
        for j, prof2 in enumerate(profiles):
            val = (1.0 - cosine(prof1.regression_predictions, prof2.regression_predictions)) ** 4
            if val > BASIC_RATING_SIMILARITY_CUTOFF:
                similarities[i, j] = val
    return similarities

### Recommender Engines

REC_MIN_COUNT = 5 # Minimum number of recommendations required to save
BASIC_RATING_SIMILARITY_CUTOFF = 0.7
BASIC_RATING_REC_COUNT = 15

def basic_rating_predictor(profiles, subject_ids, course_data=None):
    """
    Takes a list of user profile objects and a list of subject IDs (same order
    as used to build the regression predictions), computes the similarities
    between each user's results, and then determines a set of courses that would
    be most highly ranked by that user, incorporating social reinforcement.
    """

    similarities = user_similarities(profiles)

    # Build course semester distributions
    course_distributions = {} # Keys are subject IDs, values are dictionaries {semester: count}
    for prof in profiles:
        for subj, semesters in prof.roads[0].items():
            if subj not in course_distributions:
                course_distributions[subj] = {}
            for sem in semesters:
                if sem not in course_distributions[subj]:
                    course_distributions[subj][sem] = 0
                course_distributions[subj][sem] += 1

    # Determine overall predicted rating for each user
    all_user_ratings = np.vstack([user.regression_predictions for user in profiles])
    for i, profile in enumerate(profiles):
        social_ratings = np.dot(similarities[i], all_user_ratings)
        top_ratings = RankList(BASIC_RATING_REC_COUNT)
        for subject, rating in zip(subject_ids, social_ratings):
            if subject_already_taken(subject, profile, course_data): continue

            # Now weight rating by frequency in current semester
            if subject in course_distributions and profile.semester in course_distributions[subject]:
                rating *= course_distributions[subject][profile.semester] / sum(course_distributions[subject].values())
            else:
                rating *= 0.5
            top_ratings.add(subject, rating)

        subject_items = {subj: float("{:.2f}".format(rating)) for subj, rating in top_ratings.items()}
        if len(subject_items) < REC_MIN_COUNT:
            continue
        yield Recommendation(user=User.objects.get(username=profile.username), rec_type=DEFAULT_RECOMMENDATION_TYPE, subjects=json.dumps(subject_items))

BY_MAJOR_USER_CUTOFF = 20 # With at least this many users, recommendations may be generated
BY_MAJOR_REC_COUNT = 10 # Number of recommendations to generate
BY_MAJOR_FREQ_CUTOFF = 10 # Number of occurrences of subject required to consider part of major/minor
SEMESTER_DISTANCE_COEFFICIENT = 0.05

def by_major_predictor(profiles, subject_ids, course_data=None):
    """Generates recommendations for people with the same major."""

    # Build a list of majors/minors
    all_courses_of_study = set()
    for profile in profiles:
        all_courses_of_study |= profile.courses_of_study

    # Find common courses
    for course in all_courses_of_study:
        applicable_users = [p for p in profiles if course in p.courses_of_study]
        if len(applicable_users) < BY_MAJOR_USER_CUTOFF: continue

        print("Generating recommendations for {}...".format(course))

        course_distributions = {} # Keys are subject IDs, values are dictionaries {semester: count}
        for prof in applicable_users:
            for subj, semesters in prof.roads[0].items():
                if subj not in course_distributions:
                    course_distributions[subj] = {}
                for sem in semesters:
                    if sem not in course_distributions[subj]:
                        course_distributions[subj][sem] = 0
                    course_distributions[subj][sem] += 1
        avg_ratings = {subj: sum(prof.regression_predictions[subject_ids[subj]] for prof in applicable_users) / len(applicable_users) for subj in course_distributions if subj in subject_ids}

        # For each applicable user, generate a rank list by degree of
        # commonness and proximity with the user's current semester
        for prof in applicable_users:
            recs = RankList(BY_MAJOR_REC_COUNT)
            for subj in course_distributions:
                if sum(course_distributions[subj].values()) < BY_MAJOR_FREQ_CUTOFF:
                    continue
                if (subj in prof.ratings and prof.ratings[subj] < 1.0) or subject_already_taken(subj, prof, course_data): continue
                relevance = sum((1.0 - abs(sem - prof.semester) * SEMESTER_DISTANCE_COEFFICIENT) * freq for sem, freq in course_distributions[subj].items()) * avg_ratings.get(subj, -99999)
                recs.add(subj, relevance)

            subject_items = {subj: float("{:.2f}".format(rating)) for subj, rating in recs.items()}
            if len(subject_items) < REC_MIN_COUNT:
                continue
            yield Recommendation(user=User.objects.get(username=prof.username), rec_type="course:" + course, subjects=json.dumps(subject_items))

RELATED_SUBJECTS_FREQ_CUTOFF = 0.5 # Required proportion of applicable users that must have this subject

def related_subjects_predictor(profiles, subject_ids, course_data=None):
    """Generates recommendations for users who have taken a given course."""

    covered_subjects = set()

    for subject_id in subject_ids:
        # See which users have taken this course
        applicable_users = [p for p in profiles if subject_id in p.roads[0]]
        if len(applicable_users) < BY_MAJOR_USER_CUTOFF: continue

        course_distributions = {} # Keys are subject IDs, values are dictionaries {semester: count}
        for prof in applicable_users:
            for subj, semesters in prof.roads[0].items():
                if subj == subject_id: continue
                if subj not in course_distributions:
                    course_distributions[subj] = {}
                for sem in semesters:
                    if sem not in course_distributions[subj]:
                        course_distributions[subj][sem] = 0
                    course_distributions[subj][sem] += 1

        course_totals = {subj: sum(freqs.values()) / len(applicable_users) for subj, freqs in course_distributions.items() if subj not in covered_subjects}
        if len(course_totals) < BY_MAJOR_REC_COUNT:
            continue

        avg_ratings = {subj: sum(prof.regression_predictions[subject_ids[subj]] for prof in applicable_users) / len(applicable_users) for subj in course_distributions if subj in subject_ids}

        covered_subjects |= set(subj for subj, prop in course_totals.items() if prop < RELATED_SUBJECTS_FREQ_CUTOFF)

        print("Generating recommendations for {} ({} related courses)...".format(subject_id, len(course_totals)))

        # For each applicable user, generate a rank list by degree of
        # commonness and proximity with the user's current semester
        for prof in applicable_users:
            recs = RankList(BY_MAJOR_REC_COUNT)
            for subj in course_totals:
                if course_totals[subj] < RELATED_SUBJECTS_FREQ_CUTOFF:
                    continue
                if (subj in prof.ratings and prof.ratings[subj] < 1.0) or subject_already_taken(subj, prof, course_data):
                    continue
                relevance = sum((1.0 - abs(sem - prof.semester) * SEMESTER_DISTANCE_COEFFICIENT) * freq for sem, freq in course_distributions[subj].items()) * avg_ratings.get(subj, -99999)
                recs.add(subj, relevance)

            subject_items = {subj: float("{:.2f}".format(rating)) for subj, rating in recs.items()}
            if len(subject_items) < REC_MIN_COUNT:
                continue
            yield Recommendation(user=User.objects.get(username=prof.username), rec_type="subject:" + subject_id, subjects=json.dumps(subject_items))

"""
Functions that take as parameters a list of user profiles, a dictionary of subject
IDs to positions in the regression prediction vectors, and a course data
dictionary. Should yield Recommendation objects that can be saved into the database.
"""
RECOMMENDERS = [basic_rating_predictor, by_major_predictor, related_subjects_predictor]

### Save recommendations

def store_recommendation(rec):
    """Saves the given Recommendation object to the database."""
    existing = Recommendation.objects.filter(user=rec.user, rec_type=rec.rec_type)
    if existing.count() == 1:
        first = existing.first()
        first.subjects = rec.subjects
        first.save()
    else:
        if existing.count() > 1:
            Recommendation.objects.filter(user=rec.user, rec_type=rec.rec_type).delete()
        rec.save()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Not enough arguments.")
    else:
        features_path = sys.argv[1]
        subject_arrays = generate_subject_features(features_path)

        if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
            condensed_path = sys.argv[2]
            course_data = read_condensed_courses(condensed_path)
        else:
            course_data = None

        # Get rating and road information
        rating_data = get_rating_data()
        road_data, majors_data = get_road_data()
        all_user_ids = set(rating_data.keys()) & set(road_data.keys())
        if len(sys.argv) > 3 and sys.argv[3] == '-v':
            for user_id in all_user_ids:
                print(user_id + ":")
                if user_id in rating_data:
                    print(rating_data[user_id])
                if user_id in road_data:
                    print(road_data[user_id])
                if user_id in majors_data:
                    print(majors_data[user_id])

        # Close the connection because computation will take a while
        db.close_connection()

        # Build user profiles
        subject_ids = sorted(subject_arrays.keys())
        subject_id_dict = dict(zip(subject_ids, range(len(subject_ids))))
        X_test = scipy.sparse.vstack([subject_arrays[id] for id in subject_ids])
        profiles = [UserRecommenderProfile.build(user_id,
                                                 subject_arrays,
                                                 X_test,
                                                 rating_data.get(user_id, {}),
                                                 road_data.get(user_id, ({}, {})),
                                                 majors_data.get(user_id, set()),
                                                 int(User.objects.get(username=user_id).student.current_semester)) for user_id in all_user_ids]

        # Clear recommendations
        for prof in profiles:
            Recommendation.objects.filter(user=User.objects.get(username=prof.username)).delete()

        # Run various recommenders
        for recommender in RECOMMENDERS:
            for rec in recommender(profiles, subject_id_dict, course_data):
                if rec is None: continue
                store_recommendation(rec)
