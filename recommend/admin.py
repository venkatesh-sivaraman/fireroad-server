from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(Rating)
admin.site.register(Recommendation)
admin.site.register(Road)
admin.site.register(Student)
