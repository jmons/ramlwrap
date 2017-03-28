from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

import json


def login_request(request):

    username = request.POST['username']
    password = request.POST['password']

    user = authenticate(username=username, password=password)

    if user is not None:
        login(request, user)
        return HttpResponse("ok")
    else:
        raise Exception("Bad login")
    
    
def logout_request(request):
    logout(request)


@login_required
def protected_view(request):
    ret_data = {
        "status": "ok",
        "logged_in_user": request.user.username
    }

    return ret_data
