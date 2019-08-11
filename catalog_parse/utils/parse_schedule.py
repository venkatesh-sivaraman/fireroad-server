import numpy as np
import re
from .catalog_constants import *

# For when the schedule string contains multiple subjects, like
# 12.S592: Lecture: xyz
subject_id_regex = r'^([A-Z0-9.-]+)(\[J\])?$'

quarter_info_regex = r"\(?(begins|ends)\s+(.+?)(\.|\))"

# Class type regex matches "Lecture:abc XX:"
class_type_regex = r"([A-z0-9.-]+):(.+?)(?=\Z|\w+:)"

# Time regex matches "MTWRF9-11 ( 1-123 )" or "MTWRF EVE (8-10) ( 1-234 )".
time_regex = r"(?<!\(\s)[^MTWRFS]?([MTWRFS]+)\s*(?:([0-9-\.:]+)|(EVE\s*\(\s*(.+?)\s*\)))"

# Matches room numbers and building names
location_regex = r"\(\s*([A-Z0-9,\s-]+)\s*\)"

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

    if len(schedule.strip()) == 0:
        return "", quarter_info

    # Remove quarter information first
    lower_schedule = schedule.lower()
    match = re.search(quarter_info_regex, lower_schedule)
    if match is not None:
        schedule_type = match.group(1)
        date = match.group(2)
        quarter_info = ("1" if schedule_type == "begins" else "0") + "," + date

    trimmed_schedule = re.sub(quarter_info_regex, "", schedule, flags=re.I)

    for ignore in CatalogConstants.schedule_ignore:
        trimmed_schedule = re.sub(ignore, "", trimmed_schedule, flags=re.I)

    schedule_comps_by_id = {}
    multiple_subjects = False

    for match in re.finditer(class_type_regex, trimmed_schedule):
        schedule_type = match.group(1)
        if re.match(subject_id_regex, schedule_type):
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
                location_match = next((match for match in re.finditer(location_regex, time) if "PM" not in match.group(1)), None)
                if location_match is not None:
                    # Replace the empty component
                    location_comps = [comp.strip() for comp in location_match.group(1).split(",")]
                    location_start = min(location_start, location_match.start(0))

                time_comps = []
                for submatch in re.finditer(time_regex, time[:location_start]):
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

    joined_scheds = {id: ";".join(schedule_comps) for id, schedule_comps in schedule_comps_by_id.items()}
    return joined_scheds, quarter_info
