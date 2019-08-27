from django.db import models

class RequestCount(models.Model):
    """Keeps track of a single request."""

    path = models.CharField(max_length=50, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_agent = models.CharField(max_length=150, null=True)
    is_authenticated = models.BooleanField(default=False)
    student_unique_id = models.CharField(max_length=50, null=True)
    student_semester = models.CharField(max_length=25, null=True)

    def __str__(self):
        return "{} by {} at {}{}".format(
            self.path,
            self.user_agent,
            self.timestamp,
            " (logged in)" if self.is_authenticated else ""
        )
