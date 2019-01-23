from reqlist import *

class RequirementsProgress(object):
    """
    Stores a user's progress towards a given requirements statement. This object
    wraps a requirements statement and has a to_json_object() method which
    returns the statement's own JSON dictionary representation with progress
    information added.
    """
    def __init__(self, statement):
        """Initializes a progress object with the given requirements statement."""
        self.statement = statement

    def compute(self, courses):
        """Computes and stores the status of the requirements statement using the
        given list of Course objects."""
        pass

    def to_json_object(self):
        """Returns a JSON dictionary containing the dictionary representation of
        the enclosed requirements statement, as well as progress information."""
        pass
