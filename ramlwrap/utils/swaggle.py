"""
The Swagger parsing section of Raml Wrap
"""

import json
import logging

from swagger_parser import SwaggerParser
from django.conf.urls import url

from . validation import ExampleAPI, ValidatedPOSTAPI, ValidatedGETAPI

logger = logging.getLogger(__name__)


def swagger_url_patterns(swagger_dict, function_map):

    # Init with dictionary
    parser = SwaggerParser(swagger_dict=swagger_dict)

    tree = parser

    resource_map = {}

    _parse_swagger_child(tree, resource_map)

    patterns = _generate_swagger_patterns(resource_map, function_map, tree)

    return patterns


def _parse_swagger_child(resource, resource_map):

    # This has been carefully designed so as to not use recursion.
    if resource.paths is not None:
        for next in resource.paths:
            res = resource.paths[next]
            res["path"] = "%s%s" % ("", str(next))
            resource_map[res["path"]] = res


def _generate_swagger_patterns(resource_map, function_map, tree):

    patterns = []

    example_json = tree.definitions_example

    for t_url, resource in resource_map.items():

        t_url = t_url[1:]   # String leading /
        example = None

        if resource["path"] is not None:
            schema = None
            if "post" in resource:
                expected_params = None
                if "parameters" in resource["post"]:
                    expected_params = dict(resource["post"]["parameters"])
                    # Get the name from the parameters so we can grab the schema
                    for name in resource["post"]["parameters"]:
                        if "schema" in resource["post"]["parameters"][name]:
                            definition = resource["post"]["parameters"][name]["schema"]["$ref"]
                            # split off the definition name
                            definition = definition.split('#/definitions/')[1]
                            schema = json.loads(tree.json_specification)["definitions"][definition]

                        if "200" in resource["post"]["responses"]:
                            if "schema" in resource["post"]["responses"]["200"]:
                                definition = resource["post"]["responses"]["200"]["schema"]["$ref"]
                                # split off the definition name
                                definition = definition.split('#/definitions/')[1]
                                if definition in example_json:
                                    example = example_json[definition]

                if t_url in function_map:
                    patterns.append(url("^%s$" % t_url, ValidatedPOSTAPI, {'target': function_map[t_url], 'schema': schema, 'expected_params': expected_params}))
                else:
                    patterns.append(url("^%s$" % t_url, ExampleAPI, {'example': example, 'schema': schema}))

            if "get" in resource:
                expected_params = None
                if "parameters" in resource["get"]:
                    expected_params = dict(resource["get"]["parameters"])
                if "responses" in resource["get"]:
                    if "200" in resource["get"]["responses"]:
                        if "schema" in resource["get"]["responses"]["200"]:
                            definition = resource["get"]["responses"]["200"]["schema"]["$ref"]
                            # split off the definition name
                            definition = definition.split('#/definitions/')[1]
                            if definition in example_json:
                                example = example_json[definition]

                if t_url in function_map:
                    patterns.append(url("^%s$" % t_url, ValidatedGETAPI, {'target': function_map[t_url], 'expected_params': expected_params}))
                else:
                    patterns.append(url("^%s$" % t_url, ExampleAPI, {'example': example, 'schema': schema}))

    return patterns


