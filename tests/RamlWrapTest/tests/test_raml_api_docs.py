"""Tests for RamlWrap"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from ramlwrap.views import RamlDoc
from django.test import TestCase, Client


class RamlApiDocsTestCase(TestCase):

    def test_first_endpoint_responses(self):
        """Test that the responses are returned as an array."""
        doc = RamlDoc()
        doc.raml_file = "RamlWrapTest/tests/fixtures/raml/test_multiple_responses.raml"
        context = doc._parse_endpoints(None)

        # Find first endpoint (cannot guarantee order for Python 2.7 tests)
        for endpoint in context["endpoints"]:
            if endpoint.displayName == 'First endpoint':
                first_endpoint_responses = endpoint.methods[0].responses

        self.assertEqual(len(first_endpoint_responses), 4)

        # Python tests before 3.6 cannot guarantee order of responses so search based on code
        for response in first_endpoint_responses:
            if response.status_code == 200:
                self.assertEqual(response.description,
                                 'A nice happy description')
                self.assertEqual(response.content_type, 'application/json')
                self.assertEqual(response.schema, {"schema": "example"})
            elif response.status_code == 204:
                self.assertEqual(response.status_code, 204)
                self.assertEqual(response.description, 'No response body required')
            elif response.status_code == 422:
                self.assertEqual(response.status_code, 422)
                self.assertIsNone(response.description)
                self.assertEqual(len(response.examples), 1)
                self.assertEqual(response.examples[0], {"reason": "invalidManatee"})
            elif response.status_code == 500:
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.description, 'A really unhappy server error.')

    def test_second_endpoint_responses(self):
        """Test that the responses are returned as an array."""
        doc = RamlDoc()
        doc.raml_file = "RamlWrapTest/tests/fixtures/raml/test_multiple_responses.raml"
        context = doc._parse_endpoints(None)

        # Find first endpoint (cannot guarantee order for Python 2.7 tests)
        for endpoint in context["endpoints"]:
            if endpoint.displayName == 'Second endpoint':
                second_endpoint_responses = endpoint.methods[0].responses

        self.assertEqual(len(second_endpoint_responses), 1)
        self.assertEqual(second_endpoint_responses[0].status_code, 204)
        self.assertEqual(second_endpoint_responses[0].description, 'No response body required')

    def test_responses_backward_compatability(self):
        """Test that 200 responses data is stored in legacy fields for first endpoint."""
        doc = RamlDoc()
        doc.raml_file = "RamlWrapTest/tests/fixtures/raml/test_multiple_responses.raml"
        context = doc._parse_endpoints(None)

        # Find first endpoint (cannot guarantee order for Python 2.7 tests)
        for endpoint in context["endpoints"]:
            if endpoint.displayName == 'First endpoint':
                first_endpoint_methods = endpoint.methods[0]

        self.assertEqual(first_endpoint_methods.response_content_type, 'application/json')
        self.assertEqual(first_endpoint_methods.response_description, 'A nice happy description')
        self.assertEqual(first_endpoint_methods.response_example, {"reason": "happyDays"})
        self.assertIsNone(first_endpoint_methods.response_examples)
        self.assertEqual(first_endpoint_methods.response_schema, {"schema": "example"})
