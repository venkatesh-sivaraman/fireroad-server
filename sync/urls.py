from django.urls import re_path

from . import views

urlpatterns = [
    re_path('sync_road/', views.sync_road, name='sync_road'),
    re_path('delete_road/', views.delete_road, name='delete_road'),
    re_path('roads/', views.roads, name='roads'),
    re_path('sync_schedule/', views.sync_schedule, name='sync_schedule'),
    re_path('delete_schedule/', views.delete_schedule, name='delete_schedule'),
    re_path('schedules/', views.schedules, name='schedules')
]
