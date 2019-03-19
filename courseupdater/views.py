from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
import os
import json

version_recursion_threshold = 100
separator = "#,#"
module_dir = os.path.dirname(__file__)  # get current directory
global_file_names = ["departments", "enrollment"]
requirements_dir = "requirements"
semester_dir_prefix = "sem-"
delta_file_prefix = "delta-"

def index(request):
    return HttpResponse("Hello, world. You're at the courseupdater index.")

def read_delta(url):
    with open(url, 'r') as file:
        ret = []
        lines = file.readlines()
        if len(lines) > 0:
            ret.append(lines.pop(0).split(separator))
        else:
            ret.append([])
        if len(lines) > 0:
            version = lines.pop(0)
            ret.append(int(version))
        else:
            ret.append(0)
        updated_files = []
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 0:
                updated_files.append(stripped)
        ret.append(updated_files)
        return ret

def compute_updated_files(version, base_dir):
    updated_files = set()
    version_num = version + 1
    updated_version = version
    while version_num < version_recursion_threshold:
        url = os.path.join(base_dir, delta_file_prefix + '{}.txt'.format(version_num))
        if not os.path.exists(url):
            break
        semester, version, delta = read_delta(url)
        if version != version_num:
            print("Wrong version number in {}".format(url))
        updated_files.update(set(delta))
        updated_version = version_num
        version_num += 1
    return updated_files, updated_version

"""Returns the numerical version for the given semester, e.g. "fall-2017"."""
def current_version_for_semester(semester):
    semester_dir = os.path.join(module_dir, semester_dir_prefix + semester)
    max_version = 0
    for path in os.listdir(semester_dir):
        if path.find(delta_file_prefix) == 0:
            ext_index = path.find(".txt")
            version = int(path[len(delta_file_prefix):ext_index])
            if version > max_version:
                max_version = version
    return max_version

def compute_semester_delta(semester_comps, version_num, req_version_num=-1):
    # Walk through the delta files
    semester_dir = semester_dir_prefix + semester_comps[0] + '-' + semester_comps[1]
    updated_files, updated_version = compute_updated_files(version_num, os.path.join(module_dir, semester_dir))

    # Write out the updated files to JSON
    def url_comp(x):
        if x in global_file_names:
            return x + '.txt'
        return semester_dir + '/' + x + '.txt'
    urls_to_update = list(map(url_comp, sorted(list(updated_files))))
    resp = {'v': updated_version, 'delta': urls_to_update}

    # Check requirements also, if necessary
    if req_version_num != -1:
        updated_files, updated_version = compute_updated_files(req_version_num, os.path.join(module_dir, requirements_dir))
        urls_to_update = list(map(lambda x: requirements_dir + '/' + x + '.reql', sorted(list(updated_files))))
        resp['rv'] = updated_version
        resp['r_delta'] = urls_to_update
    return resp

def list_semesters():
    sems = []
    for path in os.listdir(module_dir):
        if path.find(semester_dir_prefix) == 0:
            sems.append(path[len(semester_dir_prefix):])
    def semester_sort_key(x):
        comps = x.split('-')
        return int(comps[1]) * 10 + (5 if comps[0] == "fall" else 0)
    sems.sort(key=semester_sort_key)
    return sems

'''Return an HTTP Response indicating the static file URLs that need to be
downloaded. Every version of the course static file database will include a
'delta-x.txt' file that specifies the semester, the version number, and the file
names that changed from the previous version. This method will compute the total
set of files and return it.'''
def check(request):
    semester = request.GET.get('sem', '')
    comps = semester.split(',')
    if len(comps) != 2:
        return HttpResponseBadRequest('<h1>Invalid number of semester components</h1><br/><p>{}</p>'.format(semester))
    version = request.GET.get('v', '')
    try:
        version_num = int(version)
    except ValueError:
        return HttpResponseBadRequest('<h1>Invalid version</h1><br/><p>{}</p>'.format(version))
    req_version = request.GET.get('rv', '')
    if len(req_version) > 0:
        try:
            req_version_num = int(req_version)
        except ValueError:
            return HttpResponseBadRequest('<h1>Invalid requirements version</h1><br/><p>{}</p>'.format(req_version))
    else:
        req_version_num = -1

    resp = compute_semester_delta(comps, version_num, req_version_num)
    return HttpResponse(json.dumps(resp), content_type="application/json")

"""Return a list of semesters and the most up-to-date version of the catalog for
each one."""
def semesters(request):
    sems = list_semesters()
    resp = list(map(lambda x: {"sem": x, "v": current_version_for_semester(x)}, sems))
    return HttpResponse(json.dumps(resp), content_type="application/json")
