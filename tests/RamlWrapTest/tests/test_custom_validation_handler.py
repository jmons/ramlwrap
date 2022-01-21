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

    def test_validation_handler(self):
        """
        Test that given a custom validation handler path, it is called.
        Test that if no handler is given, the default handler is used.
        """

        # Test that the custom method is called and a response is returned.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation_response"
        response = self.client.post("/post-api", data="{}", content_type="application/json")
        self.assertEquals(418, response.status_code)

        # Test that the custom method is called and an exception is raised.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation_exception"
        with self.assertRaises(NotImplementedError):
            response = self.client.post("/api", data="{}", content_type="application/json")

        # Test that the default is called.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = None
        response = self.client.post("/api", data="{}", content_type="application/json")
        self.assertEquals(422, response.status_code)

        delattr(settings, "RAMLWRAP_VALIDATION_ERROR_HANDLER")
        response = self.client.post("/api", data="{}", content_type="application/json")
        self.assertEquals(422, response.status_code)

    def test_validation_handler_with_request_action(self):
        """
        Test that if the handler handles request and action, these are passed through
        """
        endpoint = "/api"

        # Test that the custom method is called and a response is returned.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation_with_request_action"

        response = self.client.post(endpoint, data="{}", content_type="application/json")

        self.assertEquals(200, response.status_code)

        expected_json_body = {
            "path": endpoint,
            "content_type": "application/json"

        }

        self.assertEqual(json.loads(response.content.decode("utf-8")), expected_json_body)
