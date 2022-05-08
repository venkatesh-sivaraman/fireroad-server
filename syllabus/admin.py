from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(SyllabusSubmission)
admin.site.register(SyllabusDeployment)
admin.site.register(Syllabus)
