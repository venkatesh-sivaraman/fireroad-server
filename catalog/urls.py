from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'course/(?P<subject_id>[A-z0-9.]+)', views.lookup, name='lookup'),
    url(r'dept/(?P<dept>[A-z0-9.]+)', views.department, name='department'),
    url(r'all', views.list_all, name='list_all')
]
