from reqlist import *

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
        self.children = {} # Dictionary from child requirements to child progresses
        if self.statement.requirements.exists():
            for child in self.statement.requirements.all():
                self.children[child] = RequirementsProgress(child)

    class Progress(object):
        def __init__(self, progress, max):
            self.progress = progress
            self.max = max
        def get_progress():
            return self.progress
        def get_max():
            return self.max
        def get_percent():
            return int((self.progress / float(self.max))*100)

    @staticmethod
    def ceiling_thresh(progress, max):
        effective_progress = max(0, progress)
        if max > 0:
            return Progress(min(effective_progress, max), max)
        else:
            return Progress(effective_progress, max)

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


    @staticmethod
    def total_units(courses):
        pass

    def courses_satisfying_req(self, courses):
        if self.statement:
            return [c for c in courses if c.satisfies(self.statement)]
        return []


    def compute(self, courses):
        """Computes and stores the status of the requirements statement using the
        given list of Course objects."""
        # Compute status of children and then self, adapted from mobile apps'
        # computeRequirementsStatus method
        satisfied_courses = dict()
        if self.statement.requirement.exists():
            if False:
                pass
            else:
                satisfied_courses = courses_satisfying_req(courses)
                if not self.statement.threshold_type is None:
                    current_threshold = Threshold(self.statement.threshold_type, self.statement.threshold_cutoff, self.statement.threshold_criterion)
                    subject_progress = ceiling_thresh(len(satisfied_courses), current_threshold.cutoff_for_criterion(CRITERION_SUBJECTS))
                    unit_progress = ceiling_thresh(total_units(satisfied_courses), current_threshold.cutoff_for_criterion(CRITERION_UNITS))
                    is_fulfilled = current_threshold.is_satisfied_by(subject_progress.progress, unit_progress.progress)
                else:
                    progress = min(len(satisfied_courses), 1)
                    is_fulfilled = len(satisfied_courses) > 0
                    subject_progress = ceiling_thresh(progress, 1)
                    if len(satisfied_courses) > 0:
                        unit_progress = ceiling_thresh(satisfied_courses[0].total_units, DEFAULT_UNIT_COUNT)
                    else
                        unit_progress = ceiling_thresh(0, DEFAULT_UNIT_COUNT)
                progress = (subject_progress, unit_progress)[self.statement.threshold_type is not None and self.statement.threshold.criterion == CRITERION_UNITS]
                percent_fulfilled = progress.get_percent()
                self.statement.is_fulfilled = is_fulfilled
                self.statement.subject_progress = subject_progress.get_progress()
                self.statement.subject_max = subject_progress.get_max()
                self.statement.unit_progress = unit_progress.get_progress()
                self.statement.unit_max = unit_progress.get_max()
                self.statement.progress = progress.get_progress()
                self.statement.progress_max = progress.get_max()
                self.statement.percent_fulfilled = percent_fulfilled

        


    def to_json_object(self):
        """Returns a JSON dictionary containing the dictionary representation of
        the enclosed requirements statement, as well as progress information."""
        # Recursively decorate the JSON output of the children
        print("Json of {} with full true".format(self.statement))
        stmt = self.statement.to_json_object(full=True, child_fn=lambda c: self.children[c].to_json_object())
        # Add custom keys indicating progress for this statement
        stmt[JSONProgressConstants.is_fulfilled] = False
        # etc.
        return stmt
