"""Validation functionality."""
import importlib
import json
import logging

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from django.conf import settings
from django.http.response import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from . exceptions import FatalException

logger = logging.getLogger(__name__)


class ContentType:
    """Represents http content types."""
    JSON = 'application/json'


class Endpoint():
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

    def add_action(self, request_method, action):
        """Add an action mapping for the given request method type.
        :param request_method: http method type to map the action to.
        :param action: the action to map to the request.
        :returns: returns nothing.
        """

        if action.dynamic_value:
            for regex_key, regex in action.dynamic_value.items():
                string_to_replace = "{%s}" % regex_key
                self.url = self.url.replace(string_to_replace, regex)

        self.request_method_mapping[request_method] = action

    @csrf_exempt
    def serve(self, request, **dynamic_values):
        """Serve the request to the current endpoint. The validation and response
        that is returned depends on the incoming request http method type.
        :param request: incoming http request that must be served correctly.
        :returns: returns the HttpResponse, content of which is created by the target function.
        """

        try:
            if request.method == "GET":
                response = _validate_get_api(request, self.request_method_mapping["GET"], dynamic_values)
            elif request.method == "POST":
                response = _validate_post_api(request, self.request_method_mapping["POST"], dynamic_values)
            elif request.method == "PUT":
                response = _validate_put_api(request, self.request_method_mapping["PUT"], dynamic_values)
            else:
                response = HttpResponse(status=401)
        except KeyError:
            response = HttpResponse(status=401)

        if isinstance(response, HttpResponse):
            return response
        else:
            return HttpResponse(response)


class Action():
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
    dynamic_value = None

    def __init__(self):
        """Initialisation funciton."""
        pass


def _validate_query_params(params, checks):
    """
    Function to validate get request params. If there are checks to be
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


def _generate_example(request, action):
    """
    This is used by both GET and POST when returning an example 
    """
    # The original method of generating straight from the xample is bad 
    # because v2 parser now has an object, which also allows us to do the 
    # headers correctly
    
    ret_data = action.example
    # FIXME: not sure about this content thing
    if action.resp_content_type == "application/json":
        ret_data = json.dumps(action.example)

    return HttpResponse(ret_data, content_type=action.resp_content_type)


def _validate_get_api(request, action, dynamic_values=None):
    """
    Validate Get APIs.
    :param request: incoming http request.
    :param action: action object containing data used to validate
        and serve the get request.
    :returns: returns the HttpResponse generated by the action target.
    """

    if action.query_parameter_checks:
        # Following raises exception on fail or passes through.
        _validate_query_params(request.GET, action.query_parameter_checks)

    if action.target:
        # If there was a dynamic value, pass it through
        if dynamic_values:
            response = action.target(request, **dynamic_values)
        else:
            response = action.target(request)
    else:
        response = _generate_example(request, action)

    if not isinstance(response, HttpResponse):
        # As we weren't given a HttpResponse, we need to create one
        # and handle the data correctly.
        if action.resp_content_type == ContentType.JSON:
            if dynamic_values:
                response = HttpResponse(json.dumps(response), **dynamic_values)
            else:
                response = HttpResponse(json.dumps(response))

    return response


def _validate_post_api(request, action, dynamic_values=None):
    """
    Validate POST APIs.
    :param request: incoming http request.
    :param action: action object containing data used to validate
        and serve the post request.
    :returns: returns the HttpResponse generated by the action target.
    """

    if action.query_parameter_checks:
        # Following raises exception on fail or passes through.
        _validate_query_params(request.GET, action.query_parameter_checks)

    return _common_validation(request, action, dynamic_values)


def _validate_put_api(request, action, dynamic_values=None):
    """
    Validate PUT APIs.
    :param request: incoming http request.
    :param action: action object containing data used to validate
        and serve the put request.
    :returns: returns the HttpResponse generated by the action target.
    """

    if action.query_parameter_checks:
        # Following raises exception on fail or passes through.
        _validate_query_params(request.PUT, action.query_parameter_checks)

    return _common_validation(request, action, dynamic_values)


def _common_validation(request, action, dynamic_values=None):
    """
    Function for common logic between post and put validation
    """

    error_response = None

    if action.requ_content_type == ContentType.JSON:
        # If the expected request body is JSON, we need to load it.
        if action.schema:
            # If there is any schema, we'll validate it.
            try:
                data = json.loads(request.body.decode('utf-8'))
                validate(data, action.schema)
            except Exception as e:
                # Check the value is in settings, and that it is not None
                if hasattr(settings, 'RAMLWRAP_VALIDATION_ERROR_HANDLER') and settings.RAMLWRAP_VALIDATION_ERROR_HANDLER:
                    error_response = _call_custom_handler(e)
                else:
                    error_response = _validation_error_handler(e)
        else:
            # Otherwise just load it (no validation as no schema).
            data = json.loads(request.body.decode('utf-8'))
    else:
        # The content isn't JSON to just decode it as is.
        data = request.body.decode('utf-8')

    if error_response:
        response = error_response
    else:
        request.validated_data = data

        if action.target:
            if dynamic_values:
                # If there was a dynamic value, pass it through
                response = action.target(request, **dynamic_values)
            else:
                response = action.target(request)
        else:
            response = _generate_example(request, action)

    if not isinstance(response, HttpResponse):
        # As we weren't given a HttpResponse, we need to create one
        # and handle the data correctly.
        if action.resp_content_type == ContentType.JSON:
            if dynamic_values:
                response = HttpResponse(json.dumps(response), **dynamic_values)
            else:
                response = HttpResponse(json.dumps(response))

    return response


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
        error_resp = HttpResponse(error_response, status=422)
    else:
        raise FatalException('Malformed JSON in the request.', 400)

    return error_resp


def _call_custom_handler(e):
    """
    Dynamically import and call the custom validation error handler
    defined by the user in the django settings file.
    :param e: exception raised that must be handled.
    :returns: response returned from the custom handler, given the exception.
    """

    handler_full_path = settings.RAMLWRAP_VALIDATION_ERROR_HANDLER
    handler_method = handler_full_path.split('.')[-1]
    handler_class_path = '.'.join(handler_full_path.split('.')[0:-1])

    handler = getattr(importlib.import_module(handler_class_path), handler_method)
    return handler(e)
