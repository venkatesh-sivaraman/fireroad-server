from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'lookup/(?P<subject_id>[A-z0-9.]+)', views.lookup, name='lookup'),
    re_path(r'search/(?P<search_term>[^?]+)', views.search, name='search'),
    re_path(r'dept/(?P<dept>[A-z0-9.]+)', views.department, name='department'),
    re_path(r'all', views.list_all, name='list_all')
]
