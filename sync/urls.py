from django.conf.urls import url

from . import views

urlpatterns = [
    url('sync_road/', views.sync_road, name='sync_road'),
    url('delete_road/', views.delete_road, name='delete_road'),
    url('roads/', views.roads, name='roads'),
    url('sync_schedule/', views.sync_schedule, name='sync_schedule'),
    url('delete_schedule/', views.delete_schedule, name='delete_schedule'),
    url('schedules/', views.schedules, name='schedules')
]
