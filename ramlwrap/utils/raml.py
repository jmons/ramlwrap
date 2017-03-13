import logging
import pyraml.parser
from django.conf.urls import url

from . validation import ExampleAPI, ValidatedPOSTAPI, ValidatedGETAPI

logger = logging.getLogger(__name__)


def raml_url_patterns(raml_filepath, function_map):
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

    for t_url, resource in resource_map.items():
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
                    patterns.append(url("^%s$" % t_url, ExampleAPI, {'example': example, 'schema': schema}))

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
                    patterns.append(url("^%s$" % t_url, ExampleAPI, {'example': example, 'schema': schema}))

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
