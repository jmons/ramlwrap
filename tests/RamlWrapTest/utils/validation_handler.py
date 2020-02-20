"""
Custom validation handler for returning unqiue
and customised validation responses.
"""

from django.http.response import HttpResponse


def custom_validation_response(e):
    """
    Custom validation handler to override the default
    and return a HttpResponse I'm a teapot code.
    """

    return HttpResponse(status=418)


def custom_validation_exception(e):
    """
    Custom validation handler to override the default
    and raise an exception.
    """

    raise NotImplementedError(e)


def custom_validation_with_request_action(e, request, action):
    """
    Custom validation handler to override the default
    and return a HttpResponse I'm a teapot code.
    """

    return {
        "path": request.path,
        "content_type": action.requ_content_type
    }
