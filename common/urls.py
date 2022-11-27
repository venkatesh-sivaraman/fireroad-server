from django.urls import re_path

from . import views

from django.views.generic import TemplateView
from django.contrib.auth import logout

urlpatterns = [
    re_path('verify/', views.verify, name='verify'),
    re_path('new_user/', views.new_user, name='new_user'),
    re_path('signup/', views.signup, name='signup'),
    re_path('^login/', views.login_oauth, name='login'),
    re_path('^dev_login/', views.dev_login, name='dev_login'),
    re_path('login_touchstone/', views.login_touchstone, name='login_touchstone'),
    re_path('logout/', logout, {'next_page': 'index'}, name='logout'),
    re_path('set_semester/', views.set_semester, name='set_semester'),
    re_path('prefs/favorites/', views.favorites, name='favorites'),
    re_path('prefs/set_favorites/', views.set_favorites, name='set_favorites'),
    re_path('prefs/progress_overrides/', views.progress_overrides, name='progress_overrides'),
    re_path('prefs/set_progress_overrides/', views.set_progress_overrides, name='set_progress_overrides'),
    re_path('prefs/notes/', views.notes, name='notes'),
    re_path('prefs/set_notes/', views.set_notes, name='set_notes'),
    re_path('prefs/custom_courses/', views.custom_courses, name='custom_courses'),
    re_path('prefs/set_custom_course/', views.set_custom_course, name='set_custom_course'),
    re_path('prefs/remove_custom_course/', views.remove_custom_course, name='remove_custom_course'),
    re_path('decline/', TemplateView.as_view(template_name='common/decline.html'), name='decline'),
    re_path('fetch_token/', views.fetch_token, name='fetch_token'),
    re_path('user_info/', views.user_info, name='user_info'),
    re_path('^disapprove_client/', views.approval_page_failure, name='approval_page_failure'),
    re_path('^approve_client/', views.approval_page_success, name='approval_page_success'),

    # reference
    re_path('reference/$', TemplateView.as_view(template_name='common/docs/overview.html'), name='overview'),
    re_path('reference/auth', TemplateView.as_view(template_name='common/docs/auth.html'), name='auth'),
    re_path('reference/catalog', TemplateView.as_view(template_name='common/docs/catalog.html'), name='catalog'),
    re_path('reference/requirements', TemplateView.as_view(template_name='common/docs/requirements.html'), name='requirements'),
    re_path('reference/sync', TemplateView.as_view(template_name='common/docs/sync.html'), name='sync'),
    re_path('reference/recommender', TemplateView.as_view(template_name='common/docs/recommender.html'), name='recommender'),
    re_path('reference/file_formats', TemplateView.as_view(template_name='common/docs/file_formats.html'), name='file_formats'),

    # index
    re_path(r'^$', TemplateView.as_view(template_name='common/index.html'), name='index'),
]
