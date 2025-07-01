from django.urls import re_path
from empresa import commonviews, representantes, ofertaslaborales

urlpatterns = [
    re_path(r'^loginempresa$', commonviews.login_user, name='loginempresa_view'),
    re_path(r'^empr_representantes$', representantes.view, name='empr_representantes_view'),
    re_path(r'^empr_ofertas$', ofertaslaborales.view, name='empr_ofertas_view'),
    re_path(r'^pass$', commonviews.passwd, name='passwd'),
]