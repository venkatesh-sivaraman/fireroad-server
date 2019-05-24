"""
Takes a directory with various semesters of "raw" catalog information, and
synthesizes them into a "consensus" catalog containing the most recent version
of each course. The related file is copied directly from the most recent semester.
"""

import os
import sys
import csv
import pandas as pd
import numpy as np

SUBJECT_ID_KEY = 'Subject Id'
CORRECTIONS = 'corrections'

CONDENSED_KEYS = [
        #"Subject Id",  included by default
        "Subject Title",
        "Subject Level",
        "Total Units",
        "Prereqs",
        "Coreqs",
        "Prerequisites",
        "Corequisites",
        "Prereq or Coreq",
        "Joint Subjects",
        "Equivalent Subjects",
        "Meets With Subjects",
        "Not Offered Year",
        "Is Offered Fall Term",
        "Is Offered Iap",
        "Is Offered Spring Term",
        "Is Offered Summer Term",
        "Quarter Information",
        "Instructors",
        "Comm Req Attribute",
        "Hass Attribute",
        "Gir Attribute",
        "In-Class Hours",
        "Out-of-Class Hours",
        "Enrollment",
        "Source Semester",
        "Historical"
]

def semester_sort_key(x):
    if x == CORRECTIONS:
        return 1e9
    comps = x.split('-')
    return int(comps[2]) * 10 + (5 if comps[1] == "fall" else 0)

def build_consensus(base_path, out_path):
    if not os.path.exists(out_path):
        os.mkdir(out_path)

    semester_data = {}
    corrections_path = os.path.join(base_path, CORRECTIONS + '.txt')
    if os.path.exists(corrections_path):
        semester_data[CORRECTIONS] = pd.read_csv(corrections_path, dtype=str).replace(np.nan, '', regex=True)

    for semester in os.listdir(base_path):
        if 'sem-' not in semester: continue
        all_courses = pd.read_csv(os.path.join(base_path, semester, 'courses.txt'), dtype=str).replace(np.nan, '', regex=True)
        semester_data[semester] = all_courses

    # Sort in reverse chronological order
    semester_data = sorted(semester_data.items(), key=lambda x: semester_sort_key(x[0]), reverse=True)
    if len(semester_data) == 0:
        print("No raw semester data found.")
        return

    # Build consensus by iterating from new to old
    consensus = None
    last_size = 0
    i = 0
    for semester, data in semester_data:
        if semester == CORRECTIONS:
            data['Source Semester'] = semester
            data['Historical'] = ""
        else:
            data['Source Semester'] = semester[semester.find("-") + 1:]
            data['Historical'] = "Y" if (i != 0) else ""

        if consensus is None:
            consensus = data
        else:
            consensus = pd.concat([consensus, data])

        consensus = consensus.drop_duplicates(subset=[SUBJECT_ID_KEY], keep='first')
        print("Added {} courses with {}.".format(len(consensus) - last_size, semester))
        last_size = len(consensus)
        if semester != CORRECTIONS:
            i += 1
    consensus.set_index(SUBJECT_ID_KEY, inplace=True)

    print("Writing courses...")
    seen_departments = set()
    for subject_id in consensus.index:
        if "." not in subject_id: continue
        dept = subject_id[:subject_id.find(".")]
        if dept in seen_departments: continue

        dept_courses = consensus[consensus.index.str.startswith(dept + ".")]
        write_df(dept_courses, os.path.join(out_path, dept + ".txt"))
        seen_departments.add(dept)

    write_df(consensus, os.path.join(out_path, "courses.txt"))
    write_condensed_files(consensus, out_path)

    # Copy related file
    related_path = os.path.join(base_path, semester_data[0][0], "related.txt")
    if os.path.exists(related_path):
        with open(related_path, 'r') as file:
            with open(os.path.join(out_path, "related.txt"), 'w') as outfile:
                for line in file:
                    outfile.write(line)

def write_condensed_files(consensus, out_path, split_count=4):
    for i in range(split_count):
        lower_bound = int(i / 4.0 * len(consensus))
        upper_bound = min(len(consensus), int((i + 1) / 4.0 * len(consensus)))
        write_df(consensus[CONDENSED_KEYS].iloc[lower_bound:upper_bound], os.path.join(out_path, "condensed_{}.txt".format(i)))

def write_df(df, path):
    """Writes the df to the given path with appropriate quoting."""
    with open(path, 'w') as file:
        file.write(','.join(['Subject Id'] + list(df.columns)) + '\n')
        file.write(df.to_csv(header=False, quoting=csv.QUOTE_NONNUMERIC).replace('""', ''))

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Provide the directory containing raw semester catalog data, and the directory into which to write the output.")
        exit()

    in_path = sys.argv[1]
    out_path = sys.argv[2]

    if os.path.exists(out_path):
        print("Fatal: the directory {} already exists. Please delete it or choose a different location.".format(out_path))
        exit(1)

    build_consensus(in_path, out_path)
