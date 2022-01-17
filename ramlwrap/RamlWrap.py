"""
Raml Wrap (also known as the Raml Rap)

    Yo Yo Yo Check it Out.

    It Validates your inputs to match that file
    and it does it whilst flirting with the style
    of the pythonese, it does it with ease
    'Cause if you want to ride like a camel,
    you need to get some RAML!

Or (cough) as of v3, open api spec.

As of March 2017, RamlWrap has been MIT license, see LICENSE 
"""
import logging

from . utils.validation import Endpoint, Action
from . utils.exceptions import FatalException

from openapi_parser.parser.loader import OpenApiParser
from openapi_parser.parser import OpenApiLoaderError

from django.urls import re_path

logger = logging.getLogger(__name__)


def ramlwrap(file_path, function_map):
    """
    Produce Patterns for a file, mapped to api calls where provided in the function map
    :param file_path: the path to the apo spec file (not a file pointer)
    :param function_map: a dictionary of urls to functions for mapping (see docs)
    :return: django patterns for appending to the url_patterns
    """
    patterns = []
    try:
        parser = OpenApiParser.open(file_path)
        parser.load_all()

        for path, item in parser.path_items.items():
            # the path is 
            # item.pretty_path
            # item.summary
            epoint = Endpoint(item.pretty_path)
            print('>>>>>',item.endpoints.items())
            for verb, endpoint in item.endpoints.items():
                # this now is with the item.pretty_path the GET / POST etc
                # print(" -> %s \t: %s" % (verb, endpoint.summary))
                # print(endpoint.schema)
                my_action = Action()
                print(endpoint.responses)
                # look for the 200 (?) #FIXME what if 200 isn't default but others like no content
                if '200' in endpoint.responses:
                    # FIXME: don't hardcode application/json here!
                    my_action.schema = endpoint.responses['200'].content['application/json'].schema
                    examples = endpoint.responses['200'].content['application/json'].example
                    if len(examples) > 0:
                        for ex in examples:
                            print(ex.values())
                            my_action.example = ex
                            break; #FIXME: wtf?
                print("adding endpoint %s" % verb)


                epoint.add_action(verb.upper(), my_action)

                if '204' in endpoint.responses:
                    # FIXME: don't hardcode application/json here!
                    my_action.schema = endpoint.responses['204'].content['application/json'].schema
                    examples = endpoint.responses['204'].content['application/json'].example
                    if len(examples) > 0:
                        for ex in examples:
                            print(ex.values())
                            my_action.example = ex
                            break; #FIXME: wtf?
                print("adding endpoint %s" % verb)
                epoint.add_action(verb.upper(), my_action)

            # FIXME: the endpoint parse_regex should be used at this point
 
            if path.startswith("/"):
                path = path[1:]
            print("Adding %s " % path)
            print( "--> %s " % epoint.request_method_mapping)
            patterns.append(re_path("^%s$" % path, epoint.serve))

    except OpenApiLoaderError as error: 
        # FIXME: double check this.

        error_msg = "An error occurred processing '{}': {}".format(file_path, error)
        logger.error(error_msg)
        raise FatalException(error_msg)

    return patterns
