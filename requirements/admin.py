"""Registers models for the admin site."""

from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(RequirementsList)
admin.site.register(EditRequest)
admin.site.register(RequirementsStatement)
admin.site.register(Deployment)
