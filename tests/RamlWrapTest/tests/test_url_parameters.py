"""Tests for ramlwrap validation."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from django.test import TestCase, Client

from jsonschema.exceptions import ValidationError


class UrlParameterTestCase(TestCase):
    """TestCase for ramlwrap URL parameters"""

    client = None

    def setUp(self):
        self.client = Client()

    def test_get_with_valid_params(self):
        """
        Test that a get api with valid query params doesn't raise
        an exception.
        """

        response = self.client.get("/api/3", {"param2": "test5", "param3": 2})
        self.assertEquals(200, response.status_code)

    def test_get_with_invalid_params(self):
        """
        Test that a get api with invalid query params raises
        a ValidationError.
        """

        invalid_params = [
            # param2 must be minLength 5.
            {"param2": "test", "param3": 2},
            # param3 must be a number.
            {"param1": "1", "param2": "12345", "param3": "2sadasd"},
            # param2 must be maxLength 10.
            {"param1": "1", "param2": "12345678910", "param3": "2"},
            # param2 is required.
            {"param1": 1, "param3": 2}
        ]

        for params in invalid_params:
            with self.assertRaises(ValidationError):
                self.client.get("/api/3", params)

    def test_post_with_valid_params(self):
        """Test that a post api with valid query params doesn't raise
        an exception.
        """

        self.client.post("/api/3?param2=one2345&param3=2")

    def test_post_with_invalid_params(self):
        """Test that a post api with invalid query params raises
        a ValidationError.
        """
        invalid_params = [
            # param2 must be minLength 5.
            "param2=test&param3=2",
            # param3 must be a number.
            "param1=1&param2=12345&param3=2sadasd",
            # param2 must be maxLength 10.
            "param1=1&param2=12345678910&param3=2",
            # param2 is required.
            "param1=1&param3=2"
        ]

        for params in invalid_params:
            with self.assertRaises(ValidationError):
                self.client.get("/api/3?%s" % params)
