from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from .models import RequestCount
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
import json
import re
import itertools

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
                num_bars = (timezone.now() - early_time).seconds / interval.seconds + 1
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

def strip_leading_zeros(string):
    """Strips all leading zeros from the given string (e.g. Jan 01 -> Jan 1)."""
    return re.sub(r"(^|(?<=[^\w]))0+", "", string)

@staff_member_required
def total_requests(request, time_frame=None):
    """Returns data for the Chart.js chart containing the total number of
    requests over time."""
    early_time, delta, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, delta, lambda _: 1)
    labels, counts = itertools.izip(*((strip_leading_zeros(t.strftime(format)), item.get(1, 0)) for t, item in data))
    return HttpResponse(json.dumps({"labels": labels, "data": counts}), content_type="application/json")

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
    early_time, delta, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, delta, lambda request: translate_user_agent_string(request.user_agent))
    labels = [strip_leading_zeros(t.strftime(format)) for t, _ in data]
    datasets = {agent: [item.get(agent, 0) for _, item in data] for agent in USER_AGENT_TYPES}
    return HttpResponse(json.dumps({"labels": labels, "data": datasets}), content_type="application/json")

@staff_member_required
def logged_in_users(request, time_frame=None):
    """Returns data for the Chart.js chart representing logged-in users over time."""
    early_time, delta, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, delta, lambda request: request.student_unique_id)
    labels, counts = itertools.izip(*((strip_leading_zeros(t.strftime(format)), len([k for k in item.keys() if k])) for t, item in data))
    return HttpResponse(json.dumps({"labels": labels, "data": counts}), content_type="application/json")

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

def get_semester_name(request):
    """Returns a semester name for the given request, or None if no semester is
    logged."""
    if not request.is_authenticated:
        return None

    try:
        return SEMESTERS[int(request.student_semester)]
    except:
        return None

@staff_member_required
def user_semesters(request, time_frame=None):
    """Returns data for the Chart.js chart representing the semesters in which
    logged-in users fall."""
    early_time, delta, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, delta, get_semester_name)
    labels = SEMESTERS
    data = [sum(item.get(semester, 0) for _, item in data) for semester in SEMESTERS]
    return HttpResponse(json.dumps({"labels": labels, "data": data}), content_type="application/json")

@staff_member_required
def request_paths(request, time_frame=None):
    """Returns data for the Chart.js chart showing counts for various request paths."""
    early_time, delta, format = get_time_bounds(time_frame)
    data = RequestCount.tabulate_requests(early_time, delta, lambda request: request.path)
    labels = set.union(*(set(item.keys()) for _, item in data)) - set([None])
    counts = {label: sum(item.get(label, 0) for _, item in data) for label in labels}
    labels, counts = itertools.izip(*sorted(counts.items(), key=lambda x: x[1], reverse=True))
    if len(labels) > 15:
        labels = labels[:15]
        counts = counts[:15]
    return HttpResponse(json.dumps({"labels": labels, "data": counts}), content_type="application/json")
