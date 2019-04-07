from django.db import models
from django.forms import ModelForm
from django.contrib.auth.models import User

class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['username', 'password']

class Student(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    academic_id = models.CharField(max_length=50)
    current_semester = models.CharField(max_length=25, default='0')
    name = models.CharField(max_length=40, default="")
    semester_update_date = models.DateTimeField(auto_now=True)
    unique_id = models.CharField(max_length=50, default="")

    favorites = models.CharField(max_length=2000, default="")
    progress_overrides = models.CharField(max_length=3000, default="")
    notes = models.TextField(default="")

    def __str__(self):
        return "ID {}, in {} ({} user)".format(self.academic_id, self.current_semester, self.user)

class OAuthCache(models.Model):
    state = models.CharField(max_length=50)
    nonce = models.CharField(max_length=50)
    current_semester = models.CharField(max_length=25, default='0')
    date = models.DateTimeField(auto_now_add=True)

    # Store redirect URI if provided
    redirect_uri = models.CharField(max_length=200, null=True)

class TemporaryCode(models.Model):
    code = models.CharField(max_length=100)
    access_info = models.CharField(max_length=500)
    date = models.DateTimeField(auto_now_add=True)

class RedirectURL(models.Model):
    """Defines a registered redirect URL for the login endpoint."""
    label = models.CharField(max_length=50)
    url = models.CharField(max_length=200)

    def __str__(self):
        return self.label + ": " + self.url
