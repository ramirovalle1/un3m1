#!/usr/bin/env python
import os
import sys
import openpyxl
# import urllib2

# Full path and name to your csv file
import unicodedata
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record

import xlrd
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
from django.http import HttpResponse
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
from setuptools.windows_support import hide_file
from urllib3 import request
from docx import Document

from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, PROFESORES_GROUP_ID, \
    RESPONSABLE_BIENES_ID, ALUMNOS_GROUP_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA, \
    CLAVE_USUARIO_CEDULA, CHEQUEAR_CONFLICTO_HORARIO

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sagest.models import *


# arregla kardex ay que poner al comienzo un id menor para que funcione
# producto = Producto.objects.get(pk=104)
# idanterior = 18674
# idnormal = 18810
# arregloid = KardexInventario.objects.values_list('id', flat=True).filter(producto=producto, id__gte=idanterior, status=True).order_by('id')
# i = 0
# for k in KardexInventario.objects.filter(producto=producto, id__gte=idnormal, status=True).order_by('id'):
#     print (k.id)
#     saldoanterior = KardexInventario.objects.get(pk=arregloid[i]).saldofinalvalor
#     cantidadanterior = KardexInventario.objects.get(pk=arregloid[i]).saldofinalcantidad
#     print (saldoanterior)
#     k.saldoinicialvalor = saldoanterior
#     k.saldoinicialcantidad = cantidadanterior
#     if k.tipomovimiento==2:
#         k.saldofinalvalor = saldoanterior - k.valor
#         k.saldofinalcantidad = cantidadanterior - k.cantidad
#     else:
#         k.saldofinalvalor = saldoanterior + k.valor
#         k.saldofinalcantidad = cantidadanterior + k.cantidad
#     k.save()
#     i += 1
# kardex = KardexInventario.objects.filter(producto=producto, status=True).order_by('-id')[0]
# valorproducto = kardex.saldofinalvalor
# cantidadproducto = kardex.saldofinalcantidad
# costoproducto = kardex.costo
# InventarioReal.objects.filter(producto=producto, status=True).update(valor=valorproducto, cantidad=cantidadproducto, costo=costoproducto)


producto = Producto.objects.get(pk=104)
idanterior = 18674
for k in KardexInventario.objects.filter(producto=producto, id__gte=idanterior, status=True, anulado=False).order_by('id'):
    print (k.id)
    ultimo = KardexInventario.objects.filter(producto=producto, id__lt=k.id, anulado=False).order_by('-id')[0]
    if ultimo:
        if k.compra:
            costo = null_to_decimal(k.costo, 16)
        else:
            costo = null_to_decimal(ultimo.saldofinalvalor / ultimo.saldofinalcantidad, 16)
        k.valor = null_to_decimal(float(k.cantidad) * costo, 16)
        saldoanterior = null_to_decimal(ultimo.saldofinalvalor, 16)
        cantidadanterior = ultimo.saldofinalcantidad
        print (saldoanterior)
        k.saldoinicialvalor = saldoanterior
        k.saldoinicialcantidad = cantidadanterior
        if k.tipomovimiento==2:
            k.saldofinalvalor = saldoanterior - k.valor
            k.saldofinalcantidad = cantidadanterior - k.cantidad
        else:
            k.saldofinalvalor = saldoanterior + k.valor
            k.saldofinalcantidad = cantidadanterior + k.cantidad
        k.save()
kardex = KardexInventario.objects.filter(producto=producto, status=True, anulado=False).order_by('-id')[0]
valorproducto = kardex.saldofinalvalor
cantidadproducto = kardex.saldofinalcantidad
costoproducto = kardex.costo
InventarioReal.objects.filter(producto=producto, status=True).update(valor=valorproducto, cantidad=cantidadproducto, costo=costoproducto)
