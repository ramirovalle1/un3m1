# -*- coding: UTF-8 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sagest.forms import ArchivoFirmado
from sagest.models import Factura, NotaCredito, LiquidacionCompra
from django.views.decorators.csrf import csrf_exempt

@transaction.atomic()
@csrf_exempt
def factura(request, weburl):
    if request.method == 'POST':
        try:
            f = ArchivoFirmado(request.POST, request.FILES)
            if f.is_valid():
                archivo = request.FILES['archivo']
                data = archivo.read()
                if Factura.objects.filter(weburl=weburl).exists():
                    comprobante = Factura.objects.get(weburl=weburl)
                    comprobante.xmlfirmado = data.decode('utf-8')
                    comprobante.firmada = True
                    comprobante.save(request)
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({'result': 'bad', 'mensaje': 'No existe el Documento a firmar'})
        except Exception as ex:
            transaction.set_rollback(True)
            return JsonResponse({'result': 'bad', 'mensaje': 'Error al guardar'})

        return JsonResponse({'result': 'bad'})
    else:
        if Factura.objects.filter(weburl=weburl).exists():
            comprobante = Factura.objects.get(weburl=weburl)
            data = {'representacion': comprobante, 'representacionnombre': 'FACTURA'}
            return render(request, "sign/form.html", data, content_type="text/plain")
        return HttpResponseRedirect("/")


@transaction.atomic()
@csrf_exempt
def notacredito(request, weburl):
    if request.method == 'POST':
        try:
            f = ArchivoFirmado(request.POST, request.FILES)
            if f.is_valid():
                archivo = request.FILES['archivo']
                data = archivo.read()
                if NotaCredito.objects.filter(weburl=weburl).exists():
                    comprobante = NotaCredito.objects.get(weburl=weburl)
                    comprobante.xmlfirmado = data.decode('utf-8')
                    comprobante.firmada = True
                    comprobante.save()
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({'result': 'bad', 'mensaje': 'No existe el Documento a firmar'})
        except Exception as ex:
            transaction.set_rollback(True)
            return JsonResponse({'result': 'bad', 'mensaje': 'Error al guardar'})

        return JsonResponse({'result': 'bad'})
    else:
        if NotaCredito.objects.filter(weburl=weburl).exists():
            comprobante = NotaCredito.objects.get(weburl=weburl)
            data = {'representacion': comprobante, 'representacionnombre': 'NOTA DE CREDITO'}
            return render(request, "sign/form.html", data, content_type="text/plain")
        return HttpResponseRedirect("/")


@transaction.atomic()
@csrf_exempt
def liquidacion(request, weburl):
    if request.method == 'POST':
        try:
            f = ArchivoFirmado(request.POST, request.FILES)
            if f.is_valid():
                archivo = request.FILES['archivo']
                data = archivo.read()
                if LiquidacionCompra.objects.filter(weburl=weburl).exists():
                    comprobante = LiquidacionCompra.objects.get(weburl=weburl)
                    comprobante.xmlfirmado = data.decode('utf-8')
                    comprobante.firmada = True
                    comprobante.save()
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({'result': 'bad', 'mensaje': 'No existe el Documento a firmar'})
        except Exception as ex:
            transaction.set_rollback(True)
            return JsonResponse({'result': 'bad', 'mensaje': 'Error al guardar'})

        return JsonResponse({'result': 'bad'})
    else:
        if LiquidacionCompra.objects.filter(weburl=weburl).exists():
            comprobante = LiquidacionCompra.objects.get(weburl=weburl)
            data = {'representacion': comprobante, 'representacionnombre': 'LIQUIDACION COMPRA'}
            return render(request, "sign/form.html", data, content_type="text/plain")
        return HttpResponseRedirect("/")

