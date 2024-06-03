from .reqlist import *
import random
from catalog.models import Course
from functools import reduce

def ceiling_thresh(progress, maximum):
    """Creates a progress object
    Ensures that 0 < progress < maximum"""

    effective_progress = max(0, progress)

    if maximum > 0:
        return Progress(min(effective_progress, maximum), maximum)
    else:
        return Progress(effective_progress, maximum)


def total_units(courses):
    """Finds the total units in a list of Course objects"""
    total = 0
    for course in courses:
        total += course.total_units
    return total


def sum_progresses(progresses, criterion_type, maxFunc):
    """Adds together a list of Progress objects by combining them one by one
    criterion_type: either subjects or units
    maxFunc: describes how to combine the maximums of the Progress objects"""

    if criterion_type == CRITERION_SUBJECTS:
        mapfunc = lambda p: p.subject_fulfillment
    elif criterion_type == CRITERION_UNITS:
        mapfunc = lambda p: p.unit_fulfillment
    sum_progress = reduce(lambda p1, p2: p1.combine(p2, maxFunc), list(map(mapfunc, progresses)))
    return sum_progress


def force_unfill_progresses(satisfied_by_category, current_distinct_threshold, current_threshold):
    """Adjusts the fulfillment and progress of RequirementsProgress object with both distinct thresholds and thresholds
    These requirements follow the form "X subjects/units from at least N categories"
    satisfied_by_category: list of lists of Courses for each category
    current_distinct_threshold: threshold object for distinct threshold
    current_threshold: threshold object for regular threshold"""

    subject_cutoff = current_threshold.cutoff_for_criterion(CRITERION_SUBJECTS)
    unit_cutoff = current_threshold.cutoff_for_criterion(CRITERION_UNITS)

    #list of subjects by category sorted by units
    max_unit_subjects = [sorted(sat_cat, key = lambda s: s.total_units) for sat_cat in satisfied_by_category]

    #split subjects into two sections: fixed and free
    #fixed subjects: must have one subject from each category
    #free subjects: remaining subjects to fill requirement can come from any category
    #choose maximum-unit courses to fulfill requirement with least amount of courses possible
    fixed_subject_progress = 0
    fixed_subject_max = current_distinct_threshold.get_actual_cutoff()
    fixed_unit_progress = 0
    fixed_unit_max = 0

    #fill fixed subjects with maximum-unit course in each category
    for category_subjects in max_unit_subjects:
        if len(category_subjects) > 0:
            subject_to_count = category_subjects.pop()
            fixed_subject_progress += 1
            fixed_unit_progress += subject_to_count.total_units
            fixed_unit_max += subject_to_count.total_units
        else:
            fixed_unit_max += DEFAULT_UNIT_COUNT

    #remaining subjects/units to fill
    remaining_subject_progress = subject_cutoff - fixed_subject_max
    remaining_unit_progress = unit_cutoff - fixed_unit_max

    #choose free courses from all remaining courses
    free_courses = sorted([course for category in max_unit_subjects for course in category], key = lambda s: s.total_units, reverse = True)
    free_subject_max = subject_cutoff - fixed_subject_max
    free_unit_max = unit_cutoff - fixed_unit_max

    free_subject_progress = min(len(free_courses), free_subject_max)
    free_unit_progress = min(total_units(free_courses), free_unit_max)

    #add fixed and free courses to get total progress
    subject_progress = Progress(fixed_subject_progress + free_subject_progress, subject_cutoff)
    unit_progress = Progress(fixed_unit_progress + free_unit_progress, unit_cutoff)
    return (subject_progress, unit_progress)


class JSONProgressConstants:
    """Each of these keys will be filled in a RequirementsStatement JSON
    representation decorated by a RequirementsProgress object."""

    is_fulfilled = "fulfilled"
    progress = "progress"
    progress_max = "max"
    percent_fulfilled = "percent_fulfilled"
    satisfied_courses = "sat_courses"

    # Progress assertions
    is_bypassed = "is_bypassed"
    assertion = "assertion"


class Progress(object):
    """An object describing simple progress towards a requirement
    Different from RequirementsProgress object as it only includes progress information,
    not nested RequirementsProgress objects, fulfillment status, title, and other information
    progress: number of units/subjects completed
    max: number of units/subjects needed to fulfill requirement"""

    def __init__(self, progress, max):
        self.progress = progress
        self.max = max

    def get_percent(self):
        if self.max > 0:
            return min(100, int(round((self.progress / float(self.max)) * 100)))
        else:
            return "N/A"

    def get_fraction(self):
        if self.max > 0:
            return self.progress / float(self.max)
        else:
            return "N/A"

    def get_raw_fraction(self, unit):
        denom = max(self.max, DEFAULT_UNIT_COUNT if unit == CRITERION_UNITS else 1)
        return self.progress/denom

    def combine(self, p2, maxFunc):
        if maxFunc is not None:
            return Progress(self.progress + p2.progress, self.max + maxFunc(p2.max))
        return Progress(self.progress + p2.progress, self.max + p2.max)

    def __repr__(self):
        return str(self.progress) + " / " + str(self.max)


class RequirementsProgress(object):
    """
    Stores a user's progress towards a given requirements statement. This object
    wraps a requirements statement and has a to_json_object() method which
    returns the statement's own JSON dictionary representation with progress
    information added.

    Note: This class is maintained separately from the Django model so that
    persistent information can be stored in a database-friendly format, while
    information specific to a user's request is transient.
    """
    def __init__(self, statement, list_path):
        """Initializes a progress object with the given requirements statement."""
        self.statement = statement
        self.threshold = self.statement.get_threshold()
        self.distinct_threshold = self.statement.get_distinct_threshold()
        self.list_path = list_path
        self.children = []
        if self.statement.requirement is None:
            for index, child in enumerate(self.statement.requirements.iterator()):
                self.children.append(RequirementsProgress(child, list_path + "." + str(index)))

    def courses_satisfying_req(self, courses):
        """
        Returns the whole courses and the half courses satisfying this requirement
        separately.
        """
        if self.statement.requirement is not None:
            req = self.statement.requirement
            if "GIR:" in req or "HASS" in req or "CI-" in req:
                # Separate whole and half courses
                whole_courses = []
                half_courses = []
                for c in courses:
                    if not c.satisfies(req, courses):
                        continue
                    if c.is_half_class:
                        half_courses.append(c)
                    else:
                        whole_courses.append(c)
                return whole_courses, half_courses
            else:
                return [c for c in courses if c.satisfies(req, courses)], []

        return [], []

    def override_requirement(self, manual_progress):
        """
        Sets the progress fulfillment variables based on a manual progress value, which is
        expressed in either units or subjects depending on the requirement's threshold.
        """
        self.is_fulfilled = manual_progress >= self.threshold.get_actual_cutoff()
        subjects = 0
        units = 0
        satisfied_courses = set()

        if self.threshold.criterion == CRITERION_UNITS:
            units = manual_progress
            subjects = manual_progress / DEFAULT_UNIT_COUNT
        else:
            units = manual_progress * DEFAULT_UNIT_COUNT
            subjects = manual_progress

        subject_progress = ceiling_thresh(subjects, self.threshold.cutoff_for_criterion(CRITERION_SUBJECTS))
        unit_progress = ceiling_thresh(units, self.threshold.cutoff_for_criterion(CRITERION_UNITS))
        #fill with dummy courses
        random_ids = random.sample(list(range(1000, max(10000, subject_progress.progress + 1000))), subject_progress.progress)

        for rand_id in random_ids:
            dummy_course = Course(id = self.list_path + "_" + str(rand_id), subject_id = "gen_course_" + self.list_path + "_" + str(rand_id), title = "Generated Course " + self.list_path + " " + str(rand_id))
            satisfied_courses.add(dummy_course)

        progress_units = CRITERION_SUBJECTS if self.threshold is None else self.threshold.criterion
        self.subject_fulfillment = subject_progress
        self.subject_progress = subject_progress.progress
        self.subject_max = subject_progress.max
        self.unit_fulfillment = unit_progress
        self.unit_progress = unit_progress.progress
        self.unit_max = unit_progress.max
        progress = unit_progress if self.threshold is not None and self.threshold.criterion == CRITERION_UNITS else subject_progress
        self.progress = progress.progress
        self.progress_max = progress.max
        self.percent_fulfilled = progress.get_percent()
        self.fraction_fulfilled = progress.get_fraction()
        self.raw_fraction_fulfilled = progress.get_raw_fraction(progress_units)
        self.satisfied_courses = list(satisfied_courses)

    def compute_assertions(self, courses, progress_assertions):
        """
        Computes the fulfillment of this requirement based on progress assertions, and returns
        True if the requirement has an assertion available or False otherwise.

        Assertions are in the format of a dictionary keyed by requirements list paths, where the
        values are dictionaries containing three possible keys: "substitutions", which should be a
        list of course IDs that combine to substitute for the requirement, "ignore", which
        indicates that the requirement is not to be used when satisfying later requirements, and
        "override", which is equivalent to the old manual progress value and indicates a progress
        toward the requirement in the unit specified by the requirement's threshold type (only
        used if the requirement is a plain string requirement and has a threshold). The order of
        precedence is override, ignore, substitutions.
        """
        self.assertion = progress_assertions.get(self.list_path, None)
        self.is_bypassed = False
        if self.assertion is not None:
            substitutions = self.assertion.get("substitutions", None) #List of substitutions
            ignore = self.assertion.get("ignore", False)               #Boolean
            override = self.assertion.get("override", 0)
        else:
            substitutions = None
            ignore = False
            override = 0

        if self.statement.is_plain_string and self.threshold is not None and override:
            self.override_requirement(override)
            return True
        if ignore:
            progress_units = CRITERION_SUBJECTS if self.threshold is None else self.threshold.criterion
            self.is_fulfilled = False
            subject_progress = Progress(0, 0)
            self.subject_fulfillment = subject_progress
            self.subject_progress = subject_progress.progress
            self.subject_max = subject_progress.max
            unit_progress = Progress(0, 0)
            self.unit_fulfillment = unit_progress
            self.unit_progress = unit_progress.progress
            self.unit_max = unit_progress.max
            progress = Progress(0, 0)
            self.progress = progress.progress
            self.progress_max = progress.max
            self.percent_fulfilled = progress.get_percent()
            self.fraction_fulfilled = progress.get_fraction()
            self.raw_fraction_fulfilled = progress.get_raw_fraction(progress_units)
            self.satisfied_courses = []
            return True
        if substitutions is not None:
            satisfied_courses = set()
            subs_satisfied = 0
            units_satisfied = 0
            for sub in substitutions:
                for course in courses:
                    if course.satisfies(sub, courses):
                        subs_satisfied += 1
                        units_satisfied += course.total_units
                        satisfied_courses.add(course)
                        break
            if self.statement.is_plain_string and self.threshold is not None:
                subject_progress = Progress(subs_satisfied,
                                            self.threshold.cutoff_for_criterion(CRITERION_SUBJECTS))
                unit_progress = Progress(units_satisfied,
                                         self.threshold.cutoff_for_criterion(CRITERION_UNITS))
                progress = subject_progress if self.threshold.criterion == CRITERION_SUBJECTS else unit_progress
                self.is_fulfilled = progress.progress == progress.max
            else:
                subject_progress = Progress(subs_satisfied, len(substitutions))
                self.is_fulfilled = subs_satisfied == len(substitutions)
                unit_progress = Progress(subs_satisfied * DEFAULT_UNIT_COUNT, len(substitutions) * DEFAULT_UNIT_COUNT)
                progress = subject_progress
            progress_units = CRITERION_SUBJECTS if self.threshold is None else self.threshold.criterion
            self.subject_fulfillment = subject_progress
            self.subject_progress = subject_progress.progress
            self.subject_max = subject_progress.max
            self.unit_fulfillment = unit_progress
            self.unit_progress = unit_progress.progress
            self.unit_max = unit_progress.max
            self.progress = progress.progress
            self.progress_max = progress.max
            self.percent_fulfilled = progress.get_percent()
            self.fraction_fulfilled = progress.get_fraction()
            self.raw_fraction_fulfilled = progress.get_raw_fraction(progress_units)
            self.satisfied_courses = list(satisfied_courses)
            return True

        return False

    def bypass_children(self):
        """Sets the is_bypassed flag of the recursive children of this progress object to True."""
        for child in self.children:
            child.is_bypassed = True
            child.is_fulfilled = False
            child.subject_fulfillment = Progress(0, 0)
            child.subject_progress = 0
            child.subject_max = 0
            child.unit_fulfillment = Progress(0, 0)
            child.unit_progress = 0
            child.unit_max = 0
            child.progress = 0
            child.progress_max = 0
            child.percent_fulfilled = 0
            child.fraction_fulfilled = 0
            child.raw_fraction_fulfilled = 0
            child.satisfied_courses = []
            child.assertion = None
            child.bypass_children()

    def compute(self, courses, progress_overrides, progress_assertions):
        """Computes and stores the status of the requirements statement using the
        given list of Course objects."""
        # Compute status of children and then self, adapted from mobile apps' computeRequirementsStatus method
        satisfied_courses = set()
        if self.compute_assertions(courses, progress_assertions):
            self.bypass_children()
            return

        if self.list_path in progress_overrides:
            manual_progress = progress_overrides[self.list_path]
        else:
            manual_progress = 0
        self.is_bypassed = False
        self.assertion = None

        if self.statement.requirement is not None:
            #it is a basic requirement
            if self.statement.is_plain_string and manual_progress != 0 and self.threshold is not None:
                #use manual progress
                self.override_requirement(manual_progress)
                return
            else:
                #Example: requirement CI-H, we want to show how many have been fulfilled
                whole_courses, half_courses = self.courses_satisfying_req(courses)
                satisfied_courses = whole_courses + half_courses

                if not self.threshold is None:
                    #A specific number of courses is required
                    subject_progress = ceiling_thresh(len(whole_courses) + len(half_courses) // 2, self.threshold.cutoff_for_criterion(CRITERION_SUBJECTS))
                    unit_progress = ceiling_thresh(total_units(satisfied_courses), self.threshold.cutoff_for_criterion(CRITERION_UNITS))
                    is_fulfilled = self.threshold.is_satisfied_by(subject_progress.progress, unit_progress.progress)
                else:
                    #Only one is needed
                    progress_subjects = min(len(satisfied_courses), 1)
                    is_fulfilled = len(satisfied_courses) > 0
                    subject_progress = ceiling_thresh(progress_subjects, 1)

                    if len(satisfied_courses) > 0:
                        unit_progress = ceiling_thresh(list(satisfied_courses)[0].total_units, DEFAULT_UNIT_COUNT)
                    else:
                        unit_progress = ceiling_thresh(0, DEFAULT_UNIT_COUNT)

            progress = unit_progress if self.threshold is not None and self.threshold.criterion == CRITERION_UNITS else subject_progress


        if len(self.children) > 0:
            #It's a compound requirement
            num_reqs_satisfied = 0
            satisfied_by_category = []
            satisfied_courses = set()
            num_courses_satisfied = 0

            open_children = []
            for req_progress in self.children:
                req_progress.compute(courses, progress_overrides, progress_assertions)
                req_satisfied_courses = req_progress.satisfied_courses

                # Don't count anything from a requirement that is ignored
                if req_progress.assertion and req_progress.assertion.get("ignore", False):
                    continue
                open_children.append(req_progress)

                if req_progress.is_fulfilled and len(req_progress.satisfied_courses) > 0:
                    num_reqs_satisfied += 1

                satisfied_courses.update(req_satisfied_courses)
                satisfied_by_category.append(list(req_satisfied_courses))

                # For thresholded ANY statements, children that are ALL statements
                # count as a single satisfied course. ANY children count for
                # all of their satisfied courses.
                if req_progress.statement.connection_type == CONNECTION_TYPE_ALL and req_progress.children:
                    num_courses_satisfied += req_progress.is_fulfilled and len(req_progress.satisfied_courses) > 0
                else:
                    num_courses_satisfied += len(req_satisfied_courses)

            satisfied_by_category = [sat for prog, sat in sorted(zip(open_children, satisfied_by_category), key = lambda z: z[0].raw_fraction_fulfilled, reverse = True)]
            sorted_progresses = sorted(open_children, key = lambda req: req.raw_fraction_fulfilled, reverse = True)

            if self.threshold is None and self.distinct_threshold is None:
                is_fulfilled = (num_reqs_satisfied > 0)

                if self.statement.connection_type == CONNECTION_TYPE_ANY:
                    #Simple "any" statement
                    if len(sorted_progresses) > 0:
                        subject_progress = sorted_progresses[0].subject_fulfillment
                        unit_progress = sorted_progresses[0].unit_fulfillment
                    else:
                        subject_progress = Progress(0, 0)
                        unit_progress = Progress(0, 0)

                else:
                    #"All" statement, will be finalized later
                    subject_progress = sum_progresses(sorted_progresses, CRITERION_SUBJECTS, None)
                    unit_progress = sum_progresses(sorted_progresses, CRITERION_UNITS, None)

            else:

                if self.distinct_threshold is not None:
                    #Clip the progresses to the ones which the user is closest to completing
                    num_progresses_to_count = min(self.distinct_threshold.get_actual_cutoff(), len(sorted_progresses))
                    sorted_progresses = sorted_progresses[:num_progresses_to_count]
                    satisfied_by_category = satisfied_by_category[:num_progresses_to_count]
                    satisfied_courses = set()
                    num_courses_satisfied = 0

                    for i, child in zip(list(range(num_progresses_to_count)), open_children):
                        satisfied_courses.update(satisfied_by_category[i])
                        if child.statement.connection_type == CONNECTION_TYPE_ALL:
                            num_courses_satisfied += (child.is_fulfilled and len(child.satisfied_courses) > 0)
                        else:
                            num_courses_satisfied += len(satisfied_by_category[i])

                if self.threshold is None and self.distinct_threshold is not None:
                    #Required number of statements
                    if self.distinct_threshold == THRESHOLD_TYPE_GTE or self.distinct_threshold.type == THRESHOLD_TYPE_GT:
                        is_fulfilled = num_reqs_satisfied >= self.distinct_threshold.get_actual_cutoff()
                    else:
                        is_fulfilled = True

                    subject_progress = sum_progresses(sorted_progresses, CRITERION_SUBJECTS, lambda x: max(x, 1))
                    unit_progress = sum_progresses(sorted_progresses, CRITERION_UNITS, lambda x: (x, DEFAULT_UNIT_COUNT)[x == 0])

                elif self.threshold is not None:
                    #Required number of subjects or units
                    subject_progress = Progress(num_courses_satisfied, self.threshold.cutoff_for_criterion(CRITERION_SUBJECTS))
                    unit_progress = Progress(total_units(satisfied_courses), self.threshold.cutoff_for_criterion(CRITERION_UNITS))

                    if self.distinct_threshold is not None and (self.distinct_threshold.type == THRESHOLD_TYPE_GT or self.distinct_threshold.type == THRESHOLD_TYPE_GTE):
                        is_fulfilled = self.threshold.is_satisfied_by(subject_progress.progress, unit_progress.progress) and num_reqs_satisfied >= self.distinct_threshold.get_actual_cutoff()
                        if num_reqs_satisfied < self.distinct_threshold.get_actual_cutoff():
                            (subject_progress, unit_progress) = force_unfill_progresses(satisfied_by_category, self.distinct_threshold, self.threshold)
                    else:
                        is_fulfilled = self.threshold.is_satisfied_by(subject_progress.progress, unit_progress.progress)

            if self.statement.connection_type == CONNECTION_TYPE_ALL:
                #"All" statement - make above progresses more stringent
                is_fulfilled = is_fulfilled and (num_reqs_satisfied == len(open_children))
                if subject_progress.progress == subject_progress.max and len(open_children) > num_reqs_satisfied:
                    subject_progress.max += len(open_children) - num_reqs_satisfied
                    unit_progress.max += (len(open_children) - num_reqs_satisfied) * DEFAULT_UNIT_COUNT
            #Polish up values
            subject_progress = ceiling_thresh(subject_progress.progress, subject_progress.max)
            unit_progress = ceiling_thresh(unit_progress.progress, unit_progress.max)
            progress = unit_progress if self.threshold is not None and self.threshold.criterion == CRITERION_UNITS else subject_progress

        progress_units = CRITERION_SUBJECTS if self.threshold is None else self.threshold.criterion
        self.is_fulfilled = is_fulfilled
        self.subject_fulfillment = subject_progress
        self.subject_progress = subject_progress.progress
        self.subject_max = subject_progress.max
        self.unit_fulfillment = unit_progress
        self.unit_progress = unit_progress.progress
        self.unit_max = unit_progress.max
        self.progress = progress.progress
        self.progress_max = progress.max
        self.percent_fulfilled = progress.get_percent()
        self.fraction_fulfilled = progress.get_fraction()
        self.raw_fraction_fulfilled = progress.get_raw_fraction(progress_units)
        self.satisfied_courses = list(satisfied_courses)

    def to_json_object(self, full = True, child_fn = None):
        """Returns a JSON dictionary containing the dictionary representation of
        the enclosed requirements statement, as well as progress information."""
        # Recursively decorate the JSON output of the children
        # Add custom keys indicating progress for this statement
        stmt_json = self.statement.to_json_object(full=False)
        stmt_json[JSONProgressConstants.is_fulfilled] = self.is_fulfilled
        stmt_json[JSONProgressConstants.progress] = self.progress
        stmt_json[JSONProgressConstants.progress_max] = self.progress_max
        stmt_json[JSONProgressConstants.percent_fulfilled] = self.percent_fulfilled
        stmt_json[JSONProgressConstants.satisfied_courses] = [c.subject_id for c in self.satisfied_courses]

        if self.is_bypassed:
            stmt_json[JSONProgressConstants.is_bypassed] = self.is_bypassed
        if self.assertion:
            stmt_json[JSONProgressConstants.assertion] = self.assertion

        if full:
            if self.children:
                if child_fn is None:
                    child_fn = lambda c: c.to_json_object(full=full)
                stmt_json[JSONConstants.requirements] =[child_fn(child) for child in self.children]

        return stmt_json
