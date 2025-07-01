# -*- coding: latin-1 -*-
import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
import sys
from xlwt import *
import xlwt
from xlrd import book
from xlsxwriter import workbook
from django.http import HttpResponse
import random
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import CriterioDocenciaForm, CriterioInvestigacionForm, CriterioGestionForm, \
    CriterioArticuloForm, DetalleActividadCriterioForm, \
    CriterioDocenciaMinimoMaximoPeriodoForm, CriterioInvestigacionMinimoMaximoPeriodoForm, \
    CriterioGestionMinimoMaximoPeriodoForm, RecursosForm, RecursoAprendizajeForm, RecursoAprendizajeauxForm, \
    RecursoAprendizajeRangoForm, ActividadRecursoAprendizajeForm, ActividadRecursoAprendizajeAuxForm, \
    CriterioVinculacionForm, CriterioVinculacionMinimoMaximoPeriodoForm, ActividadPrincipalForm
from sga.funciones import log, MiPaginador, puede_realizar_accion2
from sga.funciones_templatepdf import listadodocentescriterios
from sga.models import CriterioDocencia, CriterioInvestigacion, CriterioGestion, CriterioDocenciaPeriodo, \
    CriterioInvestigacionPeriodo, CriterioGestionPeriodo, CriterioArticulo, DetalleActividadesCriterio, \
    RecursoAprendizajeTipoProfesor, RecursoAprendizaje, RecursoAprendizajeTipoProfesorRango, \
    ActividadGestionRecursoAprendizaje, ActividadDocenciaRecursoAprendizaje, ActividadInvestigacionRecursoAprendizaje, \
    CriterioLink, CriterioVinculacionPeriodo, CriterioVinculacion, CriterioDocenciaPeriodoTitulacion, \
    PeriodoGrupoTitulacion, ActividadPrincipal, Periodo, DetalleDistributivo, Persona
from inno.models import *
from inno.forms import CriterioForm, SubactividadDocentePeriodoForm
from sga.templatetags.sga_extras import encrypt
from django.forms import model_to_dict

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    persona = request.session.get('persona')
    if 'action' in request.POST:
        action = request.POST['action']

        if action == 'importarconfiguracionactividadmacro':
            try:
                periodopasado = Periodo.objects.get(id=int(request.POST['p']))
                datacriterio = {}
                filtroactividad = Q(status=True)
                if tipo := int(request.POST['t']):
                    if tipo == 1 or tipo == 4:
                        datacriterio['criteriodocenciaperiodo_id'] = request.POST['id']
                        filtroactividad &= Q(criteriodocenciaperiodo__criterio=int(request.POST['criterio_id']), criteriodocenciaperiodo__periodo=periodopasado)
                    elif tipo == 2:
                        datacriterio['criterioinvestigacionperiodo_id'] = request.POST['id']
                        filtroactividad &= Q(criterioinvestigacionperiodo__criterio=int(request.POST['criterio_id']), criterioinvestigacionperiodo__periodo=periodopasado)
                    elif tipo == 3:
                        datacriterio['criteriogestionperiodo_id'] = request.POST['id']
                        filtroactividad &= Q(criteriogestionperiodo__criterio=int(request.POST['criterio_id']), criteriogestionperiodo__periodo=periodopasado)

                for actividad in ActividadDocentePeriodo.objects.filter(filtroactividad):
                    datacriterio['criterio_id'] = actividad.criterio.pk
                    nuevaactividad = actividad.criterio.actividaddocenteperiodo_set.filter(status=True).filter(**datacriterio).first()
                    if not nuevaactividad:
                        nuevaactividad = ActividadDocentePeriodo(**datacriterio)
                        nuevaactividad.save(request)

                    for subactividad in actividad.subactividaddocenteperiodo_set.filter(status=True).values():
                        for element in ['id', 'fecha_creacion', 'usuario_creacion_id', 'fecha_modificacion', 'usuario_modificacion_id']:
                            subactividad.pop(element)
                        subactividad['fechafin'] = periodo.fin
                        subactividad['fechainicio'] = periodo.inicio
                        subactividad['actividad_id'] = nuevaactividad.pk
                        if not SubactividadDocentePeriodo.objects.values('id').filter(actividad=nuevaactividad, criterio=subactividad['criterio_id'], status=True).exists():
                            nuevasubactividad = SubactividadDocentePeriodo(**subactividad)
                            nuevasubactividad.save(request)

                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f"{ex}"})

        if action == 'addcriteriodocenciapadre':
            try:
                form = CriterioDocenciaForm(request.POST)
                if form.is_valid():
                    if periodo.clasificacion == 1:
                        if CriterioDocencia.objects.filter(nombre=form.cleaned_data['texto'], dedicacion=form.cleaned_data['dedicacion']).exists():
                            criterio = CriterioDocencia.objects.get(nombre=form.cleaned_data['texto'], dedicacion=form.cleaned_data['dedicacion'])
                            criterio.pregrado = True
                            criterio.procesotutoriaacademica = form.cleaned_data['procesotutoriaacademica']
                            criterio.procesoimparticionclase = form.cleaned_data['procesoimparticionclase']
                            criterio.save(request)
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            criteriodocencia = CriterioDocencia(nombre=form.cleaned_data['texto'],
                                                                dedicacion=form.cleaned_data['dedicacion'],
                                                                tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                pregrado=True,
                                                                procesotutoriaacademica=form.cleaned_data['procesotutoriaacademica'],
                                                                procesoimparticionclase=form.cleaned_data['procesoimparticionclase']
                                                                )
                            criteriodocencia.save(request)
                            log(u'Adiciono criterio docencia: %s' % criteriodocencia, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                    elif periodo.clasificacion == 2:
                        if CriterioDocencia.objects.filter(nombre=form.cleaned_data['texto'],dedicacion=form.cleaned_data['dedicacion']).exists():
                            criterio = CriterioDocencia.objects.get(nombre=form.cleaned_data['texto'], dedicacion=form.cleaned_data['dedicacion'])
                            criterio.posgrado = True
                            criterio.procesotutoriaacademica = form.cleaned_data['procesotutoriaacademica']
                            criterio.procesoimparticionclase = form.cleaned_data['procesoimparticionclase']
                            criterio.save(request)
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            criteriodocencia = CriterioDocencia(nombre=form.cleaned_data['texto'],
                                                                dedicacion=form.cleaned_data['dedicacion'],
                                                                tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                posgrado=True,
                                                                procesotutoriaacademica=form.cleaned_data['procesotutoriaacademica'],
                                                                procesoimparticionclase=form.cleaned_data['procesoimparticionclase']
                                                                )
                            criteriodocencia.save(request)
                            log(u'Adiciono criterio docencia: %s' % criteriodocencia, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                    elif periodo.clasificacion == 3:
                        if CriterioDocencia.objects.filter(nombre=form.cleaned_data['texto'], dedicacion=form.cleaned_data['dedicacion']).exists():
                            criterio = CriterioDocencia.objects.get(nombre=form.cleaned_data['texto'], dedicacion=form.cleaned_data['dedicacion'])
                            criterio.admision = True
                            criterio.procesotutoriaacademica = form.cleaned_data['procesotutoriaacademica']
                            criterio.procesoimparticionclase = form.cleaned_data['procesoimparticionclase']
                            criterio.save(request)
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            criteriodocencia = CriterioDocencia(nombre=form.cleaned_data['texto'],
                                                                dedicacion=form.cleaned_data['dedicacion'],
                                                                tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                admision=True,
                                                                procesotutoriaacademica = form.cleaned_data['procesotutoriaacademica'],
                                                                procesoimparticionclase = form.cleaned_data['procesoimparticionclase']
                                                                )

                            criteriodocencia.save(request)
                            log(u'Adiciono criterio docencia: %s' % criteriodocencia, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Periodo no tiene clasificación."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. {}".format(str(ex))})

        if action == 'editcriteriodocenciapadre':
            try:
                form = CriterioDocenciaForm(request.POST)
                criteriodocencia = CriterioDocencia.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    if CriterioDocencia.objects.filter(nombre=form.cleaned_data['texto'], dedicacion=form.cleaned_data['dedicacion'], tipocriterioactividad= form.cleaned_data['tipocriterioactividad']).exclude(id=criteriodocencia.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un criterio con esa dedicacion y tipo."})
                    criteriodocencia.nombre = form.cleaned_data['texto']
                    criteriodocencia.dedicacion = form.cleaned_data['dedicacion']
                    criteriodocencia.tipocriterioactividad = form.cleaned_data['tipocriterioactividad']
                    criteriodocencia.procesotutoriaacademica = form.cleaned_data['procesotutoriaacademica']
                    criteriodocencia.procesoimparticionclase = form.cleaned_data['procesoimparticionclase']
                    criteriodocencia.nombrehtml = form.cleaned_data['nombrehtml']
                    criteriodocencia.save(request)
                    log(u'Modifico criterio docencia: %s' % criteriodocencia, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delcriteriodocenciapadre':
            try:
                criteriodocencia = CriterioDocencia.objects.get(pk=int(encrypt(request.POST['id'])))
                if criteriodocencia.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el criterio tiene elementos asociados."})
                log(u'Elimino criterio docencia: %s' % criteriodocencia, request, "del")
                criteriodocencia.delete()
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addcriteriodocenciaperiodo':
            try:
                if periodo.cerradodistributivo:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede hacer cambios en este periodo."})
                for criterio in CriterioDocencia.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio=criterio).exists():
                        criteriodocenciaperiodo = CriterioDocenciaPeriodo(periodo=periodo,
                                                                          criterio=criterio)
                        criteriodocenciaperiodo.save(request)
                        # if criteriodocenciaperiodo.nombrehtml == '':
                        if criteriodocenciaperiodo.criterio.nombrehtml:
                            criteriodocenciaperiodo.nombrehtml = criteriodocenciaperiodo.criterio.nombrehtml
                            criteriodocenciaperiodo.save(request)
                        log(u'Adiciono criterio docencia periodo: %s' % criteriodocenciaperiodo, request, "add")
                    else:
                        if CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio=criterio, status=False).exists():
                            criterio = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio=criterio, status=False).first()
                            criterio.status=True
                            criterio.save()

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.{}".format(str(ex))})

        if action == 'addcriterioinvestigacionpadre':
            try:
                form = CriterioInvestigacionForm(request.POST)
                if form.is_valid():
                    if periodo.clasificacion == 1:
                        if CriterioInvestigacion.objects.filter(nombre=form.cleaned_data['texto']).exists():
                            criterio = CriterioInvestigacion.objects.get(nombre=form.cleaned_data['texto'])
                            criterio.pregrado = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criterioinvestigacion = CriterioInvestigacion(nombre=form.cleaned_data['texto'],
                                                                          tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                          pregrado=True
                                                                          )
                            criterioinvestigacion.save(request)
                            log(u'Adiciono criterio investigacion: %s' % criterioinvestigacion, request, "add")
                            return JsonResponse({"result": "ok"})

                    if periodo.clasificacion == 2:
                        if CriterioInvestigacion.objects.filter(nombre=form.cleaned_data['texto']).exists():
                            criterio = CriterioInvestigacion.objects.get(nombre=form.cleaned_data['texto'])
                            criterio.posgrado = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criterioinvestigacion = CriterioInvestigacion(nombre=form.cleaned_data['texto'],
                                                                          tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                          posgrado=True
                                                                          )
                            criterioinvestigacion.save(request)
                            log(u'Adiciono criterio investigacion: %s' % criterioinvestigacion, request, "add")
                            return JsonResponse({"result": "ok"})

                    if periodo.clasificacion == 3:
                        if CriterioInvestigacion.objects.filter(nombre=form.cleaned_data['texto']).exists():
                            criterio = CriterioInvestigacion.objects.get(nombre=form.cleaned_data['texto'])
                            criterio.admision = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criterioinvestigacion = CriterioInvestigacion(nombre=form.cleaned_data['texto'],
                                                                          tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                          admision=True
                                                                          )
                            criterioinvestigacion.save(request)
                            log(u'Adiciono criterio investigacion: %s' % criterioinvestigacion, request, "add")
                            return JsonResponse({"result": "ok"})

                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.{}".format(str(ex))})

        if action == 'editcriterioinvestigacionpadre':
            try:
                form = CriterioInvestigacionForm(request.POST)
                criterioinvestigacion = CriterioInvestigacion.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if CriterioInvestigacion.objects.filter(nombre=form.cleaned_data['texto'], tipocriterioactividad= form.cleaned_data['tipocriterioactividad']).exclude(pk=criterioinvestigacion.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un criterio con ese nombre."})
                    criterioinvestigacion.nombre = form.cleaned_data['texto']
                    criterioinvestigacion.tipocriterioactividad = form.cleaned_data['tipocriterioactividad']
                    criterioinvestigacion.nombrehtml = form.cleaned_data['nombrehtml']
                    criterioinvestigacion.save(request)
                    log(u'Modifico criterio investigacion: %s' % criterioinvestigacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delcriterioinvestigacionpadre':
            try:
                criterioinvestigacion = CriterioInvestigacion.objects.get(pk=request.POST['id'])
                if criterioinvestigacion.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el criterio tiene elementos asociados."})
                log(u'Elimino criterio investigacion: %s' % criterioinvestigacion, request, "del")
                criterioinvestigacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addcriterioinvestigacionperiodo':
            try:
                for criterio in CriterioInvestigacion.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not CriterioInvestigacionPeriodo.objects.filter(periodo=periodo, criterio=criterio).exists():
                        criterioinvestigacionperiodo = CriterioInvestigacionPeriodo(periodo=periodo,
                                                                                    criterio=criterio)
                        criterioinvestigacionperiodo.save(request)
                        # if criterioinvestigacionperiodo.nombrehtml == '':
                        if criterioinvestigacionperiodo.criterio.nombrehtml:
                            criterioinvestigacionperiodo.nombrehtml = criterioinvestigacionperiodo.criterio.nombrehtml
                            criterioinvestigacionperiodo.save(request)
                        log(u'Adiciono criterio investigacion periodo: %s' % criterioinvestigacionperiodo, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcriteriogestionpadre':
            try:
                form = CriterioGestionForm(request.POST)
                if form.is_valid():
                    if periodo.clasificacion == 1:
                        if CriterioGestion.objects.filter(nombre=form.cleaned_data['texto']).exists():
                            criterio = CriterioGestion.objects.get(nombre=form.cleaned_data['texto'])
                            criterio.pregrado = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criteriogestion = CriterioGestion(nombre=form.cleaned_data['texto'],
                                                              tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                              pregrado=True
                                                              )
                            criteriogestion.save(request)
                            log(u'Adiciono criterio investigacion: %s' % criteriogestion, request, "add")
                            return JsonResponse({"result": "ok"})
                    if periodo.clasificacion == 2:
                        if CriterioGestion.objects.filter(nombre=form.cleaned_data['texto']).exists():
                            criterio = CriterioGestion.objects.get(nombre=form.cleaned_data['texto'])
                            criterio.posgrado = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criteriogestion = CriterioGestion(nombre=form.cleaned_data['texto'],
                                                              tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                              posgrado=True
                                                              )
                            criteriogestion.save(request)
                            log(u'Adiciono criterio investigacion: %s' % criteriogestion, request, "add")
                            return JsonResponse({"result": "ok"})
                    if periodo.clasificacion == 3:
                        if CriterioGestion.objects.filter(nombre=form.cleaned_data['texto']).exists():
                            criterio = CriterioGestion.objects.get(nombre=form.cleaned_data['texto'])
                            criterio.admision = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criteriogestion = CriterioGestion(nombre=form.cleaned_data['texto'],
                                                              tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                              admision=True
                                                              )
                            criteriogestion.save(request)
                            log(u'Adiciono criterio investigacion: %s' % criteriogestion, request, "add")
                            return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.{}".format(str(ex))})

        if action == 'addcriteriovinculacionpadre':
            try:
                form = CriterioVinculacionForm(request.POST)
                if form.is_valid():
                    if periodo.clasificacion == 1:
                        if CriterioDocencia.objects.filter(nombre=form.cleaned_data['texto'], tipo=2).exists():
                            criterio = CriterioDocencia.objects.get(nombre=form.cleaned_data['texto'], tipo=2)
                            criterio.pregrado = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criteriovinculacion = CriterioDocencia(nombre=form.cleaned_data['texto'],
                                                                   tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                   pregrado=True,
                                                                   vicevinculacion=form.cleaned_data['vicevinculacion'],
                                                                   tipo=2
                                                                   )
                            criteriovinculacion.save(request)
                            log(u'Adiciono criterio vinculacion: %s' % criteriovinculacion, request, "add")
                            return JsonResponse({"result": "ok"})
                    if periodo.clasificacion == 2:
                        if CriterioDocencia.objects.filter(nombre=form.cleaned_data['texto'], tipo=2).exists():
                            criterio = CriterioDocencia.objects.get(nombre=form.cleaned_data['texto'], tipo=2)
                            criterio.posgrado = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criteriovinculacion = CriterioDocencia(nombre=form.cleaned_data['texto'],
                                                                   tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                   posgrado=True,
                                                                   vicevinculacion=form.cleaned_data['vicevinculacion'],
                                                                   tipo=2
                                                                   )
                            criteriovinculacion.save(request)
                            log(u'Adiciono criterio vinculacion: %s' % criteriovinculacion, request, "add")
                            return JsonResponse({"result": "ok"})
                    if periodo.clasificacion == 3:
                        if CriterioDocencia.objects.filter(nombre=form.cleaned_data['texto'], tipo=2).exists():
                            criterio = CriterioDocencia.objects.get(nombre=form.cleaned_data['texto'], tipo=2)
                            criterio.admision = True
                            criterio.save(request)
                            return JsonResponse({"result": "ok"})
                        else:
                            criteriovinculacion = CriterioDocencia(nombre=form.cleaned_data['texto'],
                                                                   tipocriterioactividad=form.cleaned_data['tipocriterioactividad'],
                                                                   admision=True,
                                                                   vicevinculacion=form.cleaned_data['vicevinculacion'],
                                                                   tipo=2
                                                                   )
                            criteriovinculacion.save(request)
                            log(u'Adiciono criterio vinculacion: %s' % criteriovinculacion, request, "add")
                            return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.{}".format(str(ex))})

        if action == 'addrango':
            try:
                form = RecursoAprendizajeRangoForm(request.POST)
                if form.is_valid():
                    recursoaprendizaje = RecursoAprendizajeTipoProfesor.objects.get(pk=int(request.POST['id']))
                    # if CriterioGestion.objects.filter(nombre=form.cleaned_data['texto']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya existe un criterio con ese nombre."})
                    r = RecursoAprendizajeTipoProfesorRango(recursoaprendizajetipoprofesor=recursoaprendizaje,
                                                            rangodesde=form.cleaned_data['rangodesde'],
                                                            rangohasta=form.cleaned_data['rangohasta'],
                                                            valor=form.cleaned_data['valor'])
                    r.save(request)
                    log(u'Adiciono rango recurso aprendizaje: %s' % r, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addactividadrecurso':
            try:
                form = ActividadRecursoAprendizajeForm(request.POST)
                bandera = 0
                if form.is_valid():
                    for recurso in form.cleaned_data['recurso']:
                        if request.POST['tipo'] == '1':
                            if not ActividadDocenciaRecursoAprendizaje.objects.filter(recurso=recurso, criterio_id=request.POST['id']).exists():
                                bandera = 1
                                r = ActividadDocenciaRecursoAprendizaje(recurso=recurso,
                                                                        criterio_id=request.POST['id'],
                                                                        valor=form.cleaned_data['valor'],
                                                                        distributivo=form.cleaned_data['distributivo'])
                                r.save(request)
                                log(u'Adiciono actividad recurso aprendizaje: %s' % r, request, "add")
                        if request.POST['tipo'] == '2':
                            if not ActividadInvestigacionRecursoAprendizaje.objects.filter(recurso=recurso, criterio_id=request.POST['id']).exists():
                                bandera = 1
                                r = ActividadInvestigacionRecursoAprendizaje(recurso=recurso,
                                                                             criterio_id=request.POST['id'],
                                                                             valor=form.cleaned_data['valor'],
                                                                             distributivo=form.cleaned_data['distributivo'])
                                r.save(request)
                                log(u'Adiciono actividad recurso aprendizaje: %s' % r, request, "add")
                        if request.POST['tipo'] == '3':
                            if not ActividadGestionRecursoAprendizaje.objects.filter(recurso=recurso, criterio_id=request.POST['id']).exists():
                                bandera = 1
                                r = ActividadGestionRecursoAprendizaje(recurso=recurso,
                                                                       criterio_id=request.POST['id'],
                                                                       valor=form.cleaned_data['valor'],
                                                                       distributivo=form.cleaned_data['distributivo'])
                                r.save(request)
                                log(u'Adiciono actividad recurso aprendizaje: %s' % r, request, "add")
                    if bandera == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe."})
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addrecursoaprendizaje':
            try:
                form = RecursoAprendizajeForm(request.POST)
                if form.is_valid():
                    bandera = 0
                    if form.cleaned_data['tipoprofesor']:
                        for tipo in form.cleaned_data['tipoprofesor']:
                            if not RecursoAprendizajeTipoProfesor.objects.filter(status=True,periodoacademico=periodo,recursoaprendizaje=form.cleaned_data['recurso'],tipoprofesor=tipo).exists():
                                bandera = 1
                                recursoaprendizaje = RecursoAprendizajeTipoProfesor(periodoacademico = periodo,
                                                                                    recursoaprendizaje = form.cleaned_data['recurso'],
                                                                                    tipoprofesor = tipo,
                                                                                    docencia = form.cleaned_data['docencia'],
                                                                                    investigacion = form.cleaned_data['investigacion'],
                                                                                    gestion = form.cleaned_data['gestion'])
                                recursoaprendizaje.save(request)
                                log(u'Adiciono Recurso Aprendizaje: %s' % recursoaprendizaje, request, "add")
                    else:
                        bandera = 1
                        recursoaprendizaje = RecursoAprendizajeTipoProfesor(periodoacademico=periodo,
                                                                            recursoaprendizaje=form.cleaned_data['recurso'],
                                                                            docencia=form.cleaned_data['docencia'],
                                                                            investigacion=form.cleaned_data['investigacion'],
                                                                            gestion=form.cleaned_data['gestion'])
                        recursoaprendizaje.save(request)
                        log(u'Adiciono Recurso Aprendizaje: %s' % recursoaprendizaje, request, "add")

                    if bandera==0:
                        return JsonResponse({"result": "bad", "mensaje": u"Registros repetido"})

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcriteriogestionpadre':
            try:
                form = CriterioGestionForm(request.POST)
                criteriogestion = CriterioGestion.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if CriterioGestion.objects.filter(nombre=form.cleaned_data['texto'],tipocriterioactividad= form.cleaned_data['tipocriterioactividad']).exclude(pk=criteriogestion.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un criterio con ese nombre."})
                    criteriogestion.nombre = form.cleaned_data['texto']
                    criteriogestion.tipocriterioactividad = form.cleaned_data['tipocriterioactividad']
                    criteriogestion.nombrehtml = form.cleaned_data['nombrehtml']
                    criteriogestion.save(request)
                    log(u'Modifico criterio gestion: %s' % criteriogestion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcriteriovinculacionpadre':
            try:
                form = CriterioVinculacionForm(request.POST)
                criteriovinculacion = CriterioDocencia.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if CriterioDocencia.objects.filter(nombre=form.cleaned_data['texto'],tipocriterioactividad= form.cleaned_data['tipocriterioactividad']).exclude(id=criteriovinculacion.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un criterio con ese nombre."})
                    criteriovinculacion.nombre = form.cleaned_data['texto']
                    criteriovinculacion.tipocriterioactividad = form.cleaned_data['tipocriterioactividad']
                    criteriovinculacion.vicevinculacion=form.cleaned_data['vicevinculacion']
                    criteriovinculacion.nombrehtml = form.cleaned_data['nombrehtml']
                    criteriovinculacion.save(request)
                    log(u'Modifico criterio gestion: %s' % criteriovinculacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editrango':
            try:
                form = RecursoAprendizajeRangoForm(request.POST)
                rango = RecursoAprendizajeTipoProfesorRango.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    # if CriterioGestion.objects.filter(nombre=form.cleaned_data['texto'],tipocriterioactividad= form.cleaned_data['tipocriterioactividad']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya existe un criterio con ese nombre."})
                    rango.rangodesde = form.cleaned_data['rangodesde']
                    rango.rangohasta = form.cleaned_data['rangohasta']
                    rango.valor = form.cleaned_data['valor']
                    rango.save(request)
                    log(u'Modifico rango recurso academico: %s' % rango, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editactividadrecurso':
            try:
                form = ActividadRecursoAprendizajeAuxForm(request.POST)
                tipo = request.POST['tipo']
                if tipo == '1':
                    actividad = ActividadDocenciaRecursoAprendizaje.objects.get(pk=request.POST['idactividad'])
                if tipo == '2':
                    actividad = ActividadInvestigacionRecursoAprendizaje.objects.get(pk=request.POST['idactividad'])
                if tipo == '3':
                    actividad = ActividadGestionRecursoAprendizaje.objects.get(pk=request.POST['idactividad'])
                if form.is_valid():
                    # if CriterioGestion.objects.filter(nombre=form.cleaned_data['texto'],tipocriterioactividad= form.cleaned_data['tipocriterioactividad']).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya existe un criterio con ese nombre."})
                    actividad.valor = form.cleaned_data['valor']
                    actividad.distributivo = form.cleaned_data['distributivo']
                    actividad.save(request)
                    log(u'Modifico actividad recurso academico: %s' % actividad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delcriteriogestionpadre':
            try:
                criteriogestion = CriterioGestion.objects.get(pk=request.POST['id'])
                if criteriogestion.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el criterio tiene elementos asociados."})
                log(u'Elimino criterio gestion: %s' % criteriogestion, request, "del")
                criteriogestion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delcriteriovinculacionpadre':
            try:
                # criteriovinculacion = CriterioVinculacion.objects.get(pk=request.POST['id'])
                criteriovinculacion = CriterioDocencia.objects.get(pk=request.POST['id'])
                if criteriovinculacion.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el criterio tiene elementos asociados."})
                log(u'Elimino criterio gestion: %s' % criteriovinculacion, request, "del")
                criteriovinculacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delrango':
            try:
                rango = RecursoAprendizajeTipoProfesorRango.objects.get(pk=request.POST['id'])
                # if criteriogestion.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el criterio tiene elementos asociados."})
                log(u'Elimino rango recurso aprendizaje: %s' % rango, request, "del")
                rango.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delactividadrecurso':
            try:
                tipo = request.POST['tipo']
                if tipo == '1':
                    actividad = ActividadDocenciaRecursoAprendizaje.objects.get(pk=request.POST['id'])
                if tipo == '2':
                    actividad = ActividadInvestigacionRecursoAprendizaje.objects.get(pk=request.POST['id'])
                if tipo == '3':
                    actividad = ActividadGestionRecursoAprendizaje.objects.get(pk=request.POST['id'])
                # if criteriogestion.en_uso():
                #     return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el criterio tiene elementos asociados."})
                log(u'Elimino actividad recurso aprendizaje: %s' % actividad, request, "del")
                actividad.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editrecursoaprendizaje':
            try:
                form = RecursoAprendizajeForm(request.POST)
                recursoaprendizaje = RecursoAprendizajeTipoProfesor.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    recursoaprendizaje.docencia = form.cleaned_data['docencia']
                    recursoaprendizaje.investigacion = form.cleaned_data['investigacion']
                    recursoaprendizaje.gestion = form.cleaned_data['gestion']
                    recursoaprendizaje.save(request)
                    log(u'Modifico recurso aprendizaje: %s' % recursoaprendizaje, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delrecursoaprendizaje':
            try:
                recursoaprendizaje = RecursoAprendizajeTipoProfesor.objects.get(pk=request.POST['id'])
                if recursoaprendizaje.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el recurso aprendizaje esta en uso."})
                log(u'Elimino criterio gestion: %s' % recursoaprendizaje, request, "del")
                recursoaprendizaje.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addcriteriogestionperiodo':
            try:
                for criterio in CriterioGestion.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not CriterioGestionPeriodo.objects.filter(periodo=periodo, criterio=criterio).exists():
                        criteriogestionperiodo = CriterioGestionPeriodo(periodo=periodo,
                                                                        criterio=criterio)
                        criteriogestionperiodo.save(request)
                        # if criteriogestionperiodo.nombrehtml == '':
                        if criteriogestionperiodo.criterio.nombrehtml:
                            criteriogestionperiodo.nombrehtml = criteriogestionperiodo.criterio.nombrehtml
                            criteriogestionperiodo.save(request)
                        log(u'Adiciono criterio gestion periodo: %s' % criteriogestionperiodo, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.{}".format(str(ex))})

        if action == 'addcriteriovinculacionperiodo':
            try:
                # for criterio in CriterioVinculacion.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                for criterio in CriterioDocencia.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio=criterio).exists():
                        criteriovinculacionperiodo = CriterioDocenciaPeriodo(periodo=periodo, criterio=criterio)
                        criteriovinculacionperiodo.save(request)
                        log(u'Adiciono criterio vinculacion periodo: %s' % criteriovinculacionperiodo, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.{}".format(str(ex))})

        if action == 'delcriteriodocenciaperiodo':
            try:
                criteriodocenciaperiodo = CriterioDocenciaPeriodo.objects.get(pk=request.POST['id'])
                if criteriodocenciaperiodo.detalledistributivo_set.filter(status=True).exists() or criteriodocenciaperiodo.actividaddocenciarecursoaprendizaje_set.filter(status=True).exists() or criteriodocenciaperiodo.rubricacriteriodocencia_set.filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar este registro ya que tiene información que depende de este."})
                log(u'Elimino criterio docencia: %s' % criteriodocenciaperiodo, request, "del")
                criteriodocenciaperiodo.status = False
                criteriodocenciaperiodo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editcriteriodocenciaperiodo':
            try:
                criteriodocenciaperiodo = CriterioDocenciaPeriodo.objects.get(pk=request.POST['id'])
                f = CriterioDocenciaMinimoMaximoPeriodoForm(request.POST)
                total = 0
                if f.is_valid():
                    if f.cleaned_data['maximo'] < f.cleaned_data['minimo']:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor minimo es mayor que el valor maximo."})
                    # if criteriodocenciaperiodo.criterio.id == 121 or criteriodocenciaperiodo.criterio.id == 122:
                    #     if CriterioDocenciaPeriodo.objects.filter(criterio_id=121, periodo_id= periodo).exists():
                    #         criterio1= CriterioDocenciaPeriodo.objects.get(criterio_id=121, periodo_id= periodo)
                    #         if criterio1.porcentaje:
                    #             total = criterio1.porcentaje + f.cleaned_data['porcentaje']
                    #     if CriterioDocenciaPeriodo.objects.filter(criterio_id=122, periodo_id= periodo).exists():
                    #         criterio2= CriterioDocenciaPeriodo.objects.get(criterio_id=122, periodo_id= periodo)
                    #         if criterio2.porcentaje:
                    #             total = criterio2.porcentaje + f.cleaned_data['porcentaje']
                    # if total > 100 or total < 100 and total != 0 :
                    #     return JsonResponse({"result": "bad",
                    #                          "mensaje": u"La suma de los porcentajes de los criterios debe ser 100."})

                    criteriodocenciaperiodo.actividad = f.cleaned_data['actividad']
                    criteriodocenciaperiodo.minimo = f.cleaned_data['minimo']
                    criteriodocenciaperiodo.maximo = f.cleaned_data['maximo']
                    criteriodocenciaperiodo.subirevidencia = f.cleaned_data['subirevidencia']
                    criteriodocenciaperiodo.porcentaje = f.cleaned_data['porcentaje']
                    # if criteriodocenciaperiodo.nombrehtml == '':
                    if criteriodocenciaperiodo.criterio.nombrehtml:
                        criteriodocenciaperiodo.nombrehtml = criteriodocenciaperiodo.criterio.nombrehtml
                    criteriodocenciaperiodo.save(request)
                    log(u'Modifico criterio docencia periodo: %s' % criteriodocenciaperiodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje":"Error al validar los datos", "form": [{k: v[0]} for k, v in f.errors.items()]})
                    #raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos {}.".format(ex.__str__().split('\n')[0])})

        if action == 'delcriterioinvestigacionperiodo':
            try:
                criterioinvestigacionperiodo = CriterioInvestigacionPeriodo.objects.get(pk=request.POST['id'])
                log(u'Elimino criterio investigacion: %s' % criterioinvestigacionperiodo, request, "del")
                criterioinvestigacionperiodo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editcriterioinvestigacionperiodo':
            try:
                criterioinvestigacionperiodo = CriterioInvestigacionPeriodo.objects.get(pk=request.POST['id'])
                f = CriterioInvestigacionMinimoMaximoPeriodoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['maximo'] < f.cleaned_data['minimo']:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor minimo es mayor que el valor maximo."})
                    criterioinvestigacionperiodo.actividad = f.cleaned_data['actividad']
                    criterioinvestigacionperiodo.minimo = f.cleaned_data['minimo']
                    criterioinvestigacionperiodo.maximo = f.cleaned_data['maximo']
                    criterioinvestigacionperiodo.es_actividadmacro = f.cleaned_data['es_actividadmacro']
                    # if criterioinvestigacionperiodo.nombrehtml == '':
                    if criterioinvestigacionperiodo.criterio.nombrehtml:
                        criterioinvestigacionperiodo.nombrehtml = criterioinvestigacionperiodo.criterio.nombrehtml
                    criterioinvestigacionperiodo.save(request)
                    log(u'Modifico criterio investigacion periodo: %s' % criterioinvestigacionperiodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delcriteriogestionperiodo':
            try:
                criteriogestionperiodo = CriterioGestionPeriodo.objects.get(pk=request.POST['id'])
                log(u'Elimino criterio gestion: %s' % criteriogestionperiodo, request, "del")
                criteriogestionperiodo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delcriteriovinculacionperiodo':
            try:
                criteriovinculacionperiodo = CriterioDocenciaPeriodo.objects.get(pk=request.POST['id'])
                log(u'Elimino criterio vinculacion: %s' % criteriovinculacionperiodo, request, "del")
                criteriovinculacionperiodo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editcriteriogestionperiodo':
            try:
                criteriogestionperiodo = CriterioGestionPeriodo.objects.get(pk=request.POST['id'])
                f = CriterioGestionMinimoMaximoPeriodoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['maximo'] < f.cleaned_data['minimo']:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor minimo es mayor que el valor maximo."})
                    criteriogestionperiodo.actividad = f.cleaned_data['actividad']
                    criteriogestionperiodo.minimo = f.cleaned_data['minimo']
                    criteriogestionperiodo.maximo = f.cleaned_data['maximo']
                    # if criteriogestionperiodo.nombrehtml == '':
                    if criteriogestionperiodo.criterio.nombrehtml:
                        criteriogestionperiodo.nombrehtml = criteriogestionperiodo.criterio.nombrehtml
                    criteriogestionperiodo.save(request)
                    log(u'Modifico criterio gestion periodo: %s' % criteriogestionperiodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcriteriovinculacionperiodo':
            try:
                criteriovinculacionperiodo = CriterioDocenciaPeriodo.objects.get(pk=request.POST['id'])
                f = CriterioVinculacionMinimoMaximoPeriodoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['maximo'] < f.cleaned_data['minimo']:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor minimo es mayor que el valor maximo."})
                    criteriovinculacionperiodo.actividad = f.cleaned_data['actividad']
                    criteriovinculacionperiodo.minimo = f.cleaned_data['minimo']
                    criteriovinculacionperiodo.maximo = f.cleaned_data['maximo']
                    criteriovinculacionperiodo.subirevidencia = f.cleaned_data['subirevidencia']
                    criteriovinculacionperiodo.es_actividadmacro = f.cleaned_data['es_actividadmacro']
                    # if criteriovinculacionperiodo.nombrehtml == '':
                    if criteriovinculacionperiodo.criterio.nombrehtml:
                        criteriovinculacionperiodo.nombrehtml = criteriovinculacionperiodo.criterio.nombrehtml
                    criteriovinculacionperiodo.save(request)
                    log(u'Modifico criterio vinculacion periodo: %s' % criteriovinculacionperiodo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #CRITERIO ARTICULO
        if action == 'addcriterioarticulo':
            try:
                form = CriterioArticuloForm(request.POST)
                if form.is_valid():
                    if CriterioArticulo.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    articulo=CriterioArticulo(nombre=form.cleaned_data['nombre'], vigente=form.cleaned_data['vigente'])
                    articulo.save(request)
                    log(u'Adiciono criterio de articulo: %s [%s]' % (articulo,articulo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addactividadprincipal':
            try:
                form = ActividadPrincipalForm(request.POST)
                if form.is_valid():
                    if ActividadPrincipal.objects.filter(nombre=form.cleaned_data['nombre'], tipocriterioactividadprincipal=form.cleaned_data['tipocriterio'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    actividad=ActividadPrincipal(nombre=form.cleaned_data['nombre'], tipocriterioactividadprincipal=form.cleaned_data['tipocriterio'] ,vigente=form.cleaned_data['vigente'])
                    actividad.save(request)
                    log(u'Adiciono actividad principal: %s [%s]' % (actividad,actividad), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action =='editcriterioarticulo':
            try:
                form = CriterioArticuloForm(request.POST)
                if form.is_valid():
                    articulo = CriterioArticulo.objects.get(pk=int(request.POST['id']))
                    if CriterioArticulo.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exclude(pk=articulo.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El articulo ya existe."})
                    articulo.nombre=form.cleaned_data['nombre']
                    articulo.vigente=form.cleaned_data['vigente']
                    articulo.save(request)
                    log(u'Edito criterio de articulo : %s [%s]' % (articulo,articulo.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action =='editactividadprincipal':
            try:
                form = ActividadPrincipalForm(request.POST)
                if form.is_valid():
                    actividad = ActividadPrincipal.objects.get(pk=int(encrypt(request.POST['id'])))
                    if ActividadPrincipal.objects.filter(nombre=form.cleaned_data['nombre'], tipocriterioactividadprincipal=form.cleaned_data['tipocriterio'], status=True).exclude(pk=actividad.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La actividad ya existe."})
                    actividad.nombre=form.cleaned_data['nombre']
                    actividad.tipocriterio=form.cleaned_data['tipocriterio']
                    actividad.vigente=form.cleaned_data['vigente']
                    actividad.save(request)
                    log(u'Edito actividad principal : %s [%s]' % (actividad,actividad.id), request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action =='delcriterioarticulo':
            try:
                articulo = CriterioArticulo.objects.get(pk=int(request.POST['id']))
                if not articulo.puede_eliminar():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminarse, se esta ocupando."})
                articulo.delete()
                log(u'Elimino criterio de articulo: %s [%s]' % (articulo,articulo.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action =='delactividadprincipal':
            try:
                actividad = ActividadPrincipal.objects.get(pk=int(encrypt(request.POST['id'])))
                if not actividad.puede_eliminar():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminarse, se esta ocupando."})
                actividad.delete()
                log(u'Elimino actividad principal: %s [%s]' % (actividad,actividad.id), request, "del")
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'addrecurso':
            try:
                form = RecursosForm(request.POST)
                if form.is_valid():
                    if RecursoAprendizaje.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    recurso=RecursoAprendizaje(nombre=form.cleaned_data['nombre'])
                    recurso.save(request)
                    log(u'Adiciono Recurso : %s' % (recurso), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action =='editrecurso':
            try:
                form = RecursosForm(request.POST)
                if form.is_valid():
                    recurso = RecursoAprendizaje.objects.get(pk=int(request.POST['id']))
                    if RecursoAprendizaje.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exclude(pk=recurso.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El recurso ya existe."})
                    recurso.nombre=form.cleaned_data['nombre']
                    recurso.save(request)
                    log(u'Edito recurso : %s' % (recurso), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action =='delrecurso':
            try:
                recurso = RecursoAprendizaje.objects.get(pk=int(request.POST['id']))
                if not recurso.puede_eliminar():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminarse, se esta ocupando."})
                recurso.delete()
                log(u'Elimino recurso: %s' % (recurso), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'criteriolink':
            try:
                data['criterio'] = criterio = CriterioDocenciaPeriodo.objects.get(pk=request.POST['id'])
                if criterio.criteriolink:
                    data['criteriolinks'] = CriterioLink.objects.filter(status=True).exclude(pk=criterio.criteriolink_id)
                else:
                    data['criteriolinks'] = CriterioLink.objects.filter(status=True)
                data['cid'] = request.POST['id']
                template = get_template("adm_criteriosactividades/criteriolink.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'addcriteriolink':
            try:
                aid = int(request.POST['aid'])
                cid = int(request.POST['cid'])
                aproeli = request.POST['aproeli']
                criterio = CriterioDocenciaPeriodo.objects.get(pk=cid)
                if aproeli=='a':
                    criterio.criteriolink_id = aid
                    log(u'Asigno criterio link a criterio docencia periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.criteriolink), request, "add")
                else:
                    log(u'Designo criterio link en criterio docencia periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.criteriolink), request, "del")
                    criterio.criteriolink = None
                criterio.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'articulosdocencia':
            try:
                data['criterio'] = criterio = CriterioDocenciaPeriodo.objects.get(pk=request.POST['id'])
                if criterio.articulo:
                    data['articulos'] = CriterioArticulo.objects.filter(vigente=True).exclude(pk=criterio.articulo.id)
                else:
                    data['articulos'] = CriterioArticulo.objects.filter(vigente=True)
                data['cid'] = request.POST['id']
                template = get_template("adm_criteriosactividades/articulos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'addarticulodocencia':
            try:
                aid = int(request.POST['aid'])
                cid = int(request.POST['cid'])
                aproeli = request.POST['aproeli']
                criterio = CriterioDocenciaPeriodo.objects.get(pk=cid)
                if aproeli=='a':
                    criterio.articulo_id = aid
                    log(u'Asigno criterio articulo a criterio docencia periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.articulo), request, "add")
                else:
                    log(u'Designo criterio articulo en criterio docencia periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.articulo), request, "del")
                    criterio.articulo = None
                criterio.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'articulosgestion':
            try:
                data['criterio'] = criterio = CriterioGestionPeriodo.objects.get(pk=request.POST['id'])
                if criterio.articulo:
                    data['articulos'] = CriterioArticulo.objects.filter(vigente=True).exclude(pk=criterio.articulo.id)
                else:
                    data['articulos'] = CriterioArticulo.objects.filter(vigente=True)
                data['cid'] = request.POST['id']
                template = get_template("adm_criteriosactividades/articulos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'articulosvinculacion':
            try:
                data['criterio'] = criterio = CriterioDocenciaPeriodo.objects.get(pk=request.POST['id'])
                if criterio.articulo:
                    data['articulos'] = CriterioArticulo.objects.filter(vigente=True).exclude(pk=criterio.articulo.id)
                else:
                    data['articulos'] = CriterioArticulo.objects.filter(vigente=True)
                data['cid'] = request.POST['id']
                template = get_template("adm_criteriosactividades/articulos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'addarticulogestion':
            try:
                aid = int(request.POST['aid'])
                cid = int(request.POST['cid'])
                aproeli = request.POST['aproeli']
                criterio = CriterioGestionPeriodo.objects.get(pk=cid)
                if aproeli=='a':
                    criterio.articulo_id = aid
                    log(u'Asigno criterio articulo a criterio gestion periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.articulo), request, "add")
                else:
                    log(u'Designo criterio articulo en criterio gestion periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.articulo), request, "del")
                    criterio.articulo = None
                criterio.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'addarticulovinculacion':
            try:
                aid = int(request.POST['aid'])
                cid = int(request.POST['cid'])
                aproeli = request.POST['aproeli']
                criterio = CriterioDocenciaPeriodo.objects.get(pk=cid)
                if aproeli=='a':
                    criterio.articulo_id = aid
                    log(u'Asigno criterio articulo a criterio vinculacion periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.articulo), request, "add")
                else:
                    log(u'Designo criterio articulo en criterio vinculacion periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.articulo), request, "del")
                    criterio.articulo = None
                criterio.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'articulosinvestigacion':
            try:
                data['criterio'] = criterio = CriterioInvestigacionPeriodo.objects.get(pk=request.POST['id'])
                if criterio.articulo:
                    data['articulos'] = CriterioArticulo.objects.filter(vigente=True).exclude(pk=criterio.articulo.id)
                else:
                    data['articulos'] = CriterioArticulo.objects.filter(vigente=True)
                data['cid'] = request.POST['id']
                template = get_template("adm_criteriosactividades/articulos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'addarticuloinvestigacion':
            try:
                aid = int(request.POST['aid'])
                cid = int(request.POST['cid'])
                aproeli = request.POST['aproeli']
                criterio = CriterioInvestigacionPeriodo.objects.get(pk=cid)
                if aproeli=='a':
                    criterio.articulo_id = aid
                    log(u'Asigno criterio articulo a criterio investigacion periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.articulo), request, "add")
                else:
                    log(u'Designo criterio articulo en criterio investigacion periodo: %s [%s] - %s' % (criterio, criterio.id, criterio.articulo), request, "del")
                    criterio.articulo = None
                criterio.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        elif action == 'activarproducto':
            try:
                valor = 0
                if CriterioInvestigacionPeriodo.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio=CriterioInvestigacionPeriodo.objects.get(id=request.POST['id'], status=True)
                    if not criterio.productoinvestigacion:
                        criterio.productoinvestigacion = True
                        valor = 1
                    elif criterio.productoinvestigacion==False:
                        criterio.productoinvestigacion=True
                        valor = 1
                    else:
                        criterio.productoinvestigacion=False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'activarsubirevidenciadoc':
            try:
                valor = 0
                if CriterioDocenciaPeriodo.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio=CriterioDocenciaPeriodo.objects.get(id=request.POST['id'], status=True)
                    if not criterio.subirevidencia:
                        criterio.subirevidencia = True
                        valor = 1
                    elif criterio.subirevidencia==False:
                        criterio.subirevidencia=True
                        valor = 1
                    else:
                        criterio.subirevidencia=False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'activarllenarbitacoradoc':
            try:
                valor = 0
                if CriterioDocenciaPeriodo.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio=CriterioDocenciaPeriodo.objects.get(id=request.POST['id'], status=True)
                    if not criterio.llenarbitacora:
                        criterio.llenarbitacora = True
                        valor = 1
                    elif criterio.llenarbitacora==False:
                        criterio.llenarbitacora=True
                        valor = 1
                    else:
                        criterio.llenarbitacora=False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'activarsubirevidencia':
            try:
                valor = 0
                if CriterioInvestigacionPeriodo.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio=CriterioInvestigacionPeriodo.objects.get(id=request.POST['id'], status=True)
                    if not criterio.subirevidencia:
                        criterio.subirevidencia = True
                        valor = 1
                    elif criterio.subirevidencia==False:
                        criterio.subirevidencia=True
                        valor = 1
                    else:
                        criterio.subirevidencia=False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'activarllenarbitacora':
            try:
                valor = 0
                if CriterioInvestigacionPeriodo.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio=CriterioInvestigacionPeriodo.objects.get(id=request.POST['id'], status=True)
                    if not criterio.llenarbitacora:
                        criterio.llenarbitacora = True
                        valor = 1
                    elif criterio.llenarbitacora==False:
                        criterio.llenarbitacora=True
                        valor = 1
                    else:
                        criterio.llenarbitacora=False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'activarsubirevidenciages':
            try:
                valor = 0
                if CriterioGestionPeriodo.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio=CriterioGestionPeriodo.objects.get(id=request.POST['id'], status=True)
                    if not criterio.subirevidencia:
                        criterio.subirevidencia = True
                        valor = 1
                    elif criterio.subirevidencia==False:
                        criterio.subirevidencia=True
                        valor = 1
                    else:
                        criterio.subirevidencia=False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'activarllenarbitacorages':
            try:
                valor = 0
                if CriterioGestionPeriodo.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio=CriterioGestionPeriodo.objects.get(id=request.POST['id'], status=True)
                    if not criterio.llenarbitacora:
                        criterio.llenarbitacora = True
                        valor = 1
                    elif criterio.llenarbitacora==False:
                        criterio.llenarbitacora=True
                        valor = 1
                    else:
                        criterio.llenarbitacora=False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'addactividad':
            try:
                tipo = request.POST['id']
                tipos = tipo.split('_')
                idcriterio = tipos[0]
                tip = tipos[1]
                criteriodocencia = None
                criterioinvestigacion = None
                criteriogestion = None
                if tip == '1':
                    criteriodocencia = idcriterio
                if tip == '2':
                    criterioinvestigacion = idcriterio
                if tip == '3':
                    criteriogestion = idcriterio
                f = DetalleActividadCriterioForm(request.POST)
                if f.is_valid():
                    actividad = DetalleActividadesCriterio(nombre=f.cleaned_data['nombre'],
                                                           criteriodocenciaperiodo_id=criteriodocencia,
                                                           criterioinvestigacionperiodo_id=criterioinvestigacion,
                                                           criteriogestionperiodo_id=criteriogestion,
                                                           minimo=f.cleaned_data['minimo'],
                                                           maximo=f.cleaned_data['maximo'])
                    actividad.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delactividad':
            try:
                actividad = DetalleActividadesCriterio.objects.get(pk=request.POST['id'])
                actividad.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'editactividad':
            try:
                actividad = DetalleActividadesCriterio.objects.get(pk=request.POST['id'])
                f = DetalleActividadCriterioForm(request.POST)
                if f.is_valid():
                    actividad.nombre = f.cleaned_data['nombre']
                    actividad.minimo = f.cleaned_data['minimo']
                    actividad.maximo = f.cleaned_data['maximo']
                    actividad.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'guardarperiodotitulacion':
            try:
                codigocriterio = request.POST['codigocriterio']
                lista = request.POST['lista'].split(',')
                listadocriteriotitulacion =  CriterioDocenciaPeriodoTitulacion.objects.filter(criterio_id=codigocriterio, status=True)
                listadocriteriotitulacion.delete()
                for elemento in lista:
                    if not CriterioDocenciaPeriodoTitulacion.objects.filter(titulacion_id=elemento, criterio_id=codigocriterio, status=True):
                        criteriotitulacion = CriterioDocenciaPeriodoTitulacion(titulacion_id=elemento,
                                                                               criterio_id=codigocriterio)
                        criteriotitulacion.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'buscaperiodos':
            try:
                term = request.POST['term']
                exlc = json.loads(request.POST['excl'])
                periodos = Periodo.objects.filter(status=True, nombre__icontains=term).exclude(id__in=exlc).order_by('-inicio')
                data = []
                for periodo in periodos:
                    data.append({'id': periodo.id, 'text': periodo.__str__()})
                return JsonResponse(data, safe=False)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addperiodosrelaciondos':
            try:
                criterio = CriterioDocenciaPeriodo.objects.get(pk=request.POST['criterio'])
                criterio.periodosrelacionados.add(int(request.POST['id']))
                log(u'Adiciono periodo relacionado: %s' % criterio, request, "add")
                per = criterio.periodosrelacionados.get(id=int(request.POST['id']))
                if criterio.criterio.admision and not CriterioDocenciaPeriodo.objects.filter(status=True, periodo=per, criterio=criterio.criterio).exists():
                    critadm = CriterioDocenciaPeriodo(periodo=per, criterio=criterio.criterio)
                    critadm.save(request)
                    log(u'Se adiciono criterio docencia periodo de admision de forma automatica: %s' % critadm, request, "add")
                return JsonResponse({"result": "ok", 'criterio': criterio.id, 'id': per.id, 'criterionombre': per.nombre, 'count': criterio.periodosrelacionados.count() -1 })
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})
        elif action == 'quitarperiodo':
            try:
                criterio = CriterioDocenciaPeriodo.objects.get(pk=request.POST['criterio'])
                id = criterio.periodosrelacionados.get(id=int(request.POST['id']))
                criterio.periodosrelacionados.remove(id)
                log(u'Elimino periodo relacionado: %s' % criterio, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'verdetalledocentescriterios':
            try:
                htmlrequisitos = listadodocentescriterios(request.POST['idcriterio'], request.POST['opc'])
                return htmlrequisitos
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'del-actividad':
            try:
                a = ActividadDocentePeriodo.objects.get(pk=request.POST['id'])
                a.status = False
                a.save(request)
                return JsonResponse({'result': 'ok', 'error':False})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'add-actividad':
            try:
                data2 = {}
                pk = request.POST['id']
                data2['criterio_id'] = request.POST['actividad']
                if t := int(request.POST.get('t', '0')):
                    if t == 1 or t == 4:
                        data2['criteriodocenciaperiodo_id'] = pk
                    elif t == 2:
                        data2['criterioinvestigacionperiodo_id'] = pk
                    elif t == 3:
                        data2['criteriogestionperiodo_id'] = pk

                    obj = ActividadDocentePeriodo(**data2)
                    obj.save(request)
                    return JsonResponse({'result': 'ok'})
                return JsonResponse({'result': 'bad', 'mensaje': u"No se encontró el criterio"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'add-subactividad':
            try:
                f = SubactividadDocentePeriodoForm(request.POST)
                if f.is_valid():
                    if SubactividadDocentePeriodo.objects.values('id').filter(criterio=f.cleaned_data['criterio'], actividad_id=request.POST['id'], status=True).exists():
                        raise NameError(f"La subactividad <b>{f.cleaned_data['criterio']}</b> ya se encuentra asociada a una actividad principal")

                    s = SubactividadDocentePeriodo(criterio=f.cleaned_data['criterio'],
                                                   actividad_id=request.POST['id'],
                                                   fechainicio=f.cleaned_data['fechainicio'],
                                                   fechafin=f.cleaned_data['fechafin'],
                                                   tipoevidencia=f.cleaned_data['tipoevidencia'],
                                                   cargaevidencia=f.cleaned_data['cargaevidencia'],
                                                   validacion=f.cleaned_data['validacion'],
                                                   nombrehtml=f.cleaned_data.get('nombrehtml'))
                    s.save(request)
                else:
                    for k, v in f.errors.items():
                        raise NameError(k + ', ' + v[0])
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'edit-subactividad':
            try:
                f = SubactividadDocentePeriodoForm(request.POST)
                s = SubactividadDocentePeriodo.objects.get(id=request.POST['id'])
                if f.is_valid():
                    s.criterio = f.cleaned_data['criterio']
                    s.fechainicio = f.cleaned_data['fechainicio']
                    s.fechafin = f.cleaned_data['fechafin']
                    s.tipoevidencia = f.cleaned_data['tipoevidencia']
                    s.cargaevidencia = f.cleaned_data['cargaevidencia']
                    s.validacion = f.cleaned_data['validacion']
                    s.nombrehtml = f.cleaned_data.get('nombrehtml')
                    s.save(request)
                else:
                    for k, v in f.errors.items():
                        raise NameError(k + ', ' + v[0])
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'del-subactividad':
            try:
                a = SubactividadDocentePeriodo.objects.get(pk=request.POST['id'])
                a.status = False
                a.save(request)
                return JsonResponse({'result': 'ok', 'error':False})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'del-criterio':
            try:
                a = Criterio.objects.get(pk=request.POST['id'])
                a.status = False
                if persona.usuario.is_superuser:
                    if a.tipo == 1:
                        a.actividaddocenteperiodo_set.filter(status=True).update(status=False)
                    if a.tipo == 2:
                        a.subactividaddocenteperiodo_set.filter(status=True).update(status=False)
                a.save(request)
                return JsonResponse({'result': 'ok', 'error':False})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'add-criterio':
            try:
                f = CriterioForm(request.POST)
                if f.is_valid():
                    nombre = f.cleaned_data["nombre"].strip()
                    if Criterio.objects.values('id').filter(nombre=nombre, tipo=request.POST['rt'], tipocriterio=request.POST['ids'], status=True).exists():
                        raise NameError(f'El criterio {nombre} ya existe')

                    a = Criterio(nombre=nombre, tipo=request.POST['rt'], tipocriterio=request.POST['ids'])
                    a.save(request)
                    return JsonResponse({'result': 'ok', 'error':False})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'edit-criterio':
            try:
                f = CriterioForm(request.POST)
                a = Criterio.objects.get(id=request.POST['id'])
                if f.is_valid():
                    nombre = f.cleaned_data['nombre'].strip()
                    if Criterio.objects.values('id').filter(nombre=nombre, status=True).exists():
                        raise NameError(f'El criterio {f.cleaned_data["nombre"].strip()} ya existe')

                    a.nombre = nombre
                    a.save(request)
                    return JsonResponse({'result': 'ok', 'error':False})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Criterios de actividades academicas'
        data['puede_agregar_criterio'] = puede_agregar_criterio = puede_realizar_accion2(request, 'sga.puede_agregar_criterio_periodo')
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'verdetalledocentessubactividad':
                try:
                    data2 = {}
                    subactividad = SubactividadDocentePeriodo.objects.get(id=request.GET['id'])
                    detalledistributivo = subactividad.subactividaddetalledistributivo_set.filter(status=True).values_list('actividaddetalledistributivo__criterio', flat=True)
                    listadodocentes = DetalleDistributivo.objects.filter(id__in=detalledistributivo).order_by('distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2', 'distributivo__profesor__persona__nombres')
                    data2['criterio'] = subactividad
                    data2['listadodocentes'] = listadodocentes
                    template = get_template("adm_evaluaciondocentesacreditacion/viewdocentescriterios.html")
                    json_content = template.render(data2)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'subactividades':
                try:
                    data['title'] = 'Gestión de subactividades'
                    tipocriterio = request.GET['tipo']
                    data['actividad'] = actividad = ActividadDocentePeriodo.objects.get(id=request.GET['id'])
                    data['dataset'] = SubactividadDocentePeriodo.objects.filter(actividad=actividad, criterio__status=True, status=True)
                    data['tipo'] = tipocriterio
                    return render(request, "adm_criteriosactividades/subactividades.html", data)
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

            if action == 'criterios':
                try:
                    data['title'] = f'Gestión de actividades y subactividades'
                    data['t'] = tipo = int(request.GET.get('t', 1))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['tipocriterio'] = tipocriterio = int(encrypt(request.GET.get('tipocriterio')))
                    data[f'criterio{tipo}'] = Criterio.objects.filter(status=True, tipo=tipo, tipocriterio=tipocriterio).order_by('-fecha_creacion')
                    return render(request, "adm_criteriosactividades/criterios.html", data)
                except Exception as ex:
                    pass

            if action == 'add-criterio':
                try:
                    data['form2'] = CriterioForm()
                    data['rt'] = request.GET['t']
                    data['ids'] = request.GET['tc']
                    template = get_template("proyectovinculaciondocente/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'html': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'add-subactividad':
                try:
                    f = SubactividadDocentePeriodoForm()
                    actividad = ActividadDocentePeriodo.objects.get(id=request.GET['id'])
                    criterioselected = actividad.subactividaddocenteperiodo_set.filter(actividad__status=True, criterio__status=True, status=True).values_list('criterio', flat=True)
                    f.fields['fechafin'].initial = periodo.fin
                    f.fields['fechainicio'].initial = periodo.inicio
                    f.fields['criterio'].queryset = Criterio.objects.filter(tipo=2, tipocriterio=actividad.criterio.tipocriterio, status=True).exclude(id__in=criterioselected)
                    data['id'] = actividad.pk
                    data['form2'] = f
                    template = get_template("proyectovinculaciondocente/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'html': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edit-subactividad':
                try:
                    model = SubactividadDocentePeriodo.objects.get(pk=request.GET['id'])
                    a_criterio = SubactividadDocentePeriodo.objects.filter(criterio__status=True, status=True).values_list('criterio', flat=True).exclude(criterio__id=model.criterio.pk).distinct()
                    f = SubactividadDocentePeriodoForm(initial=model_to_dict(model))
                    f.fields['criterio'].queryset = Criterio.objects.filter(tipo=2, tipocriterio=model.actividad.criterio.tipocriterio, status=True).exclude(id__in=a_criterio)
                    # if not request.user.is_superuser:
                    #     f.ocultar_plantilla()
                    data['form2'] = f
                    data['id'] = model.pk
                    template = get_template("proyectovinculaciondocente/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'html': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edit-criterio':
                try:
                    c = Criterio.objects.get(id=request.GET['id'])
                    data['form2'] = CriterioForm(initial={'nombre': c.nombre})
                    data['id'] = c.pk
                    template = get_template("proyectovinculaciondocente/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'html': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'actividades':
                tab = 0
                try:
                    data['title'] = 'Gestión de actividades'
                    id, criterio = request.GET.get('id'), None
                    filtro = Q(criterio__status=True, status=True)
                    tab = int(request.GET['t'])
                    if tab == 1 or tab == 4:
                        criterio = CriterioDocenciaPeriodo.objects.get(id=id)
                        filtro &= Q(criteriodocenciaperiodo=criterio.pk)
                    elif tab == 2:
                        criterio = CriterioInvestigacionPeriodo.objects.get(id=id)
                        filtro &= Q(criterioinvestigacionperiodo=criterio.pk)
                    elif tab == 3:
                        criterio = CriterioGestionPeriodo.objects.get(id=id)
                        filtro &= Q(criteriogestionperiodo=criterio.pk)

                    data['tab'] = tab
                    data['criterio'] = criterio
                    data['actividades'] = ActividadDocentePeriodo.objects.filter(filtro)
                    exclude = ActividadDocentePeriodo.objects.values_list('criterio_id', flat=True).filter(criterioinvestigacionperiodo__periodo=periodo, status=True)
                    data['nuevasactividades'] = Criterio.objects.filter(tipo=1, tipocriterio=tab, status=True).exclude(id__in=exclude)
                    periodosactividad = list(ActividadDocentePeriodo.objects.values_list('criterioinvestigacionperiodo__periodo', flat=True).filter(criterioinvestigacionperiodo__isnull=False, status=True))
                    periodosactividad += list(ActividadDocentePeriodo.objects.values_list('criteriodocenciaperiodo__periodo', flat=True).filter(criteriodocenciaperiodo__isnull=False, status=True))
                    data['listaperiodos'] = Periodo.objects.filter(id__in=set(periodosactividad)).exclude(id=periodo.pk).order_by('inicio')
                    return render(request, 'adm_criteriosactividades/actividades.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(f'/adm_criteriosactividades?t={tab}')

            if action == 'listadoperiodoseval':
                try:
                    lista = []
                    idcriterio=request.GET['idcriterio']
                    listadoperiodoseval = PeriodoGrupoTitulacion.objects.filter(pk__gte=17,status=True).order_by('fechainicio')
                    for lis in listadoperiodoseval:
                        visto = ''
                        if lis.criteriodocenciaperiodotitulacion_set.filter(criterio_id=idcriterio,status=True):
                            visto = 'checked'
                        lista.append([lis.id,  lis.nombre, visto])
                    data = {"results": "ok", 'listadoperiodoseval': lista}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'criteriosdocencia':
                try:
                    if not puede_agregar_criterio:
                        return HttpResponseRedirect('/adm_criteriosactividades?info=Lo sentimos usted no tiene acceso a esta sección')
                    data['title'] = u'Criterios de actividades de docencia'
                    if periodo.clasificacion == 1:
                        # data['criterios'] = CriterioDocencia.objects.filter(pregrado=True, status=True)
                        data['criterios'] = CriterioDocencia.objects.filter(pregrado=True, tipo=1, status=True)
                    elif periodo.clasificacion == 2:
                        data['criterios'] = CriterioDocencia.objects.filter(posgrado=True, tipo=1, status=True)
                    elif periodo.clasificacion == 3:
                        data['criterios'] = CriterioDocencia.objects.filter(admision=True, tipo=1, status=True)
                    # data['criteriospregrado'] = CriterioDocencia.objects.filter(pregrado=True)
                    return render(request, "adm_criteriosactividades/criteriosdocencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addcriteriodocenciapadre':
                try:
                    data['title'] = u'Adicionar criterio de actividad de docencia'
                    data['form'] = form = CriterioDocenciaForm()
                    form.add()
                    template = get_template("adm_criteriosactividades/addcriteriodocenciapadre.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editcriteriodocenciapadre':
                try:
                    data['title'] = u'Editar criterio de actividad de docencia'
                    data['criterio'] = criterio = CriterioDocencia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = CriterioDocenciaForm(initial={'dedicacion': criterio.dedicacion,
                                                                 'texto': criterio.nombre,
                                                                 'tipocriterioactividad': criterio.tipocriterioactividad,
                                                                 'procesotutoriaacademica': criterio.procesotutoriaacademica,
                                                                 'procesoimparticionclase': criterio.procesoimparticionclase,
                                                                 'nombrehtml': criterio.nombrehtml
                                                                 })
                    template = get_template("adm_criteriosactividades/editcriteriodocenciapadre.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'criteriosinvestigacion':
                try:
                    if not puede_agregar_criterio:
                        return HttpResponseRedirect('/adm_criteriosactividades?info=Lo sentimos usted no tiene acceso a esta sección')
                    data['title'] = u'Criterios de actividades de investigación'
                    if periodo.clasificacion == 1:
                        data['criterios'] = CriterioInvestigacion.objects.filter(pregrado=True, status=True)
                    if periodo.clasificacion == 2:
                        data['criterios'] = CriterioInvestigacion.objects.filter(posgrado=True, status=True)
                    if periodo.clasificacion == 3:
                        data['criterios'] = CriterioInvestigacion.objects.filter(admision=True, status=True)
                    return render(request, "adm_criteriosactividades/criteriosinvestigacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addcriterioinvestigacionpadre':
                try:
                    data['title'] = u'Adicionar criterio de actividad de investigación'
                    data['form'] = form = CriterioInvestigacionForm()
                    form.add()
                    return render(request, "adm_criteriosactividades/addcriterioinvestigacionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriterioinvestigacionpadre':
                try:
                    data['title'] = u'Editar criterio de actividad de investigación'
                    data['criterio'] = criterio = CriterioInvestigacion.objects.get(pk=request.GET['id'])
                    data['form'] = CriterioInvestigacionForm(initial={'texto': criterio.nombre, 'tipocriterioactividad': criterio.tipocriterioactividad, 'nombrehtml': criterio.nombrehtml})
                    return render(request, "adm_criteriosactividades/editcriterioinvestigacionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriterioinvestigacionpadre':
                try:
                    data['title'] = u'Eliminar criterios de actividad investigación'
                    data['criterio'] = CriterioInvestigacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delcriterioinvestigacionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'criteriosgestion':
                try:
                    if not puede_agregar_criterio:
                        return HttpResponseRedirect('/adm_criteriosactividades?info=Lo sentimos usted no tiene acceso a esta sección')
                    data['title'] = u'Criterios de actividades de gestión'
                    if periodo.clasificacion == 1:
                        data['criterios'] = CriterioGestion.objects.filter(pregrado=True, status=True)
                    if periodo.clasificacion == 2:
                        data['criterios'] = CriterioGestion.objects.filter(posgrado=True, status=True)
                    if periodo.clasificacion == 3:
                        data['criterios'] = CriterioGestion.objects.filter(admision=True, status=True)
                    return render(request, "adm_criteriosactividades/criteriosgestion.html", data)
                except Exception as ex:
                    pass

            if action == 'rangorecursoaprendizaje':
                try:
                    data['recursoaprendizaje'] = recursoaprendizajetipoprofesor = RecursoAprendizajeTipoProfesor.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Rango recurso aprendizaje - %s' % recursoaprendizajetipoprofesor
                    data['rangos'] = RecursoAprendizajeTipoProfesorRango.objects.filter(status=True, recursoaprendizajetipoprofesor=recursoaprendizajetipoprofesor).order_by('rangodesde')
                    return render(request, "adm_criteriosactividades/rangorecursoaprendizaje.html", data)
                except Exception as ex:
                    pass

            if action == 'actividadrecurso':
                try:
                    data['tipo'] = tipo = request.GET['tipo']
                    if tipo == '1':
                        data['criterio'] = criterio = CriterioDocenciaPeriodo.objects.get(pk=int(request.GET['id']))
                        data['recursos'] = recursos = criterio.actividaddocenciarecursoaprendizaje_set.filter(status=True).order_by('recurso')
                    if tipo == '2':
                        data['criterio'] = criterio = CriterioInvestigacionPeriodo.objects.get(pk=int(request.GET['id']))
                        data['recursos'] = recursos = criterio.actividadinvestigacionrecursoaprendizaje_set.filter(status=True).order_by('recurso')
                    if tipo == '3':
                        data['criterio'] = criterio = CriterioGestionPeriodo.objects.get(pk=int(request.GET['id']))
                        data['recursos'] = recursos = criterio.actividadgestionrecursoaprendizaje_set.filter(status=True).order_by('recurso')
                    data['title'] = u'Actividad - recurso aprendizaje - %s' % criterio.criterio
                    data['id'] = request.GET['id']
                    return render(request, "adm_criteriosactividades/actividadrecurso.html", data)
                except Exception as ex:
                    pass

            if action == 'addcriteriogestionpadre':
                try:
                    data['title'] = u'Adicionar criterio de actividad de investigación'
                    data['form'] = form = CriterioGestionForm()
                    form.add()
                    return render(request, "adm_criteriosactividades/addcriteriogestionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'addcriteriovinculacionpadre':
                try:
                    data['title'] = u'Adicionar criterio de actividad de vinculación'
                    data['form'] = form = CriterioVinculacionForm()
                    form.add()
                    return render(request, "adm_criteriosactividades/addcriteriovinculacionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'addrango':
                try:
                    data['title'] = u'Adicionar rango recurso academico'
                    data['form'] = RecursoAprendizajeRangoForm()
                    data['idrecurso'] = request.GET['id']
                    return render(request, "adm_criteriosactividades/addrango.html", data)
                except Exception as ex:
                    pass

            if action == 'addactividadrecurso':
                try:
                    data['title'] = u'Adicionar actividad recurso academico'
                    data['tipo'] = tipo = request.GET['tipo']
                    data['id'] = request.GET['id']
                    form = ActividadRecursoAprendizajeForm()
                    form.tipo(tipo)
                    data['form'] = form
                    return render(request, "adm_criteriosactividades/addactividadrecurso.html", data)
                except Exception as ex:
                    pass

            if action == 'addrecursoaprendizaje':
                try:
                    data['title'] = u'Adicionar Recurso Aprendizaje'
                    data['form'] = RecursoAprendizajeForm()
                    return render(request, "adm_criteriosactividades/addrecursoaprendizaje.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriteriogestionpadre':
                try:
                    data['title'] = u'Editar criterio de actividad de investigación'
                    data['criterio'] = criterio = CriterioGestion.objects.get(pk=request.GET['id'])
                    data['form'] = CriterioGestionForm(initial={'texto': criterio.nombre, 'tipocriterioactividad': criterio.tipocriterioactividad, 'nombrehtml': criterio.nombrehtml})
                    return render(request, "adm_criteriosactividades/editcriteriogestionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriteriovinculacionpadre':
                try:
                    data['title'] = u'Editar criterio de actividad de vinculación'
                    # data['criterio'] = criterio = CriterioVinculacion.objects.get(pk=request.GET['id'])
                    data['criterio'] = criterio = CriterioDocencia.objects.get(pk=request.GET['id'])
                    data['form'] = CriterioVinculacionForm(initial={'texto': criterio.nombre, 'tipocriterioactividad': criterio.tipocriterioactividad, 'nombrehtml': criterio.nombrehtml})
                    return render(request, "adm_criteriosactividades/editcriteriovinculacionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'editrango':
                try:
                    data['title'] = u'Editar rango recurso academico'
                    data['rango'] = rango = RecursoAprendizajeTipoProfesorRango.objects.get(pk=request.GET['id'])
                    data['form'] = RecursoAprendizajeRangoForm(initial={'rangodesde': rango.rangodesde,
                                                                        'rangohasta': rango.rangohasta,
                                                                        'valor': rango.valor})
                    return render(request, "adm_criteriosactividades/editrango.html", data)
                except Exception as ex:
                    pass

            if action == 'editactividadrecurso':
                try:
                    data['title'] = u'Editar actividad recurso academico'
                    data['tipo'] = tipo = request.GET['tipo']
                    data['id'] = request.GET['id']
                    if tipo == '1':
                        data['actividad'] = actividad = ActividadDocenciaRecursoAprendizaje.objects.get(pk=request.GET['idrecurso'])
                    if tipo == '2':
                        data['actividad'] = actividad = ActividadInvestigacionRecursoAprendizaje.objects.get(pk=request.GET['idrecurso'])
                    if tipo == '3':
                        data['actividad'] = actividad = ActividadGestionRecursoAprendizaje.objects.get(pk=request.GET['idrecurso'])

                    form = ActividadRecursoAprendizajeAuxForm(initial={'recurso': actividad.recurso,
                                                                       'valor': actividad.valor,
                                                                       'distributivo': actividad.distributivo})
                    form.editar(tipo)
                    data['form'] = form
                    return render(request, "adm_criteriosactividades/editactividadrecurso.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriogestionpadre':
                try:
                    data['title'] = u'Eliminar criterios de actividad investigación'
                    data['criterio'] = CriterioGestion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delcriteriogestionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriovinculacionpadre':
                try:
                    data['title'] = u'Eliminar criterios de actividad vinculación'
                    # data['criterio'] = CriterioVinculacion.objects.get(pk=request.GET['id'])
                    data['criterio'] = CriterioDocencia.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delcriteriovinculacionpadre.html", data)
                except Exception as ex:
                    pass

            if action == 'delrango':
                try:
                    data['title'] = u'Eliminar rango recurso academico'
                    data['rango'] = RecursoAprendizajeTipoProfesorRango.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delrango.html", data)
                except Exception as ex:
                    pass

            if action == 'delactividadrecurso':
                try:
                    data['title'] = u'Eliminar actividad recurso academico'
                    data['tipo'] = tipo = request.GET['tipo']
                    data['id'] = request.GET['id']
                    if tipo == '1':
                        data['actividad'] = actividad = ActividadDocenciaRecursoAprendizaje.objects.get(pk=request.GET['idrecurso'])
                    if tipo == '2':
                        data['actividad'] = actividad = ActividadInvestigacionRecursoAprendizaje.objects.get(pk=request.GET['idrecurso'])
                    if tipo == '3':
                        data['actividad'] = actividad = ActividadGestionRecursoAprendizaje.objects.get(pk=request.GET['idrecurso'])
                    return render(request, "adm_criteriosactividades/delactividadrecurso.html", data)
                except Exception as ex:
                    pass

            if action == 'editrecursoaprendizaje':
                try:
                    data['title'] = u'Editar Recurso Aprendizaje'
                    data['recursoaprendizaje'] = recursoaprendizaje = RecursoAprendizajeTipoProfesor.objects.get(pk=request.GET['id'])
                    form = RecursoAprendizajeauxForm(initial={'recurso': recursoaprendizaje.recursoaprendizaje,
                                                              'tipoprofesor': recursoaprendizaje.tipoprofesor,
                                                              'docencia': recursoaprendizaje.docencia,
                                                              'investigacion': recursoaprendizaje.investigacion,
                                                              'gestion': recursoaprendizaje.gestion})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_criteriosactividades/editrecursoaprendizaje.html", data)
                except Exception as ex:
                    pass

            if action == 'delrecursoaprendizaje':
                try:
                    data['title'] = u'Eliminar recurso aprendizaje'
                    data['recursoaprendizaje'] = RecursoAprendizajeTipoProfesor.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delrecursoaprendizaje.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriodocenciaperiodo':
                try:
                    data['title'] = u'Eiminar criterios de docencia periodo'
                    data['criterio'] = CriterioDocenciaPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delcriteriodocenciaperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriteriodocenciaperiodo':
                try:
                    data['title'] = u'Editar criterio de docencia periodo'
                    data['criterio'] = criterio = CriterioDocenciaPeriodo.objects.get(pk=request.GET['id'])
                    data['form'] = CriterioDocenciaMinimoMaximoPeriodoForm(initial={'minimo': criterio.minimo,
                                                                                    'actividad': criterio.actividad,
                                                                                    'subirevidencia': criterio.subirevidencia,
                                                                                    'maximo': criterio.maximo,
                                                                                    'porcentaje': criterio.porcentaje})
                    return render(request, "adm_criteriosactividades/editcriteriodocenciaperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriterioinvestigacionperiodo':
                try:
                    data['title'] = u'Eliminar criterios de investigación periodo'
                    data['criterio'] = CriterioInvestigacionPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delcriterioinvestigacionperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriterioinvestigacionperiodo':
                try:
                    data['title'] = u'Editar criterio de investigación periodo'
                    data['criterio'] = criterio = CriterioInvestigacionPeriodo.objects.get(pk=request.GET['id'])
                    data['form'] = CriterioInvestigacionMinimoMaximoPeriodoForm(initial={'minimo': criterio.minimo,
                                                                                         'actividad': criterio.actividad,
                                                                                         'maximo': criterio.maximo,
                                                                                         'es_actividadmacro': criterio.es_actividadmacro})
                    return render(request, "adm_criteriosactividades/editcriterioinvestigacionperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriogestionperiodo':
                try:
                    data['title'] = u'Eliminar criterios de gestion periodo'
                    data['criterio'] = CriterioGestionPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delcriteriogestionperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriovinculacionperiodo':
                try:
                    data['title'] = u'Eliminar criterios de vinculacion periodo'
                    data['criterio'] = CriterioDocenciaPeriodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delcriteriovinculacionperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriteriogestionperiodo':
                try:
                    data['title'] = u'Editar criterio de investigación periodo'
                    data['criterio'] = criterio = CriterioGestionPeriodo.objects.get(pk=request.GET['id'])
                    data['form'] = CriterioGestionMinimoMaximoPeriodoForm(initial={'minimo': criterio.minimo,
                                                                                   'actividad': criterio.actividad,
                                                                                   'maximo': criterio.maximo})
                    return render(request, "adm_criteriosactividades/editcriteriogestionperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriteriovinculacionperiodo':
                try:
                    data['title'] = u'Editar criterio de vinculación periodo'
                    data['criterio'] = criterio = CriterioDocenciaPeriodo.objects.get(pk=request.GET['id'])
                    data['form'] = CriterioVinculacionMinimoMaximoPeriodoForm(initial={'minimo': criterio.minimo,
                                                                                       'actividad': criterio.actividad,
                                                                                       'maximo': criterio.maximo,
                                                                                       'subirevidencia': criterio.subirevidencia,
                                                                                       'es_actividadmacro': criterio.es_actividadmacro,
                                                                                       })
                    return render(request, "adm_criteriosactividades/editcriteriovinculacionperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'addcriterioarticulo':
                try:
                    data['title'] = u'Adicionar criterio de artículo'
                    data['form'] = CriterioArticuloForm()
                    return render(request, "adm_criteriosactividades/addcriterioarticulo.html", data)
                except Exception as ex:
                    pass

            if action == 'addactividadprincipal':
                try:
                    data['title'] = u'Adicionar actividad principal'
                    data['form'] = ActividadPrincipalForm()
                    template = get_template("adm_criteriosactividades/addactividadprincipal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editactividadprincipal':
                try:
                    data['title'] = u'Editar actividad principal'
                    data['actividad'] = actividad = ActividadPrincipal.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = ActividadPrincipalForm(initial={'nombre': actividad.nombre,
                                                                   'tipocriterio': actividad.tipocriterioactividadprincipal,
                                                                   'vigente': actividad.vigente})
                    template = get_template("adm_criteriosactividades/editactividadprincipal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editcriterioarticulo':
                try:
                    data['title'] = u'Editar criterio de artículo'
                    data['criterio'] = criterio = CriterioArticulo.objects.get(pk=request.GET['id'])
                    data['form'] = CriterioArticuloForm(initial={'nombre': criterio.nombre,
                                                                 'vigente': criterio.vigente})
                    return render(request, "adm_criteriosactividades/editcriterioarticulo.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriterioarticulo':
                try:
                    data['title'] = u'Eliminar criterios de artículo'
                    data['criterio'] = CriterioArticulo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delcriterioarticulo.html", data)
                except Exception as ex:
                    pass

            if action == 'addrecurso':
                try:
                    data['title'] = u'Adicionar recurso'
                    data['form'] = RecursosForm()
                    return render(request, "adm_criteriosactividades/addrecurso.html", data)
                except Exception as ex:
                    pass

            if action == 'editrecurso':
                try:
                    data['title'] = u'Editar recurso'
                    data['recurso'] = recurso = RecursoAprendizaje.objects.get(pk=request.GET['id'])
                    data['form'] = RecursosForm(initial={'nombre': recurso.nombre})
                    return render(request, "adm_criteriosactividades/editrecurso.html", data)
                except Exception as ex:
                    pass

            if action == 'delrecurso':
                try:
                    data['title'] = u'Eliminar recurso'
                    data['recurso'] = RecursoAprendizaje.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delrecurso.html", data)
                except Exception as ex:
                    pass

            if action == 'criteriosarticulo':
                try:
                    data['title'] = u'Criterios de artículos'
                    data['criterios'] = CriterioArticulo.objects.all().order_by('-fecha_creacion')
                    return render(request, "adm_criteriosactividades/criteriosarticulo.html", data)
                except Exception as ex:
                    pass

            if action == 'actividadprincipal':
                try:
                    data['title'] = u'Actividades Principales'
                    search, url_vars = request.GET.get('s', ''), ''
                    actividades = ActividadPrincipal.objects.filter(status=True).order_by('tipocriterioactividadprincipal')
                    numerofilas = 25
                    paging = MiPaginador(actividades, numerofilas)
                    p = 1
                    url_vars += "&action=actividadprincipal"
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        else:
                            p = paginasesion
                            if p == 1:
                                numerofilasguiente = numerofilas
                            else:
                                numerofilasguiente = numerofilas * (p - 1)
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['actividades'] = page.object_list
                    return render(request, "adm_criteriosactividades/actividadprincipal.html", data)
                except Exception as ex:
                    pass

            if action == 'criteriosvinculacion':
                try:
                    data['title'] = u'Criterios de actividades de vinculación'
                    if periodo.clasificacion == 1:
                        # data['criterios'] = CriterioVinculacion.objects.filter(pregrado=True, status=True)
                        data['criterios'] = CriterioDocencia.objects.filter(pregrado=True, tipo=2, status=True)
                    if periodo.clasificacion == 2:
                        # data['criterios'] = CriterioVinculacion.objects.filter(posgrado=True, status=True)
                        data['criterios'] = CriterioDocencia.objects.filter(posgrado=True, tipo=2, status=True)
                    if periodo.clasificacion == 3:
                        # data['criterios'] = CriterioVinculacion.objects.filter(admision=True, status=True)
                        data['criterios'] = CriterioDocencia.objects.filter(admision=True, tipo=2, status=True)
                    return render(request, "adm_criteriosactividades/criteriosvinculacion.html", data)
                except Exception as ex:
                    pass

            if action == 'recurso':
                try:
                    data['title'] = u'Recurso'
                    data['recursos'] = RecursoAprendizaje.objects.filter(status=True).order_by('-fecha_creacion')
                    return render(request, "adm_criteriosactividades/recurso.html", data)
                except Exception as ex:
                    pass

            if action == 'actividadescriterio':
                try:
                    data['tip'] = tip = request.GET['tip']
                    if tip == '1':
                        data['title'] = u'Actividades de criterios - Docencia'
                        data['criterio'] = criteriodocencia = CriterioDocenciaPeriodo.objects.get(pk=request.GET['id'])
                        data['detalle'] = criteriodocencia.detalleactividadescriterio_set.filter(status=True)
                    if tip == '2':
                        data['title'] = u'Actividades de criterios - Investigación'
                        data['criterio'] = criterioinvestigacion = CriterioInvestigacionPeriodo.objects.get(pk=request.GET['id'])
                        data['detalle'] = criterioinvestigacion.detalleactividadescriterio_set.filter(status=True)
                    if tip == '3':
                        data['title'] = u'Actividades de criterios - Gestión'
                        data['criterio'] = criteriogestion = CriterioGestionPeriodo.objects.get(pk=request.GET['id'])
                        data['detalle'] = criteriogestion.detalleactividadescriterio_set.filter(status=True)
                    return render(request, "adm_criteriosactividades/actividadescriterio.html", data)
                except Exception as ex:
                    pass

            if action == 'addactividad':
                try:
                    data['tip'] = tip = request.GET['idtipo']
                    if tip == '1':
                        data['title'] = u'Adicionar actividad de criterios - Docencia'
                        data['criterio'] = CriterioDocenciaPeriodo.objects.get(pk=request.GET['idcriterio'])
                    if tip == '2':
                        data['title'] = u'Adicionar actividad de criterios - Investigación'
                        data['criterio'] = CriterioInvestigacionPeriodo.objects.get(pk=request.GET['idcriterio'])
                    if tip == '3':
                        data['title'] = u'Adicionar actividad de criterios - Gestión'
                        data['criterio'] = CriterioGestionPeriodo.objects.get(pk=request.GET['idcriterio'])
                    data['form'] = DetalleActividadCriterioForm(initial={})
                    return render(request, "adm_criteriosactividades/addactividad.html", data)
                except Exception as ex:
                    pass

            if action == 'delactividad':
                try:
                    data['title'] = u'Eliminar actividad'
                    data['idcriterio'] = request.GET['idcriterio']
                    data['idtipo'] = request.GET['idtipo']
                    data['actividad'] = DetalleActividadesCriterio.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividades/delactividad.html", data)
                except Exception as ex:
                    pass

            if action == 'editactividad':
                try:
                    data['title'] = u'Editar actividad a criterio'
                    data['idcriterio'] = request.GET['idcriterio']
                    data['idtipo'] = request.GET['idtipo']
                    data['actividad'] = actividad = DetalleActividadesCriterio.objects.get(pk=request.GET['id'])
                    form = DetalleActividadCriterioForm(initial={'nombre': actividad.nombre,
                                                                 'minimo': actividad.minimo,
                                                                 'maximo': actividad.maximo})
                    data['form'] = form
                    return render(request, "adm_criteriosactividades/editactividad.html", data)
                except Exception as ex:
                    pass

            if action == 'addperiodosrelaciondos':
                try:
                    data['criterio'] = criterio = CriterioDocenciaPeriodo.objects.get(pk=request.GET['id'])
                    data['periodos'] = criterio.periodosrelacionados.all()
                    data['excl'] = list(criterio.periodosrelacionados.values_list('id', flat=True))
                    template = get_template("adm_criteriosactividades/periodosrelacionados.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

            elif action == 'docentescriterioexcel':
                try:
                    idcriterio = int(request.GET['idcriterio'])
                    opc = int(request.GET['opc'])
                    listadodocentes = []
                    if opc == 1:
                        criterio = CriterioDocenciaPeriodo.objects.get(pk=idcriterio, criterio__tipo=1)
                        listadodocentes = DetalleDistributivo.objects.filter(criteriodocenciaperiodo=criterio).order_by('distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2', 'distributivo__profesor__persona__nombres')
                    elif opc == 2:
                        criterio = CriterioInvestigacionPeriodo.objects.get(pk=idcriterio)
                        listadodocentes = DetalleDistributivo.objects.filter(criterioinvestigacionperiodo=criterio).order_by('distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2', 'distributivo__profesor__persona__nombres')
                    elif opc == 3:
                        criterio = CriterioGestionPeriodo.objects.get(pk=idcriterio)
                        listadodocentes = DetalleDistributivo.objects.filter(criteriogestionperiodo=criterio).order_by('distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2', 'distributivo__profesor__persona__nombres')
                    elif opc == 4:
                        criterio = CriterioDocenciaPeriodo.objects.get(pk=idcriterio, criterio__tipo=2)
                        listadodocentes = DetalleDistributivo.objects.filter(criteriodocenciaperiodo=criterio).order_by('distributivo__profesor__persona__apellido1', 'distributivo__profesor__persona__apellido2', 'distributivo__profesor__persona__nombres')

                    if listadodocentes:
                        __author__ = 'Unemi'
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('Docentes')
                        ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write(1, 0, f'{str(criterio.criterio)}', font_style)
                        response = HttpResponse(content_type="application/ms-excel")
                        nombre = 'criterio_docentes_'
                        response['Content-Disposition'] = 'attachment; filename=Listado_' + nombre + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"DOCUMENTO", 3500),
                            (u"DOCENTE", 10000),
                            (u"CORREO", 10000),
                            (u"COORDINACIÓN", 12000),
                            (u"CARRERA", 12000),
                            (u"HORAS", 2000),
                            (u"ADMISIÓN", 2500),
                        ]
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        row_num = 4
                        for d in listadodocentes:
                            p = d.distributivo.profesor.persona
                            coordinacion = d.distributivo.coordinacion
                            carrera = d.distributivo.carrera
                            ws.write(row_num, 0, '%s' % p.identificacion(), font_style2)
                            ws.write(row_num, 1, '%s' % p, font_style2)
                            ws.write(row_num, 2, '%s' % p.emailinst, font_style2)
                            ws.write(row_num, 3, '%s' % coordinacion, font_style2)
                            ws.write(row_num, 4, '%s' % carrera, font_style2)
                            ws.write(row_num, 5, '%s' % d.horas, font_style2)
                            ws.write(row_num, 6, '%s' % 'SI' if d.es_admision else 'NO', font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                    else:
                        pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['reporte_0'] = obtener_reporte('actividades_distributivo_periodo')
                data['t'] = int(request.GET['t']) if 't' in request.GET else None
                data['recurso_aprendizajes'] = RecursoAprendizajeTipoProfesor.objects.filter(periodoacademico=periodo, status=True).order_by('recursoaprendizaje', 'tipoprofesor')
                if periodo.clasificacion == 1:
                    data['criterios_docencia'] = listadodocencia = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__tipo=1, status=True).order_by('actividad_id')
                    data['cadenadoc'] = DetalleDistributivo.objects.values_list('criteriodocenciaperiodo_id', flat=True).filter(criteriodocenciaperiodo_id__in=listadodocencia.values_list('id')).order_by('criteriodocenciaperiodo_id').distinct()
                    data['criterios_investigacion'] = listadoinvestigacion = CriterioInvestigacionPeriodo.objects.filter(periodo=periodo, status=True).order_by('actividad_id')
                    data['cadenainv'] = DetalleDistributivo.objects.values_list('criterioinvestigacionperiodo_id', flat=True).filter(criterioinvestigacionperiodo_id__in=listadoinvestigacion.values_list('id')).order_by('criterioinvestigacionperiodo_id').distinct()
                    data['criterios_gestion'] = listadogestion = CriterioGestionPeriodo.objects.filter(periodo=periodo, status=True).order_by('actividad_id')
                    data['cadenagest'] = DetalleDistributivo.objects.values_list('criteriogestionperiodo_id', flat=True).filter(criteriogestionperiodo_id__in=listadogestion.values_list('id')).order_by('criteriogestionperiodo_id').distinct()
                    # data['criterios_vinculacion'] = CriterioVinculacionPeriodo.objects.filter(periodo=periodo, criterio__pregrado=True).order_by('actividad_id')
                    data['criterios_vinculacion'] = listadovinculacion = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__tipo=2, status=True).order_by('actividad_id')
                    data['cadenavin'] = DetalleDistributivo.objects.values_list('criteriodocenciaperiodo_id', flat=True).filter(criteriodocenciaperiodo_id__in=listadovinculacion.values_list('id')).order_by('criteriodocenciaperiodo_id').distinct()
                if periodo.clasificacion == 2:
                    data['criterios_docencia'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__tipo=1, criterio__posgrado=True, status=True).order_by('actividad_id')
                    data['criterios_investigacion'] = CriterioInvestigacionPeriodo.objects.filter(periodo=periodo, criterio__posgrado=True, status=True).order_by('actividad_id')
                    data['criterios_gestion'] = CriterioGestionPeriodo.objects.filter(periodo=periodo, criterio__posgrado=True, status=True).order_by('actividad_id')
                    # data['criterios_vinculacion'] = CriterioVinculacionPeriodo.objects.filter(periodo=periodo,criterio__posgrado=True).order_by('actividad_id')
                    data['criterios_vinculacion'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__tipo=2, criterio__posgrado=True, status=True).order_by('actividad_id')
                if periodo.clasificacion == 3:
                    data['criterios_docencia'] = listadodocencia =  CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__tipo=1, criterio__admision=True, status=True).order_by('actividad_id')
                    data['cadenadoc'] = DetalleDistributivo.objects.values_list('criteriodocenciaperiodo_id', flat=True).filter(criteriodocenciaperiodo_id__in=listadodocencia.values_list('id'))
                    data['criterios_investigacion'] = CriterioInvestigacionPeriodo.objects.filter(periodo=periodo, criterio__admision=True, status=True).order_by('actividad_id')
                    data['criterios_gestion'] = CriterioGestionPeriodo.objects.filter(periodo=periodo, criterio__admision=True, status=True).order_by('actividad_id')
                    # data['criterios_vinculacion'] = CriterioVinculacionPeriodo.objects.filter(periodo=periodo,criterio__admision=True).order_by('actividad_id')
                    data['criterios_vinculacion'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, criterio__tipo=2, criterio__admision=True, status=True).order_by('actividad_id')
                # data['criterios_docencia'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo).order_by(
                #     'actividad_id')
                # data['criterios_investigacion'] = CriterioInvestigacionPeriodo.objects.filter(periodo=periodo).order_by(
                #     'actividad_id')
                # data['criterios_gestion'] = CriterioGestionPeriodo.objects.filter(periodo=periodo).order_by('actividad_id')
                # data['recurso_aprendizajes'] = RecursoAprendizajeTipoProfesor.objects.filter(periodoacademico=periodo,
                #                                                                              status=True).order_by(
                #     'recursoaprendizaje', 'tipoprofesor')
                # data['reporte_0'] = obtener_reporte('actividades_distributivo_periodo')
                # data['t'] = None
                # if 't' in request.GET:
                #     data['t'] = int(request.GET['t'])
                return render(request, "adm_criteriosactividades/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/?info=' + ex.__str__())
