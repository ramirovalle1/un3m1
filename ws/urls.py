# chat/urls.py
from django.urls import re_path, path

from ws.views import index

urlpatterns = [
    re_path(r'^chat/index$', index.view, name='index'),
    re_path(r'^chat/(?P<room_name>[\w-]+)/$', index.room, name='room'),
]
