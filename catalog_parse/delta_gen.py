'''
This script will compare the files in the two provided directories (if the old
catalog exists) and produce a delta file that enumerates which files have changed.
This file will be saved in the appropriate directory within server_path (a variable
set at the top of this script). The version number is automatically detected based
on which delta files are already present in this location.
'''

import os
import sys
import shutil

SEMESTER_PREFIX = "sem-"
DELTA_PREFIX = "delta-"
DELTA_SEPARATOR = "#,#"
REQUIREMENTS_DIR_NAME = "requirements"
EXCLUDED_FILE_NAMES = ["features.txt"]

# These file names will be concatenated to the delta file if the version number is 1.
FIRST_VERSION_FILE_NAMES = ["departments", "enrollment"]

def write_delta_file(semester_name, delta, outpath):
    """Writes a file to the given path describing a change to the catalog
    involving the given list of files.

    Args:
       - semester_name: The name for the semester, such as 'fall-2019'.
       - delta: A list of files that changed in this change to the catalog.
       - outpath: A directory in which to save the delta file.
    """
    # Determine version number
    version_num = 1
    if os.path.exists(outpath):
        while os.path.exists(os.path.join(outpath, DELTA_PREFIX + str(version_num) + ".txt")):
            version_num += 1
    else:
        os.mkdir(outpath)
    if version_num == 1:
        delta = delta + FIRST_VERSION_FILE_NAMES

    comps = semester_name.split('-')
    delta_file_path = os.path.join(outpath, DELTA_PREFIX + str(version_num) + ".txt")
    with open(delta_file_path, 'w') as delta_file:
        if semester_name != REQUIREMENTS_DIR_NAME:
            delta_file.write(DELTA_SEPARATOR.join(comps) + "\n")
        else:
            delta_file.write("\n")
        delta_file.write(str(version_num) + "\n")
        delta_file.write("\n".join(delta))

    print("Delta file written to {}.".format(delta_file_path))

def delta_file_name(path):
    """Determines the correct filename by stripping the file extension of txt
    and reql files."""
    if ".txt" in path:
        return path[:path.find(".txt")]
    elif ".reql" in path:
        return path[:path.find(".reql")]
    return path

def make_delta(new_directory, old_directory):
    """Computes a list of file names that have changed between the old directory
    and the new directory."""
    delta = []
    for path in os.listdir(new_directory):
        if path[0] == '.' or path in EXCLUDED_FILE_NAMES:
            continue
        old_path = os.path.join(old_directory, path)
        if not os.path.exists(old_path):
            delta.append(delta_file_name(path))
            continue
        with open(os.path.join(new_directory, path), 'r') as new_file:
            with open(old_path, 'r') as old_file:
                new_lines = new_file.readlines()
                old_lines = old_file.readlines()
                if new_lines != old_lines:
                    delta.append(delta_file_name(path))
    return delta

def commit_delta(new_directory, old_directory, server_path, delta):
    """Writes the delta to file, and moves the contents of new_directory into
    old_directory (preserving the old contents in an '-old' directory)."""

    old_name = os.path.basename(old_directory)
    if SEMESTER_PREFIX in old_name:
        semester_name = old_name[old_name.find(SEMESTER_PREFIX) + len(SEMESTER_PREFIX):]
    else:
        semester_name = old_name

    write_delta_file(semester_name, delta, os.path.join(server_path, old_name))
    old_dest = os.path.join(os.path.dirname(old_directory), old_name + "-old")
    if os.path.exists(old_dest):
        shutil.rmtree(old_dest)
    if os.path.exists(old_directory):
        shutil.move(old_directory, old_dest)
    shutil.move(new_directory, old_directory)

def main():
    """Generates delta files from the command line."""
    if len(sys.argv) < 4:
        print(("Insufficient arguments. Pass the directory of new files, the "
               "directory that the files should be saved to (e.g. sem-spring-"
               "2018), and the path to the courseupdater directory in the "
               "server. Make sure you do not add trailing slashes to your "
               "paths."))
        exit(1)
    new_directory = sys.argv[1]
    old_directory = sys.argv[2]
    old_name = os.path.basename(old_directory)
    server_path = sys.argv[3]
    print("Changed items:")
    delta = make_delta(new_directory, old_directory)
    for changed_file in delta:
        print(changed_file)
    if raw_input("Ready to write files?") in ['y', 'yes', '\n']:
        commit_delta(new_directory, old_directory, server_path, delta)
        print("Old files moved to {}. New files moved to {}.".format(
            os.path.join(os.path.dirname(old_directory), old_name + "-old"),
            old_directory))
    else:
        print("Aborting.")

if __name__ == '__main__':
    main()
