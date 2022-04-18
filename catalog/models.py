from __future__ import unicode_literals
from django.core.exceptions import ObjectDoesNotExist

from django.db import models
from common.models import Student
from catalog_parse.utils.catalog_constants import *

class Attribute:
    """
    Class that describes an attribute.

    Each attribute subclass has:
    - attributes: a list of valid attributes
    - multiple: whether it makes sense for multiple classes with this attribute
      to exist in the same list of classes
    """
    def __init__(self, req, needs_unique_id):
        self.requirement = req
        self.course = Course(id=req)
        self.needs_unique_id = needs_unique_id

    @classmethod
    def parse_req(cls, req):
        """Takes in a possible requirement, returns an instance of a
        specific attribute class if that requirement is valid, otherwise None"""
        if req in cls.attributes:
            return cls(req, cls.multiple)
        return None

    @classmethod
    def combine(cls, attrs, unique_id):
        """Combines attributes to form a hybrid attribute.  Their courses
        are combined together to form a course that satisfies each attribute's
        requirement, and a unique id is assigned to the course only if it makes
        sense for each attribute to exist multiple times in a list of courses"""
        new_attr = cls(" ".join(map(lambda a: a.requirement,attrs)),True)
        for attr in attrs:
            new_attr.course = attr.modify_course(new_attr.course)
            new_attr.needs_unique_id = new_attr.needs_unique_id and attr.needs_unique_id
        if new_attr.needs_unique_id:
            new_attr.course.id += str(unique_id)
        new_attr.course.subject_id = new_attr.requirement
        return new_attr

class GIRAttribute(Attribute):
    attributes = ["REST", "LAB2", "LAB", "CAL1", "CAL2", "CHEM", "BIOL", "PHY1", "PHY2"]
    #most GIR attributes should only be once (e.g. CAL1), but some can be used twice (e.g. REST) - changed in __init__
    multiple = False
    def __init__(self, req, needs_unique_id):
        if(req == "REST" or req == "LAB2" or req == "LAB"):
            needs_unique_id = True
        Attribute.__init__(self, req, needs_unique_id)

    def modify_course(self, course):
        course.gir_attribute = self.requirement
        return course

class HASSAttribute(Attribute):
    attributes = ["HASS-S", "HASS-H", "HASS-A","HASS"]
    #There could be many HASS classes in a schedule
    multiple = True
    def modify_course(self, course):
        course.hass_attribute = self.requirement
        return course

class CommunicationAttribute(Attribute):
    attributes = ["CI-H", "CI-HW"]
    #There could be many CI classes in a schedule
    multiple = True
    def modify_course(self, course):
        course.communication_requirement = self.requirement
        return course

class CourseFields:
    subject_id = "subject_id"
    title = "title"
    level = "level"
    description = "description"
    department = "department"
    equivalent_subjects = "equivalent_subjects"
    joint_subjects = "joint_subjects"
    meets_with_subjects = "meets_with_subjects"
    prerequisites = "prerequisites"
    corequisites = "corequisites"
    gir_attribute = "gir_attribute"
    communication_requirement = "communication_requirement"
    hass_attribute = "hass_attribute"
    instructors = "instructors"
    offered_fall = "offered_fall"
    offered_IAP = "offered_IAP"
    offered_spring = "offered_spring"
    offered_summer = "offered_summer"
    offered_this_year = "offered_this_year"
    total_units = "total_units"
    is_variable_units = "is_variable_units"
    lab_units = "lab_units"
    lecture_units = "lecture_units"
    design_units = "design_units"
    preparation_units = "preparation_units"
    pdf_option = "pdf_option"
    has_final = "has_final"
    not_offered_year = "not_offered_year"
    quarter_information = "quarter_information"
    related_subjects = "related_subjects"
    schedule = "schedule"
    virtual_status = "virtual_status"
    url = "url"
    rating = "rating"
    in_class_hours = "in_class_hours"
    out_of_class_hours = "out_of_class_hours"
    enrollment_number = "enrollment_number"
    enrollment_number = "enrollment_number"
    either_prereq_or_coreq = "either_prereq_or_coreq"
    old_id = "old_id"
    public = "public"
    creator = "creator"
    custom_color = "custom_color"
    source_semester = "source_semester"
    is_historical = "is_historical"
    parent = "parent"
    children = "children"
    is_half_class = "is_half_class"

# Tools to convert from strings to Course field values
def string_converter(value):
    return value
def float_converter(value):
    return float(value) if len(value) > 0 else 0.0
def bool_converter(value):
    return value is not None and value == "Y"
def int_converter(value):
    return int(value) if len(value) > 0 else 0
def list_converter(value):
    modified = value.replace("[J]", "").replace("\\n", "\n")
    if "#,#" in value:
        modified = modified.replace(" ", "")
    modified = modified.strip().replace(";", ",")
    if "#,#" in modified:
        sub_values = modified.split("#,#")
        return "{" + sub_values[0] + "}" + "," + sub_values[1]
    else:
        return modified

# Converts from CSV header to JSON key (and value conversion function)
CSV_HEADERS = {
    CourseAttribute.subjectID:                  (CourseFields.subject_id, string_converter),
    CourseAttribute.title:                      (CourseFields.title, string_converter),
    CourseAttribute.subjectLevel:               (CourseFields.level, string_converter),
    CourseAttribute.description:                (CourseFields.description, string_converter),
    CourseAttribute.equivalentSubjects:         (CourseFields.equivalent_subjects, list_converter),
    CourseAttribute.jointSubjects:              (CourseFields.joint_subjects, list_converter),
    CourseAttribute.meetsWithSubjects:          (CourseFields.meets_with_subjects, list_converter),
    CourseAttribute.prerequisites:              (CourseFields.prerequisites, list_converter),
    CourseAttribute.corequisites:               (CourseFields.corequisites, list_converter),
    CourseAttribute.GIR:                        (CourseFields.gir_attribute, string_converter),
    CourseAttribute.communicationRequirement:   (CourseFields.communication_requirement, string_converter),
    CourseAttribute.hassRequirement:            (CourseFields.hass_attribute, string_converter),
    CourseAttribute.instructors:                (CourseFields.instructors, list_converter),
    CourseAttribute.offeredFall:                (CourseFields.offered_fall, bool_converter),
    CourseAttribute.offeredIAP:                 (CourseFields.offered_IAP, bool_converter),
    CourseAttribute.offeredSpring:              (CourseFields.offered_spring, bool_converter),
    CourseAttribute.offeredSummer:              (CourseFields.offered_summer, bool_converter),
    CourseAttribute.totalUnits:                 (CourseFields.total_units, int_converter),
    CourseAttribute.isVariableUnits:            (CourseFields.is_variable_units, bool_converter),
    CourseAttribute.labUnits:                   (CourseFields.lab_units, int_converter),
    CourseAttribute.lectureUnits:               (CourseFields.lecture_units, int_converter),
    CourseAttribute.preparationUnits:           (CourseFields.preparation_units, int_converter),
    CourseAttribute.halfClass:                  (CourseFields.is_half_class, bool_converter),
    CourseAttribute.pdfOption:                  (CourseFields.pdf_option, bool_converter),
    CourseAttribute.hasFinal:                   (CourseFields.has_final, bool_converter),
    CourseAttribute.notOfferedYear:             (CourseFields.not_offered_year, string_converter),
    CourseAttribute.quarterInformation:         (CourseFields.quarter_information, string_converter),
    CourseAttribute.schedule:                   (CourseFields.schedule, string_converter),
    CourseAttribute.virtualStatus:              (CourseFields.virtual_status, string_converter),
    CourseAttribute.URL:                        (CourseFields.url, string_converter),
    CourseAttribute.averageRating:              (CourseFields.rating, float_converter),
    CourseAttribute.averageInClassHours:        (CourseFields.in_class_hours, float_converter),
    CourseAttribute.averageOutOfClassHours:     (CourseFields.out_of_class_hours, float_converter),
    CourseAttribute.enrollment:                 (CourseFields.enrollment_number, float_converter),
    CourseAttribute.eitherPrereqOrCoreq:        (CourseFields.either_prereq_or_coreq, bool_converter),
    CourseAttribute.oldID:                      (CourseFields.old_id, string_converter),
    CourseAttribute.sourceSemester:             (CourseFields.source_semester, string_converter),
    CourseAttribute.isHistorical:               (CourseFields.is_historical, bool_converter),
    CourseAttribute.parent:                     (CourseFields.parent, string_converter),
    CourseAttribute.children:                   (CourseFields.children, string_converter),
    "Design Units":                             (CourseFields.design_units, int_converter),
    "Related Subjects":                         (CourseFields.related_subjects, string_converter),
    "Enrollment Number":                        (CourseFields.enrollment_number, float_converter),
    "Custom Color":                             (CourseFields.custom_color, string_converter)
}

FIELD_TO_CSV = {field_name: csv_header for csv_header, (field_name, _) in CSV_HEADERS.items()}

# Create your models here.
class Course(models.Model):
    subject_id = models.CharField(db_index=True, max_length=20, null=True)
    title = models.CharField(max_length=200, null=True)

    # Differentiates users' custom subjects from catalog subjects
    public = models.BooleanField(default=False)
    creator = models.ForeignKey("common.Student", null=True, on_delete=models.CASCADE, related_name="custom_courses")
    custom_color = models.CharField(max_length=15, null=True)

    # Source semester
    source_semester = models.CharField(max_length=15, default="")
    is_historical = models.BooleanField(default=False)

    parent = models.CharField(max_length=15, null=True)
    children = models.CharField(max_length=50, null=True)

    @classmethod
    def public_courses(cls):
        return Course.objects.filter(public=True)

    @classmethod
    def make_generic(cls, subject_id, unique_id):
        """Creates a generic course that satisfies the requirements separated by
        spaces in the given subject ID, e.g. "CI-H HASS-A". Returns a Course whose
        subject ID has unique ID appended. Raises a ValueError if one or more
        generic attributes are invalid."""

        is_generic_course = False
        if "." not in subject_id:
            #potential a generic course
            #generic course could have more than one attribute, e.g. CI-H HASS-A
            subject_ids = subject_id.split(" ")
            #dict of attributes and values to add to created Course object
            matching_attributes = []
            #attributes to test for in generic course (gets a list of CourseAttributeLists properties that aren't hidden)
            tested_attributes = [GIRAttribute, HASSAttribute, CommunicationAttribute]
            is_generic_course = True
            for subject_attribute in subject_ids:
                #each spaced delimited subject attribute must be sensical
                subject_attribute_exists = False
                for attribute in tested_attributes:
                    #if the course matches a generic attribute, it is a generic course with that attribute
                    matching_attribute = attribute.parse_req(subject_attribute)
                    if matching_attribute is not None:
                        matching_attributes.append(matching_attribute)
                        subject_attribute_exists = True

                if not subject_attribute_exists:
                    is_generic_course = False

        #add all matching attributes to generic course
        if is_generic_course:
            generic_course = Attribute.combine(matching_attributes, unique_id).course
            return generic_course
        else:
            raise ValueError

    # Used to keep multiple semesters' worth of courses in the database
    catalog_semester = models.CharField(max_length=15)

    level = models.CharField(max_length=5, null=True)
    description = models.TextField(null=True)
    department = models.CharField(max_length=50, null=True)

    # Comma-separated strings
    equivalent_subjects = models.TextField(default="", null=True)
    joint_subjects = models.TextField(default="", null=True)
    meets_with_subjects = models.TextField(default="", null=True)

    def _get_courses(self, val):
        if val is None: return []
        comps = val.split(",")
        result = []
        for comp in comps:
            try:
                course = Course.public_courses().get(subject_id=comp)
                result.append(course)
            except ObjectDoesNotExist:
                continue
        return result

    def get_equivalent_subjects(self):
        return self._get_courses(self.equivalent_subjects)
    def get_joint_subjects(self):
        return self._get_courses(self.joint_subjects)
    def get_meets_with_subjects(self):
        return self._get_courses(self.meets_with_subjects)


    prerequisites = models.TextField(null=True)
    corequisites = models.TextField(null=True)
    either_prereq_or_coreq = models.BooleanField(default=False)

    # EECS subject renumbering
    old_id = models.CharField(max_length=20, null=True)

    gir_attribute = models.CharField(max_length=20, null=True)
    communication_requirement = models.CharField(max_length=30, null=True)
    hass_attribute = models.CharField(max_length=20, null=True)

    def get_hass_attributes(self):
        """Returns a list of HASS attributes stored in the hass_attribute field."""
        if not self.hass_attribute:
            return []
        return self.hass_attribute.split(",")

    instructors = models.TextField(null=True)
    offered_fall = models.BooleanField(default=False)
    offered_IAP = models.BooleanField(default=False)
    offered_spring = models.BooleanField(default=False)
    offered_summer = models.BooleanField(default=False)
    offered_this_year = models.BooleanField(default=True)

    total_units = models.IntegerField(default=0)
    is_variable_units = models.BooleanField(default=False)
    lecture_units = models.IntegerField(default=0)
    design_units = models.IntegerField(default=0)
    lab_units = models.IntegerField(default=0)
    preparation_units = models.IntegerField(default=0)
    is_half_class = models.BooleanField(default=False)
    has_final = models.BooleanField(default=False)
    pdf_option = models.BooleanField(default=False)
    not_offered_year = models.CharField(max_length=15, null=True)

    quarter_information = models.CharField(max_length=30, null=True)

    url = models.CharField(max_length=75, null=True)

    enrollment_number = models.FloatField(default=0.0)
    related_subjects = models.CharField(null=True, max_length=250)
    schedule = models.TextField(null=True)
    virtual_status = models.CharField(null=True, max_length=100)

    rating = models.FloatField(default=0.0)
    in_class_hours = models.FloatField(default=0.0)
    out_of_class_hours = models.FloatField(default=0.0)

    def __str__(self):
        return "<Course {}: {}>".format(self.subject_id, self.title)

    def to_json_object(self, full=True):
        """
        Returns a JSON object representing this course suitable for returning
        from an HTTP request. If full is False, returns only the basic metadata
        about the course.
        """
        data = {
            CourseFields.subject_id:            self.subject_id,
            CourseFields.title:                 self.title,
            CourseFields.total_units:           self.total_units,
            CourseFields.offered_fall:          self.offered_fall,
            CourseFields.offered_IAP:           self.offered_IAP,
            CourseFields.offered_spring:        self.offered_spring,
            CourseFields.offered_summer:        self.offered_summer,
            CourseFields.public:                self.public,
        }
        if self.level is not None and len(self.level) > 0:
            data[CourseFields.level] = self.level
        if self.is_historical:
            data[CourseFields.source_semester] = self.source_semester
            data[CourseFields.is_historical] = self.is_historical

        if self.custom_color is not None and len(self.custom_color) > 0:
            data[CourseFields.custom_color] = self.custom_color
        if self.creator is not None:
            data[CourseFields.creator] = self.creator.unique_id

        if self.joint_subjects is not None and len(self.joint_subjects) > 0:
            data[CourseFields.joint_subjects] = self.joint_subjects.split(",")
        if self.equivalent_subjects is not None and len(self.equivalent_subjects) > 0:
            data[CourseFields.equivalent_subjects] = self.equivalent_subjects.split(",")
        if self.meets_with_subjects is not None and len(self.meets_with_subjects) > 0:
            data[CourseFields.meets_with_subjects] = self.meets_with_subjects.split(",")

        if self.quarter_information is not None and len(self.quarter_information) > 0:
            data[CourseFields.quarter_information] = self.quarter_information
        if self.not_offered_year is not None and len(self.not_offered_year) > 0:
            data[CourseFields.not_offered_year] = self.not_offered_year

        if self.instructors is not None and len(self.instructors) > 0:
            data[CourseFields.instructors] = self.instructors.split("\n")
        if self.communication_requirement is not None and len(self.communication_requirement) > 0:
            data[CourseFields.communication_requirement] = self.communication_requirement
        if self.hass_attribute is not None and len(self.hass_attribute) > 0:
            data[CourseFields.hass_attribute] = self.hass_attribute
        if self.gir_attribute is not None and len(self.gir_attribute) > 0:
            data[CourseFields.gir_attribute] = self.gir_attribute

        if self.parent is not None and len(self.parent) > 0:
            data[CourseFields.parent] = self.parent
        if self.children is not None and len(self.children) > 0:
            data[CourseFields.children] = self.children.split(",")

        if self.virtual_status is not None and len(self.virtual_status) > 0:
            data[CourseFields.virtual_status] = self.virtual_status

        if not full: return data

        data[CourseFields.lecture_units] = self.lecture_units
        data[CourseFields.lab_units] = self.lab_units
        data[CourseFields.design_units] = self.design_units
        data[CourseFields.preparation_units] = self.preparation_units
        data[CourseFields.is_variable_units] = self.is_variable_units
        data[CourseFields.is_half_class] = self.is_half_class
        data[CourseFields.pdf_option] = self.pdf_option
        data[CourseFields.has_final] = self.has_final

        if self.description is not None and len(self.description) > 0:
            data[CourseFields.description] = self.description
        if self.prerequisites is not None and len(self.prerequisites) > 0:
            data[CourseFields.prerequisites] = self.prerequisites
        if self.corequisites is not None and len(self.corequisites) > 0:
            data[CourseFields.corequisites] = self.corequisites
        if self.either_prereq_or_coreq:
            data[CourseFields.either_prereq_or_coreq] = self.either_prereq_or_coreq
        if self.schedule is not None and len(self.schedule) > 0:
            data[CourseFields.schedule] = self.schedule
        if self.url is not None and len(self.url) > 0:
            data[CourseFields.url] = self.url
        if self.related_subjects is not None and len(self.related_subjects) > 0:
            comps = self.related_subjects.split(',')
            data[CourseFields.related_subjects] = [comps[i] for i in range(0, len(comps), 2)]

        if self.rating != 0.0:
            data[CourseFields.rating] = self.rating
        if self.enrollment_number != 0.0:
            data[CourseFields.enrollment_number] = self.enrollment_number
        if self.in_class_hours != 0.0:
            data[CourseFields.in_class_hours] = self.in_class_hours
        if self.out_of_class_hours != 0.0:
            data[CourseFields.out_of_class_hours] = self.out_of_class_hours

        return data


    def satisfies(self, requirement, all_courses=None):
        """
        If `allCourses` is not nil, it may be a list of course objects that can
        potentially satisfy the requirement. If a combination of courses
        satisfies the requirement, this method will return true.
        """

        req = requirement.replace("GIR:","")

        if "GIR:" in requirement and self.gir_attribute is not None and len(self.gir_attribute) > 0 and self.gir_attribute == req:
            return True

        hasses = self.get_hass_attributes()
        if "HASS" in req and hasses and (req in hasses or req == "HASS"):
            return True

        if "CI-" in req and self.communication_requirement is not None and len(self.communication_requirement) > 0 and self.communication_requirement == req:
            return True

        if self.subject_id == req or req in self.joint_subjects.split(",") or req in self.equivalent_subjects.split(","):
            return True

        # For example: 6.00 satisfies the 6.0001 requirement
        if self.children is not None and req in self.children.split(","):
            return True

        # For example: 6.0001 and 6.0002 together satsify the 6.00 requirement
        if all_courses is not None and self.parent is not None and req == self.parent:
            try:
                parent_course = Course.public_courses().get(subject_id=self.parent)
                ids = set(c.subject_id for c in all_courses)
                if parent_course.children is not None and all((child in ids) for child in parent_course.children.split(",")):
                    return True
            except:
                pass

        return False
