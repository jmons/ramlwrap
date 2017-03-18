import json
import logging

from jsonschema import validate
from jsonschema.exceptions import ValidationError

from django.views.decorators.csrf import csrf_exempt
from django.http.response import HttpResponse

from . exceptions import FatalException

logger = logging.getLogger(__name__)

@csrf_exempt
def ExampleAPI(request, schema, example):

    return HttpResponse(_example_api(request, schema, example))


def _example_api(request, schema, example):

    if schema:
        data = json.loads(request.body.decode("utf-8"))
        validate(data, schema)

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

    if expected_params:
        _is_valid_query(request.GET, expected_params)   # Either passes through or raises an exception.

    if schema:
        # If there is a problem with the json data, return a 400.
        try:
            data = json.loads(request.body.decode("utf-8"))
        except Exception as e:
            raise FatalException("Malformed JSON in the request.", 400)

        # Else if there is a problem with the  json schema validation, return a 422 and the reason.
        try:
            validate(data, schema)   # this will throw an exception if it doesn't validate.
        except ValidationError as e:
            message = "Validation failed. {}".format(e.message)
            error_response = {
                "message": message,
                "code": e.validator
            }
            logger.info(message)
            return HttpResponse(error_response, status=422)
    else:
        data = json.loads(request.body.decode('utf-8'))

    # Add validated data to request
    request.validated_data = data

    response = target(request)

    if isinstance(response, HttpResponse):
        return response
    else:
        return HttpResponse(json.dumps(response))
