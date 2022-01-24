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


class ActionsTestCase(TestCase):
    """TestCase for ramlwrap JSON correct action responses"""

    client = None

    def setUp(self):
        self.client = Client()

    def test_no_schema_validation_passes_through(self):
        """Test that given an action with no schema and a request
        with a json body, the body is passed through."""

        action = Action()
        action.resp_content_type = ContentType.JSON
        action.target = _mock_post_target
        request = RequestFactory().post(
            path="post-api-no-request-schema-or-example",
            data=json.dumps({"testkey": "testvalue"}),
            content_type="application/json")

        self.assertTrue(_validate_api(request, action))

    def test_validated_get_passes_through(self):
        """Test that a valid get request passes through
        to the action and the correct response is returned."""

        action = Action()
        action.target = _mock_get_target
        action.resp_content_type = ContentType.JSON
        request = RequestFactory().get("/api-with-query-params", {"param1": 2, "param2": "hello"})

        resp = _validate_api(request, action)
        self.assertTrue(resp.__class__ is HttpResponse)
        self.assertEqual(resp.content.decode("utf-8"), json.dumps({"valid": True}))

    def test_validated_post_passes_through(self):
        """Test that a valid post request passes through
        to the action and the correct response is returned."""
        action = Action()
        action.target = _mock_post_target_json_resp
        action.resp_content_type = ContentType.JSON
        request = RequestFactory().post("/api-with-query-params?param2=one2345&param3=2")

        resp = _validate_api(request, action)
        self.assertTrue(resp.__class__ is HttpResponse)
        self.assertEqual(resp.content.decode("utf-8"), json.dumps({"valid": True}))

    def test_unsupported_method_returns_not_allowed(self):
        """Test that when a request is made for an
        unsupported method, a 405 is returned with correct list of permitted methods.
        """
        endpoint = Endpoint("/api-with-query-params")
        endpoint.request_method_mapping = {
            "GET": {},
            "POST": {}
        }

        request = RequestFactory().generic(
            "/api-with-query-params",
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

        endpoint = Endpoint("/api-with-query-params")
        endpoint.request_method_mapping = {
            "GET": {},
        }

        request = RequestFactory().post(
            "/api-with-query-params",
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
