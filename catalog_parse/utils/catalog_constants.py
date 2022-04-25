class CatalogConstants:
    equivalent_subj_prefix = "credit cannot also be received for"
    not_offered_prefix = "not offered academic year "
    units_prefix = "units:"
    units_arranged_prefix = "units arranged"
    prereq_prefix = "prereq:"
    coreq_prefix = "coreq:"
    meets_with_prefix = "subject meets with"
    joint_subj_prefix = "same subject as"
    pdf_string = "[P/D/F]"

    undergrad = "undergrad"
    graduate = "graduate"
    undergradValue = "U"
    graduateValue = "G"
    fall = "fall"
    spring = "spring"
    iap = "iap"
    summer = "summer"

    staff = "staff"
    none = "none"

    url_prefix = "http"

    either_prereq_or_coreq_flag = " or"

    hassH = "hass humanities"
    hassA = "hass arts"
    hassS = "hass social sciences"
    hassE = "hass elective"
    hassABasic = "arts"
    hassHBasic = "humanities"
    hassSBasic = "social sciences"
    hassEBasic = "elective"

    ciH = "communication intensive hass"
    ciHW = "communication intensive writing"
    ciH_abbreviation = "CI-H"
    ciHW_abbreviation = "CI-HW"
    hassH_abbreviation = "HASS-H"
    hassA_abbreviation = "HASS-A"
    hassS_abbreviation = "HASS-S"
    hassE_abbreviation = "HASS-E"

    schedule_ignore = [r"for audition info go to:\.?\s+.+?\.\s+"]

    @staticmethod
    def abbreviation(attribute):
        if attribute.lower() == CatalogConstants.hassH:
            return CatalogConstants.hassH_abbreviation
        elif attribute.lower() == CatalogConstants.hassA:
            return CatalogConstants.hassA_abbreviation
        elif attribute.lower() == CatalogConstants.hassS:
            return CatalogConstants.hassS_abbreviation
        elif attribute.lower() == CatalogConstants.hassE:
            return CatalogConstants.hassE_abbreviation
        if attribute.lower() == CatalogConstants.hassHBasic:
            return CatalogConstants.hassH_abbreviation
        elif attribute.lower() == CatalogConstants.hassABasic:
            return CatalogConstants.hassA_abbreviation
        elif attribute.lower() == CatalogConstants.hassSBasic:
            return CatalogConstants.hassS_abbreviation
        elif attribute.lower() == CatalogConstants.hassEBasic:
            return CatalogConstants.hassE_abbreviation
        elif attribute.lower() == CatalogConstants.ciH:
            return CatalogConstants.ciH_abbreviation
        elif attribute.lower() == CatalogConstants.ciHW:
            return CatalogConstants.ciHW_abbreviation
        else:
            print("Don't have an abbreviation for \(attribute)")
            return attribute

    final_flag = "+final"

    gir_requirements = {
        "1/2 Rest Elec in Sci & Tech": "RST2",
        "Rest Elec in Sci & Tech": "REST",
        "Physics I": "PHY1",
        "Physics II": "PHY2",
        "Calculus I": "CAL1",
        "Calculus II": "CAL2",
        "Chemistry": "CHEM",
        "Biology": "BIOL",
        "Institute Lab": "LAB",
        "Partial Lab": "LAB2"
    }

    joint_class = "[J]"
    gir_suffix = "[GIR]"

class CourseAttribute:
    subjectID = "Subject Id"
    title = "Subject Title"
    description = "Subject Description"
    offeredFall = "Is Offered Fall Term"
    offeredIAP = "Is Offered Iap"
    offeredSpring = "Is Offered Spring Term"
    offeredSummer = "Is Offered Summer Term"
    lectureUnits = "Lecture Units"
    labUnits = "Lab Units"
    preparationUnits = "Preparation Units"
    totalUnits = "Total Units"
    isVariableUnits = "Is Variable Units"
    pdfOption = "PDF Option"
    hasFinal = "Has Final"
    instructors = "Instructors"
    oldPrerequisites = "Prerequisites"
    oldCorequisites = "Corequisites"
    prerequisites = "Prereqs"
    corequisites = "Coreqs"
    notes = "Notes"
    schedule = "Schedule"
    virtualStatus = "Virtual Status"
    notOfferedYear = "Not Offered Year"
    hassRequirement = "Hass Attribute"
    GIR = "Gir Attribute"
    communicationRequirement = "Comm Req Attribute"
    meetsWithSubjects = "Meets With Subjects"
    jointSubjects = "Joint Subjects"
    equivalentSubjects = "Equivalent Subjects"
    URL = "URL"
    quarterInformation = "Quarter Information"
    subjectLevel = "Subject Level"
    eitherPrereqOrCoreq = "Prereq or Coreq"

    # Old subject ID (renumbering)
    oldID = "Old Subject Id"

    # Evaluation fields
    averageRating = "Rating"
    averageInClassHours = "In-Class Hours"
    averageOutOfClassHours = "Out-of-Class Hours"
    raterCount = "Rater Count"
    enrollment = "Enrollment"

    # Equivalences
    parent = "Parent"
    children = "Children"

    # post-parsing keys
    sourceSemester = "Source Semester"
    isHistorical = "Historical"
    halfClass = "Half Class"

ALL_ATTRIBUTES = [
    CourseAttribute.subjectID,
    CourseAttribute.title,
    CourseAttribute.subjectLevel,
    CourseAttribute.lectureUnits,
    CourseAttribute.labUnits,
    CourseAttribute.preparationUnits,
    CourseAttribute.totalUnits,
    CourseAttribute.isVariableUnits,
    CourseAttribute.halfClass,
    CourseAttribute.hasFinal,
    CourseAttribute.GIR,
    CourseAttribute.communicationRequirement,
    CourseAttribute.hassRequirement,
    CourseAttribute.prerequisites,
    CourseAttribute.corequisites,
    CourseAttribute.oldPrerequisites,
    CourseAttribute.oldCorequisites,
    CourseAttribute.eitherPrereqOrCoreq,
    CourseAttribute.oldID,
    CourseAttribute.description,
    CourseAttribute.jointSubjects,
    CourseAttribute.meetsWithSubjects,
    CourseAttribute.equivalentSubjects,
    CourseAttribute.notOfferedYear,
    CourseAttribute.offeredFall,
    CourseAttribute.offeredIAP,
    CourseAttribute.offeredSpring,
    CourseAttribute.offeredSummer,
    CourseAttribute.quarterInformation,
    CourseAttribute.instructors,
    CourseAttribute.schedule,
    CourseAttribute.virtualStatus,
    CourseAttribute.URL,
    CourseAttribute.averageRating,
    CourseAttribute.averageInClassHours,
    CourseAttribute.averageOutOfClassHours,
    CourseAttribute.enrollment,
    CourseAttribute.parent,
    CourseAttribute.children
]

CONDENSED_ATTRIBUTES = [
    CourseAttribute.subjectID,
    CourseAttribute.title,
    CourseAttribute.subjectLevel,
    CourseAttribute.totalUnits,
    CourseAttribute.halfClass,
    CourseAttribute.prerequisites,
    CourseAttribute.corequisites,
    CourseAttribute.oldPrerequisites,
    CourseAttribute.oldCorequisites,
    CourseAttribute.eitherPrereqOrCoreq,
    CourseAttribute.oldID,
    CourseAttribute.jointSubjects,
    CourseAttribute.equivalentSubjects,
    CourseAttribute.meetsWithSubjects,
    CourseAttribute.notOfferedYear,
    CourseAttribute.offeredFall,
    CourseAttribute.offeredIAP,
    CourseAttribute.offeredSpring,
    CourseAttribute.offeredSummer,
    CourseAttribute.quarterInformation,
    CourseAttribute.instructors,
    CourseAttribute.virtualStatus,
    CourseAttribute.communicationRequirement,
    CourseAttribute.hassRequirement,
    CourseAttribute.GIR,
    CourseAttribute.averageRating,
    CourseAttribute.averageInClassHours,
    CourseAttribute.averageOutOfClassHours,
    CourseAttribute.enrollment,
    CourseAttribute.parent,
    CourseAttribute.children
]
