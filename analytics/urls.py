from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'total_requests/', views.total_requests, name="total_requests"),
    url(r'user_agents/', views.user_agents, name="user_agents"),
    url(r'^$', views.dashboard, name='analytics_dashboard'),
]
