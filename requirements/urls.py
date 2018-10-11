from django.conf.urls import url

from . import views

from django.views.generic import TemplateView

urlpatterns = [
    url(r'^success/', views.success, name='submit_success'),
    url(r'^create/', views.create, name='create'),
    url(r'^get_json/(?P<list_id>.{1,50})', views.get_json, name='get_json'),
    url(r'^edit/(?P<list_id>.{1,50})', views.edit, name='edit'),
    url(r'^$', views.index, name='requirements_index'),
]
