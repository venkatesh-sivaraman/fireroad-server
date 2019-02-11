from django.conf.urls import url

from . import views
from . import editor

from django.views.generic import TemplateView

urlpatterns = [
    url(r'^edit/(?P<list_id>.{1,50})', editor.edit, name='edit'),
    url(r'^success/', editor.success, name='submit_success'),
    url(r'^create/', editor.create, name='create'),
    url(r'^preview/', editor.preview, name='preview'),
    url(r'^list_reqs/', views.list_reqs, name='list_reqs'),
    url(r'^get_json/(?P<list_id>.{1,50})/', views.get_json, name='get_json'),
    url(r'^progress/(?P<list_id>.{1,50})/(?P<courses>.*)', views.progress, name='progress'),
    url(r'^$', editor.index, name='requirements_index'),
]
