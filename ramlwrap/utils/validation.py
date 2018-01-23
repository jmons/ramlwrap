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

    def add_action(self, request_method, example=None, schema=None, target=None, query_parameter_checks=None):
        """Add an action mapping for the given request method type.
        :param request_method: http method type to map the action to.
        :param example: example to return if the endpoint is mocked.
        :param schema: schema to validate the incoming request against.
        :param target: target function that is returned to django to process the request.
        :param query_parameter_checks: rules to validate the query params against.
        :returns: returns nothing.
        """
        action = Action(example, schema, target, query_parameter_checks)
        self.request_method_mapping[request_method] = action

    @csrf_exempt
    def serve(self, request):
        """Serve the request to the current endpoint. The validation and response
        that is returned depends on the incoming request http method type.
        :param request: incoming http request that must be served correctly.
        :returns: returns the HttpResponse, content of which is created by the target function.
        """

        if request.method == "GET":
            response = _validate_get_api(request, self.request_method_mapping["GET"])
        elif request.method == "POST":
            response = _validate_post_api(request, self.request_method_mapping["POST"])
        else:
            response = 404   # TODO THis is wrong... MethodNotAllowed??

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
    expected_query_params = None

    def __init__(self, example, schema, target, query_parameter_checks):
        """
        Initialisation function that creates the Action to store the given params.
        :param example: example to be returned when mocking the function.
            This comes straight in from the raml parsing.
        :param schema: schema to validate the incoming request against.
        :param target: function that will process the incoming request.
        :param query_parameter_checks: rules that are used to validate the
            request's query parameters against.
        :returns: returns nothing.
        """
        self.example = example
        self.schema = schema
        self.target = target
        self.query_parameter_checks = query_parameter_checks


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

    # If expected params, check them. If not, pass.
    if checks:
        for param in checks:
            # If the expected param is in the query.
            if param in params:
                for check, rule in checks[param].__dict__.items():
                    if rule is not None:
                        error_message = 'QueryParam [%s] failed validation check [%s]:[%s]' % (param, check, rule)
                        if check == 'minLength':
                            if len(params.get(param)) < rule:
                                raise ValidationError(error_message)
                        elif check == 'maxLength':
                            if len(params.get(param)) > rule:
                                raise ValidationError(error_message)
            # Isn't in the query but it is required, throw a validation exception.
            elif checks[param].required is True:
                raise ValidationError('QueryParam [%s] failed validation check [Required]:[True]' % param)

    # TODO Add more checks here.
    return True


def _validate_get_api(request, action):
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
        response = action.target(request)
    else:
        response = action.example

    if isinstance(response, HttpResponse):
        return response
    else:
        return HttpResponse(json.dumps(response))


def _validate_post_api(request, action):
    """
    Validate POST APIs.
    :param request: incoming http request.
    :param action: action object containing data used to validate
        and serve the get request.
    :returns: returns the HttpResponse generated by the action target.
    """

    error_response = None
    if action.query_parameter_checks:
        # Following raises exception on fail or passes through.
        _validate_query_params(request.GET, action.query_parameter_checks)

    if action.schema:
        # If there is a problem with the json data, return a 400.
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
        data = json.loads(request.body.decode('utf-8'))

    if error_response:
        response = error_response
    else:
        request.validated_data = data
        if action.target:
            response = action.target(request)
        else:
            response = action.example

    if isinstance(response, HttpResponse):
        return response
    else:
        return HttpResponse(json.dumps(response))


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
