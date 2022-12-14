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

    # Options for the parse
    designate_virtual_status = models.BooleanField(default=False)

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
    designate_virtual_status = forms.BooleanField(label='Designate subject virtual status',
                                                  widget=forms.CheckboxInput(attrs={'class':
                                                                                    'filled-in'}),
                                                  initial=False,
                                                  required=False)

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

class CatalogCorrection(Course):
    date_added = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=25, null=True)

    def __str__(self):
        return "Correction to {} by {} on {}".format(self.subject_id, self.author, self.date_added)

class CatalogCorrectionForm(forms.ModelForm):

    class Meta:
        model = CatalogCorrection
        fields = ["subject_id", "title", "parent", "children", "description", "instructors", "gir_attribute", "communication_requirement", "hass_attribute", "equivalent_subjects", "old_id", "total_units", "lecture_units", "lab_units", "preparation_units", "design_units", "offered_fall", "offered_IAP", "offered_spring", "offered_summer", "is_variable_units", "is_half_class"]
        labels = {
            "gir_attribute": "GIR Attribute (e.g. PHY1, REST)",
            "communication_requirement": "Communication Requirement (e.g. CI-H)",
            "hass_attribute": "HASS Attribute (comma-separated)",
            "is_variable_units": "Variable units",
            "is_half_class": "Half class",
            "old_id": "Old subject ID"
        }
        widgets = {
            "description": forms.TextInput,
            "instructors": forms.TextInput,
            "offered_fall": forms.CheckboxInput,
            "offered_IAP": forms.CheckboxInput,
            "offered_spring": forms.CheckboxInput,
            "offered_summer": forms.CheckboxInput,
        }
