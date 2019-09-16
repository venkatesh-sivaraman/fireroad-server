"""Registers models for the admin site."""

from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(CatalogUpdate)
admin.site.register(CatalogCorrection)
