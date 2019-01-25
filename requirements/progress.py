from reqlist import *


def ceiling_thresh(progress, maximum):
    effective_progress = max(0, progress)
    if maximum > 0:
        return Progress(min(effective_progress, maximum), maximum)
    else:
        return Progress(effective_progress, maximum)


def total_units(courses):
    total = 0
    for course in courses:
        total += course.total_units
    pass

def combine_progresses(p1,p2, maxFunc):
    if maxFunc is not None:
        return Progress(p1.progress+p2.progress,p1.max+maxFunc(p2.max))
    return Progress(p1.progress+p2.progress,p1.max+p2.max)

def sum_progresses(progresses, criterion_type, maxFunc):
    if criterion_type == CRITERION_SUBJECTS:
        mapfunc = lambda p: p.subject_fulfillment
    elif criterion_type == CRITERION_UNITS:
        mapfunc = lambda p: p.unit_fulfillment
    sum_progress = reduce(lambda p1, p2: combine_progresses(p1, p2, maxFunc), map(mapfunc, progresses))
    return sum_progress


class JSONProgressConstants:
    """Each of these keys will be filled in a RequirementsStatement JSON
    representation decorated by a RequirementsProgress object."""

    is_fulfilled = "fulfilled"
    subject_progress = "s_progress"
    subject_max = "s_max"
    unit_progress = "u_progress"
    unit_max = "u_max"
    progress = "progress"
    progress_max = "max"
    percent_fulfilled = "percent_fulfilled"
    children_fulfillment = "zreqs"
    satisfied_courses = "sat_courses"

class Progress(object):
    def __init__(self, progress, max):
        self.progress = progress
        self.max = max
    def get_progress(self):
        return self.progress
    def get_max(self):
        return self.max
    def get_percent(self):
        if self.max > 0:
            return int((self.progress / float(self.max))*100)
        else:
            return 0
    def get_fraction(self):
        if self.max > 0:
            return self.progress / float(self.max)
        else:
            return 0.0

class Threshold(object):
    def __init__(self, threshold_type, number, criterion):
        self.type = threshold_type
        self.cutoff = number
        self.criterion = criterion
    def cutoff_for_criterion(self, criterion):
        if self.criterion == criterion:
            co = self.cutoff
        elif self.criterion == CRITERION_SUBJECTS:
            co = self.cutoff * DEFAULT_UNIT_COUNT
        else:
            co = self.cutoff / DEFAULT_UNIT_COUNT
        return co
    def get_actual_cutoff(self):
        if self.type == THRESHOLD_TYPE_GT:
            return self.cutoff + 1
        elif self.type == THRESHOLD_TYPE_LT:
            return self.cutoff - 1
        return self.cutoff
    def is_satisfied_by(self, subject_progress, unit_progress):
        progress = (subject_progress, unit_progress)[self.criterion == CRITERION_UNITS]
        actualcutoff = self.get_actual_cutoff()
        if self.type == THRESHOLD_TYPE_LT or self.type == THRESHOLD_TYPE_LTE:
            return progess <= actualcutoff
        elif self.type == THRESHOLD_TYPE_GT or self.type == THRESHOLD_TYPE_GTE:
            return progress >= actualcutoff
    def __repr__(self):
        return self.type + " " + self.criterion + " " + self.number

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
    def __init__(self, statement):
        """Initializes a progress object with the given requirements statement."""
        self.statement = statement
        self.children = []
        if self.statement.requirements.exists():
            for child in self.statement.requirements.all():
                self.children.append(RequirementsProgress(child))

    def courses_satisfying_req(self, courses):
        if self.statement.requirement is not None:
            return [c for c in courses if c.satisfies(self.statement.requirement)]
        return []


    def compute(self, courses):
        """Computes and stores the status of the requirements statement using the
        given list of Course objects."""
        # Compute status of children and then self, adapted from mobile apps'
        # computeRequirementsStatus method
        satisfied_courses = []
        current_threshold = Threshold(self.statement.threshold_type, self.statement.threshold_cutoff, self.statement.threshold_criterion)
        current_distinct_threshold = Threshold(self.statement.distinct_threshold_type, self.statement.distinct_threshold_cutoff, self.statement.distinct_threshold_criterion)
        print("statement:")
        if self.statement.requirement is not None:
            if False:
                #manual progress
                pass
            else:
                satisfied_courses = self.courses_satisfying_req(courses)
                if not self.statement.threshold_type is None:
                    subject_progress = ceiling_thresh(len(satisfied_courses), current_threshold.cutoff_for_criterion(CRITERION_SUBJECTS))
                    unit_progress = ceiling_thresh(total_units(satisfied_courses), current_threshold.cutoff_for_criterion(CRITERION_UNITS))
                    is_fulfilled = current_threshold.is_satisfied_by(subject_progress.progress, unit_progress.progress)
                else:
                    progress_subjects = min(len(satisfied_courses), 1)
                    is_fulfilled = len(satisfied_courses) > 0
                    subject_progress = ceiling_thresh(progress_subjects, 1)
                    if len(satisfied_courses) > 0:
                        unit_progress = ceiling_thresh(satisfied_courses[0].total_units, DEFAULT_UNIT_COUNT)
                    else:
                        unit_progress = ceiling_thresh(0, DEFAULT_UNIT_COUNT)
                progress = (subject_progress, unit_progress)[self.statement.threshold_type is not None and self.statement.threshold_criterion == CRITERION_UNITS]
                self.is_fulfilled = is_fulfilled
                self.subject_fulfillment = subject_progress
                self.subject_progress = subject_progress.get_progress()
                self.subject_max = subject_progress.get_max()
                self.unit_fulfillment = unit_progress
                self.unit_progress = unit_progress.get_progress()
                self.unit_max = unit_progress.get_max()
                self.progress = progress.get_progress()
                self.progress_max = progress.get_max()
                self.percent_fulfilled = progress.get_percent()
                self.fraction_fulfilled = progress.get_fraction()
                self.satisfied_courses = satisfied_courses
        elif len(self.children)>0:
            print("children:")
            print(self.children)
            # satisfied_by_category = []
            # total_satisfied = []
            num_reqs_satisfied = 0

            for req_progress in self.children:
                req_progress.compute(courses)
                req_satisfied_courses = req_progress.satisfied_courses
                if(req_progress.is_fulfilled):
                    num_reqs_satisfied += 1
                satisfied_courses.extend(req_satisfied_courses)


            sorted_progresses = sorted(self.children,key=lambda req: req.fraction_fulfilled, reverse=True)
            print("Sorted progresses:")
            print([str(s) for s in sorted_progresses])
            # sorted_progresses.sort(key=lambda req: req.fraction_fulfilled, reverse=True)
            if self.statement.threshold_type is None and self.statement.distinct_threshold_type is None:
                is_fulfilled = (num_reqs_satisfied > 0)
                if self.statement.connection_type == CONNECTION_TYPE_ANY:
                    if len(sorted_progresses) > 0:
                        subject_progress = sorted_progresses[0].subject_fulfillment
                        unit_progress = sorted_progresses[0].unit_fulfillment
                    else:
                        subject_progress = Progress(0,0)
                        unit_progress = Progress(0,0)
                else:
                    subject_progress = sum_progresses(sorted_progresses, CRITERION_SUBJECTS, None)
                    unit_progress = sum_progresses(sorted_progresses, CRITERION_UNITS, None)
            else:
                if self.statement.distinct_threshold_type is not None:
                    sorted_progresses = sorted_progresses[:min(current_distinct_threshold.get_actual_cutoff(), len(sorted_progresses))]
                if self.statement.threshold_type is None and self.statement.distinct_threshold_type is not None:
                    if self.statement.distinct_threshold_type == THRESHOLD_TYPE_GTE or self.statement.distinct_threshold_type == THRESHOLD_TYPE_GT:
                        is_fulfilled = num_reqs_satisfied >= current_distinct_threshold.get_actual_cutoff()
                    else:
                        is_fulfilled = True
                    subject_progress = sum_progresses(sorted_progresses, CRITERION_SUBJECTS, lambda x: max(x,1))
                    unit_progress = sum_progresses(sorted_progresses, CRITERION_UNITS, lambda x: (x, DEFAULT_UNIT_COUNT)[x==0])
                elif self.statement.threshold_type is not None:
                    subject_progress = Progress(len(satisfied_courses), current_threshold.cutoff_for_criterion(CRITERION_SUBJECTS))
                    unit_progress = Progress(total_units(satisfied_courses), current_threshold.cutoff_for_criterion(CRITERION_UNITS))
                    if self.statement.distinct_threshold_type is not None and (self.statement.distinct_threshold_type == THRESHOLD_TYPE_GT or self.statement.distinct_threshold_type == THRESHOLD_TYPE_GTE):
                        is_fulfilled = current_threshold.is_satisfied_by(subject_progress.progress, unit_progress.progress) and num_reqs_satisfied >= current_distinct_threshold.get_actual_cutoff()
                        if num_reqs_satisfied < current_distinct_threshold.get_actual_cutoff():
                            subject_progress = sum_progresses(sorted_progresses, CRITERION_SUBJECTS, lambda x: max(x,1))
                            unit_progress = sum_progresses(sorted_progresses, CRITERION_UNITS, lambda x: (x, DEFAULT_UNIT_COUNT)[x==0])
                    else:
                        is_fulfilled = current_threshold.is_satisfied_by(subject_progress.progress, unit_progress.progress)
            if self.statement.connection_type == CONNECTION_TYPE_ALL:
                is_fulfilled = is_fulfilled and (num_reqs_satisfied == len(self.children))
                if subject_progress.progress == subject_progress.max and len(self.children) > num_reqs_satisfied:
                    subject_progress.max += len(self.children) - num_reqs_satisfied
                    unit_progress.max += (len(self.children) - num_reqs_satisfied) * DEFAULT_UNIT_COUNT
            subject_progress = ceiling_thresh(subject_progress.progress, subject_progress.max)
            unit_progress = ceiling_thresh(unit_progress.progress, unit_progress.max)
            progress = (subject_progress, unit_progress)[self.statement.threshold_type is not None and self.statement.threshold_criterion == CRITERION_UNITS]
            self.is_fulfilled = is_fulfilled
            self.subject_fulfillment = subject_progress
            self.subject_progress = subject_progress.get_progress()
            self.subject_max = subject_progress.get_max()
            self.unit_fulfillment = unit_progress
            self.unit_progress = unit_progress.get_progress()
            self.unit_max = unit_progress.get_max()
            self.progress = progress.get_progress()
            self.progress_max = progress.get_max()
            self.percent_fulfilled = progress.get_percent()
            self.fraction_fulfilled = progress.get_fraction()
            self.satisfied_courses = satisfied_courses

    def to_json_object(self, full=True):
        """Returns a JSON dictionary containing the dictionary representation of
        the enclosed requirements statement, as well as progress information."""
        # Recursively decorate the JSON output of the children
        print("Json of {} with full true".format(self.statement))
        # stmt = self.statement.to_json_object(full=True, child_fn=lambda c: self.children[c].to_json_object())
        # Add custom keys indicating progress for this statement
        # stmt[JSONProgressConstants.is_fulfilled] = False
        stmt_json = self.statement.to_json_object()
        stmt_json[JSONProgressConstants.is_fulfilled] = self.is_fulfilled
        stmt_json[JSONProgressConstants.subject_progress] = self.subject_progress
        stmt_json[JSONProgressConstants.subject_max] = self.subject_max
        stmt_json[JSONProgressConstants.unit_progress] = self.unit_progress
        stmt_json[JSONProgressConstants.unit_max] = self.unit_max
        stmt_json[JSONProgressConstants.progress] = self.progress
        stmt_json[JSONProgressConstants.progress_max] = self.progress_max
        stmt_json[JSONProgressConstants.percent_fulfilled] = self.percent_fulfilled
        stmt_json[JSONProgressConstants.satisfied_courses] = map(lambda c: c.subject_id, self.satisfied_courses)
        if full:
            if JSONConstants.requirements in stmt_json:
                del stmt_json[JSONConstants.requirements]
            stmt_json[JSONProgressConstants.children_fulfillment] = []
            for child in self.children:
                stmt_json[JSONProgressConstants.children_fulfillment].append(child.to_json_object(full))
        # stmt = self.statement.to_json_object(full=True, child_fn=lambda c: self.children[c].to_json_object())

        # stmt_json["children_fulfillment"] = map()
        return stmt_json
