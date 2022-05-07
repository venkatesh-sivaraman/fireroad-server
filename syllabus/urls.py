from django.conf.urls import url

from . import views

from django.views.generic import TemplateView

urlpatterns = [
    url(r'^$', views.index, name='syllabus_index'),
    url(r'^success/', views.success, name='syllabus_success'),
    url(r'^viewer/', views.viewer, name='syllabus_viewer'),
    url(r'^create/', views.create, name='syllabus_create'),
    url(r'^review/(?P<syllabus_sub>\d+)', views.review, name='syllabus_review'),
    url(r'^review/', views.review_all, name='syllabus_review_all'),
    url(r'^resolve/(?P<syllabus_sub>\d+)', views.resolve, name='syllabus_resolve'),
    url(r'^uncommit/(?P<syllabus_sub>\d+)', views.uncommit, name='syllabus_uncommit'),
    url(r'^commit/(?P<syllabus_sub>\d+)', views.commit, name='syllabus_commit'),
]
