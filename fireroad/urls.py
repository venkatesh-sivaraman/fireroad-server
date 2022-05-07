"""fireroad URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic.base import RedirectView
from django.contrib import admin
from common.views import dev_login
from django.conf import settings

# admin.autodiscover()
# admin.site.login = staff_member_required(admin.site.login, login_url=settings.LOGIN_URL)

urlpatterns = [
    url(r'courses/', include('catalog.urls')),
    url(r'courseupdater/', include('courseupdater.urls')),
    url(r'recommend/', include('recommend.urls')),
    url(r'admin/', admin.site.urls),
    url(r'sync/', include('sync.urls')),
    url(r'analytics/', include('analytics.urls')),
    url(r'requirements/', include('requirements.urls')),
    url(r'syllabus/', include('syllabus.urls')),
    url(r'', include('common.urls')),
]

# Redirect to the appropriate login page if one is specified in the settings module
if settings.LOGIN_URL:
    if settings.LOGIN_URL.strip("/") != 'dev_login':
        urlpatterns.insert(0, url(r'^admin/login/$', RedirectView.as_view(url=settings.LOGIN_URL,
                                                                          permanent=True,
                                                                          query_string=True)))
        urlpatterns.insert(0, url(r'^dev_login/$', RedirectView.as_view(url=settings.LOGIN_URL,
                                                                          permanent=True,
                                                                          query_string=True)))
    if settings.LOGIN_URL.strip("/") != 'login':
        urlpatterns.insert(0, url(r'^login/$', RedirectView.as_view(url=settings.LOGIN_URL,
                                                                    permanent=True,
                                                                    query_string=True)))
