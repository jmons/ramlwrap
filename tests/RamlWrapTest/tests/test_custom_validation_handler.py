"""Tests for ramlwrap validation."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from django.conf import settings
from django.test import TestCase, Client


class ContentTypeTestCase(TestCase):
    """TestCase for ramlwrap content type"""

    client = None

    def setUp(self):
        self.client = Client()
        self.invalid_data = { "description": "This JSON does not match the schema" }

    def test_validation_handler_called_if_schema_mismatch(self):
        # Test that the custom method is called and a response is returned.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation__http_418_response"
        response = self.client.post("/post-api-yaml-schema", data=json.dumps(self.invalid_data), content_type="application/json")
        self.assertEquals(418, response.status_code)

    def test_validation_handler_called__raises_exception(self):
        # Test that the custom method is called and an exception is raised.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation__raises_exception"
        with self.assertRaises(NotImplementedError):
            self.client.post("/post-api-yaml-schema", data=self.invalid_data, content_type="application/json")

    def test_default_validation_handler_called_if_custom_not_defined(self):
        # Test that the default is called.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = None
        response = self.client.post("/post-api-yaml-schema", data=self.invalid_data, content_type="application/json")
        self.assertEquals(422, response.status_code)

    def test_default_validation_handler_called_if_custom_not_defined(self):
        delattr(settings, "RAMLWRAP_VALIDATION_ERROR_HANDLER")
        response = self.client.post("/post-api-yaml-schema", data=self.invalid_data, content_type="application/json")
        self.assertEquals(422, response.status_code)

    def test_validation_handler_with_request_action(self):
        """
        Test that if the handler handles request and action, these are passed through
        """
        endpoint = "/post-api-yaml-schema"

        # Test that the custom method is called and a response is returned.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation_with_request_action"

        response = self.client.post(endpoint, data=self.invalid_data, content_type="application/json")

        self.assertEquals(200, response.status_code)

        expected_json_body = {
            "path": endpoint,
            "content_type": "application/json"

        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected_json_body)
