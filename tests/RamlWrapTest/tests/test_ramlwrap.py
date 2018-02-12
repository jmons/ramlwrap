"""Tests for RamlWrap"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from ramlwrap import ramlwrap
from ramlwrap.utils.raml import raml_url_patterns
from ramlwrap.utils.exceptions import FatalException
from django.test import TestCase, Client


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

    # FIXME new parser loads the empty file without erroring
    #def test_error_parsing_file(self):
    #     """If the a subcomponent of a file doesn't exist it should error."""
           #Adding skip - this test (or the test file) is bad at the time of writing:
    #    error_message = "An error occurred reading 'RamlWrapTest/tests/fixtures/raml/test_missing_attribute.raml': 'str' object has no attribute 'get'"
    #    #with self.assertRaisesMessage(FatalException, error_message):
    #    with self.assertRaises(Exception):
    #        ramlwrap("RamlWrapTest/tests/fixtures/raml/test_missing_attribute.raml", {})

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

        self.assertEqual("application/json", response["Content-Type"])  # note Capitalisation difference as a header
        self.assertDictEqual(expected_data, json.loads(reply_data))

        self.assertEqual(expected_data, json.loads(reply_data))

    def test_raml_get_example_returned(self):
        """Test that a valid get request with no target returns
        the example json.
        """

        expected_data = {"exampleData": "You just made a get!"}
        response = self.client.get("/api/3?param2=sixsix")

        reply_data = response.content.decode("utf-8")
        
        self.assertEqual(expected_data, json.loads(reply_data))
        self.assertEqual("application/json", response["Content-Type"])  # note Capitalisation difference as a header
        self.assertDictEqual(expected_data, json.loads(reply_data))

    def test_empty_post(self):
        """Testing that ramlwrap can handle an empty post request."""

        response = self.client.post("/api/4", data=None)
        self.assertEqual(response.status_code, 200)

    def test_raml_dynamic_urls(self):
        """
        Testing dynamic get and post urls,
        that given a raml file the patterns are generated with the correct entry points.
        """

        funcmap = {}
        patterns = raml_url_patterns("RamlWrapTest/tests/fixtures/raml/test_dynamic.raml", funcmap)

        expected_methods = {
            "dynamicapi/{dynamic_id}": {"GET": {"example": {"exampleData": "You just made a dynamic get request!"}}},
            "dynamicapi/{dynamic_id}/api": {
                "GET": {"example": {"exampleData": "You just made another dynamic get request!"}}},
            "dynamicapi/{dynamic_id}/api": {
                "POST": {"example": {"exampleData": "You just made a dynamic post request!"}}},
            "dynamicapi/{dynamic_id}/api2":  {
                "POST": {"example": {"exampleData": "You just made another dynamic post request!"}}},
            "dynamicapi/{dynamic_id}/{dynamic_id_2}": {
                "GET": {"example": {"exampleData": "You just made a dynamic get request with 2 dynamic values!"}}},
            "dynamicapi/{dynamic_id}/{dynamic_id_2}/api3": {
                "GET": {"example": {"exampleData": "You just made another dynamic get request with 2 dynamic values!"}}},
            "dynamicapi/{dynamic_id}/{dynamic_id_2}/api4": {
                "POST": {"example": {"exampleData": "You just made another dynamic post request with 2 dynamic values!"}}},
            "notdynamic": {"GET": {"example": {"exampleData": "regular get request"}}}
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

    def test_dynamic_get_urls(self):
        """
        Test to check that the dynamic value in the url is being passed into the function correctly with GET request
         And that the regex on that value is being applied
         regex = Letters only (?P<dynamic_id>[a-zA-Z]+)
        """

        data = [
            {
                "dynamicValue": "aBc",
                "responseData": b'{"dynamicValue": "aBc"}',
                "status": 200
            },
            {
                "dynamicValue": "123",
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/123 was not found on this server.</p>',
                "status": 404
            },
            {
                "dynamicValue": "A1b2C",
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/A1b2C was not found on this server.</p>',
                "status": 404
            },
            {
                "dynamicValue": "!",
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/! was not found on this server.</p>',
                "status": 404
            }
        ]

        for value in data:
            response = self.client.get("/dynamicapi/{}".format(value["dynamicValue"]))
            self.assertEquals(response.status_code, value["status"])
            self.assertEquals(response.content, value["responseData"])

    def test_multiple_dynamic_value_get_urls_return_example_returned(self):
        """
        Test to ensure that urls with multiple dynamic values are parsed correctly,
        and that example data is returned as expected
        """
        response = self.client.get("/dynamicapi/mysteryvalue/123")

        self.assertEqual(response.status_code, 200)

        expected_data = {"exampleData": "You just made a dynamic get request with 2 dynamic values!"}
        reply_data = response.content.decode("utf-8")

        self.assertEqual("application/json", response["Content-Type"])  # note Capitalisation difference as a header
        self.assertDictEqual(expected_data, json.loads(reply_data))

        self.assertEqual(expected_data, json.loads(reply_data))

    def test_multiple_dynamic_value_get_urls(self):
        """
        Test to check both dynamic values in the url are being passed into the function correctly with GET request
         And that the regex on the value is being applied
         dynamic_id regex = Letters only (?P<dynamic_id>[a-zA-Z]+)
         dynamic_id_2 regex = Nums only (?P<dynamic_id_2>[0-9]+)
        """

        # Test a success response
        response = self.client.get("/dynamicapi/aBc/123/api3")
        self.assertEquals(response.status_code, 200)
        self.assertEquals({"dynamicValueOne": "aBc", "dynamicValueTwo": "123"}, json.loads(response.content.decode('utf')))

        # Test responses to urls where dynamic value doesn't match the regex
        data = [
            {
                "dynamicId1": "aBc",
                "dynamicId2": "aBc",  # Should be nums only
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/aBc/aBc/api3 was not found on this server.</p>'
            },
            {
                "dynamicId1": 111,  # Should be letters only
                "dynamicId2": 111,
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/111/111/api3 was not found on this server.</p>'
            },
            {
                "dynamicId1": 111,  # Should be letters only
                "dynamicId2": "aBc",  # Should be nums only
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/111/aBc/api3 was not found on this server.</p>'
            },
            {
                "dynamicId1": "!",  # Should be letters only
                "dynamicId2": 111,
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/!/111/api3 was not found on this server.</p>',
                "status": 404
            },
            {
                "dynamicId1": "aBc",
                "dynamicId2": "!",  # Should be nums only
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/aBc/!/api3 was not found on this server.</p>',
                "status": 404
            },
        ]

        for value in data:
            response = self.client.get("/dynamicapi/{}/{}/api3".format(value["dynamicId1"], value["dynamicId2"]))
            self.assertEquals(response.status_code, 404)
            self.assertEquals(value["responseData"], response.content)

    def test_multiple_dynamic_value_post_urls(self):
        """
        Test to check both dynamic values in the url are being passed into the function correctly with POST request
         And that the regex on the value is being applied
         dynamic_id regex = Letters only (?P<dynamic_id>[a-zA-Z]+)
         dynamic_id_2 regex = Nums only (?P<dynamic_id_2>[0-9]+)
        """

        # Test a success response
        response = self.client.post("/dynamicapi/hello/1111/api4", json.dumps({"data": "value"}), content_type="application/json")
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.status_code, 200)
        self.assertEquals({"dynamicValueOne": "hello", "dynamicValueTwo": "1111"}, json.loads(response.content.decode('utf')))

    def test_dynamic_post_urls(self):
        """
        Test to check that the dynamic value in the url is being passed into the function correctly with POST request
         And that the regex on that value is being applied
         regex = Letters only (?P<dynamic_id>[a-zA-Z]+)
        """

        data = [
            {
                "dynamicValue": "aBc",
                "responseData": b'{"dynamicValue": "aBc"}',
                "status": 200
            },
            {
                "dynamicValue": "123",
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/123/api was not found on this server.</p>',
                "status": 404
            },
            {
                "dynamicValue": "A1b2C",
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/A1b2C/api was not found on this server.</p>',
                "status": 404
            },
            {
                "dynamicValue": "!",
                "responseData": b'<h1>Not Found</h1><p>The requested URL /dynamicapi/!/api was not found on this server.</p>',
                "status": 404
            }
        ]

        for value in data:
            response = self.client.post("/dynamicapi/{}/api".format(value["dynamicValue"]),
                                        json.dumps({"data": "value"}), content_type="application/json")
            self.assertEquals(response.status_code, value["status"])
            self.assertEquals(response.content, value["responseData"])

    def test_dynamic_raml_post_example_returned(self):
        """
        Test that the example is returned as expected from dynamic url if it is not linked to a function in func map
        (reqex must still exist!)
        """

        response = self.client.post("/dynamicapi/mysteryvalue/api2", data=json.dumps({"data": "foobar"}), content_type="application/json")

        self.assertEqual(response.status_code, 200)

        expected_data = {"exampleData": "You just made another dynamic post request!"}
        reply_data = response.content.decode("utf-8")

        self.assertEqual("application/json", response["Content-Type"])  # note Capitalisation difference as a header
        self.assertDictEqual(expected_data, json.loads(reply_data))

        self.assertEqual(expected_data, json.loads(reply_data))

    def test_non_dynamic_urls(self):
        """
        Test correct function is called with non dynamic urls
         when there is no regex in the url func map
        """

        response = self.client.get("/notdynamic")
        self.assertEquals(response.status_code, 200)
        self.assertEquals(json.loads(response.content.decode('utf-8')), {"message": "woohoo"})