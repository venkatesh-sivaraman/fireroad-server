import numpy as np
import re
from .catalog_constants import *

def collapse_parentheses(text):
    """
    Removes all parenthetical expressions from the given string and leaves
    open/close parenthesis pairs, so that anything left is unparenthesized.

    Example: a, (b or c), (d and e) => a, (), ()
    """
    mut = ""
    paren_level = 0
    for c in text:
        if c == "(":
            paren_level += 1
            if paren_level == 1: mut += c
        elif c == ")":
            paren_level -= 1
            if paren_level == 0: mut += c
        elif paren_level == 0:
            mut += c
    return mut

information_separator = r'[\r\n/,;-]'

def filter_course_list(list_string):
    """
    Produces an old-style prerequisites list.
    """
    trimmed_list = list_string.replace("(", "").replace(")", "")
    if ";" in trimmed_list:
        comps = trimmed_list.split(";")
        return [subcomp for comp in comps for subcomp in filter_course_list(comp)]

    items = re.split(information_separator, trimmed_list.replace(" or", ",").replace(" and", ","))
    trimmed_items = [item.strip() for item in items]
    if " or" in trimmed_list:
        return [[item for item in trimmed_items if len(item) and CatalogConstants.none not in item.lower()]]

    return [[item] for item in trimmed_items if len(item) and CatalogConstants.none not in item.lower()]


def process_req_list_item(item):
    """
    Convert the registrar site string into a requirements list-parseable string.
    If the requirements contain more than one element, the result is parenthesized.
    """
    filtered_item = item.strip().replace("\n", " ").replace("(GIR)", "[GIR]")
    if len(filtered_item) == 0 or "none" in filtered_item:
        return ""

    # Search for parenthetical groups and replace them with macros
    paren_levels = [""]
    substitutions = {}
    for c in filtered_item:
        if c == "(":
            paren_levels.append("")
        elif c == ")":
            if len(paren_levels) <= 1:
                print(("Invalid prerequisite syntax:", item))
                continue
            sub_key = "#@%" + str(len(substitutions)) + "%@#"
            last_item = paren_levels.pop()
            sub_result = process_single_level_req_item(last_item)
            for key, sub in list(substitutions.items()):
                sub_result = sub_result.replace("''" + key + "''", "(" + sub + ")")
            substitutions[sub_key] = sub_result
            paren_levels[-1] += sub_key
        else:
            paren_levels[-1] += c

    if len(paren_levels) == 0:
        print(("Unmatched parentheses:", item))
    result = process_single_level_req_item(paren_levels[-1])
    for key, sub in list(substitutions.items()):
        result = result.replace("''" + key + "''", "(" + sub + ")")
    return result

# This only handles one level of parenthesization, I think
req_list_comp = r"([^(),;]+(\s*\[GIR\])?|\((.*)\))"
req_list_comp_regex = req_list_comp + r"((\s*,)|(\s+(?=and))|(\s+(?=or)))"
req_list_and_final_regex = r"^\s*(and)?\s*" + req_list_comp + r"\s*;?"
req_list_or_final_regex = r"^\s*or\s*" + req_list_comp + r"\s*;?"

def process_single_level_req_item(item):
    """
    Process a requirements list by considering it as a sequence of parallel items
    connected with an 'and' or an 'or'.
    """

    if len(item) == 0:
        return ""

    filtered_item = item.strip().replace("\n", " ")
    if "none" in filtered_item.lower():
        return ""

    components = []
    is_or = False
    while len(filtered_item) > 0:
        match = re.search(req_list_comp_regex, filtered_item)
        if match is not None:
            current_comp = match.group(1).strip()
            if current_comp[0] == "(" and current_comp[-1] == ")":
                current_comp = current_comp[1:-1]
            components.append(process_single_level_req_item(current_comp))

            filtered_item = filtered_item[match.end(0):].strip()
            continue

        match = re.search(req_list_or_final_regex, filtered_item)
        if match is not None:
            last_comp = match.group(1)
            if last_comp == filtered_item:
                # The component hasn't changed - simply return it
                components.append(last_comp)
            else:
                components.append(process_single_level_req_item(last_comp))
            is_or = True

            filtered_item = filtered_item[match.end(0):].strip()
            continue

        match = re.search(req_list_and_final_regex, filtered_item)
        if match is not None and filtered_item != "or" and filtered_item != "and":
            last_comp = match.group(2)
            if last_comp == filtered_item:
                # The component hasn't changed - simply return it
                components.append(last_comp)
            else:
                components.append(process_single_level_req_item(last_comp))

            filtered_item = filtered_item[match.end(0):].strip()
            continue

        print((filtered_item, "doesn't match anything"))
        break

    if is_or:
        base = "/".join(components)
    else:
        base = ", ".join(components)

    if len(components) > 1:
        return base
    else:
        return process_base_requirement(base)

course_regex = r'([A-z0-9]+)\.([A-z0-9]+)'

def process_base_requirement(item):
    """
    Process an atomic requirement, such as "6.031" or "permission of instructor."
    """
    # Handle GIRs
    if CatalogConstants.gir_suffix in item:
        gir_symbol = item.replace(CatalogConstants.gir_suffix, "").strip()
        gir_id = CatalogConstants.gir_requirements[gir_symbol]
        return "GIR:" + gir_id

    # Handle courses, already-processed items
    match = re.search(course_regex, item)
    if match is not None and match.start(0) == 0:
        return item

    if "GIR:" in item or "''" in item:
        return item

    # The rest are plain strings
    return "''" + item + "''"

def handle_prereq(item, attributes):
    """Fills in the attributes based on the given item."""
    case_insensitive_item = item.lower()
    prereq_position = case_insensitive_item.find(CatalogConstants.prereq_prefix)
    prereq_range = (prereq_position, prereq_position + len(CatalogConstants.prereq_prefix))

    # First check if coreq is in parentheses, then find its range
    if CatalogConstants.coreq_prefix in collapse_parentheses(case_insensitive_item):
        coreq_position = case_insensitive_item.find(CatalogConstants.coreq_prefix)
        coreq_range = (coreq_position, coreq_position + len(CatalogConstants.coreq_prefix))

        prereq_string = item[prereq_range[1]:coreq_range[0]].strip()
        attributes[CourseAttribute.oldPrerequisites] = filter_course_list(prereq_string)
        attributes[CourseAttribute.prerequisites] = process_req_list_item(prereq_string)

        coreq_string = item[coreq_range[1]:]
        attributes[CourseAttribute.oldCorequisites] = filter_course_list(coreq_string)
        attributes[CourseAttribute.corequisites] = process_req_list_item(coreq_string)

        if prereq_string.find(CatalogConstants.either_prereq_or_coreq_flag) + len(CatalogConstants.either_prereq_or_coreq_flag) == len(prereq_string) - 1:
            attributes[CourseAttribute.eitherPrereqOrCoreq] = True

    else:
        attributes[CourseAttribute.oldPrerequisites] = filter_course_list(item[prereq_range[1]:])
        attributes[CourseAttribute.prerequisites] = process_req_list_item(item[prereq_range[1]:])

def handle_coreq(item, attributes):
    """Fills in the corequisite attributes based on the given item."""
    case_insensitive_item = item.lower()
    coreq_position = case_insensitive_item.find(CatalogConstants.coreq_prefix)
    coreq_range = (coreq_position, coreq_position + len(CatalogConstants.coreq_prefix))
    attributes[CourseAttribute.oldCorequisites] = filter_course_list(item[coreq_range[1]:])
    attributes[CourseAttribute.corequisites] = process_req_list_item(item[coreq_range[1]:])
