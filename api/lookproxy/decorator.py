import base64

from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import auth
from django.contrib.auth import authenticate, login


def lookproxy_auth_required(view):
    def _decorator(request, *args, **kwargs):
        try:
            merchantId = request.merchantId
            request = request.request
            if 'HTTP_AUTHORIZATION' in request.META:
                auth = request.META['HTTP_AUTHORIZATION']
                if auth == merchantId:
                    return view(request, *args, **kwargs)
            response = HttpResponse()
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic'
            return response
        except Exception as ex:
            response = HttpResponse()
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic'
            return response
    return _decorator