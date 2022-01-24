"""Validation functionality."""
import importlib
import inspect
import json
import logging
import sys

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from django.conf import settings
from django.http.request import HttpRequest
from django.http.response import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from . exceptions import FatalException

logger = logging.getLogger(__name__)


class ContentType:
    """Represents http content types."""
    JSON = 'application/json'

    def __init__(self):
        """Initialisation function."""
        pass


class Endpoint:
    """
    Endpoint that represents one url in the service. Each endpoint
    contains Actions which represent a request method that the endpoint
    supports.
    """

    url = None
    request_method_mapping = None

    def __init__(self, url):
        """Initialisation function."""
        self.url = url
        self.request_method_mapping = {}

    def parse_regex(self, regex_dict):
        """
        Replace dynamic template in url with corresponding regex for a dynamic value
        :param regex_dict: dictionary of dynamic id names to regex
        e.g. {'dynamic_id': '(?P<dynamic_id>[a-zA-Z]+)'}
        """

        for regex_key, regex in regex_dict.items():
            string_to_replace = "{%s}" % regex_key
            self.url = self.url.replace(string_to_replace, regex)

    def add_action(self, request_method, action):
        """Add an action mapping for the given request method type.
        :param request_method: http method type to map the action to.
        :param action: the action to map to the request.
        :returns: returns nothing.
        """

        self.request_method_mapping[request_method] = action

    @csrf_exempt
    def serve(self, request, **dynamic_values):
        """Serve the request to the current endpoint. The validation and response
        that is returned depends on the incoming request http method type.
        :param request: incoming http request that must be served correctly.
        :param dynamic_values: kwargs of dynamic id names against actual value to substitute into url
         e.g. {'dynamic_id': 'aBc'}
        :returns: returns the HttpResponse, content of which is created by the target function.
        """

        if request.method in self.request_method_mapping:
            action = self.request_method_mapping[request.method]
            response = _validate_api(request, action, dynamic_values)
        else:
            response = HttpResponseNotAllowed(self.request_method_mapping.keys())

        if isinstance(response, HttpResponse):
            return response
        else:
            return HttpResponse(response)


class Action:
    """
    Maps out the api definition associated with the parent Endpoint.
    One of these will be created per http request method type.
    """

    example = None
    schema = None
    target = None
    query_parameter_checks = None
    resp_content_type = None
    requ_content_type = None
    regex = None

    def __init__(self):
        """Initialisation function."""
        pass


def _validate_query_params(params, checks):
    """
    Function to validate HTTP GET request params. If there are checks to be
    performed then they will be; these will be items such as length and type
    checks defined in the definition file.
    :param params: incoming request parameters.
    :param checks: dict of param to rule to validate with.
    :raises ValidationError: raised when any query parameter fails any
        of its checks defined in the checks param.
    :returns: true if validated, otherwise raises an exception when fails.
    """

    # If validation checks, check the params. If not, pass.
    if checks:
        for param in checks:
            # If the expected param is in the query.
            if param in params:
                for check, rule in checks[param].items():
                    if rule is not None:
                        error_message = 'QueryParam [%s] failed validation check [%s]:[%s]' % (param, check, rule)
                        if check == 'minLength':
                            if len(params.get(param)) < rule:
                                raise ValidationError(error_message)
                        elif check == 'maxLength':
                            if len(params.get(param)) > rule:
                                raise ValidationError(error_message)
                        elif check == 'type':
                            if rule == 'number':
                                try:
                                    float(params.get(param))
                                except ValueError:
                                    raise ValidationError(error_message)

            # If the require param isn't in the query.
            elif checks[param]['required'] is True:
                raise ValidationError('QueryParam [%s] failed validation check [Required]:[True]' % param)

    return True


def _generate_example(action):
    """
    This is used by both GET and POST when returning an example 
    """
    # The original method of generating straight from the example is bad
    # because v2 parser now has an object, which also allows us to do the
    # headers correctly

    ret_data = action.example
    # FIXME: not sure about this content thing
    if action.resp_content_type == "application/json":
        ret_data = json.dumps(action.example)

    return HttpResponse(ret_data, content_type=action.resp_content_type)


def _validate_api(request, action, dynamic_values=None):
    """
    Validate APIs content.
    :param request: incoming http request.
    :param action: action object containing data used to validate
        and serve the request.
    :param dynamic_values: dict of dynamic id names against actual values to substitute into url
     e.g. {'dynamic_id': 'aBc'}
    :returns: returns the HttpResponse generated by the action target.
    """

    # FIXME validate query params in later stages
    if action.query_parameter_checks:
        # Following raises exception on fail or passes through.
        _validate_query_params(request.GET, action.query_parameter_checks)

    validate_error_response = None

    if request.body:
        validate_error_response = _validate_body(request, action)

    if validate_error_response:
        return validate_error_response
    else:
        # all validated fine
        if action.target:
            answer = action.target
            if dynamic_values:
                # If there was a dynamic value, pass it through
                return action.target(request, **dynamic_values)
            else:
                if answer is type(HttpRequest):
                    return answer
                else:
                    return HttpResponse(json.dumps(answer), content_type="application/json")
        else:
            return _generate_example(action)


def _validate_body(request, action):
    error_response = None

    if action.requ_content_type == ContentType.JSON:
        if action.schema:
            # Validate agains the schema
            try:
                data = json.loads(request.body.decode('utf-8'))
                # against json schema its fine, but openapi parser can parse it to json?
                validate(data, action.schema)
            except Exception as e:
                error_response = _validation_error_handler(e)
        else:
            # Otherwise just load it (no validation as no schema).
            data = json.loads(request.body.decode('utf-8'))
    else:
        # The content isn't JSON
        try:
            # Decode it as it is
            data = request.body.decode('utf-8')
        except UnicodeDecodeError as e:
            # Just send the body if it cannot be decoded
            data = request.body

    if not error_response:
        request.validated_data = data

    return error_response


def _validation_error_handler(e):
    """
    Default validation handler for when a ValidationError occurs.
    This behaviour can be overriden in the settings file.
    :param e: exception raised that must be handled.
    :returns: HttpResponse with status depending on the error.
        ValidationError will return a 422 with json info on the cause.
        Otherwise a FatalException is raised.
    """

    if isinstance(e, ValidationError):
        message = 'Validation failed. {}'.format(e.message)
        error_response = {
            'message': message,
            'code': e.validator
        }
        logger.info(message)
        error_resp = JsonResponse(error_response, status=422)
    else:
        raise FatalException('Malformed JSON in the request.', 400)

    return error_resp


def _call_custom_handler(e, request, action):
    """
    Dynamically import and call the custom validation error handler
    defined by the user in the django settings file.
    :param e: exception raised that must be handled.
    :param request: incoming http request that must be served correctly.
    :param action: action object containing data used to validate and serve the request.
    :returns: response returned from the custom handler, given the exception.
    """

    handler_full_path = settings.RAMLWRAP_VALIDATION_ERROR_HANDLER
    handler_method = handler_full_path.split('.')[-1]
    handler_class_path = '.'.join(handler_full_path.split('.')[0:-1])

    handler = getattr(importlib.import_module(handler_class_path), handler_method)

    if _num_arguments_to_pass(handler) == 3:
        return handler(e, request, action)
    else:
        # Handle old versions that still only accept the exception
        return handler(e)


def _num_arguments_to_pass(handler):
    if sys.version_info[0] < 3:
        # Python 2
        args = inspect.getargspec(handler).args
        return len(args)
    else:
        # Python 3
        signature = inspect.signature(handler)
        return len(signature.parameters)
