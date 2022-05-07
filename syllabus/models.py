from django.db import models
from django import forms

SEMESTER_CHOICES = [
    ('Fall', 'fall'),
    ('IAP', 'iap'),
    ('Spring', 'spring'),
    ('Summer', 'summer')
]

class DeploySyllabusForm(forms.Form):
    email_address = forms.CharField(label='Editor Email', max_length=100, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Email address'}))
    summary = forms.CharField(label='Summary of Uploads', max_length=2000, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Summary of uploads...'}))

class SyllabusDeployment(models.Model):
    author = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    summary = models.CharField(max_length=2000)
    date_executed = models.DateTimeField(null=True)

    def __unicode__(self):
        return u"{}Deployment by {} at {} ({} edits): {}".format("(Pending) " if self.date_executed is None else "", self.author, self.timestamp, self.edit_requests.count(), self.summary)

class SyllabusForm(forms.Form):
    is_committing = forms.BooleanField(label='commit')
    email_address = forms.CharField(label='Email address', max_length=100, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Email address'}))
    semester = forms.ChoiceField(label='Semester', choices=SEMESTER_CHOICES, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Semester (e.g. Fall)'}))
    year = forms.CharField(label='Year', max_length=4, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Year (e.g. 2022)'}))
    subject_id = forms.CharField(label='Course Number', max_length=20, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Course number (e.g. 18.01)'}))
    file = forms.FileField(label='Syllabus File', widget=forms.FileInput(attrs={'class': 'input-field'}))

class SyllabusSubmission(models.Model):
    email_address = models.CharField(max_length=100)
    semester = models.CharField(max_length=6, choices=SEMESTER_CHOICES)
    year = models.CharField(max_length=4)
    subject = models.ForeignKey('catalog.Course', on_delete=models.CASCADE, related_name='+')
    file = models.FileField(upload_to='syllabus/')
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    committed = models.BooleanField(default=False)
    deployment = models.ForeignKey(SyllabusDeployment, null=True, on_delete=models.SET_NULL, related_name='syllabus_submissions')

    def __unicode__(self):
        return u"{}{}{} request for '{}' by {}: {}".format("(Resolved) " if self.resolved else "", "(Committed) " if self.committed else "", self.type, self.subject_id, self.email_address, self.reason)
