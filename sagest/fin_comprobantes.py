# -*- coding: UTF-8 -*-
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import last_access, secure_module
from sagest.commonviews import secuencia_egreso
from sagest.forms import CentroCostoForm, TraspasoTramiteForm, ComprobanteEgresoForm
from sagest.models import TramitePago, DocumentosTramitePago, BeneficiariTramitePago, CentroCostoComprobantePago, ComprobanteEgreso
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log
from sga.models import Persona


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
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ComprobanteEgresoForm(request.POST)
                if f.is_valid():
                    facturas = json.loads(request.POST['lista_items1'])
                    docs = Decimal(request.POST['valdoc'])
                    riva = Decimal(request.POST['retiva'])
                    rf = Decimal(request.POST['retfuente'])
                    # beneficiario = BeneficiariTramitePago.objects.get(beneficiario=f.cleaned_data['beneficiario'])
                    beneficiario = f.cleaned_data['beneficiario']
                    comprobante = ComprobanteEgreso(beneficiario=beneficiario.beneficiario.nombre_completo(),
                                                    identificacion=f.cleaned_data['identificacion'],
                                                    fecha=f.cleaned_data['fecha'],
                                                    valordocumentos=docs,
                                                    totalretenidoiva=riva,
                                                    totalretenidofuente=rf,
                                                    totalanticipos=f.cleaned_data['totalanticipos'],
                                                    totalotros=f.cleaned_data['totalotros'],
                                                    totalmultas=f.cleaned_data['totalmultas'],
                                                    totalpagar=f.cleaned_data['totalpagar'],
                                                    concepto=f.cleaned_data['concepto'],
                                                    observacion=f.cleaned_data['observacion'])
                    comprobante.save(request)
                    beneficiario.comprobante = comprobante
                    beneficiario.save(request)
                    for d in facturas:
                        factura = DocumentosTramitePago.objects.get(pk=int(d['id']))
                        factura.comprobante = comprobante
                        factura.beneficiario = beneficiario
                        factura.save(request)
                    log(u'Adiciono nuevo comprobante de egreso: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok", 'id': comprobante.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = ComprobanteEgresoForm(request.POST)
                if f.is_valid():
                    facturas = json.loads(request.POST['lista_items1'])
                    comprobante = ComprobanteEgreso.objects.get(pk=int(request.POST['id']))
                    beneficiario = comprobante.beneficiaritramitepago_set.all()[0]
                    comprobante.fecha=f.cleaned_data['fecha']
                    comprobante.totalanticipos=f.cleaned_data['totalanticipos']
                    comprobante.totalotros=f.cleaned_data['totalotros']
                    comprobante.totalmultas=f.cleaned_data['totalmultas']
                    comprobante.totalpagar=f.cleaned_data['totalpagar']
                    comprobante.concepto=f.cleaned_data['concepto']
                    comprobante.observacion=f.cleaned_data['observacion']
                    comprobante.save(request)
                    for fact in DocumentosTramitePago.objects.filter(comprobante=comprobante,beneficiario=beneficiario).exclude(pk__in=[int(d['id']) for d in facturas]):
                        fact.comprobante = None
                        fact.beneficiario = None
                        fact.save(request)
                        log(u'Elimino enlace de documento de tramite de pago con comprobando y beneficiario: %s [%s]' % (fact,fact.id), request, "del")
                    for d in facturas:
                        factura = DocumentosTramitePago.objects.get(pk=int(d['id']))
                        factura.comprobante = comprobante
                        factura.beneficiario = beneficiario
                        factura.save(request)
                    log(u'Adiciono nuevo comprobante de egreso: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok", 'id': comprobante.id})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'tramite_benef':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                lista = []
                valdoc = 0
                ret = 0
                for responsable in tramite.beneficiaritramitepago_set.filter(comprobante__isnull=True):
                    if [responsable.id, responsable.beneficiario.nombre_completo_inverso()] not in lista:
                        lista.append([responsable.id, responsable.beneficiario.nombre_completo_inverso()])
                data = {}
                data['detalles'] = tramite.documentostramitepago_set.filter(comprobante__isnull=True)
                template = get_template("fin_comprobantes/documentos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'lista': lista, 'concepto': tramite.motivo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'tramite_benef_edit':
            try:
                tramite = TramitePago.objects.get(pk=int(request.POST['id']))
                data = {}
                data['detalles'] = tramite.documentostramitepago_set.all()
                detalles_utilizado = list(tramite.documentostramitepago_set.values_list('id').filter(comprobante__isnull=False))
                template = get_template("fin_comprobantes/documentos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content,'lista':detalles_utilizado})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'addcosto':
            try:
                f = CentroCostoForm(request.POST)
                comprobante = ComprobanteEgreso.objects.get(pk=int(request.POST['id']))
                if f.is_valid():
                    valoractual = Decimal(comprobante.total_costos()) + Decimal(f.cleaned_data['total'])
                    if valoractual > comprobante.totalpagar:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor supera el total del Comprobante."})
                    costo = CentroCostoComprobantePago(comprobante=comprobante,
                                                   centrocosto_id=f.cleaned_data['detalle'],
                                                   valor=Decimal(f.cleaned_data['total']))
                    costo.save(request)
                    costo.centrocosto.actualiza_saldo_egreso(comprobante.fecha.year)
                    log(u'Adiciono nuevo costo al comprobante: %s' % comprobante, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarcosto':
            try:
                costo = CentroCostoComprobantePago.objects.get(pk=int(request.POST['id']))
                centrocosto = costo.centrocosto
                comprobante = costo.comprobante
                costo.delete()
                centrocosto.actualiza_saldo_egreso(comprobante.fecha.year)
                log(u'Elimino costo: %s' % costo, request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'id_benef':
            try:
                beneficiario = Persona.objects.get(pk=int(request.POST['id']))
                ide = beneficiario.identificacion()
                return JsonResponse({"result": "ok", "ide": ide})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'finalizarcomp':
            try:
                comprobante = ComprobanteEgreso.objects.get(pk=int(request.POST['id']))
                comprobante.estado = 2
                comprobante.save(request)
                secuencia = secuencia_egreso(request)
                if not comprobante.numero:
                    secuencia.resumenegreso += 1
                    secuencia.save(request)
                    comprobante.numero = secuencia.resumenegreso
                comprobante.save(request)
                log(u'Finalizar comprobante: %s' % comprobante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarcomprobante':
            try:
                comprobante = ComprobanteEgreso.objects.get(pk=int(request.POST['id']))
                comprobante.documentostramitepago_set.update(comprobante=None)
                comprobante.beneficiaritramitepago_set.update(comprobante=None)
                comprobante.delete()
                log(u'Elimino comprobante: %s' % comprobante, request, "delete")
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
                    data['title'] = u'Agregar Comprobante'
                    form = ComprobanteEgresoForm()
                    # form.adicionar()
                    data['form'] = form
                    return render(request, "fin_comprobantes/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar comprobante'
                    data['comprobante'] = comprobante = ComprobanteEgreso.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(comprobante)
                    beneficiario=comprobante.beneficiaritramitepago_set.all()[0]
                    form = ComprobanteEgresoForm(initial={'tramite':beneficiario.tramitepago,
                                                          'beneficiario':beneficiario.id,
                                                          'fecha':comprobante.fecha,
                                                          'valordocumentos':comprobante.valordocumentos,
                                                          'concepto':comprobante.concepto,
                                                          'identificacion':beneficiario.beneficiario.identificacion(),
                                                          'totalretenidoiva':comprobante.totalretenidoiva,
                                                          'totalotros':comprobante.totalotros,
                                                          'totalanticipos':comprobante.totalanticipos,
                                                          'totalmultas':comprobante.totalmultas,
                                                          'totalpagar':comprobante.totalpagar,
                                                          'observacion':comprobante.observacion})
                    form.editar()
                    data['tramite_id']=beneficiario.tramitepago.id
                    data['form'] = form
                    data['documentos'] = comprobante.documentostramitepago_set.all()
                    return render(request, "fin_comprobantes/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'finalizarcomp':
                try:
                    data['title'] = u'Confirmar finalizar comprobante'
                    data['comprobante'] = ComprobanteEgreso.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_comprobantes/finalizar.html", data)
                except:
                    pass

            if action == 'eliminarcomprobante':
                try:
                    data['title'] = u'Confirmar eliminar Comprobante de Egresos'
                    data['comprobante'] = ComprobanteEgreso.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_comprobantes/eliminar.html", data)
                except:
                    pass

            if action == 'centrocosto':
                try:
                    data['title'] = u'Centro de Costos del Comprobante'
                    data['comprobante'] = comprobante = ComprobanteEgreso.objects.get(pk=int(request.GET['id']))
                    data['costos'] = comprobante.centrocostocomprobantepago_set.all()
                    return render(request, "fin_comprobantes/centrocosto.html", data)
                except Exception as ex:
                    pass

            if action == 'addcosto':
                try:
                    data['title'] = u'Agregar Costo al Comprobante'
                    data['comprobante'] = comprobante = ComprobanteEgreso.objects.get(pk=int(request.GET['id']))
                    data['form'] = CentroCostoForm()
                    return render(request, "fin_comprobantes/addcosto.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminarcosto':
                try:
                    data['title'] = u'Confirmar eliminar Detalle'
                    data['costo'] = costo = CentroCostoComprobantePago.objects.get(pk=int(request.GET['id']))
                    data['comprobante'] = costo.comprobante
                    return render(request, "fin_comprobantes/eliminarcosto.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Comprobantes de Egresos'
            ids = None
            search = None
            if 's' in request.GET:
                search = request.GET['s']
                comprobantes = ComprobanteEgreso.objects.filter(Q(beneficiario__icontains=search, status=True) |
                                                     Q(fecha__icontains=search, status=True) |
                                                     Q(numero__icontains=search, status=True) |
                                                     Q(identificacion__icontains=search, status=True)).distinct().order_by('-fecha')
            elif 'id' in request.GET:
                ids = request.GET['id']
                comprobantes = ComprobanteEgreso.objects.filter(id=ids, status=True).order_by('-fecha')
            else:
                comprobantes = ComprobanteEgreso.objects.filter(status=True).order_by('-fecha')
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
            data['reporte_0'] = obtener_reporte('comprobantes_egresos')
            data['form'] = TraspasoTramiteForm()
            data['mi_departamento'] = persona.mi_departamento()
            data['search'] = search if search else ""
            return render(request, "fin_comprobantes/view.html", data)