from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.core.exceptions import ObjectDoesNotExist
from .models import RequestCount
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
import json
import itertools

@staff_member_required
def dashboard(request):
    """Renders the template for the dashboard."""
    return render(request, "analytics/dashboard.html")

@staff_member_required
def total_requests(request):
    """Returns data for the Chart.js chart containing the total number of
    requests over time."""
    early_time = timezone.now() - timezone.timedelta(hours=24)
    data = RequestCount.tabulate_requests(early_time, timezone.timedelta(hours=1), lambda _: 1)
    labels, counts = itertools.izip(*((t.strftime("%m/%d/%Y %H:%M"), item.get(1, 0)) for t, item in data))
    counts = [item.get(1, 0) for _, item in data]
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
def user_agents(request):
    """Returns data for the Chart.js chart containing the various user agents
    observed over time."""
    early_time = timezone.now() - timezone.timedelta(hours=24)
    data = RequestCount.tabulate_requests(early_time, timezone.timedelta(hours=1), lambda request: translate_user_agent_string(request.user_agent))
    labels = [t.strftime("%m/%d/%Y %H:%M") for t, _ in data]
    datasets = {agent: [item.get(agent, 0) for _, item in data] for agent in USER_AGENT_TYPES}
    return HttpResponse(json.dumps({"labels": labels, "data": datasets}), content_type="application/json")
