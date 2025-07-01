"""
Clickjacking Protection Middleware.

This module provides a middleware that implements protection against a
malicious site loading resources from your site in a hidden frame.
"""
from urllib.parse import urlparse

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from settings import CORS_ALLOWED_ORIGINS


class XFrameOptionsMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Don't set it if it's already in the response
        if response.get('X-Frame-Options') is not None:
            return response

        # Don't set it if they used @xframe_options_exempt
        if getattr(response, 'xframe_options_exempt', False):
            return response
        parsed = None
        if 'HTTP_REFERER' in request.META:
            parsed = urlparse(request.META['HTTP_REFERER'])
        # print(parsed)
        if parsed:
            if not f'{parsed.scheme}://{parsed.netloc}' in CORS_ALLOWED_ORIGINS:
                response['X-Frame-Options'] = self.get_xframe_options_value(request, response)
            else:
                response['X-Frame-Options'] = 'ALLOWALL'
        else:
            response['X-Frame-Options'] = self.get_xframe_options_value(request, response)
        return response

    def get_xframe_options_value(self, request, response):
        return getattr(settings, 'X_FRAME_OPTIONS', 'SAMEORIGIN').upper()
