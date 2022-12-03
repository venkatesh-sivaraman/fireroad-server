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

semester_prefix = "sem-"
delta_prefix = "delta-"
delta_separator = "#,#"
requirements_dir_name = "requirements"
excluded_file_names = ["features.txt"]

# These file names will be concatenated to the delta file if the version number is 1.
first_version_file_names = ["departments", "enrollment"]

def write_delta_file(semester_name, delta, outpath):
    # Determine version number
    version_num = 1
    if os.path.exists(outpath):
        while os.path.exists(os.path.join(outpath, delta_prefix + str(version_num) + ".txt")):
            version_num += 1
    else:
        os.mkdir(outpath)
    if version_num == 1:
        delta = delta + first_version_file_names

    comps = semester_name.split('-')
    delta_file_path = os.path.join(outpath, delta_prefix + str(version_num) + ".txt")
    with open(delta_file_path, 'w') as file:
        if semester_name != requirements_dir_name:
            file.write(delta_separator.join(comps) + "\n")
        else:
            file.write("\n")
        file.write(str(version_num) + "\n")
        file.write("\n".join(delta))

    print(("Delta file written to {}.".format(delta_file_path)))

def delta_file_name(path):
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
        if path[0] == '.' or path in excluded_file_names: continue
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
    if semester_prefix in old_name:
        semester_name = old_name[old_name.find(semester_prefix) + len(semester_prefix):]
    else:
        semester_name = old_name

    write_delta_file(semester_name, delta, os.path.join(server_path, old_name))
    old_dest = os.path.join(os.path.dirname(old_directory), old_name + "-old")
    if os.path.exists(old_dest):
        shutil.rmtree(old_dest)
    if os.path.exists(old_directory):
        shutil.move(old_directory, old_dest)
    shutil.move(new_directory, old_directory)

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Insufficient arguments. Pass the directory of new files, the directory that the files should be saved to (e.g. sem-spring-2018), and the path to the courseupdater directory in the server. Make sure you do not add trailing slashes to your paths.")
        exit(1)
    new_directory = sys.argv[1]
    old_directory = sys.argv[2]
    server_path = sys.argv[3]
    print("Changed items:")
    delta = make_delta(new_directory, old_directory)
    for file in delta:
        print(file)
    if eval(input("Ready to write files?")) in ['y', 'yes', '\n']:
        commit_delta(new_directory, old_directory, server_path, delta)
        print(("Old files moved to {}. New files moved to {}.".format(os.path.join(os.path.dirname(old_directory), old_name + "-old"), old_directory)))
    else:
        print("Aborting.")
