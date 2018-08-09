from django.conf.urls import url

from . import views

urlpatterns = [
    url('upload_road/', views.upload_road, name='upload_road'),
    #url('sync_road/', views.sync_road, name='sync_road'),
    url('roads/', views.roads, name='roads')
]
