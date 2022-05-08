from django.db import models
from django import forms
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.template.defaultfilters import filesizeformat

import os
import magic
import shutil
from uuid import uuid4

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
        return u"{}Deployment by {} at {} ({} edits): {}".format("(Pending) " if self.date_executed is None else "", self.author, self.timestamp, self.syllabus_submissions.count(), self.summary)

# Source: https://stackoverflow.com/a/27916582
@deconstructible
class FileValidator(object):
    error_messages = {
     'max_size': ("File size must not be greater than %(max_size)s."
                  " Your file size is %(size)s."),
     'min_size': ("File size must not be less than %(min_size)s. "
                  "Your file size is %(size)s."),
     'content_type': "Files of type %(content_type)s are not supported.",
    }

    def __init__(self, max_size=None, min_size=None, content_types=()):
        self.max_size = max_size
        self.min_size = min_size
        self.content_types = content_types

    def __call__(self, data):
        if self.max_size is not None and data.size > self.max_size:
            params = {
                'max_size': filesizeformat(self.max_size),
                'size': filesizeformat(data.size),
            }
            raise ValidationError(self.error_messages['max_size'],
                                   'max_size', params)

        if self.min_size is not None and data.size < self.min_size:
            params = {
                'min_size': filesizeformat(self.min_size),
                'size': filesizeformat(data.size)
            }
            raise ValidationError(self.error_messages['min_size'],
                                   'min_size', params)

        if self.content_types:
            content_type = magic.from_buffer(data.read(), mime=True)
            data.seek(0)

            if content_type not in self.content_types:
                params = { 'content_type': content_type }
                raise ValidationError(self.error_messages['content_type'],
                                   'content_type', params)

    def __eq__(self, other):
        return (
            isinstance(other, FileValidator) and
            self.max_size == other.max_size and
            self.min_size == other.min_size and
            self.content_types == other.content_types
        )

def validate_subject_id(subject_id):
    from catalog.models import Course
    if Course.objects.filter(subject_id=subject_id).count() == 0:
        raise ValidationError(u'Must provide a valid subject ID')

class SyllabusForm(forms.Form):
    is_committing = forms.BooleanField(label='commit')
    email_address = forms.CharField(label='Email address', max_length=100, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Email address'}))
    semester = forms.ChoiceField(label='Semester', choices=SEMESTER_CHOICES, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Semester (e.g. Fall)'}))
    year = forms.CharField(label='Year', max_length=4, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Year (e.g. 2022)'}))
    subject_id = forms.CharField(label='Course Number', max_length=20, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Course number (e.g. 18.01)'}), validators=[validate_subject_id])
    file = forms.FileField(label='Syllabus File', widget=forms.ClearableFileInput(attrs={'class': 'input-field', 'accept': 'application/pdf'}), validators=[FileValidator(max_size=1024*1024*5, content_types=('application/pdf',))])

def rename_file(inst, filename):
    upload_to = 'syllabus/'
    _, ext = os.path.splitext(filename)
    new_name = 'syllabus_' + inst.subject_id.replace('.', '_') + '_' + inst.semester + '_' + inst.year + ext

    fss = FileSystemStorage()
    filepath = fss.get_available_name(os.path.join(upload_to, new_name))
    return filepath

class SyllabusSubmission(models.Model):
    email_address = models.CharField(max_length=100)
    semester = models.CharField(max_length=6, choices=SEMESTER_CHOICES)
    year = models.CharField(max_length=4)
    subject_id = models.CharField(max_length=20)
    file = models.FileField(upload_to=rename_file)
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    committed = models.BooleanField(default=False)
    deployment = models.ForeignKey(SyllabusDeployment, null=True, on_delete=models.SET_NULL, related_name='syllabus_submissions')

    def __unicode__(self):
        return u"{}{}{} {} {} syllabus by {}".format("(Resolved) " if self.resolved else "", "(Committed) " if self.committed else "", self.subject_id, self.semester, self.year, self.email_address)

    def update_file_name(self, copy=True):
        current_filepath = self.file.path
        current_filename = os.path.basename(current_filepath)
        _, ext = os.path.splitext(current_filepath)
        upload_to = 'syllabus/'

        proper_file_prefix = 'syllabus_' + self.subject_id.replace('.', '_') + '_' + self.semester + '_' + self.year

        fss = FileSystemStorage()
        filepath = fss.get_available_name(os.path.join(upload_to, proper_file_prefix + ext))
        filepath = os.path.join(settings.MEDIA_ROOT, filepath)

        if current_filename.startswith(proper_file_prefix):
            if copy:
                shutil.copyfile(current_filepath, filepath)
                self.file = fss.open(filepath)
                self.save()
        else:
            if copy:
                shutil.copyfile(current_filepath, filepath)
                self.file = fss.open(filepath)
                self.save()
            else:
                shutil.move(current_filepath, filepath)
                self.file = fss.open(filepath)
                self.save()

    def remove_file(self):
        os.remove(self.file.path)

class Syllabus(models.Model):
    semester = models.CharField(max_length=6, choices=SEMESTER_CHOICES)
    year = models.CharField(max_length=4)
    subject_id = models.CharField(max_length=20)
    file = models.FileField()
    timestamp = models.DateTimeField(null=False)

    def __unicode__(self):
        return u"{} {} {} syllabus".format(self.subject_id, self.semester, self.year)

    def to_json_object(self):
        return {
            'semester': self.semester,
            'year': self.year,
            'subject_id': self.subject_id,
            'file_url': settings.MY_BASE_URL + self.file.url,
            'id': self.pk
        }
