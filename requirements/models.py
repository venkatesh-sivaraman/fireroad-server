from __future__ import unicode_literals

from django.db import models
from django import forms
from .reqlist import JSONConstants, RequirementsStatement, undecorated_component, unwrapped_component, SyntaxConstants, THRESHOLD_TYPE_GTE, CRITERION_SUBJECTS

# Create your models here.
class RequirementsList(RequirementsStatement):
    """Describes a requirements list document (for example, major3, minorWGS).
    The requirements list document has a variety of titles of different lengths,
    as well as raw string contents in the requirements list format. It can also
    parse the raw contents and store its requirements statements as
    RequirementsStatement objects."""

    list_id = models.CharField(max_length=25)
    short_title = models.CharField(max_length=50, default="")
    medium_title = models.CharField(max_length=100, default="")
    title_no_degree = models.CharField(max_length=250, default="")
    #title = models.CharField(max_length=250, default="")

    contents = models.CharField(max_length=10000, default="")
    catalog_url = models.CharField(max_length=150, default="")

    #description = models.TextField(null=True)

    def __unicode__(self):
        return u"{} - {}".format(self.short_title, self.title)

    def to_json_object(self, full=True, child_fn=None):
        """Encodes this requirements list into a dictionary that can be sent
        as JSON. If full is False, only returns the metadata about the requirements
        list. See the documentation of RequirementsStatement.to_json_object() for
        info about child_fn."""
        base = {
            JSONConstants.list_id: self.list_id,
            JSONConstants.short_title: self.short_title,
            JSONConstants.medium_title: self.medium_title,
            JSONConstants.title: self.title,
            JSONConstants.title_no_degree: self.title_no_degree
        }
        if full:
            if self.requirements.exists():
                base[JSONConstants.requirements] = [child_fn(r) if child_fn is not None else r.to_json_object() for r in self.requirements.all()]
            base[JSONConstants.description] = self.description if self.description is not None else ""
            if self.catalog_url is not None and len(self.catalog_url) > 0:
                base[JSONConstants.catalog_url] = self.catalog_url

        return base

    def parse(self, contents_str, full=True):
        """Parses the given contents string, using only the header if full is
        False, or otherwise the entire requirements file. The RequirementsList
        must be created using the RequirementsList.objects.create() method or
        have already been saved prior to calling this method."""

        lines = contents_str.split('\n')
        # Remove full-line comments and strip newlines
        lines = [l.strip() for l in lines if l.find(SyntaxConstants.comment_character) != 0]
        # Remove partial-line comments
        lines = [l[:l.find(SyntaxConstants.comment_character)] if SyntaxConstants.comment_character in l else l for l in lines]

        # First line is the header
        first = lines.pop(0)
        header_comps = [comp.strip() for comp in first.split('#,#')]
        if len(header_comps):
            self.short_title = header_comps.pop(0)
        if len(header_comps):
            self.medium_title = header_comps.pop(0)
        if len(header_comps) > 1:
            self.title_no_degree = header_comps.pop(0)
            self.title = header_comps.pop(0)
        elif len(header_comps) > 0:
            self.title = header_comps.pop(0)

        while len(header_comps) > 0:
            comp = header_comps.pop(0)
            if "=" in comp:
                arg_comps = comp.split("=")
                if len(arg_comps) != 2:
                    print("{}: Unexpected number of = symbols in first line argument".format(self.list_id))
                    continue
                if arg_comps[0].strip() == "threshold":
                    self.threshold_type = THRESHOLD_TYPE_GTE
                    try:
                        self.threshold_cutoff = int(arg_comps[1])
                    except:
                        print("{}: Invalid threshold argument {}".format(self.list_id, arg_comps[1]))
                        continue
                    self.threshold_criterion = CRITERION_SUBJECTS
                elif arg_comps[0].strip() == "url":
                    self.catalog_url = arg_comps[1].strip()


        self.contents = contents_str

        if not full:
            return

        # Second line is the description of the course
        desc_line = lines.pop(0)
        if len(desc_line) > 0:
            self.description = desc_line.replace("\\n", "\n")

        self.save()
        if len(lines) == 0:
            print("{}: Reached end of file early!".format(self.list_id))
            return
        if len(lines[0]) != 0:
            print("{}: Third line isn't empty (contains \"{}\")".format(self.list_id, lines[0]))
            return

        lines.pop(0)

        # Parse top-level list
        top_level_sections = []
        while len(lines) > 0 and len(lines[0]) > 0:
            if lines.count <= 2:
                print("{}: Not enough lines for top-level sections - need variable names and descriptions on two separate lines.".format(self.list_id))
                return

            var_name = undecorated_component(lines.pop(0))
            description = undecorated_component(lines.pop(0).replace("\\n", "\n"))

            if SyntaxConstants.declaration_character in var_name or SyntaxConstants.declaration_character in description:
                print("{}: Encountered ':=' symbol in top-level section. Maybe you forgot the required empty line after the last section's description line?".format(self.list_id))
            top_level_sections.append((var_name, description))

        if len(lines) == 0:
            return
        lines.pop(0)

        # Parse variable declarations
        variables = {}
        while len(lines) > 0:
            current_line = lines.pop(0)
            if len(current_line) == 0:
                continue
            if SyntaxConstants.declaration_character not in current_line:
                print("{}: Unexpected line: {}".format(self.list_id, current_line))
                continue
            comps = current_line.split(SyntaxConstants.declaration_character)
            if len(comps) != 2:
                print("{}: Can't have more than one occurrence of \"{}\" on a line".format(self.list_id, SyntaxConstants.declaration_character))
                continue

            declaration = comps[0]
            statement_title = ""
            if SyntaxConstants.variable_declaration_separator in declaration:

                index = declaration.find(SyntaxConstants.variable_declaration_separator)
                variable_name = undecorated_component(declaration[:index])
                statement_title = undecorated_component(declaration[index + len(SyntaxConstants.variable_declaration_separator):])
            else:
                variable_name = undecorated_component(comps[0])

            statement = RequirementsStatement.initialize(statement_title, comps[1])
            variables[variable_name] = statement

        for name, description in top_level_sections:
            if name not in variables:
                print("{}: Undefined variable: {}".format(self.list_id, name))
                return

            req = variables[name]
            req.description = description
            req.list = self
            req.parent = self
            req.substitute_variables(variables)

# Deployment

REQUEST_TYPE_EDIT = "Edit"
REQUEST_TYPE_CREATE = "Create"

class DeployForm(forms.Form):
    email_address = forms.CharField(label='Editor Email', max_length=100, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Email address'}))
    summary = forms.CharField(label='Summary of Changes', max_length=2000, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Summary of changes...'}))

class Deployment(models.Model):
    author = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    summary = models.CharField(max_length=2000)
    date_executed = models.DateTimeField(null=True)

    def __unicode__(self):
        return u"{}Deployment by {} at {} ({} edits): {}".format("(Pending) " if self.date_executed is None else "", self.author, self.timestamp, self.edit_requests.count(), self.summary)

# Edit requests

class EditForm(forms.Form):
    is_committing = forms.BooleanField(label='commit')
    email_address = forms.CharField(label='Email address', max_length=100, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Email address'}))
    new_list_id = forms.CharField(label='List ID', max_length=15, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'List ID (e.g. major2)'}))
    reason = forms.CharField(label='Reason for submission', max_length=2000, widget=forms.TextInput(attrs={'class': 'input-field', 'placeholder': 'Reason for submission...'}))
    contents = forms.CharField(label='contents', max_length=10000, widget=forms.HiddenInput(), required=False)

class EditRequest(models.Model):
    type = models.CharField(max_length=10)
    list_id = models.CharField(max_length=15, default="")
    email_address = models.CharField(max_length=100)
    reason = models.CharField(max_length=2000)
    original_contents = models.TextField(null=True)
    contents = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    committed = models.BooleanField(default=False)
    deployment = models.ForeignKey(Deployment, null=True, on_delete=models.SET_NULL, related_name='edit_requests')

    def __unicode__(self):
        return u"{}{}{} request for '{}' by {}: {}".format("(Resolved) " if self.resolved else "", "(Committed) " if self.committed else "", self.type, self.list_id, self.email_address, self.reason)
