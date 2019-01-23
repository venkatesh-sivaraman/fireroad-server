from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'lookup/(?P<subject_id>[A-z0-9.]+)', views.lookup, name='lookup'),
    url(r'search/(?P<search_term>[^?]+)', views.search, name='search'),
    url(r'dept/(?P<dept>[A-z0-9.]+)', views.department, name='department'),
    url(r'all', views.list_all, name='list_all')
]
