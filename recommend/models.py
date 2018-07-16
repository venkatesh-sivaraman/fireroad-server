from django.db import models
from django.forms import ModelForm
from django.contrib.auth.models import User

MAX_RATING_VALUE = 5
DEFAULT_RECOMMENDATION_TYPE = "for-you"

# Create your models here.
class Rating(models.Model):
    user_id = models.BigIntegerField(default=0)
    subject_id = models.CharField(max_length=50)
    value = models.IntegerField(default=0)

    def __str__(self):
        return "User {} rated {} as {}".format(self.user_id, self.subject_id, self.value)

class Recommendation(models.Model):
    user_id = models.BigIntegerField(default=0)
    rec_type = models.CharField(max_length=20)
    subjects = models.CharField(max_length=500)

    def __str__(self):
        return "Recommendation ({}) for user {}: {}".format(self.rec_type, self.user_id, self.subjects)

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['username', 'password']

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    academic_id = models.CharField(max_length=50)
    current_semester = models.CharField(max_length=25, default='0')
    name = models.CharField(max_length=40, default="")

    def __str__(self):
        return "{}: ID {}, in {}".format(self.user.username, self.academic_id, self.current_semester)

road_compressions = {
    ('"overrideWarnings":', '"ow":'),
    ('"semester":', '"sm":'),
    ('"title":', '"t":'),
    ('"units":', '"u":')
}

class Road(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    contents = models.CharField(max_length=5000)

    def __str__(self):
        return "{}: {}".format(self.user.username, self.contents)

    @staticmethod
    def compress_road(road_text):
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

class OAuthCache(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    state = models.CharField(max_length=50)
    nonce = models.CharField(max_length=50)
    date = models.DateTimeField(auto_now_add=True)
