#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.db import transaction

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

fecha1 = '2016-01-01'
fecha = '2021-06-28'
print("**********COMIENZA*********")
tipo = ''
kardex = KardexInventario.objects.filter(fecha__lte=fecha,fecha__gte=fecha1).order_by('fecha')
for k in kardex:
    k.saldoinicialcantidad = round(k.saldoinicialcantidad,2)
    k.saldofinalcantidad = round(k.saldofinalcantidad,2)
    k.saldoinicialvalor = round(k.saldoinicialvalor,4)
    k.saldofinalvalor = round(k.saldofinalvalor,4)
    k.valor = round(k.valor,4)
    k.save()
    if round(k.saldoinicialcantidad,2)<=0:
        k.saldoinicialvalor=0

    if round(k.saldofinalcantidad,2)<=0:
        k.saldofinalvalor = 0
        k.save()

    if k.tipomovimiento==1:
        if k.compra:
            compra = DetalleIngresoProducto.objects.get(pk=k.compra.pk)
            compra.total = round(compra.total,4)
            compra.save()
            k.valor = compra.total
            k.saldofinalvalor = round((k.saldoinicialvalor+k.valor),4)
            k.save()
            tipo='suma'
    if k.tipomovimiento == 2:
        if k.salida:
            salida = DetalleSalidaProducto.objects.get(pk = k.salida.pk)
            salida.valor = round(salida.valor,4)
            salida.save()
            k.valor = salida.valor
            k.saldofinalvalor = round((k.saldoinicialvalor-k.valor),4)
            k.save()
            tipo='resta'

    print(tipo,k.saldoinicialvalor, k.valor,k.saldofinalvalor)
#

# ids = [3360,3342,3341,3336,3334,3271,3196,3195,2809,2784,2721,2651,1104,972,886,883,874,748,349,347]
# for i in ids:
#     print('**************',i,'***********')
#     kardex = KardexInventario.objects.filter(fecha__lte=fecha,fecha__gte=fecha1).order_by('fecha')
#     for k in kardex:
#         if k.tipomovimiento == 1:
#             if k.compra:
#                 if DetalleIngresoProducto.objects.filter(pk=k.compra.pk,producto_id=i):
#                     #compra = DetalleIngresoProducto.objects.get(pk=k.compra.pk,producto_id=i)
#                     tipo='suma'
#                     print(tipo, k.saldoinicialvalor, k.valor, k.saldofinalvalor)
#
#         if k.tipomovimiento == 2:
#             if k.salida:
#                 if DetalleSalidaProducto.objects.filter(pk = k.salida.pk,producto_id=i):
#                     #salida = DetalleSalidaProducto.objects.get(pk = k.salida.pk,producto_id=i)
#                     tipo = 'resta'
#                     print(tipo, k.saldoinicialvalor, k.valor, k.saldofinalvalor)
#



