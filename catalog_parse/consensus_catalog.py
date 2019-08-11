"""
Takes a directory with various semesters of "raw" catalog information, and
synthesizes them into a "consensus" catalog containing the most recent version
of each course. The related file is copied directly from the most recent semester.
"""

import os
import sys
import csv
import re
import pandas as pd
import numpy as np
from .utils.catalog_constants import *

KEYS_TO_WRITE = [key for key in CONDENSED_ATTRIBUTES if key != CourseAttribute.subjectID] + [CourseAttribute.sourceSemester, CourseAttribute.isHistorical]

def semester_sort_key(x):
    comps = x.split('-')
    return int(comps[2]) * 10 + (5 if comps[1] == "fall" else 0)

def make_corrections(corrections, consensus):
    """Based on the given correction dictionary objects, modifies
    the appropriate fields in the given consensus dataframe."""
    for correction in corrections:
        subject_id = correction["Subject Id"]
        if '*' in subject_id:
            # Use regex matching to find appropriate rows
            regex = re.escape(subject_id).replace('\*', '.')
            consensus_rows = consensus[consensus.index.str.match(regex)]
            for idx, consensus_row in consensus_rows.iterrows():
                for col in correction:
                    if col == "Subject Id": continue
                    if correction[col]:
                        if col not in consensus.columns:
                            consensus[col] = ""
                        print("Correction for {}: {} ==> {}".format(idx, col, correction[col]))
                        consensus.ix[idx][col] = correction[col]

        elif subject_id in consensus.index:
            # Find the subject in the consensus dataframe
            consensus_row = consensus.ix[subject_id]
            for col in correction:
                if col == "Subject Id": continue
                if correction[col]:
                    print("Correction for {}: {} ==> {}".format(subject_id, col, correction[col]))
                    consensus_row[col] = correction[col]

        else:
            # Add the subject
            print("Correction: adding subject {}".format(subject_id))
            consensus.loc[subject_id] = {col: correction.get(col, None) for col in consensus.columns}


def build_consensus(base_path, out_path, corrections=None):
    if not os.path.exists(out_path):
        os.mkdir(out_path)

    semester_data = {}

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
        data[CourseAttribute.sourceSemester] = semester[semester.find("-") + 1:]
        data[CourseAttribute.isHistorical] = "Y" if (i != 0) else ""

        if consensus is None:
            consensus = data
        else:
            consensus = pd.concat([consensus, data], sort=False)

        consensus = consensus.drop_duplicates(subset=[CourseAttribute.subjectID], keep='first')
        print("Added {} courses with {}.".format(len(consensus) - last_size, semester))
        last_size = len(consensus)
        i += 1

    consensus.set_index(CourseAttribute.subjectID, inplace=True)
    make_corrections(corrections, consensus)

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

    # Copy the first available related file
    for semester, data in semester_data:
        related_path = os.path.join(base_path, semester, "related.txt")
        if os.path.exists(related_path):
            with open(related_path, 'r') as file:
                with open(os.path.join(out_path, "related.txt"), 'w') as outfile:
                    for line in file:
                        outfile.write(line)
            break

def write_condensed_files(consensus, out_path, split_count=4):
    for i in range(split_count):
        lower_bound = int(i / 4.0 * len(consensus))
        upper_bound = min(len(consensus), int((i + 1) / 4.0 * len(consensus)))
        write_df(consensus[KEYS_TO_WRITE].iloc[lower_bound:upper_bound], os.path.join(out_path, "condensed_{}.txt".format(i)))

def write_df(df, path):
    """Writes the df to the given path with appropriate quoting."""
    with open(path, 'w') as file:
        file.write(','.join([CourseAttribute.subjectID] + list(df.columns)) + '\n')
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
