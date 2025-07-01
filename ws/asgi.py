import os
from channels.security.websocket import OriginValidator
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django_asgi_app = get_asgi_application()

from settings import CORS_ALLOWED_ORIGINS
from ws import routing
from ws.middlewares import TokenAuthMiddlewareStack

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": OriginValidator(
        TokenAuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns
                )
            ),
        # URLRouter(routing.websocket_urlpatterns),
        CORS_ALLOWED_ORIGINS,
    ),
})
