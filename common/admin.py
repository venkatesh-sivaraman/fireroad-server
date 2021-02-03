from django.contrib import admin

# Register your models here.
from .models import *

# The approved_users field creates some issues when trying to update APIClients,
# so just remove it entirely
class APIClientAdmin(admin.ModelAdmin):
    exclude = ('approved_users',)

admin.site.register(Student)
admin.site.register(RedirectURL)
admin.site.register(APIClient, APIClientAdmin)