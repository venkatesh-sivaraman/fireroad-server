from django.urls import re_path

from . import views
from . import editor

from django.views.generic import TemplateView

urlpatterns = [
    re_path(r'^edit/(?P<list_id>.{1,50})', editor.edit, name='requirements_edit'),
    re_path(r'^success/', editor.success, name='submit_success'),
    re_path(r'^create/', editor.create, name='create'),
    re_path(r'^preview/', editor.preview, name='preview'),
    re_path(r'^review/(?P<edit_req>\d+)', editor.review, name='review'),
    re_path(r'^review/', editor.review_all, name='review_all'),
    re_path(r'^resolve/(?P<edit_req>\d+)', editor.resolve, name='resolve'),
    re_path(r'^ignore_edit/(?P<edit_req>\d+)', editor.ignore_edit, name='ignore_edit'),
    re_path(r'^uncommit/(?P<edit_req>\d+)', editor.uncommit, name='uncommit'),
    re_path(r'^commit/(?P<edit_req>\d+)', editor.commit, name='commit'),
    re_path(r'^list_reqs/', views.list_reqs, name='list_reqs'),
    re_path(r'^get_json/(?P<list_id>.{1,50})/', views.get_json, name='get_json'),
    re_path(r'^progress/(?P<list_id>.{1,50})/(?P<courses>.+)', views.progress, name='progress'),
    re_path(r'^progress/(?P<list_id>.{1,50})/', views.road_progress, name='road_progress'),
    re_path(r'^$', editor.index, name='requirements_index'),
]
