"""Tests for RamlWrap"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from ramlwrap import ramlwrap
from ramlwrap.utils.validation import Endpoint
from ramlwrap.utils.raml import raml_url_patterns
from ramlwrap.utils.exceptions import FatalException
from django.conf import settings
from django.test import TestCase, Client
from django.test.client import RequestFactory
from unittest import skip

from jsonschema.exceptions import ValidationError

from ramlwrap.utils.yaml_include_loader import Loader


def _get_parent_class(method):
    """Return the class for the given method."""
    members = inspect.getmembers(method)
    for m in members:
        if m[0] == "__self__":
            return m[1]

def _internal_mockfunc(request, example):
    pass

def _internal_mock_post(request, example):
    """json loads the request and return it."""
    return json.loads(request.validated_data)


class RamlWrapTestCase(TestCase):

    client = None

    def setUp(self):
        self.client = Client()

    def test_pattern_urls_from_raml(self):
        """Test that given a raml file the patterns are generated with the correct urls."""
        funcmap = {}
        patterns = raml_url_patterns("RamlWrapTest/tests/fixtures/raml/test.raml", funcmap)
        expected_urls = [
            "api",
            "api/1",
            "api/1/1.1",
            "api/1/1.1/1.1.1",
            "api/2",
            "api/3"
        ]

        for expected_url in expected_urls:
            found = False
            for pattern in patterns:
                if pattern.regex.match(expected_url):
                    found = True
            if not found:
                self.fail("[%s] entrypoint example did not match expected." % expected_url)

    def test_pattern_entrypoints_from_raml(self):
        """Test that given a raml file the patterns are generated with the correct entry points."""

        funcmap = {}
        patterns = raml_url_patterns("RamlWrapTest/tests/fixtures/raml/test.raml", funcmap)
        expected_methods = {
            "api": {"POST": {"example": '{"data": "foo"}'}},
            "api/1": {"POST": {}},
            "api/1/1.1": {"GET": {}},
            "api/1/1.1/1.1.1": {"GET": {}},
            "api/2": {"GET": {}},
            "api/3": {"GET": {}}
        }

        for pattern in patterns:
            entrypoint = _get_parent_class(pattern.callback)
            pattern_url = pattern.regex.match(entrypoint.url).group(0)
            self.assertEqual(pattern_url, entrypoint.url)
            for method in expected_methods[pattern_url]:
                method_info = expected_methods[pattern_url][method]
                if "example" in method_info:
                    expected_example = method_info["example"]
                    self.assertEqual(expected_example, entrypoint.request_method_mapping[method].example)

    @skip("This test needs fixing.")
    def test_get_api(self):
        """
        Test that the ValidatedGETAPI is validating correctly.
        """
        expected_params = {
            "name": {
                "repeat": None,
                "displayName": "Name",
                "name": None,
                "default": None,
                "pattern": None,
                "enum": None,
                "maximum": None,
                "required": True,
                "minimum": None,
                "minLength": 5,
                "maxLength": None,
                "type": "string",
                "example": "Michelangelo",
                "description": None
            }
        }
        rf = RequestFactory()
        request = rf.get("/turtle/?name=Michelangelo")
        self.assertEqual(_is_valid_query(request.GET, expected_params), True)

        request = rf.get("/turtle/?name=Mike")
        with self.assertRaises(ValidationError):
            _is_valid_query(request.GET, expected_params)

        request = rf.get("/turtle/")
        with self.assertRaises(ValidationError):
            _is_valid_query(request.GET, expected_params)

        expected_params = {
            "name": {
                "repeat": None,
                "displayName": "Name",
                "name": None,
                "default": None,
                "pattern": None,
                "enum": None,
                "maximum": None,
                "required": True,
                "minimum": None,
                "minLength": 5,
                "maxLength": None,
                "type": "string",
                "example": "Michelangelo",
                "description": None
            },
            "type": {
                "repeat": None,
                "displayName": "Quote type",
                "name": None,
                "default": None,
                "pattern": None,
                "enum": None,
                "maximum": None,
                "required": False,
                "minimum": None,
                "minLength": 4,
                "maxLength": None,
                "type": "string",
                "example": "funny",
                "description": None
            }
        }

        request = rf.get("/turtle/quote/?name=Michelangelo")
        self.assertEquals(_is_valid_query(request.GET, expected_params), True)

    def test_raml_schema_validation(self):
        """Test that the validation is applied when present"""

        response = self.client.post("/api", data="{}", content_type="application/json")
        self.assertEquals(422, response.status_code)

    def test_raml_example_returned(self):
        """Test that the example is returned as expected."""
        response = self.client.post("/api", data=json.dumps({"data": "foobar"}), content_type="application/json")

        self.assertEqual(response.status_code, 200)

        expected_data = {"data": "foo"}
        reply_data = response.content.decode("utf-8")
        self.assertEqual(expected_data, json.loads(reply_data))

    def test_empty_post(self):
        """Testing that ramlwrap can handle an empty post request."""

        response = self.client.post("/app2/foo", data=None)
        self.assertEqual(response.status_code, 200)

    def test_validation_handler(self):
        """
        Test that given a custom validation handler path, it is called.
        Test that if no handler is given, the default handler is used.
        """

        # Test that the custom method is called and a response is returned.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation_response"
        response = self.client.post("/app1", data="{}", content_type="application/json")
        self.assertEquals(418, response.status_code)

        # Test that the custom method is called and an exception is raised.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation_exception"
        with self.assertRaises(NotImplementedError):
            response = self.client.post("/app1", data="{}", content_type="application/json")

        # Test that the default is called.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = None
        response = self.client.post("/app1", data="{}", content_type="application/json")
        self.assertEquals(422, response.status_code)

        delattr(settings, "RAMLWRAP_VALIDATION_ERROR_HANDLER")
        response = self.client.post("/app1", data="{}", content_type="application/json")
        self.assertEquals(422, response.status_code)
