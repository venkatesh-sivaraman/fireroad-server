from django.db import models

MAX_RATING_VALUE = 5

# Create your models here.
class Rating(models.Model):
    user_id = models.IntegerField(default=0)
    subject_id = models.CharField(max_length=50)
    value = models.IntegerField(default=0)

    def __str__(self):
        return "<User {} rated {} as {}>".format(self.user_id, self.subject_id, self.value)
