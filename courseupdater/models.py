"""Data models for the course updater module."""

from django.db import models
from django import forms
from catalog.models import Course

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

    def __unicode__(self):
        base = u"Catalog update for {} on {}".format(self.semester, self.creation_date)
        if self.is_completed:
            base += u" (completed)"
        elif self.is_staged:
            base += u" (staged)"
        elif self.is_started:
            base += u" ({:.2f}% complete - {})".format(self.progress, self.progress_message)
        return base

class CatalogUpdateStartForm(forms.Form):
    """A form that allows the web user to start a catalog update for the data
    in a given semester."""

    semester = forms.CharField(label='Semester',
                               max_length=30,
                               widget=forms.TextInput(attrs={
                                   'class': 'input-field',
                                   'placeholder': 'e.g. fall-2019'
                               }))

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
    """A form that lets the user register the current catalog update for
    deployment at the next database refresh. No fields are required here, as
    the submission of the form is sufficient."""
    pass

class CatalogCorrection(Course):
    """Represents a correction to the catalog. Inherits from catalog.Course, so
    has the ability to override any field on the course."""

    date_added = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=25, null=True)

    def __unicode__(self):
        return u"Correction to {} by {} on {}".format(
            self.subject_id, self.author, self.date_added)

class CatalogCorrectionForm(forms.ModelForm):
    """A form that allows users to input values for the catalog correction.
    Currently only a subset of fields are supported by this form."""

    class Meta:
        model = CatalogCorrection
        fields = ["subject_id", "title", "parent", "children", "description",
                  "instructors", "gir_attribute", "communication_requirement",
                  "hass_attribute", "total_units", "lecture_units",
                  "lab_units", "preparation_units", "design_units",
                  "offered_fall", "offered_IAP", "offered_spring",
                  "offered_summer", "is_variable_units", "is_half_class"]
        labels = {
            "gir_attribute": "GIR Attribute (e.g. PHY1, REST)",
            "communication_requirement": "Communication Requirement (e.g. CI-H)",
            "hass_attribute": "HASS Attribute (comma-separated)",
            "is_variable_units": "Variable units",
            "is_half_class": "Half class"
        }
        widgets = {
            "description": forms.TextInput,
            "instructors": forms.TextInput,
            "offered_fall": forms.CheckboxInput,
            "offered_IAP": forms.CheckboxInput,
            "offered_spring": forms.CheckboxInput,
            "offered_summer": forms.CheckboxInput,
        }
