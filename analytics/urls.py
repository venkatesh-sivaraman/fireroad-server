from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'total_requests/(?P<time_frame>[a-z-]*)', views.total_requests, name="total_requests"),
    url(r'user_agents/(?P<time_frame>[a-z-]*)', views.user_agents, name="user_agents"),
    url(r'logged_in_users/(?P<time_frame>[a-z-]*)', views.logged_in_users, name="logged_in_users"),
    url(r'user_semesters/(?P<time_frame>[a-z-]*)', views.user_semesters, name="user_semesters"),
    url(r'request_paths/(?P<time_frame>[a-z-]*)', views.request_paths, name="request_paths"),
    url(r'^$', views.dashboard, name='analytics_dashboard'),
]
