from urllib.request import urlopen
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, SESSION_KEY, _get_user_session_key, HASH_SESSION_KEY, _get_backends, BACKEND_SESSION_KEY, user_logged_in
from django.middleware.csrf import rotate_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from social_core.actions import do_complete
from social_core.backends.google import GoogleOAuth2
import requests
import mimetypes
from social_core.exceptions import AuthAlreadyAssociated
# from core.funciones import generar_nombre
from social_django.utils import psa
from social_django.views import _do_login
from settings import MEDIA_ROOT
import os
from django.utils.crypto import constant_time_compare
from sga.funciones import generar_nombre


def social_user(backend, uid, user=None, *args, **kwargs):
    provider = backend.name
    social = backend.strategy.storage.user.get_social_auth(provider, uid)
    if social:
        if user and social.user != user:
            msg = 'This account is already in use.'
            raise AuthAlreadyAssociated(backend, msg)
        elif not user:
            user = social.user
    return {'social': social,
            'user': user,
            'is_new': user is None,
            'new_association': social is None}


def associate_user(backend, uid, user=None, social=None, *args, **kwargs):
    if user and not social:
        try:
            social = backend.strategy.storage.user.create_social_auth(
                user, uid, backend.name
            )
        except Exception as err:
            if not backend.strategy.storage.is_integrity_error(err):
                raise
            # Protect for possible race condition, those bastard with FTL
            # clicking capabilities, check issue #131:
            #   https://github.com/omab/django-social-auth/issues/131
            result = social_user(backend, uid, user, *args, **kwargs)
            # Check if matching social auth really exists. In case it does
            # not, the integrity error probably had different cause than
            # existing entry and should not be hidden.
            if not result['social']:
                raise
            return result
        else:
            return {'social': social,
                    'user': social.user,
                    'new_association': True}


USER_FIELDS = ['username', 'email']


def create_user(strategy, details, backend, user=None, *args, **kwargs):
    if user:
        return {'is_new': False}

    fields = dict((name, kwargs.get(name, details.get(name)))
                  for name in backend.setting('USER_FIELDS', USER_FIELDS))
    if not fields:
        return

    return {
        'is_new': True,
        'user': strategy.create_user(**fields)
    }


def loginchangeuser(request, user, backend=None):
    """
    FUNCION COPIA DE login() PARA CAMBIO DE USUARIO Y PERSONALIZACIÓN
    """
    session_auth_hash = ""
    if user is None:
        user = request.user
    if hasattr(user, "get_session_auth_hash"):
        session_auth_hash = user.get_session_auth_hash()

    if SESSION_KEY in request.session:
        if _get_user_session_key(request) != user.pk or (
                session_auth_hash
                and not constant_time_compare(
            request.session.get(HASH_SESSION_KEY, ""), session_auth_hash
        )
        ):
            # To avoid reusing another user's session, create a new, empty
            # session if the existing session corresponds to a different
            # authenticated user.
            request.session.flush()
    else:
        request.session.cycle_key()

    try:
        backend = backend or user.backend
    except AttributeError:
        backends = _get_backends(return_tuples=True)
        if len(backends) == 1:
            _, backend = backends[0]
        else:
            raise ValueError(
                "You have multiple authentication backends configured and "
                "therefore must provide the `backend` argument or set the "
                "`backend` attribute on the user."
            )
    else:
        if not isinstance(backend, str):
            raise TypeError(
                "backend must be a dotted import path string (got %r)." % backend
            )

    request.session[SESSION_KEY] = user._meta.pk.value_to_string(user)
    request.session[BACKEND_SESSION_KEY] = backend
    request.session[HASH_SESSION_KEY] = session_auth_hash
    request.session['login_manual'] = True
    if hasattr(request, "user"):
        request.user = user
    rotate_token(request)
    user_logged_in.send(sender=user.__class__, request=request, user=user)
