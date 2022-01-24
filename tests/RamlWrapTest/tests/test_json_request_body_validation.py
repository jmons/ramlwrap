"""Tests for ramlwrap validation."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from ramlwrap.utils.validation import _validate_api, Action, ContentType, Endpoint

from django.http.response import HttpResponse, HttpResponseNotAllowed
from django.test import TestCase, Client
from django.test.client import RequestFactory


def _mock_post_target(request, dynamic_value=None):
    """Return true if the validated data is correct."""
    if request.validated_data == {"testkey": "testvalue"}:
        valid = True
    else:
        valid = False
    return valid


def _mock_post_target_json_resp(request, dynamic_value=None):
    """Mock function that returns some json for a post."""
    return {"valid": True}


def _mock_get_target(request, dynamic_value=None):
    """Return true if the validated data is correct."""
    valid = True
    if not request.GET.get("param1") == "2":
        valid = False
    if not request.GET.get("param2") == "hello":
        valid = False
    return {"valid": valid}


class JsonRequestBodyValidationInlineYamlSchemaTestCase(TestCase):
    """TestCase for ramlwrap JSON request body validation against schema."""

    client = None

    def setUp(self):
        self.client = Client()

    def test_valid_json_request_body_is_accepted(self):
        """Test that when schema is present, it is used to
        validate the incoming request.
        """
        valid_request_body = {
                  "appId": "1"
                }
        response = self.client.post("/post-api-yaml-schema", data=json.dumps(valid_request_body), content_type="application/json")
        self.assertEquals(200, response.status_code)

    def test_invalid_json_request_body_returns_422(self):
        """Test that when schema is present, it is used to
        validate the incoming request.
        """
        # request should have a appId field
        invalid_request_body = {
            "version": "1"
        }
        response = self.client.post("/post-api-yaml-schema", data=json.dumps(invalid_request_body), content_type="application/json")
        self.assertEquals(422, response.status_code, "Invalid JSON format should return 422")
        self.assertEqual({"message": "Validation failed. 'appId' is a required property", "code": "required"},
                         json.loads(response.content.decode('utf-8')))
