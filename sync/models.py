from django.db import models
from django.contrib.auth.models import User
from django.forms import ModelForm

road_compressions = {
    ('"overrideWarnings":', '"ow":'),
    ('"semester":', '"sm":'),
    ('"title":', '"t":'),
    ('"units":', '"u":')
}

class Road(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    contents = models.CharField(max_length=10000)

    def __str__(self):
        return "{}: {}".format(self.user.username, self.contents)

    @staticmethod
    def compress_road(road_text):
        road_text = road_text.replace("\n", "")
        road_text = road_text.replace("\t", "")
        road_text = road_text.replace('" : ', '":')
        for expr, sub in road_compressions:
            road_text = road_text.replace(expr, sub)
        return road_text

    @staticmethod
    def expand_road(road_text):
        for expr, sub in road_compressions:
            road_text = road_text.replace(sub, expr)
        return road_text

class RoadForm(ModelForm):
    class Meta:
        model = Road
        fields = ['name', 'contents']
