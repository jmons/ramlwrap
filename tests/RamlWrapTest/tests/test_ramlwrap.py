"""Tests for RamlWrap"""
import json
import os
import sys
import yaml

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from ramlwrap import ramlwrap
from ramlwrap.utils.validation import WrappedAPI
from ramlwrap.utils.raml import raml_url_patterns
from ramlwrap.utils.swaggle import swagger_url_patterns
from ramlwrap.utils.exceptions import FatalException
from django.conf import settings
from django.test import TestCase, Client
from django.test.client import RequestFactory
from unittest import skip

from jsonschema.exceptions import ValidationError

from ramlwrap.utils.yaml_include_loader import Loader


def _internal_mockfunc(request, example):
    pass

def _internal_mock_post(request, example):
    """json loads the request and return it."""
    return json.loads(request.validated_data)


class RamlWrapTestCase(TestCase):

    client = None

    def setUp(self):
        self.client = Client()

    def test_ramlwrap_success(self):

        funcmap_1 = {
            'app2': _internal_mockfunc,
            'turtle': _internal_mockfunc,
            'turtle/quote': _internal_mockfunc
        }

        funcmap_2 = {
            'choose_pet': _internal_mockfunc,
            'suprise_pet': _internal_mockfunc
        }

        # Test with Raml file
        self.assertTrue(ramlwrap('RamlWrapTest/tests/fixtures/raml/test1.raml', funcmap_1))

        # Test with Swagger file - references local json files
        self.assertTrue(ramlwrap('RamlWrapTest/tests/fixtures/swagger/swagger.yaml', funcmap_2))

        # Test with Swagger file - all details within same file
        self.assertTrue(ramlwrap('RamlWrapTest/tests/fixtures/swagger/all_in_swagger.yaml', funcmap_2))

    def test_ramlwrap_fail(self):
        """Test that ramlwrap raises FatalExceptions where needed."""

        funcmap = {
            'test1': _internal_mockfunc,
            'test2': _internal_mockfunc,
        }

        # Test with non-existent files
        fail_file_paths = [
            'bad_file.yaml',
            1234,
            'boop',
            'RamlWrapTest/tests/fixtures/swagger/im_not_here.yaml',
        ]

        for file_path in fail_file_paths:
            with self.assertRaises(FatalException):
                ramlwrap(file_path, funcmap)

    def test_raml_url_patterns(self):
        """Test that given a raml file the patterns are generated correctly."""
        funcmap = {
            'app2': _internal_mockfunc,
            'turtle': _internal_mockfunc,
            'turtle/quote': _internal_mockfunc
        }

        patterns = raml_url_patterns('RamlWrapTest/tests/fixtures/raml/test1.raml', funcmap)

        # These urls should now match, and have a function and default args as defined
        urls_to_test = [
            {
                'url': 'app2',
                'function': WrappedAPI.validate,
            },
            {
                'url': 'app2/foo',
                'function': WrappedAPI.mock,
            },
            {
                'url': 'app1',
                'function': WrappedAPI.mock,
            },
            {
                'url': 'turtle',
                'function': WrappedAPI.validate,
            },
            {
                'url': 'app2/foo/bar',
                'function': WrappedAPI.mock,
            },
            {
                'url': 'app3/foo/bar',
                'function': WrappedAPI.mock,
            }
        ]

        for x in urls_to_test:
            found = False
            for p in patterns:
                if p.regex.match(x['url']):
                    found = True
                    self.assertEqual(type(x['function']), type(p.callback))
            if not found:
                self.fail('[%s] did not match any of the regexes' % x['url'])

    def test_swagger_url_patterns(self):

        funcmap = {
            'choose_pet': _internal_mockfunc,
            'suprise_pet': _internal_mockfunc
        }

        # Load json refs into the file
        with open('RamlWrapTest/tests/fixtures/swagger/swagger.yaml', 'r') as stream:
            swagger_dict = yaml.load(stream, Loader)

        patterns = swagger_url_patterns(swagger_dict, funcmap)

        # These urls should now match, and have a function and default args as defined
        urls_to_test = [
            {
                'url': 'choose_pet',
                'function': WrappedAPI.validate,
            },
            {
                'url': 'suprise_pet',
                'function': WrappedAPI.validate,
            }
        ]

        for x in urls_to_test:
            found = False
            for p in patterns:
                if p.regex.match(x['url']):
                    found = True
                    self.assertEqual(type(x['function']), type(p.callback))
            if not found:
                self.fail('[%s] did not match any of the regexes' % x['url'])

            if not found:
                self.fail('[%s] did not match any of the regexes' % x['url'])

    @skip('This test needs fixing.')
    def test_get_api(self):
        """
        Test that the ValidatedGETAPI is validating correctly.
        """
        expected_params = {
            'name': {
                'repeat': None,
                'displayName': 'Name',
                'name': None,
                'default': None,
                'pattern': None,
                'enum': None,
                'maximum': None,
                'required': True,
                'minimum': None,
                'minLength': 5,
                'maxLength': None,
                'type': 'string',
                'example': 'Michelangelo',
                'description': None
            }
        }
        rf = RequestFactory()
        request = rf.get('/turtle/?name=Michelangelo')
        self.assertEqual(_is_valid_query(request.GET, expected_params), True)

        request = rf.get('/turtle/?name=Mike')
        with self.assertRaises(ValidationError):
            _is_valid_query(request.GET, expected_params)

        request = rf.get('/turtle/')
        with self.assertRaises(ValidationError):
            _is_valid_query(request.GET, expected_params)

        expected_params = {
            'name': {
                'repeat': None,
                'displayName': 'Name',
                'name': None,
                'default': None,
                'pattern': None,
                'enum': None,
                'maximum': None,
                'required': True,
                'minimum': None,
                'minLength': 5,
                'maxLength': None,
                'type': 'string',
                'example': 'Michelangelo',
                'description': None
            },
            'type': {
                'repeat': None,
                'displayName': 'Quote type',
                'name': None,
                'default': None,
                'pattern': None,
                'enum': None,
                'maximum': None,
                'required': False,
                'minimum': None,
                'minLength': 4,
                'maxLength': None,
                'type': 'string',
                'example': 'funny',
                'description': None
            }
        }

        request = rf.get('/turtle/quote/?name=Michelangelo')
        self.assertEquals(_is_valid_query(request.GET, expected_params), True)

    def test_raml_schema_validation(self):
        """Test that the validation is applied when present"""

        response = self.client.post('/app1', data='{}', content_type='application/json')
        self.assertEquals(422, response.status_code)

    def test_raml_example_returned(self):
        """Test that the example is returned as expected."""
        response = self.client.post('/app1', data=json.dumps({ 'data': 'foobar'}), content_type='application/json')

        self.assertEqual(response.status_code, 200)

        expected_data = {'data': 'foo'}
        reply_data = response.content.decode('utf-8')
        self.assertEqual(expected_data, json.loads(reply_data))

    def test_empty_post(self):
        """Testing that ramlwrap can handle an empty post request."""

        response = self.client.post('/app2/foo', data=None)
        self.assertEqual(response.status_code, 200)

    def test_validation_handler(self):
        """
        Test that given a custom validation handler path, it is called.
        Test that if no handler is given, the default handler is used.
        """

        # Test that the custom method is called and a response is returned.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = 'RamlWrapTest.utils.validation_handler.custom_validation_response'
        response = self.client.post('/app1', data='{}', content_type='application/json')
        self.assertEquals(418, response.status_code)

        # Test that the custom method is called and an exception is raised.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = 'RamlWrapTest.utils.validation_handler.custom_validation_exception'
        with self.assertRaises(NotImplementedError):
            response = self.client.post('/app1', data='{}', content_type='application/json')

        # Test that the default is called.
        settings.RAMLWRAP_VALIDATION_ERROR_HANDLER = None
        response = self.client.post('/app1', data='{}', content_type='application/json')
        self.assertEquals(422, response.status_code)

        delattr(settings, 'RAMLWRAP_VALIDATION_ERROR_HANDLER')
        response = self.client.post('/app1', data='{}', content_type='application/json')
        self.assertEquals(422, response.status_code)
