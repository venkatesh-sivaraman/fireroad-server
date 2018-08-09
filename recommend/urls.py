from django.conf.urls import url

from . import views

from django.views.generic import TemplateView

urlpatterns = [
    url('rate/', views.rate, name='rate'),
    url('get/', views.get, name='get')
]
