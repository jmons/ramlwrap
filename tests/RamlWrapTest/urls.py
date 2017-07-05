"""RamlWrapTest URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin

from ramlwrap import ramlwrap

from webapi.views import login_request, logout_request, protected_view

urlpatterns = [
    url(r'login$',  login_request),
    url(r'logout$',  logout_request),
    
    url(r'^admin/', admin.site.urls),
]

# empty mapping table
function_map = {}

# Load in test raml file
urlpatterns.extend(ramlwrap("RamlWrapTest/tests/fixtures/raml/test1.raml", function_map))


# add in web_api testing functions
function_map_web = {
    "web_app_tests/get": protected_view,
    "web_app_tests/post": protected_view
}

urlpatterns.extend(ramlwrap("webapi/tests/fixtures/test_web_api.raml", function_map_web))

