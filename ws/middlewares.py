import jwt, re
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken, TokenError

User = get_user_model()


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class WebSocketJWTAuthMiddleware:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict(scope['headers'])
        parsed_query_string = parse_qs(scope["query_string"])
        scope["user"] = AnonymousUser()
        if parsed_query_string:
            app = parsed_query_string.get(b"app", [None])[0].decode("utf-8")
            if app == 'sge':
                token = parsed_query_string.get(b"token", [None])[0].decode("utf-8")
                if token:
                    token = parsed_query_string.get(b"token")[0].decode("utf-8")
                    try:
                        access_token = AccessToken(token)
                        scope["user"] = await get_user(access_token.payload['user_id'])
                    except TokenError:
                        scope["user"] = AnonymousUser()
            elif app == 'uxplora':
                token = parsed_query_string.get(b"token", [None])[0].decode("utf-8")
                if token:
                    if token == '073f04a72445c6cc3d3a379456c441ea':
                        try:
                            # access_token = AccessToken(token)
                            scope["user"] = await get_user(1)
                        except TokenError:
                            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)


TokenAuthMiddlewareStack = lambda inner: WebSocketJWTAuthMiddleware(AuthMiddlewareStack(inner))


def _str_to_dict(str):
    return {k: v.strip('"') for k, v in re.findall(r'(\S+)=(".*?"|\S+)', str)}
