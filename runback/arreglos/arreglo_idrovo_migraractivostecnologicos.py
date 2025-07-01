#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.http import HttpResponse

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

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

from datetime import datetime
from sagest.models import ActivoFijo, ActivoTecnologico

activostecnologicos = ActivoTecnologico.objects.filter(status=True, activotecnologico__catalogo__equipoelectronico=True,
                                                       activotecnologico__catalogo__status=True, activotecnologico__statusactivo=1,
                                                       activotecnologico__status=True, activotecnologico__catalogo__clasificado=True).values_list('activotecnologico_id')
activosfijos = ActivoFijo.objects.filter(id__in=activostecnologicos, status=True)
contador = 0
for activo in activosfijos:
    result = ActivoTecnologico.objects.filter(activotecnologico=activo)
    if result:
        contador += 1
        result[0].codigogobierno = activo.codigogobierno
        result[0].codigointerno = activo.codigointerno
        result[0].fechaingreso = activo.fechaingreso
        result[0].observacion = activo.observacion
        result[0].costo = activo.costo
        result[0].costohistorico = activo.costohistorico
        result[0].serie = activo.serie
        result[0].descripcion = activo.descripcion
        result[0].modelo = activo.modelo
        result[0].tipocomprobante = activo.tipocomprobante
        result[0].numerocomprobante = activo.numerocomprobante
        result[0].fechacomprobante = activo.fechacomprobante
        result[0].fechaultimadeprec = activo.fechaultimadeprec
        result[0].fechafindeprec = activo.fechafindeprec
        result[0].deprecia = activo.deprecia
        result[0].vidautil = activo.vidautil
        result[0].valorresidual = activo.valorresidual
        result[0].valordepreciacionacumulada = activo.valordepreciacionacumulada
        result[0].valordepreciacionanual = activo.valordepreciacionanual
        result[0].subidogobierno = activo.subidogobierno
        result[0].estructuraactivo = activo.estructuraactivo
        result[0].clasebien = activo.clasebien
        result[0].catalogo = activo.catalogo
        result[0].origeningreso = activo.origeningreso
        result[0].tipodocumentorespaldo = activo.tipodocumentorespaldo
        result[0].clasedocumentorespaldo = activo.clasedocumentorespaldo
        result[0].estado = activo.estado
        result[0].statusactivo = activo.statusactivo
        result[0].tipoproyecto = activo.tipoproyecto
        result[0].cuentacontable = activo.cuentacontable
        result[0].origenregistro = activo.origenregistro
        result[0].custodio = activo.custodio
        result[0].responsable = activo.responsable
        result[0].ubicacion = activo.ubicacion
        result[0].color = activo.color
        result[0].dimensiones = activo.dimensiones
        result[0].material = activo.material
        result[0].provincia = activo.provincia
        result[0].canton = activo.canton
        result[0].parroquia = activo.parroquia
        result[0].zona = activo.zona
        result[0].nomenclatura = activo.nomenclatura
        result[0].sector = activo.sector
        result[0].direccion = activo.direccion
        result[0].direccion2 = activo.direccion2
        result[0].escritura = activo.escritura
        result[0].fechaescritura = activo.fechaescritura
        result[0].notaria = activo.notaria
        result[0].beneficiariocontrato = activo.beneficiariocontrato
        result[0].fechacontrato = activo.fechacontrato
        result[0].duracioncontrato = activo.duracioncontrato
        result[0].montocontrato = activo.montocontrato
        result[0].archivobaja = activo.archivobaja
        result[0].procesobaja = activo.procesobaja
        result[0].tipo_registro = 1
        result[0].save()
        print(str(contador) + " - Se registra el activo tecnológico " + str(activo))