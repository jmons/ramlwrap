"""
Raml Wrap (also known as the Raml Rap)

    Yo Yo Yo Check it Out.

    It Validates your inputs to match that file
    and it does it whilst flirting with the style
    of the pythonese, it does it with ease
    'Cause if you want to ride like a camel,
    you need to get some RAML!

    To all my homies who made this happen
    Jamie, Natalie and the Bees
    Ron managing us with Tim's a rappin'
    you aint got nothing on old - JAY TEEEeeeeee(ssss)

This file is the prototype Raml Wrap. Its going to have a license when we pick one,
until then, let JT know how much you love it, so he bothers to release it properly.

Tweet him @jmons, and leave this message in. Feel free to extend the Rap. Perhaps
sing it and put it on youtube...
"""

import json
import logging
import pyraml.parser
from django.conf.urls import url

from rest_framework.response import Response
from rest_framework.decorators import api_view

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from exceptions import FatalException

logger = logging.getLogger(__name__)


def url_patterns(raml_filepath, function_map):
    """
    creates url patterns that match the endpoints in the raml file, so can be quickly inserted into django urls.
    Note these
    :param raml_filepath: the path to the raml file (not a file pointer)
    :param function_map: a dictionary of urls to functions for mapping
    :return:
    """

    tree = pyraml.parser.load(raml_filepath)

    resource_map = _get_resource_for_tree(tree)

    patterns = _generate_patterns(resource_map, function_map)

    return patterns


def _generate_patterns(resource_map, function_map):

    patterns = []

    for t_url, resource in resource_map.iteritems():
        t_url = t_url[1:]   # String leading /
        example = None

        if resource.methods is not None:
            schema = None
            if "post" in resource.methods:
                expected_params = None
                if resource.methods['post'].queryParameters:
                    expected_params = dict(resource.methods['post'].queryParameters)
                if resource.methods['post'].body:
                    if resource.methods['post'].body['application/json']:
                        if resource.methods['post'].body['application/json'].schema:
                            schema = resource.methods['post'].body['application/json'].schema

                if resource.methods['post'].responses:
                    if resource.methods['post'].responses[200]:
                        if resource.methods['post'].responses[200].body:
                            if resource.methods['post'].responses[200].body['application/json']:
                                if resource.methods['post'].responses[200].body['application/json'].example:
                                    example = resource.methods['post'].responses[200].body['application/json'].example

                if t_url in function_map:
                    patterns.append(url("^%s$" % t_url, ValidatedPOSTAPI, {'target': function_map[t_url], 'schema': schema, 'expected_params': expected_params}))
                else:
                    patterns.append(url("^%s$" % t_url, ExamplePostAPI, {'example': example, 'schema': schema}))

            if "get" in resource.methods:
                expected_params = None
                if resource.methods['get'].queryParameters:
                    expected_params = dict(resource.methods['get'].queryParameters)
                if resource.methods['get'].responses:
                    if resource.methods['get'].responses[200]:
                        if resource.methods['get'].responses[200].body:
                            if resource.methods['get'].responses[200].body['application/json']:
                                if resource.methods['get'].responses[200].body['application/json'].example:
                                    example = resource.methods['get'].responses[200].body['application/json'].example

                if t_url in function_map:
                    patterns.append(url("^%s$" % t_url, ValidatedGETAPI, {'target': function_map[t_url], 'expected_params': expected_params}))
                else:
                    patterns.append(url("^%s$" % t_url, ExampleGetAPI, {'example': example, 'schema': schema}))

    return patterns


def _get_resource_for_tree(tree):

    resource_map = {}
    to_look_at = []

    _parse_child(tree, resource_map, to_look_at, "")

    for item in to_look_at:
        _parse_child(resource_map[item], resource_map, to_look_at, resource_map[item].path)

    return resource_map


def _parse_child(resource, resource_map, to_look_at, path):

    # This has been carefully designed so as to not use recursion.
    if resource.resources is not None:
        for next in resource.resources:
            res = resource.resources[next]
            res.path = "%s%s" % (path, next)

            resource_map[res.path] = res
            to_look_at.append(res.path)


@api_view(["GET"])
def ExampleGetAPI(request, schema, example):

    return Response(_example_api(request, schema, example))



@api_view(["POST"])
def ExamplePostAPI(request, schema, example):

    return Response(_example_api(request, schema, example))


def _example_api(request, schema, example):

    if schema:
        data = json.loads(request.body)
        validate(data, schema)

    if not example:
        return None
    else:
        return json.loads(example)


def _is_valid_query(params, expected_params):
    """
    Function to validate get request params.
    """

    # If expected params, check them. If not, pass.
    if expected_params:
        for param in expected_params:
            # If the expected param is in the query.
            if param in params:
                for check, rule in expected_params[param].iteritems():
                    if rule is not None:
                        error_message = "QueryParam [%s] failed validation check [%s]:[%s]" % (param, check, rule)
                        if check == "minLength":
                            if len(params.get(param)) < rule:
                                raise ValidationError(error_message)
                        elif check == "maxLength":
                            if len(params.get(param)) > rule:
                                raise ValidationError(error_message)

            # Isn't in the query but it is required, throw a validation exception.
            elif expected_params[param]["required"] is True:
                raise ValidationError("QueryParam [%s] failed validation check [Required]:[True]" % param)

    # TODO Add more checks here.
    return True


@api_view(["GET"])
def ValidatedGETAPI(request, expected_params, target):
    """
    Validate GET APIs.
    """

    if _is_valid_query(request.GET, expected_params):
        return target(request)


@api_view(["POST"])
def ValidatedPOSTAPI(request, schema, expected_params, target):
    """
    Validate POST APIs.
    """
    if expected_params:
        _is_valid_query(request.GET, expected_params)   # Either passes through or raises an exception.

    if schema:
        # If there is a problem with the json data, return a 400.
        try:
            data = json.loads(request.body)
        except Exception as e:
            raise FatalException("Malformed JSON in the request.", 400)

        # Else if there is a problem with the  json schema validation, return a 422 and the reason.
        try:
            validate(data, schema)   # this will throw an exception if it doesn't validate.
        except ValidationError as e:
            message = "Validation failed. {}".format(e.message)
            error_response = {
                "message": message,
                "code": e.validator
            }
            logger.info(message)
            return Response(error_response, status=422)
    else:
        data = json.loads(request.body)

    # Add validated data to request
    request.validated_data = data

    return target(request)
