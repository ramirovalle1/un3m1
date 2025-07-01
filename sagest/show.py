# -*- coding: UTF-8 -*-
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from sagest.models import Factura, NotaCredito
from sga.models import miinstitucion


@transaction.atomic()
def factura(request, id):
    try:
        data = {}
        data['comprobante'] = factura = Factura.objects.get(pk=id)
        data['institucion'] = miinstitucion()
        data['pagos'] = factura.pagos.all()
        return render(request, "rec_facturas/detalle_factura_pdf.html", data)
    except Exception as ex:
        return HttpResponseRedirect("/")


@transaction.atomic()
def notacredito(request, id):
    try:
        data = {}
        data['comprobante'] = notacredito = NotaCredito.objects.get(pk=id)
        data['institucion'] = miinstitucion()
        data['detalles'] = notacredito.detalle.all()
        return render(request, "rec_notacredito/detalle_notacredito_pdf.html", data)
    except Exception as ex:
        return HttpResponseRedirect("/")