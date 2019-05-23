from django.db import models
from django import forms

# Create your models here.
class CatalogUpdate(models.Model):
    """
    Describes an update to the course catalog, and lists the current state.
    """
    creation_date = models.DateTimeField(auto_now_add=True)
    semester = models.CharField(default="", max_length=30)
    progress = models.FloatField(default=0.0)
    progress_message = models.CharField(default="", max_length=50)
    is_completed = models.BooleanField(default=False)
    is_started = models.BooleanField(default=False)

    def __str__(self):
        base = "Catalog update for {} on {}".format(self.semester, self.creation_date)
        if self.is_completed:
            base += " (completed)"
        elif self.is_started:
            base += " ({:.2f}% complete - {})".format(self.progress, self.progress_message)
        return base

class CatalogUpdateStartForm(forms.Form):
    semester = forms.CharField(label='Semester', max_length=30, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'e.g. fall-2019'}))

class CatalogUpdateDeployForm(forms.Form):
    pass
