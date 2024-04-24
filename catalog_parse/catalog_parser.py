"""
This module is written to replace the original Swift web scraper
that produces structured subject listing information from the
MIT registrar's website.
"""

from lxml import html
import lxml.etree as etree
import requests
import re
import sys
import os

from .utils import *

# On the registrar page, all subject listings are contained
# within the HTML node specified by this XPath
SUBJECT_CONTENT_XPATH = '//*[@id="contentleft"]/table/tr[last()]/td/table/tr/td'

UNNECESSARY_IDENTIFIERS = ["textbook"]

URL_PREFIX = "http://student.mit.edu/catalog/"
URL_SUFFIX = ".html"
URL_LAST_PREFIX = "m"

CONDENSED_SPLIT_COUNT = 4

subject_id_regex = r'([A-Z0-9.-]+)(\[J\])?(,?)\s+'
course_id_list_regex = r'([A-Z0-9.-]+(,\s)?)+(?![:])'
instructor_regex = r"(?:^|\s|[:])[A-Z]\. \w+"

# For type checking str or unicode in Python 2 and 3
try:
    basestring
except NameError:
    basestring = str

COURSE_NUMBERS = [
    "1", "2", "3", "4",
    "5", "6", "7", "8",
    "9", "10", "11", "12",
    "14", "15", "16", "17",
    "18", "20", "21", "21A",
    "21W", "CMS", "21G", "21H",
    "21L", "21M", "21T", "WGS", "22",
    "24", "CC", "CSB", "EC",
    "EM", "ES", "HST", "IDS",
    "MAS", "SCM",
    "AS", "MS", "NS",
    "STS", "SWE", "SP"
]

ALPHABET = "abcdefghijklmnopqrstuvwxyz"

# Stores the HTML of the last page retrieved
LAST_PAGE_HTML = None

def load_course_elements(url):
    """
    Loads the HTML text at the given page, parses its HTML, and
    separates out the HTML elements belonging to each subject
    on the page. Returns a list of tuples, where each tuple is
    (subject_id, [elem, elem, ...]). Returns None if the page does
    not exist.
    """
    global LAST_PAGE_HTML

    page = requests.get(url)
    if page.status_code != 200:
        return None

    LAST_PAGE_HTML = page.text

    tree = html.fromstring(page.content, parser=html.HTMLParser(remove_comments=True))
    # Add newlines to br elements
    for br in tree.xpath("*//br"):
        br.tail = "\n" + br.tail if br.tail else "\n"

    course_elements = tree.xpath(SUBJECT_CONTENT_XPATH)

    # Group by anchor elements (<a name="subject id">) or h3 (in case the links are missing
    # or out of order)
    course_ids = []
    courses = []
    for element in course_elements[0].getchildren():
        if element.tag == "a" and "name" in element.keys():
            subject_id = element.get("name")
            course_ids.append(subject_id)
            courses.append([])
        else:
            match = re.match(subject_id_regex, element.text_content())
            if element.tag == "h3":
                if match is not None:
                    if len(course_ids) == 0 or (match.group(1) != course_ids[-1] and not match.group(3)):
                        subject_id = match.group(1)
                        course_ids.append(subject_id)
                        courses.append([element])
                    elif len(courses) > 0:
                        courses[-1].append(element)
                # if no match with subject ID, ignore this h3!
            elif len(courses) > 0:
                courses[-1].append(element)

    return list(zip(course_ids, courses))

def get_inner_html(node):
    """Gets the inner HTML of a node, including tags."""
    children = ''.join(etree.tostring(e).decode('utf-8') for e in node)
    if node.text is None:
        return children
    return node.text + children

def recursively_extract_info(node):
    """
    Recursively extracts information from the given node. Returns
    (child items, should stop).
    """
    info_items = []
    contents = get_inner_html(node)

    if node.tag == "img":
        if "title" in node.keys() and len(node.get("title")):
            info_items.append(node.get("title"))
    elif node.tag == "a":
        if "name" in node.keys():
            return (info_items, True)
        text = node.text_content().strip()
        if len(text):
            info_items.append(text)
    elif node.tag == "span" and len(contents) > 0:
        info_items.append(contents)
    else:
        for child in node.getchildren():
            should_stop = False
            new_info, should_stop = recursively_extract_info(child)
            info_items += new_info
            if should_stop:
                break

    return info_items, False

def extract_course_properties(elements):
    """
    Extracts relevant course information from the given list of
    elements. Returns the information as a list of strings.

    This method uses two approaches to extract the most information out of
    the parsed HTML. First, it analyzes the HTML tag hierarchy to get
    information from the images and nested tags. Then it combines all of
    the plain text together and collects each line of text as its own
    information item.
    """

    info_items = []
    # Recursively collect info from tree
    for node in elements:
        child_items, should_stop = recursively_extract_info(node)
        if should_stop and len(info_items) > 0:
            break

        info_items += child_items
        if should_stop:
            break

    # Compute flat text representation
    total_text = ""
    for node in elements:
        total_text += node.text_content()
        if node.tail is not None:
            total_text += node.tail

    # Collect info from flat text
    for line in total_text.split("\n"):
        if len(line.strip()) > 0:
            info_items.append(line.strip())

    # Sort by length, so most informative information items will be added last
    info_items.sort(key=lambda x: len(x.replace("\n", "")))

    return info_items

### Information Item Processing

def subject_title_regex(subject_id):
    """Makes a regex that detects a subject title when the subject ID is present,
    for example, "6.006 Introduction to Algorithms". Also detects parenthesized
    additional subjects that this subject title may contain."""
    return r"{}(?:{})?\s*(\([A-Z0-9.,\s-]+\))?\s+".format(
        re.escape(subject_id),
        r"|".join(re.escape(x) for x in CatalogConstants.joint_class)
    )

def process_info_item(item, attributes, write_virtual_status=False):
    """Determines the type of the given info item and adds it into the
    attributes dictionary."""
    case_insensitive_item = item.lower()
    def_not_desc = False # Filter out candidates for description

    # Prereqs
    if CatalogConstants.prereq_prefix in case_insensitive_item:
        handle_prereq(item, attributes)
        def_not_desc = True

    # Coreqs
    elif CatalogConstants.coreq_prefix in case_insensitive_item:
        handle_coreq(item, attributes)
        def_not_desc = True

    # URL
    elif CatalogConstants.url_prefix in case_insensitive_item:
        # don't save
        pass

    # Schedule
    elif re.search(r'([MTWRF]+)(\s*EVE\s*\()?(\d+)\)?', item):
        trimmed_item = item
        if CatalogConstants.final_flag in trimmed_item:
            attributes[CourseAttribute.hasFinal] = True
            trimmed_item = trimmed_item.replace(CatalogConstants.final_flag, "")

        sched, quarter_info, sem, virtual_status = parse_schedule(trimmed_item.strip().replace("\n", ""))

        sched_attrs = [CourseAttribute.schedule]
        quarter_info_attrs = [CourseAttribute.quarterInformation]

        if sem == "Fall":
            sched_attrs.append(CourseAttribute.scheduleFall)
            quarter_info_attrs.append(CourseAttribute.quarterInformationFall)
        elif sem == "IAP":
            sched_attrs.append(CourseAttribute.scheduleIAP)
            quarter_info_attrs.append(CourseAttribute.quarterInformationIAP)
        elif sem == "Spring":
            sched_attrs.append(CourseAttribute.scheduleSpring)
            quarter_info_attrs.append(CourseAttribute.quarterInformationSpring)

        if len(sched) > 0:
            for attr in sched_attrs:
                if attr in attributes:
                    attributes[attr].update(sched)
                else:
                    attributes[attr] = sched
        if len(quarter_info) > 0:
            for attr in quarter_info_attrs:
                attributes[attr] = quarter_info
        if write_virtual_status:
            attributes[CourseAttribute.virtualStatus] = virtual_status
        def_not_desc = True

    # Subject title
    elif CourseAttribute.subjectID in attributes and re.search(course_id_list_regex, item) is not None and re.search(subject_title_regex(attributes[CourseAttribute.subjectID]), item) is not None and len(item) <= 125:
        match = re.search(subject_title_regex(attributes[CourseAttribute.subjectID]), item)
        if match.group(1) is not None and len(match.group(1)) > 0:
            attributes[CourseAttribute.subjectID] = match.group(0).strip()
        end = match.end(0)
        title = item[end:]
        for suffix in CatalogConstants.joint_class:
            title = re.sub(re.escape(suffix) + r"$", "", title)
        title = title.strip()
        attributes[CourseAttribute.title] = title
        def_not_desc = True

    # Old subject ID
    elif re.match(r'\(' + subject_id_regex + '\)$', item):
        attributes[CourseAttribute.oldID] = item[1:-1]
        def_not_desc = True

    # Subject level
    elif CatalogConstants.undergrad in case_insensitive_item and abs(len(item) - len(CatalogConstants.undergrad)) < 10:
        attributes[CourseAttribute.subjectLevel] = CatalogConstants.undergradValue
    elif CatalogConstants.graduate in case_insensitive_item and abs(len(item) - len(CatalogConstants.graduate)) < 10:
        attributes[CourseAttribute.subjectLevel] = CatalogConstants.graduateValue

    # Notes
    elif len(item) > 75 and len(attributes.get(CourseAttribute.description, "")) > len(item):
        if CourseAttribute.notes in attributes:
            attributes[CourseAttribute.notes] = attributes[CourseAttribute.notes] + "\n" + item.strip()
        else:
            attributes[CourseAttribute.notes] = item.strip()

    # Meets with/joint/equivalent subjects
    elif CatalogConstants.meets_with_prefix in case_insensitive_item or CatalogConstants.equivalent_subj_prefix in case_insensitive_item or CatalogConstants.joint_subj_prefix in case_insensitive_item:
        prefixes = '|'.join(re.escape(p) for p in [CatalogConstants.meets_with_prefix, CatalogConstants.equivalent_subj_prefix, CatalogConstants.joint_subj_prefix])
        for i, match in enumerate(re.finditer('({0})(.+?)(?=\\Z|\)|{0})'.format(prefixes), item, re.I | re.S)):
            prefix = match.group(1)
            contents = [comp.strip() for comp in match.group(2).split(",") if len(comp.strip()) > 0]
            if i == 0 and match.start(0) > 3: continue

            if prefix.lower() == CatalogConstants.meets_with_prefix:
                attributes[CourseAttribute.meetsWithSubjects] = contents
            elif prefix.lower() == CatalogConstants.equivalent_subj_prefix:
                attributes[CourseAttribute.equivalentSubjects] = contents
            elif prefix.lower() == CatalogConstants.joint_subj_prefix:
                for suffix in CatalogConstants.joint_class:
                    for i in range(len(contents)):
                        contents[i] = re.sub(re.escape(suffix) + r"$", "", contents[i])
                attributes[CourseAttribute.jointSubjects] = contents
            else:
                print("Unrecognized prefix")

    # Not offered information
    elif CatalogConstants.not_offered_prefix in case_insensitive_item:
        upper_bound = item.find(CatalogConstants.not_offered_prefix) + len(CatalogConstants.not_offered_prefix)
        attributes[CourseAttribute.notOfferedYear] = item[upper_bound:].strip()

    # Variable units
    elif CatalogConstants.units_arranged_prefix in case_insensitive_item:
        attributes[CourseAttribute.isVariableUnits] = True

    # Unit counts
    elif CatalogConstants.units_prefix in case_insensitive_item:

        # P/D/F option
        if CatalogConstants.pdf_string in item:
            attributes[CourseAttribute.pdfOption] = True
            item = item.replace(CatalogConstants.pdf_string, "")
        else:
            attributes[CourseAttribute.pdfOption] = False

        upper_bound = item.find(CatalogConstants.units_prefix) + len(CatalogConstants.units_prefix)
        units_string = item[upper_bound:].strip()
        comps = re.split(r'\s', units_string)[-1].split("-")
        if len(comps) >= 3:
            attributes[CourseAttribute.lectureUnits] = int(comps[0])
            attributes[CourseAttribute.labUnits] = int(comps[1])
            attributes[CourseAttribute.preparationUnits] = int(comps[2])
            attributes[CourseAttribute.totalUnits] = int(comps[0]) + int(comps[1]) + int(comps[2])

    # HASS requirement
    elif any(hass_code in case_insensitive_item for hass_code in [CatalogConstants.hassH, CatalogConstants.hassA, CatalogConstants.hassS, CatalogConstants.hassE]):
        attributes[CourseAttribute.hassRequirement] = CatalogConstants.abbreviation(item.strip())

    # Multiple HASS requirements
    elif "+" in item and len(item) < 50 and any(hass_code in case_insensitive_item for hass_code in [CatalogConstants.hassHBasic, CatalogConstants.hassABasic, CatalogConstants.hassSBasic, CatalogConstants.hassEBasic]):
        comps = item.split("+")
        attributes[CourseAttribute.hassRequirement] = ','.join([CatalogConstants.abbreviation(comp.strip()) for comp in comps])

    # CI requirement
    elif any(ci_code in case_insensitive_item for ci_code in [CatalogConstants.ciH, CatalogConstants.ciHW]):
        attributes[CourseAttribute.communicationRequirement] = CatalogConstants.abbreviation(item.strip())

    # GIR requirement
    elif item.strip() in CatalogConstants.gir_requirements:
        attributes[CourseAttribute.GIR] = CatalogConstants.gir_requirements[item.strip()]

    # Instructors
    elif len(item) < 100 and re.search(instructor_regex, item) is not None:
        new_comp = item.strip().replace("\n", "")
        if CourseAttribute.instructors in attributes and (CatalogConstants.fall in attributes[CourseAttribute.instructors].lower() or CatalogConstants.spring in new_comp.lower()):
            attributes[CourseAttribute.instructors] += '\n' + new_comp
        else:
            attributes[CourseAttribute.instructors] = new_comp

    # Offered terms
    elif CatalogConstants.fall in case_insensitive_item:
        attributes[CourseAttribute.offeredFall] = True
    elif CatalogConstants.iap in case_insensitive_item:
        attributes[CourseAttribute.offeredIAP] = True
    elif CatalogConstants.spring in case_insensitive_item:
        attributes[CourseAttribute.offeredSpring] = True
    elif CatalogConstants.summer in case_insensitive_item:
        attributes[CourseAttribute.offeredSummer] = True

    # The longest item that is more than 30 characters long should be the description
    if len(item) > 30 and not def_not_desc:
        if CourseAttribute.description not in attributes or len(attributes[CourseAttribute.description]) < len(item):
            attributes[CourseAttribute.description] = item.strip()

def expand_subject_ids(subject_id):
    """
    If the given subject ID represents a range of IDs, returns a list of all
    of them. For example:
    6.S193-6.S198 ==> [6.S193, 6.S194, 6.S195, 6.S196, 6.S197, 6.S198]
    10.81 (10.83, 10.85, 10.87) ==> [10.81, 10.83, 10.85, 10.87]
    """

    # Matches 6.S193-6.S198
    match = re.match(r'([A-Z0-9.]+[^0-9])([0-9]+)-[A-Z0-9.]+[^0-9]([0-9]+)', subject_id)
    if match is not None:
        base = match.group(1)
        start_num = int(match.group(2))
        end_num = int(match.group(3))
        return [base + str(num).zfill(len(match.group(2))) for num in range(start_num, end_num + 1)]

    # Matches 10.81 (10.83, 10.85, 10.87)
    match = re.match(r'([A-Z0-9.]+)\s*\(((?:[A-Z0-9.]+,\s*)*(?:[A-Z0-9.]+\s*))\)', subject_id)
    if match is not None:
        base = match.group(1)
        alternatives = match.group(2).split(',')
        return [base.strip()] + [alt.strip() for alt in alternatives]

    return [subject_id]

def merge_duplicates(courses):
    """
    Merges any duplicate courses so that most extracted information is preserved.
    Given two courses, keeps the value for each course attribute with the greater
    string length. Returns a new list of courses.
    """
    merged_courses = []
    merged_courses_set = set()
    course_dict = {}
    for course in courses:
        if CourseAttribute.subjectID not in course: continue
        course_dict.setdefault(course[CourseAttribute.subjectID], []).append(course)

    for course in courses:
        if CourseAttribute.subjectID not in course: continue
        subject_id = course[CourseAttribute.subjectID]
        if subject_id in merged_courses_set: continue

        if len(course_dict[subject_id]) > 1:
            total_course = {}
            keys = set().union(*(other.keys() for other in course_dict[subject_id]))
            for key in keys:
                vals = [other.get(key, '') for other in course_dict[subject_id]]

                if key == CourseAttribute.URL:
                    # Choose a URL without the hyphen in the link name
                    correct_val = next((val for val in vals if len(val) and '-' not in val[val.rfind('#'):]), None)
                    if correct_val is not None:
                        total_course[key] = correct_val

                # The 'best' value is the longest value
                best_val = max(vals, key=lambda x: len(unicode(x)))
                total_course[key] = best_val
            merged_courses.append(total_course)
        else:
            merged_courses.append(course)
        merged_courses_set.add(subject_id)

    return merged_courses

def courses_from_dept_code(dept_code, **options):
    """
    Loads courses from the catalog for the given department code (department +
    alphabetical code, such as "6a" or "21Gb", which defines a page on the
    registrar site). Returns None if the page does not exist.
    """

    catalog_url = URL_PREFIX + URL_LAST_PREFIX + dept_code + URL_SUFFIX

    elements = load_course_elements(catalog_url)
    if elements is None:
        # The page does not exist
        return None

    courses = []
    autofill_ids = []
    for id, nodes in elements:
        if len(nodes) == 0:
            autofill_ids.append(id)
            continue

        props = extract_course_properties(nodes)

        id = id.replace('[J]', '')
        if id.endswith('J'):
            id = id[:-1]

        attribs = {
            CourseAttribute.subjectID: id,
            CourseAttribute.URL: catalog_url + "#" + id
        }
        for prop in props:
            process_info_item(prop, attribs, **options)

        # The subject ID might have changed during parsing
        id = attribs[CourseAttribute.subjectID]

        # Apply the subject content to multiple subject IDs if they are contained within this entry
        subject_ids = expand_subject_ids(id) + autofill_ids

        if len(subject_ids) > 1:
            # Possibly split up schedules by subject
            schedules = attribs.get(CourseAttribute.schedule, {})
            if "" in schedules:
                # Only one schedule for all
                schedules = {other_id: schedules[""] for other_id in subject_ids}

            for other_id in subject_ids:
                copied_course = {key: val for key, val in attribs.items()}
                copied_course[CourseAttribute.subjectID] = other_id
                if other_id in schedules:
                    copied_course[CourseAttribute.schedule] = schedules[other_id]
                elif CourseAttribute.schedule in copied_course:
                    del copied_course[CourseAttribute.schedule]
                courses.append(copied_course)
        else:
            # Use only the first item in the schedule dictionary
            for attrib in [CourseAttribute.schedule,
                           CourseAttribute.scheduleFall,
                           CourseAttribute.scheduleIAP,
                           CourseAttribute.scheduleSpring]:
                if attrib in attribs:
                    attribs[attrib] = list(attribs[attrib].values())[0]
            courses.append(attribs)

        # Autofill regions that were empty with the subsequent course information
        # For example, 6.260, 6.261 Advanced Topics in Communications
        if len(autofill_ids) > 0:
            autofill_ids = []

    return courses

### Writing courses

def writing_description_for_attribute(course, attribute):
    """Returns a string that represents the given attribute of the given course,
    where course is a dictionary {attribute: value}."""
    if attribute not in course:
        return ""

    item = course[attribute]
    if isinstance(item, basestring):
        return '"' + item.replace('"', "'").replace('\n', '\\n') + '"'
    elif isinstance(item, bool):
        return "Y" if item == True else "N"
    elif isinstance(item, float):
        return "{:.2f}".format(item)
    elif isinstance(item, int):
        return str(item)
    elif isinstance(item, list) and len(item) > 0 and isinstance(item[0], list):
        return '"' + ";".join(",".join(subitem) for subitem in item) + '"'
    elif isinstance(item, list):
        return '"' + ",".join(item) + '"'
    else:
        print("Don't have a way to represent attribute {}: {} ({})".format(attribute, item, type(item)))
        return str(item)

def write_courses(courses, filepath, attributes):
    """Writes the given list of courses to the given file, in CSV format. Only
    writes the given list of attributes."""
    csv_comps = [attributes]

    for course in courses:
        csv_comps.append([writing_description_for_attribute(course, attrib) for attrib in attributes])

    with open(filepath, 'w') as file:
        if sys.version_info > (3, 0):
            file.write("\n".join(",".join(item) for item in csv_comps))
        else:
            file.write("\n".join(",".join(item) for item in csv_comps).encode('utf-8'))

### Main method

def parse(output_dir, equivalences_path=None, write_related=True,
          progress_callback=None, write_virtual_status=False):
    """
    Parses the catalog from the web and writes the files to the given directory.

    output_dir: path to a directory into which to write the results
    equivalences_path: path to a JSON file containing equivalences, i.e.
        [[["6.0001", "6.0002"], "6.00"], ...]
    write_related: if True, compute the related and features files as well
    progress_callback: a function that takes the current progress (from 0-100) and an
        update string
    write_virtual_status: if True, write the "Virtual Status" field
    """

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    # Parse each department
    all_courses = []
    courses_by_dept = {}
    for i, course_code in enumerate(COURSE_NUMBERS):
        if progress_callback is not None:
            progress_callback(float(i) / len(COURSE_NUMBERS) * 50, "Parsing course {} ({} of {})...".format(course_code, i + 1, len(COURSE_NUMBERS)))

        dept_courses = []
        original_html = None
        for letter in ALPHABET:
            total_code = course_code + letter

            # Check that this page was linked to in the original dept page
            if original_html is not None and (URL_LAST_PREFIX + total_code + URL_SUFFIX) not in original_html:
                continue

            addl_courses = [course for course in courses_from_dept_code(
                                total_code,
                                write_virtual_status=write_virtual_status)
                            if course_code in course[CourseAttribute.subjectID]]
            if len(addl_courses) == 0:
                continue

            print("======", total_code)
            dept_courses += addl_courses
            if original_html is None:
                original_html = LAST_PAGE_HTML

        dept_courses = merge_duplicates(dept_courses)
        course_dict = {course[CourseAttribute.subjectID]: course for course in dept_courses}

        # Add in equivalences
        if equivalences_path is not None:
            parse_equivalences(equivalences_path, course_dict)

        # Write department-specific file
        write_courses(dept_courses, os.path.join(output_dir, course_code + ".txt"), ALL_ATTRIBUTES)
        all_courses += dept_courses
        courses_by_dept[course_code] = course_dict

    print("Writing condensed courses...")
    for i in range(CONDENSED_SPLIT_COUNT):
        lower_bound = int(i / float(CONDENSED_SPLIT_COUNT) * len(all_courses))
        upper_bound = min(len(all_courses), int((i + 1) / float(CONDENSED_SPLIT_COUNT) * len(all_courses)))
        write_courses(all_courses[lower_bound:upper_bound], os.path.join(output_dir, "condensed_{}.txt".format(i)), CONDENSED_ATTRIBUTES)

    print("Writing all courses...")
    write_courses(all_courses, os.path.join(output_dir, "courses.txt"), ALL_ATTRIBUTES)

    if write_related:
        write_related_and_features(courses_by_dept, output_dir, progress_callback=progress_callback, progress_start=50.0)
    print("Done.")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python catalog_parser.py output-dir [equivalences-file]")
        exit(1)

    output_dir = sys.argv[1]

    if len(sys.argv) > 2:
        equiv_path = sys.argv[2]
    else:
        equiv_path = None

    parse(output_dir, equivalences_path=equiv_path,
          write_related=('-norel' not in sys.argv))
