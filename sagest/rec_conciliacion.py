# -*- coding: UTF-8 -*-
import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.commonviews import anio_ejercicio
from sagest.forms import ConciliacionForm #,BancoForm
from sagest.models import ComprobanteRecaudacion, PapeletasDepositos, \
    DetalleNotaCreditoComprobante, CuentaBanco, DetalleTransferenciaGobierno, \
    DetalleConciliacion, TipoMovimientoConciliacion, SaldoCuentaBanco, DetalleConciliacionTransferencia, Banco
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, convertir_fecha


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
                f = ConciliacionForm(request.POST)
                if f.is_valid():
                    tipo = f.cleaned_data['tipomovimiento']
                    conciliacion = None
                    cuenta = CuentaBanco.objects.get(pk=int(request.POST['cuenta']))
                    fecha = f.cleaned_data['fecha']
                    valor = Decimal(request.POST['valortotal'])
                    if fecha > datetime.now().date():
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha no puede ser mayor a la actual."})
                    if SaldoCuentaBanco.objects.filter(fecha=fecha, estado=2, cuentabanco=cuenta).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El saldo para esa fecha ya fue cerrado."})
                    ultimafecha = SaldoCuentaBanco.objects.filter(estado=1, cuentabanco=cuenta).order_by('-fecha')[0].fecha
                    if fecha > ultimafecha or fecha < ultimafecha:
                        return JsonResponse({"result": "bad", "mensaje": u"Está tratando de adicionar fuera de la fecha establecida."})
                    if not tipo.id == 4 and not tipo.id == 5:
                        datos = json.loads(request.POST['lista_items1'])
                        if tipo.id == 1:
                            for p in datos:
                                papeleta = PapeletasDepositos.objects.get(id=int(p['id']))
                                conciliacion = DetalleConciliacion(tipo=tipo,
                                                                   fecha=fecha,
                                                                   referencia=papeleta.referencia,
                                                                   cuentabanco=cuenta,
                                                                   valor=papeleta.valor)
                                conciliacion.save(request)
                                papeleta.conciliacionbancaria = conciliacion
                                papeleta.save(request)
                            cuenta.saldo += conciliacion.valor
                            cuenta.save(request)
                        if tipo.id == 2:
                            for p in datos:
                                trans = DetalleTransferenciaGobierno.objects.get(id=int(p['id']))
                                conciliacion = DetalleConciliacion(tipo=tipo,
                                                                   fecha=fecha,
                                                                   referencia=trans.numero,
                                                                   cuentabanco=cuenta,
                                                                   valor=trans.montorecibido)
                                conciliacion.save(request)
                                trans.conciliacionbancaria = conciliacion
                                trans.save(request)
                            cuenta.saldo += conciliacion.valor
                            cuenta.save(request)
                        if tipo.id == 3:
                            for p in datos:
                                tipoc = int(p['tipo'])
                                if not tipoc:
                                    nota = DetalleNotaCreditoComprobante.objects.get(id=int(p['id']))
                                    conciliacion = DetalleConciliacion(tipo=tipo,
                                                                       fecha=fecha,
                                                                       referencia=str(nota.numero),
                                                                       cuentabanco=cuenta,
                                                                       valor=nota.valor)
                                    conciliacion.save(request)
                                    nota.conciliacionbancaria = conciliacion
                                    nota.save(request)
                                elif tipoc == 1:
                                    nota = ComprobanteRecaudacion.objects.get(id=int(p['id']))
                                    conciliacion = DetalleConciliacion(tipo=tipo,
                                                                       fecha=fecha,
                                                                       referencia=str(nota.numero),
                                                                       cuentabanco=cuenta,
                                                                       valor=nota.valortotal)
                                    conciliacion.save(request)
                                    nota.conciliacionbancaria = conciliacion
                                    nota.save(request)
                                else:
                                    nota = DetalleConciliacionTransferencia.objects.get(id=int(p['id']))
                                    conciliacion = DetalleConciliacion(tipo=tipo,
                                                                       fecha=fecha,
                                                                       referencia=nota.referencia,
                                                                       cuentabanco=cuenta,
                                                                       valor=nota.valor)
                                    conciliacion.save(request)
                                    nota.conciliacionbancaria = conciliacion
                                    nota.save(request)
                            cuenta.saldo += conciliacion.valor
                            cuenta.save(request)
                    else:
                        conciliacion = DetalleConciliacion(tipo=tipo,
                                                           fecha=fecha,
                                                           referencia=f.cleaned_data['referencia'],
                                                           cuentabanco=cuenta,
                                                           valor=Decimal(f.cleaned_data['valor']))
                        conciliacion.save(request)
                    if tipo.id == 4:
                        conciliacion.observacion = f.cleaned_data['observacion']
                        conciliacion.save(request)
                        cuenta.saldo -= conciliacion.valor
                        cuenta.save(request)
                    if tipo.id == 5:
                        conciliacion.cuentabancoegreso = f.cleaned_data['cuentabanco']
                        conciliacion.save(request)
                        cuenta.saldo -= conciliacion.valor
                        cuenta.save(request)
                        detalle = DetalleConciliacionTransferencia(fecha=conciliacion.fecha,
                                                                   cuentabanco=conciliacion.cuentabancoegreso,
                                                                   valor=conciliacion.valor,
                                                                   referencia=conciliacion.referencia)
                        detalle.save(request)
                    saldos = cuenta.saldo_cuenta(fecha)
                    saldos.actualizar_conciliacion()
                    log(u'Adiciono nueva conciliacion: %s' % conciliacion, request, "add")
                    return JsonResponse({"result": "ok", 'id': conciliacion.id, 'cuentaid': cuenta.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = ConciliacionForm(request.POST)
                if f.is_valid():
                    conciliacion = DetalleConciliacion.objects.get(pk=int(request.POST['id']))
                    tipo = conciliacion.tipo
                    cuenta = conciliacion.cuentabanco
                    fecha = conciliacion.fecha
                    if tipo.id == 4:
                        conciliacion.observacion = f.cleaned_data['observacion']
                        conciliacion.referencia = f.cleaned_data['referencia']
                        conciliacion.valor = Decimal(f.cleaned_data['valor'])
                        conciliacion.save(request)
                    if tipo.id == 5:
                        conciliacion.cuentabancoegreso = f.cleaned_data['cuentabanco']
                        conciliacion.referencia = f.cleaned_data['referencia']
                        conciliacion.valor = Decimal(f.cleaned_data['valor'])
                        conciliacion.save(request)
                    log(u'Edito conciliacion: %s' % conciliacion, request, "add")
                    return JsonResponse({"result": "ok", 'id': conciliacion.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_comprobante':
            try:
                data['conciliacion'] = conciliacion = DetalleConciliacion.objects.get(pk=int(request.POST['id']))
                if SaldoCuentaBanco.objects.filter(cuentabanco=conciliacion.cuentabanco, fecha=conciliacion.fecha).exists():
                    data['saldo_cuenta'] = SaldoCuentaBanco.objects.get(cuentabanco=conciliacion.cuentabanco, fecha=conciliacion.fecha)
                else:
                    saldo = conciliacion.cuentabanco.saldo_cuenta(conciliacion.fecha)
                    saldo.actualizar_conciliacion()
                    data['saldo_cuenta'] = saldo
                template = get_template("rec_conciliacion/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'datos_conciliacion':
            try:
                data = {}
                data['tipo'] = tipo = TipoMovimientoConciliacion.objects.get(pk=int(request.POST['tipo']))
                data['cuenta'] = cuenta = CuentaBanco.objects.get(pk=int(request.POST['cuenta']))
                fecha = convertir_fecha(request.POST['fecha'])
                if tipo.id == 1:
                    data['detalles'] = papeletas = PapeletasDepositos.objects.filter(conciliacionbancaria__isnull=True, comprobanterecaudacion__fecha=fecha, comprobanterecaudacion__cuentadeposito=cuenta)
                elif tipo.id == 2:
                    data['detalles'] = transferencia = DetalleTransferenciaGobierno.objects.filter(conciliacionbancaria__isnull=True, comprobanterecaudacion__fecha=fecha, comprobanterecaudacion__cuentadeposito=cuenta)
                elif tipo.id == 3:
                    data['detalles'] = DetalleNotaCreditoComprobante.objects.filter(conciliacionbancaria__isnull=True, comprobanterecaudacion__fecha=fecha, comprobanterecaudacion__cuentadeposito=cuenta)
                    data['detalles2'] = ComprobanteRecaudacion.objects.filter(tipocomprobanterecaudacion__id=4, conciliacionbancaria__isnull=True, fecha=fecha, detallenotacreditocomprobante__isnull=True, cuentadeposito=cuenta)
                    data['detalles3'] = DetalleConciliacionTransferencia.objects.filter(conciliacionbancaria__isnull=True, fecha=fecha, cuentabanco=cuenta)
                template = get_template("rec_conciliacion/datosventanillanotas.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'eliminar':
            try:
                conciliacion = DetalleConciliacion.objects.get(pk=int(request.POST['id']))
                conciliacion.papeletasdepositos_set.update(conciliacionbancaria=None)
                conciliacion.detallenotacreditocomprobante_set.update(conciliacionbancaria=None)
                conciliacion.detalletransferenciagobierno_set.update(conciliacionbancaria=None)
                conciliacion.detalleconciliaciontransferencia_set.update(conciliacionbancaria=None)
                cuenta = conciliacion.cuentabanco
                fecha = conciliacion.fecha
                cuenta.saldo -= conciliacion.valor
                cuenta.save(request)
                conciliacion.delete()
                saldos = cuenta.saldo_cuenta(fecha)
                saldos.actualizar_conciliacion()
                cuenta.saldo -= conciliacion.valor
                cuenta.save(request)
                saldos = cuenta.saldo_cuenta(fecha)
                saldos.actualizar_conciliacion()
                log(u'Elimino conciliacion: %s' % conciliacion, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'finalizar':
            try:
                saldo = SaldoCuentaBanco.objects.get(pk=int(request.POST['id']))
                saldo.estado = 2
                cuenta = saldo.cuentabanco
                cuenta.saldo = saldo.saldofinal
                cuenta.save(request)
                saldo.save(request)
                saldo.actualizar_conciliacion()
                nuevosaldo = SaldoCuentaBanco(cuentabanco=cuenta,
                                              fecha=(saldo.fecha + timedelta(days=1)))
                nuevosaldo.save(request)
                nuevosaldo.actualizar_conciliacion()
                log(u'Finalizar saldo: %s' % saldo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})



        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nueva Conciliación'
                    data['cuenta'] = cuenta = CuentaBanco.objects.get(pk=int(request.GET['cuentaid']))
                    fecha = request.GET['fecha']
                    form = ConciliacionForm(initial={'fecha': fecha})
                    form.adicionar(cuenta)
                    data['form'] = form
                    return render(request, "rec_conciliacion/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar conciliacion'
                    data['conciliacion'] = conciliacion = DetalleConciliacion.objects.get(pk=int(request.GET['id']))
                    data['cuenta'] = conciliacion.cuentabanco
                    form = ConciliacionForm(initial={'tipomovimiento': conciliacion.tipo,
                                                     'observacion': conciliacion.observacion,
                                                     'referencia': conciliacion.referencia,
                                                     'cuentabanco': conciliacion.cuentabanco,
                                                     'valor': conciliacion.valor,
                                                     'fecha': conciliacion.fecha})
                    form.editar()
                    data['form'] = form
                    data['papeletas'] = conciliacion.papeletasdepositos_set.all()
                    data['transfer'] = conciliacion.detalletransferenciagobierno_set.all()
                    data['notacreditos'] = conciliacion.detallenotacreditocomprobante_set.all()
                    return render(request, "rec_conciliacion/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminar':
                try:
                    data['title'] = u'Confirmar eliminar Conciliación'
                    data['conciliacion'] = DetalleConciliacion.objects.get(pk=int(request.GET['id']))
                    data['cuenta'] = CuentaBanco.objects.get(pk=int(request.GET['cuentaid']))
                    return render(request, "rec_conciliacion/eliminar.html", data)
                except:
                    pass



            if action == 'finalizar':
                try:
                    data['title'] = u'Confirmar finalizar saldo'
                    data['saldo'] = saldo = SaldoCuentaBanco.objects.get(pk=int(request.GET['id']))
                    data['cuenta'] = saldo.cuentabanco
                    return render(request, "rec_conciliacion/finalizar.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Concilicaciones Bancarias'
            ids = None
            search = None
            cuenta = None
            data['cuenta_banco'] = cuentas = CuentaBanco.objects.all()
            if 'cuentaid' in request.GET:
                data['cuenta'] = cuenta = CuentaBanco.objects.get(pk=int(request.GET['cuentaid']))
            else:
                data['cuenta'] = cuenta = cuentas[0]
            if 's' in request.GET:
                search = request.GET['s']
                conciliaciones = DetalleConciliacion.objects.filter(Q(tipo__nombre__icontains=search) |
                                                                    Q(referencia__icontains=search), cuentabanco=cuenta).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                conciliaciones = DetalleConciliacion.objects.filter(id=ids, cuentabanco=cuenta)
            else:
                conciliaciones = DetalleConciliacion.objects.filter(cuentabanco=cuenta)
            paging = MiPaginador(conciliaciones, 25)
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
                except Exception as ex:
                    p = 1
                page = paging.page(p)
            except Exception as ex:
                page = paging.page(p)
            request.session['paginador'] = p
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['ids'] = ids if ids else None
            data['page'] = page
            data['conciliaciones'] = page.object_list
            data['reporte_0'] = obtener_reporte('comprobante_recaudaciones')
            data['reporte_1'] = obtener_reporte('comprobante_recaudaciones_devengado')
            if SaldoCuentaBanco.objects.filter(cuentabanco=cuenta).exists():
                data['saldo_cuenta'] = ultimo = SaldoCuentaBanco.objects.filter(cuentabanco=cuenta).order_by('-fecha')[0]
            else:
                data['saldo_cuenta'] = ultimo = cuenta.saldo_cuenta(datetime.now().date())
            data['depositos_pendiente'] = PapeletasDepositos.objects.filter(conciliacionbancaria__isnull=True).count()
            data['transfer_pendiente'] = DetalleTransferenciaGobierno.objects.filter(conciliacionbancaria__isnull=True).count()
            data['notac_pendiente'] = (DetalleNotaCreditoComprobante.objects.filter(conciliacionbancaria__isnull=True).count() + ComprobanteRecaudacion.objects.filter(tipocomprobanterecaudacion__id=4, conciliacionbancaria__isnull=True).count() + DetalleConciliacionTransferencia.objects.filter(conciliacionbancaria__isnull=True).count())
            data['search'] = search if search else ""
            try:
                return render(request, "rec_conciliacion/view.html", data)
            except Exception as ex:
                pass