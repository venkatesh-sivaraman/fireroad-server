import os, sys, math
import csv
import re
from nltk import sent_tokenize, word_tokenize, pos_tag
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
import random
from collections import deque
from .catalog_constants import *

equiv_subject_keys = [
    CourseAttribute.equivalentSubjects,
    CourseAttribute.jointSubjects,
    CourseAttribute.meetsWithSubjects
]

KEYWORD_COVERAGE_TRIM = 0.25  # Remove top-covering 10% (common but technical words)

# Set this flag to true to prevent using NLTK and WordNet to improve keyword accuracy
FAST = False

def process_list_item(list_item):
    if len(list_item) > 0:
        #mod_value = re.sub(r'permission of instructor', 'POI', line[list_item], flags=re.IGNORECASE)
        mod_value = list_item.replace("Physics I", "GIR:PHY1")
        mod_value = mod_value.replace("Physics II", "GIR:PHY2")
        mod_value = mod_value.replace("Calculus I", "GIR:CAL1")
        mod_value = mod_value.replace("Calculus II", "GIR:CAL2")
        mod_value = re.sub(r'[A-z](?=[a-z])[a-z]+', ',', list_item)
        mod_value = mod_value.replace(';', ',')
        temp_mod = mod_value
        bracketize = False
        values = []
        for comp in temp_mod.split(","):
            if "[" in comp and "]" in comp:
                values.append(comp)
                bracketize = False
            elif "[" in comp:
                bracketize = True
                values.append(comp + "]")
            elif "]" in comp:
                if bracketize:
                    values.append("[" + comp)
                else:
                    values.append(comp)
                bracketize = False
            else:
                if bracketize:
                    values.append("[" + comp + "]")
                else:
                    values.append(comp)
        return ",".join(values)
    return list_item

def wordnet_pos_code(tag):
    if tag.startswith('NN'):
        return wordnet.NOUN
    elif tag.startswith('VB'):
        return wordnet.VERB
    elif tag.startswith('JJ'):
        return wordnet.ADJ
    elif tag.startswith('RB'):
        return wordnet.ADV
    else:
        return ''

def term_frequencies(description):
    """
    Returns a dict where each key corresponds to a word, and the value is the frequency of that word in the description string.
    """
    ret = {}
    sentences = [description.lower()] if FAST else sent_tokenize(description.lower())
    for sentence in sentences:
        comps = word_tokenize(sentence) #re.split(r'[^A-z0-9\'-]+', description.lower())
        lemmatizer = WordNetLemmatizer()
        if not FAST:
            poses = pos_tag(comps)
        else:
            poses = comps
        for item in poses:
            if not FAST:
                word, pos = item
            else:
                word = item
            if len(word) <= 3 or "." in word or "," in word or ";" in word or sum([1 for c in word if c.isdigit()]) >= len(word) / 2: continue
            if FAST:
                lemma = word
            else:
                pos_code = wordnet_pos_code(pos)
                if len(pos_code) > 0:
                    lemma = lemmatizer.lemmatize(word, pos=pos_code)
                else:
                    lemma = word
            if lemma in ret:
                ret[lemma] += 1
            else:
                ret[lemma] = 1
    return ret

def tf_idf(tf_list, all_term_frequencies):
    scores = {}
    for word, frequency in tf_list.items():
        idf = math.log(len(all_term_frequencies) / sum(1 for x in all_term_frequencies.values() if word in x))
        scores[word] = frequency * idf
    return scores

def doc_distance(tf1, tf2):
    """
    Computes a dot-product for the two term-frequency dictionaries provided. Returns float; higher numbers mean better correlation.
    """
    common_words = set(tf1.keys()) & set(tf2.keys())
    ret = 0.0
    for word in common_words:
        ret += tf1[word] * tf2[word] * math.log(len(word))
    return ret

def is_equivalent(id, course, other_id):
    """Returns True if the given other ID is equal or in the equivalent subjects
    for the given course."""
    return other_id == id or other_id in course.get(CourseAttribute.equivalentSubjects, []) or other_id in course.get(CourseAttribute.jointSubjects, []) or other_id in course.get(CourseAttribute.meetsWithSubjects, [])

def write_course_features(courses_by_dept, tf_lists, related_matrix, outpath, max_keywords=5, min_keywords=1):
    # Use the below code to input min count and threshold at runtime
    '''comps = input("Choose min_count,threshold:").split(",")
    while len(comps) == 2:
        related_regions = find_related_regions(related_matrix, min_count=int(comps[0]), threshold=float(comps[1]))
        print("Related regions: ")
        for region in related_regions:
            print(region)
        comps = input("Choose min_count,threshold:").split(",")'''
    related_regions = find_related_regions(related_matrix)
    print("Related regions: ")
    for region in related_regions:
        print(region)

    keywords_by_subject = {}
    subjects_by_keyword = {}
    max_generated_keywords = max_keywords * 3
    for dept, courses in courses_by_dept.items():
        print(dept)
        for id, course in courses.items():
            if id not in tf_lists: continue
            tfidf = tf_idf(tf_lists[id], tf_lists)
            sorted_items = sorted(tfidf, key=tfidf.get, reverse=True)
            if len(sorted_items) > max_generated_keywords:
                sorted_items = sorted_items[:max_generated_keywords]
            keywords_by_subject[id] = sorted_items
            for keyword in sorted_items:
                if keyword in subjects_by_keyword:
                    subjects_by_keyword[keyword].append(id)
                else:
                    subjects_by_keyword[keyword] = [id]
    # Find the minimum number of keywords that capture the entire course database
    sorted_keywords = sorted(subjects_by_keyword, key=lambda x: (len(subjects_by_keyword[x]), len(x)), reverse=True)
    sorted_keywords = sorted_keywords[int(len(sorted_keywords) * KEYWORD_COVERAGE_TRIM):]
    print("Total: {} keywords. Top 100:".format(len(sorted_keywords)))
    print(sorted_keywords[:100])

    covered_subjects = set()
    partially_covered_subjects = set()
    necessary_keywords = set()
    for keyword in sorted_keywords:
        new_subjects = subjects_by_keyword[keyword]
        if any(subj not in covered_subjects for subj in new_subjects):
            necessary_keywords.add(keyword)
            # Update covered and incomplete subject sets
            for subject in new_subjects:
                if sum([1 for kw in keywords_by_subject[subject] if kw in necessary_keywords]) >= min_keywords:
                    covered_subjects.add(subject)
                else:
                    partially_covered_subjects.add(subject)
        if len(covered_subjects) == len(keywords_by_subject):
            break
    print("Needed {} keywords to cover dataset: {}".format(len(necessary_keywords), necessary_keywords))
    with open(outpath, 'w') as file:
        for dept, courses in courses_by_dept.items():
            for id in courses:
                if id not in keywords_by_subject:
                    print("No keywords for {}".format(id))
                    continue
                keywords = keywords_by_subject[id]
                allowed_keywords = [kw for kw in keywords if kw in necessary_keywords]
                if len(allowed_keywords) > max_keywords:
                    allowed_keywords = allowed_keywords[:max_keywords]
                region_indexes = ['r' + str(i) for i, region in enumerate(related_regions) if id in region]
                if CourseAttribute.subjectLevel in courses[id]:
                    level_list = ["level" + courses[id][CourseAttribute.subjectLevel]]
                else:
                    level_list = []

                # Get other relevant departments using equivalent subjects
                depts = set([dept])
                for equiv_key in equiv_subject_keys:
                    for other_course in courses[id].get(equiv_key, []):
                        if '.' not in other_course: continue
                        depts.add(other_course[:other_course.find('.')])
                file.write(",".join([id] + list(depts) + level_list + allowed_keywords + region_indexes) + "\n")

def find_related_regions(related_matrix, min_count=5, threshold=0.2):
    """
    Finds and returns sets of at least min_count subjects that have a value in
    the related_matrix of at least threshold. The return format is a list of sets.
    """
    filtered_matrix = {}
    for subject in related_matrix:
        filtered_matrix[subject] = {subject_2: relation for subject_2, relation in related_matrix[subject].items() if relation >= threshold}

    sets = []
    discovered_subjects = set()
    max_count = min_count * 4
    for subject in related_matrix:
        if subject in discovered_subjects: continue
        putative_set = set()
        subject_stack = deque([subject])
        while len(putative_set) < max_count and len(subject_stack) > 0:
            current_subject = subject_stack.popleft()
            if current_subject in discovered_subjects:
                continue
            neighbors = [x for x in filtered_matrix[current_subject] if x not in putative_set]
            neighbors.sort(key=lambda x: filtered_matrix[current_subject][x], reverse=True)
            subject_stack.extend(neighbors)
            discovered_subjects.add(current_subject)
            putative_set.add(current_subject)
        if len(putative_set) >= min_count:
            sets.append(putative_set)
    return sets


# Todo: Implement APSP (Floyd-Warshall) for the relevance scores and produce a matrix that gives the relationship between any two courses.

def write_related_and_features(courses_by_dept, dest, progress_callback=None, progress_start=None):
    """
    courses_by_dept should be a dictionary of department codes to dictionaries
    {subject_id: course_dict}.
    dest should be a directory at which to write the related and features files.
    progress_callback should be a function taking the current progress (from 0-100)
        and a string describing the current task.
    progress_start may be a number from 0-100 from which the progress should start.
    """
    tf_lists = {}
    k = 10

    if progress_callback is not None:
        start = progress_start if progress_start is not None else 0.0
        progress_callback(start + 0.1 * (100.0 - start), "Computing term frequencies...")
    print("Computing term frequencies...")

    for dept, courses in courses_by_dept.items():
        for id, course in courses.items():
            tf_lists[id] = term_frequencies(course.get(CourseAttribute.description, "") + "\n" + course.get(CourseAttribute.title, ""))

    if progress_callback is not None:
        start = progress_start if progress_start is not None else 0.0
        progress_callback(start + 0.2 * (100.0 - start), "Writing related courses...")
    print("Writing related courses...")

    # First determine which departments are closely related to each other
    dept_lists = {}
    for dept, courses in courses_by_dept.items():
        for id, course in courses.items():
            if dept not in dept_lists: dept_lists[dept] = {}
            for term, freq in tf_lists[id].items():
                if term in dept_lists[dept]:
                    dept_lists[dept][term] += freq
                else:
                    dept_lists[dept][term] = freq

    dept_similarities = {}
    for dept1 in dept_lists:
        for dept2 in dept_lists:
            if len(dept_lists[dept1]) == 0 or len(dept_lists[dept2]) == 0:
                dept_similarities[(dept1, dept2)] = 0.00001
                dept_similarities[(dept2, dept1)] = 0.00001
                continue
            sim = max(doc_distance(dept_lists[dept1], dept_lists[dept2]) ** 2 / (doc_distance(dept_lists[dept1], dept_lists[dept1]) * doc_distance(dept_lists[dept2], dept_lists[dept2])), 0.00001)
            #sim = math.log(sim) / math.log(2.0)
            dept_similarities[(dept1, dept2)] = sim
            dept_similarities[(dept2, dept1)] = sim

    progress = 0
    progress_stepwise = 0
    related_matrix = {}
    related_max = 1e20
    max_relation = -1e20

    with open(os.path.join(dest, "related.txt"), "w") as file:
        for dept, courses in courses_by_dept.items():
            for id, course in courses.items():

                related_matrix[id] = {}
                ranks = [("", 0) for i in range(k)]
                for other_id, tf in tf_lists.items():
                    if is_equivalent(id, course, other_id):
                        related_matrix[id][other_id] = related_max
                        continue
                    if other_id in related_matrix:
                        dist = related_matrix[other_id][id]
                    else:
                        dist = doc_distance(tf_lists[id], tf) * dept_similarities[(dept, other_id[:other_id.find(".")])]
                    related_matrix[id][other_id] = dist
                    if dist == related_max:
                        continue
                    if dist > max_relation:
                        max_relation = dist
                    for i in range(k):
                        if dist >= ranks[i][1]:
                            comp_dept = ranks[i][0][:ranks[i][0].find(".")]
                            if comp_dept in courses_by_dept:
                                comp_course = courses_by_dept[comp_dept][ranks[i][0]]
                                if (other_id == ranks[i][0] or is_equivalent(ranks[i][0], comp_course, other_id)) and comp_dept != dept: break
                            ranks.insert(i, (other_id, dist))
                            del ranks[-1]
                            break
                ranks = [[x, "{:.3f}".format(y)] for x, y in ranks if y > 0]
                file.write(','.join([id] + [item for sublist in ranks for item in sublist]) + '\n')
            progress += 1
            if round(progress / len(courses_by_dept) * 10.0) == progress_stepwise + 1:
                progress_stepwise += 1

                if progress_callback is not None:
                    start = progress_start if progress_start is not None else 0.0
                    progress_callback(start + (0.2 + progress_stepwise / 17) * (100.0 - start), "Writing related courses...")
                print("{}% complete...".format(progress_stepwise * 10))

    # Divide every element in the relation matrix by the maximum attained value
    for subject in related_matrix:
        related_matrix[subject] = {subject_2: min(value / max_relation, 1.0) for subject_2, value in related_matrix[subject].items()}

    if progress_callback is not None:
        start = progress_start if progress_start is not None else 0.0
        progress_callback(start + 0.9 * (100.0 - start), "Computing course features...")
    print("Computing course features...")
    write_course_features(courses_by_dept, tf_lists, related_matrix, os.path.join(dest, "features.txt"))
