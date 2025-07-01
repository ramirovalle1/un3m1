# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.commonviews import anio_ejercicio, secuencia_egreso
from sagest.forms import DocumentosComprobanteRecaudacionForm
from sagest.models import PuntoVenta, ResumenComprobantesEgreso, ComprobanteEgreso
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    lugarrecaudacion = PuntoVenta.objects.all()[0]
    perfilprincipal = request.session['perfilprincipal']
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = DocumentosComprobanteRecaudacionForm(request.POST)
                if f.is_valid():
                    comprobantes = json.loads(request.POST['lista_items1'])
                    if len(comprobantes) == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un comprobante."})
                    documento = ResumenComprobantesEgreso(fecha=f.cleaned_data['fecha'],
                                                      descripcion=f.cleaned_data['descripcion'],
                                                      estado=1)
                    documento.save(request)
                    for d in comprobantes:
                        comprobante = ComprobanteEgreso.objects.get(pk=int(d['id']))
                        documento.comprobantes.add(comprobante)
                    log(u'Adiciono nuevo documento: %s' % documento, request, "add")
                    return JsonResponse({"result": "ok", 'id': documento.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'finalizarcomp':
            try:
                comprobante = ResumenComprobantesEgreso.objects.get(pk=int(request.POST['id']))
                comprobante.estado = 2
                comprobante.save(request)
                secuencia = secuencia_egreso(request)
                if not comprobante.numero:
                    secuencia.resumenegreso += 1
                    secuencia.save(request)
                    comprobante.numero = secuencia.resumenegreso
                comprobante.save(request)
                log(u'Finalizar documento: %s' % comprobante, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = DocumentosComprobanteRecaudacionForm(request.POST)
                if f.is_valid():
                    comprobantesrec = json.loads(request.POST['lista_items1'])
                    if len(comprobantesrec) == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un comprobante."})
                    documento = ResumenComprobantesEgreso.objects.get(pk=int(request.POST['id']))
                    for companterior in documento.comprobantes.all():
                        documento.comprobantes.remove(companterior)
                    documento.fecha = f.cleaned_data['fecha']
                    documento.descripcion = f.cleaned_data['descripcion']
                    documento.save(request)
                    for d in comprobantesrec:
                        comprobante = ComprobanteEgreso.objects.get(pk=int(d['id']))
                        documento.comprobantes.add(comprobante)
                    log(u'Edito documento: %s' % documento, request, "add")
                    return JsonResponse({"result": "ok", 'id': documento.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_comprobante':
            try:
                data['comprobante'] = comprobante = ResumenComprobantesEgreso.objects.get(pk=int(request.POST['id']))
                data['detalles'] = comprobante.comprobantes.all()
                template = get_template("fin_resumencomprobantes/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminar':
            try:
                comprobante = ResumenComprobantesEgreso.objects.get(pk=int(request.POST['id']))
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
                    data['title'] = u'Agregar documento'
                    form = DocumentosComprobanteRecaudacionForm()
                    data['comprobantes'] = ComprobanteEgreso.objects.filter(resumencomprobantesegreso__isnull=True).order_by('numero')
                    data['form'] = form
                    return render(request, "fin_resumencomprobantes/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar documento'
                    data['comprobante'] = comprobante = ResumenComprobantesEgreso.objects.get(pk=int(request.GET['id']))
                    lista1 = []
                    lista2 = []
                    for comprobanterec in ComprobanteEgreso.objects.filter(resumencomprobantesegreso__isnull=True).order_by('numero'):
                        lista1.append(comprobanterec.id)
                    for micomporbante in comprobante.comprobantes.all():
                        lista2.append(micomporbante.id)
                    data['comprobantes'] = ComprobanteEgreso.objects.filter(Q(id__in=lista1) | Q(id__in=lista2)).order_by('numero')
                    initial = model_to_dict(comprobante)
                    form = DocumentosComprobanteRecaudacionForm(initial=initial)
                    data['form'] = form
                    return render(request, "fin_resumencomprobantes/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'finalizarcomp':
                try:
                    data['title'] = u'Confirmar finalizar comprobante'
                    data['comprobante'] = ResumenComprobantesEgreso.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_resumencomprobantes/finalizar.html", data)
                except:
                    pass

            if action == 'eliminar':
                try:
                    data['title'] = u'Confirmar eliminar Documento'
                    data['comprobante'] = ResumenComprobantesEgreso.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_resumencomprobantes/eliminar.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Resumen de Comprobantes de Egreso'
            ids = None
            search = None
            if 's' in request.GET:
                search = request.GET['s']
                documentos = ResumenComprobantesEgreso.objects.filter(Q(numero__icontains=search) |
                                                                     Q(fecha__icontains=search)).distinct().order_by('-numero', '-fecha')
            elif 'id' in request.GET:
                ids = request.GET['id']
                documentos = ResumenComprobantesEgreso.objects.filter(id=ids).order_by('-numero', '-fecha')
            else:
                documentos = ResumenComprobantesEgreso.objects.all().order_by('-numero', '-fecha')
            paging = MiPaginador(documentos, 25)
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
            data['documentos'] = page.object_list
            data['reporte_0'] = obtener_reporte('resumen_comprobante_egreso')
            data['search'] = search if search else ""
            try:
                return render(request, "fin_resumencomprobantes/view.html", data)
            except Exception as ex:
                pass