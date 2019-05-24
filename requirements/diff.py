import re
import numpy as np
from django.utils.html import escape

def best_diff_sequence(old, new, allow_subs=True, max_delta=None):
    """Compute the best diff sequence between the old and new requirements list
    contents. Uses a simple DP-based edit distance algorithm. If allow subs is
    True, the diff sequence may use 0 to denote either substitutions or the same
    value."""

    memo = np.zeros((len(old) + 1, len(new) + 1))

    parent_pointers = np.zeros((len(old) + 1, len(new) + 1))
    parent_pointers[-1,:] = 1
    parent_pointers[:,-1] = -1
    parent_pointers[-1,-1] = 0

    for i in reversed(range(len(old) + 1)):
        for j in reversed(range(len(new) + 1)):
            if i == len(old) and j == len(new): continue
            if max_delta is not None:
                if i - j >= max_delta:
                    parent_pointers[i,j] = 1
                    memo[i,j] = 1e4
                    continue
                elif j - i >= max_delta:
                    parent_pointers[i,j] = -1
                    memo[i,j] = 1e4
                    continue

            options = [] # Format: (score, label)
            if i < len(old) and j < len(new) and (allow_subs or old[i] == new[j]):
                options.append((memo[i+1, j+1] + (max(len(old[i]), len(new[j])) if old[i] != new[j] else 0), 0))
            if i < len(old):
                options.append((memo[i+1, j] + len(old[i]) + 1, -1))
            if j < len(new):
                options.append((memo[i, j+1] + len(new[j]) + 1, 1))

            score, label = min(enumerate(options), key=lambda x: (x[1], x[0]))[1]
            memo[i,j] = score
            parent_pointers[i,j] = label

    best_sequence = []
    i = 0
    j = 0
    while i <= len(old) and j <= len(new):
        best_sequence.append(parent_pointers[i,j])
        if best_sequence[-1] == 0:
            i += 1
            j += 1
        elif best_sequence[-1] == 1:
            j += 1
        elif best_sequence[-1] == -1:
            i += 1
    return best_sequence[:-1]

WORD_FINDER_REGEX = r"[\w'.-]+|[^\w'.-]"

def delete_insert_diff_line(old, new):
    """Builds a basic diff line in which the old text is deleted and the new text
    is inserted."""
    return "<p class=\"diff-line\"><span class=\"deletion\">{}</span><span class=\"insertion\">{}</span></p>\n".format(old, new)

def build_diff_line(old, new, max_delta=None):
    """Builds a single line of the diff."""
    result = "<p class=\"diff-line\">"

    if old == new:
        result += old
    else:
        old_words = re.findall(WORD_FINDER_REGEX, old)
        new_words = re.findall(WORD_FINDER_REGEX, new)
        diff_sequence = best_diff_sequence(old_words, new_words, allow_subs=False, max_delta=max_delta)
        i = 0
        j = 0
        current_change = None
        for change in diff_sequence:
            if change == 0: # Same character (since allow subs is False)
                if current_change is not None:
                    result += "</span>"
                    current_change = None
                result += escape(old_words[i])
                i += 1
                j += 1
            elif change == 1: # Insertion
                if current_change != 1:
                    if current_change is not None:
                        result += "</span>"
                    result += "<span class=\"insertion\">"
                    current_change = 1
                result += escape(new_words[j])
                j += 1
            elif change == -1: # Deletion
                if current_change != -1:
                    if current_change is not None:
                        result += "</span>"
                    result += "<span class=\"deletion\">"
                    current_change = -1
                result += escape(old_words[i])
                i += 1
        if current_change is not None:
            result += "</span>"
    result += "</p>\n"
    return result

def build_diff(old, new, changed_lines_only=False, max_line_delta=None, max_word_delta=None):
    """
    Generates HTML to render a diff between the given two strings.
    """
    old_lines = re.split(r'\r?\n', old)
    new_lines = re.split(r'\r?\n', new + '\n')
    diff_sequence = best_diff_sequence(old_lines, new_lines, max_delta=max_line_delta)
    print("Done diffing lines")
    result = ""
    i = 0
    j = 0
    for change in diff_sequence:
        if change == 0: # Same character (since allow subs is False)
            if old_lines[i] != new_lines[j]:
                result += build_diff_line(old_lines[i], new_lines[j], max_delta=max_word_delta)
            i += 1
            j += 1
        elif change == 1: # Insertion
            result += "<p class=\"diff-line\"><span class=\"insertion\">" + escape(new_lines[j]) + "</span></p>\n"
            j += 1
        elif change == -1: # Deletion
            result += "<p class=\"diff-line\"><span class=\"deletion\">" + escape(old_lines[i]) + "</span></p>\n"
            i += 1
    return result
