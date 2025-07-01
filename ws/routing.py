# chat/routing.py
from django.urls import re_path

from ws.consumers.chat import ChatConsumer
from ws.consumers.client import ClientConsumer
from ws.consumers.horario import HorarioConsumer
from ws.consumers.uxplora import UxploraConsumer

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>\w+)/$', ChatConsumer.as_asgi()),
    re_path(r'ws/client', ClientConsumer.as_asgi()),
    re_path(r'ws/room/(?P<key_room>\d+)$', HorarioConsumer.as_asgi()),
    re_path(r'ws/uxplora', UxploraConsumer.as_asgi()),
]
