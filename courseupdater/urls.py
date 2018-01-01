from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url('check/', views.check, name='check'),
    url('semesters/', views.semesters, name='semesters')
]
