"""URLs for the rating and recommendation system."""

from django.conf.urls import url
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    url('rate/', views.rate, name='rate'),
    url('get/', views.get, name='get')
]
