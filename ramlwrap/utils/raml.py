import logging
import yaml

from django.conf.urls import url

from .yaml_include_loader import Loader
from .validation import Endpoint, Action

logger = logging.getLogger(__name__)


def raml_url_patterns(raml_filepath, function_map):
    """
    creates url patterns that match the endpoints in the raml file, so can be quickly inserted into django urls.
    Note these
    :param raml_filepath: the path to the raml file (not a file pointer)
    :param function_map: a dictionary of urls to functions for mapping
    :return:
    """

    # This function will run in three phases:
    # 1) Load the raml (as a yaml document)
    # 2) Parse the raml into nodes that represent 'endpoints'
    # 3) Convert endpoints into a url structure

    # migrating from pyraml: file handling now has to be done by us
    # worry about streaming files in future version (for VERY BIG raml?)
    f = open(raml_filepath)
    tree = yaml.load(f, Loader=Loader)  # This loader has the !include directive
    f.close()

    # The resource map is the found nodes

    patterns = []
    to_look_at = [
        {
            "node": tree,
            "path": ""
        }
    ]

    # FIXME: get baseuri, and default media types out here

    defaults = {
        "content_type": "application/json",
    }

    for item in to_look_at:
        _parse_child(item, patterns, to_look_at, function_map, defaults)

    return patterns


def _parse_child(resource, patterns, to_look_at, function_map, defaults):

    node = resource['node']
    path = resource['path']
    local_endpoint = None

    for k in node:
        if k.startswith("/"):
            item = {
                "node": node[k],
                "path": "%s%s" % (path, k)
            }

            to_look_at.append(item)

        else:
            # attribute not subpath
            # FIXME: deal with other headers in future ? (unit tests!)
            
            if k in ("get", "post", "put"):
                act = node[k]

                if not local_endpoint:
                    local_endpoint = Endpoint(path[1:])

                # look for a 200.body.{{content-type}}
                # and a 200.body.{{content-type}}.example

                a = Action()
                a.resp_content_type = defaults["content_type"]

                # FIXME: at some point allow a construct for multi-methods
                if path in function_map:
                    if "function" in function_map[path]:
                        # add the target function
                        a.target = function_map[path]["function"]

                    if "regex" in function_map[path]:
                        # Add dynamic value regex if present
                        a.dynamic_value = function_map[path]["regex"]
                
                if 'body' in act:
                    # if body, look for content type : if not there maybe not valid raml?
                    # FIXME: this may be a bug requring a try/catch - need more real world example ramls
                    a.requ_content_type = next(iter(act['body']))
                    # Also look for a schema here
                    if "schema" in act['body'][a.requ_content_type]:
                        a.schema = act['body'][a.requ_content_type]['schema']

                # This horrendous if blocks are to get around none type erros when the tree
                # is not fully built out.

                if 'responses' in act and act['responses']:
                    for status_code in act['responses']:
                        # this is a response that we care about:
                        
                        if status_code == 200:
                            two_hundred = act['responses'][200]
                            for resp_attr in two_hundred:
                                if resp_attr == "body":
                                    # not sure if this can fail and be valid raml?
                                    a.resp_content_type = next(iter(two_hundred['body']))
                                    if two_hundred['body'][a.resp_content_type]:
                                        if "example" in two_hundred['body'][a.resp_content_type]:
                                            a.example = two_hundred['body'][a.resp_content_type]['example']
                                        
                if "queryParameters" in act and act["queryParameters"]:
                    # FIXME: does this help in the query parameterising?
                    # For filling out a.queryparameterchecks
                    a.query_parameter_checks = act['queryParameters']

                if k == "get":
                    local_endpoint.add_action("GET", a)
                elif k == "post":
                    local_endpoint.add_action("POST", a)
                elif k == "put":
                    local_endpoint.add_action("PUT", a)

    if local_endpoint:
        # strip leading
        if local_endpoint.url.startswith("/"):
            url_to_use = local_endpoint.url[1:]
        else:
            url_to_use = local_endpoint.url

        patterns.append(url("^%s$" % url_to_use, local_endpoint.serve))
