from django.db import models
import re

CONNECTION_TYPE_ALL = "all"
CONNECTION_TYPE_ANY = "any"
CONNECTION_TYPE_NONE = "none"

THRESHOLD_TYPE_LT = "LT"
THRESHOLD_TYPE_LTE = "LTE"
THRESHOLD_TYPE_GT = "GT"
THRESHOLD_TYPE_GTE = "GTE"

CRITERION_SUBJECTS = "subjects"
CRITERION_UNITS = "units"

DEFAULT_UNIT_COUNT = 12

def top_level_separator_regex(separator):
    """Returns a regex that matches separators in only the top level of a string
    (i.e. no separators found within parenthetical statements)."""
    sep_pattern = re.escape(separator)
    return sep_pattern + r'(?![^\(]*\))'

modifier_regex = "\\{(.*?)\\}(?![^\\(]*\\))"

def undecorated_component(component):
    """Returns the given component string without leading/trailing whitespace
    and quotation marks."""
    return component.strip(" \t\r\n\"'")

def unwrapped_component(component):
    """Returns the given component string without leading/trailing whitespace
    and unwrapped out of any parenthesis pairs."""
    unwrapping = component.strip(" \t\n\r")
    while unwrapping[0] == "(" and unwrapping[-1] == ")":
        unwrapping = unwrapping[1:-1]
    return unwrapping

def components_separated_by_regex(string, regex):
    return [undecorated_component(comp) for comp in re.split(regex, string)]

class SyntaxConstants:
    """Static constants for use in parsing."""
    all_separator = ","
    any_separator = "/"
    comment_character = "%%"
    declaration_character = ":="
    variable_declaration_separator = ","
    header_separator = "#,#"

    threshold_parameter = "threshold="
    url_parameter = "url="

class JSONConstants:
    """Static constants for use in output to JSON."""
    # Common keys
    title = "title"
    description = "desc"

    # Top level keys in a RequirementsList JSON dictionary
    list_id = "list-id"
    short_title = "short-title"
    medium_title = "medium-title"
    title_no_degree = "title-no-degree"
    # And requirements

    # Top level keys in a RequirementsStatement JSON dictionary
    requirement = "req" # string requirement (if not present, see reqs)
    is_plain_string = "plain-string" # optional boolean
    requirements = "reqs" # list of RequirementsStatement objects (if not present, see req)
    connection_type = "connection-type" # exists if requirements exists, and is "all", "any", or "none"
    threshold = "threshold" # optional dictionary (see below)
    distinct_threshold = "distinct-threshold" # optional dictionary (see below)
    thresh_description = "threshold-desc" # User-facing string describing the thresholds (if applicable)

    # Keys within the threshold or distinct-threshold dictionaries
    thresh_type = "type"
    thresh_cutoff = "cutoff"
    thresh_criterion = "criterion"

class RequirementsStatement(models.Model):
    """Represents a single requirements statement, encompassing a series of
    subjects or other requirements statements connected by AND or OR."""

    #list = models.ForeignKey("RequirementsList", on_delete=models.CASCADE, related_name="requirements", null=True)

    title = models.CharField(max_length=250, null=True)
    description = models.TextField(null=True)
    requirement = models.CharField(max_length=100, null=True)
    parent = models.ForeignKey("self", null=True, related_name="requirements", on_delete=models.CASCADE)
    is_plain_string = models.BooleanField(default=False)

    connection_type = models.CharField(max_length=10, choices=(
        (CONNECTION_TYPE_ALL, "all"),
        (CONNECTION_TYPE_ANY, "any"),
        (CONNECTION_TYPE_NONE, "none")
    ), default=CONNECTION_TYPE_ALL)

    # Threshold
    threshold_type = models.CharField(max_length=4, choices=(
        (THRESHOLD_TYPE_LT, "less than"),
        (THRESHOLD_TYPE_LTE, "at most"),
        (THRESHOLD_TYPE_GT, "greater than"),
        (THRESHOLD_TYPE_GTE, "at least")
    ), null=True)
    threshold_cutoff = models.IntegerField(default=0, null=False)
    threshold_criterion = models.CharField(max_length=10, choices=(
        (CRITERION_SUBJECTS, "subjects"),
        (CRITERION_UNITS, "units")
    ), default=CRITERION_SUBJECTS)

    # Distinct threshold
    distinct_threshold_type = models.CharField(max_length=4, choices=(
        (THRESHOLD_TYPE_LT, "less than"),
        (THRESHOLD_TYPE_LTE, "at most"),
        (THRESHOLD_TYPE_GT, "greater than"),
        (THRESHOLD_TYPE_GTE, "at least")
    ), null=True)
    distinct_threshold_cutoff = models.IntegerField(default=0, null=False)
    distinct_threshold_criterion = models.CharField(max_length=10, choices=(
        (CRITERION_SUBJECTS, "subjects"),
        (CRITERION_UNITS, "units")
    ), default=CRITERION_SUBJECTS)

    def threshold_description(self):
        """Returns a string description of this statement's threshold."""
        ret = ""
        if self.requirement is not None and self.connection_type == CONNECTION_TYPE_ALL and self.threshold_type is None:
            return ret

        if self.threshold_type is not None and self.threshold_cutoff != 1:
            if self.threshold_cutoff > 1:
                if self.threshold_type == THRESHOLD_TYPE_LTE:
                    ret = "select at most {}".format(self.threshold_cutoff)
                elif self.threshold_type == THRESHOLD_TYPE_LT:
                    ret = "select at most {}".format(self.threshold_cutoff - 1)
                elif self.threshold_type == THRESHOLD_TYPE_GTE:
                    ret = "select any {}".format(self.threshold_cutoff)
                elif self.threshold_type == THRESHOLD_TYPE_GT:
                    ret = "select any {}".format(self.threshold_cutoff + 1)

                if self.threshold_criterion == CRITERION_UNITS:
                    ret += " units"
                elif self.threshold_criterion == CRITERION_SUBJECTS and self.connection_type == CONNECTION_TYPE_ALL:
                    ret += " subjects"
            elif self.threshold_cutoff == 0 and self.connection_type == CONNECTION_TYPE_ANY:
                ret = "optional - select any"

        elif self.connection_type == CONNECTION_TYPE_ALL:
            ret = "select all"
        elif self.connection_type == CONNECTION_TYPE_ANY:
            if self.requirements.all().exists() and len(self.requirements.all()) == 2:
                ret = "select either"
            else:
                ret = "select any"

        if self.distinct_threshold_type is not None and self.distinct_threshold_cutoff > 0:
            if self.distinct_threshold_type == THRESHOLD_TYPE_LTE:
                category_text = "categories" if self.distinct_threshold_cutoff != 1 else "category"
                ret += " from at most {} {}".format(self.distinct_threshold_cutoff, category_text)
            elif self.distinct_threshold_type == THRESHOLD_TYPE_LT:
                category_text = "categories" if self.distinct_threshold_cutoff - 1 != 1 else "category"
                ret += " from at most {} {}".format(self.distinct_threshold_cutoff - 1, category_text)
            elif self.distinct_threshold_type == THRESHOLD_TYPE_GTE:
                category_text = "categories" if self.distinct_threshold_cutoff != 1 else "category"
                ret += " from at least {} {}".format(self.distinct_threshold_cutoff, category_text)
            elif self.distinct_threshold_type == THRESHOLD_TYPE_GT:
                category_text = "categories" if self.distinct_threshold_cutoff + 1 != 1 else "category"
                ret += " from at least {} {}".format(self.distinct_threshold_cutoff + 1, category_text)

        return ret

    def __str__(self):
        thresh_desc = self.threshold_description()
        if self.requirement is not None:
            return "{}{}{}".format(self.title + ": " if self.title is not None else "", self.requirement, " (" + thresh_desc + ")" if len(thresh_desc) > 0 else "")
        elif self.requirements.all().exists():
            connection_string = self.get_connection_type_display()
            if len(thresh_desc) > 0:
                connection_string += " ({})".format(thresh_desc)

            return "{}{} of \n".format(self.title + ": " if self.title is not None else "", connection_string) + "\n".join([str(r) for r in self.requirements.all()])

        return self.title if self.title is not None else "No title"

    def to_json_object(self, full=True, child_fn=None):
        """Encodes this requirements statement into a serializable object that can
        be dumped to JSON.

        If this statement has child requirements, it uses the child_fn to output
        the JSON for each child. If child_fn is None, uses the to_json_object()
        on the child requirements; if not, it should be a function that takes a
        RequirementsStatement and produces a JSON object describing it.

        The full keyword argument is currently not used by RequirementsStatement."""

        base = {}
        if self.title is not None and len(self.title) > 0:
            base[JSONConstants.title] = self.title
        if self.description is not None and len(self.description) > 0:
            base[JSONConstants.description] = self.description

        if self.threshold_type is not None:
            base[JSONConstants.threshold] = {
                JSONConstants.thresh_type: self.threshold_type,
                JSONConstants.thresh_cutoff: self.threshold_cutoff,
                JSONConstants.thresh_criterion: self.threshold_criterion,
            }
        if self.distinct_threshold_type is not None:
            base[JSONConstants.distinct_threshold] = {
                JSONConstants.thresh_type: self.distinct_threshold_type,
                JSONConstants.thresh_cutoff: self.distinct_threshold_cutoff,
                JSONConstants.thresh_criterion: self.distinct_threshold_criterion,
            }

        desc = self.threshold_description()
        if len(desc) > 0:
            base[JSONConstants.thresh_description] = desc
        if self.is_plain_string:
            base[JSONConstants.is_plain_string] = self.is_plain_string

        if self.requirement is not None:
            base[JSONConstants.requirement] = self.requirement
        elif self.requirements.exists():
            base[JSONConstants.requirements] = [(child_fn(r) if child_fn is not None else r.to_json_object()) for r in self.requirements.all()]
            base[JSONConstants.connection_type] = self.connection_type

        return base

    ### Parsing methods

    def separate_top_level_items(self, text):
        """Returns a list of the top-level substituents of the given requirements
        statement, as well as a connection type string."""

        trimmed = text.strip(" \t\n\r")
        if len(trimmed) >= 4 and trimmed[:2] == '""' and trimmed[-2:] == '""':
            return ([undecorated_component(trimmed)], CONNECTION_TYPE_NONE)

        components = []
        connection_type = CONNECTION_TYPE_ALL
        current_indent_level = 0

        for character in trimmed:
            if character == SyntaxConstants.all_separator and current_indent_level == 0:
                connection_type = CONNECTION_TYPE_ALL
                components.append("")
            elif character == SyntaxConstants.any_separator and current_indent_level == 0:
                connection_type = CONNECTION_TYPE_ANY
                components.append("")
            else:
                if character == "(":
                    current_indent_level += 1
                elif character == ")":
                    current_indent_level -= 1
                if len(components) == 0:
                    components.append("")
                components[-1] += character

        return ([undecorated_component(s) for s in components], connection_type)

    def parse_modifier_component(self, modifier):
        """Returns a tuple indicating the threshold type, the cutoff, and criterion."""

        # Of the form >=x, <=x, >x, or <x
        threshold_type = THRESHOLD_TYPE_GTE
        cutoff = 1
        criterion = CRITERION_SUBJECTS

        if ">=" in modifier:
            threshold_type = THRESHOLD_TYPE_GTE
        elif "<=" in modifier:
            threshold_type = THRESHOLD_TYPE_LTE
        elif ">" in modifier:
            threshold_type = THRESHOLD_TYPE_GT
        elif "<" in modifier:
            threshold_type = THRESHOLD_TYPE_LT
        number_string = modifier.replace(">", "").replace("<", "").replace("=", "")
        if "u" in number_string:
            criterion = CRITERION_UNITS
            number_string = number_string.replace("u", "")

        try:
            cutoff = int(number_string)
        except ValueError:
            print("Couldn't get number out of modifier string {}".format(modifier))

        return (threshold_type, cutoff, criterion)

    def parse_modifier(self, modifier):
        """Applies the given modifier to this RequirementsStatement object."""

        if "|" in modifier:
            comps = modifier.split("|")
            if len(comps) != 2:
                print("Unsupported number of components in modifier string: {}".format(modifier))
                return

            if len(comps[0]) > 0:
                type, cutoff, criterion = self.parse_modifier_component(comps[0])
                self.threshold_type = type
                self.threshold_cutoff = cutoff
                self.threshold_criterion = criterion
            if len(comps[1]) > 0:
                type, cutoff, criterion = self.parse_modifier_component(comps[1])
                self.distinct_threshold_type = type
                self.distinct_threshold_cutoff = cutoff
                self.distinct_threshold_criterion = criterion

        elif len(modifier) > 0:
            type, cutoff, criterion = self.parse_modifier_component(modifier)
            self.threshold_type = type
            self.threshold_cutoff = cutoff
            self.threshold_criterion = criterion

    def substitute_variables(self, dictionary):
        """Substitutes the variable names in this requirement using the given
        dictionary of names to requirement statements."""
        if self.requirement is not None:
            # This requirement might be a variable
            if self.requirement in dictionary:
                sub_req = dictionary[self.requirement]
                sub_req.parent = self
                sub_req.substitute_variables(dictionary)
                self.requirement = None
        elif self.requirements.exists():
            reqs_to_delete = set()
            for i, statement in enumerate(self.requirements.all()):
                if statement.requirement is not None and statement.requirement in dictionary:
                    sub_req = dictionary[statement.requirement]
                    reqs_to_delete.add(statement)
                    sub_req.parent = self
                    sub_req.substitute_variables(dictionary)
                else:
                    statement.substitute_variables(dictionary)
            for req_to_delete in reqs_to_delete:
                req_to_delete.delete()

        self.save()

    @staticmethod
    def initialize(title, contents, parent=None):
        """Initializes a new requirements statement with the given title and
        requirement string. Parses the requirements statement."""
        statement = RequirementsStatement.objects.create(title=title, parent=parent)
        statement.list = list
        statement.parse_string(contents)
        statement.save()
        return statement

    @staticmethod
    def from_string(string, parent=None):
        """Saves and returns the statement object resulting from parsing the
        given string."""
        statement = RequirementsStatement.objects.create()
        statement.parent = parent
        statement.parse_string(string)
        statement.save()
        return statement

    def parse_string(self, string):
        """Parses the given requirements statement and sets self's properties
        accordingly."""
        filtered_statement = string
        modifier_match = re.search(modifier_regex, filtered_statement)
        if modifier_match is not None:
            self.parse_modifier(modifier_match.group(1))
            filtered_statement = re.sub(modifier_regex, "", filtered_statement)

        components, connection_type = self.separate_top_level_items(filtered_statement)
        if self.threshold_type is not None and self.threshold_cutoff == 0 and self.threshold_type == THRESHOLD_TYPE_GTE:
            self.connection_type = CONNECTION_TYPE_ANY
        else:
            self.connection_type = connection_type
        self.is_plain_string = (connection_type == CONNECTION_TYPE_NONE)

        if len(components) == 1 or self.is_plain_string:
            self.requirement = components[0]
        else:
            for c in components:
                RequirementsStatement.from_string(unwrapped_component(c), parent=self)
