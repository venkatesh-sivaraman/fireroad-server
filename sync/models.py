"""Models for sync functionality, namely storage for users' Road and Schedules."""

from django.db import models
from django.contrib.auth.models import User
from django.forms import ModelForm

ROAD_COMPRESSIONS = {
    ('"overrideWarnings":', '"ow":'),
    ('"semester":', '"sm":'),
    ('"title":', '"t":'),
    ('"units":', '"u":')
}

SCHEDULE_COMPRESSIONS = {
    ('"selectedSubjects":', '"ssub":'),
    ('"selectedSections":', '"ssec":'),
    ('"allowedSections":', '"as":'),
}

class Road(models.Model):
    """A class that describes a user's road document. Roads and Schedules should have the same API
    unless absolutely necessary."""

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    contents = models.TextField()
    modified_date = models.DateTimeField(auto_now=True)
    last_agent = models.CharField(max_length=50, default="")

    def __unicode__(self):
        return u"{}: {}, last modified {}".format(
            self.user.username, self.name.encode('utf-8'), self.modified_date)

    @staticmethod
    def compress(road_text):
        """Makes certain substitutions in the road file JSON to reduce the size of the stored text
        in the server."""
        road_text = road_text.replace("\n", "")
        road_text = road_text.replace("\t", "")
        road_text = road_text.replace('" : ', '":')
        for expr, sub in ROAD_COMPRESSIONS:
            road_text = road_text.replace(expr, sub)
        return road_text

    @staticmethod
    def expand(road_text):
        """Performs the reverse operation of compress() to create a spec-compliant road file
        again."""
        for expr, sub in ROAD_COMPRESSIONS:
            road_text = road_text.replace(sub, expr)
        return road_text


class Schedule(models.Model):
    """A class that describes a user's schedule document. Roads and Schedules should have the same
    API unless absolutely necessary."""

    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    contents = models.TextField()
    modified_date = models.DateTimeField(auto_now=True)
    last_agent = models.CharField(max_length=50, default="")

    def __unicode__(self):
        return u"{}: {}, last modified {}".format(
            self.user.username, self.name.encode('utf-8'), self.modified_date)

    @staticmethod
    def compress(schedule_text):
        """Makes certain substitutions that reduce the size of the schedule file in the
        database."""
        schedule_text = schedule_text.replace("\n", "")
        schedule_text = schedule_text.replace("\t", "")
        schedule_text = schedule_text.replace('" : ', '":')
        for expr, sub in SCHEDULE_COMPRESSIONS:
            schedule_text = schedule_text.replace(expr, sub)
        return schedule_text

    @staticmethod
    def expand(schedule_text):
        """Performs the reverse operation to compress(), recreating a schedule spec-compliant
        file."""
        for expr, sub in SCHEDULE_COMPRESSIONS:
            schedule_text = schedule_text.replace(sub, expr)
        return schedule_text
