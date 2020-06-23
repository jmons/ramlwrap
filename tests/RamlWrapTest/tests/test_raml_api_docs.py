"""Tests for RamlWrap"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from ramlwrap.views import RamlDoc
from django.test import TestCase, Client


class RamlApiDocsTestCase(TestCase):

    def test_responses(self):
        """Test that the responses are returned as an array."""
        doc = RamlDoc()
        doc.raml_file = "RamlWrapTest/tests/fixtures/raml/test_multiple_responses.raml"
        context = doc._parse_endpoints(None)

        self.assertEqual(len(context["endpoints"][0].methods[0].responses), 4)

        # Python tests before 3.6 cannot guarantee order of responses so search based on code
        for response in context["endpoints"][0].methods[0].responses:
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

    def test_responses_backward_compatability(self):
        """Test that 200 responses data is stored in legacy fields."""
        doc = RamlDoc()
        doc.raml_file = "RamlWrapTest/tests/fixtures/raml/test_multiple_responses.raml"
        context = doc._parse_endpoints(None)

        self.assertEqual(context["endpoints"][0].methods[0].response_content_type, 'application/json')
        self.assertEqual(context["endpoints"][0].methods[0].response_description, 'A nice happy description')
        self.assertEqual(context["endpoints"][0].methods[0].response_example, {"reason": "happyDays"})
        self.assertIsNone(context["endpoints"][0].methods[0].response_examples)
        self.assertEqual(context["endpoints"][0].methods[0].response_schema, {"schema": "example"})
