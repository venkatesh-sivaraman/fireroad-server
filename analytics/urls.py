from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'total_requests/(?P<time_frame>[a-z-]*)', views.total_requests, name="total_requests"),
    re_path(r'user_agents/(?P<time_frame>[a-z-]*)', views.user_agents, name="user_agents"),
    re_path(r'logged_in_users/(?P<time_frame>[a-z-]*)', views.logged_in_users, name="logged_in_users"),
    re_path(r'user_semesters/(?P<time_frame>[a-z-]*)', views.user_semesters, name="user_semesters"),
    re_path(r'request_paths/(?P<time_frame>[a-z-]*)', views.request_paths, name="request_paths"),
    re_path(r'active_documents/(?P<time_frame>[a-z-]*)', views.active_documents, name="active_documents"),
    re_path(r'^$', views.dashboard, name='analytics_dashboard'),
]
