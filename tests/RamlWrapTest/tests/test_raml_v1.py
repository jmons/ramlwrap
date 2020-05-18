"""Tests for RamlWrap"""
import inspect
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from ramlwrap.utils.raml import raml_url_patterns
from django.test import TestCase, Client

import django
from distutils.version import StrictVersion


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


class RamlWrapv1TestCase(TestCase):
    client = None

    def setUp(self):
        self.client = Client()

    def test_raml_with_multiple_examples__only_one_is_returned(self):
        """Test that a valid get request with no target returns
        the example json.
        """

        expected_data_1 = {"exampleData": "This is the first example response"}
        expected_data_2 = {"exampleData2": "This is a second example"}

        response = self.client.get("/ramlv1-api/multi-example")
        reply_data = response.content.decode("utf-8")
        actual_response = json.loads(reply_data)

        # Due to the unordered nature of dictionaries in certain Python versions, we are happy if either one of
        # the examples is returned
        self.assertTrue(actual_response == expected_data_1 or actual_response == expected_data_2)

