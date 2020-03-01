#  FireRoad - Road File Specification

The FireRoad road file (.road file extension) is a JSON file with a structure as defined below. Earlier versions of FireRoad used a CSV-like format, which from now on will only be read by the FireRoad app (not written).

To see an example of read/write for .road files, see the code in [User.swift](User.swift).

## Top-Level Objects

The top-level object is a dictionary with two keys:

* **numYears** - The number of years to display in the road. The user can edit this value by adding and removing full years (including fall, IAP, spring, and summer) from the end of their road.
* **coursesOfStudy** - A list of courses of study that the user has added (e.g. "major6", "girs"). Each course of study corresponds in name to a requirements list.
* **selectedSubjects** - A list of selected subjects (see below).
* **progressOverrides** - (*Will be deprecated when `substitutions` is implemented*) A dictionary mapping requirement IDs to manual progress values. Requirement IDs are '.'-delimited strings that identify a particular requirements statement. For example, `major3a.2` specifies the 3rd child of the 3-A major, which is a manual progress requirement defined as `""72 units""{>=72u}`. Manual progress values are integers specifying how far the user is toward fulfilling that requirement; the range is determined by the requirements statement. In the previous example, the value may range from 0 to 72.
* **progressAssertions** - (*Supersedes `progressOverrides`*) A dictionary mapping requirement IDs to progress assertion dictionaries. Requirement IDs are defined as in `progressOverrides`, while progress assertions can contain the given keys:
  * `substitutions`: A list of subject ID strings. If this key is present, the user is overriding the given requirement by completing this list of courses instead of the published list. This list may be empty, which corresponds to an automatic fulfillment of the requirement.
  * `ignore`: A boolean indicating whether to ignore this requirement. If this is `true`, then the fulfillment status of this requirement should be ignored when computing parent fulfillment statuses.

## Selected Subjects List

The selected subjects list contains a list of subjects that the user has put on their road. Each subject is represented by a dictionary containing the following keys:

* **subject_id** - The subject ID (e.g. "6.009").
* **title** - The subject title (e.g. "Fundamentals of Programming").
* **units** - The total number of units provided by this subject.
* **semester** - (*Deprecated, use `semester_id` instead*) The semester number in which this subject is placed. The semester numbers are zero indexed, with the order as follows: *Previous Credit, Freshman Fall, Freshman IAP, Freshman Spring, ..., Senior Spring*.
* **semester_id** - (*Supersedes `semester`*) A string ID for the semester in which this subject is placed. Examples of the semester ID include: `prior-credit`, `fall-1` (1st year fall), `IAP-3` (3rd year IAP), `summer-6` (6th year summer).
* **overrideWarnings** - A boolean indicating whether the prereq/coreq and not-offered warnings should be hidden for this subject. 

### Notes

1) The information contained in each subject is intentionally redundant so that the road file can be displayed in a preliminary way without loading the entire course database.
2) The same subject ID may appear multiple times with different semester numbers, if the user selects the same subject for different semesters.
3) Subjects in the selected subjects list may be **generic courses**, which are defined in [Course.swift](Course.swift). 

## Example

```
{
  "coursesOfStudy" : [
    "girs",
    "major6-7"
  ],
  "progressAssertions" : {
    // Fulfill independent inquiry with 21M.387
    "major6-2.1.1" : {
      substitutions : ["21M.387"]
    },
    // Ignore 6.047 in lab subjects
    "major6-2.1.0.2": {
      ignore: true
    }
  },
  "selectedSubjects" : [
    {
      "overrideWarnings" : false,
      "semester_id" : "prior-credit",
      "title" : "Generic Physics I GIR",
      "subject_id" : "PHY1",
      "units" : 12
    },
    {
      "overrideWarnings" : false,
      "semester_id" : "fall-1",
      "title" : "Principles of Chemical Science",
      "subject_id" : "5.112",
      "units" : 12
    },
    {
      "overrideWarnings" : false,
      "semester_id": "fall-2",
      "title" : "Fundamentals of Programming",
      "subject_id" : "6.009",
      "units" : 12
    },
    {
      "overrideWarnings" : false,
      "semester_id" : "fall-2",
      "title" : "Advanced Music Performance",
      "subject_id" : "21M.480",
      "units" : 6
    },
    {
      "overrideWarnings" : false,
      "semester_id" : "spring-2",
      "title" : "Advanced Music Performance",
      "subject_id" : "21M.480",
      "units" : 6
    }
  ]
}
```
