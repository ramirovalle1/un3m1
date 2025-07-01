import os
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from .models import *

@transaction.atomic()
def view(request):
    data = {}

    if request.method == 'POST':
        res_json = []
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'view_requisitos_pagos_link':
                try:
                    INFORME_ACTIVIDAD = 14
                    CHECK_LIST_DE_PAGO = 16
                    FACTURA = 4
                    FORMATO_DE_PROVEEDORES = 6
                    RELACION_DEPENDENCIA_LABORAL = 20
                    IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO = 19
                    pk = request.GET.get('id', '0')
                    if pk == 0:
                        raise NameError("Parametro no encontrado")
                    factura = None
                    eSolicitudPago = SolicitudPago.objects.get(id=pk)
                    eRequisitoSolicitudPago = eSolicitudPago.traer_pasos_solicitud().order_by("orden").exclude( requisito_id__in=(CHECK_LIST_DE_PAGO, FACTURA,))
                    try:
                        impedimentoejercercargopublico = eSolicitudPago.traer_pasos_solicitud().order_by("orden").filter( requisito_id=IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO).first()
                        relaciondependencialaboral = eSolicitudPago.traer_pasos_solicitud().order_by("orden").filter( requisito_id=RELACION_DEPENDENCIA_LABORAL).first()
                        if impedimentoejercercargopublico.last_historial() and relaciondependencialaboral.last_historial():
                            if not impedimentoejercercargopublico.last_historial().archivo and not relaciondependencialaboral.last_historial().archivo:
                                eRequisitoSolicitudPago = eSolicitudPago.traer_pasos_solicitud().order_by("orden").exclude(requisito_id__in=(CHECK_LIST_DE_PAGO, FACTURA,IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO,RELACION_DEPENDENCIA_LABORAL))
                        else:
                            eRequisitoSolicitudPago = eSolicitudPago.traer_pasos_solicitud().order_by("orden").exclude( requisito_id__in=(CHECK_LIST_DE_PAGO, FACTURA, IMPEDIMENTO_PARA_EJERCER_CARGO_PUBLICO,RELACION_DEPENDENCIA_LABORAL))

                    except Exception as ex:
                        pass


                    if eSolicitudPago.traer_pasos_solicitud().order_by("orden").filter(requisito_id =FACTURA):
                        factura = eSolicitudPago.traer_pasos_solicitud().order_by("orden").filter(requisito_id =FACTURA).first()
                    data['eSolicitudPago'] = eSolicitudPago
                    data['factura'] = factura
                    data['eRequisitosPagos'] = eRequisitoSolicitudPago

                    return render(request, "adm_solicitudpago/link_requisito.html", data)
                except Exception as ex:
                    pass
            elif action == 'descarga_masiva_documentos':
                try:
                    id = request.GET.get('id', 0)
                    if id == 0: raise NameError("Parametro no encontrado")
                    eActaPagoPosgrado = ActaPagoPosgrado.objects.get(pk=id)
                    response =eActaPagoPosgrado.descargar_requisitos_todos(request)
                    if response:
                        return response
                    else:
                        raise NameError("Error ,.rar")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            elif action == 'descarga_individual_documentos':
                    try:
                        id = request.GET.get('id', 0)
                        if id == 0: raise NameError("Parametro no encontrado")
                        eSolicitudPago = SolicitudPago.objects.get(pk=id)
                        response = eSolicitudPago.descargar_requisitos(request)
                        if response:
                            return response
                        else:
                            raise NameError("Error ,.rar")

                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        else:
            try:
                data['title'] = u'Requisitos de pago'

                return render(request, 'adm_solicitudpago/view.html', data)
            except Exception as ex:
                print(ex)
                print(sys.exc_info()[-1].tb_lineno)
