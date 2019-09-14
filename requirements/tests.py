from django.test import TestCase
from .models import *
from .progress import *
from catalog.models import Course

# Create your tests here.
class RequirementsStatementTest(TestCase):

    def test_parse_string_simple(self):
        string = "6.00"
        req = RequirementsStatement.from_string(string)
        self.assertEqual("6.00", req.requirement)
        self.assertFalse(req.requirements.exists())

    def test_parse_string_and(self):
        string = "2.001, 2.002"
        req = RequirementsStatement.from_string(string)
        self.assertEqual(None, req.requirement)
        self.assertEqual(CONNECTION_TYPE_ALL, req.connection_type)
        self.assertEqual(2, req.requirements.count())
        self.assertEqual(set(["2.001", "2.002"]),
                         set([child.requirement for child in req.requirements.all()]))

    def test_parse_string_or(self):
        string = "7.013/21M.284/6.003"
        req = RequirementsStatement.from_string(string)
        self.assertEqual(None, req.requirement)
        self.assertEqual(CONNECTION_TYPE_ANY, req.connection_type)
        self.assertEqual(3, req.requirements.count())
        self.assertEqual(set(["7.013", "21M.284", "6.003"]),
                         set([child.requirement for child in req.requirements.all()]))

    def test_parse_string_threshold(self):
        string = "CMS.01/CMS.02/CMS.03{>=2}"
        req = RequirementsStatement.from_string(string)
        self.assertEqual(None, req.requirement)
        self.assertEqual(CONNECTION_TYPE_ANY, req.connection_type)
        self.assertEqual(THRESHOLD_TYPE_GTE, req.threshold_type)
        self.assertEqual(2, req.threshold_cutoff)
        self.assertEqual(CRITERION_SUBJECTS, req.threshold_criterion)
        self.assertEqual(3, req.requirements.count())
        self.assertEqual(set(["CMS.01", "CMS.02", "CMS.03"]),
                         set([child.requirement for child in req.requirements.all()]))

    def test_parse_string_distinct_threshold(self):
        string = "x/y/z/w{<24u|>=1}"
        req = RequirementsStatement.from_string(string)
        self.assertEqual(None, req.requirement)
        self.assertEqual(CONNECTION_TYPE_ANY, req.connection_type)
        self.assertEqual(THRESHOLD_TYPE_LT, req.threshold_type)
        self.assertEqual(24, req.threshold_cutoff)
        self.assertEqual(CRITERION_UNITS, req.threshold_criterion)
        self.assertEqual(THRESHOLD_TYPE_GTE, req.distinct_threshold_type)
        self.assertEqual(1, req.distinct_threshold_cutoff)
        self.assertEqual(CRITERION_SUBJECTS, req.distinct_threshold_criterion)
        self.assertEqual(4, req.requirements.count())
        self.assertEqual(set("xyzw"),
                         set([child.requirement for child in req.requirements.all()]))

    def test_parse_string_plain_string(self):
        string = '""a requirement""{>36u}'
        req = RequirementsStatement.from_string(string)
        self.assertEqual("a requirement", req.requirement)
        self.assertEqual(True, req.is_plain_string)
        self.assertEqual(CONNECTION_TYPE_NONE, req.connection_type)
        self.assertEqual(THRESHOLD_TYPE_GT, req.threshold_type)
        self.assertEqual(36, req.threshold_cutoff)
        self.assertEqual(CRITERION_UNITS, req.threshold_criterion)

    def test_requirement_json_object(self):
        req = RequirementsStatement.initialize("my req", "a/b{>=0}")
        self.assertEqual({
            JSONConstants.title: "my req",
            JSONConstants.threshold: {
                JSONConstants.thresh_type: THRESHOLD_TYPE_GTE,
                JSONConstants.thresh_cutoff: 0,
                JSONConstants.thresh_criterion: CRITERION_SUBJECTS
            },
            JSONConstants.thresh_description: "optional - select any",
            JSONConstants.connection_type: CONNECTION_TYPE_ANY,
            JSONConstants.requirements: [{
                JSONConstants.requirement: "a"
            }, {
                JSONConstants.requirement: "b"
            }]
        }, req.to_json_object())

    def test_substitute_variables(self):
        parent = RequirementsStatement.from_string("x, y")
        vars = {
            "z": RequirementsStatement.from_string("6.003"),
            "x": RequirementsStatement.from_string("6.002/z"),
            "y": RequirementsStatement.from_string("6.009")
        }
        parent.substitute_variables(vars)
        children = parent.requirements.all()
        self.assertEqual(2, len(children))
        x = children[0]
        self.assertEqual(2, x.requirements.count())
        self.assertEqual(set(["6.002", "6.003"]),
                         set([child.requirement for child in x.requirements.all()]))
        self.assertEqual(CONNECTION_TYPE_ANY, x.connection_type)
        y = children[1]
        self.assertEqual("6.009", y.requirement)


class RequirementsProgressTest(TestCase):

    def setUp(self):
        Course.objects.create(subject_id="2.001", title="Foo").save()
        Course.objects.create(subject_id="2.002", title="Bar").save()
        Course.objects.create(subject_id="2.003", title="Foo Bar").save()
        Course.objects.create(subject_id="8.01",
                              title="Physics",
                              gir_attribute="GIR:PHY1").save()
        Course.objects.create(subject_id="21M.030",
                              title="World Music",
                              communication_requirement="CI-H").save()
        Course.objects.create(subject_id="21M.421",
                              title="MITSO",
                              hass_attribute="HASS-A").save()
        Course.objects.create(subject_id="17.55",
                              title="Latin American Studies",
                              communication_requirement="CI-H").save()
        Course.objects.create(subject_id="21L.001",
                              title="Some Literature Subject",
                              communication_requirement="CI-HW").save()
        for course in Course.objects.all():
            course.total_units = 12
            course.public = True
            course.save()

    def assert_basic_progress(self, courses, max_courses, progress):
        """Asserts that the given number of courses and the max number of
        courses are satisfied in the given RequirementsProgress object.
        Assumes each course is 12 units."""
        self.assertEqual(courses, progress.subject_progress)
        self.assertEqual(max_courses, progress.subject_max)
        self.assertEqual(courses * 12, progress.unit_progress)
        self.assertEqual(max_courses * 12, progress.unit_max)
        self.assertEqual(courses, progress.progress)
        self.assertEqual(max_courses, progress.progress_max)
        self.assertEqual(courses / float(max_courses) * 100.0, progress.percent_fulfilled)
        self.assertEqual(courses / float(max_courses), progress.fraction_fulfilled)

    def test_progress_basic_and(self):
        statement = RequirementsStatement.from_string("2.001, 2.003")
        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="2.001")]
        progress.compute(courses, {})
        self.assertFalse(progress.is_fulfilled)
        self.assert_basic_progress(1, 2, progress)
        self.assertEqual(courses, progress.satisfied_courses)

        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="2.001"),
                   Course.objects.get(subject_id="2.003")]
        progress.compute(courses, {})
        self.assertTrue(progress.is_fulfilled)
        self.assert_basic_progress(2, 2, progress)
        self.assertEqual(courses, progress.satisfied_courses)

        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="21M.030"),
                   Course.objects.get(subject_id="8.01")]
        progress.compute(courses, {})
        self.assertFalse(progress.is_fulfilled)
        self.assert_basic_progress(0, 2, progress)
        self.assertEqual([], progress.satisfied_courses)

    def test_progress_basic_or(self):
        statement = RequirementsStatement.from_string("2.001/2.003")
        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="2.001")]
        progress.compute(courses, {})
        self.assertTrue(progress.is_fulfilled)
        self.assert_basic_progress(1, 1, progress)
        self.assertEqual(courses, progress.satisfied_courses)

        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="2.001"),
                   Course.objects.get(subject_id="2.003")]
        progress.compute(courses, {})
        self.assertTrue(progress.is_fulfilled)
        self.assert_basic_progress(1, 1, progress)
        self.assertEqual(courses, progress.satisfied_courses)

        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="21M.030"),
                   Course.objects.get(subject_id="8.01")]
        progress.compute(courses, {})
        self.assertFalse(progress.is_fulfilled)
        self.assert_basic_progress(0, 1, progress)
        self.assertEqual([], progress.satisfied_courses)

    def test_progress_manual(self):
        statement = RequirementsStatement.from_string('""2 classes""{>=2}')
        manual = {"0": 1}
        courses = [Course.objects.get(subject_id="21M.421")]
        progress = RequirementsProgress(statement, "0")
        progress.compute(courses, manual)
        self.assertFalse(progress.is_fulfilled)
        self.assert_basic_progress(1, 2, progress)
        # Computation should generate a dummy course
        self.assertEqual(1, len(progress.satisfied_courses))

    def test_progress_manual_units(self):
        statement = RequirementsStatement.from_string('""24 units""{>=24u}')
        manual = {"myid": 18}
        courses = [Course.objects.get(subject_id="21M.421")]
        progress = RequirementsProgress(statement, "myid")
        progress.compute(courses, manual)
        self.assertFalse(progress.is_fulfilled)
        self.assertEqual(1, progress.subject_progress)
        self.assertEqual(2, progress.subject_max)
        self.assertEqual(18, progress.unit_progress)
        self.assertEqual(24, progress.unit_max)
        self.assertEqual(18, progress.progress)
        self.assertEqual(24, progress.progress_max)
        self.assertEqual(75.0, progress.percent_fulfilled)
        self.assertEqual(0.75, progress.fraction_fulfilled)
        # Computation should generate a dummy course
        self.assertEqual(1, len(progress.satisfied_courses))

    def test_progress_or_threshold(self):
        statement = RequirementsStatement.from_string("2.001/2.002/2.003{>=2}")
        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="2.001")]
        progress.compute(courses, {})
        self.assertFalse(progress.is_fulfilled)
        self.assert_basic_progress(1, 2, progress)
        self.assertEqual(courses, progress.satisfied_courses)

        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="2.001"),
                   Course.objects.get(subject_id="2.002"),
                   Course.objects.get(subject_id="2.003")]
        progress.compute(courses, {})
        self.assertTrue(progress.is_fulfilled)
        self.assert_basic_progress(2, 2, progress)
        self.assertEqual(courses, progress.satisfied_courses)

        progress = RequirementsProgress(statement, "0")
        courses = [Course.objects.get(subject_id="2.001"),
                   Course.objects.get(subject_id="2.003")]
        progress.compute(courses, {})
        self.assertTrue(progress.is_fulfilled)
        self.assert_basic_progress(2, 2, progress)
        self.assertEqual(courses, progress.satisfied_courses)
