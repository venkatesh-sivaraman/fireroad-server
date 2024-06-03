from django.db import models
from django.contrib.auth.models import User
from django.forms import ModelForm

road_compressions = {
    ('"overrideWarnings":', '"ow":'),
    ('"semester":', '"sm":'),
    ('"title":', '"t":'),
    ('"units":', '"u":')
}

schedule_compressions = {
    ('"selectedSubjects":', '"ssub":'),
    ('"selectedSections":', '"ssec":'),
    ('"allowedSections":', '"as":'),
}

class Road(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    contents = models.TextField()
    modified_date = models.DateTimeField(auto_now=True)
    last_agent = models.CharField(max_length=50, default="")

    def __str__(self):
        return "{}: {}, last modified {}".format(self.user.username, self.name, self.modified_date)

    @staticmethod
    def compress(road_text):
        road_text = road_text.replace("\n", "")
        road_text = road_text.replace("\t", "")
        road_text = road_text.replace('" : ', '":')
        for expr, sub in road_compressions:
            road_text = road_text.replace(expr, sub)
        return road_text

    @staticmethod
    def expand(road_text):
        for expr, sub in road_compressions:
            road_text = road_text.replace(sub, expr)
        return road_text

class RoadForm(ModelForm):
    class Meta:
        model = Road
        fields = ['name', 'contents']

class RoadBackup(models.Model):
    """Represents a timestamped snapshot of a particular road."""
    document = models.ForeignKey(Road, null=True, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    last_agent = models.CharField(max_length=50, default="")
    name = models.CharField(max_length=50)
    contents = models.TextField()

    def __str__(self):
        return "Backup of {}, saved {} by {}".format(self.document.name if self.document else "<null>",
                                                     self.timestamp,
                                                     self.last_agent if self.last_agent else "<empty>")

class Schedule(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    contents = models.TextField()
    modified_date = models.DateTimeField(auto_now=True)
    last_agent = models.CharField(max_length=50, default="")

    def __str__(self):
        return "{}: {}, last modified {}".format(self.user.username, self.name, self.modified_date)

    @staticmethod
    def compress(schedule_text):
        schedule_text = schedule_text.replace("\n", "")
        schedule_text = schedule_text.replace("\t", "")
        schedule_text = schedule_text.replace('" : ', '":')
        for expr, sub in schedule_compressions:
            schedule_text = schedule_text.replace(expr, sub)
        return schedule_text

    @staticmethod
    def expand(schedule_text):
        for expr, sub in schedule_compressions:
            schedule_text = schedule_text.replace(sub, expr)
        return schedule_text

class ScheduleBackup(models.Model):
    """Represents a timestamped snapshot of a particular schedule."""
    document = models.ForeignKey(Schedule, null=True, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    last_agent = models.CharField(max_length=50, default="")
    name = models.CharField(max_length=50)
    contents = models.TextField()

    def __str__(self):
        return "Backup of {}, saved {} by {}".format(self.document.name if self.document else "<null>",
                                                     self.timestamp,
                                                     self.last_agent if self.last_agent else "<empty>")

