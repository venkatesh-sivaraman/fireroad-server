from __future__ import unicode_literals

from django.db import models
from django import forms

# Create your models here.
class RequirementsList(models.Model):
    list_id = models.CharField(max_length=25)
    short_title = models.CharField(max_length=50, default="")
    medium_title = models.CharField(max_length=100, default="")
    title_no_degree = models.CharField(max_length=250, default="")
    title = models.CharField(max_length=250, default="")

    contents = models.CharField(max_length=10000, default="")

    def __str__(self):
        return self.short_title + " - " + self.title

    def parse(self, contents_str):
        lines = contents_str.split('\n')

        first = lines.pop(0)
        header_comps = first.split('#,#')
        if len(header_comps):
            self.short_title = header_comps.pop(0)
        if len(header_comps):
            self.medium_title = header_comps.pop(0)
        if len(header_comps) > 1:
            self.title_no_degree = header_comps.pop(0)
            self.title = header_comps.pop(0)
        elif len(header_comps) > 0:
            self.title = header_comps.pop(0)

        self.contents = contents_str

class EditForm(forms.Form):
    email_address = forms.CharField(label='Email address', max_length=100, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Email address'}))
    reason = forms.CharField(label='Reason for submission', max_length=2000, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Reason for submission...'}))
    contents = forms.CharField(label='contents', max_length=10000, widget=forms.HiddenInput(), required=False)

class EditRequest(models.Model):
    type = models.CharField(max_length=10)
    email_address = models.CharField(max_length=100)
    reason = models.CharField(max_length=2000)
    contents = models.CharField(max_length=10000)
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return "{}{} request by {} at {}: {}".format("(Resolved) " if self.resolved else "", self.type, self.email_address, self.timestamp, self.reason)
