from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from .models import RequestCount
from sync.models import Road, Schedule
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
import json
import re
import pytz
import itertools

# The time zone used to display times in all the views. This is distinct from
# the time zone that the server runs on, which is UTC by default.
DISPLAY_TIME_ZONE = pytz.timezone("America/New_York")

@staff_member_required
def dashboard(request):
    """Renders the template for the dashboard."""
    return render(request, "analytics/dashboard.html")

def get_time_bounds(time_frame):
    """Translates a time frame string (e.g. "day", "week", "month", "year",
    "all-time") into a minimum time and an interval between times for the
    data collection. Returns (minimum time, interval, format string)."""
    if time_frame == "week":
        early_time = timezone.now() - timezone.timedelta(days=7)
        early_time = early_time.replace(hour=0, minute=0)
        delta = timezone.timedelta(days=1)
        format = "%a, %b %d"
    elif time_frame == "month":
        early_time = timezone.now() - timezone.timedelta(weeks=4)
        early_time = early_time.replace(hour=0, minute=0)
        delta = timezone.timedelta(days=1)
        format = "%b %d"
    elif time_frame == "year":
        early_time = timezone.now() - timezone.timedelta(weeks=52)
        early_time = early_time.replace(hour=0, minute=0)
        delta = timezone.timedelta(weeks=1)
        format = "%b %d, %Y"
    elif time_frame == "all-time":
        try:
            early_time = RequestCount.objects.order_by("timestamp").first().timestamp
            early_time = early_time.replace(minute=0)
            # Try multiple intervals to see what's best
            last_result = None
            test_intervals = [
                (timezone.timedelta(hours=1), "%I %p"),
                (timezone.timedelta(days=1), "%a, %b %d"),
                (timezone.timedelta(weeks=1), "%a, %b %d"),
                (timezone.timedelta(weeks=4), "%b %d, %Y")
            ]
            for interval, format in test_intervals:
                num_bars = (timezone.now() - early_time).total_seconds() / interval.total_seconds() + 1
                last_result = early_time, interval, format
                if 8 <= num_bars <= 15:
                    break
            early_time, delta, format = last_result
            format = "%b %d, %Y"
        except ObjectDoesNotExist:
            early_time = timezone.now() - timezone.timedelta(hours=24)
            early_time = early_time.replace(hour=0, minute=0)
            delta = timezone.timedelta(hours=1)
            format = "%I %p"
    else:
        early_time = timezone.now() - timezone.timedelta(hours=24)
        early_time = early_time.replace(minute=0)
        delta = timezone.timedelta(hours=1)
        format = "%I %p"
    return early_time, delta, format

def format_date(date, format):
    """Formats the date for rendering in a template by converting to the
    appropriate time zone, formatting it into a string, and stripping all
    leading zeros from the given string (e.g. Jan 01 -> Jan 1)."""
    string = timezone.localtime(date).strftime(format)
    return re.sub(r"(^|(?<=[^\w]))0+", "", string)

@staff_member_required
def total_requests(request, time_frame=None):
    """Returns data for the Chart.js chart containing the total number of
    requests over time."""
    timezone.activate(DISPLAY_TIME_ZONE)
    early_time, delta, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, delta, lambda _: 1)
    labels, counts = itertools.izip(*((format_date(t, format), item.get(1, 0)) for t, item in data))
    return HttpResponse(json.dumps({"labels": labels, "data": counts, "total": "{:,}".format(sum(counts))}), content_type="application/json")

USER_AGENT_TYPES = [
    "Desktop",
    "iOS",
    "Android",
    "Mobile Safari",
    "Android Browser"
]

def translate_user_agent_string(user_agent):
    """Returns the most likely user agent type for the given user agent string."""
    if not user_agent:
        return None
    if "CFNetwork" in user_agent:
        return "iOS"
    elif "okhttp" in user_agent:
        return "Android"
    elif "Android" in user_agent:
        return "Android Browser"
    elif "Mobile" in user_agent and "Safari" in user_agent:
        return "Mobile Safari"
    else:
        return "Desktop"

@staff_member_required
def user_agents(request, time_frame=None):
    """Returns data for the Chart.js chart containing the various user agents
    observed over time."""
    timezone.activate(DISPLAY_TIME_ZONE)
    early_time, delta, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, delta, lambda request: translate_user_agent_string(request.user_agent))
    labels = [format_date(t, format) for t, _ in data]
    datasets = {agent: [item.get(agent, 0) for _, item in data] for agent in USER_AGENT_TYPES}
    return HttpResponse(json.dumps({"labels": labels, "data": datasets}), content_type="application/json")

@staff_member_required
def logged_in_users(request, time_frame=None):
    """Returns data for the Chart.js chart representing logged-in users over time."""
    timezone.activate(DISPLAY_TIME_ZONE)
    early_time, delta, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, delta, lambda _: 1, distinct_users=True)
    total_data = RequestCount.tabulate_requests(early_time, None, lambda _: 1, distinct_users=True)
    labels, counts = itertools.izip(*((format_date(t, format), item.get(1, 0)) for t, item in data))
    return HttpResponse(json.dumps({"labels": labels, "data": counts, "total": "{:,}".format(total_data.get(1, 0))}), content_type="application/json")

SEMESTERS = [
    "None",
    "1st Year Fall",
    "1st Year IAP",
    "1st Year Spring",
    "2nd Year Fall",
    "2nd Year IAP",
    "2nd Year Spring",
    "3rd Year Fall",
    "3rd Year IAP",
    "3rd Year Spring",
    "4th Year Fall",
    "4th Year IAP",
    "4th Year Spring",
    "5th Year Fall",
    "5th Year IAP",
    "5th Year Spring",
]

def get_semester_number(request):
    """Returns a tuple with the user's ID and the semester number for the given
    request, or None if no semester is logged."""
    if not request.is_authenticated:
        return None

    try:
        return int(request.student_semester)
    except:
        return None

@staff_member_required
def user_semesters(request, time_frame=None):
    """Returns data for the Chart.js chart representing the semesters in which
    logged-in users fall."""
    timezone.activate(DISPLAY_TIME_ZONE)
    early_time, _, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, None, get_semester_number, distinct_users=True)
    labels = SEMESTERS

    semester_buckets = [0 for _ in SEMESTERS]
    for semester, _ in data.items():
        if not semester or semester < 0 or semester >= len(semester_buckets):
            continue
        semester_buckets[semester] += 1
    return HttpResponse(json.dumps({"labels": labels, "data": semester_buckets}), content_type="application/json")

@staff_member_required
def request_paths(request, time_frame=None):
    """Returns data for the Chart.js chart showing counts for various request paths."""
    timezone.activate(DISPLAY_TIME_ZONE)
    early_time, _, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, None, lambda request: request.path)
    labels = set(data.keys()) - set([None])
    counts = {label: data.get(label, 0) for label in labels}
    labels, counts = itertools.izip(*sorted(counts.items(), key=lambda x: x[1], reverse=True))
    if len(labels) > 15:
        labels = labels[:15]
        counts = counts[:15]
    return HttpResponse(json.dumps({"labels": labels, "data": counts}), content_type="application/json")

@staff_member_required
def active_documents(request, time_frame=None):
    """Returns data for the scorecard showing the number of active roads and schedules."""
    timezone.activate(DISPLAY_TIME_ZONE)
    early_time, _, format = get_time_bounds(time_frame)
    modified_roads = Road.objects.filter(modified_date__gte=early_time).count()
    modified_schedules = Schedule.objects.filter(modified_date__gte=early_time).count()
    return HttpResponse(json.dumps({"roads": "{:,}".format(modified_roads), "schedules": "{:,}".format(modified_schedules)}), content_type="application/json")
