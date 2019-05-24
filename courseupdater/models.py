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
    is_staged = models.BooleanField(default=False)
    is_started = models.BooleanField(default=False)

    def __str__(self):
        base = "Catalog update for {} on {}".format(self.semester, self.creation_date)
        if self.is_completed:
            base += " (completed)"
        elif self.is_staged:
            base += " (staged)"
        elif self.is_started:
            base += " ({:.2f}% complete - {})".format(self.progress, self.progress_message)
        return base

class CatalogUpdateStartForm(forms.Form):
    semester = forms.CharField(label='Semester', max_length=30, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'e.g. fall-2019'}))

    def clean_semester(self):
        """
        Ensures that the entered semester is of the form 'season-year'.
        """
        semester = self.cleaned_data['semester']
        comps = semester.split('-')
        if len(comps) != 2:
            raise forms.ValidationError("Semester must be in the format 'season-year'.")
        season, year = comps
        if season not in ('fall', 'spring'):
            raise forms.ValidationError("Season must be fall or spring.")
        try:
            year = int(year)
        except:
            raise forms.ValidationError("Year should be a number.")
        else:
            if year < 2000 or year > 3000:
                raise forms.ValidationError("Invalid year.")
        return semester


class CatalogUpdateDeployForm(forms.Form):
    pass
