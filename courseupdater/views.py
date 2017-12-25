from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
import os
import json

version_recursion_threshold = 100
separator = "#,#"
module_dir = os.path.dirname(__file__)  # get current directory
global_file_names = ["departments", "enrollment"]

def index(request):
    return HttpResponse("Hello, world. You're at the courseupdater index.")

def read_delta(url):
    with open(url, 'r') as file:
        ret = []
        lines = file.readlines()
        if len(lines) > 0:
            season, year = lines.pop(0).split(separator)
            ret.append((season, year))
        else:
            ret.append(("none", "none"))
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
        version_num = int(version) + 1
    except ValueError:
        return HttpResponseBadRequest('<h1>Invalid version</h1><br/><p>{}</p>'.format(version))

    # Walk through the delta files
    updated_files = set()
    updated_version = version_num - 1
    semester_dir = comps[0] + '-' + comps[1]
    while version_num < version_recursion_threshold:
        url = os.path.join(module_dir, semester_dir, 'delta-{}.txt'.format(version_num))
        if not os.path.exists(url):
            print("Doesn't exist: {}".format(url))
            break
        semester, version, delta = read_delta(url)
        if version != version_num:
            print("Wrong version number in {}".format(url))
        updated_files.update(set(delta))
        updated_version = version_num
        version_num += 1

    # Write out the updated files to JSON
    def url_comp(x):
        if x in global_file_names:
            return x + '.txt'
        return semester_dir + '/' + x + '.txt'
    urls_to_update = list(map(url_comp, sorted(list(updated_files))))
    resp = {'v': updated_version, 'delta': urls_to_update}
    return HttpResponse(json.dumps(resp), content_type="application/json")
