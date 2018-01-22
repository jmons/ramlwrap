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

def _is_valid_query(params, expected_params):
    """Function to validate get request params."""

    # If expected params, check them. If not, pass.
    if expected_params:
        for param in expected_params:
            # If the expected param is in the query.
            if param in params:
                for check, rule in expected_params[param].__dict__.items():
                    if rule is not None:
                        error_message = 'QueryParam [%s] failed validation check [%s]:[%s]' % (param, check, rule)
                        if check == 'minLength':
                            if len(params.get(param)) < rule:
                                raise ValidationError(error_message)
                        elif check == 'maxLength':
                            if len(params.get(param)) > rule:
                                raise ValidationError(error_message)
            # Isn't in the query but it is required, throw a validation exception.
            elif expected_params[param].required is True:
                raise ValidationError('QueryParam [%s] failed validation check [Required]:[True]' % param)

    # TODO Add more checks here.
    return True


def _validate_get_api(request, expected_params, target):
    """Validate GET APIs."""

    if _is_valid_query(request.GET, expected_params):
        response = target(request)

        if isinstance(response, HttpResponse):
            return response
        else:
            return HttpResponse(json.dumps(response))

def _validate_post_api(request, schema, expected_params, target):
    """Validate POST APIs."""

    error_response = None
    if expected_params:
        _is_valid_query(request.GET, expected_params)   # Either passes through or raises an exception.

    if schema:
        # If there is a problem with the json data, return a 400.
        try:
            data = json.loads(request.body.decode('utf-8'))
            validate(data, schema) 
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
        response = target(request)

    if isinstance(response, HttpResponse):
        return response
    else:
        return HttpResponse(json.dumps(response))

def _example_api(request, example, schema=None):
    """Example API that returns the example from schema."""

    response = None
    if schema:
        # If there is a problem with the json data, return a 400.
        try:
            data = json.loads(request.body.decode('utf-8'))
            validate(data, schema)
        except Exception as e:
            if hasattr(settings, 'RAMLWRAP_VALIDATION_ERROR_HANDLER') and settings.RAMLWRAP_VALIDATION_ERROR_HANDLER:
                response = _call_custom_handler(e)
            else:
                response = _validation_error_handler(e)

    if response:
        return response

    if not example:
        return None
    else:
        return example


class WrappedAPI():
    """
    Standardised Validated API which wraps all method type specific functions.
    Depending on the type of API the request is passed through
    to the correct functionality.
    """

    def __init__(self):
        """Initialisation function."""
        self.accepted_methods = []
        self.get_mapping = {}
        self.post_mapping = {}

    def add_method(self, method, kwargs, example=None):
        """
        Adds a new method to the current wrapped api. This means that
        the given method will now be supported by this api. For the given
        method the expected kwargs and their values are stored so that when
        the api is called by the dependent, the arguments can be pased in.
        :method: the http method to add to the wrapped api.
        :kwargs: the arguments that will be passed in to the request. These
            keys and values will be varying dependent upon the method.
        :example: the example data, if any.
        """
        if method == 'GET':
            self.accepted_methods.append('GET')
            self.get_mapping['kwargs'] = kwargs
            self.get_mapping['example'] = example
        elif method == 'POST':
            self.accepted_methods.append('POST')
            self.post_mapping['kwargs'] = kwargs
            self.post_mapping['example'] = example
        else:
            pass

    @csrf_exempt
    def validate(self, *args, **kwargs):
        """Wrapper validation api function."""

        request = args[0]

        if request.method not in self.accepted_methods:
            raise NotImplementedError

        if request.method == 'POST':
            response = _validate_post_api(request, **self.post_mapping['kwargs'])
        elif request.method == 'GET':
            response = _validate_get_api(request, **self.get_mapping['kwargs'])
        else:
            raise NotImplementedError

        if isinstance(response, HttpResponse):
            return response
        else:
            return HttpResponse(response)

    @csrf_exempt
    def mock(self, *args, **kwargs):
        """Mock API that is returned if there is no real implementation."""
        request = args[0]

        if request.method not in self.accepted_methods:
            raise NotImplementedError

        if request.method == 'POST':
            response = _example_api(
                request=request,
                schema=self.post_mapping['kwargs']['schema'],
                example=self.post_mapping['example']
            )
        elif request.method == 'GET':
            response = _example_api(
                request=request,
                example=self.get_mapping['example']
            )
        else:
            raise NotImplementedError

        if isinstance(response, HttpResponse):
            return response
        else:
            return HttpResponse(response)


def _validation_error_handler(e):
    """
    Handle validation errors.
    This can be overridden via the settings.
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
    Dynamically import and call the custom handler
    defined by the user in the django settings file.
    """

    handler_full_path = settings.RAMLWRAP_VALIDATION_ERROR_HANDLER
    handler_method = handler_full_path.split('.')[-1]
    handler_class_path = '.'.join(handler_full_path.split('.')[0:-1])

    handler = getattr(importlib.import_module(handler_class_path), handler_method)
    return handler(e)
