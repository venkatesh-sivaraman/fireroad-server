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

    def compute(self, courses):
        """Computes and stores the status of the requirements statement using the
        given list of Course objects."""
        # Compute status of children and then self, adapted from mobile apps'
        # computeRequirementsStatus method
        pass

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
