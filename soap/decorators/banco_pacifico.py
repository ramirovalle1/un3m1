import base64
import datetime
import json
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import auth
from django.contrib.auth import authenticate, login


# The basic auth decorator
def login_or_basic_auth_required(view):
    def _decorator(request, *args, **kwargs):
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = base64.b64decode(auth[1]).decode('utf-8').split(':', 1)
                    user = authenticate(username=uname, password=passwd)
                    if user is not None:
                        if user.is_active:
                            request.user = user
                            return view(request, *args, **kwargs)
        response = HttpResponse()
        response.status_code = 401
        response['WWW-Authenticate'] = 'Basic'
        return response
    return _decorator