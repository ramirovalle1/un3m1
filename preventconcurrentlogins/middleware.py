from django.contrib.sessions.models import Session
from django.conf import settings
from django import VERSION as DJANGO_VERSION
from django.utils import deprecation
from importlib import import_module

from preventconcurrentlogins.models import Visitor

engine = import_module(settings.SESSION_ENGINE)


def is_authenticated(user):
    """
    Check if user is authenticated, consider backwards compatibility
    """
    if DJANGO_VERSION >= (1, 10, 0):
        return user.is_authenticated
    else:
        return user.is_authenticated()


class PreventConcurrentLoginsMiddlewareUnemi(deprecation.MiddlewareMixin if DJANGO_VERSION >= (1, 10, 0) else object):
    """
    Django middleware that prevents multiple concurrent logins..
    Adapted from http://stackoverflow.com/a/1814797 and https://gist.github.com/peterdemin/5829440
    """

    def process_request(self, request):
        if is_authenticated(request.user):
            if not request.user.is_superuser:
                key_from_cookie = request.session.session_key
                sistema = request.session['tiposistema'] if 'tiposistema' in request.session else ''
                if Visitor.objects.db_manager("sga_select").values("id").filter(user=request.user, sistema=sistema).exists():
                    visitor = Visitor.objects.get(user=request.user, sistema=sistema)
                    session_key_in_visitor_db = visitor.session_key
                    tiposistema = visitor.sistema
                    if session_key_in_visitor_db != key_from_cookie and tiposistema != sistema:
                        engine.SessionStore(session_key_in_visitor_db).delete()
                        visitor.session_key = key_from_cookie
                        visitor.save()
                else:
                    Visitor.objects.create(
                        user=request.user,
                        session_key=key_from_cookie,
                        sistema=request.session['tiposistema'] if 'tiposistema' in request.session else ''
                    )
