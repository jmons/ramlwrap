import json

from django.http import HttpResponse


def dynamic_api_one(request, dynamic_id):
    """
    Just an example api to check the dynamic part of the url is working correctly
    and is passed into the api function
    """

    return HttpResponse(json.dumps({"dynamicValue": dynamic_id}), content_type="application/json")


def dynamic_api_two(request, dynamic_id, dynamic_id_2):
    """
    Example api to check multiple dynamic values are passed through to the function correctly from a url
    """

    return HttpResponse(json.dumps({"dynamicValueOne": dynamic_id, "dynamicValueTwo": dynamic_id_2}), content_type="application/json")


def regular_api(request):
    """
    Example api for non dynamic urls
    """

    return HttpResponse(json.dumps({"message": "woohoo"}), content_type="application/json")

def dynamic_api_one_type_b(request, dynamic_id):
    """
    Just an example api to check the dynamic part of the url is working correctly
    and is passed into the api function
    """

    return {"dynamicValue": dynamic_id}

def regular_api_type_b(request):
    """
    Example api for non dynamic urls
    """

    return {"message": "woohoo"}