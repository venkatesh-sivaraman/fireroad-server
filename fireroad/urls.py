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
from django.urls import include, re_path
from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic.base import RedirectView
from django.contrib import admin
from common.views import dev_login
from django.conf import settings

# admin.autodiscover()
# admin.site.login = staff_member_required(admin.site.login, login_url=settings.LOGIN_URL)

urlpatterns = [
    re_path(r'courses/', include('catalog.urls')),
    re_path(r'courseupdater/', include('courseupdater.urls')),
    re_path(r'recommend/', include('recommend.urls')),
    re_path(r'admin/', admin.site.urls),
    re_path(r'sync/', include('sync.urls')),
    re_path(r'analytics/', include('analytics.urls')),
    re_path(r'requirements/', include('requirements.urls')),
    re_path(r'', include('common.urls')),
]

# Redirect to the appropriate login page if one is specified in the settings module
if settings.LOGIN_URL:
    if settings.LOGIN_URL.strip("/") != 'dev_login':
        urlpatterns.insert(0, re_path(r'^admin/login/$', RedirectView.as_view(url=settings.LOGIN_URL,
                                                                          permanent=True,
                                                                          query_string=True)))
        urlpatterns.insert(0, re_path(r'^dev_login/$', RedirectView.as_view(url=settings.LOGIN_URL,
                                                                          permanent=True,
                                                                          query_string=True)))
    if settings.LOGIN_URL.strip("/") != 'login':
        urlpatterns.insert(0, re_path(r'^login/$', RedirectView.as_view(url=settings.LOGIN_URL,
                                                                    permanent=True,
                                                                    query_string=True)))


