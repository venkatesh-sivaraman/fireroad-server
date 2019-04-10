import numpy as np
import sys
import django
import scipy.sparse
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.linear_model import LinearRegression, Ridge, LogisticRegression, RidgeClassifier
from scipy.spatial.distance import cosine
import json
import os
import time
import csv
import re
import random
os.environ['DJANGO_SETTINGS_MODULE'] = "fireroad.settings"
django.setup()
from recommend.models import Rating, Recommendation, DEFAULT_RECOMMENDATION_TYPE
from sync.models import Road
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

# IDs for which to look at a different subject to get equivalence types
special_equiv_subjects = {
    "PHY1": "8.01",
    "PHY2": "8.02",
    "CAL1": "18.01",
    "CAL2": "18.02",
    "BIOL": "7.012",
    "CHEM": "5.111"
}

# Don't generate recommendations for these majors/minors
excluded_courses = { "girs" }

# Don't generate related-subject recommendations for these subjects
excluded_subjects = ["18.01", "18.02", "8.01", "8.02"]

ROAD_SELECTED_SUBJECTS_KEY = u"selectedSubjects"
ROAD_SUBJECT_ID_KEY = u"id"
ROAD_SUBJECT_ID_ALT_KEY = u"subject_id"
ROAD_SEMESTER_KEY = u"semester"
ROAD_COURSES_KEY = u"coursesOfStudy"

keyword_indexes = {}

### Building input data

def get_subject_id(info_dict):
    """Finds the subject ID in the given road subject info dictionary. Returns
    None if no subject ID is present."""
    return info_dict.get(ROAD_SUBJECT_ID_KEY, info_dict.get(ROAD_SUBJECT_ID_ALT_KEY, None))

def generate_subject_features(features_path):
    """
    Reads the features.txt file that comes generated from the catalog data
    scrubber tool, and produces a dictionary that keys subject IDs to sparse
    matrices that describe each subject.
    """
    global keyword_indexes
    subjects = {}
    exclusions = [re.compile(x) for x in EXCLUDED_PATTERNS]
    with open(features_path, 'r') as file:
        for line in file:
            comps = line.strip().split(',')
            if len(comps) == 0: continue
            subject_id = comps[0]
            if next((x for x in exclusions if x.search(subject_id) is not None), None):
                continue
            keyword_set = set()
            if len(comps) >= 2:
                for keyword in comps[1:]:
                    if keyword not in keyword_indexes:
                        keyword_indexes[keyword] = len(keyword_indexes)
                    keyword_set.add(keyword_indexes[keyword])
            subjects[subject_id] = keyword_set

    subject_arrays = {}
    dim = len(keyword_indexes)
    print("Dimension of vectors: 1 by {}".format(dim))
    for subject_id, keywords in subjects.items():
        mat = np.zeros((dim,))
        for k in keywords:
            mat[k] = 1
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
            contents = json.loads(Road.expand(road.contents))
            if road.user.username not in road_data:
                road_data[road.user.username] = ({}, {})

            selected_subjs = contents[ROAD_SELECTED_SUBJECTS_KEY]
            course_to_sem, sem_to_course = road_data[road.user.username]
            for subj in selected_subjs:
                subject_id = get_subject_id(subj)
                if subject_id is None: continue

                if subject_id not in course_to_sem:
                    course_to_sem[subject_id] = set()
                course_to_sem[subject_id].add(subj[ROAD_SEMESTER_KEY])

                if subj[ROAD_SEMESTER_KEY] not in sem_to_course:
                    sem_to_course[subj[ROAD_SEMESTER_KEY]] = set()
                sem_to_course[subj[ROAD_SEMESTER_KEY]].add(subject_id)

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
        self.departments = set(subj[:subj.find('.')] for subj in self.subjects_taken())

    def subjects_taken(self):
        """Returns a list of the subjects taken by this user."""
        return list(self.roads[0].keys()) # + list(self.ratings.keys())

    def filtered_rated_subjects(self):
        """
        Returns a list of ratings that are valid, i.e. non-negative and
        present in the user's road or negative. This is because the app
        automatically assigns ratings that are non-negative, so some of the ratings
        may be spurious and due to courses that were on the user's road in the
        past.
        """
        base = set([subj for subj in sorted(self.ratings.keys()) if subj in subject_arrays])
        taken_subjects = set(self.subjects_taken())
        return list([subj for subj in base if self.ratings[subj] < 0 or subj in taken_subjects])

    def compute_regression_predictions(self, subject_arrays, all_subject_features):
        """
        Computes regression predictions on the (subject, rating) pairs stored in
        self.ratings. Once finished, sets the value of self.regression_predictions
        to a numpy array of predicted ratings for every course, in the order
        specified by all_subject_features. subject_arrays should be a dictionary
        of feature vectors keyed by subject IDs; all_subject_features should be
        a matrix of the same subject features where each row is a subject (in a
        pre-specified order).
        """
        ratings_keys = self.filtered_rated_subjects()

        if len(ratings_keys) == 0:
            self.regression_predictions = np.zeros(all_subject_features.shape[0])
            return
        X = np.vstack([subject_arrays[subj] for subj in ratings_keys for i in range(abs(int(self.ratings[subj])))])
        Y = np.array([self.ratings[subj] for subj in ratings_keys for i in range(abs(int(self.ratings[subj])))])

        model = Ridge(alpha=0.75) #RidgeClassifier() #Ridge(alpha=0.75) #RandomForestRegressor()
        model.fit(X, Y)
        self.regression_predictions = model.predict(all_subject_features)
        # For debugging (in Jupyter)
        # self.X = X
        # self.coefficients = (model.coef_, model.intercept_)

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

    def replace(self, object, new_object):
        """Replaces an equivalent object with another object."""
        idx = next((i for i in range(len(self.list)) if self.list[i][0] == object), None)
        if idx is None:
            print("Didn't find {} in rank list.".format(object))
        self.list[idx] = (new_object, self.list[idx][1])

    def __contains__(self, object):
        return next((x for x in self.list if x[0] == object), None) is not None

    def objects(self):
        """Returns the objects without their corresponding numerical values."""
        return [x[0] for x in self.list if x[0] is not None]

    def items(self):
        """Returns the objects in tuples with their corresponding numerical values."""
        return [x for x in self.list if x[0] is not None]

def subject_in_list(subject, subject_list, course_data=None):
    """Determines whether the given subject (or one of its equivalent subjects)
    is already present in the given subject list."""
    if subject in special_equiv_subjects:
        subject = special_equiv_subjects[subject]
    for other_subject in subject_list:
        if other_subject in special_equiv_subjects:
            other_subject = special_equiv_subjects[other_subject]
        if other_subject == subject:
            return other_subject
        if course_data is None or other_subject not in course_data: continue
        for key in equiv_subject_keys:
            if key not in course_data[other_subject]: continue
            if subject in course_data[other_subject][key]:
                return other_subject
    return None

def user_similarities(profiles):
    """Returns an nxn matrix, where n is the number of profiles, indicating the
    similarity between each pair of users."""
    # Assemble pairwise user similarities
    similarities = np.zeros((len(profiles), len(profiles)))
    for i, prof1 in enumerate(profiles):
        my_sims = np.zeros((len(profiles),))
        for j, prof2 in enumerate(profiles):
            val = (1.0 - cosine(prof1.regression_predictions, prof2.regression_predictions)) ** 4
            val *= 1.0 - (np.tanh(abs(prof1.semester - prof2.semester) / 4.0) ** 2)
            if i == j:
                val = 0.0
            my_sims[j] = val

        normalizer = (1.0 - SELF_PROPORTION) / np.sum(my_sims)
        for j, prof2 in enumerate(profiles):
            # Weight by similarity of semester
            if i == j:
                val = SELF_PROPORTION
            else:
                val = my_sims[j] * normalizer
            similarities[i, j] = val
    return similarities

def update_by_equivalent_subjects(subject, rank_list, profile, course_data):
    """Checks for equivalent subjects in the given rank list, and replaces it if
    this subject is more closely related to the given profile than the existing
    one. Returns True if the subject was existing, and False if not."""
    existing = subject_in_list(subject, rank_list.objects(), course_data)
    if not existing:
        return False
    if subject[:subject.find('.')] in profile.departments:
        rank_list.replace(existing, subject)
    return True

def random_perturbation(value):
    """Randomly adjusts the given float value."""
    return value * random.uniform(1.0 - RANDOM_PERTURBATION, 1.0 + RANDOM_PERTURBATION)

### Recommender Engines

SELF_PROPORTION = 0.6 # Self recommendations are worth this proportion of total normalized weight
REC_MIN_COUNT = 5 # Minimum number of recommendations required to save
BASIC_RATING_SIMILARITY_CUTOFF = 0.4
BASIC_RATING_REC_COUNT = 15
RANDOM_PERTURBATION = 0.05   # Multiply by a random value from (1-x) to (1+x)

def basic_rating_predictor(profiles, subject_ids, subject_id_dict, course_data=None):
    """
    Takes a list of user profile objects and a list of subject IDs (same order
    as used to build the regression predictions), computes the similarities
    between each user's results, and then determines a set of courses that would
    be most highly ranked by that user, incorporating social reinforcement.
    """

    profiles = [p for p in profiles if len(p.filtered_rated_subjects()) > 0]
    print("{} users with available rated subjects".format(len(profiles)))
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
            if subject_in_list(subject, profile.subjects_taken(), course_data): continue
            if update_by_equivalent_subjects(subject, top_ratings, profile, course_data): continue

            # Now weight rating by frequency in current semester
            if subject in course_distributions and profile.semester in course_distributions[subject]:
               num_occurrences = float(sum(course_distributions[subject].values()))
               rating *= 0.25 + float(course_distributions[subject][profile.semester]) / num_occurrences

            # Random salt
            rating = random_perturbation(rating)

            top_ratings.add(subject, rating)

        subject_items = {subj: float("{:.2f}".format(rating)) for subj, rating in top_ratings.items()}
        if len(subject_items) < REC_MIN_COUNT:
            continue
        yield Recommendation(user=User.objects.get(username=profile.username), rec_type=DEFAULT_RECOMMENDATION_TYPE, subjects=json.dumps(subject_items))

BY_MAJOR_USER_CUTOFF = 10 # With at least this many users, recommendations may be generated
BY_MAJOR_REC_COUNT = 10 # Number of recommendations to generate
BY_MAJOR_FREQ_CUTOFF = 10 # Number of occurrences of subject required to consider part of major/minor
SEMESTER_DISTANCE_COEFFICIENT = 0.05

def by_major_predictor(profiles, subject_ids, subject_id_dict, course_data=None):
    """Generates recommendations for people with the same major."""

    # Build a list of majors/minors
    all_courses_of_study = set()
    for profile in profiles:
        all_courses_of_study |= profile.courses_of_study

    # Find common courses
    for course in all_courses_of_study:
        if course in excluded_courses: continue

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
        avg_ratings = {subj: float(sum(prof.regression_predictions[subject_id_dict[subj]] for prof in applicable_users)) / float(len(applicable_users)) for subj in course_distributions if subj in subject_id_dict}

        # For each applicable user, generate a rank list by degree of
        # commonness and proximity with the user's current semester
        for prof in applicable_users:
            recs = RankList(BY_MAJOR_REC_COUNT)
            for subj in course_distributions:
                if sum(course_distributions[subj].values()) < BY_MAJOR_FREQ_CUTOFF:
                    continue
                if (subj in prof.ratings and prof.ratings[subj] < 1.0) or subject_in_list(subj, prof.subjects_taken(), course_data):
                    continue
                if update_by_equivalent_subjects(subj, recs, prof, course_data):
                    continue
                relevance = sum((1.0 - abs(sem - prof.semester) * SEMESTER_DISTANCE_COEFFICIENT) * freq for sem, freq in course_distributions[subj].items()) * avg_ratings.get(subj, -99999)
                recs.add(subj, relevance)

            subject_items = {subj: float("{:.2f}".format(rating)) for subj, rating in recs.items()}
            if len(subject_items) < REC_MIN_COUNT:
                continue
            yield Recommendation(user=User.objects.get(username=prof.username), rec_type="course:" + course, subjects=json.dumps(subject_items))

RELATED_SUBJECTS_FREQ_CUTOFF = 0.3 # Required proportion of applicable users that must have this subject
NUM_RELATED_SUBJECTS_RECS = 1 # Number of related subjects recommendations to save per user

def related_subjects_predictor(profiles, subject_ids, subject_id_dict, course_data=None):
    """Generates recommendations for users who have taken a given course."""

    covered_subjects = set()

    best_recommendation_per_user = {prof.username: RankList(NUM_RELATED_SUBJECTS_RECS) for prof in profiles}
    for subject_id in subject_ids:
        if subject_in_list(subject_id, excluded_subjects, course_data): continue

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

        course_totals = {subj: float(sum(freqs.values())) / float(len(applicable_users)) for subj, freqs in course_distributions.items() if subj not in covered_subjects}
        if len(course_totals) < BY_MAJOR_REC_COUNT:
            continue

        avg_ratings = {subj: sum(prof.regression_predictions[subject_id_dict[subj]] for prof in applicable_users) / len(applicable_users) for subj in course_distributions if subj in subject_id_dict}

        covered_subjects |= set(subj for subj, prop in course_totals.items() if prop >= RELATED_SUBJECTS_FREQ_CUTOFF)

        print("Generating recommendations for {} ({} related courses)...".format(subject_id, len(course_totals)))

        # For each applicable user, generate a rank list by degree of
        # commonness and proximity with the user's current semester
        for prof in applicable_users:
            recs = RankList(BY_MAJOR_REC_COUNT)
            for subj in course_totals:
                if course_totals[subj] < RELATED_SUBJECTS_FREQ_CUTOFF:
                    continue
                if (subj in prof.ratings and prof.ratings[subj] < 1.0) or subject_in_list(subj, prof.subjects_taken(), course_data):
                    continue
                if update_by_equivalent_subjects(subj, recs, prof, course_data):
                    continue
                relevance = sum((1.0 - abs(sem - prof.semester) * SEMESTER_DISTANCE_COEFFICIENT) * freq for sem, freq in course_distributions[subj].items()) * avg_ratings.get(subj, -99999)
                recs.add(subj, relevance)

            subject_items = {subj: float("{:.2f}".format(rating)) for subj, rating in recs.items()}
            if len(subject_items) < REC_MIN_COUNT:
                continue
            rec = Recommendation(user=User.objects.get(username=prof.username), rec_type="subject:" + subject_id, subjects=json.dumps(subject_items))
            best_recommendation_per_user[prof.username].add(rec, random_perturbation(float(sum(subject_items.values())) / float(len(subject_items))))

    for prof, list in best_recommendation_per_user.items():
        if len(list.objects()) > 0:
            for rec in list.objects():
                yield rec

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

        verbose = '-v' in sys.argv
        dev_mode = '--dev' in sys.argv

        # Get rating and road information
        rating_data = get_rating_data()
        road_data, majors_data = get_road_data()
        all_user_ids = set(rating_data.keys()) & set(road_data.keys())
        if verbose:
            for user_id in all_user_ids:
                print(user_id + ":")
                if user_id in rating_data:
                    print(rating_data[user_id])
                if user_id in road_data:
                    print(road_data[user_id])
                if user_id in majors_data:
                    print(majors_data[user_id])

        # Close the connection because computation will take a while
        if django.VERSION[1] >= 10 or django.VERSION[0] >= 2:
            db.connections.close_all()
        else:
            db.close_connection()

        # Build user profiles
        subject_ids = sorted(subject_arrays.keys())
        subject_id_dict = dict(zip(subject_ids, range(len(subject_ids))))
        X_test = np.vstack([subject_arrays[id] for id in subject_ids])
        profiles = [UserRecommenderProfile.build(user_id,
                                                 subject_arrays,
                                                 X_test,
                                                 rating_data.get(user_id, {}),
                                                 road_data.get(user_id, ({}, {})),
                                                 majors_data.get(user_id, set()),
                                                 int(User.objects.get(username=user_id).student.current_semester)) for user_id in all_user_ids]

        # Clear recommendations
        if not dev_mode:
            for prof in profiles:
               Recommendation.objects.filter(user=User.objects.get(username=prof.username)).delete()

        # Run various recommenders
        for recommender in RECOMMENDERS:
            for rec in recommender(profiles, subject_ids, subject_id_dict, course_data):
                if rec is None: continue
                if verbose: print(rec)
                if not dev_mode:
                    store_recommendation(rec)
