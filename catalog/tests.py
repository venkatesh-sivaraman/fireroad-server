"""Test cases for the course catalog models."""

import json

from django.test import TestCase
from django.test.client import RequestFactory

from .models import Course, CourseFields
from . import views


class CourseCatalogTest(TestCase):
    """Tests the Course model object and the catalog endpoints."""

    def setUp(self):
        self.factory = RequestFactory()

        # Dummy courses
        Course.objects.create(subject_id="2.001",
                              title="Foo",
                              public=True).save()
        Course.objects.create(subject_id="2.002",
                              title="Bar",
                              public=True).save()
        Course.objects.create(subject_id="2.003",
                              title="Foo Bar",
                              public=True).save()
        Course.objects.create(subject_id="8.01",
                              title="Physics",
                              gir_attribute="GIR:PHY1",
                              public=True).save()
        Course.objects.create(subject_id="21L.001",
                              title="Some Literature Subject",
                              communication_requirement="CI-HW",
                              public=True).save()

        # Course for JSON object testing
        course = Course.objects.create(
            subject_id="21M.030",
            title="World Music",
            total_units=12,
            offered_fall=True,
            offered_spring=True,
            public=True,
            level="U",
            joint_subjects="21M.830,21M.290",
            equivalent_subjects="21M.031",
            meets_with_subjects="",
            quarter_information="1,march 1",
            not_offered_year="2019-2020",
            instructors="E. Zimmer\nC. Smith",
            communication_requirement="CI-H",
            hass_attribute="HASS-A",
            gir_attribute="REST",
            lecture_units=5,
            preparation_units=7,
            description="Test description of 21M.030",
            prerequisites="21M.051/''permission of instructor''",
            schedule="Lecture,4-364/MW/0/9.30-11,4-364/MW/0/11-12.30",
            url="http://student.mit.edu/catalog/m21Ma.html#21M.030",
            related_subjects="21M.011,4.0,21M.031,3.0",
            rating=5.0,
            enrollment_number=45.0,
            in_class_hours=3.0,
            out_of_class_hours=5.5)
        course.save()

        # Multi-HASS course
        Course.objects.create(
            subject_id="21L.013",
            title="Supernatural in Literature",
            hass_attribute="HASS-A,HASS-H",
            public=True).save()

        # Parent/child courses
        Course.objects.create(subject_id="6.00",
                              title="Intro to Computer Science",
                              public=True,
                              children="6.0001,6.0002").save()
        Course.objects.create(subject_id="6.0001",
                              title="Intro to Programming",
                              public=True,
                              parent="6.00").save()
        Course.objects.create(subject_id="6.0002",
                              title="Intro to Data Science",
                              public=True,
                              parent="6.00").save()

    # Course model testing

    def test_json_object(self):
        """Abbreviated course's JSON has the correct values"""
        course = Course.objects.get(subject_id="21M.030")
        result = course.to_json_object(full=False)
        expected = {
            CourseFields.subject_id: u"21M.030",
            CourseFields.title: u"World Music",
            CourseFields.total_units: 12,
            CourseFields.offered_fall: True,
            CourseFields.offered_IAP: False,
            CourseFields.offered_spring: True,
            CourseFields.offered_summer: False,
            CourseFields.public: True,
            CourseFields.level: u"U",
            CourseFields.joint_subjects: [u"21M.830", u"21M.290"],
            CourseFields.equivalent_subjects: [u"21M.031"],
            CourseFields.quarter_information: u"1,march 1",
            CourseFields.not_offered_year: u"2019-2020",
            CourseFields.instructors: [u"E. Zimmer", u"C. Smith"],
            CourseFields.communication_requirement: u"CI-H",
            CourseFields.hass_attribute: u"HASS-A",
            CourseFields.gir_attribute: u"REST",
        }
        self.maxDiff = None # pylint: disable=invalid-name
        self.assertDictEqual(expected, result)

    def test_json_object_full(self):
        """Full course's JSON has the correct values"""
        course = Course.objects.get(subject_id="21M.030")
        result = course.to_json_object()
        expected = {
            CourseFields.subject_id: u"21M.030",
            CourseFields.title: u"World Music",
            CourseFields.total_units: 12,
            CourseFields.offered_fall: True,
            CourseFields.offered_IAP: False,
            CourseFields.offered_spring: True,
            CourseFields.offered_summer: False,
            CourseFields.public: True,
            CourseFields.level: u"U",
            CourseFields.joint_subjects: [u"21M.830", u"21M.290"],
            CourseFields.equivalent_subjects: [u"21M.031"],
            CourseFields.quarter_information: u"1,march 1",
            CourseFields.not_offered_year: u"2019-2020",
            CourseFields.instructors: [u"E. Zimmer", u"C. Smith"],
            CourseFields.communication_requirement: u"CI-H",
            CourseFields.hass_attribute: u"HASS-A",
            CourseFields.gir_attribute: u"REST",
            CourseFields.lecture_units: 5,
            CourseFields.lab_units: 0,
            CourseFields.design_units: 0,
            CourseFields.preparation_units: 7,
            CourseFields.is_variable_units: False,
            CourseFields.is_half_class: False,
            CourseFields.pdf_option: False,
            CourseFields.has_final: False,
            CourseFields.description: u"Test description of 21M.030",
            CourseFields.prerequisites: u"21M.051/''permission of instructor''",
            CourseFields.schedule: u"Lecture,4-364/MW/0/9.30-11,4-364/MW/0/11-12.30",
            CourseFields.url: u"http://student.mit.edu/catalog/m21Ma.html#21M.030",
            CourseFields.related_subjects: [u"21M.011", u"21M.031"],
            CourseFields.rating: 5.0,
            CourseFields.enrollment_number: 45.0,
            CourseFields.in_class_hours: 3.0,
            CourseFields.out_of_class_hours: 5.5
        }
        self.maxDiff = None
        self.assertDictEqual(expected, result)

    def test_hass_fulfillment(self):
        """HASS attribute fulfillment"""
        course = Course.objects.get(subject_id="21M.030")
        self.assertTrue(course.satisfies("HASS"))
        self.assertTrue(course.satisfies("HASS-A"))
        self.assertFalse(course.satisfies("HASS-H"))
        self.assertFalse(course.satisfies("HASS-S"))
        self.assertFalse(course.satisfies("HASS-E"))

    def test_multiple_hass_fulfillment(self):
        """Fulfillment of multiple HASS types"""
        course = Course.objects.get(subject_id="21L.013")
        self.assertTrue(course.satisfies("HASS"))
        self.assertTrue(course.satisfies("HASS-A"))
        self.assertTrue(course.satisfies("HASS-H"))
        self.assertFalse(course.satisfies("HASS-S"))
        self.assertFalse(course.satisfies("HASS-E"))

    def test_gir_fulfillment(self):
        """Fulfillment of GIR requirements"""
        course = Course.objects.get(subject_id="21M.030")
        self.assertFalse(course.satisfies("GIR:PHY1"))
        self.assertFalse(course.satisfies("GIR:LAB"))
        self.assertFalse(course.satisfies("REST"))
        self.assertTrue(course.satisfies("GIR:REST"))

    def test_parent_child_fulfillment(self):
        """Fulfillment of the child courses by the parent"""
        course = Course.objects.get(subject_id="6.00")
        self.assertTrue(course.satisfies("6.0001"))
        self.assertTrue(course.satisfies("6.0002"))

    def test_child_parent_fulfillment(self):
        """Fulfillment of the parent course by the children"""
        courses = [Course.objects.get(subject_id="6.0001"),
                   Course.objects.get(subject_id="6.0002")]
        self.assertFalse(courses[0].satisfies("6.00"))
        self.assertFalse(courses[1].satisfies("6.00"))
        self.assertTrue(courses[0].satisfies("6.00", all_courses=courses))
        self.assertTrue(courses[1].satisfies("6.00", all_courses=courses))

    # Catalog endpoints

    def test_lookup_subject(self):
        """Lookup by subject ID"""
        request = self.factory.get("/courses/lookup/")
        response = views.lookup(request, subject_id="2.001")
        self.assertEqual(200, response.status_code)
        self.assertDictContainsSubset({
            CourseFields.subject_id: u"2.001",
            CourseFields.title: u"Foo"
        }, json.loads(response.content))

    def test_lookup_subject_not_existing(self):
        """Lookup a subject that doesn't exist"""
        request = self.factory.get("/courses/lookup/")
        response = views.lookup(request, subject_id="foo")
        self.assertEqual(404, response.status_code)

    def test_lookup_subject_no_subject(self):
        """Lookup a subject with no subject ID provided"""
        request = self.factory.get("/courses/lookup/")
        response = views.lookup(request)
        self.assertEqual(400, response.status_code)

    def test_department(self):
        """Lookup all courses by a department"""
        request = self.factory.get("/courses/department/")
        response = views.department(request, dept="2")
        self.assertEqual(200, response.status_code)
        courses = json.loads(response.content)
        self.assertEqual(
            {"2.001", "2.002", "2.003"},
            {course[CourseFields.subject_id] for course in courses})

    def test_department_empty(self):
        "Lookup a department that has no courses"""
        request = self.factory.get("/courses/department/")
        response = views.department(request, dept="43")
        self.assertEqual(200, response.status_code)
        courses = json.loads(response.content)
        self.assertEqual([], courses)

    def test_department_no_dept(self):
        """Lookup a department with no department provided"""
        request = self.factory.get("/courses/department/")
        response = views.department(request)
        self.assertEqual(400, response.status_code)

    def test_list_all(self):
        """List all courses"""
        request = self.factory.get("/courses/all/")
        response = views.list_all(request)
        self.assertEqual(200, response.status_code)
        courses = json.loads(response.content)
        subject_ids = {course[CourseFields.subject_id] for course in courses}
        self.assertEqual({"2.001",
                          "2.002",
                          "2.003",
                          "8.01",
                          "21L.001",
                          "21M.030",
                          "21L.013",
                          "6.00",
                          "6.0001",
                          "6.0002"},
                         subject_ids)

    def test_search(self):
        """Search for course by text phrase"""
        request = self.factory.get("/courses/search/")
        response = views.search(request, search_term="physics")
        self.assertEqual(200, response.status_code)
        results = json.loads(response.content)
        self.assertEqual(1, len(results))
        self.assertEqual("8.01", results[0][CourseFields.subject_id])

    def test_search_type(self):
        """Search for course with search type"""
        request = self.factory.get("/courses/search/", {"type": "ends"})
        response = views.search(request, search_term="2")
        self.assertEqual(200, response.status_code)
        results = json.loads(response.content)
        self.assertEqual(2, len(results))
        subject_ids = {course[CourseFields.subject_id] for course in results}
        self.assertEqual({"2.002", "6.0002"}, subject_ids)

    def test_search_gir(self):
        """Search for course with GIR requirement"""
        request = self.factory.get("/courses/search/", {"gir": "rest"})
        response = views.search(request, search_term="w")
        self.assertEqual(200, response.status_code)
        results = json.loads(response.content)
        self.assertEqual(1, len(results))
        self.assertEqual("21M.030", results[0][CourseFields.subject_id])

    def test_search_hass(self):
        """Search for course with HASS requirement"""
        request = self.factory.get("/courses/search/", {"hass": "h"})
        response = views.search(request, search_term="s")
        self.assertEqual(200, response.status_code)
        results = json.loads(response.content)
        self.assertEqual(1, len(results))
        self.assertEqual("21L.013", results[0][CourseFields.subject_id])

    def test_search_ci(self):
        """Search for course with CI requirement"""
        request = self.factory.get("/courses/search/", {"ci": "not-ci"})
        response = views.search(request, search_term="music")
        self.assertEqual(200, response.status_code)
        results = json.loads(response.content)
        self.assertEqual([], results)

    def test_search_offered(self):
        """Search for course filtered by offered time"""
        request = self.factory.get("/courses/search/", {"offered": "fall"})
        response = views.search(request, search_term="d")
        self.assertEqual(200, response.status_code)
        results = json.loads(response.content)
        self.assertEqual(1, len(results))
        self.assertEqual("21M.030", results[0][CourseFields.subject_id])

    def test_search_level(self):
        """Search for course filtered by U/G level"""
        request = self.factory.get("/courses/search/", {"level": "grad"})
        response = views.search(request, search_term="anything")
        self.assertEqual(200, response.status_code)
        results = json.loads(response.content)
        self.assertEqual([], results)
