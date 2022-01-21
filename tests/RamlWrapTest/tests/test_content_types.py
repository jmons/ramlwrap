"""Tests for ramlwrap validation."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from django.test import TestCase, Client


class ContentTypeTestCase(TestCase):
    """TestCase for ramlwrap content type"""

    client = None

    def setUp(self):
        self.client = Client()

    def test_post_with_valid_content_types(self):
        """
        Check that all content types defined in the openapi file are valid
        """

        valid_content_types = [
            "application/json",
            "application/x-www-form-urlencoded"
        ]

        for content_type in valid_content_types:
            response = self.client.post('/api/multi_content_type', data="{}", content_type=content_type)
            self.assertEquals(response.status_code, 200)

    def test_post_with_invalid_content_types(self):
        """
        Check that making a request with a content type which doesn't match the one in the schema, fails
        """

        valid_content_types = [
            "text/plain",
            "application/xml"
        ]

        for content_type in valid_content_types:
            response = self.client.post('/api/multi_content_type', data="{}", content_type=content_type)
            self.assertEquals(response.status_code, 422)

    def test_post_with_no_content_types(self):
        """
        Check that making a request with a content type
        but to a url which has no defined content types in the schema, passes
        """

        # Raml file doesn't define content types, so content type validation doesn't occur
        content_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "text/plain",
            "application/xml"
        ]

        for content_type in content_types:
            response = self.client.post('/api/no_content_type', data="{}", content_type=content_type)
            self.assertEquals(response.status_code, 200)
