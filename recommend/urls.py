from django.conf.urls import url

from . import views

urlpatterns = [
    url('rate/', views.rate, name='rate'),
    url('get/', views.get, name='get'),
    url('verify/', views.verify, name='verify'),
    url('new_user/', views.new_user, name='new_user'),
]
