"""Tests for ramlwrap validation."""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from ramlwrap.utils.validation import _validate_api, Action, ContentType, Endpoint

from django.conf import settings
from django.http.response import HttpResponse, HttpResponseNotAllowed
from django.test import TestCase, Client
from django.test.client import RequestFactory

from jsonschema.exceptions import ValidationError


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


class ValidationTestCase(TestCase):
    """TestCase for ramlwrap validation functionality."""

    client = None

    def setUp(self):
        self.client = Client()

    def test_raml_schema_validation(self):
        """Test that when schema is present, it is used to
        validate the incoming request.
        """

        response = self.client.post("/api", data="{}", content_type="application/json")
        self.assertEquals(422, response.status_code)
        self.assertEqual({"message": "Validation failed. 'data' is a required property", "code": "required"},
                         json.loads(response.content.decode('utf-8')))

    def test_get_with_valid_params(self):
        """
        Test that a get api with valid query params doesn't raise
        an exception.
        """

        self.client.get("/api/3", {"param2": "test5", "param3": 2})

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

    def test_validation_handler(self):
        """
        Test that given a custom validation handler path, it is called.
        Test that if no handler is given, the default handler is used.
        """

        # Test that the custom method is called and a response is returned.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = "RamlWrapTest.utils.validation_handler.custom_validation_response"
        response = self.client.post("/api", data="{}", content_type="application/json")
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

    def test_no_schema_validation_passes_through(self):
        """Test that given an action with no schema and a request
        with a json body, the body is passed through."""

        action = Action()
        action.resp_content_type = ContentType.JSON
        action.target = _mock_post_target
        request = RequestFactory().post(
            path="api/4",
            data=json.dumps({"testkey": "testvalue"}),
            content_type="application/json")

        self.assertTrue(_validate_api(request, action))

    def test_validated_get_passes_through(self):
        """Test that a valid get request passes through
        to the action and the correct response is returned."""

        action = Action()
        action.target = _mock_get_target
        action.resp_content_type = ContentType.JSON
        request = RequestFactory().get("api/3", {"param1": 2, "param2": "hello"})

        resp = _validate_api(request, action)
        self.assertTrue(resp.__class__ is HttpResponse)
        self.assertEqual(resp.content.decode("utf-8"), json.dumps({"valid": True}))

    def test_validated_post_passes_through(self):
        """Test that a valid post request passes through
        to the action and the correct response is returned."""
        action = Action()
        action.target = _mock_post_target_json_resp
        action.resp_content_type = ContentType.JSON
        request = RequestFactory().post("/api/3?param2=one2345&param3=2")

        resp = _validate_api(request, action)
        self.assertTrue(resp.__class__ is HttpResponse)
        self.assertEqual(resp.content.decode("utf-8"), json.dumps({"valid": True}))

    def test_unsupported_method_returns_not_allowed(self):
        """Test that when a request is made for an
        unsupported method, a 405 is returned with correct list of permitted methods.
        """
        endpoint = Endpoint("/api/3")
        endpoint.request_method_mapping = {
            "GET": {},
            "POST": {}
        }

        request = RequestFactory().generic(
            "/api/3",
            "UNSUPPORTED_METHOD",
            data=json.dumps({"testkey": "testvalue"}),
            content_type="application/json")

        resp = endpoint.serve(request)
        self.assertTrue(resp.__class__ is HttpResponseNotAllowed)

        allowed_methods = self._parse_allowed_methods(resp)
        self.assertEqual(allowed_methods, ["GET", "POST"])

    def test_unknown_method_returns_not_allowed(self):
        """Test that when a request is made for an unknown
        method, a 405 is returned with correct list of permitted methods.
        """

        endpoint = Endpoint("/api/3")
        endpoint.request_method_mapping = {
            "GET": {},
        }

        request = RequestFactory().post(
            "/api/3",
            data=json.dumps({"testkey": "testvalue"}),
            content_type="application/json")

        resp = endpoint.serve(request)

        self.assertTrue(resp.__class__ is HttpResponseNotAllowed)
        allowed_methods = self._parse_allowed_methods(resp)
        self.assertEqual(allowed_methods, ["GET"])

    def _parse_allowed_methods(self, resp):
        allowed_methods_with_spacing = resp['Allow'].split(',')
        allowed_methods = []
        for method in allowed_methods_with_spacing:
            allowed_methods.append(method.strip())

        allowed_methods.sort()
        return allowed_methods
