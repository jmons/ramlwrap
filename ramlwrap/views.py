from django.http import HttpResponse
from django.shortcuts import render

import yaml

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
        for tag in ["title", "description", "version", "mediaType"]:
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
    request_example       = None
    response_content_type = None
    response_example      = None
    response_schema       = None
    response_description  = None


def _parse_child(resource, endpoints, item_queue, rootnode=False):
    """ Only set root = True on the root of the raml file """
    # look for endpoints etc. This is subtly different to the tree parser in the
    # main ramlwrap usage, although consider a refactor to merge these two into
    # the same. (i.e. the other one takes a function map, where as this doesn't)

    node  = resource['node']
    path  = resource['path']

    if(rootnode): 
        level = -2
    else:
        level = resource['level']

    # Parse children endpoints
    for key in node:

        if key.startswith("/"):
            item = {
                "node"  : node[key],
                "path"  : "%s%s" % (path, key),
                "level" : level + 1
            }
            item_queue.insert(0, item)

    # Skip rootnode
    if rootnode: 
        return

    # Skip empty nodes
    if not "displayName" in node:
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
                    m.request_schema = method_data['body'][m.request_content_type]['schema']

                # Request example
                if "example" in method_data['body'][m.request_content_type]:
                    m.request_example = method_data['body'][m.request_content_type]['example']

            # Response
            if 'responses' in method_data and method_data['responses']:
                for status_code in method_data['responses']:
                    if status_code == 200:
                        response = method_data['responses'][status_code]
                        for response_attr in response:
                            if response_attr == "description":
                                m.response_description = response['description']
                            elif response_attr == "body":
                                # not sure if this can fail and be valid raml?
                                m.response_content_type = next(iter(response['body']))
                                if response['body'][m.response_content_type]:
                                    if "schema" in response['body'][m.response_content_type]:
                                        m.response_schema = response['body'][m.response_content_type]['schema']
                                    if "example" in response['body'][m.response_content_type]:
                                        m.response_example = response['body'][m.response_content_type]['example']
