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
from sagest.commonviews import secuencia_recaudacion, anio_ejercicio
from sagest.forms import DocumentosComprobanteRecaudacionForm
from sagest.models import ComprobanteRecaudacion, \
    PuntoVenta, ImpresionComprobantes, AnioEjercicio
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log
from sga.models import MESES_CHOICES


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
                    documento = ImpresionComprobantes(fecha=f.cleaned_data['fecha'],
                                                      descripcion=f.cleaned_data['descripcion'],
                                                      estado=1,
                                                      anioejercicio=anio_ejercicio())
                    documento.save(request)
                    for d in comprobantes:
                        comprobante = ComprobanteRecaudacion.objects.get(pk=int(d['id']))
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
                comprobante = ImpresionComprobantes.objects.get(pk=int(request.POST['id']))
                comprobante.estado = 2
                comprobante.save(request)
                secuencia = secuencia_recaudacion(request, lugarrecaudacion, 'documento')
                if not comprobante.numero:
                #     secuencia.documento += 1
                #     secuencia.save(request)
                    comprobante.numero = secuencia
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
                    documento = ImpresionComprobantes.objects.get(pk=int(request.POST['id']))
                    for companterior in documento.comprobantes.all():
                        documento.comprobantes.remove(companterior)
                    documento.fecha = f.cleaned_data['fecha']
                    documento.descripcion = f.cleaned_data['descripcion']
                    documento.save(request)
                    for d in comprobantesrec:
                        comprobante = ComprobanteRecaudacion.objects.get(pk=int(d['id']))
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
                data['comprobante'] = comprobante = ImpresionComprobantes.objects.get(pk=int(request.POST['id']))
                data['detalles'] = comprobante.comprobantes.all()
                template = get_template("rec_documentoscomprobantes/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminar':
            try:
                comprobante = ImpresionComprobantes.objects.get(pk=int(request.POST['id']))
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
                    data['comprobantes'] = ComprobanteRecaudacion.objects.filter(impresioncomprobantes__isnull=True,numero__gt=0,status=True).exclude(estado=3).order_by('numero')
                    data['form'] = form
                    return render(request, "rec_documentoscomprobantes/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar documento'
                    data['comprobante'] = comprobante = ImpresionComprobantes.objects.get(pk=int(request.GET['id']))
                    lista1 = []
                    lista2 = []
                    for comprobanterec in ComprobanteRecaudacion.objects.filter(impresioncomprobantes__isnull=True).order_by('numero'):
                        lista1.append(comprobanterec.id)
                    for micomporbante in comprobante.comprobantes.all():
                        lista2.append(micomporbante.id)
                    data['comprobantes'] = ComprobanteRecaudacion.objects.filter(Q(id__in=lista1) | Q(id__in=lista2)).order_by('numero')
                    initial = model_to_dict(comprobante)
                    form = DocumentosComprobanteRecaudacionForm(initial=initial)
                    data['form'] = form
                    return render(request, "rec_documentoscomprobantes/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'finalizarcomp':
                try:
                    data['title'] = u'Confirmar finalizar comprobante'
                    data['comprobante'] = ImpresionComprobantes.objects.get(pk=int(request.GET['id']))
                    return render(request, "rec_documentoscomprobantes/finalizar.html", data)
                except:
                    pass

            if action == 'cambioperiodo':
                try:
                    anio = AnioEjercicio.objects.get(id=int(request.GET['id']))
                    request.session['aniofiscalpresupuesto'] = anio.anioejercicio
                except Exception as ex:
                    pass

            if action == 'eliminar':
                try:
                    data['title'] = u'Confirmar eliminar Documento'
                    data['comprobante'] = ImpresionComprobantes.objects.get(pk=int(request.GET['id']))
                    return render(request, "rec_documentoscomprobantes/eliminar.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Documentos de Comprobantes de Recaudación'
            ids = None
            search = None
            data['mianio'] = anio
            if 's' in request.GET:
                search = request.GET['s']
                documentos = ImpresionComprobantes.objects.filter(Q(numero__icontains=search) |
                                                                     Q(fecha__icontains=search), anioejercicio__anioejercicio=anio).distinct().order_by('-numero','-fecha') # '-numero',
            elif 'id' in request.GET:
                ids = request.GET['id']
                documentos = ImpresionComprobantes.objects.filter(id=ids, anioejercicio__anioejercicio=anio).order_by('-numero','-fecha')
            else:
                documentos = ImpresionComprobantes.objects.filter(anioejercicio__anioejercicio=anio).order_by('-numero','-fecha')
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
            data['reporte_0'] = obtener_reporte('comprobante_dia')
            data['reporte_1'] = obtener_reporte('resumen_comp_cont')
            data['anios'] = AnioEjercicio.objects.all()
            data['anioejercicio'] = anio_ejercicio().anioejercicio
            data['meses'] = MESES_CHOICES
            data['search'] = search if search else ""
            try:
                return render(request, "rec_documentoscomprobantes/view.html", data)
            except Exception as ex:
                pass