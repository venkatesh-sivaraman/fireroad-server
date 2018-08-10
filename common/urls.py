from django.conf.urls import url

from . import views

from django.views.generic import TemplateView

urlpatterns = [
    url('verify/', views.verify, name='verify'),
    url('new_user/', views.new_user, name='new_user'),
    url('signup/', views.signup, name='signup'),
    url('login/', views.login_oauth, name='login'),
    url('set_semester/', views.set_semester, name='set_semester'),
    url('decline/', TemplateView.as_view(template_name='common/decline.html'), name='decline'),
]
