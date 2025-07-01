# -*- coding: UTF-8 -*-
import json
import sys
from decimal import Decimal
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from decorators import secure_module
from sagest.forms import PodPeriodoForm, PodPeriodoFactorForm, PodFactorForm, PodEvaluacionDetCalificaForm, \
    PodEvaluacionDetForm, PodEvaluacionDetArchivoForm, MetasUnidadArchivoForm, PodEvaluacionDetArchivoMetaForm, \
    PodDiccionarioCompLaboralForm, PodProductoCompetenciaForm, PodEvaluacionMetaForm
from sagest.models import PodPeriodo, PodFactor, PodPeridoFactor, PodEvaluacionDet, Departamento, DistributivoPersona, \
    PodEvaluacion, PodEvaluacionDetRecord, PodEvaluacionDetCali, PodEvaluacionDetRecordMeta, PodEvaluacionMeta, \
    PodEvaluacionRelacionMeta, PodDiccionarioCompLaboral, PodDiccionarioCompLaboralDet, PodDiccionarioCompLabRelacion, \
    PodProductoEvaDet, PodEvaDetProductoRelacion, PodRelIntExt, PodEvaDetIERelacion, PodEvaDetCompLabRelacion, \
    CompetenciaLaboral,ProductoServicioSeccion, ProductoServicioTh
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre, log, convertir_fecha, null_to_decimal
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import MONTH_CHOICES, Persona
from django.db.models import Q
from django.template.context import Context
from django.template.loader import get_template
from xlwt import *
import random
from django.contrib import messages

from sga.templatetags.sga_extras import encrypt


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
                f = PodPeriodoForm(request.POST, request.FILES)
                if f.is_valid():
                    # if PodPeriodo.objects.filter(anio=f.cleaned_data['anio'], status=True).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya existe un periodo activo con ese año."})
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("podperiodo_", newfile._name)
                    podperiodo = PodPeriodo(anio=f.cleaned_data['anio'],
                                            descripcion=f.cleaned_data['descripcion'],
                                            inicio=f.cleaned_data['inicio'],
                                            fin=f.cleaned_data['fin'],
                                            iniciopod=f.cleaned_data['iniciopod'],
                                            finpod=f.cleaned_data['finpod'],
                                            inicioeval=f.cleaned_data['inicioeval'],
                                            fineval=f.cleaned_data['fineval'],
                                            publicacion=f.cleaned_data['publicacion'],
                                            archivo=newfile)
                    podperiodo.save(request)
                    log(u'añadio periodo pod: %s' % podperiodo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                periodo = PodPeriodo.objects.get(pk=request.POST['id'])
                f = PodPeriodoForm(request.POST, request.FILES)
                if f.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("podperiodo_", newfile._name)
                        periodo.archivo = newfile
                    periodo.descripcion = f.cleaned_data['descripcion']
                    periodo.iniciopod = f.cleaned_data['iniciopod']
                    periodo.finpod = f.cleaned_data['finpod']
                    periodo.inicio = f.cleaned_data['inicio']
                    periodo.fin = f.cleaned_data['fin']
                    periodo.inicioeval = f.cleaned_data['inicioeval']
                    periodo.fineval = f.cleaned_data['fineval']
                    periodo.publicacion = f.cleaned_data['publicacion']
                    periodo.save(request)
                    log(u'edito periodo pod: %s' % periodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                periodo = PodPeriodo.objects.get(pk=request.POST['id'])
                periodo.status = False
                periodo.save(request)
                log(u'cambio estado de periodo pod: %s' % periodo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addfactorperiodo':
            try:
                f = PodPeriodoFactorForm(request.POST)
                if f.is_valid():
                    periodo = PodPeriodo.objects.get(pk=request.POST['id'])
                    minimo = Decimal(request.POST['valorminimo'])
                    maximo = Decimal(request.POST['valormaximo'])
                    if PodPeridoFactor.objects.filter(podperiodo=periodo, podfactor=f.cleaned_data['podfactor']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un periodo activo con ese factor."})
                    if PodPeridoFactor.objects.filter(podperiodo=periodo, orden=f.cleaned_data['orden']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un factor para este periodo con ese orden."})
                    podperiodofactor = PodPeridoFactor(podperiodo=periodo,
                                                       podfactor=f.cleaned_data['podfactor'],
                                                       orden=f.cleaned_data['orden'],
                                                       minimo=minimo,
                                                       maximo=maximo)
                    podperiodofactor.save(request)
                    log(u'añadio factor periodo pod: %s' % podperiodofactor, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addfactor':
            try:
                f = PodFactorForm(request.POST)
                if f.is_valid():
                    minimo = Decimal(f.cleaned_data['minimo'])
                    maximo = Decimal(f.cleaned_data['maximo'])
                    if maximo <= minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor Máximo no puede ser menor o igual al mínimo."})
                    factor = PodFactor(tipofactor=f.cleaned_data['tipofactor'],
                                       descripcion=f.cleaned_data['descripcion'],
                                       minimo=minimo,
                                       maximo=maximo)
                    factor.save(request)
                    log(u'añadio factor periodo pod: %s' % factor, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'adddiccomlab':
            try:
                f = PodDiccionarioCompLaboralForm(request.POST)
                compobservable = request.POST.getlist('compobservable')
                if f.is_valid():
                    poddic = PodDiccionarioCompLaboral(tipo=f.cleaned_data['tipo'],
                                                       denominacion=f.cleaned_data['denominacion'],
                                                       definicion=f.cleaned_data['definicion'])
                    poddic.save(request)
                    log(u'añadio diccionario de competencia laboral: %s' % poddic, request, "add")
                    c = 0
                    while c < len(compobservable):
                        producto = PodDiccionarioCompLaboralDet(
                            nivel= c + 1,
                            compobservable=compobservable[c])
                        c += 1
                        producto.save(request)
                        log(u'añadio detalle de competencia laboral: %s' % producto, request, "add")
                        relacion = PodDiccionarioCompLabRelacion(
                            complaboralcab_id=poddic.id,
                            complaboraldet_id=producto.id
                        )
                        relacion.save(request)
                        log(u'añadio relacion entre det y cab de competencia laboral: %s' % relacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editdiccomlab':
            try:
                f = PodDiccionarioCompLaboralForm(request.POST)
                diccionario = PodDiccionarioCompLaboral.objects.get(pk=request.POST['id'])
                compobservable = request.POST.getlist('compobservable')
                if f.is_valid():
                    diccionario.tipo = f.cleaned_data['tipo']
                    diccionario.denominacion = f.cleaned_data['denominacion']
                    diccionario.definicion = f.cleaned_data['definicion']
                    diccionario.save(request)
                    log(u'edito diccionario de competencia laboral: %s' % diccionario, request, "edit")

                    detalles = PodDiccionarioCompLabRelacion.objects.filter(complaboralcab_id=diccionario.id)
                    c = 0
                    for detalle in detalles:
                        detalle.complaboraldet.compobservable = compobservable[c]
                        detalle.complaboraldet.save()
                        c += 1
                        log(u'edito detalle de competencia laboral: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editfactorperiodo':
            try:
                periodo = PodPeriodo.objects.get(pk=request.POST['pod'])
                factor = PodPeridoFactor.objects.get(pk=request.POST['id'])
                f = PodPeriodoFactorForm(request.POST)
                if f.is_valid():
                    if PodPeridoFactor.objects.filter(podperiodo=periodo, orden=f.cleaned_data['orden']).exclude(id=factor.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un factor para este periodo con ese orden."})
                    minimo = Decimal(f.cleaned_data['minimo'])
                    maximo = Decimal(f.cleaned_data['maximo'])
                    if maximo <= minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor Máximo no puede ser menor o igual al mínimo."})
                    factor.minimo = minimo
                    factor.maximo = maximo
                    factor.orden = f.cleaned_data['orden']
                    factor.save(request)
                    log(u'edit factor periodo pod: %s' % factor, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editfactor':
            try:
                factor = PodFactor.objects.get(pk=request.POST['id'])
                f = PodFactorForm(request.POST)
                if f.is_valid():
                    minimo = Decimal(f.cleaned_data['minimo'])
                    maximo = Decimal(f.cleaned_data['maximo'])
                    if maximo <= minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor Máximo no puede ser menor o igual al mínimo."})
                    factor.minimo = minimo
                    factor.maximo = maximo
                    factor.tipofactor = f.cleaned_data['tipofactor']
                    factor.descripcion = f.cleaned_data['descripcion']
                    factor.save(request)
                    log(u'añadio factor pod: %s' % factor, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletefactor':
            try:
                factor = PodFactor.objects.get(pk=request.POST['id'])
                factor.status = False
                factor.save(request)
                log(u'cambio estado factor periodo pod: %s' % factor, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deletefactorperiodo':
            try:
                factor = PodPeridoFactor.objects.get(pk=request.POST['id'])
                factor.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deletediccomlab':
            try:
                diccionario = PodDiccionarioCompLaboral.objects.get(pk=request.POST['id'])
                diccionario.status = False
                diccionario.save()
                log(u'elimino diccionario de competencia laboral: %s' % diccionario, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        if action == 'valores_factor':
            try:
                factor = PodFactor.objects.get(pk=int(request.POST['id']))
                minimo = Decimal(factor.minimo)
                maximo = Decimal(factor.maximo)
                return JsonResponse({"result": "ok", "minimo": float(minimo), "maximo": float(maximo)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'agregar_servidores':
            try:
                podperiodo = PodPeriodo.objects.get(pk=int(request.POST['idp']))
                departamento = Departamento.objects.get(pk=int(request.POST['idd']))
                if not PodEvaluacion.objects.filter(podperiodo=podperiodo, departamento=departamento).exists():
                    if departamento.responsable:
                        podevaluacion = PodEvaluacion(podperiodo=podperiodo, departamento=departamento, evaluador=departamento.responsable)
                        podevaluacion.save(request)
                for p in Persona.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not PodEvaluacionDet.objects.filter(podperiodo=podperiodo, departamento=departamento, evaluado=p).exists():
                        podevaluaciondet = PodEvaluacionDet(podperiodo=podperiodo,
                                                            departamento=departamento,
                                                            evaluado=p,
                                                            inicio=podperiodo.inicio,
                                                            fin=podperiodo.fin,
                                                            iniciopod=podperiodo.iniciopod,
                                                            finpod=podperiodo.finpod,
                                                            inicioeval=podperiodo.inicioeval,
                                                            fineval=podperiodo.fineval)
                        podevaluaciondet.save(request)
                        podevaluaciondet.actualiza_campos_distributivo(request)
                        log(u'Adiciono persona para la evaluacion: %s' % podevaluaciondet, request, "add")
                    else:
                        #podevaluaciondet = PodEvaluacionDet.objects.get(podperiodo=podperiodo, departamento=departamento, evaluado=p)

                        podevaluaciondet = PodEvaluacionDet.objects.filter(podperiodo=podperiodo, departamento=departamento, evaluado=p)
                        for det in podevaluaciondet:
                            if not det.status:
                                det.status = True
                                det.save(request)

                        # if not podevaluaciondet.status:
                        #     podevaluaciondet.status = True
                        #     podevaluaciondet.save(request)

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'delete_evaluado':
            try:
                podevaluaciondet = PodEvaluacionDet.objects.get(pk=request.POST['id'])
                podevaluaciondet.status = False
                podevaluaciondet.save(request)
                log(u'cambio estado de evaluado pod: %s' % podevaluaciondet, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'fecha_evaluado':
            try:
                if int(request.POST['idf']) != 0:
                    # if PodEvaluacionDet.objects.filter(Q(inicio__lte=convertir_fecha(request.POST['ini'])) & Q(fin__gte=convertir_fecha(request.POST['ini'])), podperiodo_id=request.POST['idp'], departamento_id=request.POST['idd'], evaluado_id=request.POST['evaluado']).exclude(pk=request.POST['idf']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha inicial o final incorrecta."})
                    # if PodEvaluacionDet.objects.filter(Q(inicio__lte=convertir_fecha(request.POST['fin'])) & Q(fin__gte=convertir_fecha(request.POST['fin'])), podperiodo_id=request.POST['idp'], departamento_id=request.POST['idd'], evaluado_id=request.POST['evaluado']).exclude(pk=request.POST['idf']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha inicial o final incorrecta."})
                    podevaluaciondet = PodEvaluacionDet.objects.get(pk=request.POST['idf'])
                    podevaluaciondet.inicio = convertir_fecha(request.POST['ini'])
                    podevaluaciondet.fin = convertir_fecha(request.POST['fin'])
                    podevaluaciondet.iniciopod = convertir_fecha(request.POST['ipod'])
                    podevaluaciondet.finpod = convertir_fecha(request.POST['fpod'])
                    podevaluaciondet.inicioeval = convertir_fecha(request.POST['ieval'])
                    podevaluaciondet.fineval = convertir_fecha(request.POST['feval'])
                else:
                    # if PodEvaluacionDet.objects.filter(Q(inicio__lte=convertir_fecha(request.POST['ini'])) & Q(fin__gte=convertir_fecha(request.POST['ini'])), podperiodo_id=request.POST['idp'], departamento_id=request.POST['idd'], evaluado_id=request.POST['evaluado']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha inicial o final incorrecta."})
                    # if PodEvaluacionDet.objects.filter(Q(inicio__lte=convertir_fecha(request.POST['fin'])) & Q(fin__gte=convertir_fecha(request.POST['fin'])), podperiodo_id=request.POST['idp'], departamento_id=request.POST['idd'], evaluado_id=request.POST['evaluado']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha inicial o final incorrecta."})
                    podevaluaciondet = PodEvaluacionDet(podperiodo_id=request.POST['idp'],
                                                        departamento_id=request.POST['idd'],
                                                        evaluado_id=request.POST['evaluado'],
                                                        inicio=convertir_fecha(request.POST['ini']),
                                                        fin=convertir_fecha(request.POST['fin']),
                                                        iniciopod=convertir_fecha(request.POST['ipod']),
                                                        finpod=convertir_fecha(request.POST['fpod']),
                                                        inicioeval=convertir_fecha(request.POST['ieval']),
                                                        fineval=convertir_fecha(request.POST['feval']))
                podevaluaciondet.save(request)
                podevaluaciondet.actualiza_campos_distributivo(request)
                log(u'añadio fecha evaluado pod: %s' % podevaluaciondet, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al ingresar los datos."})

        if action == 'editar_record':
            try:
                f = PodEvaluacionDetCalificaForm(request.POST)
                if f.is_valid():
                    podevaluaciondetrecord = PodEvaluacionDetRecord.objects.get(pk=int(request.POST['id']))
                    podevaluaciondetrecord.estado = f.cleaned_data['estado']
                    podevaluaciondetrecord.observacionaprobador = f.cleaned_data['observacionaprobador']
                    podevaluaciondetrecord.fechaestado = datetime.now()
                    podevaluaciondetrecord.aprobador = request.session['persona']
                    if request.POST['tipo'] == 'P':
                        podevaluaciondetrecord.podevaluaciondet.estadopod = f.cleaned_data['estado']
                        # podevaluaciondetrecord.podevaluaciondet.estadopod = 2
                    else:
                        podevaluaciondetrecord.podevaluaciondet.estadoeva = f.cleaned_data['estado']
                        # podevaluaciondetrecord.podevaluaciondet.estadoeva = 2
                    podevaluaciondetrecord.notificado = True
                    podevaluaciondetrecord.podevaluaciondet.save(request)
                    podevaluaciondetrecord.save(request)
                    log(u'edito record pod: %s' % podevaluaciondetrecord, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editar_record_meta':
            try:
                f = PodEvaluacionDetCalificaForm(request.POST)
                # if 'archivo' in request.FILES['archivo']:
                #     d = request.FILES['archivo']
                #     if d.size > 10485760:
                #         return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                #     newfiles = request.FILES['archivo']
                #     newfilesd = newfiles._name
                #     ext = newfilesd[newfilesd.rfind("."):]
                #     if ext != '.xls' and ext != '.xlsx' and ext != '.pdf':
                #         return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .xls, .xlsx, .pdf"})
                if f.is_valid():
                    podevaluaciondetrecord = PodEvaluacionDetRecordMeta.objects.get(pk=int(request.POST['id']))
                    podevaluaciondetrecord.estado = f.cleaned_data['estado']
                    podevaluaciondetrecord.observacionaprobador = f.cleaned_data['observacionaprobador']
                    podevaluaciondetrecord.fechaestado = datetime.now()
                    podevaluaciondetrecord.aprobador = request.session['persona']
                    if request.POST['tipo'] == 'P':
                        podevaluaciondetrecord.podevaluacion.estadopodmeta = f.cleaned_data['estado']
                        # podevaluaciondetrecord.podevaluaciondet.estadopod = 2
                    else:
                        podevaluaciondetrecord.podevaluacion.estadoevameta = f.cleaned_data['estado']
                        # podevaluaciondetrecord.podevaluaciondet.estadoeva = 2
                    podevaluaciondetrecord.notificado = True
                    podevaluaciondetrecord.podevaluacion.save(request)
                    podevaluaciondetrecord.save(request)
                    log(u'edito record pod meta: %s' % podevaluaciondetrecord, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'del_record':
            try:
                if 'id' in request.POST and 'tipo' in request.POST:
                    podevaluaciondetrecord = PodEvaluacionDetRecord.objects.get(pk=int(request.POST['id']))
                    if podevaluaciondetrecord.podevaluaciondetcali_set.all().exists():
                        podevaluaciondetrecord.podevaluaciondetcali_set.all().delete()
                    log(u'elimimnó record pod codigo: %s' % podevaluaciondetrecord, request, "del")
                    idr = podevaluaciondetrecord.id
                    podevaluaciondet = podevaluaciondetrecord.podevaluaciondet
                    podevaluaciondetrecord.delete()
                    if PodEvaluacionDetRecord.objects.filter(status=True, podevaluaciondet=podevaluaciondet).exists():
                        podevaluaciondetrecord = PodEvaluacionDetRecord.objects.filter(status=True, podevaluaciondet=podevaluaciondet, tipoformulacio=1 if request.POST['tipo'] == 'P' else 2)
                        if podevaluaciondetrecord.exists():
                            podevaluaciondetrecord = podevaluaciondetrecord.order_by('-id')[0]
                            if podevaluaciondetrecord.estado==3:
                                if podevaluaciondetrecord.tipoformulacio == 1:
                                    podevaluaciondet.estadopod = 3
                                if podevaluaciondetrecord.tipoformulacio == 2:
                                    podevaluaciondet.estadoeva = 3
                        else:
                            if request.POST['tipo'] == 'P':
                                podevaluaciondet.estadopod = 1
                            else:
                                podevaluaciondet.estadoeva = 1
                        podevaluaciondet.save(request)

                    return JsonResponse({"result": "ok", "idr": idr })
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'del_record_meta':
            try:
                if 'id' in request.POST and 'tipo' in request.POST:
                    podevaluaciondetrecord = PodEvaluacionDetRecordMeta.objects.get(pk=int(request.POST['id']))
                    idr = podevaluaciondetrecord.id
                    podevaluacion = podevaluaciondetrecord.podevaluacion
                    podevaluaciondetrecord.delete()
                    if PodEvaluacionDetRecordMeta.objects.filter(status=True, podevaluacion=podevaluacion, tipoformulacio=1 if request.POST['tipo'] == 'P' else 2).exists():
                        podevaluaciondetrecord = PodEvaluacionDetRecordMeta.objects.filter(status=True, podevaluacion=podevaluacion, tipoformulacio=1 if request.POST['tipo'] == 'P' else 2)
                        if podevaluaciondetrecord.exists():
                            podevaluaciondetrecord = podevaluaciondetrecord.order_by('-id')[0]
                            if podevaluaciondetrecord.estado==3:
                                if podevaluaciondetrecord.tipoformulacio == 1:
                                    podevaluacion.estadopod = 3
                                if podevaluaciondetrecord.tipoformulacio == 2:
                                    podevaluacion.estadoeva = 3
                        else:
                            if request.POST['tipo'] == 'P':
                                podevaluacion.estadopod = 1
                            else:
                                podevaluacion.estadoeva = 1
                        podevaluacion.save(request)

                    return JsonResponse({"result": "ok", "idr": idr })
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'agregar_funcionario' or action == 'agredar_director':
            try:
                f = PodEvaluacionDetForm(request.POST)
                if f.is_valid():
                    podperiodo = PodPeriodo.objects.get(pk=int(request.POST['idp']))
                    departamento = Departamento.objects.get(pk=int(request.POST['idd']))
                    persona = DistributivoPersona.objects.get(pk=f.cleaned_data['evaluado']).persona
                    if action == 'agregar_funcionario':
                        if PodEvaluacionDet.objects.filter(podperiodo=podperiodo, departamento=departamento, evaluado=persona, status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe funcionario, en este periodo y departamento."})
                        podevaluaciondet = PodEvaluacionDet(podperiodo=podperiodo,
                                                            departamento=departamento,
                                                            evaluado=persona,
                                                            inicio=podperiodo.inicio,
                                                            fin=podperiodo.fin,
                                                            iniciopod=podperiodo.iniciopod,
                                                            finpod=podperiodo.finpod,
                                                            inicioeval=podperiodo.inicioeval,
                                                            fineval=podperiodo.fineval)
                        podevaluaciondet.save(request)
                        podevaluaciondet.actualiza_campos_distributivo(request)
                        log(u'añadio funcionario pod: %s' % podevaluaciondet, request, "add")
                    elif action == 'agredar_director':
                        PodEvaluacion.objects.filter(podperiodo=podperiodo, departamento=departamento, status=True).update(status=False)
                        podevaluacion = PodEvaluacion(podperiodo=podperiodo, departamento=departamento, evaluador=persona)
                        podevaluacion.save(request)
                        log(u'añadio director pod: %s' % podevaluacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'agregar_record':
            try:
                f = PodEvaluacionDetArchivoForm(request.POST, request.FILES)
                if f.is_valid():
                    podevaluaciondetrecord = PodEvaluacionDetRecord(podevaluaciondet_id=int(request.POST['id']),
                                                                    observacionenvia=f.cleaned_data['observacionenvia'],
                                                                    tipoformulacio=1 if request.POST['tipo'] == 'P' else 2,
                                                                    estado=5)
                    if 'misionpuesto' in request.POST:
                        podevaluaciondetrecord.misionpuesto = request.POST['misionpuesto']
                    podevaluaciondetrecord.save(request)
                    #PRODUCTOS/SERVICIOS
                    productos = request.POST.getlist('producto[]')
                    # prointermedio = request.POST.getlist('productointer[]')
                    # conespecifico = request.POST.getlist('conoespe[]')
                    # aplicacion = request.POST.getlist('aplica')

                    c = 0
                    while c < len(productos):
                        proevadet = PodProductoEvaDet(producto_id=int(productos[c]),
                                                      prointermedio=productos[c + 1],
                                                      conespe=productos[c + 2],
                                                      aplicacon=int(productos[c + 3]))
                        proevadet.save()
                        relacion = PodEvaDetProductoRelacion(podevadetcab_id=podevaluaciondetrecord.id,
                                                             podevametadet_id=proevadet.id)
                        relacion.save()
                        c+=4

                    #RELACIONES INTERNAS/EXTERNAS
                    internos = request.POST.getlist('interno[]')
                    externos = request.POST.getlist('externo[]')

                    c = 0
                    while c < len(internos):
                        intext = PodRelIntExt(interno=internos[c],
                                              externo=externos[c])
                        intext.save()
                        relacion = PodEvaDetIERelacion(podevadetcab_id=podevaluaciondetrecord.id,
                                                       podcomlabdet_id=intext.id)
                        relacion.save()
                        c+=1

                    #COMPETENCIAS TECNICAS/CONDUCTUALES
                    comptecid = request.POST.getlist('comptecid[]')
                    niveltec = request.POST.getlist('niveltec[]')
                    # compobstec = request.POST.getlist('compobstec[]')

                    compconid = request.POST.getlist('compconid[]')
                    nivelcon = request.POST.getlist('nivelcon[]')
                    # compobscon = request.POST.getlist('compobscon[]')

                    c = 0
                    while c < len(comptecid):
                        if niveltec[c] == 'ALTO':
                            lvl = 1
                        elif niveltec[c] == 'MEDIO':
                            lvl = 2
                        else:
                            lvl = 3
                        relaciones = PodDiccionarioCompLabRelacion.objects.get(complaboralcab_id=int(comptecid[c]),
                                                                               complaboraldet__nivel=lvl)
                        relacionevaxcamplab = PodEvaDetCompLabRelacion(podevadetcab_id=podevaluaciondetrecord.id,
                                                                       podcomlabdet_id=relaciones.id)
                        relacionevaxcamplab.save()
                        c+=1

                    c = 0
                    while c < len(compconid):
                        if niveltec[c] == 'ALTO':
                            lvl = 1
                        elif niveltec[c] == 'MEDIO':
                            lvl = 2
                        else:
                            lvl = 3
                        relaciones = PodDiccionarioCompLabRelacion.objects.get(complaboralcab_id=int(compconid[c]),
                                                                               complaboraldet__nivel=lvl)
                        relacionevaxcamplab = PodEvaDetCompLabRelacion(podevadetcab_id=podevaluaciondetrecord.id,
                                                                       podcomlabdet_id=relaciones.id)
                        relacionevaxcamplab.save()
                        c+=1

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
                                                                        puntaje=null_to_decimal(float(request.POST['%s' % f.id]), 2))
                            podevaluaciondetcali.save(request)
                            if f.podfactor.tipofactor == 1:
                                puntaje += podevaluaciondetcali.puntaje
                            elif f.podfactor.tipofactor == 2:
                                puntaje -= podevaluaciondetcali.puntaje
                        podevaluaciondetrecord.podevaluaciondet.estadoeva = 5
                        podevaluaciondetrecord.puntaje = null_to_decimal(float(request.POST['total']), 2)
                        podevaluaciondetrecord.save(request)
                    podevaluaciondetrecord.podevaluaciondet.save(request)
                    log(u'añadio record pod: %s' % podevaluaciondetrecord, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
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
                caracteristicas = request.POST.getlist('catacteristica[]')
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
                        podevaluaciondetrecord.podevaluacion.estadoevameta = 5
                        podevaluaciondetrecord.puntaje = null_to_decimal(float(request.POST['total']), 2)
                        podevaluaciondetrecord.save(request)
                    podevaluaciondetrecord.podevaluacion.save(request)
                    log(u'añadio record pod: %s' % podevaluaciondetrecord, request, "add")
                    if request.POST['tipo'] == 'P':
                        c = 0
                        while c < len(caracteristicas):
                            prod= ProductoServicioTh.objects.get(pk=int(caracteristicas[c]))
                            producto = PodEvaluacionMeta(
                                producto=prod,
                                indicador=caracteristicas[c+1].upper(),
                                mproyectada=caracteristicas[c+2],
                                observacion=caracteristicas[c+5])
                            c += 6
                            producto.save(request)
                            log(u'Añadio meta pod: %s' % producto, request, "add")
                            relacion = PodEvaluacionRelacionMeta(
                                evaluacion_id=podevaluaciondetrecord.id,
                                meta_id=producto.id
                            )
                            relacion.save(request)
                            log(u'Añadido record pod: %s' % relacion, request, "add")
                    else:
                        c = 0
                        while c < len(caracteristicas):
                            prod = ProductoServicioTh.objects.get(pk=int(caracteristicas[c]))
                            producto = PodEvaluacionMeta(
                                producto=prod,
                                indicador=caracteristicas[c + 1].upper(),
                                mproyectada=caracteristicas[c + 2],
                                mcumplida=caracteristicas[c + 3],
                                porcentajecumplimiento=caracteristicas[c + 4],
                                observacion=caracteristicas[c + 5])
                            c += 6
                            producto.save(request)
                            log(u'añadio meta pod: %s' % producto, request, "add")
                            relacion = PodEvaluacionRelacionMeta(
                                evaluacion_id=podevaluaciondetrecord.id,
                                meta_id=producto.id
                            )
                            relacion.save(request)
                            log(u'añadio record pod: %s' % relacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'ingresopodevajefenotainterna':
            try:
                f = MetasUnidadArchivoForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    #ext = newfilesd[newfilesd.rfind("."):]

                    extension = newfilesd.split('.')
                    tam = len(extension)
                    ext = extension[tam - 1].lower()

                    if ext == 'pdf' or ext == 'xls' or ext == 'xlsx':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.xls,.xlsx"})
                    if d.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if f.is_valid():
                    podevaluacion = PodEvaluacion.objects.get(pk=int(request.POST['id']))
                    podevaluacion.metanotai=f.cleaned_data['nota']
                    podevaluacion.metaobservacioni=f.cleaned_data['observacion']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("%s_NotaInterna_" % podevaluacion.id, newfile._name)
                        podevaluacion.metaarchivoi = newfile
                    podevaluacion.save(request)
                    log(u'Edito notas interna: %s' % podevaluacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'notaexterno':
            try:
                f = MetasUnidadArchivoForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    #ext = newfilesd[newfilesd.rfind("."):]

                    extension = newfilesd.split('.')
                    tam = len(extension)
                    ext = extension[tam - 1].lower()

                    if ext == 'pdf' or ext == 'xls' or ext == 'xlsx':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.xls,.xlsx"})
                    if d.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if f.is_valid():
                    podevaluacion = PodPeriodo.objects.get(pk=int(request.POST['id']))
                    podevaluacion.metanotae=f.cleaned_data['nota']
                    podevaluacion.metaobservacione=f.cleaned_data['observacion']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("%s_NotaExterno_" % podevaluacion.id, newfile._name)
                        podevaluacion.metaarchivoe = newfile
                    podevaluacion.save(request)
                    log(u'Edito notas externo: %s' % podevaluacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addproducto':
            try:
                f = PodEvaluacionMetaForm(request.POST)
                producto = ProductoServicioSeccion.objects.get(pk=int(request.POST['producto'])).producto

                if f.is_valid():
                    evaluacionmeta = PodEvaluacionMeta(evaluacion_id = request.POST['id'],
                                                       producto = producto,
                                                       indicador = f.cleaned_data['indicador'],
                                                       mproyectada = f.cleaned_data['mproyectada'],
                                                       mcumplida = f.cleaned_data['mcumplida'],
                                                       porcentajecumplimiento = f.cleaned_data['porcentajecumplimiento'],
                                                       observacion = f.cleaned_data['observacion']
                                                       )

                    evaluacionmeta.save(request)
                    log(u'Edito notas externo: %s' % evaluacionmeta, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                     raise NameError('Error')
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'editproducto':
            try:
                f = PodEvaluacionMetaForm(request.POST)
                evaluacionmeta=PodEvaluacionMeta.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    evaluacionmeta.indicador=f.cleaned_data['indicador']
                    evaluacionmeta.mproyectada=f.cleaned_data['mproyectada']
                    evaluacionmeta.mcumplida=f.cleaned_data['mcumplida']
                    evaluacionmeta.porcentajecumplimiento=f.cleaned_data['porcentajecumplimiento']
                    evaluacionmeta.observacion=f.cleaned_data['observacion']
                    evaluacionmeta.save(request)
                    log(u'Edito notas externo: %s' % evaluacionmeta, request, "editproducto")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})
        elif action == 'deleteproducto':
            try:
                registro = PodEvaluacionMeta.objects.get(pk=request.POST['id'])
                registro.status = False
                registro.save(request)
                log(u'Elimino Producto: %s' % registro, request, "deleteproducto")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Periodo POD'
                    data['form'] = PodPeriodoForm()
                    return render(request, 'pod_periodo/add.html', data)
                except Exception as ex:
                    pass

            elif action == 'ver_meta':
                try:
                    data = {}
                    podevaluacion = PodEvaluacion.objects.get(pk=int(request.GET['idpod']))
                    data['evaluado'] = podevaluacion.evaluador
                    data['departamento'] = podevaluacion.departamento
                    data['podevaluacion'] = podevaluacion
                    data['tipo'] = request.GET['tipo']
                    if request.GET['tipo'] == 'P':
                        template = get_template("pod_periodo/ver_meta.html")
                    else:
                        template = get_template("pod_periodo/ver_meta2.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            elif action == 'edit':
                try:
                    data['title'] = u'Modificar Periodo POD'
                    data['periodo'] = periodo = PodPeriodo.objects.get(pk=request.GET['id'])
                    form = PodPeriodoForm(initial={"anio": periodo.anio,
                                                   "descripcion": periodo.descripcion,
                                                   "inicio": periodo.inicio,
                                                   "fin": periodo.fin,
                                                   "inicioeval": periodo.inicioeval,
                                                   "fineval": periodo.fineval,
                                                   "iniciopod": periodo.iniciopod,
                                                   "finpod": periodo.finpod,
                                                   "publicacion": periodo.publicacion})
                    form.edit()
                    data['form'] = form
                    return render(request, 'pod_periodo/edit.html', data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Periodo POD'
                    data['periodo'] = PodPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, 'pod_periodo/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'planificar':
                try:
                    data['title'] = u'Planificar'
                    data['periodopod'] = PodPeriodo.objects.get(pk=request.GET['id'])
                    data['meses'] = MONTH_CHOICES
                    depa = data['depa'] = int(request.GET['departamento']) if 'departamento' in request.GET else 0
                    podevaluacion = PodEvaluacionDet.objects.filter(podperiodo_id=int(request.GET['id']), status=True).order_by("departamento", "evaluado").distinct("departamento__nombre", "evaluado__apellido1", "evaluado__apellido2", "evaluado__nombres")
                    data['departamento'] = Departamento.objects.filter(podevaluaciondet__podperiodo_id=int(request.GET['id']), podevaluaciondet__status=True, status=True).distinct()
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
                    if depa != 0:
                        podevaluacion = podevaluacion.filter(departamento_id=depa).distinct("departamento__nombre", "evaluado__apellido1", "evaluado__apellido2", "evaluado__nombres")
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

                    return render(request, 'pod_periodo/planificar.html', data)
                except Exception as ex:
                    pass


            elif action == 'productos':
                try:
                    data['title'] = u'Productos'
                    data['evaluacion'] = evaluacion = PodEvaluacion.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo = evaluacion.podperiodo

                    data['departameto'] = departamento = evaluacion.departamento

                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        metas = PodEvaluacionMeta.objects.filter((Q(producto__nombre__icontains=search) | Q(indicador__icontains=search)), evaluacion=evaluacion, status=True)
                    else:
                        metas = PodEvaluacionMeta.objects.filter(status=True,evaluacion=evaluacion)
                    paging = MiPaginador(metas, 25)
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
                    data['metas'] = page.object_list
                    return render(request, "pod_periodo/productos.html", data)
                except Exception as ex:
                    pass


            if action == 'addproducto':
                try:
                    data['form2'] = form = PodEvaluacionMetaForm()
                    data['id'] = pk=request.GET['id']
                    data['action'] = action
                    evaluacion = PodEvaluacion.objects.get(pk=pk)
                    form.adicionar(evaluacion.departamento)
                    template = get_template("pod_periodo/modal/formproducto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editproducto':
                try:
                    data['title']='Editar Producto'
                    data['id'] = pk = int(encrypt(request.GET['id']))
                    producto = PodEvaluacionMeta.objects.get(pk=pk)
                    form=PodEvaluacionMetaForm(initial=model_to_dict(producto))
                    form.fields['producto'].queryset=ProductoServicioSeccion.objects.filter(producto=producto.producto)
                    form.edit()
                    data['form2']=form
                    data['action']=action
                    template = get_template("pod_periodo/modal/formproducto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'deleteproducto':
                try:
                    data['title'] = u'Eliminar Producto '
                    data['producto'] = PodEvaluacionMeta.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['action'] = action
                    return render(request, 'pod_periodo/deleteproducto.html', data)
                except Exception as ex:
                    pass
            elif action == 'adicionar_grupos':
                try:
                    data = {}
                    data['departamento'] = Departamento.objects.filter(distributivopersona__regimenlaboral_id__in=[1, 4], status=True, distributivopersona__estadopuesto__id=PUESTO_ACTIVO_ID, distributivopersona__status=True).distinct()
                    data['idp'] = request.GET['id']
                    template = get_template("pod_periodo/adicionar_grupos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'agregar_funcionario':
                try:
                    data = {}
                    data['idp'] = request.GET['id']
                    data['idd'] = request.GET['depa']
                    data['action'] = 'agregar_funcionario'
                    data['permite_modificar'] = True
                    data['form'] = PodEvaluacionDetForm()
                    template = get_template("pod_periodo/agregar_funcionario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'agredar_director':
                try:
                    data = {}
                    data['idp'] = request.GET['id']
                    data['idd'] = request.GET['depa']
                    data['action'] = 'agredar_director'
                    data['permite_modificar'] = True
                    data['form'] = PodEvaluacionDetForm()
                    template = get_template("pod_periodo/agregar_funcionario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ingresopodeva':
                try:
                    data = {}
                    podevaluaciondet = PodEvaluacionDet.objects.get(pk=int(request.GET['iddet']))
                    data['evaluado'] = podevaluaciondet.evaluado
                    data['podevaluaciondet'] = podevaluaciondet
                    data['departamento'] = podevaluaciondet.departamento
                    data['tipo'] = request.GET['tipo']
                    data['record'] = PodEvaluacionDetRecord.objects.filter(status=True, podevaluaciondet=podevaluaciondet, tipoformulacio=1 if request.GET['tipo'] == 'P' else 2)
                    template = get_template("pod_periodo/ingresopodeva.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ingresopodevajefe':
                try:
                    data = {}
                    podevaluacion = PodEvaluacion.objects.get(pk=int(request.GET['iddet']))
                    data['podevaluacion'] = podevaluacion
                    if request.GET['tipo'] == 'P':
                        data['permite_modificar'] = podevaluacion.puede_ingresar_pod_meta_adm()
                    else:
                        data['permite_modificar'] = podevaluacion.puede_ingresar_eva_meta_adm()
                    data['departamento'] = podevaluacion.departamento
                    data['tipo'] = request.GET['tipo']
                    data['record'] = PodEvaluacionDetRecordMeta.objects.filter(status=True, podevaluacion=podevaluacion, tipoformulacio=1 if request.GET['tipo'] == 'P' else 2)
                    template = get_template("pod_periodo/ingresopodevajefe.html")
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
                    form = PodEvaluacionDetCalificaForm(initial={'estado': podevaluaciondetrecord.estado, 'observacionaprobador': podevaluaciondetrecord.observacionaprobador})
                    form.aprobar_choise()
                    data['form'] = form
                    data['permite_modificar'] = not podevaluaciondetrecord.notificado
                    template = get_template("pod_periodo/editar_record.html")
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
                    form = PodEvaluacionDetCalificaForm(initial={'estado': podevaluaciondetrecord.estado, 'observacionaprobador': podevaluaciondetrecord.observacionaprobador})
                    form.aprobar_choise()
                    data['form'] = form
                    data['permite_modificar'] = not podevaluaciondetrecord.notificado
                    template = get_template("pod_periodo/editar_record_meta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_metas':
                try:
                    data = {}
                    podevaluaciondetrecord = PodEvaluacionDetRecordMeta.objects.get(pk=int(request.GET['metas']))
                    data['tipo'] = request.GET['tipo']
                    data['replanificarcordmeta'] = podevaluaciondetrecord
                    data['metas'] = PodEvaluacionRelacionMeta.objects.filter(evaluacion=podevaluaciondetrecord,status=True)
                    template = get_template("pod_periodo/ver_metas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_fichapod':
                try:
                    data = {}
                    data['podevaluaciondetrecord'] = podevaluaciondetrecord = PodEvaluacionDetRecord.objects.get(pk=int(request.GET['ficha']))
                    data['productos'] = PodEvaDetProductoRelacion.objects.filter(podevadetcab_id=podevaluaciondetrecord.id)
                    data['relaciones'] = PodEvaDetIERelacion.objects.filter(podevadetcab_id=podevaluaciondetrecord.id)
                    data['competencias'] = PodEvaDetCompLabRelacion.objects.filter(podevadetcab_id=podevaluaciondetrecord.id)

                    template = get_template("pod_periodo/ver_fichapod.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_fichapode':
                try:
                    data = {}
                    data['podevaluaciondetrecord'] = podevaluaciondetrecord = PodEvaluacionDetRecord.objects.get(pk=int(request.GET['ficha']))
                    data['productos'] = PodEvaDetProductoRelacion.objects.filter(podevadetcab_id=podevaluaciondetrecord.id)
                    data['relaciones'] = PodEvaDetIERelacion.objects.filter(podevadetcab_id=podevaluaciondetrecord.id)
                    data['competencias'] = PodEvaDetCompLabRelacion.objects.filter(podevadetcab_id=podevaluaciondetrecord.id)
                    template = get_template("pod_periodo/ver_fichapod_e.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_com':
                try:
                    data = {}
                    data['tipo'] = tipo = request.GET['tipo']
                    if tipo == 'tecnico':
                        diccionario = CompetenciaLaboral.objects.filter(status=True, tipo=1)
                    else:
                        diccionario = CompetenciaLaboral.objects.filter(status=True, tipo=2)
                    data['diccionarios'] = diccionario
                    template = get_template("pod_periodo/ver_diccionario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_comportamiento':
                try:
                    data = {}
                    poddic = PodDiccionarioCompLabRelacion.objects.filter(complaboralcab_id=int(request.GET['comportamiento']))
                    data['compobservable'] = poddic
                    template = get_template("pod_periodo/ver_compotamiento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addevapod':
                try:
                    podevaluaciondet = PodEvaluacionDet.objects.get(pk=int(request.GET['id']))
                    data['tipo'] = request.GET['tipo']
                    form = PodEvaluacionDetArchivoForm()
                    formpc = PodProductoCompetenciaForm()
                    data['form2'] = form
                    data['form'] = formpc
                    data['podevaluaciondet'] = podevaluaciondet
                    data['action'] = 'agregar_record'
                    if request.GET['tipo'] == 'P':
                        data['permite_modificar'] = puedemod = podevaluaciondet.puede_ingresar_pod_adm()
                    else:
                        data['factores'] = PodPeridoFactor.objects.filter(podperiodo=podevaluaciondet.podperiodo,
                                                                          status=True).order_by("orden")
                        data['permite_modificar'] = puedemod = podevaluaciondet.puede_ingresar_eva_adm()
                    data['title'] = u'Adicionar Planificación de POD'
                    if not puedemod:
                        messages.warning(request,'NO ESTA ACTIVO LA MODIFICACIÓN')
                        return redirect('/pod_periodo?action=planificar&id={}'.format(podevaluaciondet.podperiodo.id))
                    else:
                        return render(request, 'pod_periodo/addevapod.html', data)
                except Exception as ex:
                    pass

            elif action == 'addcalpod':
                try:
                    podevaluaciondetrecord = PodEvaluacionDetRecord.objects.get(podevaluaciondet_id=int(request.GET['id']))
                    data['productos'] = PodEvaDetProductoRelacion.objects.filter(
                        podevadetcab_id=podevaluaciondetrecord.id)
                    data['relaciones'] = PodEvaDetIERelacion.objects.filter(podevadetcab_id=podevaluaciondetrecord.id)
                    data['competencias'] = PodEvaDetCompLabRelacion.objects.filter(
                        podevadetcab_id=podevaluaciondetrecord.id)
                    podevaluaciondet = PodEvaluacionDet.objects.get(pk=int(request.GET['id']))
                    data['tipo'] = request.GET['tipo']
                    form = PodEvaluacionDetArchivoForm()
                    data['form2'] = form
                    data['podevaluaciondet'] = podevaluaciondet
                    data['action'] = 'agregar_record'
                    if request.GET['tipo'] == 'P':
                        data['permite_modificar'] = podevaluaciondet.puede_ingresar_pod_adm()
                    else:
                        data['factores'] = PodPeridoFactor.objects.filter(podperiodo=podevaluaciondet.podperiodo,
                                                                          status=True).order_by("orden")
                        data['permite_modificar'] = podevaluaciondet.puede_ingresar_eva_adm()
                    data['title'] = u'Adicionar Planificación de POD'
                    return render(request, 'pod_periodo/addcalpod.html', data)
                except Exception as ex:
                    pass

            elif action == 'buscarproductos':
                try:
                    q = request.GET['q'].upper().strip()
                    # per = PodEvaluacionMeta.objects.filter(Q(producto__icontains=q), Q(status=True))
                    per = PodEvaluacionRelacionMeta.objects.filter(meta__producto__nombre__icontains=q, meta__mcumplida__gte=1, evaluacion__podevaluacion__departamento=int(request.GET['dep']), evaluacion__estado=3)
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{}".format(x.meta.producto)}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'buscarcompetenciastec':
                try:
                    q = request.GET['q'].upper().strip()
                    per = PodDiccionarioCompLaboral.objects.filter(Q(denominacion__icontains=q) & Q(tipo=1), Q(status=True))

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{}".format(x.denominacion)}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'aggcompetenciatec':
                try:
                    data = {}
                    # comptecnica = PodDiccionarioCompLaboral.objects.filter(Q(pk=int(request.GET['tec'])) & Q(tipo=int(request.GET['estado'])), Q(status=True))
                    comptecnica = PodDiccionarioCompLabRelacion.objects.get(Q(complaboralcab__pk=int(request.GET['tec'])) & Q(complaboraldet__nivel=int(request.GET['estado'])), Q(status=True))
                    return JsonResponse({"result": "ok", 'ct': comptecnica.complaboralcab.denominacion, 'nivel': comptecnica.complaboraldet.nivel, 'co': comptecnica.complaboraldet.compobservable})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarcompetenciascon':
                try:
                    q = request.GET['q'].upper().strip()
                    per = PodDiccionarioCompLaboral.objects.filter(Q(denominacion__icontains=q) & Q(tipo=2), Q(status=True))
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{}".format(x.denominacion)}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

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
                        data['permite_modificar'] = podevaluaciondet.puede_ingresar_pod_adm()
                    else:
                        data['factores'] = PodPeridoFactor.objects.filter(podperiodo=podevaluaciondet.podperiodo, status=True).order_by("orden")
                        data['permite_modificar'] = podevaluaciondet.puede_ingresar_eva_adm()
                    template = get_template("pod_periodo/agregar_record.html")
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
                    data['productospod'] = PodEvaluacionMeta.objects.filter(status=True).order_by('producto__nombre')
                    if request.GET['tipo'] == 'P':
                        data['permite_modificar'] = podevaluacion.puede_ingresar_pod_meta_adm()
                    else:
                        if PodEvaluacionDetRecordMeta.objects.filter(podevaluacion = podevaluacion, estado=3, status=True).order_by('-id').exists():
                            ulreg = PodEvaluacionDetRecordMeta.objects.filter(podevaluacion=podevaluacion).order_by('-id')[0]
                            data['metas'] = PodEvaluacionRelacionMeta.objects.filter(evaluacion=ulreg, status=True).order_by('id')
                        # data['factores'] = PodPeridoFactor.objects.filter(podperiodo=podevaluaciondet.podperiodo, status=True).order_by("orden")
                        data['permite_modificar'] = podevaluacion.puede_ingresar_eva_meta_adm()
                    template = get_template("pod_periodo/agregar_record_meta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'planificar_fechas':
                try:
                    data = {}
                    data['idp'] = request.GET['idp']
                    data['departamento'] = Departamento.objects.get(pk=int(request.GET['idd']))
                    data['evaluado'] = Persona.objects.get(pk=int(request.GET['ide']))
                    data['fechas'] = PodEvaluacionDet.objects.filter(departamento=data['departamento'], evaluado=data['evaluado'], podperiodo_id=int(request.GET['idp']), status=True).order_by("inicio")
                    template = get_template("pod_periodo/planificar_fechas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscar_usuario':
                try:
                    data = {}
                    data['personal'] = DistributivoPersona.objects.filter(regimenlaboral_id__in=[1], estadopuesto__id=PUESTO_ACTIVO_ID, unidadorganica_id=int(request.GET['idd']), status=True).exclude(persona__in=Persona.objects.filter(podevaluaciondet__departamento__id=int(request.GET['idd']), podevaluaciondet__podperiodo__id=int(request.GET['idp']), podevaluaciondet__status=True))
                    template = get_template("pod_periodo/buscar_usuario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delete_evaluado':
                try:
                    data['title'] = u'Eliminar Evaluado'
                    data['podevaluaciondet'] = PodEvaluacionDet.objects.get(pk=request.GET['id'])
                    return render(request, 'pod_periodo/delete_evaluado.html', data)
                except Exception as ex:
                    pass

            elif action == 'factores':
                try:
                    data['title'] = u'Factores de evaluación del período'
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        factores = PodFactor.objects.filter(descripcion__icontains=search, status=True)
                    else:
                        factores = PodFactor.objects.filter(status=True)
                    paging = MiPaginador(factores, 25)
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
                    data['factores'] = page.object_list
                    return render(request, "pod_periodo/factores.html", data)
                except Exception as ex:
                    pass

            elif action == 'diccomlab':
                try:
                    data['title'] = u'Diccionario de Competencias Laborales'
                    search = None
                    tipo = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        factores = PodDiccionarioCompLaboral.objects.filter(descripcion__icontains=search, status=True).order_by('id')
                    else:
                        factores = PodDiccionarioCompLaboral.objects.filter(status=True).order_by('id')
                    paging = MiPaginador(factores, 25)
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
                    data['factores'] = page.object_list
                    return render(request, "pod_periodo/diccomlab.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddiccomlab':
                try:
                    data['title'] = u'Adicionar Diccionario de Competencia Laborales'
                    data['form'] = PodDiccionarioCompLaboralForm()
                    return render(request, 'pod_periodo/adddiccomlab.html', data)
                except Exception as ex:
                    pass

            elif action == 'editdiccomlab':
                try:
                    data['title'] = u'Modificar Diccionario de Competencia Laborales'
                    data['dicom'] = factor = PodDiccionarioCompLaboral.objects.get(pk=request.GET['id'])
                    data['rel'] = PodDiccionarioCompLabRelacion.objects.filter(complaboralcab_id=factor.id)
                    data['form'] = PodDiccionarioCompLaboralForm(initial={"tipo": factor.tipo,
                                                          "denominacion": factor.denominacion,
                                                          "definicion": factor.definicion})
                    return render(request, 'pod_periodo/editdiccomlab.html', data)
                except Exception as ex:
                    pass

            elif action == 'deletediccomlab':
                try:
                    data['title'] = u'Diccionario de Competencia Laborales'
                    data['diccionario'] = PodDiccionarioCompLaboral.objects.get(pk=request.GET['id'])
                    return render(request, 'pod_periodo/deletediccomlab.html', data)
                except Exception as ex:
                    pass

            elif action == 'addfactor':
                try:
                    data['title'] = u'Adicionar Factor de Evaluación'
                    data['form'] = PodFactorForm()
                    return render(request, 'pod_periodo/addfactor.html', data)
                except Exception as ex:
                    pass

            elif action == 'editfactor':
                try:
                    data['title'] = u'Modificar Factor de Evaluación'
                    data['factor'] = factor = PodFactor.objects.get(pk=request.GET['id'])
                    data['form'] = PodFactorForm(initial={"tipofactor": factor.tipofactor,
                                                          "minimo": factor.minimo,
                                                          "maximo": factor.maximo,
                                                          "descripcion": factor.descripcion})
                    return render(request, 'pod_periodo/editfactor.html', data)
                except Exception as ex:
                    pass

            elif action == 'deletefactor':
                try:
                    data['title'] = u'Eliminar Factor de Evaluacion'
                    data['factor'] = PodFactor.objects.get(pk=request.GET['id'])
                    return render(request, 'pod_periodo/deletefactor.html', data)
                except Exception as ex:
                    pass

            elif action == 'factoresperiodo':
                try:
                    data['title'] = u'Factores de evaluación del período'
                    data['periodo'] = periodo = PodPeriodo.objects.get(pk=request.GET['id'])
                    data['factores'] = periodo.podperidofactor_set.all().order_by('orden')
                    return render(request, "pod_periodo/factoresperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfactorperiodo':
                try:
                    data['title'] = u'Adicionar Factor de Evaluación'
                    form = PodPeriodoFactorForm()
                    data['periodo'] = periodo = PodPeriodo.objects.get(pk=request.GET['id'])
                    form.adicionar()
                    data['form'] = form
                    return render(request, 'pod_periodo/addfactorperiodo.html', data)
                except Exception as ex:
                    pass

            elif action == 'resultado':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'
                    periodo = request.GET['periodo']
                    podperidofactor = PodPeridoFactor.objects.filter(podperiodo_id=int(periodo), status=True).order_by("orden")
                    columns = [
                        (u"Nº.", 2000),
                        (u"CÉDULA", 3000),
                        (u"EMPLEADO", 9000),
                        (u"DEPARTAMENTO", 9000),
                        (u"EVALUADOR", 9000),
                        (u"CALIFICACIÓN", 3000),
                        (u"APROBADO", 3000),
                    ]
                    for x in podperidofactor:
                        columns.append((x.podfactor.descripcion, 6000),)
                    row_num = 3
                    columns.append((u"Escala Calificación", 3000),)
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 4
                    i = 0
                    for r in PodEvaluacionDet.objects.filter(podperiodo_id=int(periodo), status=True).order_by("departamento", "evaluado"):
                        i += 1
                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, r.evaluado.cedula, font_style2)
                        ws.write(row_num, 2, r.evaluado.nombre_completo_inverso(), font_style2)
                        ws.write(row_num, 3, r.departamento.nombre, font_style2)
                        ws.write(row_num, 4, r.director().evaluador.nombre_completo_inverso() if r.director() else [], font_style2)
                        record = r.podevaluaciondetrecord_set.filter(tipoformulacio=2, status=True, estado__in=[1, 3, 5]).order_by("-fecha_creacion")[0] if r.podevaluaciondetrecord_set.filter(tipoformulacio=2, status=True, estado__in=[1, 3, 5]) else []
                        ws.write(row_num, 5, record.puntaje if record else 0, style0)
                        ws.write(row_num, 6, r.get_estadoeva_display(), font_style2)
                        c = 7
                        for x in podperidofactor:
                            ws.write(row_num, c, x.calificacion(record=record), font_style2)
                            c += 1
                        escala = "Sin Calificar"
                        if record:
                            if record.puntaje >= 91:
                                escala = "Excelente"
                            elif record.puntaje >= 81:
                                escala = "Muy Bueno"
                            elif record.puntaje >= 71:
                                escala = "Satisfactoria"
                            elif record.puntaje >= 61:
                                escala = "Deficiente"
                            else:
                                escala = "Inaceptable"
                        ws.write(row_num, c, escala, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'seguimiento':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'
                    periodo = request.GET['periodo']
                    # podperidofactor = PodPeridoFactor.objects.filter(podperiodo_id=int(periodo), status=True).order_by("orden")
                    columns = [
                        (u"DEPARTAMENTO EVALUACION", 9000),
                        (u"MODALIDAD LABORAL", 9000),
                        (u"NÚMERO IDENTIFICACIÓN", 3000),
                        (u"NOMBRES", 9000),
                        (u"DENOMINACIÓN PUESTO ACTUAL", 9000),
                        (u"UNIDAD ORGÁNICA", 9000),
                        (u"PERIODO DE EVALUACION INICIO", 9000),
                        (u"PERIODO DE EVALUACION FIN", 9000),
                        (u"ESTADO P", 3000),
                        (u"ESTADO E", 3000),
                        (u"PUNTAJE", 3000),
                    ]
                    # for x in podperidofactor:
                    #     columns.append((x.podfactor.descripcion, 6000),)
                    row_num = 3
                    # columns.append((u"Escala Calificación", 3000),)
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 4
                    i = 0
                    for r in PodEvaluacionDet.objects.filter(podperiodo_id=int(periodo), status=True).order_by("departamento", "evaluado"):
                        i += 1
                        departamento1 = r.departamento
                        if departamento1:
                            ws.write(row_num, 0, departamento1.nombre, font_style2)
                        else:
                            ws.write(row_num, 0, '', font_style2)

                        modalidad = r.evaluado.mis_modalidad_actuales2()
                        if modalidad:
                            ws.write(row_num, 1, modalidad.descripcion, font_style2)

                        ws.write(row_num, 2, r.evaluado.cedula, font_style2)
                        ws.write(row_num, 3, r.evaluado.nombre_completo_inverso(), font_style2)

                        cargo = r.denominacionpuesto
                        if cargo:
                            ws.write(row_num, 4, cargo.descripcion, font_style2)

                        unidadorganica = r.unidadorganica
                        if unidadorganica:
                            ws.write(row_num, 5, unidadorganica.nombre, font_style2)

                        ws.write(row_num, 6, str(r.inicio), font_style2)
                        ws.write(row_num, 7, str(r.fin), font_style2)
                        # ws.write(row_num, 4, r.director().evaluador.nombre_completo_inverso() if r.director() else [], font_style2)
                        estadopod1 = ""
                        if r.estadopod==3:
                            estadopod1 = "POD Aceptado"
                        if r.estadopod==2:
                            estadopod1 = "POD en Espera de Aprobación"
                        if r.estadopod==4:
                            estadopod1 = "POD Rechazado"
                        if r.estadopod==5:
                            estadopod1 = "En Revisión"
                        if r.estadopod==1:
                            estadopod1 = "POD sin Archivos"
                        ws.write(row_num, 8, estadopod1, font_style2)
                        estadoeva1 = ""
                        if r.estadoeva==3:
                            estadoeva1 = "Evaluación Aceptado"
                        if r.estadoeva==2:
                            estadoeva1 = "Evaluación en Espera de Aprobación"
                        if r.estadoeva==4:
                            estadoeva1 = "Evaluación Rechazado"
                        if r.estadoeva==5:
                            estadoeva1 = "En Revisión"
                        if r.estadoeva==1:
                            estadoeva1 = "Evaluación sin Archivos"
                        ws.write(row_num, 9, estadoeva1, font_style2)
                        record = r.podevaluaciondetrecord_set.filter(tipoformulacio=2, status=True, estado__in=[1, 3, 5]).order_by("-fecha_creacion")[0] if r.podevaluaciondetrecord_set.filter(tipoformulacio=2, status=True, estado__in=[1, 3, 5]) else []
                        ws.write(row_num, 10, record.puntaje if record else 0, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'editfactorperiodo':
                try:
                    data['title'] = u'Modificar Periodo POD'
                    data['periodo'] = periodo = PodPeriodo.objects.get(pk=request.GET['pod'])
                    data['factor'] = factor = PodPeridoFactor.objects.get(pk=request.GET['id'])
                    form = PodPeriodoFactorForm(initial={"podfactor": factor.podfactor,
                                                         "minimo": factor.minimo,
                                                         "maximo": factor.maximo,
                                                         "orden": factor.orden})
                    form.edit()
                    data['form'] = form
                    return render(request, 'pod_periodo/editfactorperiodo.html', data)
                except Exception as ex:
                    pass

            elif action == 'deletefactorperiodo':
                try:
                    data['title'] = u'Eliminar Factor de Evaluacion'
                    data['periodo'] = PodPeriodo.objects.get(pk=request.GET['pod'])
                    data['factor'] = PodPeridoFactor.objects.get(pk=request.GET['id'])
                    return render(request, 'pod_periodo/deletefactorperiodo.html', data)
                except Exception as ex:
                    pass

            elif action == 'ingresopodevajefenotainterna':
                try:
                    data = {}
                    podevaluacion = PodEvaluacion.objects.get(pk=int(request.GET['idpod']))
                    data['departamento'] = podevaluacion.departamento
                    data['podevaluacion'] = podevaluacion
                    data['form2'] = MetasUnidadArchivoForm(initial={'nota': podevaluacion.metanotai, 'observacion': podevaluacion.metaobservacioni})
                    # data['record'] = PodEvaluacionDetRecord.objects.filter(status=True, podevaluaciondet=podevaluaciondet, tipoformulacio=1 if request.GET['tipo'] == 'P' else 2)
                    template = get_template("pod_periodo/ingresopodevajefenotainterna.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'notaexterno':
                try:
                    data = {}
                    podperiodo = PodPeriodo.objects.get(pk=int(request.GET['idpod']))
                    data['podperiodo'] = podperiodo
                    data['form2'] = MetasUnidadArchivoForm(initial={'nota': podperiodo.metanotae, 'observacion': podperiodo.metaobservacione})
                    # data['record'] = PodEvaluacionDetRecord.objects.filter(status=True, podevaluaciondet=podevaluaciondet, tipoformulacio=1 if request.GET['tipo'] == 'P' else 2)
                    template = get_template("pod_periodo/notaexterno.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'resultadoevaluacion':
                try:
                    podperiodo = PodPeriodo.objects.get(pk=int(request.GET['periodo']))
                    data['podperiodo'] = podperiodo
                    data['detalles'] = PodEvaluacionDet.objects.filter(podperiodo=podperiodo, status=True, podevaluaciondetrecord__podevaluaciondetcali__isnull=False).distinct()
                    return conviert_html_to_pdf('pod_periodo/resultadoevaluacion.html',{'pagesize': 'A4 landscape', 'datos': data})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_cronograma?info=%s" % 'Error al generar informe de estudiantes de prácticas')

            elif action == 'resultadoevaluaciondetalle':
                try:
                    podperiodo = PodPeriodo.objects.get(pk=int(request.GET['periodo']))
                    data['podperiodo'] = podperiodo
                    data['detalles'] = PodEvaluacionDet.objects.filter(podperiodo=podperiodo, status=True, evaluado__id=int(request.GET['evaluado'])).distinct()
                    return conviert_html_to_pdf('pod_periodo/resultadoevaluacion.html',{'pagesize': 'A4 landscape', 'datos': data})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_cronograma?info=%s" % 'Error al generar informe de estudiantes de prácticas')


            elif action == 'resultadoevaluacion1':

                try:
                    __author__ = 'Unemi'
                    podperiodo = PodPeriodo.objects.get(pk=int(request.GET['periodo']))
                    podevaluaciondet = PodEvaluacionDet.objects.filter(podperiodo=podperiodo, status=True, podevaluaciondetrecord__podevaluaciondetcali__isnull=False).distinct()
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Times New Roman, color-index black, bold on , height 275; alignment: horiz centre')
                    subtitulo = easyxf('font: name Times New Roman, bold on, height 200; align:wrap on, horiz centre, vert centre')
                    normal = easyxf('font: name Times New Roman, height 200; alignment: horiz left')
                    nnormal = easyxf('font: name Times New Roman, height 200; alignment: horiz centre')
                    subtitulo.borders = borders
                    normal.borders = borders
                    nnormal.borders = borders
                    wb = Workbook(encoding='utf-8')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=RESULTADO_EVALUACION_' + random.randint(1, 10000).__str__() + '.xls'
                    ws = wb.add_sheet('Resultado_Evaluacion')
                    ws.write_merge(0, 0, 0, 15, 'INFORME CONSOLIDADO DE RESULTADOS', title)
                    ws.write_merge(1, 1, 0, 10, u'%s' % "ANALISIS DE RESULTADOS DE LA EVALUACION DE DESEMPEÑO INSTITUCIONAL", title2)
                    ws.col(0).width = 1000
                    ws.col(1).width = 5000
                    ws.col(2).width = 5000
                    ws.col(3).width = 5000
                    ws.col(4).width = 5000
                    ws.col(5).width = 5000
                    ws.col(6).width = 5000
                    ws.col(7).width = 5000
                    ws.col(8).width = 5000
                    ws.col(9).width = 5000
                    ws.col(10).width = 5000
                    ws.col(11).width = 5000
                    ws.col(12).width = 5000
                    ws.col(13).width = 5000
                    ws.col(14).width = 5000
                    ws.col(15).width = 5000
                    row_num = 2
                    c = 0
                    for factores in podperiodo.factores():
                        ws.write_merge(row_num + 2, row_num + 2, 7+c, 7+c, factores.descripcion, subtitulo)
                        c=c+1
                    ws.write_merge(row_num, row_num+2, 0, 0, u'N°', subtitulo)
                    ws.write_merge(row_num, row_num+2, 1, 1, u'NOMBRES Y APELLIDOS', subtitulo)
                    ws.write_merge(row_num, row_num+2, 2, 2, u'NÚMERO DE CEDULA', subtitulo)
                    ws.write_merge(row_num, row_num+2, 3, 3, u'PUESTO INSTITUCIONAL', subtitulo)
                    ws.write_merge(row_num, row_num+2, 4, 4, u'UNIDAD/PROCESO', subtitulo)
                    ws.write_merge(row_num, row_num+2, 5, 5, u'ROL DEL PUESTO', subtitulo)
                    ws.write_merge(row_num, row_num, 6, 6+c+3, u'FACTORES', subtitulo)
                    ws.write_merge(row_num+1, row_num+2, 6, 6, u'INDICADORES DE GESTION OPERATIVA', subtitulo)
                    ws.write_merge(row_num+1, row_num+1, 7, 7+c-1, u'NIVEL DE EFICIENCIA DEL DESEMPEÑO INDIVIDUAL', subtitulo)
                    ws.write_merge(row_num + 1, row_num + 2, 7+c, 7+c, u'NIVEL DE SATISFACCIÓN DE USUARIOS EXTERNOS', subtitulo)
                    ws.write_merge(row_num + 1, row_num + 2, 8+c, 8+c, u'NIVEL DE SATISFACCIÓN DE USUARIOS INTERNOS', subtitulo)
                    ws.write_merge(row_num + 1, row_num + 2, 9+c, 9+c, u'CUMPLIMIENTO DE NORMAS INTERNAS(-)', subtitulo)
                    ws.write_merge(row_num, row_num + 2, 10+c, 10+c, u'EVALUACIÓN CUANTITATIVA', subtitulo)
                    ws.write_merge(row_num, row_num + 2, 11+c, 11+c, u'EVALUACIÓN CUALITATIVA', subtitulo)
                    i = 0
                    row_num=row_num+3
                    for detalle in podevaluaciondet:
                        i = i+1
                        ws.write(row_num, 0, i.__str__(), normal)
                        ws.write(row_num, 1, detalle.evaluado.nombre_completo_inverso(), normal)
                        ws.write(row_num, 2, detalle.evaluado.cedula, normal)
                        if detalle.denominacionpuesto:
                            ws.write(row_num, 3, detalle.denominacionpuesto.descripcion, normal)
                        else:
                            ws.write(row_num, 3, '', normal)
                        if detalle.unidadorganica:
                            ws.write(row_num, 4, detalle.unidadorganica.nombre, normal)
                        else:
                            ws.write(row_num, 4, '', normal)
                        ws.write(row_num, 5, '', normal)
                        ws.write(row_num, 6, detalle.notapunto1().__str__(), normal)
                        cc = 0
                        for nivele in detalle.detallerecord():
                            ws.write(row_num, 7+cc, nivele.puntaje.__str__(), normal)
                            cc = cc+1
                        if cc < c:
                            while (cc < c):
                                ws.write(row_num, 7 + cc, "0", normal)
                                cc+=1
                        ws.write(row_num, 7+cc, detalle.notapunto3().__str__(), normal)
                        ws.write(row_num, 8+cc, detalle.notapunto4().__str__(), normal)
                        ws.write(row_num, 9+cc, detalle.notapunto5().__str__(), normal)
                        ws.write(row_num, 10+cc, detalle.sumatotal().__str__(), normal)
                        ws.write(row_num, 11+cc, detalle.resultado().__str__(), normal)
                        row_num = row_num + 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'EVAL Apertura'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                periodos = PodPeriodo.objects.filter(descripcion__icontains=search, status=True)
            else:
                periodos = PodPeriodo.objects.filter(status=True)
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
            return render(request, "pod_periodo/view.html", data)