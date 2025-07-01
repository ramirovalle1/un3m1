# -*- coding: UTF-8 -*-
import json
import os
import random
from datetime import datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import easyxf, XFStyle, Workbook

from decorators import secure_module, last_access
from sagest.commonviews import secuencia_recaudacion, anio_ejercicio
from sagest.forms import ComprobanteRecaudacionForm, ResumenComprobantePartidaForm, \
    CentroCostoForm, DevengarComprobanteForm, PartidasDevengarForm, ComprobanteRecaudacionFechaForm, \
    PercibirComprobanteForm, CurPercibirForm
from sagest.models import Factura, ComprobanteRecaudacion, \
    PuntoVenta, Pago, PapeletasDepositos, \
    DetalleNotaCreditoComprobante, ReciboCaja, CuentaBanco, TipoConceptoTransferenciaGobierno, \
    DetalleTransferenciaGobierno, ResumenComprobantePartida, null_to_decimal, CentroCostoTramiteIngreso, Diario, \
    DetalleDiario, CuentaContable, SesionCaja, FormaDePago, \
    ComprobanteRecaudacionCurPercibido, PagoReciboCaja
from settings import VENTA_BASE_ID, PERSONA_AUTORIZA_COMPROBANTE_INGRESO_ID, CUENTA_ACREEDORA_ID, \
    TESORERO_ID, SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, convertir_fecha, fechaformatostr, variable_valor
from sga.models import Persona
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ComprobanteRecaudacionForm(request.POST)
                comprobante = None
                if f.is_valid():
                    tipo = f.cleaned_data['tipocomprobante']
                    tesorero_id = variable_valor('TESORERO')
                    autoriza_id = variable_valor('AUTORIZA_COMPROBANTE')

                    if tipo.id == 1 or tipo.id == 3 or tipo.id == 7 or tipo.id == 8:
                        fecharec = f.cleaned_data['fecha']
                        if tipo.id == 3:
                            fechacomp = f.cleaned_data['fecha']
                        else:
                            fechacomp = f.cleaned_data['fechacomp']
                        valortotal = Decimal(request.POST['valortotalcomprobante'])
                        cierre = None
                        if SesionCaja.objects.filter(fecha=fechacomp).exists():
                            cierre = SesionCaja.objects.filter(fecha=fechacomp)[0]
                        else:
                            cierre = SesionCaja.objects.all().order_by('id')[0]
                        if fechacomp > datetime.now().date():
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha del comprobante no puede ser mayor a la actual."})
                        facturas = json.loads(request.POST['lista_items1'])
                        papeletas = json.loads(request.POST['lista_items2'])
                        puntoventa = f.cleaned_data['puntoemision']
                        comprobante = ComprobanteRecaudacion(tipocomprobanterecaudacion=tipo,
                                                             fecha=fechacomp,
                                                             cuentadeposito=f.cleaned_data['cuentadepositopac'],
                                                             puntoemision=puntoventa,
                                                             depositante=f.cleaned_data['depositante'],
                                                             concepto=f.cleaned_data['concepto'],
                                                             referencia=f.cleaned_data['referencia'],
                                                             observacion=f.cleaned_data['observacion'],
                                                             autoriza_id=autoriza_id,
                                                             tesorero_id=tesorero_id,
                                                             deposita=cierre.caja.persona,
                                                             valortotal=valortotal)
                        comprobante.save(request)
                        for d in facturas:
                            tipodoc = d['tipodoc']

                            if tipodoc == "FAC":
                                factura = Factura.objects.get(pk=int(d['id']))
                                factura.comprobante = comprobante
                                factura.pagada = True
                                factura.save(request)
                                factura.save(request)
                                factura.pagos.update(comprobante=comprobante)
                            elif tipodoc == "REC":
                                recibocaja = PagoReciboCaja.objects.get(pk=int(d['id']))
                                recibocaja.comprobante = comprobante
                                recibocaja.save(request)
                                recibocaja.pagos.update(comprobante=comprobante)
                            elif tipodoc == "REC2":
                                reciboc = ReciboCaja.objects.get(pk=int(d['id']))
                                reciboc.comprobante = comprobante
                                reciboc.save(request)
                                saldopartida = reciboc.partida
                                if not saldopartida:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"No está definida la Partida para este Recibo de Caja %s." % reciboc})
                                if ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante,
                                                                            partida=saldopartida).exists():
                                    detalle = \
                                    ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante,
                                                                             partida=saldopartida)[0]
                                    detalle.valor += reciboc.valor
                                    detalle.save(request)
                                else:
                                    detallecomprobante = ResumenComprobantePartida(comprobanterecaudacion=comprobante,
                                                                                   partida=saldopartida,
                                                                                   valor=reciboc.valor)
                                    detallecomprobante.save(request)
                        for pago in Pago.objects.filter(comprobante=comprobante):
                            saldopartida = pago.rubro.tipo.partida_saldo(pago.fecha.year)
                            if not saldopartida:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"No está definida la Partida para este rubro %s." % pago.rubro.tipo})
                            if ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante,  partida=saldopartida.partidassaldo).exists():
                                detalle = ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante, partida=saldopartida.partidassaldo)[0]
                                # detalle.valor += pago.valortotal
                                detalle.valor += (pago.subtotal0+pago.subtotaliva)
                                detalle.save(request)
                            else:
                                detallecomprobante = ResumenComprobantePartida(comprobanterecaudacion=comprobante,
                                                                               partida=saldopartida.partidassaldo,
                                                                               valor=(pago.subtotal0+pago.subtotaliva))
                                detallecomprobante.save(request)
                        for p in papeletas:
                            papeleta = PapeletasDepositos(comprobanterecaudacion=comprobante,
                                                          referencia=p['referencia'],
                                                          valor=Decimal(p['valor']))
                            papeleta.save(request)

                    if tipo.id == 2:
                        fecharec = f.cleaned_data['fecha']
                        fechacomp = f.cleaned_data['fecha']
                        valortotal = Decimal(request.POST['valortotalcomprobante'])
                        if fechacomp > datetime.now().date():
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha del comprobante no puede ser mayor a la actual."})
                        cierre = None
                        if SesionCaja.objects.filter(fecha=fechacomp).exists():
                            cierre = SesionCaja.objects.filter(fecha=fechacomp)[0]
                        else:
                            cierre = SesionCaja.objects.all().order_by('id')[0]
                        facturas = json.loads(request.POST['lista_items1'])
                        puntoventa = f.cleaned_data['puntoemision']
                        comprobante = ComprobanteRecaudacion(tipocomprobanterecaudacion=tipo,
                                                             fecha=fechacomp,
                                                             cuentadeposito=f.cleaned_data['cuentadepositopac'],
                                                             puntoemision=puntoventa,
                                                             depositante=f.cleaned_data['depositante'],
                                                             concepto=f.cleaned_data['concepto'],
                                                             referencia=f.cleaned_data['referencia'],
                                                             observacion=f.cleaned_data['observacion'],
                                                             autoriza_id=autoriza_id,
                                                             tesorero_id=tesorero_id,
                                                             deposita=cierre.caja.persona,
                                                             valortotal=valortotal)
                        comprobante.save(request)
                        for d in facturas:
                            tipodoc = d['tipodoc']

                            if tipodoc == "FAC":
                                factura = Factura.objects.get(pk=int(d['id']))
                                factura.comprobante = comprobante
                                factura.save(request)
                                factura.pagos.update(comprobante=comprobante)
                            else:
                                recibocaja = PagoReciboCaja.objects.get(pk=int(d['id']))
                                recibocaja.comprobante = comprobante
                                recibocaja.save(request)
                                recibocaja.pagos.update(comprobante=comprobante)


                        for pago in Pago.objects.filter(comprobante=comprobante):
                            saldopartida = pago.rubro.tipo.partida_saldo(pago.fecha.year)
                            if not saldopartida:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"No está definida la Partida para este rubro %s." % pago.rubro.tipo})
                            if ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante, partida=saldopartida.partidassaldo).exists():
                                detalle = ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante, partida=saldopartida.partidassaldo)[0]
                                # detalle.valor += pago.valortotal
                                detalle.valor += (pago.subtotal0+pago.subtotaliva)
                                detalle.save(request)
                            else:
                                detallecomprobante = ResumenComprobantePartida(comprobanterecaudacion=comprobante,
                                                                               partida=saldopartida.partidassaldo,
                                                                               valor=(pago.subtotal0+pago.subtotaliva))
                                detallecomprobante.save(request)
                    if tipo.id == 4:
                        fechanot = f.cleaned_data['fechanotacredito']
                        fechacomp = f.cleaned_data['fechanotacredito']
                        valortotal = Decimal(request.POST['valortotalcomprobante'])
                        if fechanot > datetime.now().date():
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no puede ser mayor a la actual."})
                        cierre = None
                        if SesionCaja.objects.filter(fecha=fechacomp).exists():
                            cierre = SesionCaja.objects.filter(fecha=fechacomp)[0]
                        else:
                            cierre = SesionCaja.objects.all().order_by('id')[0]
                        facturas = json.loads(request.POST['lista_items1'])
                        notas = json.loads(request.POST['lista_items2'])
                        puntoventa = f.cleaned_data['puntoemision']
                        comprobante = ComprobanteRecaudacion(tipocomprobanterecaudacion=tipo,
                                                             fecha=fechacomp,
                                                             fechanotacredito=fechanot,
                                                             cuentadeposito=f.cleaned_data['cuentadepositopac'],
                                                             puntoemision=puntoventa,
                                                             depositante=f.cleaned_data['depositante'],
                                                             concepto=f.cleaned_data['concepto'],
                                                             referencia=f.cleaned_data['referencia'],
                                                             observacion=f.cleaned_data['observacion'],
                                                             autoriza_id=autoriza_id,
                                                             tesorero_id=tesorero_id,
                                                             deposita=cierre.caja.persona,
                                                             valortotal=valortotal)
                        comprobante.save(request)
                        for d in facturas:
                            factura = Factura.objects.get(pk=int(d['id']))
                            factura.comprobante = comprobante
                            factura.pagada = True
                            factura.save(request)
                            factura.pagos.update(comprobante=comprobante)
                        for pago in Pago.objects.filter(comprobante=comprobante):
                            saldopartida = pago.rubro.tipo.partida_saldo(pago.fecha.year)
                            if not saldopartida:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"No está definida la Partida para este rubro %s." % pago.rubro.tipo})
                            if ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante, partida=saldopartida.partidassaldo).exists():
                                detalle = ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante,
                                                                                   partida=saldopartida.partidassaldo)[0]
                                # detalle.valor += pago.valortotal
                                detalle.valor += (pago.subtotal0+pago.subtotaliva)
                                detalle.save(request)
                            else:
                                detallecomprobante = ResumenComprobantePartida(comprobanterecaudacion=comprobante,
                                                                               partida=saldopartida.partidassaldo,
                                                                               valor=(pago.subtotal0+pago.subtotaliva))
                                detallecomprobante.save(request)
                        for n in notas:
                            nota = DetalleNotaCreditoComprobante(comprobanterecaudacion=comprobante,
                                                                 numero=n['numero'],
                                                                 valor=Decimal(n['valor']))
                            nota.save(request)
                    if tipo.id == 5:
                        fecharec = f.cleaned_data['fecha']
                        fechacomp = f.cleaned_data['fecha']
                        cierre = None
                        if SesionCaja.objects.filter(fecha=fechacomp).exists():
                            cierre = SesionCaja.objects.filter(fecha=fechacomp)[0]
                        else:
                            cierre = SesionCaja.objects.all().order_by('id')[0]
                        valortotal = Decimal(request.POST['valortotalcomprobante'])
                        if fechacomp > datetime.now().date():
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha del comprobante no puede ser mayor a la actual."})
                        recibos = json.loads(request.POST['lista_items1'])
                        papeletas = json.loads(request.POST['lista_items2'])
                        puntoventa = f.cleaned_data['puntoemision']
                        comprobante = ComprobanteRecaudacion(tipocomprobanterecaudacion=tipo,
                                                             fecha=fechacomp,
                                                             cuentadeposito=f.cleaned_data['cuentadepositopac'],
                                                             puntoemision=puntoventa,
                                                             depositante=f.cleaned_data['depositante'],
                                                             concepto=f.cleaned_data['concepto'],
                                                             referencia=f.cleaned_data['referencia'],
                                                             observacion=f.cleaned_data['observacion'],
                                                             autoriza_id=autoriza_id,
                                                             tesorero_id=tesorero_id,
                                                             deposita=cierre.caja.persona,
                                                             valortotal=valortotal)
                        comprobante.save(request)
                        for r in recibos:
                            recibo = ReciboCaja.objects.get(pk=int(r['id']))
                            recibo.comprobante = comprobante
                            recibo.save(request)
                            saldopartida = recibo.partida
                            if not saldopartida:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"No está definida la Partida para este Recibo de Caja %s." % recibo})
                            if ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante, partida=saldopartida).exists():
                                detalle = ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante,partida=saldopartida)[0]
                                detalle.valor += recibo.valor
                                detalle.save(request)
                            else:
                                detallecomprobante = ResumenComprobantePartida(comprobanterecaudacion=comprobante,
                                                                               partida=saldopartida,
                                                                               valor=recibo.valor)
                                detallecomprobante.save(request)
                        for p in papeletas:
                            papeleta = PapeletasDepositos(comprobanterecaudacion=comprobante,
                                                          referencia=p['referencia'],
                                                          valor=Decimal(p['valor']))
                            papeleta.save(request)
                        if not valortotal:
                            comprobante.valortotal = comprobante.papeletasdepositos_set.aggregate(valor=Sum('valor'))['valor']
                            comprobante.save(request)
                    if tipo.id == 6:
                        fechacomp = f.cleaned_data['fechacomp']
                        valordiferencia = Decimal(request.POST['totaldiferencia'])
                        if fechacomp > datetime.now().date():
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha del comprobante no puede ser mayor a la actual."})
                        cierre = None
                        if SesionCaja.objects.filter(fecha=fechacomp).exists():
                            cierre = SesionCaja.objects.filter(fecha=fechacomp)[0]
                        else:
                            cierre = SesionCaja.objects.all().order_by('id')[0]
                        puntoventa = f.cleaned_data['puntoemision']
                        comprobante = ComprobanteRecaudacion(tipocomprobanterecaudacion=tipo,
                                                             fecha=fechacomp,
                                                             cuentadeposito=f.cleaned_data['cuentadepositocent'],
                                                             puntoemision=puntoventa,
                                                             depositante=f.cleaned_data['depositante'],
                                                             concepto=f.cleaned_data['concepto'],
                                                             referencia=f.cleaned_data['referencia'],
                                                             observacion=f.cleaned_data['observacion'],
                                                             autoriza_id=autoriza_id,
                                                             tesorero_id=tesorero_id,
                                                             deposita=cierre.caja.persona,
                                                             valortotal=f.cleaned_data['valortotal'])
                        comprobante.save(request)
                        detalle = DetalleTransferenciaGobierno(comprobanterecaudacion=comprobante,
                                                               tipoconcepto=f.cleaned_data['conceptotrans'],
                                                               numero=f.cleaned_data['numerocur'],
                                                               montopresupuestado=f.cleaned_data['montopresupuestado'],
                                                               montorecibido=f.cleaned_data['valortotal'],
                                                               diferencia=valordiferencia,
                                                               observacion=f.cleaned_data['observacion'],
                                                               cuota=f.cleaned_data['cuota'])
                        detalle.save(request)
                        # saldopartida = detalle.tipoconcepto.partida
                        # if not saldopartida:
                        #     transaction.set_rollback(True)
                        #     return JsonResponse({"result": "bad",
                        #                                     "mensaje": u"No está definida la Partida para este Recibo de Caja %s." % recibo}),
                        #                         content_type="application/json")
                        # detallecomprobante = ResumenComprobantePartida(comprobanterecaudacion=comprobante,
                        #                                                partida=saldopartida,
                        #                                                valor=recibo.valor)
                        # detallecomprobante.save(request)
                    log(u'Adiciono nuevo comprobante: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok", 'id': comprobante.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcosto':
            try:
                f = CentroCostoForm(request.POST)
                comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    valoractual = Decimal(comprobante.total_costos()) + Decimal(f.cleaned_data['total'])
                    if valoractual > comprobante.valortotal:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor supera el total del Comprobante."})
                    costo = CentroCostoTramiteIngreso(comprobante=comprobante,
                                                      centrocosto_id=f.cleaned_data['detalle'],
                                                      valor=Decimal(f.cleaned_data['total']))
                    costo.save(request)
                    costo.centrocosto.actualiza_saldo_ingreso(comprobante.fecha.year)
                    log(u'Adiciono nuevo costo al documento: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarcosto':
            try:
                costo = CentroCostoTramiteIngreso.objects.get(pk=int(request.POST['id']))
                centrocosto = costo.centrocosto
                comprobante = costo.comprobante
                costo.delete()
                centrocosto.actualiza_saldo_ingreso(comprobante.fecha.year)
                log(u'Elimino costo: %s' % costo, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'finalizarcomp':
            try:
                comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))
                comprobante.estado = 2
                comprobante.save(request)
                secuencia = secuencia_recaudacion(request, comprobante.puntoemision, 'comprobante')
                if not comprobante.numero:
                    # secuencia.comprobante += 1
                    # secuencia.save(request)
                    comprobante.numero = secuencia
                comprobante.save(request)
                log(u'Finalizar comprobante: %s' % comprobante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'confirmarpartida':
            try:
                comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))
                # if not comprobante.valortotal == null_to_decimal(comprobante.resumencomprobantepartida_set.aggregate(valor=Sum('valor'))['valor']):
                #     return JsonResponse({"result": "bad", "mensaje": u"El saldo de las partidas y comprobante deben coincidir."})
                comprobante.confirmado = True
                comprobante.fechaconfirmacion = datetime.now().date()
                comprobante.jefepresupuesto_id = variable_valor('PRESUPUESTO')
                comprobante.personaconfirma = persona
                secuencia = secuencia_recaudacion(request, comprobante.puntoemision, 'nocur')
                if not comprobante.nocur:
                    # secuencia.nocur += 1
                    # secuencia.save(request)
                    comprobante.nocur = secuencia
                comprobante.save(request)
                for partidacomprobante in comprobante.resumencomprobantepartida_set.all():
                    partidacomprobante.partida.actualizar_saldos(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addpartida':
            try:
                f = ResumenComprobantePartidaForm(request.POST)
                if f.is_valid():
                    comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))
                    saldopartida = f.cleaned_data['partida']
                    valor = f.cleaned_data['valor']
                    totalpartidas = comprobante.valor_partidas() + Decimal(valor)
                    if totalpartidas > comprobante.valortotal:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de las partidas supera el valor del comprobante."})
                    detallecomprobante = ResumenComprobantePartida(comprobanterecaudacion=comprobante,
                                                                   partida=saldopartida,
                                                                   valor=valor)
                    detallecomprobante.save(request)
                    log(u'Adiciono nuevo partida: %s' % saldopartida, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editpartida':
            try:
                f = ResumenComprobantePartidaForm(request.POST)
                if f.is_valid():
                    partidacomprobante = ResumenComprobantePartida.objects.get(pk=int(request.POST['id']))
                    partidacomprobante.partida=f.cleaned_data['partida']
                    partidacomprobante.valor=f.cleaned_data['valor']
                    partidacomprobante.save(request)
                    log(u'Adiciono edito partida: %s' % partidacomprobante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cambiarfecha':
            try:
                f = ComprobanteRecaudacionFechaForm(request.POST)

                if f.is_valid():
                    if f.cleaned_data['fechaesigef']:
                        if f.cleaned_data['fechaesigef'] < f.cleaned_data['fecha']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha eSigef debe ser mayor o igual a la fecha del comprobante."})

                    if 'lista_items1' in request.POST:
                        curs = json.loads(request.POST['lista_items1'])
                        for c in curs:
                            if datetime.strptime(c['fecha'], "%d-%m-%Y").date() < f.cleaned_data['fecha']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha BCE del CUR # %s debe ser mayor o igual a la fecha del comprobante." % (c['numerocur'])})

                    comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))
                    comprobante.fecha=f.cleaned_data['fecha']
                    #comprobante.fechabanco=f.cleaned_data['fechabanco']
                    if f.cleaned_data['fechaesigef']:
                        comprobante.fechaesigef=f.cleaned_data['fechaesigef']

                    comprobante.save(request)

                    if 'lista_items1' in request.POST:
                        curs = json.loads(request.POST['lista_items1'])
                        for c in curs:
                            comprobantecur = ComprobanteRecaudacionCurPercibido.objects.get(pk=int(c['id']))
                            comprobantecur.fechabce = datetime.strptime(c['fecha'], "%d-%m-%Y").date()
                            comprobantecur.save(request)

                    log(u'Modifico Fecha al Comprobanete de Recaudacion: %s' % comprobante, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = ComprobanteRecaudacionForm(request.POST)
                if f.is_valid():
                    comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))
                    tipo = comprobante.tipocomprobanterecaudacion
                    comprobante.papeletasdepositos_set.all().delete()
                    if tipo.id == 1 or tipo.id == 3 or tipo.id == 7 or tipo.id == 8:
                        papeletas = json.loads(request.POST['lista_items8'])
                        comprobante.cuentadeposito = f.cleaned_data['cuentadepositopac']
                        comprobante.depositante = f.cleaned_data['depositante']
                        comprobante.concepto = f.cleaned_data['concepto']
                        comprobante.referencia = f.cleaned_data['referencia']
                        comprobante.observacion = f.cleaned_data['observacion']

                        if tipo.id == 8:
                            comprobante.valortotal = Decimal(request.POST['valortotalcomprobante'])

                        comprobante.save(request)
                        comprobante.resumencomprobantepartida_set.all().delete()
                        for pago in Pago.objects.filter(comprobante=comprobante):
                            saldopartida = pago.rubro.tipo.partida_saldo(pago.fecha.year)
                            if not saldopartida:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"No está definida la Partida para este rubro %s." % pago.rubro.tipo})
                            if ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante,  partida=saldopartida.partidassaldo).exists():
                                detalle = ResumenComprobantePartida.objects.filter(comprobanterecaudacion=comprobante, partida=saldopartida.partidassaldo)[0]
                                # detalle.valor += pago.valortotal
                                detalle.valor += (pago.subtotal0+pago.subtotaliva)
                                detalle.save(request)
                            else:
                                detallecomprobante = ResumenComprobantePartida(comprobanterecaudacion=comprobante,
                                                                               partida=saldopartida.partidassaldo,
                                                                               valor=(pago.subtotal0+pago.subtotaliva))
                                detallecomprobante.save(request)

                        for p in papeletas:
                            papeleta = PapeletasDepositos(comprobanterecaudacion=comprobante,
                                                          referencia=p['referencia'],
                                                          valor=Decimal(p['valor']))
                            papeleta.save(request)
                    if tipo.id == 2:
                        comprobante.cuentadeposito = f.cleaned_data['cuentadepositopac']
                        comprobante.depositante = f.cleaned_data['depositante']
                        comprobante.concepto = f.cleaned_data['concepto']
                        comprobante.referencia = f.cleaned_data['referencia']
                        comprobante.observacion = f.cleaned_data['observacion']
                        comprobante.save(request)
                    if tipo.id == 4:
                        notas = json.loads(request.POST['lista_items2'])
                        valortotal = Decimal(request.POST['valortotalcomprobante'])
                        comprobante.cuentadeposito = f.cleaned_data['cuentadepositopac']
                        comprobante.depositante = f.cleaned_data['depositante']
                        comprobante.concepto = f.cleaned_data['concepto']
                        comprobante.referencia = f.cleaned_data['referencia']
                        comprobante.observacion = f.cleaned_data['observacion']
                        comprobante.valortotal = valortotal
                        comprobante.save(request)
                        comprobante.detallenotacreditocomprobante_set.all().delete()
                        for n in notas:
                            nota = DetalleNotaCreditoComprobante(comprobanterecaudacion=comprobante,
                                                                 numero=n['numero'],
                                                                 valor=Decimal(n['valor']))
                            nota.save(request)
                    if tipo.id == 5:
                        papeletas = json.loads(request.POST['lista_items2'])
                        comprobante.cuentadeposito = f.cleaned_data['cuentadepositopac']
                        comprobante.depositante = f.cleaned_data['depositante']
                        comprobante.concepto = f.cleaned_data['concepto']
                        comprobante.referencia = f.cleaned_data['referencia']
                        comprobante.observacion = f.cleaned_data['observacion']
                        comprobante.save(request)
                        for p in papeletas:
                            papeleta = PapeletasDepositos(comprobanterecaudacion=comprobante,
                                                          referencia=p['referencia'],
                                                          valor=Decimal(p['valor']))
                            papeleta.save(request)
                    if tipo.id == 6:
                        comprobante.cuentadeposito = f.cleaned_data['cuentadepositopac']
                        comprobante.depositante = f.cleaned_data['depositante']
                        comprobante.concepto = f.cleaned_data['concepto']
                        comprobante.referencia = f.cleaned_data['referencia']
                        comprobante.observacion = f.cleaned_data['observacion']
                        comprobante.save(request)
                    log(u'Adiciono edito comprobante: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

        if action == 'devengar':
            try:
                comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))

                if Diario.objects.filter(tipo=1, documento=comprobante.numero, status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El Comprobante de ingreso ya ha sido devengado."})

                if not 'lista_items1' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe agregar cuenta(s) deudora(s)."})
                else:
                    sumacuenta = 0
                    for cuenta in json.loads(request.POST['lista_items1']):
                        sumacuenta += Decimal(cuenta['monto']).quantize(Decimal('.01'))

                    if sumacuenta == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe agregar cuenta(s) deudora(s)."})

                f = DevengarComprobanteForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['valortotal'] != sumacuenta:
                        return JsonResponse({"result": "bad", "mensaje": u"La sumatoria de valores de las cuentas deben ser igual al Valor Total."})


                    datos = json.loads(request.POST['lista_items1'])

                    diario = Diario(tipo=1,
                                    documento=comprobante.numero)
                    diario.save(request)
                    for cuenta in comprobante.resumencomprobantepartida_set.all():
                        detalleacreedor = DetalleDiario(diario=diario,
                                                naturaleza=2,
                                                cuentacontable=cuenta.partida.partida.mi_cuenta(),
                                                valor=cuenta.valor)
                        detalleacreedor.save(request)

                    # cuentaiva = CuentaContable.objects.get(cuenta='213.81.07')
                    # for cuenta in comprobante.pago_set.filter(iva__gt=0):
                    #     detalleacreedor = DetalleDiario(diario=diario,
                    #                             naturaleza=2,
                    #                             cuentacontable=cuentaiva,
                    #                             valor=cuenta.iva)
                    #     detalleacreedor.save(request)

                    cuentaiva = CuentaContable.objects.get(cuenta='213.81.07')
                    totaliva = 0
                    ivas = comprobante.pago_set.filter(iva__gt=0)
                    if ivas:
                        totaliva = null_to_decimal(Decimal(comprobante.pago_set.filter(iva__gt=0).aggregate(totaliva=Sum('iva'))['totaliva']).quantize(Decimal('.01')), 2)

                    if totaliva > 0:
                        detalleacreedor = DetalleDiario(diario=diario,
                                                        naturaleza=2,
                                                        cuentacontable=cuentaiva,
                                                        valor=totaliva)
                        detalleacreedor.save(request)

                    for d in datos:
                        cuenta = CuentaContable.objects.get(pk=int(d['id']))
                        detalledeudor = DetalleDiario(diario=diario,
                                                naturaleza=1,
                                                cuentacontable=cuenta,
                                                valor=Decimal(d['monto']))
                        detalledeudor.save(request)
                    comprobante.curdevengado = f.cleaned_data['curdevengado']
                    comprobante.conceptodevengado = f.cleaned_data['conceptodevengado']
                    comprobante.conceptopercibido = ""
                    comprobante.devengado = True
                    comprobante.fechadevengado = datetime.now().date()
                    comprobante.save(request)
                    log(u'Adiciono edito comprobante: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editdevengado':
            try:
                if not 'lista_items1' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Debe agregar cuenta(s) deudora(s)."})
                else:
                    sumacuenta = 0
                    for cuenta in json.loads(request.POST['lista_items1']):
                        sumacuenta += Decimal(cuenta['monto']).quantize(Decimal('.01'))

                    if sumacuenta == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe agregar cuenta(s) deudora(s)."})

                f = DevengarComprobanteForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['valortotal'] != sumacuenta:
                        return JsonResponse({"result": "bad", "mensaje": u"La sumatoria de valores de las cuentas deben ser igual al Valor Total."})

                    diario = Diario.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista_items1'])
                    comprobante = ComprobanteRecaudacion.objects.get(numero=diario.documento)

                    diario.detallediario_set.filter(naturaleza=2).delete()
                    for cuenta in comprobante.resumencomprobantepartida_set.all():
                        detalleacreedor = DetalleDiario(diario=diario,
                                                        naturaleza=2,
                                                        cuentacontable=cuenta.partida.partida.mi_cuenta(),
                                                        valor=cuenta.valor)
                        detalleacreedor.save(request)

                    # cuentaiva = CuentaContable.objects.get(cuenta='213.81.07')
                    # for cuenta in comprobante.pago_set.filter(iva__gt=0):
                    #     detalleacreedor = DetalleDiario(diario=diario,
                    #                                     naturaleza=2,
                    #                                     cuentacontable=cuentaiva,
                    #                                     valor=cuenta.iva)
                    #     detalleacreedor.save(request)

                    cuentaiva = CuentaContable.objects.get(cuenta='213.81.07')
                    totaliva = 0
                    ivas = comprobante.pago_set.filter(iva__gt=0)
                    if ivas:
                        totaliva = null_to_decimal(Decimal(comprobante.pago_set.filter(iva__gt=0).aggregate(totaliva=Sum('iva'))['totaliva']).quantize(Decimal('.01')), 2)

                    if totaliva > 0:
                        detalleacreedor = DetalleDiario(diario=diario,
                                                        naturaleza=2,
                                                        cuentacontable=cuentaiva,
                                                        valor=totaliva)
                        detalleacreedor.save(request)

                    diario.detallediario_set.filter(naturaleza=1).delete()
                    for d in datos:
                        cuenta = CuentaContable.objects.get(pk=int(d['id']))
                        detalledeudor = DetalleDiario(diario=diario,
                                                      naturaleza=1,
                                                      cuentacontable=cuenta,
                                                      valor=Decimal(d['monto']))
                        detalledeudor.save(request)
                    comprobante.curdevengado = f.cleaned_data['curdevengado']
                    comprobante.conceptodevengado = f.cleaned_data['conceptodevengado']
                    comprobante.conceptopercibido = ""
                    comprobante.devengado = True
                    comprobante.fechadevengado = datetime.now().date()
                    comprobante.save(request)
                    log(u'Adiciono edito comprobante: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'percibir':
            try:
                comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))

                if Diario.objects.filter(tipo=2, documento=comprobante.numero, status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"El Comprobante de ingreso ya ha sido percibido"})

                f = PercibirComprobanteForm(request.POST)
                if f.is_valid():
                    if Decimal(request.POST['totalmontocur']).quantize(Decimal('.01')) != f.cleaned_data['valortotal']:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor Totales CUR debe ser igual al Valor Total"})
                    elif Decimal(request.POST['vdebefil1']).quantize(Decimal('.01')) <= 0.00:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de la cuenta deudora de la fila # 1 está en negativo"})
                    elif Decimal(request.POST['totalmontodebe']).quantize(Decimal('.01')) != Decimal(request.POST['totalmontohaber']).quantize(Decimal('.01')):
                        return JsonResponse({"result": "bad", "mensaje": u"Los totales de las cuentas deudoras y acreedoras deben ser iguales"})
                    elif Decimal(request.POST['totalmontodebe']).quantize(Decimal('.01')) != f.cleaned_data['valortotal']:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor total de las cuentas deudoras y acreedoras deben ser igual al Valor Total del comprobante"})


                    diario = Diario(tipo=2,
                                    documento=comprobante.numero)
                    diario.save(request)

                    diario2 = Diario.objects.get(tipo=1, documento=comprobante.numero)

                    # cuentad = diario2.detallediario_set.filter(naturaleza=1)[0]
                    # detalleacreedor = DetalleDiario(diario=diario,
                    #                         naturaleza=2,
                    #                         cuentacontable=cuentad.cuentacontable,
                    #                         valor=cuentad.valor)
                    # detalleacreedor.save(request)

                    cuentad = diario2.detallediario_set.filter(naturaleza=1)
                    for ctad in cuentad:
                        detalleacreedor = DetalleDiario(diario=diario,
                                                        naturaleza=2,
                                                        cuentacontable=ctad.cuentacontable,
                                                        valor=ctad.valor)
                        detalleacreedor.save(request)


                    valoraux=0
                    if 'lista_items1' in request.POST:
                        datos = json.loads(request.POST['lista_items1'])
                        for d in datos:
                            valoraux += Decimal(d['monto'])
                        cuenta = CuentaContable.objects.get(pk=CUENTA_ACREEDORA_ID)
                        detalledeudor = DetalleDiario(diario=diario,
                                                      naturaleza=1,
                                                      cuentacontable=cuenta,
                                                      valor=comprobante.valortotal - valoraux)
                        detalledeudor.save(request)
                        for d in datos:
                            cuenta = CuentaContable.objects.get(pk=int(d['id']))
                            detalledeudor = DetalleDiario(diario=diario,
                                                    naturaleza=1,
                                                    cuentacontable=cuenta,
                                                    valor=Decimal(d['monto']))
                            detalledeudor.save(request)
                    else:
                        cuenta = CuentaContable.objects.get(pk=CUENTA_ACREEDORA_ID)
                        detalledeudor = DetalleDiario(diario=diario,
                                                      naturaleza=1,
                                                      cuentacontable=cuenta,
                                                      valor=comprobante.valortotal - valoraux)
                        detalledeudor.save(request)


                    comprobante.conceptopercibido = f.cleaned_data['conceptopercibido']
                    comprobante.percibido = True
                    comprobante.fechaesigef = f.cleaned_data['fechaesigef']
                    comprobante.personapercibe = persona
                    comprobante.fechapercibido = datetime.now().date()
                    comprobante.save(request)

                    curs = json.loads(request.POST['lista_items2'])
                    for c in curs:
                        tipocobro = FormaDePago.objects.get(pk=c['tiporeca'])
                        curpercibido = ComprobanteRecaudacionCurPercibido(comprobante=comprobante,
                                                                          numerocur=c['numerocur'],
                                                                          fechabce=convertir_fecha(c['fechabce']),
                                                                          valor=c['montocur'],
                                                                          afectatotal=True if c['afecta']==1 else False,
                                                                          tipocobro=tipocobro)
                        curpercibido.save(request)


                    log(u'Adiciono edito comprobante: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        if action == 'detalle_asiento':
            try:
                data['diario'] = diario = Diario.objects.get(pk=int(request.POST['id']))
                data['asientos'] = diario.detallediario_set.filter(status=True).order_by('naturaleza')
                template = get_template("rec_comprobantes/detalle_asiento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'datos_rec_ventanilla':
            try:
                data = {}
                data['puntoemision'] = puntoemision = PuntoVenta.objects.get(pk=int(request.POST['puntoemision']))
                fecha = convertir_fecha(request.POST['fecha'])
                data['detalles'] = facturas = Factura.objects.filter(comprobante__isnull=True, pagos__fecha=fecha, valida=True, autorizada=True, puntoventa=puntoemision).exclude(pagos__pagocuentaporcobrar__isnull=False).exclude(pagos__rubro__contratorecaudacion__isnull=False).exclude(pagos__rubro__tipo__id=2755).exclude(pagos__rubro__tipo__id=VENTA_BASE_ID).exclude(pagos__pagotransferenciadeposito__isnull=False).distinct()
                cajeros = Persona.objects.filter(lugarrecaudacion__sesioncaja__factura__in=facturas).distinct()
                valortotal = null_to_decimal(Pago.objects.filter(factura__in=facturas).aggregate(valor=Sum('valortotal'))['valor'])
                template = get_template("rec_comprobantes/datosventanilla.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'cajeros': [x.nombre_completo() for x in cajeros], 'valortotal': str(valortotal) if valortotal else 0})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'datos_rec_devolucion':
            try:
                data = {}
                data['puntoemision'] = puntoemision = PuntoVenta.objects.get(pk=int(request.POST['puntoemision']))
                fecha = convertir_fecha(request.POST['fecha'])
                data['detalles'] = recibocaja = ReciboCaja.objects.filter(comprobante__isnull=True, sesioncaja__fecha=fecha).distinct()
                valortotal = null_to_decimal(recibocaja.aggregate(valor=Sum('valor'))['valor'])
                template = get_template("rec_comprobantes/datosdevolucion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'valortotal': str(valortotal) if valortotal else 0})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'datos_rec_notacredito':
            try:
                data = {}
                data['puntoemision'] = puntoemision = PuntoVenta.objects.get(pk=int(request.POST['puntoemision']))
                fecha = convertir_fecha(request.POST['fecha'])
                data['detalles'] = facturas = Factura.objects.filter(Q(pagos__pagocuentaporcobrar__isnull=False) | Q(pagos__pagotransferenciadeposito__isnull=False), pagos__fecha=fecha, comprobante__isnull=True, valida=True, autorizada=True, puntoventa=puntoemision).exclude(pagos__rubro__tipo__id=VENTA_BASE_ID).exclude(pagos__pagotransferenciadeposito__recaudacionventanilla=True).distinct()
                valortotal = null_to_decimal(Pago.objects.filter(factura__in=facturas).aggregate(valor=Sum('valortotal'))['valor'])
                template = get_template("rec_comprobantes/datosventanillanotas.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'valortotal': str(valortotal) if valortotal else 0})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'datos_rec_terceros':
            try:
                data = {}
                data['puntoemision'] = puntoemision = PuntoVenta.objects.get(pk=int(request.POST['puntoemision']))
                fecha = convertir_fecha(request.POST['fecha'])
                data['detalles'] = facturas = Factura.objects.filter(Q(pagos__rubro__tipo__id=VENTA_BASE_ID) | Q(pagos__pagotransferenciadeposito__isnull=False), comprobante__isnull=True, pagos__fecha=fecha, valida=True, autorizada=True, puntoventa=puntoemision).exclude(pagos__pagocuentaporcobrar__isnull=False).exclude(pagos__pagotransferenciadeposito__recaudacionventanilla=True).exclude(pagos__rubro__contratorecaudacion__isnull=False).distinct()
                valortotal = null_to_decimal(Pago.objects.filter(factura__in=facturas).aggregate(valor=Sum('valortotal'))['valor'])

                data['reciboscaja'] = reciboscaja = PagoReciboCaja.objects.filter(comprobante__isnull=True,
                                                                                  pagos__pagotransferenciadeposito__recaudacionventanilla=False,
                                                                                  pagos__fecha=fecha,
                                                                                  puntoventa=puntoemision).order_by(
                    'id').distinct()
                data['reciboscaja2'] = recibocaja = ReciboCaja.objects.filter(comprobante__isnull=True, fechacomprobante=fecha).distinct()

                totalrecibos = null_to_decimal(reciboscaja.aggregate(totalrecibo=Sum('valor'))['totalrecibo'])
                totalrecibos2 = null_to_decimal(recibocaja.aggregate(totalrecibo=Sum('valor'))['totalrecibo'])
                valortotal = valortotal + totalrecibos + totalrecibos2
                template = get_template("rec_comprobantes/datosventanillaterceros.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'valortotal': str(valortotal) if valortotal else 0})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'datos_rec_otros':
            try:
                data = {}
                data['puntoemision'] = puntoemision = PuntoVenta.objects.get(pk=int(request.POST['puntoemision']))
                fecha = convertir_fecha(request.POST['fecha'])
                data['detalles'] = facturas = Factura.objects.filter(Q(pagos__pagocuentaporcobrar__isnull=True) | Q(pagos__rubro__contratorecaudacion__isnull=True), comprobante__isnull=True, pagos__fecha=fecha, valida=True, autorizada=True, puntoventa=puntoemision).exclude(pagos__pagotransferenciadeposito__recaudacionventanilla=True).exclude(pagos__rubro__tipo__id=VENTA_BASE_ID).distinct()
                # data['detalles'] = facturas = Factura.objects.filter(Q(pagos__pagocuentaporcobrar__isnull=False) | Q(pagos__rubro__contratorecaudacion__isnull=False), comprobante__isnull=True, pagos__fecha=fecha, valida=True, autorizada=True, puntoventa=puntoemision).exclude(pagos__pagotransferenciadeposito__recaudacionventanilla=True).exclude(pagos__rubro__tipo__id=VENTA_BASE_ID).distinct()
                valortotal = null_to_decimal(Pago.objects.filter(factura__in=facturas).aggregate(valor=Sum('valortotal'))['valor'])
                template = get_template("rec_comprobantes/datosventanillaterceros.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'valortotal': str(valortotal) if valortotal else 0})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'datos_rec_fianza':
            try:
                data = {}
                data['puntoemision'] = puntoemision = PuntoVenta.objects.get(pk=int(request.POST['puntoemision']))
                fecha = convertir_fecha(request.POST['fecha'])
                data['reciboscaja2'] = recibocaja = ReciboCaja.objects.filter(comprobante__isnull=True,
                                                                              fechacomprobante=fecha).distinct()

                valortotal = null_to_decimal(recibocaja.aggregate(totalrecibo=Sum('valor'))['totalrecibo'])
                template = get_template("rec_comprobantes/datosventanillaterceros.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'valortotal': str(valortotal) if valortotal else 0})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'datos_rec_matricula':
            try:
                data = {}
                data['puntoemision'] = puntoemision = PuntoVenta.objects.get(pk=int(request.POST['puntoemision']))
                fecha = convertir_fecha(request.POST['fecha'])

                data['detalles'] = facturas = Factura.objects.filter(comprobante__isnull=True, pagos__pagotransferenciadeposito__recaudacionventanilla=True, pagos__fecha=fecha, valida=True, autorizada=True, puntoventa=puntoemision).exclude(pagos__pagocuentaporcobrar__isnull=False).exclude(pagos__rubro__contratorecaudacion__isnull=False).exclude(pagos__rubro__tipo__id=VENTA_BASE_ID).distinct().order_by('numero')

                # for f in facturas:
                #     print(f.numero)

                data['reciboscaja'] = reciboscaja = PagoReciboCaja.objects.filter(status=True, comprobante__isnull=True, pagos__pagotransferenciadeposito__recaudacionventanilla=True, pagos__fecha=fecha, puntoventa=puntoemision).order_by('id').distinct()

                valortotal = null_to_decimal(Pago.objects.filter(factura__in=facturas).aggregate(valor=Sum('valortotal'))['valor'])

                totalrecibos = null_to_decimal(reciboscaja.aggregate(totalrecibo=Sum('valor'))['totalrecibo'])

                valortotal = valortotal + totalrecibos

                template = get_template("rec_comprobantes/datosventanillamatricula.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'valortotal': str(valortotal) if valortotal else 0})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'eliminarcomprobante':
            try:
                comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))
                comprobante.factura_set.update(comprobante=None)
                comprobante.pagorecibocaja_set.update(comprobante=None)
                if comprobante.tipocomprobanterecaudacion.id == 4:
                    comprobante.factura_set.update(pagada=False)
                comprobante.recibocaja_set.update(comprobante=None)
                comprobante.pago_set.update(comprobante=None)
                comprobante.delete()
                log(u'Elimino comprobante: %s' % comprobante, request, "delete")
                res_json = {"error": False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'anularcomprobante':
            try:
                comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.POST['id']))
                comprobante.factura_set.update(comprobante=None)
                comprobante.pagorecibocaja_set.update(comprobante=None)
                if comprobante.tipocomprobanterecaudacion.id == 4:
                    comprobante.factura_set.update(pagada=False)
                comprobante.recibocaja_set.update(comprobante=None)
                comprobante.pago_set.update(comprobante=None)
                comprobante.estado=3
                comprobante.personaanula=persona
                comprobante.fechaanula=datetime.now().date()
                comprobante.save(request)
                log(u'Anulo comprobante de ingreso: %s' % comprobante, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletepartida':
            try:
                partidacomprobante = ResumenComprobantePartida.objects.get(pk=int(request.POST['id']))
                partidaanterior = partidacomprobante.partida
                partidacomprobante.delete()
                log(u'Elimino partida del comprobante: %s' % partidaanterior, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'partida_concepto':
            try:
                concepto = TipoConceptoTransferenciaGobierno.objects.get(pk=int(request.POST['id']))
                lista = []
                lista.append([concepto.partida.id, concepto.partida.codigo + ' - ' + concepto.partida.nombre])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'cuenta_concepto':
            try:
                cuenta = CuentaBanco.objects.get(pk=int(request.POST['id']))
                lista = []
                for concepto in cuenta.tipoconceptotransferenciagobierno_set.all():
                    if [concepto.id, concepto.nombre] not in lista:
                        lista.append([concepto.id, concepto.nombre])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'comprobantesdescuadretotalcuenta':
            try:
                lista_nocuadrados = []
                comprobantes = ComprobanteRecaudacion.objects.filter(status=True, devengado=True).exclude(estado=3).order_by('-numero', '-fecha')
                for c in comprobantes:
                    comp = c.verifica_asiento_devengado_percibido()
                    if comp is not None:
                        lista_nocuadrados.append([fechaformatostr(str(c.fecha)[:10], 'DMA'), c.numero, c.depositante, c.tipocomprobanterecaudacion.nombre,  c.valortotal, comp['debedev'], comp['haberdev'], comp['debeper'], comp['haberper']])

                data['lista_nocuadrados'] = lista_nocuadrados

                template = get_template("rec_comprobantes/comprobantedescuadre.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'lista_nocuadrados': lista_nocuadrados})
            except Exception as ex:
                print("error")
                return JsonResponse({"result": "bad"})

        if action == 'listado_excel_descuadre':
            try:
                listacomprobantes = json.loads(request.POST['listacomprobantes'])
                __author__ = 'Unemi'
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'tesoreria'))
                title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                title2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre, vert distributed; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str=' "$" #,##0.00')
                fuentenormalneg2 = easyxf('font: name Verdana, bold on, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentefecha = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center', num_format_str='yyyy-mm-dd')

                wb = Workbook(encoding='utf-8')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=comprobantes_ingreso_descuadre_' + random.randint(1, 10000).__str__() + '.xls'
                nombre = "COMPROBANTESINGRESODESCUADRECUENTAS" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/tesoreria/" + nombre
                ws = wb.add_sheet('Comprobantes')
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                ws.write_merge(1, 1, 0, 10, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title2)
                ws.write_merge(2, 2, 0, 10, 'LISTADO DE COMPROBANTES DE INGRESO CON DESCUADRE DE TOTALES DE CUENTAS DE ASIENTOS DEVENGADO Y PERCIBIDO ', title2)
                row_num = 4
                ws.write_merge(row_num, row_num+1, 0, 0, "#", fuentecabecera)
                ws.write_merge(row_num, row_num+1, 1, 1, "Fecha", fuentecabecera)
                ws.write_merge(row_num, row_num+1, 2, 2, "Comprobante", fuentecabecera)
                ws.write_merge(row_num, row_num+1, 3, 3, "Depositante", fuentecabecera)
                ws.write_merge(row_num, row_num+1, 4, 4, "Tipo Comprobante", fuentecabecera)
                ws.write_merge(row_num, row_num+1, 5, 5, "Total Comprobante", fuentecabecera)
                ws.write_merge(row_num, row_num, 6, 7, "Devengado", fuentecabecera)
                ws.write_merge(row_num, row_num, 8, 9, "Percibido", fuentecabecera)
                row_num = 5
                ws.write_merge(row_num, row_num, 6, 6, "Debe", fuentecabecera)
                ws.write_merge(row_num, row_num, 7, 7, "Haber", fuentecabecera)
                ws.write_merge(row_num, row_num, 8, 8, "Debe", fuentecabecera)
                ws.write_merge(row_num, row_num, 9, 9, "Haber", fuentecabecera)

                ws.col(0).width = 1000
                ws.col(3).width = 9000
                ws.col(4).width = 7000
                for k in range(5, 10):
                    ws.col(k).width = 4000

                row_num = 6
                cont = 1
                for c in listacomprobantes:
                    ws.write(row_num, 0, cont, fuentenormalneg2)
                    ws.write(row_num, 1, c['fecha'], fuentefecha)
                    ws.write(row_num, 2, c['numero'], fuentenormal)
                    ws.write(row_num, 3, c['depositante'], fuentenormal)
                    ws.write(row_num, 4, c['tipocomprobante'], fuentenormal)
                    ws.write(row_num, 5, Decimal(c['valortotal']).quantize(Decimal('.01')), fuentemoneda)
                    ws.write(row_num, 6, Decimal(c['debedev']).quantize(Decimal('.01')), fuentemoneda)
                    ws.write(row_num, 7, Decimal(c['haberdev']).quantize(Decimal('.01')), fuentemoneda)
                    if Decimal(c['debeper']) != 0.00 and Decimal(c['haberper']) != 0.00:
                        ws.write(row_num, 8, Decimal(c['debeper']).quantize(Decimal('.01')), fuentemoneda)
                        ws.write(row_num, 9, Decimal(c['haberper']).quantize(Decimal('.01')), fuentemoneda)
                    else:
                        ws.write(row_num, 8, "", fuentenormal)
                        ws.write(row_num, 9, "", fuentenormal)

                    row_num += 1
                    cont += 1

                wb.save(filename)
                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                print("error")
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Agregar comprobante'
                    form = ComprobanteRecaudacionForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "rec_comprobantes/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar comprobante'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(comprobante)
                    transferencia = None
                    if comprobante.detalletransferenciagobierno_set.all().exists():
                        transferencia = comprobante.detalletransferenciagobierno_set.all()[0]
                    valordeposito = comprobante.papeletasdepositos_set.all().aggregate(valor=Sum('valor'))['valor']
                    valorotros = comprobante.detallenotacreditocomprobante_set.all().aggregate(valor=Sum('valor'))['valor']
                    form = ComprobanteRecaudacionForm(initial={'tipocomprobante': comprobante.tipocomprobanterecaudacion,
                                                               'puntoemision': comprobante.puntoemision,
                                                               'fechacomp': comprobante.fecha,
                                                               'fecha': comprobante.fecha,
                                                               'fechanotacredito': comprobante.fecha,
                                                               'cuentadepositopac': comprobante.cuentadeposito,
                                                               'cuentadepositocent': comprobante.cuentadeposito,
                                                               'depositante': comprobante.depositante,
                                                               'conceptotrans': transferencia.tipoconcepto if transferencia else None,
                                                               'concepto': comprobante.concepto,
                                                               'referencia': comprobante.referencia,
                                                               'montopresupuestado': transferencia.montopresupuestado if transferencia else None,
                                                               'diferencia': transferencia.diferencia if transferencia else None,
                                                               'numerocur': transferencia.numero if transferencia else None,
                                                               'cuota': transferencia.cuota if transferencia else None,
                                                               'valordeposito': valordeposito if valordeposito else 0,
                                                               'valorotros': comprobante.valortotal - (valorotros if valorotros else 0),
                                                               'valorfactura': (valorotros if valorotros else 0),
                                                               'valornotacredito': (valorotros if valorotros else 0),
                                                               'valortotal': comprobante.valortotal})
                    form.editar()
                    data['form'] = form
                    data['papeletas'] = comprobante.papeletasdepositos_set.all()
                    data['facturas'] = comprobante.factura_set.all().order_by('id')
                    data['recibos'] = comprobante.pagorecibocaja_set.all().order_by('id')
                    data['notacreditos'] = comprobante.detallenotacreditocomprobante_set.all()
                    return render(request, "rec_comprobantes/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'devengar':
                try:
                    data['title'] = u'Devengar comprobante'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(comprobante)
                    form = DevengarComprobanteForm(
                        initial={'fecha': comprobante.fecha,
                                 'depositante': comprobante.depositante,
                                 'conceptodevengado': comprobante.conceptodevengado,
                                 'curdevengado': comprobante.curdevengado,
                                 'valortotal': comprobante.valortotal})
                    form.bloquea_campo_total()
                    data['form'] = form
                    data['form2'] = PartidasDevengarForm(initial={'valor': comprobante.valortotal})
                    data['partidas'] = comprobante.resumencomprobantepartida_set.all()

                    ivas = comprobante.pago_set.filter(iva__gt=0)
                    totaliva = 0
                    if ivas:
                        totaliva = null_to_decimal(Decimal(comprobante.pago_set.filter(iva__gt=0).aggregate(totaliva=Sum('iva'))['totaliva']).quantize(Decimal('.01')), 2)
                    # data['ivas'] = ivas
                    data['totaliva'] = totaliva
                    data['cuentaiva'] = CuentaContable.objects.get(cuenta='213.81.07')
                    return render(request, "rec_comprobantes/devengar.html", data)
                except Exception as ex:
                    pass

            if action == 'editdevengado':
                try:
                    data['title'] = u'Devengar comprobante'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    data['diario'] = diario = Diario.objects.get(tipo=1, documento=comprobante.numero, status=True)
                    initial = model_to_dict(comprobante)
                    form = DevengarComprobanteForm(
                        initial={'fecha': comprobante.fecha,
                                 'depositante': comprobante.depositante,
                                 'conceptodevengado': comprobante.conceptodevengado,
                                 'curdevengado': comprobante.curdevengado,
                                 'valortotal': comprobante.valortotal})
                    form.bloquea_campo_total()
                    data['form'] = form
                    data['form2'] = PartidasDevengarForm(initial={'valor': comprobante.valortotal})
                    data['partidas'] = comprobante.resumencomprobantepartida_set.all()
                    data['cuentas'] = diario.detallediario_set.filter(naturaleza=1)

                    # data['ivas'] = comprobante.pago_set.filter(iva__gt=0)
                    totaliva = 0
                    ivas = comprobante.pago_set.filter(iva__gt=0)
                    if ivas:
                        totaliva = null_to_decimal(Decimal(comprobante.pago_set.filter(iva__gt=0).aggregate(totaliva=Sum('iva'))['totaliva']).quantize(Decimal('.01')), 2)

                    data['totaliva'] = totaliva
                    data['cuentaiva'] = CuentaContable.objects.get(cuenta='213.81.07')
                    return render(request, "rec_comprobantes/editdevengado.html", data)
                except Exception as ex:
                    pass

            if action == 'percibir':
                try:
                    data['title'] = u'Realizar percibido'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(comprobante)

                    form = PercibirComprobanteForm(
                        initial={'fechacomp': comprobante.fecha,
                                 'depositante': comprobante.depositante,
                                 'conceptopercibido': comprobante.conceptodevengado,
                                 'valortotal': comprobante.valortotal})

                    form.percibircomprobante()
                    diario = Diario.objects.get(tipo=1, documento=comprobante.numero)
                    data['cuentas'] = cuentas = diario.detallediario_set.filter(naturaleza=2)
                    totalcuentas = cuentas.aggregate(totalcuentas=Sum('valor'))['totalcuentas']
                    data['totalacreedora'] = totalcuentas
                    data['cuentaacreedora'] = CuentaContable.objects.get(id=CUENTA_ACREEDORA_ID)

                    comp = comprobante.verifica_asiento_devengado_percibido()
                    if comp is None:
                        descuadre = False
                    else:
                        descuadre = True
                        form.bloquearcomprobante()
                        data['totaldebe'] = comp['debedev']
                        data['totalhaber'] = comp['haberdev']

                    data['form'] = form
                    data['form2'] = PartidasDevengarForm()
                    data['form3'] = CurPercibirForm()
                    data['descuadredevengado'] = descuadre
                    return render(request, "rec_comprobantes/percibir.html", data)
                except Exception as ex:
                    pass

            if action == 'addpartida':
                try:
                    data['title'] = u'Agregar partida'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    form = ResumenComprobantePartidaForm()
                    form.adicionar(comprobante.fecha.year)
                    data['form'] = form
                    return render(request, "rec_comprobantes/addpartida.html", data)
                except Exception as ex:
                    pass

            if action == 'centrocosto':
                try:
                    data['title'] = u'Centro de Costos del Comprobante de Ingreso'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    data['costos'] = comprobante.centrocostotramiteingreso_set.all()
                    return render(request, "rec_comprobantes/centrocosto.html", data)
                except Exception as ex:
                    pass

            if action == 'asientos':
                try:
                    data['title'] = u'Asiento Contable del Comprobante de Ingreso'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    data['diarios'] = diario = Diario.objects.filter(documento=comprobante.numero, status=True)
                    data['curpercibido'] = comprobante.numerocurpercibido()
                    return render(request, "rec_comprobantes/asientos.html", data)
                except Exception as ex:
                    pass

            if action == 'addcosto':
                try:
                    data['title'] = u'Agregar Costo'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    data['form'] = CentroCostoForm()
                    return render(request, "rec_comprobantes/addcosto.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminarcosto':
                try:
                    data['title'] = u'Confirmar eliminar Detalle'
                    data['costo'] = costo = CentroCostoTramiteIngreso.objects.get(pk=int(request.GET['id']))
                    data['comprobante'] = costo.comprobante
                    return render(request, "rec_comprobantes/eliminarcosto.html", data)
                except:
                    pass

            if action == 'editpartida':
                try:
                    data['title'] = u'Editar partida'
                    data['partida'] = partida = ResumenComprobantePartida.objects.get(pk=int(request.GET['id']))
                    data['comprobante'] = partida.comprobanterecaudacion
                    form = ResumenComprobantePartidaForm(initial={'partida': partida.partida,
                                                                  'valor': partida.valor})
                    form.edit(partida, partida.comprobanterecaudacion.fecha.year)
                    data['form'] = form
                    return render(request, "rec_comprobantes/editpartida.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiarfecha':
                try:
                    data['title'] = u'Editar Fecha Comprobante'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.filter(pk=int(request.GET['id']))[0]
                    data['curpercibido'] = comprobante.comprobanterecaudacioncurpercibido_set.filter(status=True)
                    form = ComprobanteRecaudacionFechaForm(initial={'numero': comprobante.numero,
                                                                    'fecha': comprobante.fecha,
                                                                    #'fechabanco': comprobante.fechabanco,
                                                                    'fechaesigef': comprobante.fechaesigef})

                    if comprobante.fechaesigef:
                        data['validaesigef'] = True
                    else:
                        data['validaesigef'] = False
                        form.bloqueafechaesigef()

                    form.bloqueanumero()
                    data['form'] = form
                    return render(request, "rec_comprobantes/cambiarfecha.html", data)
                except Exception as ex:
                    pass

            if action == 'partidas':
                try:
                    data['title'] = u'Partidas del Comprobante'
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    data['partidas'] = comprobante.resumencomprobantepartida_set.all()
                    data['iva'] = comprobante.pago_set.filter(iva__gt=0).aggregate(valor=Sum('iva'))['valor']
                    return render(request, "rec_comprobantes/partidas.html", data)
                except Exception as ex:
                    pass

            if action == 'finalizarcomp':
                try:
                    data['title'] = u'Confirmar finalizar comprobante'
                    data['comprobante'] = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "rec_comprobantes/finalizar.html", data)
                except:
                    pass

            if action == 'confirmarpartida':
                try:
                    data['title'] = u'Confirmar partidas de comprobante'
                    data['comprobante'] = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "rec_comprobantes/confirmar.html", data)
                except:
                    pass

            if action == 'eliminarcomprobante':
                try:
                    data['title'] = u'Confirmar eliminar Comprobante de Ingresos'
                    data['comprobante'] = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "rec_comprobantes/eliminar.html", data)
                except:
                    pass


            if action == 'deletepartida':
                try:
                    data['title'] = u'Confirmar eliminar Partida Comprobante de Ingresos'
                    data['partida'] = partida = ResumenComprobantePartida.objects.get(pk=int(request.GET['id']))
                    data['comprobante'] = partida.comprobanterecaudacion
                    return render(request, "rec_comprobantes/eliminarpartida.html", data)
                except:
                    pass

            if action == 'detalle_comprobante':
                try:
                    data['comprobante'] = comprobante = ComprobanteRecaudacion.objects.get(pk=int(request.GET['id']))
                    data['facturas'] = comprobante.factura_set.all()
                    data['recibos'] = comprobante.pagorecibocaja_set.all().order_by('id')
                    data['reciboscaja'] = comprobante.recibocaja_set.all().order_by('id')
                    data['papeletas'] = comprobante.papeletasdepositos_set.all()
                    data['transfer'] = comprobante.detalletransferenciagobierno_set.all()
                    data['partidas'] = comprobante.resumencomprobantepartida_set.all()
                    data['notas'] = comprobante.detallenotacreditocomprobante_set.all()
                    template = get_template("rec_comprobantes/detalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'buscarconceptofactura':
                try:
                    texto = ''
                    tipo = request.GET['tipodoc']
                    if tipo == 'REC2':
                        recibo = ReciboCaja.objects.get(status=True,id=request.GET['id'])
                        referencia = "RECIBO DE CAJA # %s" % recibo.numerocompleto
                        texto = recibo.concepto
                    else:
                        factura = Factura.objects.get(status=True,id=request.GET['id'])
                        referencia = "FACTURA # %s"%str(factura.numerocompleto)
                        for pago in factura.pagos.all():
                            rubro = pago.rubro
                            texto +=rubro.__str__()+', '
                    return JsonResponse({"result": True, "texto":texto,"referencia":referencia})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. Detalle: %s"%(ex.__str__())})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Comprobantes'
            ids = None
            search = None
            descuadre = False
            url_vars = ''
            comprobantes = ComprobanteRecaudacion.objects.filter(status=True, devengado=True).order_by('-numero', '-fecha')
            # for c in comprobantes:
            #     if c.estado != 3:
            #         comp = c.verifica_asiento_devengado_percibido()
            #         if comp is not None:
            #             descuadre = True
            #             break

            descuadre = False

            if 's' in request.GET:
                search = request.GET.get('s','')
                url_vars += "&s=%s" % search

                comprobantes = ComprobanteRecaudacion.objects.filter(Q(depositante__icontains=search) |
                                                                     Q(numero__icontains=search) |
                                                                     Q(nocur__icontains=search) |
                                                                     Q(tipocomprobanterecaudacion__nombre__icontains=search) |
                                                                     Q(valortotal__icontains=search) |
                                                                     Q(fecha__icontains=search), status=True).distinct().order_by('-numero', '-fecha')
            elif 'id' in request.GET:
                ids = request.GET['id']
                url_vars += "&ids=%s" % ids
                comprobantes = ComprobanteRecaudacion.objects.filter(id=ids, status=True).order_by('-numero', '-fecha')
            else:
                comprobantes = ComprobanteRecaudacion.objects.filter(status=True).order_by('-numero', '-fecha')

            estadocomprobante = 0
            if 'estadocomprobante' in request.GET:
                estadocomprobante = int(request.GET['estadocomprobante'])
                url_vars += "&estadocomprobante=%s" % estadocomprobante

                if estadocomprobante > 0:
                    if estadocomprobante == 1:
                        comprobantes = comprobantes.filter(numero__gt=0)
                    else:
                        comprobantes = comprobantes.filter(numero=0)


            paging = MiPaginador(comprobantes, 25)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                else:
                    p = paginasesion
                try:
                    page = paging.page(p)
                except:
                    p = 1
                page = paging.page(p)
            except:
                page = paging.page(p)
            request.session['paginador'] = p
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['ids'] = ids if ids else None
            data['page'] = page
            data['comprobantes'] = page.object_list
            data['estadocomprobante'] = estadocomprobante
            data['reporte_0'] = obtener_reporte('comprobante_recaudaciones')
            data['reporte_6'] = obtener_reporte('comprobante_recaudaciones_2')
            data['reporte_1'] = obtener_reporte('comprobante_recaudaciones_devengado')
            data['reporte_2'] = obtener_reporte('comprobante_ingreso_cont')
            data['reporte_7'] = obtener_reporte('comprobante_ingreso_perc')
            data['reporte_3'] = obtener_reporte('resumen_comprobante_presupuesto')
            data['reporte_4'] = obtener_reporte('resumen_comprobante_presupuesto_ind')
            data['reporte_5'] = obtener_reporte('resumen_comprobante_presupuesto_ex')
            data['search'] = search if search else ""
            data['url_vars'] = url_vars
            data['hoy'] = datetime.now().date()
            data['descuadre'] = descuadre
            data['estadocomprobante'] = estadocomprobante
            try:
                return render(request, "rec_comprobantes/view.html", data)
            except Exception as ex:
                pass