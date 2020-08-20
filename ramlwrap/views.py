from django.http import HttpResponse
from django.shortcuts import render
from collections import OrderedDict

import yaml, copy

from .utils.yaml_include_loader import Loader

try:
    # This import fails for django 1.9
    from django.views import View
except Exception as error:
    print("failed to [from django.views import View] {}".format(error))
    from django.views.generic.base import View


class RamlDoc(View):
    """
    As a view system, this should be called with the raml_file set. If desired
    then replacing the template is also possible with the variable `template`.
    """

    raml_file = None
    # FIXME: make this inside ramlwrap and fix setup.py to have fixtures
    template = 'ramlwrap_default_main.html'

    def get(self, request):
        # WARNING multi return function (view switching logic)
        context = self._parse_endpoints(request)

        if "type" in request.GET:
            if request.GET['type'] in ("single_api", "schema"):
                target_endpoint = request.GET['entry']
                endpoints = context['endpoints']
                for suspect in endpoints:
                    if suspect.url == target_endpoint:
                        endpoints = [ suspect ]
                        context['endpoints'] = endpoints

            if request.GET['type'] == "schema":
                if request.GET['schema_direction'] == "request":
                    # FIXME ok this doesnt work. Writing here- need to have a better string to work out what you want.
                    return HttpResponse(context['endpoints'][0].request_schema)
                else:
                    raise Exception("Not implemneted yet - response schema")

        return render(request, self.template, context)

    def _parse_endpoints(self, request):

        # Read Raml file
        file = open(self.raml_file)
        loaded_yaml = yaml.load(file, Loader=Loader)  # This loader has the !include directive
        file.close()

        # Parse raml file and generate the tree
        item_queue = [] # Queue
        endpoints  = [] # Endpoint list

        # Parse root and queue its children
        root_element = {
            "node": loaded_yaml,
            "path": ""
        }
        _parse_child(root_element, endpoints, item_queue, True)

        # Keep parsing children queue until empty
        while item_queue:
            item = item_queue.pop(0)
            _parse_child(item, endpoints, item_queue)

        # Build object with parsed data
        context = {
            "endpoints" : endpoints
        }

        # Root attributes
        for tag in ["title", "description", "version", "mediaType", "baseUri"]:
            if tag in loaded_yaml:
                context[tag] = loaded_yaml[tag]
            else:
                context[tag] = None

        # Nested attributes
        for tag in ["documentation", "traits", "securitySchemes"]:
            context[tag] = {}
            if tag in loaded_yaml:
                for key in loaded_yaml[tag][0]:
                    context[tag][key] = loaded_yaml[tag][0][key]

        # Return the data to the template
        return context


# FIXME delete this before committing. Holder for Gateway
def noscript(request):
    return HttpResponse("")


class Endpoint():
    url          = ""
    description  = ""
    request_type = ""
    methods      = None
    level        = 0

    def __init__(self):
        self.methods = []


class Method():
    method_type = ""
    displayName = ""
    description = ""

    request_content_type  = None
    request_schema        = None
    request_schema_original = None
    request_example       = None
    request_examples      = None

    response_content_type = None
    response_schema       = None
    response_example      = None
    response_examples     = None
    response_description  = None

    responses = None
    examples = None

    def __init__(self):
        self.responses = []
        self.examples = []


class Response:
    content_type = None
    schema = None
    schema_original = None
    examples = None
    description = None
    status_code = None

    def __init__(self, content_type=None, schema=None, schema_original=None, description=None, status_code=None):
        self.content_type = content_type
        self.schema = schema
        self.schema_original = schema_original
        self.examples = []
        self.description = description
        self.status_code = status_code


class Example:
    title = None
    body = None

    def __init__(self, title=None, body=None):
        self.title = title
        self.body = body


def _parse_child(resource, endpoints, item_queue, rootnode=False):
    """ Only set root = True on the root of the raml file """
    # look for endpoints etc. This is subtly different to the tree parser in the
    # main ramlwrap usage, although consider a refactor to merge these two into
    # the same. (i.e. the other one takes a function map, where as this doesn't)

    node = resource['node']
    path = resource['path']

    if rootnode:
        level = -2
    else:
        level = resource['level']

    # Storing endpoints in temporary array to preserve order
    child_item_array = []

    # Parse children endpoints
    for key in node:
        if key.startswith("/"):
            item = {
                "node": node[key],
                "path": "%s%s" % (path, key),
                "level": level + 1
            }
            child_item_array.insert(0, item)

    for i in child_item_array:
        item_queue.insert(0, i)

    # Skip rootnode
    if rootnode:
        return

    # Skip empty nodes
    if "displayName" not in node:
        return

    # Parse endpoint data
    current_endpoint = Endpoint()
    current_endpoint.url = path
    current_endpoint.level = level
    endpoints.append(current_endpoint)

    # Endpoint name
    if "displayName" in node:
        current_endpoint.displayName = node["displayName"]

    # Endpoint description
    if "description" in node:
        current_endpoint.description = node["description"]

    # Endpoint methods
    for method_type in ["get", "post", "put", "patch", "delete"]:

        if method_type in node:
            method_data = node[method_type]

            m = Method()
            m.method_type = method_type
            current_endpoint.methods.append(m)

            # Method description
            if "description" in method_data:
                m.description = method_data['description']

            # Request
            if "body" in method_data:
                # if body, look for content type : if not there maybe not valid raml?
                # FIXME: this may be a bug requiring a try/catch - need more real world example ramls
                m.request_content_type = next(iter(method_data['body']))

                # Request schema
                if "schema" in method_data['body'][m.request_content_type]:
                    m.request_schema_original = method_data['body'][m.request_content_type]['schema']
                    m.request_schema = _parse_schema_definitions(copy.deepcopy(m.request_schema_original))

                # Request example
                if "example" in method_data['body'][m.request_content_type]:
                    m.request_example = method_data['body'][m.request_content_type]['example']
                    m.examples.append(Example(body=method_data['body'][m.request_content_type]['example']))

                # Request examples
                if "examples" in method_data['body'][m.request_content_type]:
                    m.request_examples = method_data['body'][m.request_content_type]['examples']
                    # New examples object
                    for example in method_data['body'][m.request_content_type]['examples']:
                        m.examples.append(
                            Example(title=example, body=method_data['body'][m.request_content_type]['examples'][example]))

            # Response
            if 'responses' in method_data and method_data['responses']:
                for status_code in method_data['responses']:
                    _parse_response(m, method_data, status_code)


def _parse_response(m, method_data, status_code):
    response_obj = Response(status_code=status_code)

    response = method_data['responses'][status_code]

    if response:
        for response_attr in response:
            if response_attr == "description":
                response_obj.description = response['description']
            elif response_attr == "body":
                # not sure if this can fail and be valid raml?
                response_obj.content_type = next(iter(response['body']))
                if response['body'][response_obj.content_type]:
                    if "schema" in response['body'][response_obj.content_type]:
                        response_obj.schema_original = response['body'][response_obj.content_type][
                            'schema']
                        response_obj.schema = _parse_schema_definitions(
                            copy.deepcopy(response_obj.schema_original))
                    if "example" in response['body'][response_obj.content_type]:
                        response_obj.examples.append(Example(body=response['body'][response_obj.content_type]['example']))
                        # For backward compatibility
                        if status_code == 200:
                            m.response_example = response['body'][response_obj.content_type]['example']
                    if "examples" in response['body'][response_obj.content_type]:
                        for example in response['body'][response_obj.content_type]['examples']:
                            response_obj.examples.append(
                                Example(title=example, body=response['body'][response_obj.content_type]['examples'][example]))
                        # For backward compatibility
                        if status_code == 200:
                            m.response_example = response['body'][response_obj.content_type]['examples']

    # For backward compatibility, store 200 responses in specific fields
    if status_code == 200:
        m.response_content_type = response_obj.content_type
        m.response_description = response_obj.description
        m.response_schema_original = response_obj.schema_original
        m.response_schema = response_obj.schema

    m.responses.append(response_obj)


def _parse_schema_definitions(schema):

    # If the schema has definitions, replace definitions references with the definition data
    if "definitions" in schema:
        definitions = schema['definitions']

        # Parse definitions in definition properties
        for key in definitions:
            if "properties" in definitions[key]:
                definitions[key]['properties'] = _parse_properties_definitions(definitions[key]['properties'], definitions)

        # Parse definitions in properties
        if "properties" in schema:
            schema['properties'] = _parse_properties_definitions(schema['properties'], definitions)

    return schema


def _parse_properties_definitions(properties, definitions):

    for key in properties:

        # If a property has a $ref definition reference, replace it with the definition
        if "$ref" in properties[key]:
            definition = properties[key]['$ref'].replace("#/definitions/", "")
            if definition in definitions:
                properties[key] = definitions[definition]

        elif "type" in properties[key]:

            # If the property is an object, parse its properties for definitions recursively
            if properties[key]['type'] == "object" and "properties" in properties[key]:
                properties[key]['properties'] = _parse_properties_definitions(properties[key]['properties'], definitions)

            # If the property is an array with a $ref definition reference, replace it with the definition
            elif properties[key]['type'] == "array" and "items" in properties[key] and "$ref" in properties[key]['items']:
                definition = properties[key]['items']['$ref'].replace("#/definitions/", "")
                if definition in definitions:
                    properties[key]['items'] = definitions[definition]

    return properties
