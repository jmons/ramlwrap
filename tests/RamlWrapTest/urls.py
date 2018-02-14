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
from RamlWrapTest.apis.test_apis import dynamic_api_one, dynamic_api_two, regular_api

urlpatterns = [
    url(r'^admin/', admin.site.urls),
]

function_map = {
    # Dynamic urls linked to functions with regex for their dynamic values
    'dynamicapi/{dynamic_id}': {'function': dynamic_api_one, 'regex': {'dynamic_id': '(?P<dynamic_id>[a-zA-Z]+)'}},
    'dynamicapi/{dynamic_id}/api': {'function': dynamic_api_one, 'regex': {'dynamic_id': '(?P<dynamic_id>[a-zA-Z]+)'}},
    'dynamicapi/{dynamic_id}/{dynamic_id_2}/api3': {'function': dynamic_api_two, 'regex': {'dynamic_id': '(?P<dynamic_id>[a-zA-Z]+)', 'dynamic_id_2': '(?P<dynamic_id_2>[0-9]+)'}},
    'dynamicapi/{dynamic_id}/{dynamic_id_2}/api4': {'function': dynamic_api_two, 'regex': {'dynamic_id': '(?P<dynamic_id>[a-zA-Z]+)', 'dynamic_id_2': '(?P<dynamic_id_2>[0-9]+)'}},

    # urls not linked to a function, but it must still have linked regex in order for example data to be returned
    'dynamicapi/{dynamic_id}/api2': {'regex': {'dynamic_id': '(?P<dynamic_id>[a-zA-Z]+)'}},
    'dynamicapi/{dynamic_id}/{dynamic_id_2}': {'regex': {'dynamic_id': '(?P<dynamic_id>[a-zA-Z]+)', 'dynamic_id_2': '(?P<dynamic_id_2>[0-9]+)'}},


    'notdynamic': {'function': regular_api}
}

# Load in test raml file
urlpatterns.extend(ramlwrap("RamlWrapTest/tests/fixtures/raml/test.raml", function_map))
urlpatterns.extend(ramlwrap("RamlWrapTest/tests/fixtures/raml/test_dynamic.raml", function_map))
