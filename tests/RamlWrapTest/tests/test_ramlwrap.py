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

    def test_file_formats(self):
        """Test that if the file extension isn't raml then an exception is raised."""
        error_message = "The file: 'RamlWrapTest/tests/fixtures/raml/test.txt' does not have a .raml extension!"
        with self.assertRaisesMessage(FatalException, error_message):
            ramlwrap("RamlWrapTest/tests/fixtures/raml/test.txt", {})

    def test_error_parsing_file(self):
        """If the a subcomponent of a file doesn't exist it should error."""
        error_message = "An error occurred reading 'RamlWrapTest/tests/fixtures/raml/test_missing_attribute.raml': 'str' object has no attribute 'get'"
        #with self.assertRaisesMessage(FatalException, error_message):
        with self.assertRaises(Exception):
            ramlwrap("RamlWrapTest/tests/fixtures/raml/test_missing_attribute.raml", {})

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
            "api/3",
            "api/4"
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
            "api": {"POST": {"example": {"data": "value"}}},
            "api/1": {"POST": {}},
            "api/1/1.1": {"GET": {}},
            "api/1/1.1/1.1.1": {"GET": {}},
            "api/2": {"GET": {}},
            "api/3": {"GET": {}},
            "api/4": {"POST": {}}
        }

        for pattern in patterns:
            entrypoint = _get_parent_class(pattern.callback)
            pattern_url = pattern.regex.match(entrypoint.url).group(0)
            self.assertEqual(pattern_url, entrypoint.url)
            for method in expected_methods[pattern_url]:
                method_info = expected_methods[pattern_url][method]
                if "example" in method_info:
                    expected_example = method_info["example"]
                    
                    self.assertDictEqual(expected_example, entrypoint.request_method_mapping[method].example)

    def test_raml_post_example_returned(self):
        """Test that the example is returned as expected."""
        response = self.client.post("/api", data=json.dumps({"data": "foobar"}), content_type="application/json")

        self.assertEqual(response.status_code, 200)

        expected_data = {"data": "value"}
        reply_data = response.content.decode("utf-8")

        self.assertEqual("application/json", response["Content-Type"]) # note Capitlaisation difference as a header        
        self.assertDictEqual(expected_data, json.loads(reply_data))

        #self.assertEqual(expected_data, json.loads(reply_data))

    def test_raml_get_example_returned(self):
        """Test that a valid get request with no target returns
        the example json.
        """

        expected_data = {"exampleData": "You just made a get!"}
        response = self.client.get("/api/3?param2=sixsix")

        reply_data = response.content.decode("utf-8")
        
        #self.assertEqual(expected_data, json.loads(reply_data))
        self.assertEqual("application/json", response["Content-Type"]) # note Capitlaisation difference as a header
        self.assertDictEqual(expected_data, json.loads(reply_data))

    def test_empty_post(self):
        """Testing that ramlwrap can handle an empty post request."""

        response = self.client.post("/api/4", data=None)
        self.assertEqual(response.status_code, 200)
