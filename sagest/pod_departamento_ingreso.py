# -*- coding: UTF-8 -*-

import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect,JsonResponse
from django.shortcuts import render
from django.template import RequestContext
from decorators import secure_module
from sagest.forms import PodPeriodoForm, PodEvaluacionDetArchivoForm, MetasUnidadArchivoForm, \
    PodEvaluacionDetArchivoMetaForm
from sagest.models import PodPeriodo, PodEvaluacionDet, PodEvaluacion, PodEvaluacionDetRecord, PodEvaluacionDetCali, \
    PodPeridoFactor, Departamento, PodEvaluacionDetRecordMeta
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre, log
from sga.models import MONTH_CHOICES
from django.db.models import Q
from django.template.context import Context
from django.template.loader import get_template


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'editar_record':
            try:
                f = PodEvaluacionDetArchivoForm(request.POST, request.FILES)
                if f.is_valid():
                    podevaluaciondetrecord = PodEvaluacionDetRecord.objects.get(pk=int(request.POST['record']))
                    podevaluaciondetrecord.observacionenvia=f.cleaned_data['observacionenvia']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if request.POST['tipo'] == 'P':
                            newfile._name = generar_nombre("%s_PodFile_" % podevaluaciondetrecord.id, newfile._name)
                        else:
                            newfile._name = generar_nombre("%s_EvaFile_" % podevaluaciondetrecord.id, newfile._name)
                        podevaluaciondetrecord.archivo = newfile
                    if request.POST['tipo'] != 'P':
                        puntaje = 0
                        for f in PodPeridoFactor.objects.filter(podperiodo=podevaluaciondetrecord.podevaluaciondet.podperiodo, status=True).order_by("orden"):
                            podevaluaciondetcali = PodEvaluacionDetCali.objects.get(podevaluaciondetrecord=podevaluaciondetrecord, podfactor=f.podfactor, status=True)
                            podevaluaciondetcali.puntaje = round(float(request.POST['%s' % f.id]), 2)
                            podevaluaciondetcali.save(request)
                            if f.podfactor.tipofactor == 1:
                                puntaje += podevaluaciondetcali.puntaje
                            elif f.podfactor.tipofactor == 2:
                                puntaje -= podevaluaciondetcali.puntaje
                        podevaluaciondetrecord.puntaje = puntaje
                    podevaluaciondetrecord.save(request)
                    log(u'edito record: %s' % podevaluaciondetrecord.id, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editar_record_meta':
            try:
                f = PodEvaluacionDetArchivoMetaForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    newfiles = request.FILES['archivo']
                    newfilesd = newfiles._name
                    ext = newfilesd[newfilesd.rfind("."):]

                    extension = newfilesd._name.split('.')
                    tam = len(extension)
                    ext = extension[tam - 1]


                    if ext != '.xls' and ext != '.xlsx':
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .xls, .xlsx"})
                if f.is_valid():
                    podevaluaciondetrecord = PodEvaluacionDetRecordMeta.objects.get(pk=int(request.POST['record']))
                    podevaluaciondetrecord.observacionenvia=f.cleaned_data['observacionenvia']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if request.POST['tipo'] == 'P':
                            newfile._name = generar_nombre("%s_PodFile_" % podevaluaciondetrecord.id, newfile._name)
                        else:
                            newfile._name = generar_nombre("%s_EvaFile_" % podevaluaciondetrecord.id, newfile._name)
                        podevaluaciondetrecord.archivo = newfile
                    if request.POST['tipo'] != 'P':
                        puntaje = round(float(request.POST['nota']), 2)
                        podevaluaciondetrecord.puntaje = puntaje
                    podevaluaciondetrecord.save(request)
                    log(u'edito record meta: %s' % podevaluaciondetrecord.id, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregar_record':
            try:
                f = PodEvaluacionDetArchivoForm(request.POST, request.FILES)
                d = request.FILES['archivo']
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                newfiles = request.FILES['archivo']
                newfilesd = newfiles._name

                extension = newfilesd.split('.')
                tam = len(extension)
                ext = extension[tam - 1].lower()

                if ext != 'pdf':
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf"})
                if f.is_valid():
                    podevaluaciondetrecord = PodEvaluacionDetRecord(podevaluaciondet_id=int(request.POST['id']),
                                                                    observacionenvia=f.cleaned_data['observacionenvia'],
                                                                    tipoformulacio=1 if request.POST['tipo'] == 'P' else 2,
                                                                    estado=5)
                    podevaluaciondetrecord.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if request.POST['tipo'] == 'P':
                            newfile._name = generar_nombre("%s_PodFile_" % podevaluaciondetrecord.id, newfile._name)
                        else:
                            newfile._name = generar_nombre("%s_EvaFile_" % podevaluaciondetrecord.id, newfile._name)
                        podevaluaciondetrecord.archivo = newfile
                    podevaluaciondetrecord.save(request)
                    if request.POST['tipo'] == 'P':
                        podevaluaciondetrecord.podevaluaciondet.estadopod = 5
                    else:
                        puntaje = 0
                        for f in PodPeridoFactor.objects.filter(podperiodo=podevaluaciondetrecord.podevaluaciondet.podperiodo, status=True).order_by("orden"):
                            podevaluaciondetcali = PodEvaluacionDetCali(podevaluaciondetrecord=podevaluaciondetrecord,
                                                                        podfactor=f.podfactor,
                                                                        puntaje=round(float(request.POST['%s' % f.id]), 2))
                            podevaluaciondetcali.save(request)
                            if f.podfactor.tipofactor == 1:
                                puntaje += podevaluaciondetcali.puntaje
                            elif f.podfactor.tipofactor == 2:
                                puntaje -= podevaluaciondetcali.puntaje
                        podevaluaciondetrecord.podevaluaciondet.estadoeva = 5
                        podevaluaciondetrecord.puntaje = puntaje
                        podevaluaciondetrecord.save(request)
                    podevaluaciondetrecord.podevaluaciondet.save(request)
                    log(u'añadio record: %s' % podevaluaciondetrecord.id, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregar_record_meta':
            try:
                f = PodEvaluacionDetArchivoMetaForm(request.POST, request.FILES)
                d = request.FILES['archivo']
                if d.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                newfiles = request.FILES['archivo']
                newfilesd = newfiles._name
                #ext = newfilesd[newfilesd.rfind("."):]

                extension = newfilesd.split('.')
                tam = len(extension)
                ext = extension[tam - 1].lower()


                if ext != 'xls' and ext != 'xlsx' and ext != 'pdf':
                    return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .xls, .xlsx, .pdf"})

                if f.is_valid():
                    podevaluaciondetrecord = PodEvaluacionDetRecordMeta(podevaluacion_id=int(request.POST['id']),
                                                                        observacionenvia=f.cleaned_data['observacionenvia'],
                                                                        tipoformulacio=1 if request.POST['tipo'] == 'P' else 2,
                                                                        estado=5)
                    podevaluaciondetrecord.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if request.POST['tipo'] == 'P':
                            newfile._name = generar_nombre("%s_PodFile_" % podevaluaciondetrecord.id, newfile._name)
                        else:
                            newfile._name = generar_nombre("%s_EvaFile_" % podevaluaciondetrecord.id, newfile._name)
                        podevaluaciondetrecord.archivo = newfile
                    podevaluaciondetrecord.save(request)
                    if request.POST['tipo'] == 'P':
                        podevaluaciondetrecord.podevaluacion.estadopodmeta = 5
                    else:
                        puntaje = round(float(request.POST['nota']), 2)
                        podevaluaciondetrecord.podevaluacion.estadoevameta = 5
                        podevaluaciondetrecord.puntaje = puntaje
                        podevaluaciondetrecord.save(request)
                    podevaluaciondetrecord.podevaluacion.save(request)
                    log(u'añadio record meta: %s' % podevaluaciondetrecord.id, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Periodo POD'
                    data['form'] = PodPeriodoForm()
                    return render(request, 'pod_periodo/add.html', data)
                except Exception as ex:
                    pass

            elif action == 'planificar':
                try:
                    data['title'] = u'Ingreso POD'
                    data['periodopod'] = podperiodo = PodPeriodo.objects.get(pk=request.GET['id'])
                    data['meses'] = MONTH_CHOICES
                    pode = PodEvaluacion.objects.filter(evaluador=persona, podperiodo=podperiodo, status=True)
                    data['pode'] = pode[0]
                    podevaluacion = PodEvaluacionDet.objects.filter(departamento__in=[x.departamento for x in pode], podperiodo_id=int(request.GET['id']), status=True).order_by("departamento", "evaluado").distinct("departamento__nombre", "evaluado__apellido1", "evaluado__apellido2", "evaluado__nombres")
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            podevaluacion = podevaluacion.filter(Q(evaluado__nombres__icontains=search) |
                                                                 Q(evaluado__apellido1__icontains=search) |
                                                                 Q(evaluado__apellido2__icontains=search) |
                                                                 Q(evaluado__cedula__icontains=search) |
                                                                 Q(evaluado__pasaporte__icontains=search)).distinct("departamento__nombre", "evaluado__apellido1", "evaluado__apellido2", "evaluado__nombres")
                        else:
                            podevaluacion = podevaluacion.filter(Q(evaluado__apellido1__icontains=ss[0]) &
                                                                 Q(evaluado__apellido2__icontains=ss[1])).distinct("departamento__nombre", "evaluado__apellido1", "evaluado__apellido2", "evaluado__nombres")
                    paging = MiPaginador(podevaluacion, 25)
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
                    data['podevaluacion'] = page.object_list

                    return render(request, 'pod_departamento_ingreso/planificar.html', data)
                except Exception as ex:
                    pass

            elif action == 'ingresopodeva':
                try:
                    data = {}
                    podevaluaciondet = PodEvaluacionDet.objects.get(pk=int(request.GET['iddet']))
                    data['evaluado'] = podevaluaciondet.evaluado
                    data['departamento'] = podevaluaciondet.departamento
                    data['podevaluaciondet'] = podevaluaciondet
                    data['tipo'] = request.GET['tipo']
                    data['record'] = PodEvaluacionDetRecord.objects.filter(status=True, podevaluaciondet=podevaluaciondet, tipoformulacio=1 if request.GET['tipo'] == 'P' else 2)
                    template = get_template("pod_departamento_ingreso/ingresopodeva.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ingresopodevajefe':
                try:
                    data = {}
                    podevaluacion = PodEvaluacion.objects.get(pk=int(request.GET['iddet']))
                    # data['evaluado'] = podevaluaciondet.evaluado
                    data['departamento'] = podevaluacion.departamento
                    data['podevaluacion'] = podevaluacion
                    data['tipo'] = request.GET['tipo']
                    data['record'] = PodEvaluacionDetRecordMeta.objects.filter(status=True, podevaluacion=podevaluacion, tipoformulacio=1 if request.GET['tipo'] == 'P' else 2)
                    template = get_template("pod_departamento_ingreso/ingresopodevajefe.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_detalle':
                try:
                    data = {}
                    podevaluaciondetrecord = PodEvaluacionDetRecord.objects.get(pk=int(request.GET['record']))
                    podevaluaciondetcali = PodEvaluacionDetCali.objects.filter(podevaluaciondetrecord=podevaluaciondetrecord)
                    data['podevaluaciondetcali'] = podevaluaciondetcali
                    data['podevaluaciondetrecord'] = podevaluaciondetrecord
                    template = get_template("pod_periodo/ver_detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editar_record':
                try:
                    data = {}
                    podevaluaciondetrecord = PodEvaluacionDetRecord.objects.get(pk=int(request.GET['record']))
                    data['tipo'] = request.GET['tipo']
                    data['podevaluaciondetrecord'] = podevaluaciondetrecord
                    data['podevaluaciondet'] = podevaluaciondetrecord.podevaluaciondet
                    form = PodEvaluacionDetArchivoForm(initial={'observacionenvia': podevaluaciondetrecord.observacionenvia})
                    form.editar()
                    data['form'] = form
                    data['action'] = 'editar_record'
                    if request.GET['tipo'] == 'P':
                        data['permite_modificar'] = podevaluaciondetrecord.podevaluaciondet.puede_mod_pod()
                    else:
                        data['factores'] = PodPeridoFactor.objects.filter(podperiodo=podevaluaciondetrecord.podevaluaciondet.podperiodo, status=True).order_by("orden")
                        data['permite_modificar'] = podevaluaciondetrecord.podevaluaciondet.puede_mod_eva()
                    template = get_template("pod_departamento_ingreso/agregar_record.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'agregar_record':
                try:
                    data = {}
                    podevaluaciondet = PodEvaluacionDet.objects.get(pk=int(request.GET['id']))
                    data['tipo'] = request.GET['tipo']
                    form = PodEvaluacionDetArchivoForm()
                    data['form'] = form
                    data['podevaluaciondet'] = podevaluaciondet
                    data['action'] = 'agregar_record'
                    if request.GET['tipo'] == 'P':
                        data['permite_modificar'] = podevaluaciondet.puede_ingresar_pod()
                    else:
                        data['factores'] = PodPeridoFactor.objects.filter(podperiodo=podevaluaciondet.podperiodo, status=True).order_by("orden")
                        data['permite_modificar'] = podevaluaciondet.puede_ingresar_eva()
                    template = get_template("pod_departamento_ingreso/agregar_record.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editar_record_meta':
                try:
                    data = {}
                    podevaluaciondetrecord = PodEvaluacionDetRecordMeta.objects.get(pk=int(request.GET['record']))
                    data['tipo'] = request.GET['tipo']
                    data['podevaluaciondetrecord'] = podevaluaciondetrecord
                    data['puntaje'] = podevaluaciondetrecord.puntaje
                    data['podevaluacion'] = podevaluaciondetrecord.podevaluacion
                    form = PodEvaluacionDetArchivoMetaForm(initial={'observacionenvia': podevaluaciondetrecord.observacionenvia})
                    # form.editar()
                    data['form'] = form
                    data['action'] = 'editar_record_meta'
                    if request.GET['tipo'] == 'P':
                        data['permite_modificar'] = podevaluaciondetrecord.podevaluacion.puede_mod_pod_meta()
                    else:
                        # data['factores'] = PodPeridoFactor.objects.filter(podperiodo=podevaluaciondetrecord.podevaluaciondet.podperiodo, status=True).order_by("orden")
                        data['permite_modificar'] = podevaluaciondetrecord.podevaluacion.puede_mod_eva_meta()
                    template = get_template("pod_departamento_ingreso/agregar_record_meta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'agregar_record_meta':
                try:
                    data = {}
                    podevaluacion = PodEvaluacion.objects.get(pk=int(request.GET['id']))
                    data['tipo'] = request.GET['tipo']
                    form = PodEvaluacionDetArchivoMetaForm()
                    data['form'] = form
                    data['podevaluacion'] = podevaluacion
                    data['action'] = 'agregar_record_meta'
                    if request.GET['tipo'] == 'P':
                        data['permite_modificar'] = podevaluacion.puede_ingresar_pod_meta()
                    else:
                        # data['factores'] = PodPeridoFactor.objects.filter(podperiodo=podevaluaciondet.podperiodo, status=True).order_by("orden")
                        data['permite_modificar'] = podevaluacion.puede_ingresar_eva_meta()
                    template = get_template("pod_departamento_ingreso/agregar_record_meta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'EVAL Ingreso'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                periodos = PodPeriodo.objects.filter(descripcion__icontains=search, status=True, podevaluacion__evaluador=persona, podevaluacion__status=True).distinct()
            else:
                periodos = PodPeriodo.objects.filter(status=True, podevaluacion__evaluador=persona, podevaluacion__status=True).distinct()
            paging = MiPaginador(periodos, 25)
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
            data['periodospod'] = page.object_list
            return render(request, "pod_departamento_ingreso/view.html", data)