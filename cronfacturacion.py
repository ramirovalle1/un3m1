#!/usr/bin/env python

import os
import sys


SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()


from datetime import datetime
from django.db import transaction
from django.db.models import Q
# Full path and name to your csv file
from sagest.rec_finanzas import crear_representacion_xml_factura, firmar_comprobante_factura, envio_comprobante_sri_factura, \
    autorizacion_comprobante_factura, envio_comprobante_cliente_factura
from sagest.rec_notacredito import  crear_representacion_xml_notacredito, firmar_comprobante_notacredito, envio_comprobante_sri_notacredito, autorizacion_comprobante_notacredito, envio_comprobante_cliente_notacredito
from sagest.models import Factura, NotaCredito
from sga.models import miinstitucion
from cronrelacionados import enviar_mensaje_bot_telegram


@transaction.atomic()
def facturacion_emisionfactura(id):
    try:
        factura = Factura.objects.get(pk=int(id))
        print(factura.numerocompleto)
        if not factura.xmlgenerado:
            print("Generando XML")
            crear_representacion_xml_factura(factura.id, proceso_siguiente=True)
        elif not factura.firmada:
            print("Generando FIRMA")
            firmar_comprobante_factura(factura.id)
        elif not factura.enviadasri:
            print("Generando ENVIANDO AL SRI")
            envio_comprobante_sri_factura(factura.id)
        elif not factura.autorizada:
            print("Generando AUTORIZANDO")
            autorizacion_comprobante_factura(factura.id)
        elif not factura.enviadacliente:
            print("Generando ENVIANDO CORREO")
            envio_comprobante_cliente_factura(factura.id)
    except Exception as ex:
        print(ex)
        pass


@transaction.atomic()
def facturacion_emisionnotacredito(id):
    nota = NotaCredito.objects.get(pk=int(id))
    print(nota.numerocompleto)
    if not nota.xmlgenerado:
        crear_representacion_xml_notacredito(nota.id, proceso_siguiente=True)
    elif not nota.firmada:
        firmar_comprobante_notacredito(nota.id)
    elif not nota.enviadasri:
        envio_comprobante_sri_notacredito(nota.id, proceso_siguiente=True)
    elif not nota.autorizada:
        autorizacion_comprobante_notacredito(nota.id, proceso_siguiente=True)
    elif not nota.enviadacliente:
        envio_comprobante_cliente_notacredito(nota.id)


print("EMITIENDO COMPROBANTES ELECTRONICOS: " + datetime.now().__str__() + "\r")
facturas =Factura.objects.filter(Q(autorizada=False) | Q(enviadacliente=False), valida=True).distinct().values_list('id', flat=True).order_by('fecha', 'numerocompleto')
print(facturas.count())
institucion_ = miinstitucion()
try:
    if institucion_.proceso_facturacion:
        institucion_.proceso_facturacion = False
        institucion_.save()
        print('------INICIO PROCESO------')
        for factura in facturas:
            facturacion_emisionfactura(factura)
        for nota in NotaCredito.objects.filter(estado=1, valida=True).distinct().values_list('id', flat=True).order_by('fecha'):
            facturacion_emisionnotacredito(nota)
        institucion_.proceso_facturacion = True
        institucion_.save()
        print('------FIN PROCESO------')
    print("HECHO: " + datetime.now().__str__())
except Exception as ex:
    institucion_.proceso_facturacion = True
    institucion_.save()
    texto_notify = 'Error al notificar el rubro, {} error en la linea: {}'.format(str(ex), sys.exc_info()[-1].tb_lineno)
    enviar_mensaje_bot_telegram(texto_notify)