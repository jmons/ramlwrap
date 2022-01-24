"""Tests for RamlWrap"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ramlwrap.views import RamlDoc
from django.test import TestCase, Client
from unittest import skip


@skip("Moving to open api")
class RamlApiDocsTestCase():

    def setUp(self):
        doc = RamlDoc()
        doc.raml_file = "RamlWrapTest/tests/fixtures/raml/test_multiple_responses.raml"
        self.context = doc._parse_endpoints(None)

    def test_first_endpoint_responses(self):
        """Test that the responses are returned as an array."""
        # Find first endpoint (cannot guarantee order for Python 2.7 tests)
        first_endpoint_responses = None
        for endpoint in self.context["endpoints"]:
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
                self.assertEqual(response.examples[0].body, {"reason": "invalidManatee"})
            elif response.status_code == 500:
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.description, 'A really unhappy server error.')

    def test_second_endpoint_responses(self):
        """Test that the responses are returned as an array."""
        # Find first endpoint (cannot guarantee order for Python 2.7 tests)
        second_endpoint_responses = None
        for endpoint in self.context["endpoints"]:
            if endpoint.displayName == 'Second endpoint':
                second_endpoint_responses = endpoint.methods[0].responses

        self.assertEqual(len(second_endpoint_responses), 1)
        self.assertEqual(second_endpoint_responses[0].status_code, 204)
        self.assertEqual(second_endpoint_responses[0].description, 'No response body required')

    def test_responses_backward_compatability(self):
        """Test that 200 responses data is stored in legacy fields for first endpoint."""
        # Find first endpoint (cannot guarantee order for Python 2.7 tests)
        first_endpoint_methods = None
        for endpoint in self.context["endpoints"]:
            if endpoint.displayName == 'First endpoint':
                first_endpoint_methods = endpoint.methods[0]

        self.assertEqual(first_endpoint_methods.response_content_type, 'application/json')
        self.assertEqual(first_endpoint_methods.response_description, 'A nice happy description')
        self.assertEqual(first_endpoint_methods.response_example, {"reason": "happyDays"})
        self.assertIsNone(first_endpoint_methods.response_examples)
        self.assertEqual(first_endpoint_methods.response_schema, {"schema": "example"})


class RamlApiDocsExamplesTestCase(TestCase):

    def setUp(self):
        doc = RamlDoc()
        doc.raml_file = "RamlWrapTest/tests/fixtures/raml/test_multiple_examples.raml"
        self.context = doc._parse_endpoints(None)

    def test_multiple_response_examples(self):
        """Test that the responses are returned as an array."""
        # Find first endpoint examples (cannot guarantee order for Python 2.7 tests)
        first_endpoint_examples = None
        for endpoint in self.context["endpoints"]:
            if endpoint.displayName == 'First endpoint':
                first_endpoint_examples = endpoint.methods[0].responses[0].examples

        self.assertEqual(len(first_endpoint_examples), 2)
        for example in first_endpoint_examples:
            if example.title == 'First Example':
                self.assertEqual(example.body, {"description": "This is the first example"})
            elif example.title == 'Second Example':
                self.assertEqual(example.body, {"description": "This is the second example"})
            else:
                raise ValueError('Invalid title found ' + example.title)

    def test_single_response_examples(self):
        """Test that the responses are returned as an array."""
        # Find first endpoint examples (cannot guarantee order for Python 2.7 tests)
        second_endpoint_examples = None
        for endpoint in self.context["endpoints"]:
            if endpoint.displayName == 'Second endpoint':
                second_endpoint_examples = endpoint.methods[0].responses[0].examples

        self.assertEqual(len(second_endpoint_examples), 1)
        self.assertIsNone(second_endpoint_examples[0].title)
        self.assertEqual(second_endpoint_examples[0].body, {"description": "This is the third example"})

    def test_multiple_request_examples(self):
        """Test that the responses are returned as an array."""
        # Find first endpoint request examples (cannot guarantee order for Python 2.7 tests)
        first_endpoint_request_examples = None
        for endpoint in self.context["endpoints"]:
            if endpoint.displayName == 'First endpoint':
                first_endpoint_request_examples = endpoint.methods[0].examples

        self.assertEqual(len(first_endpoint_request_examples), 2)
        for example in first_endpoint_request_examples:
            if example.title == 'First Request Example':
                self.assertEqual(example.body, {"description": "This is the first request example"})
            elif example.title == 'Second Request Example':
                self.assertEqual(example.body, {"description": "This is the second request example"})
            else:
                raise ValueError('Invalid title found ' + example.title)

    def test_single_request_example(self):
        """Test that the responses are returned as an array."""
        # Find second endpoint request examples (cannot guarantee order for Python 2.7 tests)
        second_endpoint_request_examples = None
        for endpoint in self.context["endpoints"]:
            if endpoint.displayName == 'Second endpoint':
                second_endpoint_request_examples = endpoint.methods[0].examples

        self.assertEqual(len(second_endpoint_request_examples), 1)
        self.assertIsNone(second_endpoint_request_examples[0].title)
        self.assertEqual(second_endpoint_request_examples[0].body, {"description": "This is the third request example"})

    def test_multiple_request_examples_backward_compatability(self):
        """Test that request_examples is set correctly"""
        # Find first endpoint request examples (cannot guarantee order for Python 2.7 tests)
        first_endpoint_method = None
        for endpoint in self.context["endpoints"]:
            if endpoint.displayName == 'First endpoint':
                first_endpoint_method = endpoint.methods[0]

        expected_examples = {
            'First Request Example': {"description": "This is the first request example"},
            'Second Request Example': {"description": "This is the second request example"}
        }

        self.assertEqual(first_endpoint_method.request_examples, expected_examples)

    def test_single_request_example_backward_compatability(self):
        """Test that request_example is set correctly"""
        # Find second endpoint request method (cannot guarantee order for Python 2.7 tests)
        second_endpoint_method = None
        for endpoint in self.context["endpoints"]:
            if endpoint.displayName == 'Second endpoint':
                second_endpoint_method = endpoint.methods[0]

        self.assertEqual(second_endpoint_method.request_example, {"description": "This is the third request example"})
