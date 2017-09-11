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


@csrf_exempt
def ExampleAPI(request, schema, example):

    response = _example_api(request, schema, example)
    if isinstance(response, HttpResponse):
        return response
    else:
        return HttpResponse(response)


def _example_api(request, schema, example):

    response = None
    if schema:
        # If there is a problem with the json data, return a 400.
        try:
            data = json.loads(request.body.decode("utf-8"))
            validate(data, schema)
        except Exception as e:
            if hasattr(settings, 'RAMLWRAP_VALIDATION_ERROR_HANDLER'):
                response = _call_custom_handler(e)
            else:
                response = _validation_error_handler(e)

    if response:
        return response

    if not example:
        return None
    else:
        return example


def _is_valid_query(params, expected_params):
    """
    Function to validate get request params.
    """

    # If expected params, check them. If not, pass.
    if expected_params:
        for param in expected_params:
            # If the expected param is in the query.
            if param in params:
                for check, rule in expected_params[param].__dict__.items():
                    if rule is not None:
                        error_message = "QueryParam [%s] failed validation check [%s]:[%s]" % (param, check, rule)
                        if check == "minLength":
                            if len(params.get(param)) < rule:
                                raise ValidationError(error_message)
                        elif check == "maxLength":
                            if len(params.get(param)) > rule:
                                raise ValidationError(error_message)
            # Isn't in the query but it is required, throw a validation exception.
            elif expected_params[param].required is True:
                raise ValidationError("QueryParam [%s] failed validation check [Required]:[True]" % param)

    # TODO Add more checks here.
    return True


@csrf_exempt
def ValidatedGETAPI(request, expected_params, target):
    """
    Validate GET APIs.
    """

    if _is_valid_query(request.GET, expected_params):
        response = target(request)

        if isinstance(response, HttpResponse):
            return response
        else:
            return HttpResponse(json.dumps(response))


@csrf_exempt
def ValidatedPOSTAPI(request, schema, expected_params, target):
    """
    Validate POST APIs.
    """

    error_response = None
    if expected_params:
        _is_valid_query(request.GET, expected_params)   # Either passes through or raises an exception.

    if schema:
        # If there is a problem with the json data, return a 400.
        try:
            data = json.loads(request.body.decode("utf-8"))
            validate(data, schema) 
        except Exception as e:
            if hasattr(settings, 'RAMLWRAP_VALIDATION_ERROR_HANDLER'):
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


def _validation_error_handler(e):
    """
    Handle validation errors.
    This can be overridden via the settings.
    """

    if isinstance(e, ValidationError):
        message = "Validation failed. {}".format(e.message)
        error_response = {
            "message": message,
            "code": e.validator
        }
        logger.info(message)
        error_resp = HttpResponse(error_response, status=422)
    else:
        raise FatalException("Malformed JSON in the request.", 400)

    return error_resp


def _call_custom_handler(e):
    """
    Dynamically import and call the custom handler
    defined by the user in the django settings file.
    """

    handler_full_path = settings.RAMLWRAP_VALIDATION_ERROR_HANDLER
    handler_method = handler_full_path.split(".")[-1]
    handler_class_path = ".".join(handler_full_path.split(".")[0:-1])

    handler = getattr(importlib.import_module(handler_class_path), handler_method)
    return handler(e)
