from django.urls import re_path, path
from .tei.authentication import logintei_view
from .tei.ingresocampus import ingresocampustei_view


urlpatterns = [
    re_path('v1/tei/auth/', logintei_view, name='login_app'),
    re_path('v1/tei/ingresocampus/', ingresocampustei_view, name='ingresocampus_tei_view'),
]
