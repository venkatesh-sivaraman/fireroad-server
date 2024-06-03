from django.urls import re_path

from . import views

from django.views.generic import TemplateView

urlpatterns = [
    re_path('rate/', views.rate, name='rate'),
    re_path('get/', views.get, name='get')
]
