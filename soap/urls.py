from django.urls import re_path
from django.views.decorators.csrf import csrf_exempt
from spyne.server.django import DjangoView
from spyne.protocol.soap import Soap11, Soap12
from soap.service.views import AvayaService
from soap.service.banco_pacifico import ServiceCobro, banco_pacifico_cobro
from soap.service.wester_union import ServiceCobro, wester_union_cobro
from settings import DEBUG
"""https://github.com/luisfernandobarrera/test_djangows"""

urlpatterns = [
    # re_path(r'^soap/bp/cobro$', csrf_exempt(DjangoView.as_view(services=[ServiceCobro], tns='web.bancopacifico.service', in_protocol=Soap12(validator="lxml"), out_protocol=Soap12())), name='soap_banco_pacifico_view'),
    re_path(r'^soap/bp/cobro$', csrf_exempt(banco_pacifico_cobro), name='soap_banco_pacifico_view'),
    re_path(r'^soap/wu/cobro$', csrf_exempt(wester_union_cobro), name='soap_wester_union_view'),
    re_path(r'^avaya/$', csrf_exempt(DjangoView.as_view(services=[AvayaService], tns='mango.avaya.service', in_protocol=Soap11(), out_protocol=Soap11()))),
]
