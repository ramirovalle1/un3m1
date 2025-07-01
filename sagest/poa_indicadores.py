# -*- coding: UTF-8 -*-
import calendar
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import IndicadoresPoaForm, DocumentosIndicadorPoaForm, DetallesDocumentosIndicadorPoaForm, \
    MedioVerificacionPoaForm
from sagest.models import IndicadorPoa, AccionDocumento, AccionDocumentoDetalle, ObjetivoOperativo, ObjetivoTactico, \
    ObjetivoEstrategico, Departamento, PeriodoPoa, MedioVerificacion
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador ,log
from sga.models import MONTH_CHOICES


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = IndicadoresPoaForm(request.POST)
                if f.is_valid():
                    indicador = IndicadorPoa(objetivooperativo=f.cleaned_data['objetivooperativo'],
                                             descripcion=f.cleaned_data['descripcion'],
                                             orden=f.cleaned_data['orden'])
                    indicador.save(request)
                    log(u'añadio indicador: %s' % indicador, request, "add")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'addmedioverificacion':
            try:
                f = MedioVerificacionPoaForm(request.POST)
                if f.is_valid():
                    medioverificacion = MedioVerificacion(nombre=f.cleaned_data['descripcion'])
                    medioverificacion.save(request)
                    log(u'añadio medio de verificacion: %s' % medioverificacion, request, "add")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'edit':
            try:
                indicador = IndicadorPoa.objects.get(pk=request.POST['id'])
                f = IndicadoresPoaForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['objetivooperativo']:
                        indicador.objetivooperativo = f.cleaned_data['objetivooperativo']
                    indicador.descripcion = f.cleaned_data['descripcion']
                    indicador.orden = f.cleaned_data['orden']
                    indicador.save(request)
                    log(u'edito indicador: %s' % indicador, request, "edit")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'editmedioverificacion':
            try:
                medioverificacion = MedioVerificacion.objects.get(pk=request.POST['id'])
                f = MedioVerificacionPoaForm(request.POST)
                if f.is_valid():
                    medioverificacion.nombre = f.cleaned_data['descripcion']
                    medioverificacion.save(request)
                    log(u'edito medio de verificacion: %s' % medioverificacion, request, "edit")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'deletemedioverificador':
            try:
                medioverificador = MedioVerificacion.objects.get(pk=request.POST['id'])
                medioverificador.status = False
                medioverificador.save(request)
                log(u'elimino medio de verificacion: %s' % medioverificador, request, "del")
                return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos."}), content_type="application/json")

        if action == 'delete':
            try:
                indicador = IndicadorPoa.objects.get(pk=request.POST['id'])
                indicador.status = False
                indicador.save(request)
                for ad in indicador.acciondocumento_set.filter(status=True):
                    ad.status = False
                    ad.save(request)
                    for acd in ad.acciondocumentodetalle_set.filter(status=True):
                        acd.status = False
                        acd.save(request)
                        for adr in acd.acciondocumentodetallerecord_set.filter(status=True):
                            adr.status = False
                            adr.save(request)
                log(u'elimino indicador: %s' % indicador, request, "del")
                return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos."}), content_type="application/json")

        if action == 'adddocumento':
            try:
                indicador = IndicadorPoa.objects.get(pk=request.POST['id'])
                f = DocumentosIndicadorPoaForm(request.POST)
                if f.is_valid():
                    documento = AccionDocumento(indicadorpoa=indicador,
                                                descripcion=f.cleaned_data['descripcion'],
                                                orden=f.cleaned_data['orden'],
                                                tipo=f.cleaned_data['tipo'],
                                                porcentaje=f.cleaned_data['porcentaje'])
                    if f.cleaned_data['tipo'] == '1':
                        documento.medioverificacion = f.cleaned_data['medioverificacion']
                        documento.observacion = None
                        documento.enlace = None
                    else:
                        documento.medioverificacion = None
                        documento.observacion = f.cleaned_data['observacion']
                        documento.enlace = f.cleaned_data['enlace']
                    documento.save(request)
                    log(u'añadio documento a poa: %s' % documento, request, "add")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'editdocumento':
            try:
                documento = AccionDocumento.objects.get(pk=request.POST['id'])
                f = DocumentosIndicadorPoaForm(request.POST)
                if f.is_valid():
                    documento.descripcion = f.cleaned_data['descripcion']
                    documento.orden = f.cleaned_data['orden']
                    documento.porcentaje = f.cleaned_data['porcentaje']
                    documento.tipo = f.cleaned_data['tipo']
                    if f.cleaned_data['tipo'] == '1':
                        documento.medioverificacion = f.cleaned_data['medioverificacion']
                        documento.observacion = None
                        documento.enlace = None
                    else:
                        documento.medioverificacion = None
                        documento.observacion = f.cleaned_data['observacion']
                        documento.enlace = f.cleaned_data['enlace']
                    documento.save(request)
                    log(u'edito documento a poa: %s' % documento, request, "edit")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'deletedocumento':
            try:
                documento = AccionDocumento.objects.get(pk=request.POST['id'])
                documento.acciondocumentodetalle_set.update(status=False)
                documento.status = False
                documento.save(request)
                for acd in documento.acciondocumentodetalle_set.filter(status=True):
                    acd.status = False
                    acd.save(request)
                    for adr in acd.acciondocumentodetallerecord_set.filter(status=True):
                        adr.status = False
                        adr.save(request)
                log(u'elimino documento a poa: %s' % documento, request, "del")
                return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos."}), content_type="application/json")

        if action == 'detallesdocumento':
            try:
                documento = AccionDocumento.objects.get(pk=request.POST['id'])
                f = DetallesDocumentosIndicadorPoaForm(request.POST)
                if f.is_valid():
                    inicio = f.cleaned_data['inicio']
                    fin = f.cleaned_data['fin']
                    if inicio > fin:
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error, la fecha de inicio es mayor que la fecha fin."}), content_type="application/json")
                    if documento.acciondocumentodetalle_set.filter(status=True).filter(Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__lte=inicio, fin__gte=inicio)).exists():
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error, ya existen acciones documentos que dan conflicto con este rango de fechas."}), content_type="application/json")
                    detallesdocumento = AccionDocumentoDetalle(acciondocumento=documento,
                                                               inicio=f.cleaned_data['inicio'],
                                                               fin=f.cleaned_data['fin'],
                                                               mostrar=f.cleaned_data['mostrar'],
                                                               estado_accion=0)
                    detallesdocumento.save(request)
                    log(u'añadio detalles documento a poa: %s' % detallesdocumento, request, "add")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'editdetallesdocumento':
            try:
                detalle = AccionDocumentoDetalle.objects.get(pk=request.POST['id'])
                f = DetallesDocumentosIndicadorPoaForm(request.POST)
                if f.is_valid():
                    inicio = f.cleaned_data['inicio']
                    fin = f.cleaned_data['fin']
                    if inicio > fin:
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error, la fecha de inicio es mayor que la fecha fin."}), content_type="application/json")
                    if AccionDocumentoDetalle.objects.filter(status=True, acciondocumento=detalle.acciondocumento).filter(Q(inicio__lte=fin, fin__gte=fin) | Q(inicio__lte=inicio, fin__gte=inicio)).exclude(id=detalle.id).exists():
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error, ya existen acciones documentos que dan conflicto con este rango de fechas."}), content_type="application/json")
                    detalle.inicio = f.cleaned_data['inicio']
                    detalle.fin = f.cleaned_data['fin']
                    detalle.mostrar = f.cleaned_data['mostrar']
                    detalle.save(request)
                    log(u'edito detalles documento a poa: %s' % detalle, request, "add")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'deletedetallesdocumento':
            try:
                detalle = AccionDocumentoDetalle.objects.get(pk=request.POST['id'])
                detalle.status = False
                detalle.save(request)
                for adr in detalle.acciondocumentodetallerecord_set.filter(status=True):
                    adr.status = False
                    adr.save(request)
                log(u'elimino detalles documento a poa: %s' % detalle, request, "del")
                return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos."}), content_type="application/json")

        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Solicitud Incorrecta."}), content_type="application/json")
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['title'] = u'Adicionar Indicador POA'
                    data['action'] = 'add'
                    form = IndicadoresPoaForm()
                    form.query()
                    data['form'] = form
                    template = get_template('poa_indicadores/add.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addmedioverificacion':
                try:
                    data['title'] = u'Adicionar Medio Verificación'
                    data['action'] = 'addmedioverificacion'
                    form = MedioVerificacionPoaForm()
                    data['form'] = form
                    template = get_template('poa_indicadores/addmedioverificacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'combooperativo':
                try:
                    data['objetivostacticos'] = ObjetivoOperativo.objects.filter(objetivotactico=request.GET['id'])
                    return render(request, 'poa_objtacticos/combo.html', data)
                except Exception as ex:
                    pass

            if action == 'combotacticos':
                try:
                    data['objetivostacticos'] = ObjetivoTactico.objects.filter(objetivoestrategico=request.GET['id'])
                    return render(request, 'poa_objtacticos/combo.html', data)
                except Exception as ex:
                    pass

            if action == 'comboestrategico':
                try:
                    data['objetivostacticos'] = ObjetivoEstrategico.objects.filter(periodopoa=request.GET['id'])
                    return render(request, 'poa_objtacticos/combo.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Indicador'
                    data['action'] = 'edit'
                    data['indicador'] = indicador = IndicadorPoa.objects.get(pk=request.GET['id'])
                    form = IndicadoresPoaForm(initial={"periodopoa": indicador.objetivooperativo.objetivotactico.objetivoestrategico.periodopoa,
                                                       "objetivoestrategico": indicador.objetivooperativo.objetivotactico.objetivoestrategico,
                                                       "objetivotactico": indicador.objetivooperativo.objetivotactico,
                                                       "objetivooperativo": indicador.objetivooperativo,
                                                       "descripcion": indicador.descripcion,
                                                       "orden": indicador.orden})
                    form.editar()
                    data['form'] = form
                    template = get_template('poa_indicadores/edit.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                    #return render(request, 'poa_indicadores/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'editmedioverificacion':
                try:
                    data['title'] = u'Modificar Medio Verificación'
                    data['action'] = 'editmedioverificacion'
                    data['medioverificacion'] = medioverificacion = MedioVerificacion.objects.get(pk=request.GET['id'])

                    data['form'] = MedioVerificacionPoaForm(initial={"descripcion": medioverificacion.nombre})
                    template = get_template('poa_indicadores/editmedioverificacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Indicador'
                    data['indicador'] = IndicadorPoa.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_indicadores/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'documentos':
                try:
                    data['title'] = u'Acciones del indicador'
                    data['indicador'] = indicador = IndicadorPoa.objects.get(pk=request.GET['id'])
                    data['documentos'] = indicador.mis_documentos()
                    data['meses'] = [x[1][:3] for x in MONTH_CHOICES]
                    return render(request, 'poa_indicadores/documentos.html', data)
                except Exception as ex:
                    pass

            if action == 'adddocumento':
                try:
                    data['title'] = u'Adicionar Acción del indicador'
                    data['action'] = 'adddocumento'
                    data['indicador'] = IndicadorPoa.objects.get(pk=request.GET['id'])
                    data['form'] = DocumentosIndicadorPoaForm()
                    template = get_template('poa_indicadores/adddocumento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                    #return render(request, 'poa_indicadores/adddocumento.html', data)
                except Exception as ex:
                    pass

            if action == 'editdocumento':
                try:
                    data['title'] = u'Modificar Acción del indicador'
                    data['action'] = 'editdocumento'
                    data['documento'] = documento = AccionDocumento.objects.get(pk=request.GET['id'])
                    data['form'] = DocumentosIndicadorPoaForm(initial={'orden': documento.orden,
                                                                       'porcentaje': documento.porcentaje,
                                                                       'tipo':documento.tipo,
                                                                       'medioverificacion': documento.medioverificacion,
                                                                       'observacion':documento.observacion,
                                                                       'enlace':documento.enlace,
                                                                       'descripcion': documento.descripcion})
                    data['indicador'] = documento.indicadorpoa
                    template = get_template('poa_indicadores/editdocumento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                    #return render(request, 'poa_indicadores/editdocumento.html', data)
                except Exception as ex:
                    pass

            if action == 'deletedocumento':
                try:
                    data['title'] = u'Eliminar Acción del indicador'
                    data['documento'] = documento = AccionDocumento.objects.get(pk=request.GET['id'])
                    data['indicador'] = documento.indicadorpoa
                    return render(request, 'poa_indicadores/deletedocumento.html', data)
                except Exception as ex:
                    pass

            if action == 'detallesdocumento':
                try:
                    data['title'] = u'Rango de fechas de las Acciones'
                    data['action'] = 'detallesdocumento'
                    data['documento'] = documento = AccionDocumento.objects.get(pk=request.GET['id'])
                    anio = datetime.now().year
                    mes = datetime.now().month
                    last_day = calendar.monthrange(anio, mes)[1]
                    data['form'] = DetallesDocumentosIndicadorPoaForm(initial={'inicio': datetime(anio, mes, 1).date(),
                                                                               'fin': datetime(anio, mes, last_day).date(),
                                                                               'mostrar': True})
                    data['indicador'] = documento.indicadorpoa
                    template = get_template('poa_indicadores/detallesdocumento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                    #return render(request, 'poa_indicadores/detallesdocumento.html', data)
                except Exception as ex:
                    pass

            if action == 'editdetallesdocumento':
                try:
                    data['title'] = u'Modificar rango de fechas de las Acciones'
                    data['action'] = 'editdetallesdocumento'
                    data['detalle'] = detalle = AccionDocumentoDetalle.objects.get(pk=request.GET['id'])
                    data['form'] = DetallesDocumentosIndicadorPoaForm(initial={'inicio': detalle.inicio,
                                                                               'fin': detalle.fin,
                                                                               'mostrar': detalle.mostrar})
                    data['indicador'] = detalle.acciondocumento.indicadorpoa
                    template = get_template('poa_indicadores/editdetallesdocumento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'deletemedioverificador':
                try:
                    data['title'] = u'Eliminar Medio Verificador'
                    data['medioverificador'] = MedioVerificacion.objects.get(pk=request.GET['idmedioverificador'])
                    return render(request, "poa_indicadores/deletemedioverificador.html", data)
                except Exception as ex:
                    pass

            if action == 'deletedetallesdocumento':
                try:
                    data['title'] = u'Eliminar rango de fechas del documento'
                    data['detalle'] = detalle = AccionDocumentoDetalle.objects.get(pk=request.GET['id'])
                    data['indicador'] = detalle.acciondocumento.indicadorpoa
                    return render(request, 'poa_indicadores/deletedetallesdocumento.html', data)
                except Exception as ex:
                    pass

            if action == 'listamedioverificacion':
                try:
                    data['title'] = u'Medio Verificacion'
                    data['action'] = 'listamedioverificacion'
                    search = request.GET.get('s', '')
                    url_vars = f"&action=listamedioverificacion"
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        listamedios = MedioVerificacion.objects.filter(nombre__icontains=search,status=True).order_by('nombre')
                        url_vars += "&s={}".format(search)
                    else:
                        listamedios = MedioVerificacion.objects.filter(status=True).order_by('nombre')
                    paging = MiPaginador(listamedios, 25)
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
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['listamedioverificacion'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, 'poa_indicadores/listamedioverificacion.html', data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Indicadores POA'
            periodoid = request.GET.get('periodoid','')
            depaid = request.GET.get('depaid','')
            search = request.GET.get('s', '')
            url_vars = ''
            filtro = Q(status=True)
            search = None
            tipo = None
            data['periodoid'] = PeriodoPoa.objects.filter(status=True).order_by('-id')[0].id if 'periodoid' not in request.GET else int(request.GET['periodoid'])
            data['periodos'] = PeriodoPoa.objects.filter(status=True).order_by('-id')

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                filtro = filtro & Q(descripcion__icontains=search)
                #indicadores = IndicadorPoa.objects.filter(objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'], descripcion__icontains=search, status=True)
                url_vars += "&s={}".format(search)
            #else:
             #   indicadores = IndicadorPoa.objects.filter(objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'], status=True)

            if 'depaid' in request.GET:
                data['depaid'] = depaid = int(request.GET['depaid'])
                if depaid > 0:
                    url_vars += "&depaid={}".format(depaid)
                    filtro = filtro & Q(objetivooperativo__objetivotactico__objetivoestrategico__departamento=int(request.GET['depaid']))
                    #indicadores = indicadores.filter(objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'], objetivooperativo__objetivotactico__objetivoestrategico__departamento=int(request.GET['depaid']))
            if 'periodoid' in request.GET:
                data['periodoid'] = periodoid = int(request.GET['periodoid'])
                if periodoid > 0:
                    url_vars += "&periodoid={}".format(periodoid)
                    filtro = filtro & Q(objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'])
                 #   indicadores = indicadores.filter(
                  #      objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'],
                   #     objetivooperativo__objetivotactico__objetivoestrategico__departamento=int(
                    #        request.GET['periodoid']))
            else:
                filtro = filtro & Q(objetivooperativo__objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'])
            indicadores = IndicadorPoa.objects.filter(filtro).order_by( 'orden', 'objetivooperativo__objetivotactico__objetivoestrategico', 'objetivooperativo__objetivotactico__objetivoestrategico__departamento''objetivooperativo__objetivotactico' ,
                                                       'objetivooperativo__objetivooperativo', 'descripcion' )
            paging = MiPaginador(indicadores.order_by( 'orden', 'objetivooperativo__objetivotactico__objetivoestrategico', 'objetivooperativo__objetivotactico__objetivoestrategico__departamento''objetivooperativo__objetivotactico' ,
                                                       'objetivooperativo__objetivooperativo', 'descripcion' ), 25)
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
            data['page'] = page
            data['search'] = search if search else ""
            data['indicadores'] = page.object_list
            data['depaid'] = 0 if 'depaid' not in request.GET else int(request.GET['depaid'])
            data['departametos'] = Departamento.objects.filter(objetivoestrategico__status=True, status=True, objetivoestrategico__periodopoa_id=data['periodoid']).distinct()
            data['url_vars'] = url_vars
            if data['periodoid'] < 4:
                return render(request, "poa_indicadores/view.html", data)
            else:
                return render(request, "poa_indicadores/viewcarrera.html", data)