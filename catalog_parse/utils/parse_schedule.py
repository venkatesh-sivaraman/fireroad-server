"""Parses course catalog schedule text from the registrar site."""

import re
from .catalog_constants import *

# For when the schedule string contains multiple subjects, like
# 12.S592: Lecture: xyz
SUBJECT_ID_REGEX = r'^([A-Z0-9.-]+)(\[J\])?$'

QUARTER_INFO_REGEX = r"\(?(begins|ends)\s+(.+?)(\.|\))"

# Class type regex matches "Lecture:abc XX:"
CLASS_TYPE_REGEX = r"([A-z0-9.-]+):(.+?)(?=\Z|\w+:)"

# Time regex matches "MTWRF9-11 ( 1-123 )" or "MTWRF EVE (8-10) ( 1-234 )".
TIME_REGEX = r"(?<!\(\s)[^MTWRFS]?([MTWRFS]+)\s*(?:([0-9-\.:]+)|(EVE\s*\(\s*(.+?)\s*\)))"

# Matches room numbers and building names
LOCATION_REGEX = r"\(\s*([A-Z0-9,\s-]+)\s*\)"

def parse_schedule(schedule):
    """
    Parse the given schedule string into a standardized format. Returns a
    tuple ({subject_id: schedule string}, quarter information), where quarter
    information may be empty. If no subject IDs are found in the schedule
    string, the schedule dictionary will have the empty string as the only key.

    Schedule:
        Lecture: MWF 10am (10-250)
        Recitation: M 11am (34-301), M 1pm (34-303), M 7pm (34-302), T 10am (34-301)

    Schedule format:
        Lecture,10-250/MWF/0/10;Recitation,34-301/M/0/11,34-303/M/0/1,34-302/M/1/7 PM,34-301/T/0/10
    """

    quarter_info = ""

    if not schedule.strip():
        return "", quarter_info

    # Remove quarter information first
    lower_schedule = schedule.lower()
    match = re.search(QUARTER_INFO_REGEX, lower_schedule)
    if match is not None:
        schedule_type = match.group(1)
        date = match.group(2)
        quarter_info = ("1" if schedule_type == "begins" else "0") + "," + date

    trimmed_schedule = re.sub(QUARTER_INFO_REGEX, "", schedule, flags=re.I)

    for ignore in CatalogConstants.schedule_ignore:
        trimmed_schedule = re.sub(ignore, "", trimmed_schedule, flags=re.I)

    schedule_comps_by_id = {}
    multiple_subjects = False

    for match in re.finditer(CLASS_TYPE_REGEX, trimmed_schedule):
        schedule_type = match.group(1)
        if re.match(SUBJECT_ID_REGEX, schedule_type):
            schedule_comps = schedule_comps_by_id.setdefault(schedule_type, [])
            multiple_subjects = True
            continue
        elif not multiple_subjects:
            schedule_comps = schedule_comps_by_id.setdefault("", [])
        contents = match.group(2)

        type_comps = [schedule_type]
        if "TBA" in contents:
            type_comps.append("TBA")
        else:
            times = contents.split("or")
            for time in times:
                location_start = len(time)
                location_comps = [""]
                location_match = next((match for match in
                                       re.finditer(LOCATION_REGEX, time) if
                                       "PM" not in match.group(1)), None)
                if location_match is not None:
                    # Replace the empty component
                    location_comps = [comp.strip() for comp in location_match.group(1).split(",")]
                    location_start = min(location_start, location_match.start(0))

                time_comps = []
                for submatch in re.finditer(TIME_REGEX, time[:location_start]):
                    time_comps.append(submatch.group(1))
                    if submatch.group(2) is not None:
                        time_comps.append("0")
                        time_comps.append(submatch.group(2))
                    elif submatch.group(4) is not None:
                        time_comps.append("1")
                        time_comps.append(submatch.group(4))
                    else:
                        print("Couldn't get time of day in", time)

                for loc in location_comps:
                    type_comps.append("/".join([loc] + time_comps))

        schedule_comps.append(",".join(type_comps))

    joined_scheds = {id: ";".join(schedule_comps)
                     for id, schedule_comps in schedule_comps_by_id.items()}
    return joined_scheds, quarter_info
