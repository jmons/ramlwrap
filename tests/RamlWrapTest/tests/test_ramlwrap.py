
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

import json

from ramlwrap import ramlwrap
from ramlwrap.utils.validation import ExampleAPI, ValidatedPOSTAPI, ValidatedGETAPI, _is_valid_query, _example_api
from ramlwrap.utils.raml import raml_url_patterns
from ramlwrap.utils.swaggle import swagger_url_patterns
from ramlwrap.utils.exceptions import FatalException
from django.test import TestCase
from django.test.client import RequestFactory
from unittest import skip

from jsonschema.exceptions import ValidationError

import yaml
from ramlwrap.utils.yaml_include_loader import Loader


def _internal_mockfunc(request, example):
    pass


class RamlWrapTestCase(TestCase):

    def test_ramlwrap_success(self):

        funcmap_1 = {
            "app2": _internal_mockfunc,
            "turtle": _internal_mockfunc,
            "turtle/quote": _internal_mockfunc
        }

        funcmap_2 = {
            "choose_pet": _internal_mockfunc,
            "suprise_pet": _internal_mockfunc
        }

        # Test with Raml file
        self.assertTrue(ramlwrap("RamlWrapTest/tests/fixtures/raml/test1.raml", funcmap_1))

        # Test with Swagger file - references local json files
        self.assertTrue(ramlwrap("RamlWrapTest/tests/fixtures/swagger/swagger.yaml", funcmap_2))

        # Test with Swagger file - all details within same file
        self.assertTrue(ramlwrap("RamlWrapTest/tests/fixtures/swagger/all_in_swagger.yaml", funcmap_2))


    def test_ramlwrap_fail(self):

        funcmap= {
            "test1": _internal_mockfunc,
            "test2": _internal_mockfunc,
        }

        # Test with non-existent files
        fail_file_paths = [
            "bad_file.yaml",
            1234,
            "boop",
            "RamlWrapTest/tests/fixtures/swagger/im_not_here.yaml",
        ]

        for file_path in fail_file_paths:
            with self.assertRaises(FatalException):
                ramlwrap(file_path, funcmap)

    def test_raml_url_patterns(self):

        funcmap = {
            "app2": _internal_mockfunc,
            "turtle": _internal_mockfunc,
            "turtle/quote": _internal_mockfunc
        }

        patterns = raml_url_patterns('RamlWrapTest/tests/fixtures/raml/test1.raml', funcmap)

        # These urls should now match, and have a function and default args as defined
        urls_to_test = [
            {
                'url': "app2",
                'function': ValidatedPOSTAPI,
                'default_args': {
                    'target': _internal_mockfunc, 
                    'schema': {"$schema": "http://json-schema.org/draft-04/schema#", "description": "Schema for a request", "type": "object", "required": ["data"], "properties": {"data": {"description": "Some data that is required", "type": "string"}}}
                }
            },
            {
                'url': "app2/foo",
                'function': ExampleAPI,
                'default_args': {'example': None}
            },
            {
                'url': "app1",
                'function': ExampleAPI,
                'default_args': {'example': "{ 'data': 'foo' }"}
            },
            {
                'url': "turtle",
                'function': ValidatedGETAPI,
                'default_args': {
                    'target': _internal_mockfunc, 
                    'expected_params': {'name': {'repeat': None, 'displayName': 'Name', 'name': None, 'default': None, 'pattern': None, 'enum': None, 'maximum': None, 'required': True, 'minimum': None, 'minLength': None, 'maxLength': None, 'type': 'string', 'example': 'Michelangelo', 'description': None}}}
            },
            {
                'url': "app2/foo/bar",
                'function': ExampleAPI,
                'default_args': {'example': None}
            },
            {
                'url': "app3/foo/bar",
                'function': ExampleAPI,
                'default_args': {'example': None}
            }
        ]

        for x in urls_to_test:
            found = False

            for p in patterns:

                if p.regex.match(x['url']):
                    found = True
                    self.assertEqual(x['function'], p.callback)

                    for name, val in x['default_args'].items():
                        self.assertIn(name, p.default_args)
                        if type(val) == dict and type(p.default_args[name]) == dict:
                            self.assertEqual(set(val), set(p.default_args[name]))
                        else:
                            self.assertEqual(val, p.default_args[name])

            if not found:
                self.fail("[%s] did not match any of the regexes" % x['url'])

    def test_swagger_url_patterns(self):

        funcmap = {
            "choose_pet": _internal_mockfunc,
            "suprise_pet": _internal_mockfunc
        }

        # Load json refs into the file
        with open("RamlWrapTest/tests/fixtures/swagger/swagger.yaml", "r") as stream:
            swagger_dict = yaml.load(stream, Loader)

        patterns = swagger_url_patterns(swagger_dict, funcmap)

        # These urls should now match, and have a function and default args as defined
        urls_to_test = [
            {
                'url': "choose_pet",
                'function': ValidatedPOSTAPI,
                'default_args': {'target': _internal_mockfunc,
                                 'schema': {u'required': [u'animalWanted'], u'type': u'object', u'properties': {
                                     u'animalWanted': {u'pattern': u'^[a-zA-Z0-9-]+$', u'minimum': 3,
                                                       u'type': u'string', u'example': u'cat'}}}
                                 }
            },
            {
                'url': "suprise_pet",
                'function': ValidatedGETAPI,
                'default_args': {}
            }
        ]

        for x in urls_to_test:
            found = False

            for p in patterns:
                if p.regex.match(x['url']):
                    found = True
                    self.assertEqual(x['function'], p.callback)

                    for name, val in x['default_args'].items():
                        self.assertIn(name, p.default_args)

                        if type(val) == dict and type(p.default_args[name]) == dict:
                            self.assertEqual(set(val), set(p.default_args[name]))

                        else:
                            self.assertEqual(val, p.default_args[name])

            if not found:
                self.fail("[%s] did not match any of the regexes" % x['url'])

    @skip("This test needs fixing.")
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
        request = rf.get("/turtle/?name=Michelangelo")
        self.assertEqual(_is_valid_query(request.GET, expected_params), True)

        request = rf.get("/turtle/?name=Mike")
        with self.assertRaises(ValidationError):
            _is_valid_query(request.GET, expected_params)

        request = rf.get("/turtle/")
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

        request = rf.get("/turtle/quote/?name=Michelangelo")
        self.assertEquals(_is_valid_query(request.GET, expected_params), True)

    def test_example(self):
        """
        Testing the do thing function of ExampleAPI
        """

        data = '{"splat":"splat"}'

        response = _example_api(None, None, data)

        self.assertEqual(json.loads(data), response)

    def test_empty_post(self):
        """
        Testing that RAMLWRAP can handle a an empty post request.
        """

        response = _example_api(None, None, None)
        self.assertEqual(response, None)


