from django.conf.urls import url

from . import views

from django.views.generic import TemplateView
from django.contrib.auth.views import logout

urlpatterns = [
    url('verify/', views.verify, name='verify'),
    url('new_user/', views.new_user, name='new_user'),
    url('signup/', views.signup, name='signup'),
    url('login/', views.login_oauth, name='login'),
    url('login_touchstone/', views.login_touchstone, name='login_touchstone'),
    url('logout/', logout, {'next_page': 'index'}, name='logout'),
    url('set_semester/', views.set_semester, name='set_semester'),
    url('prefs/favorites/', views.favorites, name='favorites'),
    url('prefs/set_favorites/', views.set_favorites, name='set_favorites'),
    url('prefs/progress_overrides/', views.progress_overrides, name='progress_overrides'),
    url('prefs/set_progress_overrides/', views.set_progress_overrides, name='set_progress_overrides'),
    url('prefs/notes/', views.notes, name='notes'),
    url('prefs/set_notes/', views.set_notes, name='set_notes'),
    url('prefs/custom_courses/', views.custom_courses, name='custom_courses'),
    url('prefs/set_custom_course/', views.set_custom_course, name='set_custom_course'),
    url('prefs/remove_custom_course/', views.remove_custom_course, name='remove_custom_course'),
    url('decline/', TemplateView.as_view(template_name='common/decline.html'), name='decline'),
    url('fetch_token/', views.fetch_token, name='fetch_token'),
    url('user_info/', views.user_info, name='user_info'),

    # reference
    url('reference/$', TemplateView.as_view(template_name='common/docs/overview.html'), name='overview'),
    url('reference/auth', TemplateView.as_view(template_name='common/docs/auth.html'), name='auth'),
    url('reference/catalog', TemplateView.as_view(template_name='common/docs/catalog.html'), name='catalog'),
    url('reference/requirements', TemplateView.as_view(template_name='common/docs/requirements.html'), name='requirements'),
    url('reference/sync', TemplateView.as_view(template_name='common/docs/sync.html'), name='sync'),
    url('reference/recommender', TemplateView.as_view(template_name='common/docs/recommender.html'), name='recommender'),

    # index
    url(r'^$', TemplateView.as_view(template_name='common/index.html'), name='index'),
]
