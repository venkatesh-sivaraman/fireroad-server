from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url('check/', views.check, name='check'),
    url('semesters/', views.semesters, name='semesters'),

    url(r'update_catalog/', views.update_catalog, name='update_catalog'),
    url(r'update_progress/', views.update_progress, name='update_progress'),
    url(r'reset_update/', views.reset_update, name='reset_update'),

    url(r'corrections/delete/(?P<id>\d+)', views.delete_correction, name='delete_catalog_correction'),
    url(r'corrections/edit/(?P<id>\d+)', views.edit_correction, name='edit_catalog_correction'),
    url(r'corrections/new', views.new_correction, name='new_catalog_correction'),
    url(r'corrections/', views.view_corrections, name='catalog_corrections'),
]
