from django.conf.urls import url

from . import views
from . import editor

from django.views.generic import TemplateView

urlpatterns = [
    url(r'^edit/(?P<list_id>.{1,50})', editor.edit, name='requirements_edit'),
    url(r'^success/', editor.success, name='submit_success'),
    url(r'^create/', editor.create, name='create'),
    url(r'^preview/', editor.preview, name='preview'),
    url(r'^review/(?P<edit_req>\d+)', editor.review, name='review'),
    url(r'^review/', editor.review_all, name='review_all'),
    url(r'^resolve/(?P<edit_req>\d+)', editor.resolve, name='resolve'),
    url(r'^ignore_edit/(?P<edit_req>\d+)', editor.ignore_edit, name='ignore_edit'),
    url(r'^uncommit/(?P<edit_req>\d+)', editor.uncommit, name='uncommit'),
    url(r'^commit/(?P<edit_req>\d+)', editor.commit, name='commit'),
    url(r'^list_reqs/', views.list_reqs, name='list_reqs'),
    url(r'^get_json/(?P<list_id>.{1,50})/', views.get_json, name='get_json'),
    url(r'^progress/(?P<list_id>.{1,50})/(?P<courses>.+)', views.progress, name='progress'),
    url(r'^progress/(?P<list_id>.{1,50})/', views.road_progress, name='road_progress'),
    url(r'^$', editor.index, name='requirements_index'),
]
