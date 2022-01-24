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

        response = self.client.get("/api-with-query-params", {"param2": "test5", "param3": 2})
        self.assertEquals(200, response.status_code)

    def test_get_where_string_param_too_short__raises_validation_error(self):
        # param2 must be minLength 5.
        invalid_params = {"param2": "test", "param3": 2}
        with self.assertRaises(ValidationError):
            self.client.get("/api-with-query-params", invalid_params)

    def test_get_where_string_param_too_long__raises_validation_error(self):
        # param2 must be maxLength 10.
        invalid_params = {"param1": "1", "param2": "12345678910", "param3": "2"}
        with self.assertRaises(ValidationError):
            self.client.get("/api-with-query-params", invalid_params)

    def test_get_where_string_param_should_be_integer__raises_validation_error(self):
        # param3 must be a number.
        invalid_params = {"param1": "1", "param2": "12345", "param3": "2sadasd"}
        with self.assertRaises(ValidationError):
            self.client.get("/api-with-query-params", invalid_params)

    def test_get_where_missing_required_param__raises_validation_error(self):
        # param2 is required.
        invalid_params = {"param1": 1, "param3": 2}
        with self.assertRaises(ValidationError):
            self.client.get("/api-with-query-params", invalid_params)

    def test_post_with_valid_params(self):
        """Test that a post api with valid query params doesn't raise
        an exception.
        """
        self.client.post("/api-with-query-params?param2=one2345&param3=2")

    def test_post_where_string_param_too_short__raises_validation_error(self):
        # param2 must be minLength 5.
        invalid_params = {"param2": "test", "param3": 2}
        with self.assertRaises(ValidationError):
            self.client.post("/api-with-query-params", invalid_params)

    def test_post_where_string_param_too_long__raises_validation_error(self):
        # param2 must be maxLength 10.
        invalid_params = {"param1": "1", "param2": "12345678910", "param3": "2"}
        with self.assertRaises(ValidationError):
            self.client.post("/api-with-query-params", invalid_params)

    def test_post_where_string_param_should_be_integer__raises_validation_error(self):
        # param3 must be a number.
        invalid_params = {"param1": "1", "param2": "12345", "param3": "2sadasd"}
        with self.assertRaises(ValidationError):
            self.client.post("/api-with-query-params", invalid_params)

    def test_post_where_missing_required_param__raises_validation_error(self):
        # param2 is required.
        invalid_params = {"param1": 1, "param3": 2}
        with self.assertRaises(ValidationError):
            self.client.post("/api-with-query-params", invalid_params)
