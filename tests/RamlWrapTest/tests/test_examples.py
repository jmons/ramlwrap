"""Tests for RamlWrap"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from django.test import TestCase, Client


class ExamplesTestCase(TestCase):
    client = None

    def setUp(self):
        self.client = Client()

    def test_raml_with_multiple_examples__only_one_is_returned(self):
        """Test that a valid get request with no target returns
        the example json.
        """

        expected_data_1 = {"exampleData": "This is the first example response"}
        expected_data_2 = {"exampleData2": "This is a second example"}

        response = self.client.get("/multi-example")
        reply_data = response.content.decode("utf-8")
        actual_response = json.loads(reply_data)

        # Due to the unordered nature of dictionaries in certain Python versions, we are happy if either one of
        # the examples is returned
        self.assertTrue(actual_response == expected_data_1 or actual_response == expected_data_2)
