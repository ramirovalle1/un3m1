from django.urls import re_path, include
from api.views.wu.conciliacion import ConciliacionAPIView
from settings import DEBUG


urlpatterns = [
    re_path(r'^conciliacion$', ConciliacionAPIView.as_view(), name='api_view_wu_conciliacion'),
]
