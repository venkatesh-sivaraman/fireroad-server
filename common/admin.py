"""Registers models for the admin site."""

from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Student)
admin.site.register(RedirectURL)
