from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^$', views.index, name='index'),
    re_path('check/', views.check, name='check'),
    re_path('semesters/', views.semesters, name='semesters'),

    re_path(r'update_catalog/', views.update_catalog, name='update_catalog'),
    re_path(r'update_progress/', views.update_progress, name='update_progress'),
    re_path(r'reset_update/', views.reset_update, name='reset_update'),

    re_path(r'corrections/delete/(?P<id>\d+)', views.delete_correction, name='delete_catalog_correction'),
    re_path(r'corrections/edit/(?P<id>\d+)', views.edit_correction, name='edit_catalog_correction'),
    re_path(r'corrections/new', views.new_correction, name='new_catalog_correction'),
    re_path(r'corrections/', views.view_corrections, name='catalog_corrections'),

    re_path(r'download_data/', views.download_catalog_data, name='download_data')
]
