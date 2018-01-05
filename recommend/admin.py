from django.contrib import admin

# Register your models here.
from .models import Rating, Recommendation

admin.site.register(Rating)
admin.site.register(Recommendation)
