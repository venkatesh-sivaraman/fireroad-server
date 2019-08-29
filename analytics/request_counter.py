"""This module counts basic information about incoming requests to the
FireRoad server.

NOTE: The data that is collected contains potential user-identifying
information (namely, the user's unique ID and current semester). This info will
not leave the FireRoad server unless it is aggregated such that users are no
longer identifiable.
"""

from .models import *

EXCLUDE_PATH_PREFIXES = [
    "/favicon.ico",
    "/admin",
]

EXCLUDE_USER_AGENTS = [
    "check_http",
    "monitoring",
    "bot",
    "crawl",
    "spider"
]

class RequestCounterMiddleware(object):
    """A middleware that saves a RequestCount object each time a page is requested."""

    def process_request(self, request):
        """Called before Django calls the request's view. We will use this hook
        to log basic information about the request."""
        if any(request.path.startswith(prefix) for prefix in EXCLUDE_PATH_PREFIXES):
            return
        user_agent = request.META["HTTP_USER_AGENT"]
        if any(element in user_agent.lower() for element in EXCLUDE_USER_AGENTS):
            return

        tally = RequestCount.objects.create()
        tally.path = request.path
        if len(user_agent) > 150:
            user_agent = user_agent[:150]
        tally.user_agent = user_agent
        if request.user and request.user.is_authenticated():
            tally.is_authenticated = True
            try:
                student = request.user.student
            except:
                pass
            else:
                tally.student_unique_id = student.unique_id
                tally.student_semester = student.current_semester
        tally.save()
