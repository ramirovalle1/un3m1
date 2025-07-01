# -*- coding: UTF-8 -*-
import json
import random
from _decimal import Context
from datetime import datetime, timedelta
import sys
from builtins import float
import io
import xlsxwriter
from itertools import chain
import xlwt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Sum
from django.forms import model_to_dict
from django.template.context import Context
from django.template.loader import get_template

from balcon.forms import CategoriaBalconForm
from inno.funciones import tiene_certificacion_segunda_lengua_aprobado_director_carrera
from sagest.models import DistributivoPersona, RubroNotaDebito
from sga.excelbackground import reporte_matriculados_background
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from decorators import secure_module, last_access
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from xlwt import *
from settings import  MODULO_INGLES_ID, POSGRADO_EDUCACION_ID, \
    MODULOS_COMPUTACION_ID, ADMISION_ID, PROYECTOS_TITULACION_ID, CUPO_POR_ALTERNATIVATITULACION, NOTA_ESTADO_APROBADO, \
    ESTADO_GESTACION
from sga.commonviews import adduserdata, traerNotificaciones
from sga.forms import GrupoTitulacionForm, AlternativaTitulacionForm, EliminarMatriculatitulacionForm, \
    ComplexivoMateriaForm, ComplexivoClaseForm, ComplexivoExamenForm, ComplexivoCalificacionDiaForm, \
    CronogramaAprobacionExamenComplexivoForm, CronogramaPropuestaPracticaComplexivoForm, \
    CronogramaRevisionEstudianteComplexivoForm, CronogramaNucleoConocimientoComplexivoForm, PeriodoGrupoTitulacionForm, \
    ArchivosTitulacionForm, ModeloTitulacionForm, CombinarTipoTitulacionForm, TipoTitulacionForm, \
    CronogramaAdicionalExamenComplexivoForm, AlternativaTitulacionMatriForm, RubricaTitulacionForm, RubricaTitulacionCabForm, PonderacionRubricaForm
from sga.funciones import log, MiPaginador, generar_nombre, null_to_decimal, null_to_numeric, convertir_fecha
from sga.funciones_templatepdf import listadovalidarequisitos, listadofaltantefirmaracta
from sga.models import Carrera, Coordinacion, TipoTitulaciones, PeriodoGrupoTitulacion, GrupoTitulacion, \
    AlternativaTitulacion, \
    ModeloTitulacion, SesionTitulacion, Modelo_AlternativaTitulacion, Malla, CombinarTipoTitulaciones, Profesor, \
    ProfesoresTitulacion, \
    MatriculaTitulacion, Inscripcion, ModuloMalla, \
    AsignaturaMalla, RecordAcademico, \
    ESTADOS_MATRICULA, PerfilInscripcion, Egresado, Graduado, ParticipantesMatrices, \
    PracticasPreprofesionalesInscripcion, PersonaDatosFamiliares, EstudioInscripcion, EstadoGestacion, \
    PropuestaTitulacion, PropuestaTitulacion_Matricula, TIPO_CELULAR, ComplexivoExamenDetalle, ComplexivoMateria, \
    ComplexivoClase, Turno, ComplexivoMateriaAsignada, ComplexivoExamen, CronogramaExamenComplexivo, ArchivoTitulacion, \
    ComplexivoGrupoTematica, ComplexivoDetalleGrupo, TIPO_ARCHIVO_COMPLEXIVO_PROPUESTA, ComplexivoPropuestaPractica, \
    MESES_CHOICES, ComplexivoLeccion, DetalleRevisionCronograma, GrupoInvestigacion, CargoInstitucion, InscripcionMalla, \
    ExamenComlexivoGraduados, ItemExamenComplexivo, Periodo, CronogramaAdicionalExamenComplexivo, RubricaTitulacionCab, \
    RubricaTitulacion, ModeloRubricaTitulacion, RubricaTitulacionPonderacion, PonderacionRubrica, \
    RubricaTitulacionCabPonderacion, CoordinadorCarrera, Persona, Notificacion, Materia, MateriaAsignada, Matricula, \
    MateriaTitulacion, ResponsableCoordinacion, NivelMalla, EjeFormativo, HistorialCertificacionPersona
from sga.tasks import send_html_mail
from socioecon.models import FichaSocioeconomicaINEC
from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    periodoid=0
    # bordes
    borders = Borders()
    borders.left = 1
    borders.right = 1
    borders.top = 1
    borders.bottom = 1
    # estilos para los reportes
    title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
    subtitle = easyxf('font: name Arial, bold on , height 200; alignment: horiz centre')
    peque = easyxf('font: name Arial, bold on , height 125; alignment: horiz left')
    nnormal = easyxf('font: name Arial, bold on , height 150; alignment: horiz left')
    normal = easyxf('font: name Arial , height 100; alignment: horiz left')
    normaliz = easyxf('font: name Arial , height 175; alignment: horiz right')
    stylenotas = easyxf('font: name Arial , height 100; alignment: horiz centre')
    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    stylebnombre = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
    stylevacio = easyxf('font: name Arial , height 600; alignment: horiz centre')
    normal.borders = borders
    stylebnotas.borders = borders
    stylenotas.borders = borders
    stylebnombre.borders = borders
    stylevacio.borders = borders

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addgrupotitulacion':
            try:
                form = GrupoTitulacionForm(request.POST)
                if form.is_valid():
                    periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['periodo']))
                    if (form.cleaned_data['fechainicio'] >= periodo.fechainicio and form.cleaned_data['fechainicio'] <= periodo.fechafin)and ( form.cleaned_data['fechafin']> periodo.fechainicio and form.cleaned_data['fechafin']<=  periodo.fechafin):
                        if (form.cleaned_data['fechainicio']<form.cleaned_data['fechafin']):
                            grupo= GrupoTitulacion(periodogrupo=form.cleaned_data['periodo'],
                                                   facultad_id=int(request.POST['coordinacion']),
                                                   nombre=form.cleaned_data['nombre'],
                                                   fechainicio=form.cleaned_data['fechainicio'],
                                                   fechafin=form.cleaned_data['fechafin'])
                            grupo.save(request)
                            log(u'Adicionar Grupo Titulacion: %s' % grupo, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Las fechas que ingreso no son validas."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Las fechas que ingreso no se encuentran en el periodo seleccionado."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editgrupotitulacion':
            try:
                form = GrupoTitulacionForm(request.POST)
                if form.is_valid():
                    grupo = GrupoTitulacion.objects.get(pk=int(request.POST['id']))
                    # if grupo.periodogrupo.fechafin >= datetime.now().date() and grupo.periodogrupo.abierto:
                    if grupo.periodogrupo.fechafin >= datetime.now().date():
                        # if not grupo.tiene_alternativa_activa():
                        if (form.cleaned_data['fechainicio'] >= grupo.periodogrupo.fechainicio and form.cleaned_data['fechainicio'] < grupo.periodogrupo.fechafin) and (form.cleaned_data['fechafin'] >  grupo.periodogrupo.fechainicio and form.cleaned_data['fechafin'] <= grupo.periodogrupo.fechafin):
                            if (form.cleaned_data['fechainicio'] < form.cleaned_data['fechafin']):
                                grupo.nombre=form.cleaned_data['nombre']
                                grupo.facultad=grupo.facultad
                                grupo.fechainicio=form.cleaned_data['fechainicio']
                                grupo.fechafin=form.cleaned_data['fechafin']
                                grupo.save(request)
                                log(u'Editar Grupo Titulacion: %s' % grupo, request, "add")
                                return JsonResponse({"result": "ok"})
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Las fechas que ingreso no son validas."})
                        else:
                            return JsonResponse({"result": "bad","mensaje": u"Las fechas que ingreso no se encuentran en el periodo seleccionado."})
                    else:
                        grupo.nombre = form.cleaned_data['nombre']
                        grupo.save(request)
                        log(u'Editar Grupo Titulacion: %s' % grupo, request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'eliminargrupotitulacion':
            try:
                grupo = GrupoTitulacion.objects.get(pk=int(request.POST['id']))
                if not grupo.tiene_alternativa_activa():
                    grupo.status=False
                    grupo.save(request)
                    log(u'Elimino Grupo Titulacion: %s' % grupo, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad","mensaje": u"No se puede borrar, tiene Altenativas de Titulación activas."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'copiaralternativa':
            try:
                id = int(request.POST['id'])
                copiaalternativa = AlternativaTitulacion.objects.get(pk=id)

                copiamodeloalternativa = Modelo_AlternativaTitulacion.objects.filter(alternativa = copiaalternativa, status = True)
                creditos = Malla.objects.get(pk = int(copiaalternativa.malla.id), status=True)
                grupo = GrupoTitulacion.objects.get(pk=int(copiaalternativa.grupotitulacion.id))

                alternativa = AlternativaTitulacion(grupotitulacion_id=int(copiaalternativa.grupotitulacion.id),
                                                    tipotitulacion= copiaalternativa.tipotitulacion,
                                                    alias= copiaalternativa.alias,
                                                    horastotales = creditos.horas_titulacion,
                                                    creditos = creditos.creditos_titulacion,
                                                    horassemanales=copiaalternativa.horassemanales,
                                                    cupo=copiaalternativa.cupo,
                                                    paralelo=copiaalternativa.paralelo,
                                                    fechamatriculacion=copiaalternativa.fechamatriculacion,
                                                    fechamatriculacionfin=copiaalternativa.fechamatriculacionfin,
                                                    fechaordinariainicio=copiaalternativa.fechaordinariainicio,
                                                    fechaordinariafin=copiaalternativa.fechaordinariafin,
                                                    fechaextraordinariainicio=copiaalternativa.fechaextraordinariainicio,
                                                    fechaextraordinariafin=copiaalternativa.fechaextraordinariafin,
                                                    fechaespecialinicio=copiaalternativa.fechaespecialinicio,
                                                    fechaespecialfin=copiaalternativa.fechaespecialfin,
                                                    facultad_id=grupo.facultad_id,
                                                    carrera = copiaalternativa.carrera,
                                                    estadocomputacion = copiaalternativa.estadocomputacion,
                                                    estadoingles= copiaalternativa.estadoingles,
                                                    estadovinculacion=copiaalternativa.estadovinculacion,
                                                    estadopracticaspreprofesionales = copiaalternativa.estadopracticaspreprofesionales,
                                                    estadocredito = copiaalternativa.estadocredito,
                                                    estadonivel=copiaalternativa.estadonivel,
                                                    estadoadeudar = copiaalternativa.estadoadeudar,
                                                    estadofichaestudiantil = copiaalternativa.estadofichaestudiantil,
                                                    verestudiantes = copiaalternativa.verestudiantes,
                                                    descripcion=copiaalternativa.descripcion,
                                                    aplicapropuesta=copiaalternativa.aplicapropuesta,
                                                    fechanoaplicapropuesta = copiaalternativa.fechanoaplicapropuesta,
                                                    docenteevaluador1_id = copiaalternativa.docenteevaluador1,
                                                    docenteevaluador2_id = copiaalternativa.docenteevaluador2,
                                                    actividadcomplementaria = copiaalternativa.actividadcomplementaria,
                                                    malla = copiaalternativa.malla,
                                                    acperiodo = copiaalternativa.acperiodo,
                                                    es_copia = True
                                                    )
                alternativa.save(request)
                log(u'Adicionar Aternativa: %s - [%s]' % (alternativa,alternativa.id), request, "add")
                for copmodelo in copiamodeloalternativa:
                    mod = Modelo_AlternativaTitulacion(modelo=copmodelo.modelo,alternativa=alternativa)
                    mod.save(request)
                    log(u'Adicionar Modelo de Alternativa Titulación: %s' % mod, request, "add")

                if SesionTitulacion.objects.filter(alternativa=copiaalternativa, status = True).exists():
                    ses = SesionTitulacion.objects.get(alternativa=copiaalternativa, status = True)
                    sesion=SesionTitulacion(sesion=ses.sesion,alternativa=alternativa)
                    sesion.save(request)
                    log(u'Adicionar Sesión: %s' % sesion, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addalternativa':
            try:
                form = AlternativaTitulacionForm(request.POST)
                horastotales=0
                if form.is_valid():
                    if not form.cleaned_data['tipotitulacion']:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese un Tipo de Titulación."})
                    grupo= GrupoTitulacion.objects.get(pk=int(request.POST['idg']))
                    if ((form.cleaned_data['fechainiciomatriculacion']>= grupo.fechainicio and form.cleaned_data['fechafinmatriculacion']<=grupo.fechafin) and
                            form.cleaned_data['fechainiciomatriculacion']<=form.cleaned_data['fechafinmatriculacion']):

                        # if ((form.cleaned_data['fechaordinariainicio'] >= grupo.fechainicio and form.cleaned_data['fechaordinariafin'] <= grupo.fechafin) and
                        #         form.cleaned_data['fechaordinariainicio'] <= form.cleaned_data['fechaordinariafin'] and
                        #         form.cleaned_data['fechaordinariainicio'] > form.cleaned_data['fechafinmatriculacion']):
                        #
                        #     if ((form.cleaned_data['fechaextraordinariainicio'] >= grupo.fechainicio and form.cleaned_data['fechaextraordinariafin'] <= grupo.fechafin) and
                        #             form.cleaned_data['fechaextraordinariainicio'] <= form.cleaned_data['fechaextraordinariafin'] and
                        #             form.cleaned_data['fechaextraordinariainicio'] > form.cleaned_data['fechaordinariafin']):
                        #
                        #         if ((form.cleaned_data['fechaespecialinicio'] >= grupo.fechainicio and form.cleaned_data['fechaespecialfin'] <= grupo.fechafin) and
                        #                 form.cleaned_data['fechaespecialinicio'] <= form.cleaned_data['fechaespecialfin'] and
                        #                 form.cleaned_data['fechaespecialinicio'] > form.cleaned_data['fechaextraordinariafin']):

                        creditos = Malla.objects.get(pk=int(request.POST['malla']), status=True)
                        listmodel = form.cleaned_data['modelotitulacion']
                        for mid in listmodel:
                            model = ModeloTitulacion.objects.get(pk=int(mid.id))
                            total = model.horaspresencial + model.horasvirtual + model.horasautonoma
                            horastotales += total
                            # if horastotales ==creditos.horas_titulacion:
                            alternativa = AlternativaTitulacion(grupotitulacion_id=int(request.POST['idg']),
                                                                tipotitulacion= form.cleaned_data['tipotitulacion'],
                                                                alias= form.cleaned_data['alias'],
                                                                horastotales = creditos.horas_titulacion,
                                                                creditos = creditos.creditos_titulacion,
                                                                horassemanales=form.cleaned_data['horassemanales'],
                                                                cupo=form.cleaned_data['cupo'],
                                                                paralelo=form.cleaned_data['paralelo'],
                                                                fechamatriculacion=form.cleaned_data['fechainiciomatriculacion'],
                                                                fechamatriculacionfin=form.cleaned_data['fechafinmatriculacion'],
                                                                fechaordinariainicio=form.cleaned_data['fechaordinariainicio'],
                                                                fechaordinariafin=form.cleaned_data['fechaordinariafin'],
                                                                fechaextraordinariainicio=form.cleaned_data['fechaextraordinariainicio'],
                                                                fechaextraordinariafin=form.cleaned_data['fechaextraordinariafin'],
                                                                fechaespecialinicio=form.cleaned_data['fechaespecialinicio'],
                                                                fechaespecialfin=form.cleaned_data['fechaespecialfin'],
                                                                facultad_id=grupo.facultad_id,
                                                                carrera = form.cleaned_data['carreras'],
                                                                estadocomputacion =form.cleaned_data['estadocomputacion'],
                                                                estadoingles=form.cleaned_data['estadoingles'],
                                                                estadovinculacion=form.cleaned_data['estadovinculacion'],
                                                                estadopracticaspreprofesionales = form.cleaned_data['estadopractica'],
                                                                estadocredito = form.cleaned_data['estadocredito'],
                                                                estadonivel=form.cleaned_data['estadonivel'],
                                                                estadoadeudar = form.cleaned_data['estadoadeudar'],
                                                                estadofichaestudiantil = form.cleaned_data['estadofichaestudiantil'],
                                                                verestudiantes = form.cleaned_data['verestudiantes'],
                                                                descripcion=form.cleaned_data['descripcion'],
                                                                aplicapropuesta=form.cleaned_data['aplicapropuesta'],
                                                                fechanoaplicapropuesta = form.cleaned_data['fechanoaplicapropuesta'] if form.cleaned_data['aplicapropuesta'] else None,
                                                                docenteevaluador1_id = form.cleaned_data['docenteevaluador1'] if form.cleaned_data['aplicapropuesta'] else None,
                                                                docenteevaluador2_id = form.cleaned_data['docenteevaluador2'] if form.cleaned_data['aplicapropuesta'] else None,
                                                                actividadcomplementaria = form.cleaned_data['actividadcomplementaria'],
                                                                malla = form.cleaned_data['malla'],
                                                                acperiodo = form.cleaned_data['acperiodo'] if form.cleaned_data['actividadcomplementaria'] else None
                                                                )
                            alternativa.save(request)
                            log(u'Adicionar Aternativa: %s - [%s]' % (alternativa,alternativa.id), request, "add")
                            modelotitulacion = form.cleaned_data['modelotitulacion']
                            for modelo in modelotitulacion:
                                mod = Modelo_AlternativaTitulacion(modelo=modelo,alternativa=alternativa)
                                mod.save(request)
                                log(u'Adicionar Modelo de Alternativa Titulación: %s' % mod, request, "add")
                            if form.cleaned_data['sesion']:
                                sesion=SesionTitulacion(sesion=form.cleaned_data['sesion'],alternativa=alternativa)
                                sesion.save(request)
                                log(u'Adicionar Sesión: %s' % sesion, request, "add")
                            return JsonResponse({"result": "ok"})
                        # else:
                        #     return JsonResponse({"result": "bad","mensaje": u"Las horas totales no es igual de la carrera."})
                    #         else:
                    #             return JsonResponse({"result": "bad", "mensaje": u"Las fechas especial no validas."})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": u"Las fechas extraordinarias no validas."})
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Las fechas ordinarias no validas."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Las fecha de matriculación no validas."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editalternativa':
            try:
                horastotales=0
                form = AlternativaTitulacionForm(request.POST)
                if form.is_valid():
                    alter= AlternativaTitulacion.objects.get(pk=int(request.POST['ida']))
                    # if ((form.cleaned_data['fechainiciomatriculacion'] >= alter.grupotitulacion.periodogrupo.fechainicio and form.cleaned_data['fechafinmatriculacion'] <= alter.grupotitulacion.periodogrupo.fechafin) and form.cleaned_data['fechainiciomatriculacion'] <= form.cleaned_data['fechafinmatriculacion']):
                    #     if ((form.cleaned_data['fechaordinariainicio'] >= alter.grupotitulacion.periodogrupo.fechainicio and form.cleaned_data['fechaordinariafin'] <= alter.grupotitulacion.periodogrupo.fechafin) and form.cleaned_data['fechaordinariainicio'] <= form.cleaned_data['fechaordinariafin'] and form.cleaned_data['fechaordinariainicio'] > form.cleaned_data[ 'fechafinmatriculacion']):
                    #         if ((form.cleaned_data['fechaextraordinariainicio'] >= alter.grupotitulacion.periodogrupo.fechainicio and form.cleaned_data['fechaextraordinariafin'] <= alter.grupotitulacion.periodogrupo.fechafin) and form.cleaned_data['fechaextraordinariainicio'] <= form.cleaned_data[  'fechaextraordinariafin'] and form.cleaned_data['fechaextraordinariainicio'] > form.cleaned_data['fechaordinariafin']):
                    #             if ((form.cleaned_data['fechaespecialinicio'] >= alter.grupotitulacion.periodogrupo.fechainicio and form.cleaned_data['fechaespecialfin'] <= alter.grupotitulacion.periodogrupo.fechafin) and form.cleaned_data['fechaespecialinicio'] <= form.cleaned_data['fechaespecialfin'] and form.cleaned_data['fechaespecialinicio'] > form.cleaned_data['fechaextraordinariafin']):
                    if alter.contar_matriculados() == 0:
                        listmodel = form.cleaned_data['modelotitulacion']
                        for mid in form.cleaned_data['modelotitulacion']:
                            modelito = ModeloTitulacion.objects.get(pk=int(mid.id))
                            total = mid.horaspresencial + modelito.horasvirtual + modelito.horasautonoma
                            horastotales += total
                        creditos = Malla.objects.get(id=int(request.POST['malla']))
                        if (horastotales ==creditos.horas_titulacion):
                            alter.tipotitulacion = form.cleaned_data['tipotitulacion']
                            alter.alias = form.cleaned_data['alias']
                            alter.horastotales=creditos.horas_titulacion
                            alter.creditos = creditos.creditos_titulacion
                        else:
                            return JsonResponse({"result": "bad","mensaje": u"Las Horas Totales no es igual de la Carrera."})
                    alter.horassemanales = form.cleaned_data['horassemanales']
                    alter.cupo = form.cleaned_data['cupo']
                    alter.paralelo = form.cleaned_data['paralelo']
                    alter.fechamatriculacion = form.cleaned_data['fechainiciomatriculacion']
                    alter.fechamatriculacionfin = form.cleaned_data['fechafinmatriculacion']
                    alter.fechaordinariainicio = form.cleaned_data['fechaordinariainicio']
                    alter.fechaordinariafin = form.cleaned_data['fechaordinariafin']
                    alter.fechaextraordinariainicio = form.cleaned_data['fechaextraordinariainicio']
                    alter.fechaextraordinariafin = form.cleaned_data['fechaextraordinariafin']
                    alter.fechaespecialinicio = form.cleaned_data['fechaespecialinicio']
                    alter.fechaespecialfin = form.cleaned_data['fechaespecialfin']
                    alter.estadocomputacion = form.cleaned_data['estadocomputacion']
                    alter.estadoingles = form.cleaned_data['estadoingles']
                    alter.estadovinculacion = form.cleaned_data['estadovinculacion']
                    alter.procesorezagado = form.cleaned_data['procesorezagado']
                    alter.estadopracticaspreprofesionales = form.cleaned_data['estadopractica']
                    alter.estadocredito = form.cleaned_data['estadocredito']
                    alter.estadonivel = form.cleaned_data['estadonivel']
                    alter.estadoadeudar = form.cleaned_data['estadoadeudar']
                    alter.estadofichaestudiantil = form.cleaned_data['estadofichaestudiantil']
                    alter.verestudiantes = form.cleaned_data['verestudiantes']
                    alter.descripcion = form.cleaned_data['descripcion']
                    alter.aplicapropuesta = form.cleaned_data['aplicapropuesta']
                    alter.malla = form.cleaned_data['malla']
                    alter.es_copia = False
                    if form.cleaned_data['aplicapropuesta']:
                        alter.fechanoaplicapropuesta = form.cleaned_data['fechanoaplicapropuesta']
                        alter.docenteevaluador1_id = form.cleaned_data['docenteevaluador1']
                        alter.docenteevaluador2_id = form.cleaned_data['docenteevaluador2']
                    # else:
                    #     alter.fechanoaplicapropuesta = None
                    #     alter.docenteevaluador1 = None
                    #     alter.docenteevaluador2 = None
                    alter.actividadcomplementaria = form.cleaned_data['actividadcomplementaria']
                    if form.cleaned_data['actividadcomplementaria']:
                        alter.acperiodo_id = form.cleaned_data['acperiodo']
                    else:
                        alter.acperiodo = None
                    alter.save(request)
                    if form.cleaned_data['sesion']:
                        sesion = SesionTitulacion.objects.filter(alternativa = alter)
                        if sesion.exists():
                            sesion = sesion[0]
                            sesion.sesion = form.cleaned_data['sesion']
                            log(u'Editar Sesión titulacion: %s[%s] - alternativa[%s]' % (sesion,sesion.id,alter.id), request, "edit")
                        else:
                            sesion = SesionTitulacion(alternativa=alter,sesion=form.cleaned_data['sesion'])
                            log(u'Adiciono Sesión: %s[%s] - alternativa[%s]' % (sesion,sesion.id,alter.id), request, "add")
                        sesion.save(request)
                    modeloeliminar=alter.modelo_alternativatitulacion_set.filter(status=True).exclude(modelo__in=form.cleaned_data['modelotitulacion'])
                    if modeloeliminar.exists():
                        for eliminar in modeloeliminar:
                            log(u'Eliminar Modelo de Alternativa Titulación: %s[%s] - alternativa[%s]' % (eliminar,eliminar.id,alter.id), request, "del")
                        modeloeliminar.delete()
                    for modelo in form.cleaned_data['modelotitulacion']:
                        if not alter.modelo_alternativatitulacion_set.filter(status=True, modelo=modelo).exists():
                            mode = Modelo_AlternativaTitulacion(alternativa=alter, modelo=modelo)
                            mode.save(request)
                            log(u'Adiciono Modelo en Alternativa Titulación: %s[%s] - alternativa[%s]' % (mode,mode.id,alter.id), request, "edit")
                    log(u'Editar Aternativa: %s - [%s]' % (alter,alter.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Las Fechas Especial no validas."})
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Las Fechas Extraordinarias no validas."})
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Las Fechas Ordinarias no validas."}),
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Fecha de Matriculación no validas."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Llene todos los campos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editalternativamatri':
            try:
                form = AlternativaTitulacionMatriForm(request.POST)
                if form.is_valid():
                    matri= MatriculaTitulacion.objects.get(pk=int(request.POST['idm']))
                    matri.alternativa = form.cleaned_data['tipotitulacion']
                    matri.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Llene todos los campos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'eliminaralternativa':
            try:
                alter = AlternativaTitulacion.objects.get(pk=int(request.POST['id']))
                if alter.contar_matriculados()==0:
                    alter.status=False
                    alter.save(request)
                    log(u'Elimino Alternativa Titulacion: %s' % alter, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, tiene alumnos matriculados."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."}),

        elif action == 'updatecupo':
            try:
                alternativa = AlternativaTitulacion.objects.get(pk=int(request.POST['aid']))
                valor = int(request.POST['vc'])
                if valor > CUPO_POR_ALTERNATIVATITULACION:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede establecer un cupo menor a"+ str(CUPO_POR_ALTERNATIVATITULACION +1)})
                if valor < alternativa.contar_matriculados():
                    return JsonResponse({"result": "bad","mensaje": u"El cupo no puede ser menor a la cantidad de matriculados"})
                cupoanterior = alternativa.cupo
                alternativa.cupo = valor
                alternativa.save(request)
                log(u'Actualizo cupo a materia: %s cupo anterior: %s cupo actual: %s' % (alternativa, str(cupoanterior), str(alternativa.cupo)),request, "add")
                return JsonResponse({'result': 'ok', 'valor': alternativa.cupo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad',"mensaje": u"Error al eliminar los datos."})

        elif action == 'addprofesor':
            try:
                profesor=ProfesoresTitulacion(alternativa_id=int(request.POST['ida']),profesorTitulacion_id=int(request.POST['idp']))
                profesor.save(request)
                log(u'Adiciono profesores Titulación:%s'%profesor,request, "add")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'delprofesor':
            try:
                profesor = ProfesoresTitulacion.objects.get(pk=int(request.POST['id']))
                if not profesor.alternativa.grupotitulacion.grupocerrado():
                    if profesor.tiene_asignaturas_asignadas():
                        return JsonResponse({"result": "bad", "mensaje": u"No puede Eliminar, tiene materias asignadas"})
                    log(u'Elimino profesor Titulación:%s la persona: %s' % (profesor, persona), request, "del")
                    profesor.delete()
                    # profesor.status=False
                    # profesor.save(request)
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad","mensaje": u"No puede Eliminar, el Grupo esta Cerrado"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad',"mensaje": u"Error al guardar los datos"})

        elif action == 'comprobacionarchivo':
            try:
                matricula = MatriculaTitulacion.objects.get(pk=int(request.POST['idm']))
                if matricula.comprobacionarchivo:
                    matricula.comprobacionarchivo = False
                else:
                    matricula.comprobacionarchivo = True
                matricula.save(request)
                log(u'Cambio de Estado de Comprobacion el Archivo:%s' % matricula, request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'matricularestudiante':
            try:
                newfilecedula = None
                newfilevotacion = None
                alter = AlternativaTitulacion.objects.get(pk=int(request.POST['ida']))
                if alter.grupotitulacion.grupocerrado():
                    return JsonResponse({'result': "bad", "mensaje": u"El Proceso de Titulación ya culmino"})
                if alter.tiene_cupos():
                    inscripcion = Inscripcion.objects.get(pk=int(request.POST['idi']))
                    if 'cedula' in request.FILES and 'votacion' in request.FILES:
                        newfilecedula = request.FILES['cedula']
                        newfilecedula._name = generar_nombre("DocumentoPersonal_", newfilecedula._name)
                        newfilevotacion = request.FILES['votacion']
                        newfilevotacion._name = generar_nombre("DocumentoPersonal_", newfilevotacion._name)
                    alter = AlternativaTitulacion.objects.get(pk=int(request.POST['ida']))
                    examen = False
                    matricula = MatriculaTitulacion(alternativa=alter,
                                                    inscripcion=inscripcion,
                                                    documento_cedula=newfilecedula,
                                                    documento_certificado_votacion=newfilevotacion,
                                                    fechainscripcion=datetime.now().date(),
                                                    estado=1)
                    matricula.save(request)
                    # if alter.tipotitulacion.tipo == 1:
                    #     matricula = MatriculaTitulacion(alternativa_id=int(request.POST['ida']),
                    #                                     inscripcion=inscripcion,
                    #                                     documento_cedula=newfilecedula,
                    #                                     documento_certificado_votacion=newfilevotacion,
                    #                                     fechainscripcion=datetime.now().date(),
                    #                                     estado=6)
                    # else:
                    #     matricula = MatriculaTitulacion(alternativa_id=int(request.POST['ida']),
                    #                                     inscripcion=inscripcion,
                    #                                     documento_cedula=newfilecedula,
                    #                                     documento_certificado_votacion=newfilevotacion,
                    #                                     fechainscripcion=datetime.now().date(),
                    #                                     estado=1)
                    #     examen = True
                    # matricula.save(request)
                    if alter.tiene_examen():
                        comexa = ComplexivoExamenDetalle(matricula= matricula, examen = alter.get_examen())
                        comexa.save(request)
                        log(u"Añade alumno al Examen:%s" % comexa, request, "add")

                    log(u'Matricular estudiante administrador:%s' % matricula, request, "add")
                    display = request.POST.get("estadogestion", None)
                    if display in ["True"]:
                        matricula = MatriculaTitulacion.objects.get(Q(alternativa=int(request.POST['ida'])),Q(inscripcion_id=inscripcion.id),(Q(estado=6) | Q(estado=1)))
                        esta_gestacion = EstadoGestacion(matriculatitulacion_id=matricula.id, estadogestacion=True)
                        esta_gestacion.save(request)
                        log(u'Matricular estudiante administrador:%s' % esta_gestacion, request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u"En hora buena ustad esta matriculado en el proceso titulacion", 'examen': examen})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No Dispone de cupos para la Matriculación"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': "bad", "mensaje": u"Error al Guadar los datos"})

        elif action == 'actualizar_matriculados':
            try:
                alter = AlternativaTitulacion.objects.get(pk=int(request.POST['ida']))
                if alter.matricula_finalizada():
                    # lista_matriculados= MatriculaTitulacion.objects.filter(Q(alternativa_id = alter.id),Q(alternativa__tipotitulacion__tipo=1), Q(status = True), (Q(estado = 6)|Q(estado = 7)))
                    lista_matriculados = MatriculaTitulacion.objects.filter(Q(alternativa_id=alter.id), Q(alternativa__tipotitulacion__tipo=1), Q(status=True), (Q(estado=6) | Q(estado=7)))
                    for estudiante in lista_matriculados:
                        if estudiante.estado == 6:
                            mat = MatriculaTitulacion.objects.get(id=estudiante.id)
                            mat.estado = 8
                            mat.save(request)
                            log(u'Eliminacion de Matricula:%s' % mat, request, "del")
                        if estudiante.estado == 7:
                            if estudiante.tiene_propuesta():
                                propuesta_mat = PropuestaTitulacion_Matricula.objects.get( matricula__inscripcion=estudiante.inscripcion, status=True)
                                propuesta = PropuestaTitulacion.objects.get(propuesta=propuesta_mat.propuesta, status=True)
                                propuesta_mat.status = True
                                propuesta_mat.save(request)
                                log(u'Eliminacion de Propuesta:%s' % propuesta_mat, request, "del")
                                propuest = PropuestaTitulacion.objects.get(pk=propuesta_mat.propuesta_id)
                                propuest.estado = 4
                                propuest.save(request)
                                log(u'Eliminacion de Propuesta:%s' % propuesta, request, "del")
                                mat = MatriculaTitulacion.objects.get(id=propuesta_mat.matricula_id)
                                mat.estado = 8
                                mat.save(request)
                                log(u'Eliminacion de Propuesta:%s' % mat, request, "del")

                    return JsonResponse({"result": "ok", "mensaje": u"El proceso se a llebado a cabo correctamente"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"El proceso de matriculacion esta en curso"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': "bad", "mensaje": u"Error al Guadar los datos"})

        elif action == 'delmatricula':
            try:
                matricula = MatriculaTitulacion.objects.get(pk=int(request.POST['idm']))
                if matricula.alternativa.tipotitulacion.tipo==1 and PropuestaTitulacion_Matricula.objects.filter(matricula=matricula).exists():
                    return JsonResponse({"result": "bad","mensaje": u"No puede Eliminar Tiene Proyecto Activo"})
                matricula.estado=8
                matricula.motivo=request.POST['motivo']
                matricula.save(request)
                if  ComplexivoExamenDetalle.objects.filter(matricula=matricula).exists():
                    exa = ComplexivoExamenDetalle.objects.get(matricula=matricula)
                    log(u"Elimino Alumno del Examen %s" % exa, request, "del")
                    exa.delete()
                send_html_mail("Matricula Eliminada", "emails/eliminadomatriculatitulacion.html",{'sistema': request.session['nombresistema'], 'matricula': matricula, 'fechaeliminacion':datetime.now()}, matricula.inscripcion.persona.lista_emails_envio(), [])
                log(u'Elimino Matricula Titulación:%s' % matricula, request, "del")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})


        elif action == 'reprobarmatricula':
            try:
                matricula = MatriculaTitulacion.objects.get(pk=int(request.POST['idm']))
                matricula.estado=9
                matricula.save(request)
                if ComplexivoDetalleGrupo.objects.filter(status=True, matricula=matricula):
                    comple = ComplexivoDetalleGrupo.objects.filter(status=True, matricula=matricula).order_by("-id")[0]
                    comple.califico = True
                    comple.estadotribunal = 3
                    comple.save(request)
                log(u'Reprobó Matricula Titulación:%s' % matricula, request, "rep")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'activarmatricula':
            try:
                matricula = MatriculaTitulacion.objects.get(pk=int(request.POST['idm']))
                matricula.estado=1
                matricula.save(request)
                if ComplexivoDetalleGrupo.objects.filter(status=True, matricula=matricula):
                    comple = ComplexivoDetalleGrupo.objects.filter(status=True, matricula=matricula).order_by("-id")[0]
                    comple.estadotribunal = 1
                    comple.califico = False
                    comple.save(request)
                log(u'Activó Matricula Titulación:%s' % matricula, request, "rep")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        # -----------MATERIAS------------------------------
        elif action == 'addmateria':
            try:
                f = ComplexivoMateriaForm(request.POST)
                if f.is_valid():
                    alternativa = AlternativaTitulacion.objects.get(pk=request.POST['alternativa'])
                    if not alternativa.get_cronograma():
                        return JsonResponse({"result": 'bad', "mensaje": u"Error, Fechas no asignadas al cronograma"})
                    fechainicio = alternativa.get_cronograma().get().fechanucleobasicoinicio
                    fechafin = alternativa.get_cronograma().get().fechanucleoproffin
                    inicio = f.cleaned_data['fechainicio']
                    fin = f.cleaned_data['fechafin']
                    horatotal = f.cleaned_data['horatotal']
                    horasemanal = f.cleaned_data['horasemanal']
                    if not fechainicio:
                        return JsonResponse({"result": 'bad', "mensaje": u"Fechas no asignadas al cronograma"})
                    if not fechafin:
                        return JsonResponse({"result": 'bad', "mensaje": u"Fechas no asignadas al cronograma"})
                    if horatotal < horasemanal:
                        return JsonResponse({"result": 'bad', "mensaje": u"Las horas semanales exceden a las horas totales"})
                    if inicio > fin:
                        return JsonResponse({"result": 'bad', "mensaje": u"Fechas incorrectas"})
                    if not ((inicio >= fechainicio and inicio < fechafin) and (fin > fechainicio and fin <= fechafin)):
                        return JsonResponse({"result": 'bad', "mensaje": u"Las fechas no concuerdan con el periodo de clases"})
                    if horatotal > alternativa.get_horasrestantes():
                        return JsonResponse({"result": 'bad', "mensaje": u"Las horas totales superan a las horas disponibles"})
                    materia = ComplexivoMateria(asignatura = f.cleaned_data['asignatura'],
                                                alternativa_id = int(request.POST['alternativa']),
                                                fechainicio = inicio,
                                                fechafin = fin,
                                                sesion = alternativa.get_sesion().sesion if alternativa.get_sesion() else  f.cleaned_data['sesion'],
                                                profesor = f.cleaned_data['profesor'])
                    materia.save(request)
                    log(u"Adiciono asignatura: %s[%s]" % (materia,materia.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        elif action == 'editmateria':
            try:
                f = ComplexivoMateriaForm(request.POST)
                if f.is_valid():
                    alternativa = AlternativaTitulacion.objects.get(pk=request.POST['alternativa'])
                    if not alternativa.get_cronograma():
                        return JsonResponse({"result": 'bad', "mensaje": u"Error, Fechas no asignadas al cronograma"})
                    fechainicio = alternativa.get_cronograma().get().fechanucleobasicoinicio
                    fechafin = alternativa.get_cronograma().get().fechanucleoproffin
                    if not fechainicio:
                        return JsonResponse({"result": 'bad', "mensaje": u"Error, Fechas no asignadas al cronograma"})
                    if not fechafin:
                        return JsonResponse({"result": 'bad', "mensaje": u"Error, Fechas no asignadas al cronograma"})
                    inicio = f.cleaned_data['fechainicio']
                    fin = f.cleaned_data['fechafin']
                    horatotal = f.cleaned_data['horatotal']
                    horasemanal = f.cleaned_data['horasemanal']
                    if horatotal < horasemanal:
                        return JsonResponse({"result": 'bad', "mensaje": u"Las horas semanales exceden a las horas totales"})
                    if inicio > fin:
                        return JsonResponse({"result": 'bad', "mensaje": u"Fechas incorrectas"})
                    if not ((inicio >= fechainicio and inicio < fechafin) and (fin > fechainicio and fin <= fechafin)):
                        return JsonResponse({"result": 'bad', "mensaje": u"Las fechas no concuerdan con el periodo de clases"})
                    materia = ComplexivoMateria.objects.get(pk=request.POST['id'])
                    if horatotal > alternativa.get_horasrestantes(materia.id):
                        return JsonResponse({"result": 'bad', "mensaje": u"Las horas totales superan a las horas disponibles por el modelo de titulacion"})
                    if alternativa.get_sesion():
                        materia.sesion = alternativa.get_sesion().sesion
                    else:
                        if 'sesion' in request.POST:
                            materia.sesion = f.cleaned_data['sesion']
                    if 'profesor' in request.POST:
                        materia.profesor_id = request.POST['profesor']
                    materia.horatotal = f.cleaned_data['horatotal']
                    materia.horasemanal = f.cleaned_data['horasemanal']
                    materia.save(request)
                    log(u"Edito asignatura: %s" % materia, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        elif action == 'deletemateria':
            try:
                materia = ComplexivoMateria.objects.get(pk=request.POST['id'])
                if not materia.tiene_horario() and not materia.tiene_asignacion():
                    materia.complexivomateriaasignada_set.all().delete()
                    log(u"Elimino asignatura: %s" % materia, request, "del")
                    materia.delete()
                    return JsonResponse({"result": "ok", "id": materia.id})
                else:
                    return JsonResponse({"result": "bad", "id": materia.id,"mensaje": u"Error, la materia esta asignada a un curso u horario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # ---------------CLASES--------------------
        elif action == 'editclase':
            try:
                f = ComplexivoClaseForm(request.POST)
                if f.is_valid():
                    turno = Turno.objects.get(pk=request.POST['turno'])
                    dia = request.POST['dia']
                    materia = ComplexivoMateria.objects.get(pk=request.POST['materia'])
                    clase = ComplexivoClase.objects.get(pk=request.POST['id'])
                    clase.fechainicio = materia.fechainicio
                    clase.fechafin = materia.fechafin
                    clase.aula_id = request.POST['aula']
                    clase.save(request)
                    log(u"Edito clase: %s" % clase, request, "edit")
                else:
                    raise NameError('Error')
                return JsonResponse({"result": "ok"}),
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        elif action == 'addaula':
            try:
                f = ComplexivoClaseForm(request.POST)
                if f.is_valid():
                    materia = ComplexivoMateria.objects.get(pk=request.POST['id'])
                    clases = materia.complexivoclase_set.filter(status=True)
                for clase in clases:
                    clase.aula = f.cleaned_data['aula']
                    clase.save(request)
                    log(u"Edito aula: %s" % clase, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el aula.(%s)" % ex})

        elif action == 'matricular':
            try:
                alternativa = AlternativaTitulacion.objects.get(pk=request.POST['alt'], status=True)
                inscritos = alternativa.matriculatitulacion_set.filter(status=True, estado=1)
                materias = alternativa.complexivomateria_set.filter(status=True)
                if materias.count() > 0:
                    for inscrito in inscritos:
                        for materia in materias:
                            if not ComplexivoMateriaAsignada.objects.filter(matricula=inscrito, materia=materia).exists():
                                matricula = ComplexivoMateriaAsignada(materia=materia,matricula=inscrito)
                                matricula.save(request)
                                log(u"Adiciono matricula a asignatura: %s" % matricula, request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u"Inscripción correcta"})
                else:
                    return JsonResponse({"result": "ok", "mensaje": u"No existen materias"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error de inscripción.(%s)" % ex})

        elif action == 'eliminarasignacionasignatura':
            try:
                materia = ComplexivoMateria.objects.get(pk=request.POST['id'])
                inscripciones = ComplexivoMateriaAsignada.objects.filter(materia=materia, status=True)
                for ins in inscripciones:
                    log(u"elimino la inscripción del alumno: %s de la asignatura %s" % (ins.matricula, ins.materia), request, "del")
                inscripciones.delete()
                return JsonResponse({"result": "ok", "mensaje": u"Inscripción correcta"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error de inscripción."})

        elif action == 'eliminarasignacionesasignaturas':
            try:
                alternativa = AlternativaTitulacion.objects.get(pk=request.POST['ida'])
                materias = alternativa.complexivomateria_set.values_list("id", flat=False).all()
                if not alternativa.tienen_incriciones_asistencia():
                    inscripciones = ComplexivoMateriaAsignada.objects.filter(materia_id__in=materias, status=True)
                    for ins in inscripciones:
                        log(u"elimino la inscripción del alumno: %s de la asignatura %s" % (ins.matricula,ins.materia), request, "del")
                    inscripciones.delete()
                    return JsonResponse({"result": "ok", "mensaje": u"Inscripciones eliminadas correctamente"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Existen asistencia tomadas de las asignaturas"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error de inscripción."})
        #------------------------------EXAMEN COMPLEXIVO---------------------------------------
        elif action == 'addexamen':
            try:
                f = ComplexivoExamenForm(request.POST)
                if f.is_valid():
                    exa = f.cleaned_data['fechaexamen']
                    gra = f.cleaned_data['fechaexamenrecuperacion']
                    if int(request.POST['profesor'])<=0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"Ingrese un Profesor"})
                    if int(f.cleaned_data['notaminima'])<=0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"la nota minima debe ser mayor a 0"})
                    cro = CronogramaExamenComplexivo.objects.get(alternativatitulacion=request.POST['alternativa'])
                    if exa < cro.fechaaprobexameninicio or exa > cro.fechaaprobexamenfin:
                        return JsonResponse({'result': 'bad','mensaje': u"Fechas no estan acorde al cronograma"})
                    # if exa > gra :
                    #     return JsonResponse({'result':'bad', 'mensaje':u"Fecha de examen de gracia no debe ser menor a la fecha de Examen complexivo"})
                    examen = ComplexivoExamen(alternativa_id=request.POST['alternativa'],
                                              aula=f.cleaned_data['aula'],
                                              fechaexamen=f.cleaned_data['fechaexamen'],
                                              docente_id=int(request.POST['profesor']),
                                              notaminima=f.cleaned_data['notaminima'],
                                              horainicio=f.cleaned_data['horainicio'],
                                              horafin=f.cleaned_data['horafin'],
                                              horainiciorecuperacion=f.cleaned_data['horainiciorecuperacion'],
                                              horafinrecuperacion=f.cleaned_data['horafinrecuperacion'],
                                              fechaexamenrecuperacion=f.cleaned_data['fechaexamenrecuperacion'])
                    examen.save(request)
                    matriculados = examen.alternativa.matriculatitulacion_set.filter(estado=1)
                    for matriculado in matriculados:
                        detalle = ComplexivoExamenDetalle()
                        detalle.examen=examen
                        detalle.matricula = matriculado
                        detalle.save(request)
                    else:
                        log(u"Adiciono examen: %s" % examen, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        elif action == 'editexamen':
            try:
                f = ComplexivoExamenForm(request.POST)
                if f.is_valid():
                    exa = f.cleaned_data['fechaexamen']
                    gra = f.cleaned_data['fechaexamenrecuperacion']
                    if int(request.POST['profesor']) <= 0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"Ingrese un Profesor"})
                    if int(f.cleaned_data['notaminima']) <= 0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"la nota minima debe ser mayor a 0"})
                    cro = CronogramaExamenComplexivo.objects.get(alternativatitulacion=request.POST['alternativa'])
                    if exa < cro.fechaaprobexameninicio or exa > cro.fechaaprobexamenfin:
                        return JsonResponse({'result': 'bad', 'mensaje': u"Fechas no estan acorde al cronograma"})
                    if exa > gra:
                        return JsonResponse({'result': 'bad','mensaje': u"Fecha de examen de gracia no debe ser menor a la fecha de Examen complexivo"})
                    examen = ComplexivoExamen.objects.get(pk=request.POST['id'])
                    examen.aula = f.cleaned_data['aula']
                    examen.fechaexamen = f.cleaned_data['fechaexamen']
                    examen.docente_id=int(request.POST['profesor'])
                    examen.notaminima = f.cleaned_data['notaminima']
                    examen.horainicio = f.cleaned_data['horainicio']
                    examen.horafin = f.cleaned_data['horafin']
                    examen.horainiciorecuperacion= f.cleaned_data['horainiciorecuperacion']
                    examen.horafinrecuperacion = f.cleaned_data['horafinrecuperacion']
                    examen.fechaexamenrecuperacion = f.cleaned_data['fechaexamenrecuperacion']
                    examen.save(request)
                    log(u"Edito examen: %s" % examen, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})

        elif action == 'deleteexamen':
            try:
                examen = ComplexivoExamen.objects.get(pk=request.POST['id'])
                if not examen.tiene_examen():
                    examen.status = False
                    examen.save(request)
                    log(u"Elimino examen: %s" % examen, request, "delete")
                    return JsonResponse({"result": "ok", "id": examen.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya se asignado calificaciones"})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex})

        elif action == 'diasacalificar':
            try:
                examen = ComplexivoExamen.objects.get(pk=request.POST['id'])
                form = ComplexivoCalificacionDiaForm(request.POST)
                if form.is_valid():
                    examen.usacronograma = form.cleaned_data['usacronograma']
                    examen.diascalificar = form.cleaned_data['diasacalificar'] if form.cleaned_data['diasacalificar'] else 1
                    examen.save(request)
                    log(u'Cambio en fecha de calificaciones de examen: %s' % examen, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'existecronograma':
            try:
                alternativa = AlternativaTitulacion.objects.get(pk=request.POST['alt'])
                mensaje = ""
                result = "bad"
                if alternativa.get_cronograma():
                    result = "ok"
                else:
                    mensaje = "Para poder adicionar debe llenar primero el cronograma"
                return JsonResponse({"result": result, "mensaje": mensaje})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'actualizaraprobados':
            try:
                if 'id' in request.POST:
                    if PeriodoGrupoTitulacion.objects.filter(pk=int(request.POST['id']), fechafin__lt=datetime.now().date()).exists():
                        perg = PeriodoGrupoTitulacion.objects.get(id=int(request.POST['id']), fechafin__lt=datetime.now().date())
                        if cerrar_periodo_titulacion(perg.id):
                            return JsonResponse({"result": "ok", "mensaje": u'Se actualizado correctamente.'})
                        else:
                            return JsonResponse({"result": "ok", "mensaje": u'No hay periodos culminados para actualizar.'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u'El periodo de titulación que intenta cerrar no ha culminado.'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'confirmarabrirperiodo':
            try:
                if 'id' in request.POST:
                    if PeriodoGrupoTitulacion.objects.filter(pk=int(request.POST['id'])).exists():
                        perg = PeriodoGrupoTitulacion.objects.get(id=int(request.POST['id']))
                        perg.abierto = True
                        perg.save(request)
                        return JsonResponse({"result": "ok", "mensaje": u'Se actualizado aperturo correctamente el perido.'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u'El periodo de titulación que intenta aperturar no ha cerrado.'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        # ------------------------------------CRONOGRAMA DE TITULACION------------------------------
        elif action == 'complexivonucleoconocimiento':
            try:
                f = CronogramaNucleoConocimientoComplexivoForm(request.POST)
                if f.is_valid():
                    cronograma = CronogramaExamenComplexivo.objects.get(pk=request.POST['id'])
                    if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechanucleobasicoinicio'], f.cleaned_data['fechanucleoproffin']):
                        return JsonResponse({"result": "bad", "mensaje": u"No se encuentra dentro del rango del periodo de titulación"})
                    if not f.cleaned_data['fechanucleobasicoinicio'] <= f.cleaned_data['fechanucleoproffin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio no puede mayor a fecha fin"})
                    cronograma.fechanucleobasicoinicio = f.cleaned_data['fechanucleobasicoinicio']
                    cronograma.fechanucleoproffin = f.cleaned_data['fechanucleoproffin']
                    cronograma.save(request)
                    log(u"Asigna clases a cronograma con alternativa %s - [%s] %s" % (cronograma.alternativatitulacion_id, cronograma.alternativatitulacion.paralelo, cronograma.alternativatitulacion.carrera), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

        elif action == 'complexivoaprobacionexamen':
            try:
                f = CronogramaAprobacionExamenComplexivoForm(request.POST)
                if f.is_valid():
                    cronograma = CronogramaExamenComplexivo.objects.get(pk=request.POST['id'])
                    if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechaaprobexameninicio'], f.cleaned_data['fechaaprobexamenfin']):
                        return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas de aprobacion de examen complexivo con periodo de titulación"})
                    if not f.cleaned_data['fechaaprobexameninicio'] <= f.cleaned_data['fechaaprobexamenfin']:
                        return JsonResponse({"result": "bad","mensaje": u"La fecha inicio de aprobacion de examen complexivo no puede ser mayor que la fecha fin"})
                    if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechasubircalificacionesinicio'], f.cleaned_data['fechasubircalificacionesfin']):
                        return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas subida de calificaciones de examen complexivo con periodo de titulación"})
                    if not f.cleaned_data['fechasubircalificacionesinicio'] <= f.cleaned_data['fechasubircalificacionesfin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio subida de calificaciones de examen complexivo no puede ser mayor que la fecha fin"})
                    if f.cleaned_data['fechaaprobexamengraciainicio'] and f.cleaned_data['fechaaprobexamengraciafin']:
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechaaprobexamengraciainicio'], f.cleaned_data['fechaaprobexamengraciafin']):
                            return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas de aprobación de examen de gracia con periodo de titulación"})
                        if not f.cleaned_data['fechaaprobexamengraciainicio'] <= f.cleaned_data['fechaaprobexamengraciafin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio de aprobación de examen de gracia no puede ser mayor que la fecha fin"})
                    if f.cleaned_data['fechasubircalificacionesgraciainicio'] and f.cleaned_data['fechasubircalificacionesgraciafin']:
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechasubircalificacionesgraciainicio'], f.cleaned_data['fechasubircalificacionesgraciafin']):
                            return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas subida de calificaciones de examen de gracia con periodo de titulación"})
                        if not f.cleaned_data['fechasubircalificacionesgraciainicio'] <= f.cleaned_data['fechasubircalificacionesgraciafin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio subida de calificaciones de examen de gracia no puede ser mayor que la fecha fin"})
                    cronograma.fechaaprobexameninicio = f.cleaned_data['fechaaprobexameninicio']
                    cronograma.fechaaprobexamenfin = f.cleaned_data['fechaaprobexamenfin']
                    cronograma.fechaaprobexamengraciainicio = f.cleaned_data['fechaaprobexamengraciainicio']
                    cronograma.fechaaprobexamengraciafin = f.cleaned_data['fechaaprobexamengraciafin']
                    cronograma.fechasubircalificacionesinicio = f.cleaned_data['fechasubircalificacionesinicio']
                    cronograma.fechasubircalificacionesfin = f.cleaned_data['fechasubircalificacionesfin']
                    cronograma.fechasubircalificacionesgraciainicio = f.cleaned_data['fechasubircalificacionesgraciainicio']
                    cronograma.fechasubircalificacionesgraciafin = f.cleaned_data['fechasubircalificacionesgraciafin']
                    cronograma.save(request)
                    log(u"Asigna aprobarexamen a cronograma con alternativa %s - [%s] %s" % (cronograma.alternativatitulacion_id, cronograma.alternativatitulacion.paralelo, cronograma.alternativatitulacion.carrera), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

        elif action == 'complexivopropuestapractica':
            try:
                f = CronogramaPropuestaPracticaComplexivoForm(request.POST)
                if f.is_valid():
                    cronograma = CronogramaExamenComplexivo.objects.get(pk=request.POST['id'])
                    if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo( f.cleaned_data['fechaeleccionpropuestainicio'], f.cleaned_data['fechaeleccionpropuestafin']):
                        return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas elección de tema/línea de investigación con periodo de titulación"})
                    if not f.cleaned_data['fechaeleccionpropuestainicio'] <= f.cleaned_data['fechaeleccionpropuestafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio de elección de tema/línea de investigación no puede ser mayor que la fecha fin"})
                    if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechapropuestainicio'], f.cleaned_data['fechapropuestafin']):
                        return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas ejecución y revisión con periodo de titulación"})
                    if not f.cleaned_data['fechapropuestainicio'] <= f.cleaned_data['fechapropuestafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio de ejecución y revisión no puede ser mayor que la fecha fin"})
                    # if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechaentregadocumentoinicio'], f.cleaned_data['fechaentregadocumentofin']):
                    #     return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas entrega de carpetas al tribunal con periodo de titulación"})
                    # if not f.cleaned_data['fechaentregadocumentoinicio'] <= f.cleaned_data['fechaentregadocumentofin']:
                    #     return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio de entrega de carpetas al tribunal no puede ser mayor que la fecha fin"})
                    if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechadefensaevaluacioninicio'], f.cleaned_data['fechadefensaevaluacionfin']):
                        return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas evaluación del tribunal con periodo de titulación"})
                    if not f.cleaned_data['fechadefensaevaluacioninicio'] <= f.cleaned_data['fechadefensaevaluacionfin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio de evaluación del tribunal no puede ser mayor que la fecha fin"})
                    cronograma.fechapropuestainicio = f.cleaned_data['fechapropuestainicio']
                    cronograma.fechapropuestafin = f.cleaned_data['fechapropuestafin']
                    cronograma.fechaeleccionpropuestafin = f.cleaned_data['fechaeleccionpropuestafin']
                    cronograma.fechaeleccionpropuestainicio = f.cleaned_data['fechaeleccionpropuestainicio']
                    # cronograma.fechaentregadocumentoinicio = f.cleaned_data['fechaentregadocumentoinicio']
                    # cronograma.fechaentregadocumentofin = f.cleaned_data['fechaentregadocumentofin']
                    cronograma.fechardefensaevaluacioninicio = f.cleaned_data['fechadefensaevaluacioninicio']
                    cronograma.fechardefensaevaluacionfin = f.cleaned_data['fechadefensaevaluacionfin']
                    cronograma.save(request)
                    log(u"Asigna propuesta práctica a cronograma con alternativa %s - [%s] %s" % (cronograma.alternativatitulacion_id, cronograma.alternativatitulacion.paralelo, cronograma.alternativatitulacion.carrera), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

        elif action == 'complexivorevisionestudiante' or action == 'editcomplexivorevisionestudiante':
            try:
                f = CronogramaRevisionEstudianteComplexivoForm(request.POST)
                if f.is_valid():
                    if action == 'complexivorevisionestudiante':
                        cronograma = CronogramaExamenComplexivo.objects.get(pk=request.POST['id'])
                        revision = DetalleRevisionCronograma()
                    else:
                        revision = DetalleRevisionCronograma.objects.get(pk=request.POST['id'])
                        cronograma = revision.cronograma
                    if cronograma.registrar_revision() or action == 'editcomplexivorevisionestudiante':
                        if f.cleaned_data['fechainicio'] < cronograma.fechapropuestainicio or f.cleaned_data['fechainicio'] > cronograma.fechapropuestafin or f.cleaned_data['fechafin'] < cronograma.fechapropuestainicio or f.cleaned_data['fechafin'] > cronograma.fechapropuestafin or f.cleaned_data['calificacioninicio'] < cronograma.fechapropuestainicio or f.cleaned_data['calificacioninicio'] > cronograma.fechapropuestafin or f.cleaned_data['calificacionfin'] < cronograma.fechapropuestainicio or f.cleaned_data['calificacionfin'] > cronograma.fechapropuestafin:
                            return JsonResponse({"result": "bad", "mensaje": u"Las fechas deben estar dentro del rango definidos para la realizacion de la propuesta.."})
                        if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de desarrolo de propuesta no puede ser mayor a la fecha de inicio de la misma"})
                        # if f.cleaned_data['calificacioninicio'] < f.cleaned_data['fechafin']:
                        if  f.cleaned_data['fechafin'] >  f.cleaned_data['calificacionfin']:
                            return JsonResponse({"result": "bad", "mensaje": u"la fecha de calificacion debe ser posterior a la fecha de revision de propuesta"})
                        if f.cleaned_data['calificacionfin'] < f.cleaned_data['calificacioninicio']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de calificacion final no puede ser menor a la fecha de calificacion inicial"})
                        if action == 'editcomplexivorevisionestudiante':
                            if revision.anterior():
                                anterior = revision.anterior()
                                if f.cleaned_data['fechainicio'] < anterior.calificacionfin:
                                    return JsonResponse({"result": "bad", "mensaje": u"La fecha de revisión debe ser mayor a la fecha de calificacion de la revisión anterior"})
                            if revision.posterior():
                                posterior = revision.posterior()
                                if f.cleaned_data['calificacionfin'] > posterior.fechainicio:
                                    return JsonResponse({"result": "bad", "mensaje": u"La Fecha de calificación debe ser menor a la fecha de revision del registro revision posterior"})
                        else:
                            if cronograma.detallerevisioncronograma_set.filter(status=True).exists():
                                ultima = cronograma.ultima_revision()
                                if f.cleaned_data['fechainicio'] < ultima.calificacionfin:
                                    return JsonResponse({"result": "bad", "mensaje": u"La fecha de revision de propuesta debe ser mayor a la fecha de calificacion del registro de revision anterior"})
                        revision.cronograma = cronograma
                        revision.fechainicio = f.cleaned_data['fechainicio']
                        revision.fechafin = f.cleaned_data['fechafin']
                        revision.calificacioninicio = f.cleaned_data['calificacioninicio']
                        revision.calificacionfin = f.cleaned_data['calificacionfin']
                        # revision.validaplagio = f.cleaned_data['validaplagio']
                        revision.save(request)
                        log(u"Adiciona revisión estudiante a cronograma con alternativa %s - [%s] %s" % (cronograma.alternativatitulacion_id, cronograma.alternativatitulacion.paralelo, cronograma.alternativatitulacion.carrera), request, "add")
                        return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

        elif action == 'deleterevision':
            try:
                revision = DetalleRevisionCronograma.objects.get(pk=request.POST['id'])
                revision.status = False
                revision.save(request)
                log(u"Elimina revisión propuesta %s de cronograma %s con alternativa %s - [%s] %s" % (revision.id, revision.cronograma_id, revision.cronograma.alternativatitulacion_id, revision.cronograma.alternativatitulacion.paralelo, revision.cronograma.alternativatitulacion.carrera), request, "delete")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

        elif action == 'newcronograma':
            try:
                alternativa = AlternativaTitulacion.objects.get(pk=request.POST['alt'])
                if not CronogramaExamenComplexivo.objects.filter(alternativatitulacion=alternativa).exists():
                    cronograma = CronogramaExamenComplexivo()
                    cronograma.alternativatitulacion = alternativa
                    cronograma.save(request)
                    log(u"Crea cronograma %s con alternativa %s - [%s] %s" % (cronograma.id, cronograma.alternativatitulacion_id, cronograma.alternativatitulacion.paralelo, cronograma.alternativatitulacion.carrera), request, "Add")
                # else:
                cronograma = CronogramaExamenComplexivo.objects.get(alternativatitulacion=request.POST['alt'])
                return JsonResponse({"result": "ok", "action": "examencomplexivo", "id": cronograma.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
        #----------------------------PERIODO DE TITULACION--------------------------------
        elif action == 'addperiodo':
            try:
                form = PeriodoGrupoTitulacionForm(request.POST)
                if form.is_valid():
                    nombres=form.cleaned_data['nombre']
                    if form.cleaned_data['fechainicio']< form.cleaned_data['fechafin']:
                        if not PeriodoGrupoTitulacion.objects.filter(nombre=nombres, status=True).exists():
                            periodo=PeriodoGrupoTitulacion(nombre=form.cleaned_data['nombre'],
                                                           descripcion=form.cleaned_data['descripcion'],
                                                           fechainicio=form.cleaned_data['fechainicio'],
                                                           fechafin=form.cleaned_data['fechafin'],
                                                           porcentajeurkund=form.cleaned_data['plagio'],
                                                           nrevision=form.cleaned_data['nrevision'],
                                                           )
                            periodo.save(request)
                            log(u'Agrego Periodo Titulación: %s' % periodo, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La Fecha esta mal ingresados."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editperiodo':
            try:
                periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['id']))
                form = PeriodoGrupoTitulacionForm(request.POST)
                if form.is_valid():
                    # if periodo.tiene_grupo_activo():
                    #     periodo.descripcion = form.cleaned_data['descripcion']
                    #     periodo.porcentajeurkund = form.cleaned_data['plagio']
                    #     periodo.nrevision = form.cleaned_data['nrevision']
                    #     periodo.save(request)
                    #     log(u'Editar Periodo de Titulación: %s' % periodo, request, "editar")
                    #     return JsonResponse({"result": "ok"})
                    # else:
                    if form.cleaned_data['fechainicio'] < form.cleaned_data['fechafin']:
                        periodo.nombre=form.cleaned_data['nombre']
                        periodo.descripcion=form.cleaned_data['descripcion']
                        periodo.fechainicio = form.cleaned_data['fechainicio']
                        periodo.fechafin = form.cleaned_data['fechafin']
                        periodo.porcentajeurkund = form.cleaned_data['plagio']
                        periodo.nrevision = form.cleaned_data['nrevision']
                        periodo.save(request)
                        log(u'Editar Periodo de Titulación: %s' % periodo, request, "editar")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La Fecha esta mal ingresados."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action=='delperiodo':
            try:
                periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['id']))
                if not periodo.no_puede_eliminar():
                    periodo.status= False
                    periodo.save(request)
                    log(u'Elimino Periodo titulacion: %s' % periodo, request, "del")
                else:
                    return JsonResponse({"result": "bad","mensaje": u"No se puede Eliminar el Periodo de Titulacion, tiene Grupos de Titulacion Activas.."})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addarchivoperiodo':
            try:
                f = ArchivosTitulacionForm(request.POST, request.FILES)
                if f.is_valid():
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivotitulacion_", newfile._name)
                        archivo = ArchivoTitulacion(nombre=f.cleaned_data['nombre'],
                                                    tipotitulacion_id=2,
                                                    archivo=newfile)
                        archivo.save(request)
                        log(u'Agrego Archivo Titulación: %s' % archivo, request, "addarchivo")
                        return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editarchivoperiodo':
            try:
                f = ArchivosTitulacionForm(request.POST, request.FILES)
                if f.is_valid():
                    archivo = ArchivoTitulacion.objects.get(pk=request.POST['id'])
                    archivo.nombre = f.cleaned_data['nombre']
                    # archivo.tipotitulacion = f.cleaned_data['tipotitulacion']
                    archivo.tipotitulacion_id = 2
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivotitulacion_", newfile._name)
                        archivo.archivo = newfile
                    archivo.save(request)
                    log(u'Edito Archivo Titulación: %s' % archivo, request, "editarchivo")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delarchivoperiodo':
            try:
                archivo = ArchivoTitulacion.objects.get(pk=request.POST['id'])
                if archivo.vigente:
                    return JsonResponse({"result": "bad", "mensaje": u"El archivo se encuentra vigente."})
                archivo.status=False
                archivo.save(request)
                log(u'Elimino Archivo Titulación: %s' % archivo, request, "deletearchivo")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verificar_vigente':
            try:
                archivo = ArchivoTitulacion.objects.get(pk=request.POST['id'])
                if archivo.vigente:
                    return JsonResponse({"result": "ok", "activo":"no"})
                return JsonResponse({"result": "ok", "activo":"si"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al verificar los datos."})

        elif action == 'activardesactivararchivoperiodo':
            try:
                archivo = ArchivoTitulacion.objects.get(pk=request.POST['id'])
                if archivo.vigente:
                    archivo.vigente = False
                else:
                    archivo.vigente = True
                archivo.save(request)
                log(u"cambio vigente archivo titulacion: %s" % archivo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #-----------------------------MODELO DE TITULACION --------------------------------
        elif action == 'addmodelotitulacion':
            try:
                form = ModeloTitulacionForm(request.POST)
                if form.is_valid():
                    nombres=form.cleaned_data['nombre']
                    if not ModeloTitulacion.objects.filter(nombre=nombres, status=True).exists():
                        modelo=ModeloTitulacion(nombre=form.cleaned_data['nombre'],
                                                horaspresencial=int(form.cleaned_data['horaspresencial']),
                                                horasvirtual=int(form.cleaned_data['horasvirtual']),
                                                horasautonoma=int(form.cleaned_data['horasautonoma']),
                                                clases=form.cleaned_data['clases'],
                                                acompanamiento=form.cleaned_data['acompanamiento'],
                                                activo=form.cleaned_data['activo']
                                                )
                        modelo.save(request)
                        log(u'Agrego Modelo de Titulación: %s' % modelo, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmodelotitulacion':
            try:
                modelo = ModeloTitulacion.objects.get(pk=int(request.POST['id']))
                form = ModeloTitulacionForm(request.POST)
                if form.is_valid():
                    if modelo.tiene_alternativa_activas():
                        modelo.nombre = form.cleaned_data['nombre']
                    else:
                        modelo.nombre=form.cleaned_data['nombre']
                        modelo.horaspresencial = int (form.cleaned_data['horaspresencial'])
                        modelo.horasvirtual = int(form.cleaned_data['horasvirtual'])
                        modelo.horasautonoma = int(form.cleaned_data['horasautonoma'])
                    modelo.acompanamiento = form.cleaned_data['acompanamiento']
                    modelo.clases = form.cleaned_data['clases']
                    modelo.activo = form.cleaned_data['activo']
                    modelo.save(request)
                    log(u'Editar Modelo de Titulación: %s' % modelo, request, "editar")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Faltan campos de llenar."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action== 'delmodelotitulacion':
            try:
                modelo = ModeloTitulacion.objects.get(pk=int(request.POST['id']))
                if not modelo.tiene_alternativa_activas():
                    modelo.status= False
                    modelo.save(request)
                    log(u'Elimino Modelo de Titulación: %s' % modelo, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede Eliminar el Modelo de Titulacion, tiene Alternativa de Titulacion proceso.."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'modelotitulacionpdf':
            try:
                data['fecha'] = datetime.now().date()
                data['modelos'] = ModeloTitulacion.objects.filter(status=True).order_by('nombre')
                return conviert_html_to_pdf(
                    'adm_modelotitulacion/reporte_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass
        #--------------------------TIPO DE TITULACION---------------------------

        elif action == 'addtipotitulacion':
            try:
                form = TipoTitulacionForm(request.POST)
                if form.is_valid():
                    nombres=form.cleaned_data['nombre']
                    if not TipoTitulaciones.objects.filter(nombre=nombres, status=True).exists():
                        tipo=TipoTitulaciones(nombre=form.cleaned_data['nombre'],
                                              codigo=form.cleaned_data['codigo'],
                                              caracteristica=form.cleaned_data['caracteristica'],
                                              tipo=int(form.cleaned_data['tipo']),
                                              mecanismotitulacion=form.cleaned_data['mecanismotitulacion']
                                              )
                        tipo.save(request)
                        log(u'Agrego Tipo de Titulación: %s' % tipo, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittipotitulacion':
            try:
                tipo = TipoTitulaciones.objects.get(pk=int(request.POST['id']))
                form = TipoTitulacionForm(request.POST)
                if form.is_valid():
                    tipo.rubrica = form.cleaned_data['rubrica']
                    tipo.codigo = form.cleaned_data['codigo']
                    tipo.codigo = form.cleaned_data['codigo']
                    tipo.caracteristica = form.cleaned_data['caracteristica']
                    tipo.mecanismotitulacion = form.cleaned_data['mecanismotitulacion']
                    if not tipo.tiene_alternativa_activas():
                        tipo.tipo = int(form.cleaned_data['tipo'])
                    tipo.save(request)
                    log(u'Editar Tipo de Titulación: %s' % tipo, request, "editar")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action=='deltipotitulacion':
            try:
                tipo = TipoTitulaciones.objects.get(pk=int(request.POST['id']))
                if not tipo.tiene_alternativa_activas():
                    if tipo.combinartipotitulaciones_set.all().exists():
                        tipo.combinartipotitulaciones_set.all().delete()
                    tipo.delete()
                    # tipo.status= False
                    # tipo.save(request)
                    log(u'Eliminó Tipo de Titulación: %s' % tipo, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar Tipo de Titulación, tiene Alternativas de Titulacion en proceso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'combinartipotitulacion':
            try:
                form = CombinarTipoTitulacionForm(request.POST)
                if form.is_valid():
                    carreras = form.cleaned_data['carreras']
                    tipo = TipoTitulaciones.objects.get(pk=int(request.POST['id']))
                    for carrera in carreras:
                        if not CombinarTipoTitulaciones.objects.filter(tipotitulacion=tipo,carrera=carrera, status=True).exists():
                            combinartipo = CombinarTipoTitulaciones(tipotitulacion=tipo,carrera=carrera)
                            combinartipo.save(request)
                            log(u'Combinar Tipo de Titulación: %s' % combinartipo, request, "add")
                    combina =CombinarTipoTitulaciones.objects.filter(tipotitulacion=tipo, status=True).exclude(carrera__in=carreras)
                    for comb in combina:
                        comb.status=False
                        comb.save(request)
                        log(u'Combinar Tipo de Titulación: %s' % comb, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos a Guardar."})
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}),content_type="application/json")

        # -----------------------------REPORTE DETALLE DEL ESTUDIANTE POR ALTERNATIVA------------------------
        elif action == 'matrizmatriculadosxalternativa_excel':
            try:
                if 'id' in request.POST:
                    alter = AlternativaTitulacion.objects.get(pk=int(request.POST['id']))
                    return (reporte_matrigulados_especificos(alter, None, None, None))
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})
        # -----------------------------REPORTE DETALLE DEL ESTUDIANTE POR ALTERNATIVA------------------------



        # -----------------------------REPORTE DETALLE DEL ESTUDIANTE POR CARRERA------------------------
        elif action == 'matrizmatriculadosxcarrera_excel':
            try:
                if 'idg' in request.POST and 'idc' in request.POST:
                    grupo = GrupoTitulacion.objects.get(pk=int(request.POST['idg']))
                    carrera = Carrera.objects.get(pk=int(request.POST['idc']))
                    if grupo.alternativatitulacion_set.filter(status=True).exists():
                        return (reporte_matrigulados_especificos(None, grupo, carrera, None))
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"la carrera no tiene Alternativas creadas."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        # -----------------------------REPORTE DETALLE DEL ESTUDIANTE POR CARRERA------------------------


        #-----------------------------MATRIZ DE ESTUDIANTES MATRICULADOS POR GRUPO--------------------------
        elif action == 'matrizmatriculadosxgrupo_excel':
            try:
                if 'idg' in request.POST and 'idp' in request.POST:
                    grupo = GrupoTitulacion.objects.get(pk=int(request.POST['idg']))
                    periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['idp']))
                    if grupo.alternativatitulacion_set.filter(status=True).exists():
                        return (reporte_matrigulados_detalle_carrera(None, grupo, None, periodo))
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"la carrera no tiene Alternativas creadas."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        # -----------------------------MATRIZ DE ESTUDIANTES MATRICULADOS POR GRUPO ESPECIFCO--------------------------
        elif action == 'matrizmatriculadosxgrupo_espefica':
            try:
                if 'idg' in request.POST and 'idp' in request.POST:
                    grupo = GrupoTitulacion.objects.get(pk=int(request.POST['idg']))
                    periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['idp']))
                    if grupo.alternativatitulacion_set.filter(status=True).exists():
                        return (reporte_matrigulados_especificos(None, grupo, None, periodo))
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"la carrera no tiene Alternativas creadas."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})



        # -----------------------------MATRIZ DE ESTUDIANTES MATRICULADOS POR PERIODO--------------------------
        elif action == 'matrizmatriculadosxperiodo_excel':
            try:
                if 'idp' in request.POST:
                    periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['idp']))
                    return (reporte_matrigulados_detalle_carrera(None, None, None, periodo))
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        # -----------------------------MATRIZ DE ESTUDIANTES MATRICULADOS POR PERIODO ESPECIFICA--------------------------
        elif action == 'matrizmatriculadosxperiodo_especifica':
            try:
                if 'idp' in request.POST:
                    periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['idp']))
                    return (reporte_matrigulados_especificos(None, None, None, periodo))
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})



        #-----------------------------REPORTES EN PDF------------------------
        #-----------------------------ACTA DE CALIFICACIONES POR ALTERNATIVA ------------------------
        if action == 'actacalificaciones_pdf':
            try:
                if 'id' in request.POST:
                    data['examen'] = examen = ComplexivoExamen.objects.get(status=True, id=int(request.POST['id']))
                    data['matriculados'] = examen.complexivoexamendetalle_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    fecha = datetime.today().date()
                    data['xalter'] = True
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    data['secretariageneral'] = CargoInstitucion.objects.get(pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                    return conviert_html_to_pdf(
                        'adm_alternativatitulacion/actacalificacion_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
            except Exception as ex:
                pass
        #-----------------------------ACTA FINAL POR ALTERNATIVA------------------------
        elif action == 'actafinal_pdf':
            try:
                if 'id' in request.POST:
                    lista = []
                    data['examen'] = examen = ComplexivoExamen.objects.get(status=True, id=int(request.POST['id']))
                    cantaprobado = 0
                    cantreprobado = 0
                    for i in examen.listado_matriculados():
                        estado = ''
                        if i.nota_propuesta():
                            if i.matricula.notafinalcomplexivo() >= examen.notaminima:
                                estado = 'A'
                                cantaprobado+=1
                            else:
                                estado = 'R'
                                cantreprobado+=1
                        else:
                            if datetime.now().date() > i.matricula.alternativa.cronogramaexamencomplexivo_set.filter(status=True)[0].fechardefensaevaluacionfin:
                                estado = 'R'
                                cantreprobado += 1
                        fechadefensapropuesta = ''
                        if i.matricula.datospropuesta():
                            if i.matricula.datospropuesta().grupo:
                                if i.matricula.datospropuesta().grupo.fechadefensa:
                                    fechadefensapropuesta = i.matricula.datospropuesta().grupo.fechadefensa.strftime("%d/%m/%Y")
                        lista.append([str(i.matricula.inscripcion.persona.nombre_completo_inverso()) + ' - ' + str(i.matricula.inscripcion.carrera.alias), i.notafinal, i.nota_propuesta() if i.nota_propuesta() else 0, i.matricula.notafinalcomplexivo() if i.matricula.notafinalcomplexivo() else 0, estado, i.matricula.inscripcion.datos_egresado().fechaegreso.strftime("%d/%m/%Y") if i.matricula.inscripcion.datos_egresado() else '', i.fecha_prueba_teorica().fechaaprobexameninicio.strftime("%d/%m/%Y") if i.fecha_prueba_teorica() else '', fechadefensapropuesta, i.matricula.inscripcion.datos_graduado().fechagraduado.strftime("%d/%m/%Y") if i.matricula.inscripcion.datos_graduado() else '', i.matricula.inscripcion.datos_graduado().fechaactagrado.strftime("%d/%m/%Y") if i.matricula.inscripcion.datos_graduado() else ''])
                    data['lista'] = lista
                    data['cantaprobado'] = cantaprobado
                    data['cantreprobado'] = cantreprobado
                    data['cantestudiantes'] = examen.listado_matriculados().values('id').count()
                    fecha = datetime.today().date()
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    data['secretariageneral'] = CargoInstitucion.objects.get(pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                    return conviert_html_to_pdf(
                        'adm_alternativatitulacion/actafinal_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
            except Exception as ex:
                pass

                # -----------------------------CALIFICACION FINAL POR ALTERNATIVA------------------------
        elif action == 'calificacionfinalevaluacion_pdf':
            try:
                if 'id' in request.POST:
                    lista = []
                    data['examen'] = examen = ComplexivoExamen.objects.get(status=True, id=int(request.POST['id']))
                    cantaprobado = 0
                    cantreprobado = 0
                    for i in examen.listado_matriculados():
                        estado = ''
                        if i.matricula.nota:
                            if i.matricula.notafinalcomplexivoeva() >= examen.notaminima:
                                estado = 'A'
                                cantaprobado += 1
                            else:
                                estado = 'R'
                                cantreprobado += 1
                        else:
                            if datetime.now().date() > i.matricula.alternativa.grupotitulacion.periodogrupo.fechafin:
                                estado = 'R'
                                cantreprobado += 1
                        # fechadefensapropuesta = ''
                        # if i.matricula.datospropuesta():
                        #     if i.matricula.datospropuesta().grupo:
                        #         if i.matricula.datospropuesta().grupo.fechadefensa:
                        #             fechadefensapropuesta = i.matricula.datospropuesta().grupo.fechadefensa.strftime("%d/%m/%Y")
                        lista.append([str(i.matricula.inscripcion.persona.nombre_completo_inverso()) + ' - ' + str(i.matricula.inscripcion.carrera.alias),
                                      i.notafinal,
                                      i.matricula.nota if i.matricula.nota else 0,
                                      i.matricula.notafinalcomplexivoeva() if i.matricula.notafinalcomplexivoeva() else 0,
                                      estado,
                                      i.matricula.inscripcion.datos_egresado().fechaegreso.strftime("%d/%m/%Y") if i.matricula.inscripcion.datos_egresado() else '',
                                      i.fecha_prueba_teorica().fechaaprobexameninicio.strftime("%d/%m/%Y") if i.fecha_prueba_teorica() else '',
                                      i.matricula.inscripcion.datos_graduado().fechagraduado.strftime("%d/%m/%Y") if i.matricula.inscripcion.datos_graduado() else '',
                                      i.matricula.inscripcion.datos_graduado().fechaactagrado.strftime("%d/%m/%Y") if i.matricula.inscripcion.datos_graduado() else ''])
                    data['lista'] = lista
                    data['cantaprobado'] = cantaprobado
                    data['cantreprobado'] = cantreprobado
                    data['cantestudiantes'] = examen.listado_matriculados().count()
                    fecha = datetime.today().date()
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    data['secretariageneral'] = CargoInstitucion.objects.get( pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                    return conviert_html_to_pdf(
                        'adm_alternativatitulacion/calificaciones_final_evaluacion.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
            except Exception as ex:
                pass
        #-----------------------------NOMINA DE EXAMEN POR ALTERNATIVA------------------------
        elif action == 'nomina_examen_pdf':
            try:
                if 'id' in request.POST:
                    data['alternativa'] = alternativa =  AlternativaTitulacion.objects.get(pk=int(request.POST['id']))
                    data['grupotitulacion'] = alternativa.grupotitulacion
                    data['tipotitulacion'] = alternativa.tipotitulacion
                    data['carrera'] = alternativa.carrera
                    data['matriculados'] = alternativa.matriculatitulacion_set.filter(status=True, estado__in=[1, 10]).distinct().order_by('inscripcion')
                    # data['examen'] = examen = ComplexivoExamen.objects.get(status=True, id=int(request.POST['id']))
                    # data['matriculados'] = examen.complexivoexamendetalle_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    fecha = datetime.today().date()
                    data['xalter'] = True
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    data['responsablegta'] = DistributivoPersona.objects.get(status=True, estadopuesto=1, pk=69152) if DistributivoPersona.objects.filter(status=True, estadopuesto=1, pk=69152).exists() else ''
                    return conviert_html_to_pdf(
                        'adm_alternativatitulacion/nomina_examen_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
            except Exception as ex:
                pass
        # ----------------------------ACTA DE CALIFICACION FINAL POR CARRERA-------------------
        elif action == 'actafinal_carrera_pdf':
            try:
                cro = []
                lista = []
                cantaprobado = 0
                cantreprobado = 0
                if 'idg' in request.POST and 'idc' in request.POST:
                    if ComplexivoExamen.objects.filter(status=True, alternativa__grupotitulacion__id=int(request.POST['idg']), alternativa__carrera__id=int(request.POST['idc']), alternativa__aplicapropuesta=False).exists():
                        data['examen'] = ComplexivoExamen.objects.filter(status=True, alternativa__grupotitulacion__id=int(request.POST['idg']), alternativa__carrera__id=int(request.POST['idc']))[0]
                        data['matriculados'] = matriculados = ComplexivoExamenDetalle.objects.filter(estado=3,status=True, examen__alternativa__grupotitulacion__id=int(request.POST['idg']), examen__alternativa__carrera__id=int(request.POST['idc']), examen__alternativa__aplicapropuesta=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                        for i in matriculados:
                            fechpruebateorica = ''
                            estado = ''
                            if i.nota_propuesta():
                                if i.matricula.notafinalcomplexivo() >= i.matricula.alternativa.complexivoexamen_set.filter(status=True)[0].notaminima:
                                    estado = 'A'
                                    cantaprobado += 1
                                else:
                                    estado = 'R'
                                    cantreprobado += 1
                            else:
                                if datetime.now().date() > i.matricula.alternativa.cronogramaexamencomplexivo_set.filter(status=True)[0].fechardefensaevaluacionfin:
                                    estado = 'R'
                                    cantreprobado += 1
                            fechadefensapropuesta = ''
                            if i.matricula.datospropuesta():
                                if i.matricula.datospropuesta().grupo:
                                    if i.matricula.datospropuesta().grupo.fechadefensa:
                                        fechadefensapropuesta = i.matricula.datospropuesta().grupo.fechadefensa.strftime("%d/%m/%Y")
                            if i.matricula.alternativa.get_cronograma():
                                cro = CronogramaExamenComplexivo.objects.filter(alternativatitulacion=i.matricula.alternativa)[0]
                                if cro:
                                    fechpruebateorica = cro.fechaaprobexameninicio.strftime("%d/%m/%Y")
                            lista.append([str(i.matricula.inscripcion.persona.nombre_completo_inverso())
                                          + ' - ' + str(i.matricula.inscripcion.carrera.alias), i.notafinal,
                                          i.nota_propuesta()
                                          if i.nota_propuesta() else 0, i.matricula.notafinalcomplexivo()
                                          if i.matricula.notafinalcomplexivo() else 0, estado, i.matricula.inscripcion.datos_egresado().fechaegreso.strftime("%d/%m/%Y")
                                          if i.matricula.inscripcion.datos_egresado() else '', fechpruebateorica, fechadefensapropuesta, i.matricula.inscripcion.datos_graduado().fechagraduado.strftime("%d/%m/%Y")
                                          if i.matricula.inscripcion.datos_graduado() else '', i.matricula.inscripcion.datos_graduado().fechaactagrado.strftime("%d/%m/%Y") if i.matricula.inscripcion.datos_graduado() else ''])
                        data['lista'] = lista
                        data['cantaprobado'] = cantaprobado
                        data['cantreprobado'] = cantreprobado
                        data['cantestudiantes'] = matriculados.count()
                    fecha = datetime.today().date()
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    data['secretariageneral'] = CargoInstitucion.objects.get(pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                    return conviert_html_to_pdf('adm_alternativatitulacion/actafinalcarrera_pdf.html', {'pagesize': 'A4', 'data': data,})
            except Exception as ex:
                pass
        #-----------------------ACTA DE CALIFICACIONES POR CARRERA----------------------
        elif action == 'actacalificaciones_carrera_pdf':
            try:
                if 'idg' in request.POST and 'idc' in request.POST:
                    matricu =[]
                    if ComplexivoExamen.objects.filter(status=True, alternativa__grupotitulacion__id=int(request.POST['idg']), alternativa__carrera__id=int(request.POST['idc'])).exists():
                        data['examen'] = ComplexivoExamen.objects.filter(status=True, alternativa__grupotitulacion__id=int(request.POST['idg']), alternativa__carrera__id=int(request.POST['idc']))[0]
                        data['matriculados'] = matricu = ComplexivoExamenDetalle.objects.filter(status=True, examen__alternativa__grupotitulacion__id=int(request.POST['idg']), examen__alternativa__carrera__id=int(request.POST['idc'])).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', '-id')
                    lista = []
                    for mat in matricu:
                        if mat.matricula.inscripcion.persona.nombre_completo_inverso not in [x[0] for x in lista]:
                            lista.append([mat.matricula.inscripcion.persona.nombre_completo_inverso,mat])
                    data['xalter'] = False
                    data['listacadena'] = lista
                    fecha = datetime.today().date()
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).capitalize() + " del " + str(fecha.year)
                    data['secretariageneral'] = CargoInstitucion.objects.get(pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                    return conviert_html_to_pdf(
                        'adm_alternativatitulacion/actacalificacion_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
            except Exception as ex:
                pass
        #--------------------------NOMINA DE ESTUDIANTES MATRICULADOS POR CARRERA---------------------------
        elif action == 'nomina_examen_carrera_pdf':
            try:
                if 'idg' in request.POST and 'idc' and 'idt' in request.POST:
                    data['grupotitulacion'] = grupotitulacion = GrupoTitulacion.objects.get(pk=int(request.POST['idg']))
                    data['tipotitulacion'] = tipotitulacion = TipoTitulaciones.objects.get(pk=int(request.POST['idt']))
                    data['carrera'] = carrera = Carrera.objects.get(pk=int(request.POST['idc']))
                    data['matriculados'] = MatriculaTitulacion.objects.filter(status=True, estado__in=[1,9,10], alternativa__grupotitulacion=grupotitulacion, alternativa__tipotitulacion=tipotitulacion, alternativa__carrera=carrera).distinct().order_by('inscripcion')
                    # if ComplexivoExamen.objects.filter(status=True, alternativa__grupotitulacion__id=int(request.POST['idg']), alternativa__carrera__id=int(request.POST['idc'])).exists():
                    #     data['examen'] = ComplexivoExamen.objects.filter(status=True, alternativa__grupotitulacion__id=int(request.POST['idg']), alternativa__carrera__id=int(request.POST['idc']))[0]
                    #     data['matriculados'] = ComplexivoExamenDetalle.objects.filter(status=True, examen__alternativa__grupotitulacion__id=int(request.POST['idg']), examen__alternativa__carrera__id=int(request.POST['idc'])).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    fecha = datetime.today().date()
                    data['xalter'] = False
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    data['responsablegta'] = DistributivoPersona.objects.get(status=True, estadopuesto=1, pk=69152) if DistributivoPersona.objects.filter(status=True, estadopuesto=1, pk=69152).exists() else ''
                    return conviert_html_to_pdf(
                        'adm_alternativatitulacion/nomina_examen_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
            except Exception as ex:
                pass

        #------------------acta de acompañamientos---------------
        elif action == 'actaacompanamiento_pdf':
            try:
                if 'id' in request.POST:
                    data['grupo'] = grupo = ComplexivoGrupoTematica.objects.get(pk=int(request.POST['id']))
                    data['acompanamientos'] = grupo.complexivoacompanamiento_set.filter(status=True, grupo=grupo)
                    data['integrantes'] = grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1)|Q(matricula__estado=10))).exclude(matricula__complexivoexamendetalle__estado=2).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    data['facultad'] = grupo.tematica.carrera.coordinaciones()[0]
                    fecha = datetime.today().date()
                    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
                    data['secretariageneral'] = CargoInstitucion.objects.get(pk=1).persona.nombre_completo_inverso() if CargoInstitucion.objects.get(pk=1) else None
                    return conviert_html_to_pdf('pro_complexivotematica/actaacompanamiento_pdf.html',
                                                {
                                                    'pagesize': 'A4',
                                                    'data': data,
                                                }
                                                )
            except Exception as ex:
                pass

        elif action == 'addpregraduarestudiante':
            try:
                if 'id' in request.POST:
                    alter = AlternativaTitulacion.objects.get(pk=request.POST['id'])
                    # complex = alter.complexivoexamen_set.filter(status=True, aplicaexamen=True)[0]
                    if alter.tipotitulacion.tipo==2:
                        matriculados = alter.matriculatitulacion_set.filter(Q(status=True), (Q(estado=1)| Q(estado=10))).exclude(Q(complexivoexamendetalle__estado=2)| Q(complexivoexamendetalle__estado=1)).order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1','inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    if alter.tipotitulacion.tipo==1:
                        matriculados = alter.matriculatitulacion_set.filter(Q(status=True), (Q(estado=1) | Q(estado=10))).order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    if not alter.aplicapropuesta:
                        matriculados = matriculados.filter(complexivodetallegrupo__grupo__complexivopropuestapractica__estado=2,complexivodetallegrupo__grupo__activo=True)
                    for matricula in matriculados:
                        malla = matricula.inscripcion.malla_inscripcion().malla
                        if matricula.inscripcion.persona.sexo.id == 2:
                            titulo = malla.tituloobtenidohombre
                        else:
                            titulo = malla.tituloobtenidomujer
                        titulo = titulo if titulo else ''
                        decano = None
                        coordinadorcarrera = None
                        if malla.carrera.coordinaciones():
                            decano = malla.carrera.coordinaciones()[0].responsable_periododos(periodo, 1) if  malla.carrera.coordinaciones()[0].responsable_periododos(periodo, 1) else None
                            coordinadorcarrera = matricula.inscripcion.carrera.coordinador(periodo, matricula.inscripcion.coordinacion.sede) if matricula.inscripcion.carrera.coordinador( periodo, matricula.inscripcion.coordinacion.sede) else None
                        tiene_tribunal = False
                        tutor = None
                        if not alter.aplicapropuesta:
                            if matricula.complexivodetallegrupo_set.filter(status=True).exists():
                                detallegrupo = matricula.complexivodetallegrupo_set.filter(status=True)[0]
                                if detallegrupo.tiene_tribunal():
                                    tiene_tribunal = True
                                if Profesor.objects.filter(persona=detallegrupo.grupo.tematica.tutor.participante.persona, status=True, activo=True).exists():
                                    tutor = Profesor.objects.filter(persona=detallegrupo.grupo.tematica.tutor.participante.persona, status=True, activo=True)[0]
                        representante = None
                        if matricula.inscripcion.mi_coordinacion():
                            if matricula.inscripcion.mi_coordinacion().representantesfacultad_set.filter(status=True).exists():
                                representante = matricula.inscripcion.mi_coordinacion().representantesfacultad_set.filter(status=True).order_by('-id')[0]
                        notaegreso = matricula.inscripcion.promedio_record()
                        fecharecord = matricula.inscripcion.recordacademico_set.order_by('-fecha')[0].fecha
                        fecahapractica = None
                        if matricula.inscripcion.practicaspreprofesionalesinscripcion_set.filter(status=True, culminada=True).order_by('-fechahasta').exists():
                            fecahapractica = matricula.inscripcion.practicaspreprofesionalesinscripcion_set.filter(status=True, culminada=True).order_by('-fechahasta')[0].fechahasta
                        fechavinculacion = None
                        if matricula.inscripcion.participantesmatrices_set.filter(status=True, matrizevidencia_id=2, proyecto__status=True).order_by('-id').exists():
                            fechavinculacion =  matricula.inscripcion.participantesmatrices_set.filter(status=True, matrizevidencia_id=2, proyecto__status=True).order_by('-id')[0].fecha_creacion
                        fechaegreso = ''
                        if fecahapractica:
                            if fechavinculacion:
                                if fecharecord:
                                    if fecharecord > fecahapractica:
                                        if fecharecord > fechavinculacion.date():
                                            fechaegreso = fecharecord
                                        else:
                                            fechaegreso = fechavinculacion.date()
                                    elif fecahapractica > fechavinculacion.date():
                                        fechaegreso = fecahapractica
                                    else:
                                        fechaegreso = fechavinculacion.date()
                            else:
                                fechaegreso = fecharecord
                        else:
                            if fechavinculacion:
                                if fecharecord:
                                    if fecharecord > fechavinculacion.date():
                                        fechaegreso = fecharecord
                                    else:
                                        fechaegreso = fechavinculacion.date()
                            else:
                                fechaegreso = fecharecord
                        if not matricula.reprobo_examen_complexivo() or matricula.alternativa.tipotitulacion.tipo==1:
                            if matricula.inscripcion.completo_malla():
                                if not Egresado.objects.filter(inscripcion=matricula.inscripcion).exists():
                                    egresado = Egresado(inscripcion=matricula.inscripcion,
                                                        notaegreso=notaegreso,
                                                        fechaegreso=fechaegreso)
                                else:
                                    egresado = Egresado.objects.get(inscripcion=matricula.inscripcion, status=True)
                                    egresado.notaegreso = notaegreso
                                    egresado.fechaegreso = fechaegreso
                                egresado.save(request)
                                log(u'Adiciono egresado: %s nota: %s' % (egresado, str(egresado.notaegreso)),request, "add")
                                idsecretariageneral = CargoInstitucion.objects.get(pk=1)
                                representanteestudiantil = None
                                representantedocente = None
                                representantesuplentedocente = None
                                representanteservidores = None
                                if representante:
                                    representanteestudiantil = representante.representanteestudiantil if representante.representanteestudiantil else None
                                    representantedocente = representante.representantedocente if representante.representantedocente else None
                                    representantesuplentedocente = representante.representantesuplentedocente if representante.representantesuplentedocente else None
                                    representanteservidores = representante.representanteservidores if representante.representanteservidores else None
                                tema = ''
                                coordinacion = matricula.inscripcion.mi_coordinacion()
                                carreras = coordinacion.carreras().values_list('id')
                                directores = CoordinadorCarrera.objects.filter(status=True, tipo=3)
                                if tiene_tribunal:
                                    if detallegrupo.grupo.subtema:
                                        tema = detallegrupo.grupo.subtema
                                if not Graduado.objects.filter(status=True, inscripcion=matricula.inscripcion).exists():
                                    graduado = Graduado(inscripcion=matricula.inscripcion,
                                                        decano=decano.persona if decano else None,
                                                        notafinal=egresado.notaegreso,
                                                        nombretitulo=titulo,
                                                        horastitulacion=matricula.alternativa.horastotales,
                                                        creditotitulacion=malla.creditos_titulacion,
                                                        creditovinculacion=malla.creditos_vinculacion,
                                                        creditopracticas=malla.creditos_practicas,
                                                        fechagraduado=detallegrupo.grupo.fechadefensa if tiene_tribunal else None,
                                                        horagraduacion=detallegrupo.grupo.horadefensa if tiene_tribunal else None,
                                                        fechaactagrado=detallegrupo.grupo.fechadefensa if tiene_tribunal else None,
                                                        profesor=tutor,
                                                        integrantetribunal=detallegrupo.grupo.delegadopropuesta if tiene_tribunal else None,
                                                        docentesecretario=detallegrupo.grupo.secretariopropuesta if tiene_tribunal else None,
                                                        secretariageneral=idsecretariageneral.persona,
                                                        representanteestudiantil=representanteestudiantil,
                                                        representantedocente=representantedocente,
                                                        representantesuplentedocente=representantesuplentedocente,
                                                        representanteservidores=representanteservidores,
                                                        matriculatitulacion=matricula,
                                                        codigomecanismotitulacion=matricula.alternativa.tipotitulacion.mecanismotitulacion,
                                                        asistentefacultad=persona,
                                                        estadograduado=False,
                                                        docenteevaluador1=matricula.alternativa.docenteevaluador1,
                                                        docenteevaluador2=matricula.alternativa.docenteevaluador2,
                                                        directorcarrera=coordinadorcarrera.persona if coordinadorcarrera else None,
                                                        tematesis=tema)
                                    log(u'Adiciono graduado: %s por el metodo de complexivo de forma masiva por alternativa: %s' % (graduado, matricula.alternativa), request, "add")
                                else:
                                    graduado = Graduado.objects.get(inscripcion=matricula.inscripcion, status=True)
                                    graduado.decano = decano.persona if decano else None
                                    graduado.notafinal = egresado.notaegreso
                                    graduado.nombretitulo = titulo
                                    graduado.horastitulacion = matricula.alternativa.horastotales
                                    graduado.creditotitulacion = malla.creditos_titulacion
                                    graduado.creditovinculacion = malla.creditos_vinculacion
                                    graduado.creditopracticas = malla.creditos_practicas
                                    graduado.fechagraduado = detallegrupo.grupo.fechadefensa if tiene_tribunal else None
                                    graduado.horagraduacion = detallegrupo.grupo.horadefensa if tiene_tribunal else None
                                    graduado.fechaactagrado = detallegrupo.grupo.fechadefensa if tiene_tribunal else None
                                    graduado.profesor = tutor
                                    graduado.integrantetribunal = detallegrupo.grupo.delegadopropuesta if tiene_tribunal else None
                                    graduado.docentesecretario = detallegrupo.grupo.secretariopropuesta if tiene_tribunal else None
                                    graduado.secretariageneral = idsecretariageneral.persona
                                    graduado.representanteestudiantil = representanteestudiantil
                                    graduado.representantedocente = representantedocente
                                    graduado.representantesuplentedocente = representantesuplentedocente
                                    graduado.representanteservidores = representanteservidores
                                    graduado.matriculatitulacion=matricula
                                    graduado.codigomecanismotitulacion = matricula.alternativa.tipotitulacion.mecanismotitulacion
                                    graduado.asistentefacultad = persona
                                    graduado.tematesis = tema
                                    graduado.estadograduado = True if graduado.estadograduado else False
                                    graduado.docenteevaluador1 = matricula.alternativa.docenteevaluador1
                                    graduado.docenteevaluador2 = matricula.alternativa.docenteevaluador2
                                    graduado.directorcarrera=coordinadorcarrera.persona if coordinadorcarrera else None
                                    log(u'Modifico graduado: %s por el metodo de complexivo de forma masiva por alternativa: %s' % (graduado, matricula.alternativa), request, "edit")
                                graduado.save(request)
                                if not graduado.estadograduado:
                                    graduado.notagraduacion = graduado.calcular_notagraduacion()
                                    graduado.save(request)
                                detallepropuesta = None
                                if not matricula.alternativa.aplicapropuesta:
                                    if detallegrupo.grupo.complexivodetallegrupo_set.filter(status=True, estado=1, califico=True, matricula=matricula).exists():
                                        detallepropuesta = detallegrupo.grupo.complexivodetallegrupo_set.filter(status=True, estado=1, califico=True, matricula=matricula)[0]
                                if matricula.alternativa.tipotitulacion.tipo == 2:
                                    item = ItemExamenComplexivo.objects.filter(status=True, pk=1)[0]
                                    detalleexamen = matricula.complexivoexamendetalle_set.filter(status=True, estado=3)[0]
                                    notaexamen = float(detalleexamen.notafinal)
                                    if item.id == 1:
                                        adicionar_nota_complexivo(graduado.id, notaexamen, item, detalleexamen.examen.fechaexamen, request)
                                        if detallepropuesta:
                                            if detallepropuesta.actacerrada or detallepropuesta.matricula.estado == 10:
                                                notapropuesta = float(detallepropuesta.calificacion)
                                                notapro = null_to_numeric(((notaexamen + notapropuesta) / 2), 2)
                                                notafinal = null_to_numeric((notapro), 2)
                                                graduado.promediotitulacion = notafinal
                                                graduado.estadograduado = True
                                                graduado.save(request)
                                                detallepropuesta.actacerrada = True
                                                detallepropuesta.save(request)
                                                itemp = ItemExamenComplexivo.objects.filter(status=True, pk=2)[0]
                                                adicionar_nota_complexivo(graduado.id, notapropuesta, itemp, detallepropuesta.fecha_modificacion.date(), request)
                                else:
                                    if detallepropuesta.actacerrada or detallepropuesta.matricula.estado == 10:
                                        notapro = null_to_numeric((float(detallepropuesta.calificacion)), 2)
                                        notafinal = null_to_numeric((notapro), 2)
                                        graduado.promediotitulacion = notafinal
                                        graduado.estadograduado = True
                                        graduado.notagraduacion = graduado.calcular_notagraduacion()
                                        graduado.save(request)
                                        detallepropuesta.actacerrada = True
                                        detallepropuesta.save(request)
                                if graduado.calcular_notagraduacion():
                                    graduado.notagraduacion = graduado.calcular_notagraduacion()
                                    graduado.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addpregraduarestudianteind':
            try:
                if 'id' in request.POST:
                    matriculado = MatriculaTitulacion.objects.get(id=int(request.POST['id']))
                    matriculado.gradua_pregrado(periodo, persona, request)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, %s" % ex})

        elif action == 'addnota':
            try:
                if 'id' in request.POST and 'nota' in request.POST:
                    matricula = MatriculaTitulacion.objects.get(pk=request.POST['id'])
                    detalleexamen = matricula.complexivoexamendetalle_set.filter(status=True, estado=3)[0]
                    notaexamen = float(detalleexamen.notafinal)
                    matricula.nota = float(request.POST['nota'])
                    matricula.save(request)
                    graduado = Graduado.objects.get(inscripcion=matricula.inscripcion, status=True)
                    notapro = null_to_numeric(((notaexamen + matricula.nota) / 2), 4)
                    notafinal = null_to_numeric((notapro), 2)
                    graduado.promediotitulacion = notafinal
                    graduado.docenteevaluador1 = matricula.alternativa.docenteevaluador1
                    graduado.docenteevaluador2 = matricula.alternativa.docenteevaluador2
                    graduado.estadograduado = True
                    graduado.save(request)
                    if notafinal >= 70:
                        matricula.estado = 10
                        matricula.save(request)
                    else:
                        matricula.estado = 9
                        matricula.save(request)
                    item = ItemExamenComplexivo.objects.filter(status=True, pk=3)[0]
                    adicionar_nota_complexivo(graduado.id, float(request.POST['nota']), item, matricula.alternativa.fechanoaplicapropuesta, request)
                    log(u'Adicionó la nota de %s al estudiante %s de la carrera %s,  proceso de titulacion %s - %s' % (matricula.nota, matricula, matricula.alternativa.carrera, matricula.alternativa, matricula.alternativa.paralelo), request, "add")
                    return JsonResponse({"result": "ok", "id":matricula.id, "nota":matricula.nota})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar nota."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'modelo_estado':
            try:
                modelo = ModeloTitulacion.objects.get(pk=request.POST['id'])
                if modelo.activo:
                    return JsonResponse({"result": "ok", "activo":"no"})
                return JsonResponse({"result": "ok", "activo":"si"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al verificar los datos."})

        elif action == 'activardesactivarmodelo':
            try:
                modelo = ModeloTitulacion.objects.get(pk=request.POST['id'])
                if modelo.activo:
                    modelo.activo = False
                else:
                    modelo.activo = True
                modelo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar en modelo."})

        elif action == 'cambiaralternativa':
            try:
                matriculado = MatriculaTitulacion.objects.get(pk=request.POST['codimatriculado'])
                matriculado.alternativa_id=request.POST['codialter']
                matriculado.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar alternativa."})

        elif action == 'extraer_creditos':
            try:
                if 'id' in request.POST:
                    malla = Malla.objects.get(id=int(request.POST['id']))
                    return JsonResponse({"results": "ok", "creditos": malla.creditos_titulacion, "totalhora": malla.horas_titulacion})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al extraer los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar en modelo."})

        elif action == 'cronograma_masivo':
            try:
                if 'idg' in request.POST and 'idt' in request.POST:
                    grupo = GrupoTitulacion.objects.get(pk=request.POST['idg'], status=True)
                    alternativas = grupo.alternativatitulacion_set.filter(status=True, tipotitulacion_id=int(request.POST['idt']))
                    for alter in alternativas:
                        if alter.cronogramaexamencomplexivo_set.filter(status=True).exists():
                            crono = alter.cronogramaexamencomplexivo_set.filter(status=True)[0]
                            crono.fechanucleobasicoinicio = convertir_fecha(request.POST['id_fechanucleobasicoinicio'])
                            crono.fechanucleoproffin = convertir_fecha(request.POST['id_fechanucleoproffin'])
                            crono.fechaaprobexameninicio = convertir_fecha(request.POST['id_fechaaprobexameninicio']) if alter.tipotitulacion.tipo == 2 else None
                            crono.fechaaprobexamenfin = convertir_fecha(request.POST['id_fechaaprobexamenfin']) if alter.tipotitulacion.tipo == 2 else None
                            crono.fechasubircalificacionesinicio = convertir_fecha(request.POST['id_fechasubircalificacionesinicio']) if alter.tipotitulacion.tipo == 2 else None
                            crono.fechasubircalificacionesfin = convertir_fecha(request.POST['id_fechasubircalificacionesfin']) if alter.tipotitulacion.tipo == 2 else None
                            crono.fechaeleccionpropuestainicio = convertir_fecha(request.POST['id_fechaeleccionpropuestainicio'])
                            crono.fechaeleccionpropuestafin = convertir_fecha(request.POST['id_fechaeleccionpropuestafin'])
                            crono.fechapropuestainicio = convertir_fecha(request.POST['id_fechapropuestainicio'])
                            crono.fechapropuestafin = convertir_fecha(request.POST['id_fechapropuestafin'])
                            crono.fechardefensaevaluacioninicio = convertir_fecha(request.POST['id_fechadefensaevaluacioninicio'])
                            crono.fechardefensaevaluacionfin = convertir_fecha(request.POST['id_fechadefensaevaluacionfin'])
                            log(u'Adicionó nuevo cronograma de forma masiva %s a la alternativa de titulación %s,  del grupo %s' % (str(crono), crono.alternativatitulacion, grupo), request, "add")
                        else:
                            crono = CronogramaExamenComplexivo(alternativatitulacion=alter,
                                                               fechanucleobasicoinicio=convertir_fecha(request.POST['id_fechanucleobasicoinicio']),
                                                               fechanucleoproffin=convertir_fecha(request.POST['id_fechanucleoproffin']),
                                                               fechaaprobexameninicio=convertir_fecha(request.POST['id_fechaaprobexameninicio']) if alter.tipotitulacion.tipo==2 else None,
                                                               fechaaprobexamenfin=convertir_fecha(request.POST['id_fechaaprobexamenfin']) if alter.tipotitulacion.tipo==2 else None,
                                                               fechasubircalificacionesinicio=convertir_fecha(request.POST['id_fechasubircalificacionesinicio']) if alter.tipotitulacion.tipo==2 else None,
                                                               fechasubircalificacionesfin=convertir_fecha(request.POST['id_fechasubircalificacionesfin']) if alter.tipotitulacion.tipo==2 else None,
                                                               fechaeleccionpropuestainicio=convertir_fecha(request.POST['id_fechaeleccionpropuestainicio']),
                                                               fechaeleccionpropuestafin=convertir_fecha(request.POST['id_fechaeleccionpropuestafin']),
                                                               fechapropuestainicio=convertir_fecha(request.POST['id_fechapropuestainicio']),
                                                               fechapropuestafin=convertir_fecha(request.POST['id_fechapropuestafin']),
                                                               fechardefensaevaluacioninicio=convertir_fecha(request.POST['id_fechadefensaevaluacioninicio']),
                                                               fechardefensaevaluacionfin=convertir_fecha(request.POST['id_fechadefensaevaluacionfin']))
                            log(u'Adicionó nuevo cronograma de forma masiva %s a la alternativa de titulación %s,  del grupo %s' % (str(crono), crono.alternativatitulacion, grupo), request, "add")
                        crono.save(request)
                        if 'lista_items2' in request.POST:
                            listarevision = json.loads(request.POST['lista_items2'])
                        if listarevision:
                            if crono.detallerevisioncronograma_set.all().exists():
                                detalle = crono.detallerevisioncronograma_set.all()
                                detalle.delete()
                            for revision in listarevision:
                                detalle = DetalleRevisionCronograma(cronograma=crono, fechainicio=convertir_fecha(revision['sinicio']), fechafin=convertir_fecha(revision['sfin']), calificacioninicio=convertir_fecha(revision['rinicio']), calificacionfin=convertir_fecha(revision['rfin']))
                                detalle.save(request)
                    return JsonResponse({"result": "ok", "idg":grupo.id, "idc":alternativas[0].carrera.id, "idt":int(request.POST['idt'])})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el cronograma."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar en modelo."})

        elif action == 'addcronogramaadicional':
            try:
                if 'resolucion' in request.FILES:
                    arch = request.FILES['resolucion']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                    newfile = request.FILES['resolucion']
                    newfile._name = generar_nombre("resolucion_", newfile._name)
                    form = CronogramaAdicionalExamenComplexivoForm(request.POST, request.FILES)
                    if form.is_valid():
                        cro = CronogramaAdicionalExamenComplexivo(cronograma_id=int(request.POST['id']),
                                                                  fechainicioexamen=form.cleaned_data['fechainicioexamen'],
                                                                  fechafinexamen=form.cleaned_data['fechafinexamen'],
                                                                  fechainiciocalificacion=form.cleaned_data['fechainiciocalificacion'],
                                                                  fechafincalificacion=form.cleaned_data['fechafincalificacion'],
                                                                  observacion=form.cleaned_data['observacion'],
                                                                  resolucion=newfile)
                        cro.save(request)
                        log(u'Adicionó cronograma adicional para tomar otra prueba teorica para la alternativa %s' % cro.cronograma.alternativatitulacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar la resolución."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcronogramaadicional':
            try:
                newfile = None
                if 'resolucion' in request.FILES:
                    arch = request.FILES['resolucion']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                    newfile = request.FILES['resolucion']
                    newfile._name = generar_nombre("resolucion_", newfile._name)
                form = CronogramaAdicionalExamenComplexivoForm(request.POST, request.FILES)
                if form.is_valid():
                    cro = CronogramaAdicionalExamenComplexivo.objects.get(id=int(request.POST['id']))
                    cro.fechainicioexamen=form.cleaned_data['fechainicioexamen']
                    cro.fechafinexamen=form.cleaned_data['fechafinexamen']
                    cro.fechainiciocalificacion=form.cleaned_data['fechainiciocalificacion']
                    cro.fechafincalificacion=form.cleaned_data['fechafincalificacion']
                    cro.observacion=form.cleaned_data['observacion']
                    if newfile:
                        cro.resolucion=newfile
                    cro.save(request)
                    log(u'Edito cronograma adicional para tomar otra prueba teorica para la alternativa %s' % cro.cronograma.alternativatitulacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addexamenadicional':
            try:
                newfile = None
                f = ComplexivoExamenForm(request.POST)
                if f.is_valid():
                    exa = f.cleaned_data['fechaexamen']
                    if int(request.POST['profesor']) <= 0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"Ingrese un Profesor"})
                    if int(f.cleaned_data['notaminima']) <= 0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"la nota minima debe ser mayor a 0"})
                    cro = CronogramaAdicionalExamenComplexivo.objects.get(id=int(request.POST['id']), cronograma__alternativatitulacion=request.POST['ida'], activo=True)
                    # if exa < cro.fechainicioexamen or exa > cro.fechafinexamen:
                    #     return JsonResponse({'result': 'bad', 'mensaje': u"Fechas no esta dentro del rango del cronograma adicional"})
                    for exa in ComplexivoExamen.objects.filter(alternativa_id=request.POST['ida'], status=True):
                        exa.aplicaexamen = False
                        exa.save()
                    examenultimo = ComplexivoExamen.objects.filter(status=True, alternativa__id=request.POST['ida']).order_by('-id')[0]
                    examen = ComplexivoExamen(alternativa_id=request.POST['ida'],
                                              cronogramaadicional=cro,
                                              aula=f.cleaned_data['aula'],
                                              fechaexamen=f.cleaned_data['fechaexamen'],
                                              docente_id=int(request.POST['profesor']),
                                              notaminima=f.cleaned_data['notaminima'],
                                              horainicio=f.cleaned_data['horainicio'],
                                              horafin=f.cleaned_data['horafin'],
                                              examenadicional=True)
                    examen.save(request)

                    matriculados = examenultimo.alternativa.matriculatitulacion_set.filter(estado=9)
                    for matriculado in matriculados:
                        for det in ComplexivoExamenDetalle.objects.filter(status=True, matricula=matriculado):
                            det.examenaplica=False
                            det.save(request)
                            log(u"El examen se desactiva por un examne adicional: %s" % examen, request, "desact")
                        detalle = ComplexivoExamenDetalle(examen=examen, matricula=matriculado)
                        detalle.save(request)
                        log(u"Adiciono un nuevo examen: %s" % examen, request, "add")
                    log(u"Adicionó un examen adicional para la alternativa de titulación: %s" % examen, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al falta la resolución los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editexamenadicional':
            try:
                newfile = None
                f = ComplexivoExamenForm(request.POST)
                if f.is_valid():
                    exa = f.cleaned_data['fechaexamen']
                    if int(request.POST['profesor']) <= 0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"Ingrese un Profesor"})
                    if int(f.cleaned_data['notaminima']) <= 0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"la nota minima debe ser mayor a 0"})
                    cro = CronogramaAdicionalExamenComplexivo.objects.get(cronograma__alternativatitulacion=request.POST['ida'], activo=True)
                    if exa < cro.fechainicioexamen or exa > cro.fechafinexamen:
                        return JsonResponse({'result': 'bad', 'mensaje': u"Fechas no esta dentro del rango del cronograma adicional"})
                    for exa in ComplexivoExamen.objects.filter(alternativa_id=request.POST['ida'], status=True).exclude(id=int(request.POST['id'])):
                        exa.aplicaexamen = False
                        exa.save()
                    examen = ComplexivoExamen.objects.get(pk=int(request.POST['id']), alternativa_id=int(request.POST['ida']))
                    examen.aula=f.cleaned_data['aula']
                    examen.fechaexamen=f.cleaned_data['fechaexamen']
                    examen.docente_id=int(request.POST['profesor'])
                    examen.notaminima=f.cleaned_data['notaminima']
                    examen.horainicio=f.cleaned_data['horainicio']
                    examen.horafin=f.cleaned_data['horafin']
                    examen.save(request)
                    matriculados = examen.alternativa.matriculatitulacion_set.filter(estado=9).exclude(pk=examen.id)
                    for matriculado in matriculados:
                        for det in ComplexivoExamenDetalle.objects.filter(status=True, matricula=matriculado, examenaplica=True).exclude(examen=examen):
                            det.examenaplica=False
                            det.save(request)
                            log(u"El examen se desactiva por un examne adicional: %s" % examen, request, "desact")
                        if not ComplexivoExamenDetalle.objects.filter(examen=examen, matricula=matriculado).exists():
                            detalle = ComplexivoExamenDetalle(examen=examen, matricula=matriculado)
                            detalle.save(request)
                            log(u"Adiciono un nuevo examen: %s" % examen, request, "add")
                    log(u"Editó el examen adicional para la alternativa de titulación: %s" % examen, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al falta la resolución los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcronogramaadicional':
            try:
                if 'id' in request.POST:
                    cro = CronogramaAdicionalExamenComplexivo.objects.get(pk=int(request.POST['id']))
                    log(u'Elimino el cronograma adicional para tomar otra prueba teorica para la alternativa %s' % cro.cronograma.alternativatitulacion, request, "add")
                    cro.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verificarfechaexamen':
            try:
                if 'id' in request.POST and 'fecha' in request.POST:
                    cro = CronogramaExamenComplexivo.objects.get(pk=int(request.POST['id']))
                    if convertir_fecha(request.POST['fecha'])>cro.fechaaprobexameninicio:
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", 'fecha':cro.fechaaprobexameninicio+timedelta(days=1), "mensaje": u"La fecha debe ser mayor a la fecha de fin del examen anterior ."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'tituladosevaluar':
            try:
                # profesores = []
                periodogrupo = PeriodoGrupoTitulacion.objects.get(pk=int(request.POST['periodogrupoid']))
                titulados = MatriculaTitulacion.objects.values('id','inscripcion__persona_id','inscripcion__persona__apellido1','inscripcion__persona__apellido2','inscripcion__persona__nombres').filter(alternativa__grupotitulacion__periodogrupo=periodogrupo, cumplerequisitos__in=[1,3], status=True).exclude(inscripcion__graduado__status=True, inscripcion__graduado__estadograduado=True).order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2','inscripcion__persona__nombres')
                return JsonResponse({"result": "ok", "cantidad": len(titulados), "tutilados": list(titulados)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'recalculartituladosvalidar':
            try:
                matriculatitulacion = MatriculaTitulacion.objects.get(pk=request.POST['idmatriculatitulado'])
                alter = AlternativaTitulacion.objects.get(pk=matriculatitulacion.alternativa_id)
                data = valida_matriculatitulacion_requisitos(data, alter, matriculatitulacion.inscripcion, matriculatitulacion)
                if data:
                    # if matriculatitulacion.inscripcion.id == 27804:
                    if not Egresado.objects.filter(inscripcion=matriculatitulacion.inscripcion, status=True).exists():
                        if matriculatitulacion.inscripcion.recordacademico_set.exists():
                            fechaegreso = matriculatitulacion.inscripcion.recordacademico_set.order_by('-fecha')[0].fecha
                        else:
                            fechaegreso = datetime.now().date()

                        egresado = Egresado(inscripcion=matriculatitulacion.inscripcion,
                                            notaegreso=matriculatitulacion.inscripcion.promedio_record(),
                                            fechaegreso=fechaegreso)
                        egresado.save(request)
                    else:
                        egresado = Egresado.objects.get(inscripcion=matriculatitulacion.inscripcion, status=True)
                        egresado.notaegreso = matriculatitulacion.inscripcion.promedio_record()
                        egresado.save()
                    if not Graduado.objects.filter(inscripcion=matriculatitulacion.inscripcion, status=True).exists():
                        graduado = Graduado(inscripcion=matriculatitulacion.inscripcion,
                                            notafinal=egresado.notaegreso)
                        graduado.save(request)
                    else:
                        graduado = Graduado.objects.get(inscripcion=matriculatitulacion.inscripcion, notafinal=egresado.notaegreso, status=True)
                        graduado.save(request)


                    matriculatitulacion.cumplerequisitos = 2
                    matriculatitulacion.fechavalidacumplerequisitos = datetime.now().date()
                    matriculatitulacion.horavalidacumplerequisitos = datetime.now().time()
                    matriculatitulacion.save()
                else:
                    matriculatitulacion.cumplerequisitos = 3
                    matriculatitulacion.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                messages.error(request, str(ex))
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addrubrica':
            try:
                form = RubricaTitulacionCabForm(request.POST)
                if form.is_valid():
                    nombre=form.cleaned_data['nombre']
                    if not RubricaTitulacionCab.objects.filter(nombre=nombre, status=True).exists():
                        rubrica=RubricaTitulacionCab(nombre=form.cleaned_data['nombre'],
                                                     activa=form.cleaned_data['activa'])
                        rubrica.save(request)
                        if 'lista_items4' in request.POST:
                            listadomodelo = json.loads(request.POST['lista_items4'])
                            if listadomodelo:
                                numeroorden=0
                                for lmodelo in listadomodelo:
                                    numeroorden = numeroorden + 1
                                    modelorubrica = ModeloRubricaTitulacion(rubrica=rubrica,
                                                                            orden=numeroorden,
                                                                            nombre=lmodelo['detallenombre'],
                                                                            puntaje=lmodelo['listapuntaje'])
                                    modelorubrica.save(request)
                        log(u'Agrego rubrica titulación: %s' % rubrica, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrubrica':
            try:
                rubrica = RubricaTitulacionCab.objects.get(pk=int(request.POST['id']))
                form = RubricaTitulacionCabForm(request.POST)
                if form.is_valid():
                    rubrica.nombre = form.cleaned_data['nombre']
                    rubrica.activa = form.cleaned_data['activa']
                    rubrica.save(request)
                    log(u'Editó rúbrica de titulación: %s' % rubrica, request, "editar")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addmodelorubrica':
            try:
                rubrica = int(encrypt(request.POST['id']))
                numeroorden=0
                if ModeloRubricaTitulacion.objects.filter(rubrica_id=rubrica, status=True):
                    ordenmodelorubrica = ModeloRubricaTitulacion.objects.filter(rubrica_id=rubrica, status=True).order_by('-orden')[0]
                    numeroorden = ordenmodelorubrica.orden + 1
                else:
                    numeroorden=1
                modelorubrica=ModeloRubricaTitulacion(rubrica_id=rubrica, orden=numeroorden)
                modelorubrica.save(request)
                log(u'Agrego modelo rubrica titulación: %s' % modelorubrica, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delmodelorubrica':
            try:
                modelorubrica=ModeloRubricaTitulacion.objects.get(pk=request.POST['id'])
                log(u'Eliminó modelo rubrica titulación: %s' % modelorubrica, request, "del")
                modelorubrica.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delponderacionrubrica':
            try:
                prubonderacion=RubricaTitulacionCabPonderacion.objects.get(pk=request.POST['id'])
                log(u'Eliminó ponderacion rubrica titulación: %s' % prubonderacion, request, "del")
                prubonderacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddetallerubrica':
            try:
                rubrica = RubricaTitulacionCab.objects.get(pk=int(encrypt(request.POST['id'])))
                numeroorden = 0
                if RubricaTitulacion.objects.filter(rubrica=rubrica, status=True):
                    ordenrubicatitulacion = RubricaTitulacion.objects.filter(rubrica=rubrica, status=True).order_by('-orden')[0]
                    numeroorden = ordenrubicatitulacion.orden + 1
                else:
                    numeroorden = 1
                listadoabecedario = [
                    [0, '-'],[1, 'A'], [2, 'B'], [3, 'C'], [4, 'D'], [5, 'E'], [6, 'F'],
                    [7, 'G'], [8, 'H'], [9, 'I'], [10, 'J'], [11, 'K'], [12, 'L'], [13, 'M'], [14, 'N'],
                    [15, 'O'], [16, 'P'], [17, 'Q'], [18, 'R'], [19, 'S'], [20, 'T'], [21, 'U'], [22, 'V']
                ]
                detallerubrica=RubricaTitulacion(rubrica=rubrica,orden=numeroorden, letra=listadoabecedario[numeroorden][1])
                detallerubrica.save(request)
                listadorubricaponderacion = rubrica.rubricatitulacioncabponderacion_set.filter(activa=True, status=True)
                for idponde in listadorubricaponderacion:
                    rubricaponderacion = RubricaTitulacionPonderacion(detallerubrica=detallerubrica,
                                                                      ponderacionrubrica=idponde)
                    rubricaponderacion.save()
                log(u'Agrego detalle rubrica titulación: %s' % detallerubrica, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addnivelrubrica':
            try:
                listaitemdetalle = json.loads(request.POST['listaitemdetalle'])
                for iditem in listaitemdetalle:
                    ponderacion = RubricaTitulacionPonderacion(detallerubrica_id=iditem)
                    ponderacion.save(request)
                log(u'Agrego ponderación detalle rubrica titulación: %s' % ponderacion, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editdetallerubrica':
            try:
                detrubrica = RubricaTitulacion.objects.get(pk=int(request.POST['id']))
                form = RubricaTitulacionForm(request.POST)
                if form.is_valid():
                    detrubrica.letra = form.cleaned_data['letra']
                    detrubrica.nombre = form.cleaned_data['nombre']
                    detrubrica.leyendaexcelente = form.cleaned_data['leyendaexcelente']
                    detrubrica.excelente = form.cleaned_data['excelente']
                    detrubrica.leyendamuybueno = form.cleaned_data['leyendamuybueno']
                    detrubrica.muybueno = form.cleaned_data['muybueno']
                    detrubrica.leyendabueno = form.cleaned_data['leyendabueno']
                    detrubrica.bueno = form.cleaned_data['bueno']
                    detrubrica.leyendasuficiente = form.cleaned_data['leyendasuficiente']
                    detrubrica.suficiente = form.cleaned_data['suficiente']
                    detrubrica.puntaje = form.cleaned_data['puntaje']
                    detrubrica.tipotitulacion = form.cleaned_data['tipotitulacion']
                    detrubrica.save(request)
                    log(u'Editó detalle de rúbrica de titulación: %s' % detrubrica, request, "editar")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleterubrica':
            try:
                rubrica = RubricaTitulacionCab.objects.get(pk=request.POST['idrubrica'])
                rubrica.delete()
                log(u'Eliminó rubrica titulación: %s - %s' % (rubrica, rubrica.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'deletedetallerubrica':
            try:
                detallerubrica = RubricaTitulacion.objects.get(pk=request.POST['iddetalle'])
                detallerubrica.delete()
                log(u'Eliminó detalle rubrica titulación: %s - %s' % (detallerubrica, detallerubrica.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'actualizadetallerubricamodelo':
            try:
                detallerubrica = RubricaTitulacionPonderacion.objects.get(pk=request.POST['iddetalle'])
                tipo=int(request.POST['tipo'])
                valortexto=request.POST['valortexto']
                if tipo == 1:
                    detallerubrica.descripción=valortexto
                if tipo == 2:
                    detallerubrica.leyenda = valortexto
                detallerubrica.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'actualizamoddetallerubrica':
            try:
                rubrica = RubricaTitulacionCab.objects.get(pk=request.POST['idrubrica'])
                id_modrubrica = request.POST['id_modrubrica']
                numeroorden = 0
                if RubricaTitulacionCabPonderacion.objects.filter(rubrica=rubrica,status=True):
                    ordenponderacion = RubricaTitulacionCabPonderacion.objects.filter(rubrica=rubrica, status=True).order_by('-orden')[0]
                    numeroorden = ordenponderacion.orden + 1
                else:
                    numeroorden = 1
                rubricaponderacion = RubricaTitulacionCabPonderacion(rubrica=rubrica,
                                                                     orden=numeroorden,
                                                                     ponderacion_id=id_modrubrica)
                rubricaponderacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'actualizadetallerubrica':
            try:
                detallerubrica = RubricaTitulacion.objects.get(pk=request.POST['iddetalle'])
                tipo=int(request.POST['tipo'])
                valortexto=request.POST['valortexto']
                if tipo == 1:
                    detallerubrica.puntaje=valortexto
                if tipo == 2:
                    detallerubrica.nombre = valortexto
                if tipo == 3:
                    detallerubrica.letra = valortexto
                if tipo == 4:
                    detallerubrica.modelorubrica_id = int(valortexto)
                if tipo == 5:
                    detallerubrica.orden = int(valortexto)
                detallerubrica.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})


        elif action == 'actualizamodelorubrica':
            try:
                modelorubrica = ModeloRubricaTitulacion.objects.get(pk=request.POST['iddetalle'])
                opc=int(request.POST['opc'])
                if opc==1:
                    valortexto=request.POST['valortexto']
                    modelorubrica.nombre=valortexto
                if opc==2:
                    valortexto=request.POST['valortexto']
                    modelorubrica.puntaje=valortexto
                if opc == 3:
                    valortexto = request.POST['valortexto']
                    modelorubrica.orden = valortexto
                if opc == 4:
                    valortexto = (request.POST['valortexto']).replace('#','')
                    modelorubrica.color = valortexto
                modelorubrica.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'actualizaponderacionrubrica':
            try:
                ponderacionrubrica = RubricaTitulacionCabPonderacion.objects.get(pk=request.POST['iddetalle'])
                valortexto = request.POST['valortexto']
                ponderacionrubrica.orden = valortexto
                ponderacionrubrica.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar."})

        elif action == 'addponderacionmodal':
            try:
                with transaction.atomic():
                    form = PonderacionRubricaForm(request.POST)
                    if form.is_valid():
                        categoria = PonderacionRubrica(nombre=form.cleaned_data['nombre'].upper())
                        categoria.save(request)
                        log(u'Adiciono Ponderación de Rubricas: %s' % categoria, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."},
                                            safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editponderacionmodal':
            try:
                with transaction.atomic():
                    filtro = PonderacionRubrica.objects.get(pk=request.POST['id'])
                    f = PonderacionRubricaForm(request.POST)
                    if f.is_valid():
                        filtro.nombre = f.cleaned_data['nombre'].upper()
                        filtro.save(request)
                        log(u'Modificó Ponderación de Rubricas: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."},
                                            safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deleteponderacion':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    filtro = PonderacionRubrica.objects.get(pk=id)
                    filtro.status = False
                    filtro.save(request)
                    log(u'Eliminar registro de evidencia: %s' % filtro, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'exportarinscritos':
            try:
                idmateria = request.POST['idmateria']
                materia = Materia.objects.get(pk=idmateria)
                lista = request.POST['lista'].split(',')
                if periodo.clasificacion == 1:
                    for elemento in lista:
                        if not Matricula.objects.filter(status=True, inscripcion_id=elemento,
                                                        nivel__periodo=periodo).exists():
                            matricula = Matricula(inscripcion_id=elemento,
                                                  nivel=materia.nivel,
                                                  pago=False,
                                                  iece=False,
                                                  becado=False,
                                                  porcientobeca=0,
                                                  estado_matricula=2,
                                                  fecha=datetime.now().date(),
                                                  hora=datetime.now().time(),
                                                  fechatope=datetime.now().date(),
                                                  termino=True,
                                                  fechatermino=datetime.now()
                                                  )
                            matricula.save()
                        else:
                            matricula = \
                                Matricula.objects.filter(status=True, inscripcion_id=elemento, nivel__periodo=periodo)[
                                    0]
                        if not MateriaAsignada.objects.filter(matricula=matricula, materia=materia, status=True):
                            mateasignada = MateriaAsignada(matricula=matricula,
                                                           materia=materia,
                                                           estado_id=3)
                            mateasignada.save(request)
                            matetitulacion = MateriaTitulacion(materiaasignada=mateasignada,
                                                               rezagados=True)
                            matetitulacion.save(request)

                else:
                    for elemento in lista:
                        if not Matricula.objects.filter(status=True, inscripcion_id=elemento, nivel=materia.nivel).exists():
                            if not Matricula.objects.filter(status=True, inscripcion_id=elemento, nivel__periodo=periodo).exists():
                                matricula = Matricula(inscripcion_id=elemento,
                                                      nivel=materia.nivel,
                                                      pago=False,
                                                      iece=False,
                                                      becado=False,
                                                      porcientobeca=0,
                                                      estado_matricula=2,
                                                      fecha=datetime.now().date(),
                                                      hora=datetime.now().time(),
                                                      fechatope=datetime.now().date(),
                                                      termino=True,
                                                      fechatermino=datetime.now()
                                                      )
                                matricula.save()
                            else:
                                matricula = Matricula.objects.filter(status=True, inscripcion_id=elemento, nivel__periodo=periodo)[0]
                            if not MateriaAsignada.objects.filter(matricula=matricula, materia=materia, status=True):
                                mateasignada = MateriaAsignada(matricula=matricula,
                                                               materia=materia,
                                                               estado_id=3)
                                mateasignada.save(request)
                                matetitulacion = MateriaTitulacion(materiaasignada=mateasignada,
                                                                   rezagados=True)
                                matetitulacion.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'graduarlistadomasivo':
            try:
                lista = request.POST['lista'].split(',')
                fgraduacion = request.POST['fgraduacion']
                factagrado = request.POST['factagrado']
                fconsejo = request.POST['fconsejo']
                for elemento in lista:
                    asignado = MateriaTitulacion.objects.get(pk=elemento)
                    malla = asignado.materiaasignada.matricula.inscripcion.malla_inscripcion().malla
                    periodo = asignado.materiaasignada.materia.nivel.periodo

                    if not asignado.materiaasignada.matricula.inscripcion.graduado_set.filter(status=True):
                        graduado = Graduado(inscripcion=asignado.materiaasignada.matricula.inscripcion,
                                            materiatitulacion=asignado,
                                            decano=None,
                                            notafinal=0,
                                            nombretitulo='',
                                            horastitulacion=malla.horas_titulacion,
                                            creditotitulacion=malla.creditos_titulacion,
                                            creditovinculacion=malla.creditos_vinculacion,
                                            creditopracticas=malla.creditos_practicas,
                                            fechagraduado=None,
                                            horagraduacion=None,
                                            fechaactagrado=None,
                                            profesor=None,
                                            integrantetribunal=None,
                                            docentesecretario=None,
                                            secretariageneral=None,
                                            representanteestudiantil=None,
                                            representantedocente=None,
                                            representantesuplentedocente=None,
                                            representanteservidores=None,
                                            matriculatitulacion=None,
                                            codigomecanismotitulacion_id=22,
                                            asistentefacultad=None,
                                            estadograduado=False,
                                            docenteevaluador1=None,
                                            docenteevaluador2=None,
                                            directorcarrera=None,
                                            tematesis=asignado.materiaasignada.materia.asignaturamalla.asignatura.nombre)
                        graduado.save()
                    if asignado.materiaasignada.matricula.inscripcion.graduado_set.filter(status=True):
                        graduado = Graduado.objects.get(inscripcion=asignado.materiaasignada.matricula.inscripcion, status=True)
                        graduado.materiatitulacion = asignado
                        graduado.tematesis = asignado.materiaasignada.materia.asignaturamalla.asignatura.nombre
                        directorcarrera=CoordinadorCarrera.objects.filter(carrera=malla.carrera,tipo=3,periodo=periodo,status=True)
                        # notafinal = null_to_numeric(((asignado.materiaasignada.notafinal + asignado.materiaasignada.matricula.inscripcion.promedio_record() ) / 2), 2)
                        notafinal = null_to_numeric(((asignado.notafinal + asignado.materiaasignada.matricula.inscripcion.promedio_record() ) / 2), 2)
                        graduado.notafinal = asignado.materiaasignada.matricula.inscripcion.promedio_record()
                        # graduado.promediotitulacion = asignado.materiaasignada.notafinal
                        graduado.promediotitulacion = asignado.notafinal
                        graduado.notagraduacion = notafinal
                        graduado.estadograduado = True
                        graduado.materiatitulacion = asignado
                        graduado.periodo = periodo
                        graduado.fechagraduado = fgraduacion
                        graduado.fechaactagrado = factagrado
                        graduado.fechaconsejo = fconsejo

                        malla = graduado.inscripcion.mi_malla()
                        if graduado.inscripcion.persona.sexo:
                            if graduado.inscripcion.persona.sexo.id == 1:
                                nombretitulo = malla.tituloobtenidomujer
                            else:
                                nombretitulo = malla.tituloobtenidohombre
                            graduado.nombretitulo = nombretitulo

                        if directorcarrera:
                            graduado.directoresfacultad.add(directorcarrera[0].persona)
                        directores = ResponsableCoordinacion.objects.filter(periodo=periodo,coordinacion=asignado.materiaasignada.matricula.inscripcion.coordinacion,status=True)
                        if directores:
                            graduado.decano = directores[0].persona

                        graduado.save(request)

                    asignado.numeromemogradua = request.POST['id_memo']
                    asignado.estadograduado = True
                    asignado.save(request)
                    if not asignado.materiaasignada.matricula.inscripcion.egresado_set.filter(status=True):
                        egresado = Egresado(inscripcion=asignado.materiaasignada.matricula.inscripcion,
                                            notaegreso=graduado.notafinal,
                                            fechaegreso = periodo.fin)
                        egresado.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verdetallerequisitos':
            try:
                asignada = MateriaAsignada.objects.get(pk=request.POST['idasignada'])
                htmlrequisitos = listadovalidarequisitos(asignada.matricula.inscripcion, asignada.materia, True)
                return htmlrequisitos
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verfaltantesfirmar':
            try:
                asignada = MateriaTitulacion.objects.get(pk=request.POST['idasignada'])
                htmlrequisitos = listadofaltantefirmaracta(asignada)
                return htmlrequisitos
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'carrerascoordinacion':
            try:
                lista = []
                id_carreras = MateriaTitulacion.objects.values_list('materiaasignada__materia__asignaturamalla__malla__carrera__id', flat=True).filter(materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id=request.POST['id_coordinacion'], materiaasignada__materia__nivel__periodo=periodo, status=True).distinct()
                carreras = Carrera.objects.filter(pk__in=id_carreras)
                for carrera in carreras:
                    lista.append([carrera.id, carrera.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'imprimeexcel':
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
                ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                response = HttpResponse(content_type="application/ms-excel")
                response[
                    'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"N", 2500),
                    (u"FACULTAD", 6000),
                    (u"CARRERA", 6000),
                    (u"ASIGNATURA", 6000),
                    (u"CEDULA", 3500),
                    (u"NOMBRES", 15000),
                    (u"EMAIL INSTITUCIONAL", 6000),
                    (u"CUMPLE REQUISITOS", 6000),

                ]
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]

                row_num = 4
                i = 0
                listadomateriatitulacion = MateriaTitulacion.objects.filter(materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id=request.POST['id_coordinacion'], materiaasignada__materia__nivel__periodo=periodo, status=True)
                if int(request.POST['id_carreras']) > 0:
                    listadomateriatitulacion = MateriaTitulacion.objects.filter(materiaasignada__materia__asignaturamalla__malla__carrera__id=request.POST['id_carreras'], materiaasignada__materia__nivel__periodo=periodo, status=True)
                for listado in listadomateriatitulacion:
                    i += 1
                    campo1 = listado.materiaasignada.materia.asignaturamalla.malla.carrera.coordinacion_carrera().nombre
                    campo2 = listado.materiaasignada.materia.asignaturamalla.malla.carrera.nombre
                    campo3 = listado.materiaasignada.materia.asignaturamalla.asignatura.nombre
                    campo4 = listado.materiaasignada.matricula.inscripcion.persona.cedula
                    campo5 = listado.materiaasignada.matricula.inscripcion.persona.apellido1 + ' ' +listado.materiaasignada.matricula.inscripcion.persona.apellido2 + ' ' + listado.materiaasignada.matricula.inscripcion.persona.nombres
                    campo6 = listado.materiaasignada.matricula.inscripcion.persona.emailinst
                    validacionrequisitos = listado.materiaasignada.matricula.inscripcion.valida_requisitos_complexivo(listado.materiaasignada.materia.id,listado.actacerrada)
                    campo7 = 'NO'
                    if validacionrequisitos:
                        campo7 = 'SI'
                    ws.write(row_num, 0, i, font_style2)
                    ws.write(row_num, 1, campo1, font_style2)
                    ws.write(row_num, 2, campo2, font_style2)
                    ws.write(row_num, 3, campo3, font_style2)
                    ws.write(row_num, 4, campo4, font_style2)
                    ws.write(row_num, 5, campo5, font_style2)
                    ws.write(row_num, 6, campo6, font_style2)
                    ws.write(row_num, 7, campo7, font_style2)
                    row_num += 1

                wb.save(response)
                return response
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'reportasignatura':
                try:
                    if 'idmalla' in request.GET:
                        idmalla=int(encrypt(request.GET['idmalla']))
                        periodo=request.session['periodo']
                        if idmalla == 383:
                            materias = Materia.objects.filter(nivel__periodo_id=periodo, asignaturamalla__malla__id=idmalla, status=True).order_by('paralelo')
                        else:
                            materias = Materia.objects.filter(nivel__periodo_id=periodo, asignaturamalla__validarequisitograduacion=True, asignaturamalla__malla__id=idmalla, status=True).order_by('paralelo')
                        output = io.BytesIO()
                        workbook = xlsxwriter.Workbook(output)
                        formatorojo = workbook.add_format({'bold': True, 'font_color': 'red'})
                        for materia in materias:
                            worksheet = workbook.add_worksheet()
                            requisitos = materia.requisitomateriaunidadintegracioncurricular_set.filter(titulacion=True, status=True).order_by('id')
                            asignados = materia.materiaasignada_set.filter(status=True, retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                            worksheet.write(0, 0, 'Inscrito')
                            worksheet.write(0, 1, 'Identificación')
                            worksheet.write(0, 2, 'Correo Inst')
                            worksheet.write(0, 3, 'Correo Personal')
                            worksheet.write(0, 4, 'Materia')
                            worksheet.write(0, 5, 'Paralelo')
                            worksheet.write(0, 6, 'Facultad')
                            worksheet.write(0, 7, 'Carrera')
                            worksheet.write(0, 8, 'Malla')
                            col = 9
                            fil = 1
                            for erequisito in requisitos:
                                worksheet.write(0, col, str(erequisito.requisito))
                                col += 1
                            for asignado in asignados:
                                inscripcion = asignado.matricula.inscripcion
                                worksheet.write(fil, 0, str(inscripcion.persona))
                                worksheet.write(fil, 1, str(inscripcion.persona.identificacion()))
                                worksheet.write(fil, 2, str(inscripcion.persona.emailinst))
                                worksheet.write(fil, 3, str(inscripcion.persona.email))
                                worksheet.write(fil, 4, str(materia))
                                worksheet.write(fil, 5, str(materia.paralelo))
                                worksheet.write(fil, 6, str(materia.asignaturamalla.malla.carrera.mi_coordinacion()))
                                worksheet.write(fil, 7, str(materia.asignaturamalla.malla.carrera))
                                worksheet.write(fil, 8, str(materia.asignaturamalla.malla))
                                col = 9
                                for erequisito in requisitos:
                                    cumple = erequisito.run(inscripcion.pk)
                                    estadocumple = 'NO CUMPLE'
                                    if cumple:
                                        estadocumple = 'SI CUMPLE'
                                        worksheet.write(fil, col, estadocumple)
                                    else:
                                        worksheet.write(fil, col, estadocumple, formatorojo)
                                    col += 1
                                fil += 1
                        workbook.close()
                        output.seek(0)
                        filename = 'reporte_requisitos' + random.randint(1, 10000).__str__() + '.xlsx'
                        response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        response['Content-Disposition'] = 'attachment; filename=%s' % filename
                        return response
                    else:
                        listado1 = Materia.objects.values_list('asignaturamalla__malla_id', flat=True).filter(asignaturamalla__validarequisitograduacion=True, nivel__periodo=periodo, asignaturamalla__status=True, status=True).distinct()
                        listado2 = Materia.objects.values_list('asignaturamalla__malla_id', flat=True).filter(asignaturamalla__malla_id=383, nivel__periodo=periodo, asignaturamalla__status=True, status=True).distinct()
                        listadomalla = listado1 | listado2
                        data['mallas'] = Malla.objects.filter(pk__in=listadomalla, status=True).order_by('carrera__nombre')
                        template = get_template("adm_alternativatitulacion/modal/formreporte.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'listadotitulados':
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
                    ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 6000),
                        (u"NOMBRE", 6000),
                        (u"CARRERA", 6000),
                        (u"EMAIL", 6000),
                        (u"EMAIL INSTITUCIONAL", 6000),
                        (u"APTO PARA SUSTENTAR", 6000),

                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]

                    row_num = 4
                    periodogrupo = PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['idperiodogrupo']))
                    titulados = MatriculaTitulacion.objects.filter(alternativa__grupotitulacion__periodogrupo=periodogrupo, status=True).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2','inscripcion__persona__nombres')
                    for tit in titulados:

                        campo1 = tit.inscripcion.persona.cedula
                        campo2 = tit.inscripcion.persona.nombre_completo_inverso()
                        campo3 = tit.inscripcion.carrera.nombre
                        campo4 = tit.inscripcion.persona.email
                        campo5 = tit.inscripcion.persona.emailinst
                        campo6 = 'PENDIENTE PARA SUSTENTAR'
                        if tit.cumplerequisitos ==2:
                            campo6 = 'APTO PARA SUSTENTAR'
                        if tit.cumplerequisitos == 3:
                            campo6 = 'NO APTO PARA SUSTENTAR'

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'addgrupotitulacion':
                try:
                    data['title'] = u'Aperturar Grupos de Procesos de Titulación'
                    per=PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['periodo']))
                    titu=GrupoTitulacionForm(initial={'periodo': per })
                    titu.desabilitar()
                    data['form'] = titu
                    data['coordinacion'] = int(request.GET['coordinacion'])
                    data['periodo'] = per.id
                    return render(request, "adm_alternativatitulacion/addgrupotitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editgrupotitulacion':
                try:
                    data['title'] = u'Editar Grupo de Procesos de Titulacion'
                    data['grupo'] = grupo = GrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    form = GrupoTitulacionForm(initial={'periodo': grupo.periodogrupo,
                                                        'nombre': grupo.nombre,
                                                        'fechainicio': grupo.fechainicio,
                                                        'fechafin' : grupo.fechafin,})
                    form.desabilitar()
                    # if grupo.tiene_alternativa_activa():
                    #     # form.desabilitarfechas()
                    if grupo.periodogrupo.fechafin <= datetime.now().date() and grupo.periodogrupo.abierto:
                        # if not grupo.periodogrupo.abierto:
                        form.desabilitarfechas()
                    data['form']=form
                    return render(request, "adm_alternativatitulacion/editgrupotitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporte_matrigulados_todos_periodo':
                try:
                    if data['permiteWebPush']:
                        noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                            titulo='Excel Matriculados Proceso Titulación', destinatario=persona,
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                            en_proceso=True)
                        noti.save(request)
                        reporte_matriculados_background(request=request, data=data, notiid=noti.pk).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        try:
                            tipo = ''
                            borders = Borders()
                            borders.left = 1
                            borders.right = 1
                            borders.top = 1
                            borders.bottom = 1
                            __author__ = 'Unemi'
                            title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
                            normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                            encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
                            normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
                            subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
                            normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
                            font_style = XFStyle()
                            font_style.font.bold = True
                            font_style2 = XFStyle()
                            font_style2.font.bold = False
                            normal.borders = borders
                            normalc.borders = borders
                            normalsub.borders = borders
                            subtema.borders = borders
                            encabesado_tabla.borders = borders
                            wb = Workbook(encoding='utf-8')
                            ws = wb.add_sheet('exp_xls_post_part')

                            response = HttpResponse(content_type="application/ms-excel")
                            response[
                                'Content-Disposition'] = 'attachment; filename=Matriculados_Proceso_Titulación_Todos_Periodos ' + tipo + random.randint(
                                1, 10000).__str__() + '.xls'


                            ws.col(0).width = 1000
                            ws.col(1).width = 2500
                            ws.col(2).width = 4000
                            ws.col(3).width = 3000
                            ws.col(4).width = 3000
                            ws.col(5).width = 4000
                            ws.col(6).width = 4000
                            ws.col(7).width = 3200
                            ws.col(8).width = 5000
                            ws.col(9).width = 4000
                            ws.col(10).width = 4000
                            ws.col(11).width = 4000
                            ws.col(12).width = 4000
                            ws.col(13).width = 4000
                            ws.col(14).width = 4000
                            ws.col(15).width = 4000
                            ws.col(16).width = 4000
                            ws.col(17).width = 4000
                            ws.col(18).width = 4000
                            ws.col(19).width = 4000
                            ws.col(20).width = 4000
                            ws.col(21).width = 4000
                            ws.col(22).width = 4000
                            ws.col(23).width = 4000
                            ws.col(24).width = 4000
                            ws.col(25).width = 4000

                            row_num = 0
                            ws.write(row_num, 0, "Nº", encabesado_tabla)
                            ws.write(row_num, 1, "FACULTAD", encabesado_tabla)
                            ws.write(row_num, 2, "CARRERA", encabesado_tabla)
                            ws.write(row_num, 3, u"PARALELO", encabesado_tabla)
                            ws.write(row_num, 4, u"CEDULA", encabesado_tabla)
                            ws.write(row_num, 5, u"PRIMER APELLIDO", encabesado_tabla)
                            ws.write(row_num, 6, u"SEGUNDO APELLIDO", encabesado_tabla)
                            ws.write(row_num, 7, u"NOMBRES", encabesado_tabla)
                            ws.write(row_num, 8, u"MECANISMO TITULACIÓN", encabesado_tabla)
                            ws.write(row_num, 9, u"ESTADO. MATRICULA", encabesado_tabla)
                            ws.write(row_num, 10, u"Nº MATRICULA", encabesado_tabla)
                            ws.write(row_num, 11, u"TUTOR", encabesado_tabla)
                            ws.write(row_num, 12, u"INTEGRANTE GRUPO", encabesado_tabla)
                            ws.write(row_num, 13, u"NUMERO DE HORAS TUTORIAS", encabesado_tabla)
                            ws.write(row_num, 14, u"TEMA", encabesado_tabla)
                            ws.write(row_num, 15, u"ESTADO FINAL PREVIO SUSTENTACION", encabesado_tabla)
                            ws.write(row_num, 16, 'ESTADO PARA SUSTENTACION', encabesado_tabla)
                            ws.write(row_num, 17, 'PRESIDENTE', encabesado_tabla)
                            ws.write(row_num, 18, 'SECRETARIO', encabesado_tabla)
                            ws.write(row_num, 19, 'INTEGRANTE', encabesado_tabla)
                            ws.write(row_num, 20, u"PRUEBA TEÓRICA", encabesado_tabla)
                            ws.write(row_num, 21, u"NOTA TRABAJO TITULACIÓN PROYECTO", encabesado_tabla)
                            ws.write(row_num, 22, u"NOTA FINAL PERIODO", encabesado_tabla)
                            ws.write(row_num, 23, u"ESTADO PRUEBA TEÓRICA", encabesado_tabla)
                            ws.write(row_num, 24, u"ESTADO INVESTIGACIÓN", encabesado_tabla)
                            ws.write(row_num, 25, u"PERIODOS", encabesado_tabla)
                            ws.write(row_num, 26, u"FECHA SUSTENTACIÓN", encabesado_tabla)

                            date_format = xlwt.XFStyle()
                            date_format.num_format_str = 'yyyy/mm/dd'
                            data = {}

                            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True),
                                                                                                    Q(alternativa__status=True),
                                                                                                    (
                                                                                                            Q(estado=1) | Q(
                                                                                                        estado=9) | Q(
                                                                                                        estado=10))).order_by(
                                'alternativa__facultad', 'alternativa__carrera', 'alternativa',
                                'inscripcion__persona__apellido1')
                            row_num = 1
                            i = 0
                            for matriculados in listamatriculados:

                                if matriculados.id == 1954:
                                    c = matriculados.id

                                campo1 = matriculados.inscripcion.persona.apellido1
                                campo2 = matriculados.inscripcion.persona.apellido2
                                campo3 = matriculados.inscripcion.persona.nombres
                                campo4 = matriculados.inscripcion.persona.sexo.nombre
                                perfilinscripcion = PerfilInscripcion.objects.get(persona=matriculados.inscripcion.persona,
                                                                                  status=True)





                                listaestudios_previos = []
                                if EstudioInscripcion.objects.filter(status=True,
                                                                     persona=matriculados.inscripcion.persona).exists():
                                    estudios = EstudioInscripcion.objects.filter(status=True,
                                                                                 persona=matriculados.inscripcion.persona)
                                    for estudios_pervios in estudios:
                                        listaestudios_previos.append(estudios_pervios.carrera)  # estudiosde estudios previos'

                                if Graduado.objects.filter(inscripcion=matriculados.inscripcion, status=True).exists():
                                    graduado = Graduado.objects.get(inscripcion=matriculados.inscripcion, status=True)

                                campo25 = matriculados.alternativa.tipotitulacion.nombre

                                horas_paracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                    inscripcion=matriculados.inscripcion, status=True, culminada=True)
                                totalhoras = 0
                                if horas_paracticas.exists():
                                    for practicas in horas_paracticas:
                                        if practicas.tiposolicitud == 3:
                                            if practicas.horahomologacion:
                                                totalhoras += practicas.horahomologacion
                                        else:
                                            totalhoras += practicas.numerohora
                                lis = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True,
                                                                           proyecto__status=True,
                                                                           inscripcion_id=matriculados.inscripcion.id)
                                horas_vinculacion = 0
                                for vin in lis:
                                    horas_vinculacion += vin.horas




                                lista_discapacidad = []
                                datos_personal = PersonaDatosFamiliares.objects.filter(persona=matriculados.inscripcion.persona,
                                                                                       status=True)
                                if datos_personal.exists():
                                    for familiardiscapasidad in datos_personal:
                                        if familiardiscapasidad.tienediscapacidad:
                                            lista_discapacidad.append(
                                                [familiardiscapasidad.nombre, familiardiscapasidad.parentesco.nombre])




                                campo97 = 'REPROBADO' if matriculados.reprobo_examen_complexivo() else matriculados.get_estado_display()
                                matriculados.reprobo_examen_complexivo()

                                i += 1

                                ws.write(row_num, 0, i, normal)
                                ws.write(row_num, 1, matriculados.inscripcion.coordinacion.nombre, normal)
                                ws.write(row_num, 2, matriculados.alternativa.carrera.nombre, normal)
                                ws.write(row_num, 3, matriculados.alternativa.paralelo, normal)
                                ws.write(row_num, 4, matriculados.inscripcion.persona.cedula, normal)
                                ws.write(row_num, 5, campo1, normal)
                                ws.write(row_num, 6, campo2, normal)
                                ws.write(row_num, 7, campo3, normal)

                                ws.write(row_num, 8, campo25, normal)


                                campo100 = MatriculaTitulacion.objects.values('id').filter(
                                    Q(inscripcion=matriculados.inscripcion),
                                    (Q(estado=1) | Q(estado=9) | Q(
                                        estado=10)),
                                    fechainscripcion__lte=matriculados.fechainscripcion).count().__str__()
                                campo102 = ''
                                campo103 = ''
                                campo104 = ''
                                campo105 = ''
                                campo106 = ''
                                integrante = ""
                                if ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True):
                                    grupo = \
                                        ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True).order_by(
                                            '-id')[0]
                                    campo104 = u"%s" % str(grupo.grupo.horas_totales_tutorias_grupo())
                                    campo102 = u"%s" % grupo.grupo.tematica.tutor
                                    campo106 = grupo.grupo.estado_propuesta().get_estado_display() if grupo.grupo.estado_propuesta() else ""
                                    if grupo.grupo.subtema:
                                        campo105 = grupo.grupo.subtema
                                    for com in grupo.grupo.complexivodetallegrupo_set.filter(status=True,
                                                                                             matricula__alternativa__grupotitulacion__periodogrupo=matriculados.alternativa.grupotitulacion.periodogrupo):
                                        if matriculados != com.matricula:
                                            campo103 = integrante + u"%s" % com.matricula



                                campo107 = 'PENDIENTE PARA SUSTENTAR'

                                if matriculados.cumplerequisitos == 3:
                                    campo107 = 'NO APTO PARA SUSTENTAR'

                                totalhoras = 0
                                malla = matriculados.inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
                                practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(
                                    inscripcion=matriculados.inscripcion, status=True, culminada=True)
                                data['malla_horas_practicas'] = malla.horas_practicas



                                total_materias_malla = malla.cantidad_materiasaprobadas()
                                cantidad_materias_aprobadas_record = matriculados.inscripcion.recordacademico_set.filter(
                                    aprobada=True, status=True,
                                    asignatura__in=[x.asignatura for x in
                                                    malla.asignaturamalla_set.filter(status=True)]).count()
                                data['mi_nivel'] = nivel = matriculados.inscripcion.mi_nivel()



                                modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
                                lista = []
                                listaid = []
                                for modulo in modulo_ingles:
                                    if matriculados.inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
                                        lista.append(modulo.asignatura.nombre)
                                        listaid.append(modulo.asignatura.id)
                                data['modulo_ingles_aprobados'] = lista

                                data['malla_horas_vinculacion'] = malla.horas_vinculacion
                                horastotal = \
                                    ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True,
                                                                         proyecto__status=True,
                                                                         inscripcion_id=matriculados.inscripcion.id).aggregate(
                                        horastotal=Sum('horas'))['horastotal']

                                asignatura = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(
                                    malla__id=32)
                                record = RecordAcademico.objects.filter(inscripcion__id=matriculados.inscripcion.id,
                                                                        asignatura__id__in=asignatura, aprobada=True)
                                creditos_computacion = 0
                                malla.creditos_computacion
                                listconcreditos = []
                                for comp in record:
                                    listconcreditos.append(comp.asignatura.nombre)
                                    creditos_computacion += comp.creditos


                                presidente = ""
                                secretario = ""
                                integrantedelegado = ""
                                fechagrupo = ""

                                if ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True):
                                    grupocomplexivo = \
                                        ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True)[0]
                                    if grupocomplexivo.grupo.presidentepropuesta:
                                        presidente = u"%s" % grupocomplexivo.grupo.presidentepropuesta.persona

                                    if grupocomplexivo.grupo.secretariopropuesta:
                                        secretario = u"%s" % grupocomplexivo.grupo.secretariopropuesta.persona

                                    if grupocomplexivo.grupo.delegadopropuesta:
                                        integrantedelegado = u"%s" % grupocomplexivo.grupo.delegadopropuesta.persona

                                    if grupocomplexivo.grupo.fechadefensa:
                                        fechagrupo = u"%s" % grupocomplexivo.grupo.fechadefensa


                                codigoestado = 0
                                nomestado = ''
                                pexamen = 0
                                if matriculados.alternativa.tiene_examen():
                                    if ComplexivoExamenDetalle.objects.filter(status=True, matricula=matriculados).exists():
                                        detalle = \
                                            ComplexivoExamenDetalle.objects.filter(status=True,
                                                                                   matricula=matriculados).order_by('-id')[
                                                0]
                                        nomestado = detalle.get_estado_display()
                                        codigoestado = detalle.estado
                                        pexamen = detalle.ponderacion()

                                ppropuesta = 0
                                ptotal = 0
                                if ComplexivoGrupoTematica.objects.values('id').filter(status=True,
                                                                                       complexivodetallegrupo__status=True,
                                                                                       complexivodetallegrupo__matricula=matriculados).exists():
                                    ppropuesta = matriculados.notapropuesta()
                                if matriculados.alternativa.tipotitulacion.tipo == 1:
                                    ptotal = ppropuesta
                                if matriculados.alternativa.tipotitulacion.tipo == 2:
                                    ptotal = matriculados.notafinalcomplexivoestado(codigoestado)
                                estadotitulacion = matriculados.get_estadotitulacion_display()

                                ws.write(row_num, 19, integrantedelegado, normal)
                                ws.write(row_num, 18, secretario, normal)
                                ws.write(row_num, 17, presidente, normal)

                                ws.write(row_num, 16, campo107, normal)

                                ws.write(row_num, 9, campo97, normal)

                                ws.write(row_num, 10, campo100, normal)
                                ws.write(row_num, 11, campo102, normal)
                                ws.write(row_num, 12, campo103, normal)
                                ws.write(row_num, 13, campo104, normal)
                                ws.write(row_num, 14, campo105, normal)
                                ws.write(row_num, 15, campo106, normal)

                                ws.write(row_num, 20, pexamen, normal)
                                ws.write(row_num, 21, ppropuesta, normal)
                                ws.write(row_num, 22, ptotal, normal)
                                ws.write(row_num, 23, nomestado, normal)
                                ws.write(row_num, 24, estadotitulacion, normal)
                                ws.write(row_num, 25, matriculados.alternativa.grupotitulacion.periodogrupo.nombre, normal)
                                ws.write(row_num, 26, fechagrupo)
                                row_num += 1
                            wb.save(response)
                            return response
                        except Exception as ex:
                            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                            pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'eliminargrupotitulacion':
                try:
                    data['title'] = u'Eliminar Grupo Titulación'
                    data['grupo'] = GrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_alternativatitulacion/eliminargrupotitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'alternativa':
                try:
                    data['title'] = u'Alternativas de Titulación'
                    data['grupotitulacion'] = grupo = GrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    data['carreras'] = carrera = Coordinacion.objects.get(pk=grupo.facultad.id).carreras()
                    data['tipotitulaciones'] = TipoTitulaciones.objects.values_list('id', 'nombre', flat=False).filter(status=True, id__in=grupo.alternativatitulacion_set.values_list('tipotitulacion__id', flat=False).filter(status=True)).distinct()
                    data['fechasistema'] = datetime.now().date()
                    data['proceso_cerrado'] = grupo.grupocerrado()
                    tiposelect = 0
                    paraleloselect = 0
                    carreraid = carrera[0]
                    paralelos = AlternativaTitulacion.objects.values_list('paralelo', flat=False).filter(carrera=carreraid, status=True).distinct('paralelo') if AlternativaTitulacion.objects.filter(carrera=carreraid, status=True).exists() else []
                    alternativatitulacion = grupo.listado_alternativa(carreraid.id)
                    if 'cid' in request.GET:
                        carreraid = Carrera.objects.get(pk=int(request.GET['cid']))
                        alternativatitulacion = grupo.alternativatitulacion_set.filter(status=True, carrera_id=int(request.GET['cid']))
                    if 'tid' in request.GET:
                        tiposelect = int(request.GET['tid'])
                        alternativatitulacion = alternativatitulacion.filter(tipotitulacion__id=tiposelect)
                        paralelos = AlternativaTitulacion.objects.values_list('paralelo', flat=False).filter(pk__in=alternativatitulacion.values_list('id', flat=False)).distinct('paralelo') if AlternativaTitulacion.objects.filter(pk__in=alternativatitulacion.values_list('id', flat=False)).exists() else []
                    if 'par' in request.GET:
                        paraleloselect = request.GET['par']
                        alternativatitulacion = alternativatitulacion.filter(paralelo=paraleloselect)
                    data['matriculados_car'] = MatriculaTitulacion.objects.values('id').filter(status=True, estado__in=[1,9,10], alternativa__id__in=carreraid.alternativatitulacion_set.values_list('id', flat=False).filter(status=True, grupotitulacion=grupo)).count()
                    data['eliminados_car'] = MatriculaTitulacion.objects.values('id').filter(status=True, estado=8, alternativa__id__in=carreraid.alternativatitulacion_set.values_list('id', flat=False).filter(status=True, grupotitulacion=grupo)).count()
                    data['carreraselect'] = carreraid
                    data['contador_busqueda'] = MatriculaTitulacion.objects.filter(alternativa__id__in=alternativatitulacion.values_list('id', flat=False), estado__in=[1,9,10]).count() if alternativatitulacion else 0
                    data['tiposelectid'] = tiposelect
                    data['paraleloselect'] = paraleloselect
                    data['paralelos'] = paralelos
                    data['alternativatitulacion'] = alternativatitulacion
                    return render(request, "adm_alternativatitulacion/alternativa.html", data)
                except Exception as ex:
                    pass

            elif action == 'addalternativa':
                try:
                    data['title'] = u'Adicionar Alternativa de Titulación'
                    data['grupotitulacionid'] =int(request.GET['idg'])
                    data['carreraid'] = int(request.GET['idc'])
                    grupo = GrupoTitulacion.objects.get(pk=int(request.GET['idg']))
                    gruponombre = grupo.nombre+" "+str(grupo.fechainicio.strftime("%d/%m/%Y"))+" A "+str(grupo.fechafin.strftime("%d/%m/%Y"))
                    #malla = None
                    #if Malla.objects.filter(carrera_id=int(request.GET['idc']), vigente=True, status=True).exists():
                    #    malla = Malla.objects.filter(carrera_id=int(request.GET['idc']), vigente=True, status=True)[0]
                    coordinacion = Coordinacion.objects.get(pk=grupo.facultad.id)
                    form= AlternativaTitulacionForm(initial={'grupo':gruponombre, 'carreras': int(request.GET['idc'])})
                    form.fields['carreras'].queryset = coordinacion.carreras()
                    idperiodo = coordinacion.paeactividadesperiodoareas_set.values_list('periodoarea__periodo_id', flat=False).filter(status=True).distinct()
                    form.fields['acperiodo'].queryset = Periodo.objects.filter(id__in=idperiodo)
                    form.fields['malla'].queryset = Malla.objects.filter(carrera_id=int(request.GET['idc']), status=True)
                    form.editar()
                    form.editarsesion()
                    data['form'] = form
                    return render(request, "adm_alternativatitulacion/addalternativa.html", data)
                except Exception as ex:
                    pass

            elif action == 'editalternativa':
                try:
                    horastotales=0
                    data['title'] = u'Editar Alternativa de Titulación'
                    data['alternativa'] = alter = AlternativaTitulacion.objects.get(pk=int(request.GET['ida']))
                    gruponombre=alter.grupotitulacion.nombre+" "+str(alter.grupotitulacion.fechainicio.strftime("%d/%m/%Y"))+" A "+str(alter.grupotitulacion.fechafin.strftime("%d/%m/%Y"))
                    sesion=''
                    if alter.sesiontitulacion_set.all().exists():
                        sesion= alter.sesiontitulacion_set.get().sesion
                    form = AlternativaTitulacionForm(initial={'grupo':gruponombre,
                                                              'carreras':alter.carrera,
                                                              'alias': alter.alias,
                                                              'sesion':sesion if sesion else[],
                                                              'horastotales':alter.horastotales,
                                                              'creditos': alter.creditos,
                                                              'horassemanales': alter.horassemanales,
                                                              'cupo': alter.cupo,
                                                              'paralelo': alter.paralelo,
                                                              'fechainiciomatriculacion': alter.fechamatriculacion,
                                                              'fechafinmatriculacion': alter.fechamatriculacionfin,
                                                              'fechaordinariainicio': alter.fechaordinariainicio,
                                                              'fechaordinariafin': alter.fechaordinariafin,
                                                              'fechaextraordinariainicio': alter.fechaextraordinariainicio,
                                                              'fechaextraordinariafin': alter.fechaextraordinariafin,
                                                              'fechaespecialinicio': alter.fechaespecialinicio,
                                                              'fechaespecialfin': alter.fechaespecialfin,
                                                              'estadocomputacion': alter.estadocomputacion,
                                                              'estadoingles': alter.estadoingles,
                                                              'estadovinculacion': alter.estadovinculacion,
                                                              'estadopractica': alter.estadopracticaspreprofesionales,
                                                              'estadoadeudar': alter.estadoadeudar,
                                                              'estadocredito': alter.estadocredito,
                                                              'estadonivel': alter.estadonivel,
                                                              'estadofichaestudiantil': alter.estadofichaestudiantil,
                                                              'verestudiantes': alter.verestudiantes,
                                                              'descripcion': alter.descripcion,
                                                              'modelotitulacion': ModeloTitulacion.objects.filter(pk__in= alter.modelo_alternativatitulacion_set.values_list('modelo__id', flat=False).filter(status=True)),
                                                              'aplicapropuesta': alter.aplicapropuesta,
                                                              'procesorezagado': alter.procesorezagado,
                                                              'fechanoaplicapropuesta': alter.fechanoaplicapropuesta,
                                                              'docenteevaluador1': alter.docenteevaluador1,
                                                              'docenteevaluador2': alter.docenteevaluador2,
                                                              'actividadcomplementaria':alter.actividadcomplementaria,
                                                              'acperiodo':alter.acperiodo,
                                                              'malla':alter.malla
                                                              }
                                                     )
                    if alter.docenteevaluador1:
                        form.fields['docenteevaluador1'].widget.attrs['descripcion'] = alter.docenteevaluador1
                        form.fields['docenteevaluador1'].widget.attrs['value'] = alter.docenteevaluador1.id
                        data['eva1'] = alter.docenteevaluador1.id
                    else:
                        form.fields['docenteevaluador1'].widget.attrs['descripcion'] = '----------------'
                        form.fields['docenteevaluador1'].widget.attrs['value'] = 0
                        data['eva1'] = 0

                    if alter.docenteevaluador2:
                        form.fields['docenteevaluador2'].widget.attrs['descripcion'] = alter.docenteevaluador2
                        form.fields['docenteevaluador2'].widget.attrs['value'] = alter.docenteevaluador2.id
                        data['eva2'] = alter.docenteevaluador1.id
                    else:
                        form.fields['docenteevaluador2'].widget.attrs['descripcion'] = '----------------'
                        form.fields['docenteevaluador2'].widget.attrs['value'] = 0
                        data['eva2'] = 0
                    coordinacion = alter.grupotitulacion.facultad
                    idperiodo = coordinacion.paeactividadesperiodoareas_set.values_list('periodoarea__periodo_id', flat=False).filter(status=True).distinct()
                    form.fields['acperiodo'].queryset = Periodo.objects.filter(id__in=idperiodo)
                    form.fields['tipotitulacion'].initial=alter.tipotitulacion
                    form.fields['malla'].queryset = alter.carrera.malla_set.filter(status=True)
                    form.editar()
                    form.editarcarrera()
                    if alter.contar_matriculados()>0:
                        form.tiene_matriculados()
                    if alter.grupotitulacion.grupocerrado():
                        form.editarcupolleno()
                        data['permite_modificar'] = False
                    if not alter.sesiontitulacion_set.all().exists():
                        form.editarsesion()
                    data['form'] = form
                    # data['lista_modelo'] =alter.modelo_alternativatitulacion_set.filter(status=True)
                    return render(request, "adm_alternativatitulacion/editalternativa.html", data)
                except Exception as ex:
                    pass

            elif action == 'editalternativamatri':
                try:
                    data['title'] = u'Editar Alternativa de Titulación'
                    data['idperiodomatriculado'] = int(encrypt(request.GET['idperiodomatriculado']))
                    data['matriculado'] = matriculacion = MatriculaTitulacion.objects.get(pk=int(encrypt(request.GET['idm'])))
                    form = AlternativaTitulacionMatriForm(initial={'tipotitulacion':matriculacion.alternativa})
                    form.fields['tipotitulacion'].queryset = AlternativaTitulacion.objects.filter(carrera=matriculacion.alternativa.carrera,grupotitulacion__periodogrupo=matriculacion.alternativa.grupotitulacion.periodogrupo,status=True)
                    data['form'] = form
                    return render(request, "adm_alternativatitulacion/editalternativamatri.html", data)
                except Exception as ex:
                    pass

            elif action == 'eliminaralternativa':
                try:
                    data['title'] = u'Borrar Alternativa Titulación'
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_alternativatitulacion/eliminaralternativa.html", data)
                except Exception as ex:
                    pass

            elif action == 'duplicaralternativa':
                try:
                    data['title'] = u'Duplicar Alternativa Titulación'
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_alternativatitulacion/duplicaralternativa.html", data)
                except Exception as ex:
                    pass

            elif action == 'extraertotalmodelo':
                try:
                    if 'g' in request.GET and 'm' in request.GET and 'carrera_id' in request.GET:
                        suma=0
                        grupo = GrupoTitulacion.objects.get(pk=int(request.GET['g']))  # envia como arreglo
                        listmodel = json.loads(request.GET['m'])
                        horas_titulacion = Malla.objects.get(id=int(request.GET['idm']))
                        for mid in listmodel:
                            model = ModeloTitulacion.objects.get(pk=int(mid))
                            total = model.horaspresencial + model.horasvirtual + model.horasautonoma
                            suma += total
                        data = {"results": "ok", "total": str(suma)+"/"+str(horas_titulacion.horas_titulacion)}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'validarcreditos':
                try:
                    if 'carrera_id' in request.GET:
                        listamalla = []
                        lista = []
                        if TipoTitulaciones.objects.filter(id__in=CombinarTipoTitulaciones.objects.values_list('tipotitulacion__id', flat=False).filter(carrera_id=int(request.GET['carrera_id']), status=True)).exists():
                            titulacion = TipoTitulaciones.objects.filter(id__in=CombinarTipoTitulaciones.objects.values_list('tipotitulacion__id', flat=False).filter(carrera_id=int(request.GET['carrera_id']), status=True).distinct())
                            for lis in titulacion:
                                lista.append([lis.id, lis.nombre])
                        for malla in Malla.objects.filter(carrera_id=int(request.GET['carrera_id']), status=True):
                            listamalla.append([malla.id, str(malla)])
                        # data = {"results": "ok", "total": malla.horas_titulacion, "lista":lista, "listamalla": listamalla}
                        data = {"results": "ok", "lista":lista, "listamalla": listamalla}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'validarsesion':
                try:
                    if 't' in request.GET:
                        listado = []
                        co= CombinarTipoTitulaciones.objects.get(pk= int(request.GET['t']))
                        tipo = TipoTitulaciones.objects.get(id=co.tipotitulacion_id)
                        if tipo.rubrica:
                            rubricas = RubricaTitulacionCab.objects.filter(pk=tipo.rubrica_id)
                            for rub in rubricas:
                                listado.append([rub.id, rub.nombre])
                        if tipo==PROYECTOS_TITULACION_ID:
                            data = {"results": "ok", "tipo":1}
                        else:
                            data = {"results": "ok", "tipo":2}
                        return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addprofesores':
                try:
                    data['title'] = u'Agregar Profesores'
                    data['alternativa'] =alter= AlternativaTitulacion.objects.get(pk=int(request.GET['ida']))
                    lista_profesor=ProfesoresTitulacion.objects.values_list('profesorTitulacion').filter(alternativa_id=alter.id,status=True)
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            profesores = Profesor.objects.filter(Q(activo=True),(
                                    Q(persona__nombres__icontains=search) |
                                    Q(persona__apellido1__icontains=search) |
                                    Q(persona__apellido2__icontains=search) |
                                    Q(persona__cedula__icontains=search) |
                                    Q(persona__pasaporte__icontains=search))).exclude(
                                Q(coordinacion=MODULO_INGLES_ID) |
                                # Q(coordinacion=POSGRADO_EDUCACION_ID) |
                                Q(coordinacion=MODULOS_COMPUTACION_ID) |
                                Q(coordinacion=ADMISION_ID) |
                                Q(pk__in=lista_profesor)).distinct().order_by(
                                '-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2',
                                'persona__nombres')
                        else:
                            profesores = Profesor.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                 Q(persona__apellido2__icontains=ss[1])&
                                                                 Q(activo=True)).exclude(
                                Q(coordinacion=MODULO_INGLES_ID) |
                                # Q(coordinacion=POSGRADO_EDUCACION_ID) |
                                Q(coordinacion=MODULOS_COMPUTACION_ID) |
                                Q(coordinacion=ADMISION_ID) |
                                Q(pk__in=lista_profesor)).distinct().order_by(
                                '-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2',
                                'persona__nombres')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        profesores = Profesor.objects.filter(id=ids)
                    else:
                        profesores = Profesor.objects.filter(activo=True).order_by('-persona__usuario__is_active',
                                                                                   'persona__apellido1', 'persona__apellido2',
                                                                                   'persona__nombres').exclude(
                            Q(coordinacion=MODULO_INGLES_ID) |
                            Q(coordinacion=POSGRADO_EDUCACION_ID) |
                            Q(coordinacion=MODULOS_COMPUTACION_ID) |
                            Q(coordinacion=ADMISION_ID)|
                            Q(pk__in=lista_profesor))

                    paging = MiPaginador(profesores, 25)
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
                    data['ids'] = ids if ids else ""
                    data['profesores'] = page.object_list
                    return render(request, "adm_alternativatitulacion/addprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'delprofesor':
                try:
                    data['title'] = u'Eliminar Profesor'
                    data['profesor'] = ProfesoresTitulacion.objects.get(pk=int(request.GET['idp']))
                    return render(request, "adm_alternativatitulacion/eliminarprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'profesores':
                try:
                    data['title'] = u'Listado de Profesores'
                    data['profesores'] = ProfesoresTitulacion.objects.filter(alternativa_id=int(request.GET['ida']),status=True).order_by('-id')
                    data['alternativa'] =alter=AlternativaTitulacion.objects.get(pk=int(request.GET['ida']))
                    return render(request, "adm_alternativatitulacion/profesores.html", data)
                except Exception as ex:
                    pass

            elif action == 'matricula':
                try:
                    data['title'] = u'Listado de estudiantes matrículados al Proceso de Titulación'
                    data['alternativa'] = alter = AlternativaTitulacion.objects.get(pk=int(request.GET['ida']))
                    search = None
                    ids = None
                    ide=0
                    if 'ide' in request.GET:
                        ide = int(request.GET['ide'])
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            if ide>0:
                                matriculados = MatriculaTitulacion.objects.filter(Q(alternativa=alter)&Q(estado=ide)&(
                                        Q(inscripcion__persona__nombres__icontains=search) |
                                        Q(inscripcion__persona__apellido1__icontains=search) |
                                        Q(inscripcion__persona__apellido2__icontains=search) |
                                        Q(inscripcion__persona__cedula__icontains=search))).distinct().order_by(
                                    '-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1',
                                    'inscripcion__persona__apellido2','inscripcion__persona__nombres')

                            else:
                                matriculados = MatriculaTitulacion.objects.filter(Q(alternativa=alter) & (Q(inscripcion__persona__nombres__icontains=search) |
                                                                                                          Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                                          Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                                          Q(inscripcion__persona__cedula__icontains=search))).distinct().order_by(
                                    '-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1',
                                    'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                        else:
                            if ide>0:
                                matriculados = MatriculaTitulacion.objects.filter(Q(alternativa=alter)& Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                  Q(inscripcion__persona__apellido2__icontains=ss[1]) & Q(estado=ide)).distinct().order_by(
                                    '-inscripcion__persona__usuario__is_active',
                                    'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                    'inscripcion__persona__nombres')
                            else:
                                matriculados = MatriculaTitulacion.objects.filter(Q(alternativa=alter) & Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                  Q(inscripcion__persona__apellido2__icontains=ss[1])).distinct().order_by(
                                    '-inscripcion__persona__usuario__is_active',
                                    'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2',
                                    'inscripcion__persona__nombres')

                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        matriculados = MatriculaTitulacion.objects.filter(id=ids)
                    else:
                        if ide>0:
                            matriculados = MatriculaTitulacion.objects.filter(alternativa=alter,estado=ide).order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                        else:
                            matriculados = MatriculaTitulacion.objects.filter(alternativa=alter).order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                    paging = MiPaginador(matriculados, 25)
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
                    data['ids'] = ids if ids else ""
                    data['lista_estado_matricula'] = ESTADOS_MATRICULA
                    data['matriculados'] = page.object_list
                    data['estadomatriculaid'] = ide
                    data['periodo'] = request.session['periodo']
                    data['form'] = EliminarMatriculatitulacionForm()
                    return render(request, "adm_alternativatitulacion/matricula.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadomatriculados':
                try:
                    data['title'] = u'Listado de estudiantes matrículados al Proceso de Titulación'
                    # data['alternativa'] = alter = AlternativaTitulacion.objects.get(pk=int(request.GET['ida']))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    ids = None
                    ide=0
                    data['periodogrupo'] = periodogrupo = PeriodoGrupoTitulacion.objects.get(pk=int(encrypt(request.GET['idperiodogrupo'])))
                    if 'ide' in request.GET:
                        ide = int(request.GET['ide'])
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            if ide>0:
                                matriculados = MatriculaTitulacion.objects.filter(Q(estado=ide)&(
                                        Q(inscripcion__persona__nombres__icontains=search) |
                                        Q(inscripcion__persona__apellido1__icontains=search) |
                                        Q(inscripcion__persona__apellido2__icontains=search) |
                                        Q(inscripcion__persona__cedula__icontains=search))).exclude(estado=8).distinct().order_by(
                                    '-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1',
                                    'inscripcion__persona__apellido2','inscripcion__persona__nombres')

                            else:
                                matriculados = MatriculaTitulacion.objects.filter((Q(inscripcion__persona__nombres__icontains=search) |
                                                                                   Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                   Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                   Q(inscripcion__persona__cedula__icontains=search))).exclude(estado=8).distinct().order_by(
                                    '-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1',
                                    'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                        else:
                            if ide>0:
                                matriculados = MatriculaTitulacion.objects.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &  Q(inscripcion__persona__apellido2__icontains=ss[1]) & Q(estado=ide)).exclude(estado=8).distinct().order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                            else:
                                matriculados = MatriculaTitulacion.objects.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(inscripcion__persona__apellido2__icontains=ss[1])).exclude(estado=8).distinct().order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        matriculados = MatriculaTitulacion.objects.filter(status=True).exclude(estado=8)
                    else:
                        if ide>0:
                            matriculados = MatriculaTitulacion.objects.filter(estado=ide).exclude(estado=8).order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                        else:
                            matriculados = MatriculaTitulacion.objects.filter(status=True).exclude(estado=8).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    url_vars += "&action=listadomatriculados&idperiodogrupo=" + request.GET['idperiodogrupo']
                    paging = MiPaginador(matriculados, 25)
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
                    data['ids'] = ids if ids else ""
                    data['lista_estado_matricula'] = ESTADOS_MATRICULA
                    data['matriculados'] = page.object_list
                    data["url_vars"] = url_vars
                    data['estadomatriculaid'] = ide
                    data['periodo'] = request.session['periodo']
                    data['persona'] = request.session['persona']
                    data['form'] = EliminarMatriculatitulacionForm()
                    return render(request, "adm_alternativatitulacion/listadomatriculados.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoalternativas':
                try:
                    data['title'] = u'Listado de alternativas'
                    data['periodogrupo'] = periodogrupo = PeriodoGrupoTitulacion.objects.get(pk=int(encrypt(request.GET['idperiodogrupo'])))
                    matriculado = MatriculaTitulacion.objects.get(pk=int(encrypt(request.GET['idm'])))
                    data['grupo'] = detalle = ComplexivoDetalleGrupo.objects.filter(matricula=matriculado, status=True,grupo__activo=True)[0]
                    data['detallegrupo'] = detalle.grupo.complexivodetallegrupo_set.filter(status=True,grupo__activo=True)
                    data['periodo'] = request.session['periodo']
                    return render(request, "adm_alternativatitulacion/listadoalternativas.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadorubricas':
                try:
                    data['title'] = u'Listado de rúbricas'
                    data['listadorubricas'] = RubricaTitulacionCab.objects.filter(status=True)
                    return render(request, "adm_alternativatitulacion/listadorubricas.html", data)
                except Exception as ex:
                    pass

            elif action == 'configuraciones':
                try:
                    data['title'] = u'Configuración'
                    data['ponderaciones'] = PonderacionRubrica.objects.filter(status=True)
                    return render(request, "adm_alternativatitulacion/configuraciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'addponderacionmodal':
                try:
                    data['form2'] = PonderacionRubricaForm()
                    template = get_template("adm_alternativatitulacion/modal/formponderacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editponderacionmodal':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = PonderacionRubrica.objects.get(pk=request.GET['id'])
                    data['form2'] = PonderacionRubricaForm(initial=model_to_dict(filtro))
                    template = get_template("adm_alternativatitulacion/modal/formponderacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listadodetallerubricas':
                try:
                    data['title'] = u'Detalle de rúbricas'
                    data['rubrica'] = rubrica = RubricaTitulacionCab.objects.get(pk=int(encrypt(request.GET['idrubrica'])))
                    data['listadodetallerubricas'] = rubrica.rubricatitulacion_set.filter(status=True).order_by('modelorubrica__orden','orden')
                    data['ponderacionesrubrica'] = rubrica.rubricatitulacioncabponderacion_set.filter(status=True).order_by('orden')
                    mostrar=True
                    llenarescala=True
                    llenarpondercion=True
                    # if rubrica.id == 2 or rubrica.id == 3:
                    #     mostrar = False
                    if rubrica.en_usoalternativa():
                        mostrar = False
                    if rubrica.rubricatitulacioncabponderacion_set.filter(status=True):
                        llenarescala=False
                    if rubrica.modelorubricatitulacion_set.filter(status=True):
                        llenarpondercion=False
                    data['mostrar'] = mostrar
                    data['llenarescala'] = llenarescala
                    data['llenarpondercion'] = llenarpondercion
                    data['listadomodelorubrica'] = rubrica.modelorubricatitulacion_set.filter(status=True).order_by('id')
                    return render(request, "adm_alternativatitulacion/listadodetallerubricas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrubrica':
                try:
                    data['title'] = u'Adicionar rúbrica de titulación'
                    data['form'] = RubricaTitulacionCabForm()
                    return render(request, "adm_alternativatitulacion/addrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrubrica':
                try:
                    data['title'] = u'Editar rúbrica'
                    data['rubrica'] = rubrica = RubricaTitulacionCab.objects.get(pk=int(encrypt(request.GET['idrubrica'])))
                    form = RubricaTitulacionCabForm(initial={'nombre': rubrica.nombre,
                                                             'activa': rubrica.activa})
                    data['form'] = form
                    data['detallemodelorubrica'] = rubrica.modelorubricatitulacion_set.filter(status=True).order_by('orden')
                    data['ponderacionesrubrica'] = ponderacionesrubrica = rubrica.rubricatitulacioncabponderacion_set.filter(status=True).order_by('orden')
                    data['comboponderaciones'] = PonderacionRubrica.objects.filter(status=True).exclude(pk__in=ponderacionesrubrica.values_list('ponderacion_id',flat=True))
                    return render(request, "adm_alternativatitulacion/editrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdetallerubrica':
                try:
                    data['title'] = u'Editar detalle rúbrica'
                    data['detrubrica'] = detrubrica = RubricaTitulacion.objects.get(pk=int(encrypt(request.GET['iddetallerubrica'])))
                    form = RubricaTitulacionForm(initial={'letra': detrubrica.letra,
                                                          'nombre': detrubrica.nombre,
                                                          'excelente': detrubrica.excelente,
                                                          'muybueno': detrubrica.muybueno,
                                                          'bueno': detrubrica.bueno,
                                                          'suficiente': detrubrica.suficiente,
                                                          'leyendaexcelente': detrubrica.leyendaexcelente,
                                                          'leyendamuybueno': detrubrica.leyendamuybueno,
                                                          'leyendabueno': detrubrica.leyendabueno,
                                                          'leyendasuficiente': detrubrica.leyendasuficiente,
                                                          'puntaje': detrubrica.puntaje,
                                                          'tipotitulacion': detrubrica.tipotitulacion
                                                          })
                    data['form'] = form
                    return render(request, "adm_alternativatitulacion/editdetallerubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoalternativascambiar':
                try:
                    data['title'] = u'Listado de alternativas'
                    data['periodogrupo'] = PeriodoGrupoTitulacion.objects.get(pk=int(encrypt(request.GET['idperiodogrupo'])))
                    data['matriculado'] = matriculado = MatriculaTitulacion.objects.get(pk=int(encrypt(request.GET['idm'])))
                    data['alternativaalumno'] = alternativaalumno = AlternativaTitulacion.objects.get(pk=int(encrypt(request.GET['idalternativa'])), status=True)
                    data['alternativacambiar'] = AlternativaTitulacion.objects.filter(grupotitulacion=alternativaalumno.grupotitulacion,carrera=alternativaalumno.carrera, status=True).exclude(pk=alternativaalumno.id)
                    return render(request, "adm_alternativatitulacion/listadoalternativascambiar.html", data)
                except Exception as ex:
                    pass

            if action == 'detallematricula':
                try:
                    matricula = MatriculaTitulacion.objects.get(pk=int(request.GET['idm']))
                    alter = AlternativaTitulacion.objects.get(pk=matricula.alternativa_id)
                    inscripcion = Inscripcion.objects.get(pk=matricula.inscripcion_id)
                    # data = valida_matricular_estudiante(data, alter, inscripcion)
                    data = inscripcion.valida_matricular_estudiante(alter)
                    return render(request, "adm_alternativatitulacion/detallematriculatitulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarestudiante':
                try:
                    data['alternativa'] = alter = AlternativaTitulacion.objects.get(pk=int(request.GET['ida']))
                    if alter.matriculatitulacion_set.filter(Q(estado=1) | Q(estado=2) | Q(estado=5) | Q(estado=6) | Q(estado=7)).count()<= alter.cupo:
                        #     return ( u"En hora buena ustad esta matriculado en el proceso titulacion")
                        data['title'] = u'Listado de Alumnos'
                        lista_graduados = Graduado.objects.values_list('inscripcion_id',flat=True).filter(status= True, inscripcion__carrera= alter.carrera)
                        lista_estudiantes = MatriculaTitulacion.objects.values_list('inscripcion_id', flat=True).filter(Q(alternativa__carrera=alter.carrera), Q(status=True), (Q(estado= 1)|Q(estado=6))).exclude(complexivodetallegrupo__estado=3)
                        search = None
                        ids = None
                        if 's' in request.GET:
                            search = request.GET['s'].strip()
                            ss = search.split(' ')
                            if len(ss) == 1:
                                inscripciones = Inscripcion.objects.filter((Q(persona__nombres__icontains=search) |
                                                                            Q(persona__apellido1__icontains=search) |
                                                                            Q(persona__apellido2__icontains=search) |
                                                                            Q(persona__cedula__icontains=search)|
                                                                            Q(persona__usuario__username__icontains=search)),
                                                                           Q(carrera=alter.carrera)).distinct().exclude(Q(id__in=lista_graduados)| Q(id__in=lista_estudiantes)).distinct()
                            else:
                                inscripciones = Inscripcion.objects.filter((Q(persona__apellido1__icontains=ss[0]) &
                                                                            Q(persona__apellido2__icontains=ss[1])),
                                                                           Q(carrera=alter.carrera)).distinct().exclude(Q(id__in=lista_graduados)| Q(id__in=lista_estudiantes)).distinct()
                        else:
                            inscripciones = Inscripcion.objects.filter(carrera_id=alter.carrera_id, status= True).distinct().exclude(Q(id__in=lista_graduados)| Q(id__in=lista_estudiantes)).distinct()
                        paging = MiPaginador(inscripciones, 15)
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
                        data['ids'] = ids if ids else ""
                        data['inscripciones'] = page.object_list
                        return render(request, "adm_alternativatitulacion/buscarestudiante.html", data)
                except Exception as ex:
                    pass

            elif action == 'matricularestudiante':
                try:
                    data['title'] = u'Incripciones al Proceso de Titulación'
                    alter = AlternativaTitulacion.objects.get(pk=int(request.GET['ida']))
                    inscripcion = Inscripcion.objects.get(pk=int(request.GET['idi']))
                    data = valida_matricular_estudiante(data, alter, inscripcion)
                    if 's' in request.GET:
                        data['s'] = request.GET['s']
                    return render(request, "adm_alternativatitulacion/matricularestudiante.html", data)
                except Exception as ex:
                    pass
            # -----------MATERIAS------------------
            elif action == 'materias':
                try:
                    data['title'] = u'MATERIAS COMPLEXIVO'
                    data['alternativa'] = alternativa = AlternativaTitulacion.objects.get(pk=request.GET['alt'])
                    data['materias'] = ComplexivoMateria.objects.filter(alternativa=alternativa,status=True).order_by('id')
                    data['existecronograma'] = True if alternativa.get_cronograma() else False
                    return render(request, 'adm_alternativatitulacion/viewmateria.html', data)
                except Exception as ex:
                    pass

            elif action == 'addmateria':
                try:
                    data['title']= u'Adicionar Materia Complexivo'
                    alternativa = AlternativaTitulacion.objects.get(pk=request.GET['alt'])
                    form = ComplexivoMateriaForm(initial={'fechainicio': alternativa.get_cronograma().get().fechanucleobasicoinicio,
                                                          'fechafin': alternativa.get_cronograma().get().fechanucleoproffin})
                    form.cargarprofesor(alternativa)
                    if alternativa.sesiontitulacion_set.all().exists():
                        form.initial={'sesion': alternativa.get_sesion().sesion}
                        form.tiene_sesion()
                    data['form'] = form
                    data['alternativa'] = alternativa
                    return render(request, 'adm_alternativatitulacion/addmateria.html', data)
                except Exception as ex:
                    pass

            elif action == 'editmateria':
                try:
                    data['title'] = u'Editar materia'
                    materia=ComplexivoMateria.objects.get(pk=request.GET['id'])
                    alternativa = AlternativaTitulacion.objects.get(pk=materia.alternativa_id)
                    form = ComplexivoMateriaForm(initial={
                        'sesion': materia.sesion,
                        'asignatura': materia.asignatura,
                        'profesor': materia.profesor,
                        'horatotal': materia.horatotal,
                        'horasemanal': materia.horasemanal,
                        'fechainicio': materia.fechainicio,
                        'fechafin': materia.fechafin,
                    })

                    if alternativa.get_sesion():
                        form.tiene_sesion()
                    if materia.tiene_horario() and materia.fechainicio<=datetime.now().date():
                        form.tiene_horario()
                    form.editar()
                    data['form'] = form
                    data['alternativa'] = alternativa
                    data['materia'] = materia
                    return render(request, 'adm_alternativatitulacion/editmateria.html', data)
                except Exception as ex:
                    pass

            elif action == 'deletemateria':
                try:
                    data['title'] = u'Eliminar materia'
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    data['materia'] = materia
                    data['alternativa'] = materia.alternativa_id
                    return render(request, "adm_alternativatitulacion/deletemateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'eliminarasignacionasignatura':
                try:
                    data['title'] = u'Eliminar asignación  de asignatura'
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    data['materia'] = materia
                    data['alternativa'] = materia.alternativa.id
                    return render(request, "adm_alternativatitulacion/eliminarasignacionasignatura.html", data)
                except Exception as ex:
                    pass

            elif action == 'abrir':
                try:
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    materia.cerrado = False
                    materia.save(request)
                    log(u"Abrio materia de curso: %s" % materia, request, "open")
                    return HttpResponseRedirect('/adm_alternativatitulacion?action=materias&alt=' + str(materia.alternativa_id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'cerrar':
                try:
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    materia.cerrado = True
                    materia.save(request)
                    # for materiaasignada in materia.materiaasignadacurso_set.all():
                    #     materiaasignada.cierre_materia_asignada()
                    log(u"Cerro materia de curso: %s" % materia, request, "close")
                    return HttpResponseRedirect('/adm_alternativatitulacion?action=materias&alt=' + str(materia.alternativa_id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass
            # -----------HORARIOS------------------
            elif action == 'horario':
                try:
                    data['title'] = u'Horario'
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    data['materia'] = materia
                    data['alternativa'] = materia.alternativa_id
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    # data['turnos'] = materia.alternativa.get_sesion().sesion.turno_set.filter(pk__gte= 108) if materia.alternativa.get_sesion() else None
                    # data['turnos'] = turnos = materia.sesion.turno_set.all()
                    data['turnos'] = turnos = Turno.objects.filter(mostrar=True, status=True)
                    return render(request, "adm_alternativatitulacion/viewhorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addclase':
                try:
                    data['materia'] = materia = ComplexivoMateria.objects.get(pk=request.GET['materia'])
                    turno = request.GET['turno']
                    dia = request.GET['dia']
                    clase = ComplexivoClase()
                    clase.materia = materia
                    clase.turno_id = turno
                    clase.dia = dia
                    clase.fechainicio = materia.fechainicio
                    clase.fechafin = materia.fechafin
                    clase.save(request)
                    return HttpResponseRedirect('/adm_alternativatitulacion?action=horario&id=' + str(materia.id))
                except Exception as ex:
                    pass

            elif action == 'editclase':
                try:
                    data['title'] = u'Editar clase'
                    clase = ComplexivoClase.objects.get(pk=request.GET['id'])
                    if clase.tiene_aula():
                        form = ComplexivoClaseForm(initial={'aula': clase.aula})
                    else:
                        form = ComplexivoClaseForm()
                    data['form'] = form
                    data['action'] = 'editclase'
                    data['clase'] = clase.id
                    data['turno'] = clase.turno_id
                    data['dia'] = clase.dia
                    data['materia'] = ComplexivoMateria.objects.get(pk=clase.materia_id)
                    return render(request, "adm_alternativatitulacion/addclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteclase':
                try:
                    clase = ComplexivoClase.objects.get(pk=request.GET['id'])
                    if not clase.tiene_lecciones():
                        clase.delete()
                    else:
                        clase.activo = False
                        clase.save(request)
                    log(u"Elimino clase: %s" % clase, request, "delete")
                    return HttpResponseRedirect('/adm_alternativatitulacion?action=horario&id=' + str(clase.materia_id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'addaula':
                try:
                    data['title'] = u"Añadir Aula a la Asignatura"
                    data['materia'] = materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    data['alternativa'] = materia.alternativa_id
                    form = ComplexivoClaseForm(initial={'aula':materia.complexivoclase_set.filter(status=True).distinct('aula')[0].aula})
                    data['form'] = form
                    return render(request, "adm_alternativatitulacion/addaula.html", data)
                except Exception as ex:
                    pass

            elif action == 'right':
                try:
                    clase = ComplexivoClase.objects.get(pk=request.GET['id'])
                    materia = clase.materia
                    sesion = clase.materia.sesion
                    for i in range(clase.dia + 1, 7):
                        if materia.completo_horas_semanales():
                            break
                        if sesion.dia_habilitado(i):
                            if not clase.materia.complexivoclase_set.filter(dia=i, turno=clase.turno).exists():
                                clase_clon = ComplexivoClase(materia=clase.materia,
                                                             turno=clase.turno,
                                                             fechainicio=clase.fechainicio,
                                                             fechafin=clase.fechafin,
                                                             aula=clase.aula,
                                                             dia=i,
                                                             activo=True)
                                clase_clon.save(request)
                    return HttpResponseRedirect('/adm_alternativatitulacion?action=horario&id=' + str(clase.materia_id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass
            # ---------------EXAMEN COMPLEXIVO------------------
            elif action == 'examen':
                try:
                    data['title'] = u'Examen Complexivo'
                    data['alternativa'] = alternativa = AlternativaTitulacion.objects.get(pk=request.GET['alt'])
                    data['examenes'] = alternativa.complexivoexamen_set.filter(status=True)
                    return render(request, "adm_alternativatitulacion/viewexamen.html", data)
                except Exception as ex:
                    pass

            elif action == 'addexamen':
                try:
                    data['title'] = u"Añadir Examen Complexivo"
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=request.GET['alt'])
                    form = ComplexivoExamenForm()
                    form.cronograma_normal()
                    data['form'] = form
                    return render(request, "adm_alternativatitulacion/addexamen.html", data)
                except Exception as ex:
                    pass

            elif action == 'editexamen':
                try:
                    data['title'] = u"Editar Examen Complexivo"
                    data['examen']=examen=ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    form = ComplexivoExamenForm(initial={
                        'profesor':examen.docente.id,
                        'aula':examen.aula,
                        'horainicio':str(examen.horainicio),
                        'horafin':str(examen.horafin),
                        'notaminima': examen.notaminima,
                        'fechaexamen':examen.fechaexamen,
                        'horainiciorecuperacion': str(examen.horainiciorecuperacion),
                        'horafinrecuperacion': str(examen.horafinrecuperacion),
                        'fechaexamenrecuperacion': examen.fechaexamenrecuperacion
                    })
                    form.fields['profesor'].widget.attrs['descripcion'] = examen.docente
                    form.fields['profesor'].widget.attrs['value'] = examen.docente.id
                    data['form']=form
                    return render(request, "adm_alternativatitulacion/editexamen.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteexamen':
                try:
                    data['examen'] =  examen = ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['title'] = u'Eliminar examen'
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    return render(request, "adm_alternativatitulacion/delexamen.html", data)
                except Exception as ex:
                    pass

            elif action == 'diasacalificar':
                try:
                    data['title'] = u'Dias para calificar'
                    examen = ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    data['examen'] = examen
                    data['form'] = ComplexivoCalificacionDiaForm(initial={
                        'usacronograma' : examen.usacronograma,
                        'diasacalificar' : examen.diascalificar
                    })
                    return render(request, "adm_alternativatitulacion/diasacalificar.html", data)
                except Exception as ex:
                    pass

            elif action == 'calificaciones':
                try:
                    data['title'] = u'Examen complexivo'
                    examen = ComplexivoExamen.objects.get(pk=request.GET['id'])
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=examen.alternativa_id)
                    data['examen'] = examen
                    data['estudiantes'] = examen.complexivoexamendetalle_set.all().order_by('matricula__inscripcion')
                    return render(request, "adm_alternativatitulacion/calificaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'addexamenadicional':
                try:
                    data['title'] = u'Examen Adicional'
                    data['alt'] = AlternativaTitulacion.objects.get(status=True, pk=int(request.GET['ida']))
                    data['cronograma'] = CronogramaAdicionalExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    form = ComplexivoExamenForm()
                    form.cronograma_adicional()
                    data['form'] = form
                    return render(request, "adm_alternativatitulacion/addexamenadicional.html", data)
                except Exception as ex:
                    pass

            elif action == 'editexamenadicional':
                try:
                    data['title'] = u'Editar Examen Adicional'
                    data['alt'] = AlternativaTitulacion.objects.get(status=True, pk=int(request.GET['ida']))
                    data['examen'] = examen = ComplexivoExamen.objects.get(pk=int(request.GET['id']))
                    form = ComplexivoExamenForm(initial={'aula':examen.aula,
                                                         'profesor':examen.docente.id,
                                                         'fechaexamen':examen.fechaexamen,
                                                         'horainicio':examen.horainicio,
                                                         'horafin':examen.horafin,
                                                         'notaminima':examen.notaminima})
                    form.cronograma_adicional()
                    form.editar_crongrama_adicional(examen)
                    data['form'] = form
                    return render(request, "adm_alternativatitulacion/editexamenadicional.html", data)
                except Exception as ex:
                    pass

            #------------------------------REPORTE EXAMEN COMPLEXIVO-----------------------
            elif action == 'prueba':
                try:
                    examen = ComplexivoExamen.objects.get(status=True, id=int(request.GET['id']))
                    opcion = request.GET['opcion']
                    if opcion == 'actaexamen' or opcion == 'nominaexamen':
                        if ComplexivoExamenDetalle.objects.filter(examen=examen.id).exists():
                            return JsonResponse({"result": "ok"})
                    elif ComplexivoExamenDetalle.objects.filter(examen=examen.id,calificacion__lt=examen.notaminima).exists():
                        return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "bad", "mensaje": "No existen alumnos para este reporte"})
                except Exception as ex:
                    pass

            elif action == 'detalleexamen':
                try:
                    data['title'] = u'Curso complexivo'
                    data['persona'] = persona
                    data['matricula'] = matricula = MatriculaTitulacion.objects.get(Q(pk=int(request.GET['idm'])), (Q(estado=1) | Q(estado=10) | Q(estado=9)))
                    data['inscripcion'] = matricula.inscripcion
                    data['alternativa'] = matricula.alternativa
                    data['materias'] = matricula.alternativa.complexivomateria_set.filter(status=True).order_by('fechainicio')
                    data['archivos'] = ArchivoTitulacion.objects.filter(vigente=True, tipotitulacion__tipo=2)
                    pexamen = 0
                    ppropuesta = 0
                    if matricula.alternativa.cronogramaexamencomplexivo_set.exists():
                        if matricula.alternativa.cronogramaexamencomplexivo_set.get().fechaeleccionpropuestafin != None and matricula.alternativa.cronogramaexamencomplexivo_set.get().fechaeleccionpropuestainicio != None:
                            if datetime.now().date() <= matricula.alternativa.cronogramaexamencomplexivo_set.get().fechaeleccionpropuestafin and datetime.now().date() >= matricula.alternativa.cronogramaexamencomplexivo_set.get().fechaeleccionpropuestainicio:
                                data['disponible'] = True
                            if datetime.now().date() >= matricula.alternativa.cronogramaexamencomplexivo_set.get().fechaeleccionpropuestainicio:
                                data['disponibleinicio'] = True
                    if matricula.alternativa.tiene_examen():
                        data['examen'] = examen = matricula.alternativa.complexivoexamen_set.filter(status=True, complexivoexamendetalle__estado=3, complexivoexamendetalle__status=True).order_by('-id')[0]
                        data['detalleexamen'] = detalle = examen.complexivoexamendetalle_set.filter(matricula=matricula, status=True)
                        if detalle.exists():
                            data['detalleexamen'] = detalle = detalle.get(matricula=matricula)
                        else:
                            detalle = ComplexivoExamenDetalle(examen=examen, matricula=matricula)
                            detalle.save(request)
                            log(u"Se creo un detalle de examen complexivo porque no existia %s - [%s] idalter: %s ---creado: %s" % (matricula, examen, matricula.alternativa.id, detalle), request, "delete")
                        pexamen = detalle.ponderacion()
                    if ComplexivoGrupoTematica.objects.filter(status=True, complexivodetallegrupo__status=True, complexivodetallegrupo__matricula=matricula).exists():
                        data['grupo'] = grupo = ComplexivoGrupoTematica.objects.get(status=True, complexivodetallegrupo__status=True, complexivodetallegrupo__matricula=matricula)
                        data['companeros'] = grupo.complexivodetallegrupo_set.filter(Q(status=True), (Q(matricula__estado=1) | Q(matricula__estado=10) | Q(matricula__estado=9))).exclude(matricula=matricula)
                        data['confirmar'] = grupo.complexivodetallegrupo_set.filter(status=True, estado=4, matricula=matricula).exists()
                        data['tipoarchivo'] = TIPO_ARCHIVO_COMPLEXIVO_PROPUESTA
                        data['propuestas'] = grupo.complexivopropuestapractica_set.filter(status=True).order_by('id')
                        ppropuesta = matricula.notapropuesta()
                    data['pexamen'] = pexamen
                    data['ppropuesta'] = ppropuesta
                    data['ptotal'] = matricula.notafinalcomplexivo()
                    data['modelos'] = matricula.alternativa.modelo_alternativatitulacion_set.filter(status=True).order_by('modelo__nombre')
                    return render(request, "adm_alternativatitulacion/viewcurso.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalle':
                try:
                    data['grupo'] = grupo = ComplexivoGrupoTematica.objects.get(pk=request.GET['ida'],status=True)
                    data['tematica'] = grupo.tematica
                    data['idalum'] = MatriculaTitulacion.objects.get(pk=int(request.GET['idm']), status=True).inscripcion
                    data['grupos'] = ComplexivoGrupoTematica.objects.filter(pk__in=ComplexivoDetalleGrupo.objects.values_list("grupo__id", flat=False).filter(matricula_id=int(request.GET['idm']), grupo__complexivoacompanamiento__isnull=False).distinct())
                    data['detalles'] = grupo.complexivoacompanamiento_set.filter(status=True).order_by('id')
                    template = get_template("adm_alternativatitulacion/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            #--------------------------CRONOGRAMA DE TITULACION------------------------------
            elif action == 'nucleoconocimiento':
                try:
                    data['title'] = u'Editar Nucleo Conocimiento'
                    data['cronograma'] = cronograma=CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    data['form'] = CronogramaNucleoConocimientoComplexivoForm(initial={
                        'fechanucleobasicoinicio' : cronograma.fechanucleobasicoinicio,
                        'fechanucleoproffin': cronograma.fechanucleoproffin
                    })
                    return render(request, "adm_cronogramatitulacion/complexivonucleoconocimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobacionexamen':
                try:
                    data['title'] = u'Cronograma Aprobacion Examen Complexivo'
                    data['cronograma'] = cronograma=CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    form = CronogramaAprobacionExamenComplexivoForm(initial={
                        'fechaaprobexameninicio': cronograma.fechaaprobexameninicio,
                        'fechaaprobexamenfin':cronograma.fechaaprobexamenfin,
                        'fechaaprobexamengraciainicio':cronograma.fechaaprobexamengraciainicio,
                        'fechaaprobexamengraciafin': cronograma.fechaaprobexamengraciafin,
                        'fechasubircalificacionesinicio':cronograma.fechasubircalificacionesinicio,
                        'fechasubircalificacionesfin': cronograma.fechasubircalificacionesfin
                        # 'fechasubircalificacionesgraciainicio': cronograma.fechasubircalificacionesgraciainicio,
                        # 'fechasubircalificacionesgraciafin': cronograma.fechasubircalificacionesgraciafin
                    })
                    form.quitar_campos()
                    data['form'] = form
                    return render(request, "adm_cronogramatitulacion/complexivoaprobacionexamen.html", data)
                except Exception as ex:
                    pass

            elif action == 'propuestapractica':
                try:
                    data['title'] = u'Adicionar cronograma de trabajo titulación'
                    data['cronograma'] = cronograma = CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    data['form'] = CronogramaPropuestaPracticaComplexivoForm(initial={'fechaeleccionpropuestainicio':cronograma.fechaeleccionpropuestainicio,
                                                                                      'fechaeleccionpropuestafin':cronograma.fechaeleccionpropuestafin,
                                                                                      'fechapropuestainicio':cronograma.fechapropuestainicio,
                                                                                      'fechapropuestafin':cronograma.fechapropuestafin,
                                                                                      'fechadefensaevaluacioninicio':cronograma.fechardefensaevaluacioninicio,
                                                                                      'fechadefensaevaluacionfin':cronograma.fechardefensaevaluacionfin})
                    return render(request, "adm_cronogramatitulacion/complexivopropuestapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'revisionestudiante':
                try:
                    data['title'] = u'Cronograma Revisión Propuesta Práctica'
                    data['cronograma'] = CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    data['form'] = CronogramaRevisionEstudianteComplexivoForm()
                    return render(request, "adm_cronogramatitulacion/complexivorevisionestudiante.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrevision':
                try:
                    data['title'] = u'Cronograma Revisión Propuesta Práctica'
                    data['revision'] = revision = DetalleRevisionCronograma.objects.get(pk=int(request.GET['id']))
                    data['cronograma'] = revision.cronograma
                    data['form'] = CronogramaRevisionEstudianteComplexivoForm(initial={
                        'fechafin': revision.fechafin,
                        'fechainicio': revision.fechainicio,
                        'calificacionfin': revision.calificacionfin,
                        'calificacioninicio': revision.calificacioninicio
                    })
                    return render(request, "adm_cronogramatitulacion/editcomplexivorevisionestudiante.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleterevision':
                try:
                    data['title'] = u"Eliminar Revisión"
                    revision = DetalleRevisionCronograma.objects.get(pk=request.GET['id'])
                    data['mensaje'] = u"Esta seguro de eliminar la revisión: %s" % (request.GET['no'])
                    data['revision'] = revision
                    data['cronograma'] = revision.cronograma
                    return render(request, "adm_cronogramatitulacion/deleterevision.html", data)
                except Exception as ex:
                    pass

            elif action == 'examencomplexivo':
                try:
                    data['title'] = u'Cronograma de obtención de título'
                    data['cronograma'] = cronograma = CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    data['revisiones'] = cronograma.detallerevisioncronograma_set.filter(status=True).order_by('id')
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=cronograma.alternativatitulacion_id)
                    return render(request, "adm_cronogramatitulacion/viewexamencomplexivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'cronograma_masivo':
                try:
                    data['title'] = u'Cronograma de obtención de título'
                    data['grupotitulacion'] = grupo = GrupoTitulacion.objects.get(pk=request.GET['idg'], status=True)
                    data['carrera'] = Carrera.objects.get(pk=request.GET['idc'])
                    data['tipotitulacion'] = TipoTitulaciones.objects.get(status=True, pk=int(request.GET['idt']))
                    return render(request, "adm_alternativatitulacion/cronogramamasivo.html", data)
                except Exception as ex:
                    pass
            #---------------------PPERIPDO DE TITULACION-------------------------------
            elif action == 'addperiodo':
                try:
                    data['title'] = u'Adicionar Periodo de Titulación'
                    data['form'] = PeriodoGrupoTitulacionForm()
                    return render(request, "adm_periodotitulacion/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'delperiodo':
                try:
                    data['title'] = u'Eliminar Periodo de Titulación'
                    data['periodo'] = PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_periodotitulacion/eliminar.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodo':
                try:
                    data['title'] = u'Editar Periodo de Titulación'
                    data['periodo'] = periodo = PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    form = PeriodoGrupoTitulacionForm(
                        initial={'nombre': periodo.nombre, 'descripcion': periodo.descripcion,
                                 'fechainicio': periodo.fechainicio, 'fechafin': periodo.fechafin,
                                 'plagio': periodo.porcentajeurkund, 'nrevision': periodo.nrevision})
                    # if periodo.tiene_grupo_activo():
                    # if not periodo.abierto:
                    #     form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_periodotitulacion/editar.html", data)
                except Exception as ex:
                    pass

            elif action == 'archivoperiodo':
                try:
                    data['title'] = u'Archivos de Titulación'
                    data['archivos'] = ArchivoTitulacion.objects.filter(status=True).order_by("nombre")
                    return render(request, "adm_periodotitulacion/viewarchivos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarchivoperiodo':
                try:
                    data['title'] = u'Adicionar Archivo de Titulación'
                    form = ArchivosTitulacionForm()
                    form.ocultar()
                    data['form'] = form
                    return render(request, "adm_periodotitulacion/addarchivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarchivoperiodo':
                try:
                    data['archivo'] = archivo = ArchivoTitulacion.objects.get(pk=request.GET['id'])
                    data['title'] = u'Editar Archivo de Titulación'
                    form = ArchivosTitulacionForm(initial={
                        'nombre': archivo.nombre
                        # 'tipotitulacion': archivo.tipotitulacion
                    })
                    form.ocultar()
                    data['form'] = form
                    return render(request, "adm_periodotitulacion/editarchivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delarchivoperiodo':
                try:
                    data['title'] = u'Eliminar Archivo de Titulación'
                    data['archivo'] = ArchivoTitulacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodotitulacion/deletearchivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'periodotitulacion':
                try:
                    data['title'] = u'Periodo de Titulación'
                    data['periodos'] = PeriodoGrupoTitulacion.objects.filter(status=True).order_by('-id')
                    return render(request, "adm_periodotitulacion/view.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass
            #--------------------------MODELO DE TITULACION---------------------------------------
            elif action == 'addmodelotitulacion':
                try:
                    data['title'] = u'Modelo de Titulación'
                    data['form'] = ModeloTitulacionForm()
                    return render(request, "adm_modelotitulacion/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmodelotitulacion':
                try:
                    data['title'] = u'Editar Modelo de Titulación'
                    data['modelo'] = modelo = ModeloTitulacion.objects.get(pk=int(request.GET['id']))
                    form = ModeloTitulacionForm(initial={'nombre': modelo.nombre,
                                                         'horaspresencial': modelo.horaspresencial,
                                                         'horasvirtual': modelo.horasvirtual,
                                                         'horasautonoma': modelo.horasautonoma,
                                                         'clases': modelo.clases,
                                                         'acompanamiento': modelo.acompanamiento,
                                                         'activo': modelo.activo
                                                         })
                    if modelo.tiene_alternativa_activas():
                        form.editar()
                    data['form'] = form
                    return render(request, "adm_modelotitulacion/editar.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmodelotitulacion':
                try:
                    data['title'] = u'Eliminar Modelo de Titulación'
                    data['modelo'] = ModeloTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_modelotitulacion/eliminar.html", data)
                except Exception as ex:
                    pass

            elif action == 'modelotitulacion':
                try:
                    data['title'] = u'Modelo de Titulación'
                    data['modelo'] = ModeloTitulacion.objects.filter(status=True).order_by('nombre')
                    return render(request, "adm_modelotitulacion/view.html", data)
                except Exception as ex:
                    pass

            elif action == 'detallematriculadoultimo':
                try:
                    from bd.models import FuncionRequisitoIngresoUnidadIntegracionCurricular
                    aData = {}
                    data['nombrereq'] = request.GET['nombrereq']
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    mimalla = inscripcion.mi_malla()
                    minivel = NivelMalla.objects.filter(status=True, asignaturamalla__malla=mimalla).order_by('-orden').first()
                    idasignaturaoptativas = AsignaturaMalla.objects.values_list('asignatura__id', flat=False).filter(status=True, ejeformativo_id=4, malla=mimalla, nivelmalla__orden__lte=minivel.orden)

                    idasigrecord = inscripcion.recordacademico_set.values_list('asignatura__id', flat=False).filter(status=True, aprobada=True).exclude(asignatura__id__in=idasignaturaoptativas)
                    asigultimo = AsignaturaMalla.objects.filter(status=True, malla=mimalla, opcional=False, nivelmalla__orden__gte=minivel.orden).exclude(asignatura__id__in=idasigrecord)
                    xyz = [num for num in [1, 2, 3] if num != inscripcion.itinerario]  # exclusión de itinerario
                    asigultimo = asigultimo.exclude(itinerario__in=xyz)
                    asigpendiente = AsignaturaMalla.objects.filter(status=True, malla=mimalla, opcional=False).exclude(asignatura__id__in=idasigrecord).exclude(nivelmalla__orden=minivel.orden)
                    data['asigultimo'] = matriasigultimo = asigultimo.distinct() | asigpendiente.distinct()
                    data['mate_matriculadas'] = MateriaAsignada.objects.values_list('materia__asignaturamalla_id', flat=True).filter(status=True, retiramateria=False, matricula__inscripcion=inscripcion, materia__asignaturamalla__id__in=matriasigultimo.values('id'))
                    data['cumplereq'] = inscripcion.esta_matriculado_ultimo_nivel()
                    data['descrip_penultimo'] = FuncionRequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, funcion=2).values('nombre').first()
                    data['aprobo_asta_penultimo_malla'] = inscripcion.aprobo_asta_penultimo_malla()
                    template = get_template("adm_alternativatitulacion/modal/requisitomatriculadoultimo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'detallepracprofesionales':
                try:
                    aData = {}
                    data['nombrereq'] = request.GET['nombrereq']
                    data['idnivelmateria'] = int(request.GET['idnivelmateria'])
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    aData['estado_sistema'] = 2
                    data['practicas'] = PracticasPreprofesionalesInscripcion.objects.filter(culminada=True, status=True, inscripcion=inscripcion)
                    totalhoras = 0
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True, culminada=True)
                    malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
                    data['malla_horas_practicas'] = malla.horas_practicas
                    excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
                    fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()
                    if fechainicioprimernivel > excluiralumnos:
                        if practicaspreprofesionalesinscripcion.exists():
                            for practicas in practicaspreprofesionalesinscripcion:
                                if practicas.tiposolicitud == 3:
                                    totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
                                else:
                                    totalhoras += practicas.numerohora
                            if totalhoras >= malla.horas_practicas:
                                data['practicaspreprofesionales'] = True
                                aData['estado_sistema'] = 1
                        data['practicaspreprofesionalesvalor'] = totalhoras
                    else:
                        data['practicaspreprofesionales'] = True
                        aData['estado_sistema'] = 1
                        data['practicaspreprofesionalesvalor'] = malla.horas_practicas
                    data['listadoitinerariomalla'] = listadoitinerariomalla = malla.itinerariosmalla_set.filter(status=True)
                    data['totalitinerariomalla'] = listadoitinerariomalla.aggregate(total=Sum('horas_practicas'))['total']
                    template = get_template("adm_alternativatitulacion/modal/requisitopracpreprofesionales.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'detalleingles':
                try:
                    aData = {}
                    data['nombrereq'] = request.GET['nombrereq']
                    aData['estado_sistema'] = 2
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    malla_ids = [22]
                    malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
                    asignaturas_modulo = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla__id__in=malla_ids)
                    records1 = inscripcion.recordacademico_set.filter(status=True, asignatura__id__in=asignaturas_modulo).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_horas'] = null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignatura__id__in=asignaturas_modulo).aggregate(horas=Sum('horas'))['horas'])
                    data['total_creditos'] = null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignatura__id__in=asignaturas_modulo).aggregate(creditos=Sum('creditos'))['creditos'])
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True, status=True, asignatura__id__in=asignaturas_modulo).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True, status=True, asignatura__id__in=asignaturas_modulo).count()

                    modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
                    records2 = inscripcion.recordacademico_set.filter(asignatura_id__in=modulo_ingles.values('asignatura_id'), aprobada=True)
                    data['records'] = records1 | records2
                    numero_modulo_ingles = modulo_ingles.count()
                    lista = []
                    listaid = []
                    for modulo in modulo_ingles:
                        if inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
                            lista.append(modulo.asignatura.nombre)
                            listaid.append(modulo.asignatura.id)
                    data['modulo_ingles_aprobados'] = lista
                    data['modulo_ingles_faltante'] = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid])
                    if numero_modulo_ingles >0:
                        if numero_modulo_ingles == len(listaid):
                            data['modulo_ingles'] = True
                            aData['estado_sistema'] = 1
                    template = get_template("adm_alternativatitulacion/modal/requisitoingles.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'detallecomputacion':
                try:
                    aData = {}
                    data['nombrereq'] = request.GET['nombrereq']
                    aData['estado_sistema'] = 2
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    malla_ids = [32]
                    malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
                    asignaturas_modulo = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla__id__in=malla_ids)
                    data['records'] = inscripcion.recordacademico_set.filter(status=True, asignatura__id__in=asignaturas_modulo).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_horas'] = null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignatura__id__in=asignaturas_modulo).aggregate(horas=Sum('horas'))['horas'])
                    data['total_creditos'] = null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignatura__id__in=asignaturas_modulo).aggregate(creditos=Sum('creditos'))['creditos'])
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True, status=True, asignatura__id__in=asignaturas_modulo).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True, status=True, asignatura__id__in=asignaturas_modulo).count()

                    computacion_asignatura_ids = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
                    data['record_computacion'] = record = inscripcion.recordacademico_set.filter(asignatura__id__in=computacion_asignatura_ids, aprobada=True)
                    creditos_computacion = 0
                    data['malla_creditos_computacion'] = malla.creditos_computacion
                    for comp in record:
                        creditos_computacion += comp.creditos
                    if creditos_computacion >= malla.creditos_computacion:
                        data['computacion'] = True
                        aData['estado_sistema'] = 1
                    data['creditos_computacion'] = creditos_computacion
                    template = get_template("adm_alternativatitulacion/modal/requisitocomputacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'detallevinculacion':
                try:
                    aData = {}
                    data['idnivelmateria'] = int(request.GET['idnivelmateria'])
                    data['nombrereq'] = request.GET['nombrereq']
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
                    aData['estado_sistema'] = 2
                    data['malla_horas_vinculacion'] = malla.horas_vinculacion
                    horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, inscripcion_id=inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
                    horastotal = horastotal if horastotal else 0
                    excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
                    fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()
                    if fechainicioprimernivel > excluiralumnos:
                        if horastotal >= malla.horas_vinculacion:
                            data['vinculacion'] = True
                            aData['estado_sistema'] = 1
                        data['horas_vinculacion'] = horastotal
                    else:
                        data['horas_vinculacion'] = malla.horas_vinculacion
                        data['vinculacion'] = True
                        aData['estado_sistema'] = 1
                    data['vinculaciones'] = inscripcion.mis_proyectos_vinculacion()
                    data['listadoitinerariomalla'] = listadoitinerariomalla = malla.itinerariosvinculacionmalla_set.filter(status=True)
                    data['totalitinerariomalla'] = listadoitinerariomalla.aggregate(total=Sum('horas_vinculacion'))['total']
                    template = get_template("adm_alternativatitulacion/modal/requisitovinculacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'noadeudar':
                try:
                    aData = {}
                    data['nombrereq'] = request.GET['nombrereq']
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    aData['estado_sistema'] = 2
                    data['cliente'] = cliente = inscripcion.persona
                    rubrosnocancelados = cliente.rubro_set.filter(cancelado=False, status=True).order_by('cancelado', 'fechavence')
                    rubroscanceldos = cliente.rubro_set.filter(cancelado=True, status=True).order_by('fechavence')
                    rubros = list(chain(rubrosnocancelados, rubroscanceldos))
                    data['rubros'] = rubros
                    data['tiene_nota_debito'] = RubroNotaDebito.objects.filter(rubro__persona=cliente, rubro__cancelado=False).exists()
                    if inscripcion.adeuda_a_la_fecha() == 0:
                        data['deudas'] = True
                        aData['estado_sistema'] = 1
                    data['deudasvalor'] = inscripcion.adeuda_a_la_fecha()
                    template = get_template("adm_alternativatitulacion/modal/requisitofinanzas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'aprobaringlesdirector':
                try:
                    cumpleingles = False
                    data['nombrereq'] = request.GET['nombrereq']
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    IDIOMAS = [1, 5, 8]  # INGLES, FRANCES, QUICHUA
                    data['certificaciones'] = inscripcion.persona.certificadoidioma_set.filter(status=True, idioma_id__in=IDIOMAS)
                    data['cumpleingles'] = tiene_certificacion_segunda_lengua_aprobado_director_carrera(inscripcion.id)
                    template = get_template("adm_alternativatitulacion/modal/requisitoinglesapdirector.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'detallemallaaprobada':
                try:
                    aData = {}
                    data['nombrereq'] = request.GET['nombrereq']
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    asignaturas_modulo = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla__id__in=[22, 32])
                    data['records'] = inscripcion.recordacademico_set.filter(status=True).exclude(asignatura__id__in=asignaturas_modulo).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_creditos'] = inscripcion.total_creditos()
                    data['total_creditos_malla'] = inscripcion.total_creditos_malla()
                    data['total_creditos_modulos'] = inscripcion.total_creditos_modulos()
                    data['total_creditos_otros'] = inscripcion.total_creditos_otros()
                    data['total_horas'] = inscripcion.total_horas()
                    data['promedio'] = inscripcion.promedio_record()
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True).exclude(asignatura__id__in=asignaturas_modulo).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True).exclude(asignatura__id__in=asignaturas_modulo).count()
                    data['inscripcion_malla'] = inscripcionmalla = inscripcion.malla_inscripcion()
                    data['malla'] = malla = inscripcionmalla.malla
                    data['nivelesdemallas'] = nivelmalla = NivelMalla.objects.all().order_by('id')
                    listadoasignaturamalla = AsignaturaMalla.objects.filter(malla=malla).exclude(tipomateria_id=3)
                    data['ejesformativos'] = EjeFormativo.objects.filter(pk__in=listadoasignaturamalla.values_list('ejeformativo_id')).order_by('nombre')
                    listas_asignaturasmallas = []
                    for x in listadoasignaturamalla.exclude(ejeformativo_id=4):
                        listas_asignaturasmallas.append([x, inscripcion.aprobadaasignatura(x)])

                    for ni in nivelmalla:
                        listadooptativa = listadoasignaturamalla.filter(nivelmalla=ni, ejeformativo_id=4)
                        if inscripcion.recordacademico_set.filter(asignatura__in=listadooptativa.values_list('asignatura__id', flat=True)).exists():
                            for d in listadooptativa:
                                if inscripcion.aprobadaasignatura(d):
                                    listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                        else:
                            for d in listadooptativa:
                                listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                    data['asignaturasmallas'] = listas_asignaturasmallas
                    resumenniveles = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)} for x in NivelMalla.objects.all().order_by('id')]
                    data['resumenes'] = resumenniveles

                    # total_materias_malla = malla.cantidad_materiasaprobadas()
                    cantidadmalla = inscripcion.cantidad_asig_aprobar_ultimo_malla()
                    cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
                    # poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
                    poraprobacion = round(cantidad_materias_aprobadas_record * 100 / cantidadmalla, 0)
                    data['mi_nivel'] = nivel = inscripcion.mi_nivel()
                    inscripcionmalla = inscripcion.malla_inscripcion()
                    niveles_maximos = inscripcionmalla.malla.niveles_regulares

                    if poraprobacion >= 100:
                        data['nivel'] = True
                        aData['estado_sistema'] = 1
                    else:
                        aData['estado_sistema'] = 2
                        if niveles_maximos == nivel.nivel.id:
                            data['septimo'] = True
                    template = get_template("adm_alternativatitulacion/modal/requisitomallaaprobada.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'detallemallapenultimoaprobada':
                try:
                    aData = {}
                    data['nombrereq'] = request.GET['nombrereq']
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.GET['id']))
                    asignaturas_modulo = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla__id__in=[22, 32])
                    data['records'] = inscripcion.recordacademico_set.filter(status=True).exclude(asignatura__id__in=asignaturas_modulo).order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['total_creditos'] = inscripcion.total_creditos()
                    data['total_creditos_malla'] = inscripcion.total_creditos_malla()
                    data['total_creditos_modulos'] = inscripcion.total_creditos_modulos()
                    data['total_creditos_otros'] = inscripcion.total_creditos_otros()
                    data['total_horas'] = inscripcion.total_horas()
                    data['promedio'] = inscripcion.promedio_record()
                    data['aprobadas'] = inscripcion.recordacademico_set.filter(aprobada=True, valida=True).exclude(asignatura__id__in=asignaturas_modulo).count()
                    data['reprobadas'] = inscripcion.recordacademico_set.filter(aprobada=False, valida=True).exclude(asignatura__id__in=asignaturas_modulo).count()
                    data['inscripcion_malla'] = inscripcionmalla = inscripcion.malla_inscripcion()
                    data['malla'] = malla = inscripcionmalla.malla
                    data['nivelesdemallas'] = nivelmalla = NivelMalla.objects.all().order_by('id')
                    listadoasignaturamalla = AsignaturaMalla.objects.filter(malla=malla).exclude(tipomateria_id=3)
                    data['ejesformativos'] = EjeFormativo.objects.filter(pk__in=listadoasignaturamalla.values_list('ejeformativo_id')).order_by('nombre')
                    listas_asignaturasmallas = []
                    for x in listadoasignaturamalla.exclude(ejeformativo_id=4):
                        listas_asignaturasmallas.append([x, inscripcion.aprobadaasignatura(x)])

                    for ni in nivelmalla:
                        listadooptativa = listadoasignaturamalla.filter(nivelmalla=ni, ejeformativo_id=4)
                        if inscripcion.recordacademico_set.filter(asignatura__in=listadooptativa.values_list('asignatura__id', flat=True)).exists():
                            for d in listadooptativa:
                                if inscripcion.aprobadaasignatura(d):
                                    listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                        else:
                            for d in listadooptativa:
                                listas_asignaturasmallas.append([d, inscripcion.aprobadaasignatura(d)])
                    data['asignaturasmallas'] = listas_asignaturasmallas
                    resumenniveles = [{'id': x.id, 'horas': x.total_horas(malla), 'creditos': x.total_creditos(malla)} for x in NivelMalla.objects.all().order_by('id')]
                    data['resumenes'] = resumenniveles

                    data['creditos'] = inscripcion.aprobo_asta_penultimo_malla()
                    data['cantasigaprobadas'] = inscripcion.cantidad_asig_aprobada_penultimo_malla()
                    data['cantasigaprobar'] = inscripcion.cantidad_asig_aprobar_penultimo_malla()
                    data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivel()
                    aData['estado_sistema'] = 1 if (inscripcion.aprobo_asta_penultimo_malla() and inscripcion.esta_matriculado_ultimo_nivel()) else 2
                    template = get_template("adm_alternativatitulacion/modal/requisitomallapenultimoaprobada.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    pass
            #-------------------------TIPO DE TITULACION --------------------------

            elif action == 'addtipotitulacion':
                try:
                    data['title'] = u'Adicionar Tipo Titulación'
                    data['form'] = TipoTitulacionForm()
                    return render(request, "adm_tipotitulacion/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittipotitulacion':
                try:
                    data['title'] = u'Editar Tipo de Titulación'
                    data['tipo'] = tipo = TipoTitulaciones.objects.get(pk=int(request.GET['id']))
                    form = TipoTitulacionForm(initial={'nombre': tipo.nombre,
                                                       'codigo': tipo.codigo,
                                                       'caracteristica': tipo.caracteristica,
                                                       'tipo': tipo.tipo,
                                                       'rubrica': tipo.rubrica,
                                                       'mecanismotitulacion':tipo.mecanismotitulacion})
                    if tipo.tiene_alternativa_activas():
                        form.editar()
                    data['form'] = form
                    return render(request, "adm_tipotitulacion/editar.html", data)
                except Exception as ex:
                    pass

            elif action == 'deltipotitulacion':
                try:
                    data['title'] = u'Eliminar Tipo Titulación'
                    data['tipo'] = TipoTitulaciones.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_tipotitulacion/eliminar.html", data)
                except Exception as ex:
                    pass

            elif action == 'combinartipotitulacion':
                try:
                    data['title'] = u'Combinar Tipo de Titulación'
                    data['tipo'] = tipo = TipoTitulaciones.objects.get(pk=int(request.GET['id']))
                    if CombinarTipoTitulaciones.objects.filter(tipotitulacion=tipo, status=True).exists():
                        combinar = CombinarTipoTitulaciones.objects.filter(tipotitulacion=tipo, status=True)
                        form = CombinarTipoTitulacionForm(initial={'tipo': tipo.nombre, 'carreras': Carrera.objects.filter(pk__in=[c.carrera.id for c in combinar])})
                        data['lista_carreras'] = combinar
                    else:
                        form = CombinarTipoTitulacionForm(initial={'tipo': tipo.nombre})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_tipotitulacion/combinar.html", data)
                except Exception as ex:
                    pass

            elif action == 'tipotitulacion':
                try:
                    data['title'] = u'Tipo de Titulación'
                    data['tipo'] = TipoTitulaciones.objects.filter(status=True).order_by('nombre')
                    return render(request, "adm_tipotitulacion/view.html", data)
                except Exception as ex:
                    pass

            elif action == 'selectgruposxperiodo':
                try:
                    if 'id' in request.GET:
                        lista = []
                        grupos = GrupoTitulacion.objects.filter(status=True, periodogrupo__id=int(request.GET['id']))
                        for grupo in grupos:
                            lista.append([grupo.id, grupo.facultad.nombre])
                        data = {"result": "ok", 'lista': lista}
                        return JsonResponse(data)
                except Exception as ex:
                    pass
            #-----------------------------REPORTE EN EXCEL---------------------
            elif action == 'actaexamen':
                try:
                    examen = ComplexivoExamen.objects.get(status=True, id=int(request.GET['id']))

                    __author__ = 'Unemi'
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte 1')
                    # hoja
                    fila = 1
                    ws.write_merge(fila, fila, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    # ws.write_merge(2, 2, 0, 8, 'VICERRECTORADO ACADÉMICO Y DE INVESTIGACIÓN', title)
                    # ws.write_merge(3, 3, 0, 8, 'GESTIÓN TÉCNICA ACADÉMICA', title)
                    # ws.write_merge(4, 4, 0, 8, 'PROCESO DE  TITULACIÓN', title)
                    fila += 1
                    ws.write_merge(fila, fila, 0, 6, 'ACTA DE CALIFICACIÓN', subtitle)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename =ACTA DE CALIFICACIONES ' + '.xls'
                    ws.col(0).width = 1000
                    ws.col(1).width = 5000
                    ws.col(2).width = 5000
                    # ws.col(3).width = 1300
                    ws.col(3).width = 2000
                    ws.col(4).width = 2000
                    ws.col(5).width = 2500
                    fila += 1
                    ws.write(fila, 0, 'INICIO: ' + str(examen.alternativa.grupotitulacion.fechainicio) +
                             ' FIN: ' + str(examen.alternativa.grupotitulacion.fechafin), subtitle)
                    ws.merge(fila, fila, 0, 6)
                    fila += 4
                    ws.write(fila, 0, str(examen.alternativa.facultad), nnormal)
                    ws.merge(fila, fila, 0, 2)
                    # ws.write(12, 3, 'EXAMEN COMPLEXIVO: '+str(examen.fechaexamen), nnormal)
                    # ws.merge(12, 12, 3, 8)
                    # ws.write(13, 3, 'EXAMEN GRACIA: '+str(examen.fechaexamenrecuperacion), nnormal)
                    # ws.merge(13, 13, 3, 8)
                    fila += 1
                    ws.write(fila, 0, 'CARRERA: ' + str(examen.alternativa.carrera), nnormal)
                    ws.merge(fila, fila, 0, 6)
                    fila += 1
                    ws.write(fila, 0, 'ALTERNATIVA DE TITULACIÓN: ' + str(examen.alternativa), nnormal)
                    ws.merge(fila, fila, 0, 6)
                    fila += 1
                    ws.write(fila, 0, 'PROFESOR: ' + str(examen.docente), nnormal)
                    ws.merge(fila, fila, 0, 2)
                    # ws.write(13, 0, 'PARALELO: ' + str(examen.alternativa.paralelo), nnormal)
                    # ws.merge(13, 13, 0, 2)
                    tiem = datetime.today().date()
                    ws.write(5, 0, 'Milagro, ' + (
                            str(tiem.day) + " de " + str(MESES_CHOICES[tiem.month - 1][1]).lower() + " del " + str(tiem.year)),
                             normaliz)
                    ws.merge(5, 5, 0, 6)
                    # LETRAS PEQUEÑAS
                    fila += 2
                    ws.write_merge(fila, fila, 3, 4, 'PT(PRUEBA TEORICA)', peque)
                    # ws.write_merge(16,16,3,4, 'EX2(GRACIA)', peque)
                    # ws.write_merge(15,15,5,7, 'N.FINAL(NOTA FINAL)', peque)
                    # ws.write_merge(16,16,5,7, 'POND(PONDERACION)', peque)
                    # cuadro
                    ws.write_merge(fila, fila, 0, 1, 'Evaluaciones Parciales', stylenotas)
                    fila += 1
                    ws.write_merge(fila, fila + 1, 0, 1, 'De: 1-100', stylenotas)
                    encabezado = fila + 3
                    ws.write(encabezado, 0, 'Nº', stylebnotas)
                    ws.write_merge(encabezado, encabezado, 1, 2, 'APELLIDOS Y NOMBRES', stylebnombre)
                    ws.write(encabezado, 3, 'PT', stylebnotas)
                    # ws.write(encabezado, 4, 'EX2', stylebnotas)
                    ws.write(encabezado, 4, 'N.FINAL', stylebnotas)
                    # ws.write(encabezado, 6, 'POND', stylebnotas)
                    ws.write(encabezado, 5, 'ESTADO', stylebnotas)
                    listamatriculados = ComplexivoExamenDetalle.objects.filter(examen=examen.id).order_by(
                        'matricula__inscripcion__persona__apellido1')
                    encabezado += 1
                    if listamatriculados.exists():
                        i = 0
                        for matriculados in listamatriculados:
                            fil = i + encabezado
                            ws.write(fil, 0, str(i + 1), stylenotas)
                            ws.write(fil, 1, u'%s - %s' % (
                                matriculados.matricula, matriculados.matricula.inscripcion.carrera.alias), normal)
                            ws.merge(fil, fil, 1, 2, normal)
                            # ws.write(fil, 3, str(matriculados.calificacion), stylenotas)
                            ws.write(fil, 3, str(matriculados.notafinal), stylenotas)
                            # ws.write(fil, 4, str(matriculados.calificacionrecuperacion), stylenotas)
                            ws.write(fil, 4, str(matriculados.notafinal), stylenotas)
                            # ws.write(fil, 6, str((matriculados.notafinal*50)/100), stylenotas)
                            ws.write(fil, 5, 'APROBADO' if matriculados.notafinal >= examen.notaminima else 'REPROBADO',
                                     stylenotas)
                            i = i + 1
                        ws.write_merge(fil + 5, fil + 5, 0, 2, '_______________________________________', subtitle)
                        ws.write(fil + 6, 0, str(examen.docente), subtitle)
                        ws.merge(fil + 6, fil + 6, 0, 2)
                        ws.write_merge(fil + 7, fil + 7, 0, 2, 'DIRECTOR DE CARRERA', subtitle)
                        ws.write_merge(fil + 5, fil + 5, 3, 6, '_______________________________________', subtitle)
                        ws.write_merge(fil + 6, fil + 6, 3, 6, 'LIC. DIANA MARYLIN PINCAY CANTILLO', subtitle)
                        ws.write_merge(fil + 7, fil + 7, 3, 6, 'SECRETARÍA GENERAL', subtitle)
                        ws.write_merge(fil + 10, fil + 10, 0, 1, 'Recepción: Mes:     Día:     Hora:', peque)
                        ws.write_merge(fil + 12, fil + 12, 0, 1, '_______________________________________', peque)
                        ws.write_merge(fil + 13, fil + 13, 0, 1, 'Secretaria Responsable:', peque)
                        ws.write_merge(fil + 15, fil + 15, 0, 1, '_______________________________________', peque)
                        wb.save(response)
                        return response

                except Exception as es:
                    pass

            elif action == 'actafinal':
                try:
                    alternativa = AlternativaTitulacion.objects.get(status=True, id=int(request.GET['idalter']))
                    listamatriculados = ComplexivoExamenDetalle.objects.filter(examen__alternativa=alternativa.id).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres')
                    __author__ = 'Unemi'
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte 1')
                    # hoja
                    ws.write_merge(1, 1, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    # ws.write_merge(5, 5, 0, 6, 'ACTA DE CALIFICACIÓN', subtitle)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename =ACTA DE CALIFICACIONES ' + '.xls'
                    ws.col(0).width = 1000
                    ws.col(1).width = 5000
                    ws.col(2).width = 5000
                    ws.col(3).width = 1800
                    ws.col(4).width = 1800
                    ws.col(5).width = 1800
                    ws.col(6).width = 3000
                    ws.write(6, 0, 'INICIO: ' + str(alternativa.grupotitulacion.fechainicio) + ' FIN: ' + str(
                        alternativa.grupotitulacion.fechafin), title)
                    ws.merge(6, 6, 0, 6)
                    ws.write(7, 0, str(alternativa.facultad), nnormal)
                    ws.merge(7, 7, 0, 2)
                    ws.write(8, 0, 'CARRERA: ' + str(alternativa.carrera), nnormal)
                    ws.merge(8, 8, 0, 6)
                    ws.write(9, 0, u'ALTERNATIVA DE TITULACIÓN: ' + str(alternativa), nnormal)
                    ws.merge(9, 9, 0, 6)
                    # ws.write(12, 0, 'PARALELO: ' + str(alternativa.paralelo), nnormal)
                    # ws.merge(12, 12, 0, 2)
                    tiem = datetime.today().date()
                    ws.write(4, 0, 'Milagro, ' + (
                            str(tiem.day) + " de " + str(MESES_CHOICES[tiem.month - 1][1]).lower() + " del " + str(tiem.year)),
                             normaliz)
                    ws.merge(4, 4, 0, 6)
                    # LETRAS PEQUEÑAS
                    ws.write_merge(11, 11, 1, 1, u'PT(PRUEBA TEÓRICA)', peque)
                    ws.write_merge(12, 12, 1, 1, u'PP(PROPUESTA PRÁCTICA)', peque)
                    ws.write_merge(13, 13, 1, 1, u'N.FINAL(NOTA FINAL)', peque)

                    ws.write_merge(11, 11, 3, 5, u'FE(FECHA EGRESO)', peque)
                    ws.write_merge(12, 12, 3, 5, u'FPT(FECHA PRUEBA TEÓRICA)', peque)
                    ws.write_merge(13, 13, 3, 5, u'FPP(FECHA PROPUESTA PRÁCTICA)', peque)

                    ws.write_merge(11, 11, 7, 8, u'FG(FECHA GRADO)', peque)
                    ws.write_merge(12, 12, 7, 8, u'FAG(FECHA ACTA GRADO)', peque)
                    # cuadro
                    # ws.write_merge(15,15,0,1, 'Evaluaciones Parciales', stylenotas)
                    # ws.write_merge(16,17,0,1, 'De: 1-50', stylenotas)
                    encabezado = 14
                    ws.write(encabezado, 0, 'Nº', stylebnotas)
                    ws.write_merge(encabezado, encabezado, 1, 2, 'APELLIDOS Y NOMBRES', stylebnombre)
                    ws.write(encabezado, 3, 'PT', stylebnotas)
                    ws.write(encabezado, 4, 'PP', stylebnotas)
                    ws.write(encabezado, 5, 'N.FINAL', stylebnotas)
                    ws.write(encabezado, 6, 'ESTADO', stylebnotas)
                    ws.write(encabezado, 7, 'FE', stylebnotas)
                    ws.write(encabezado, 8, 'FPT', stylebnotas)
                    ws.write(encabezado, 9, 'FPP', stylebnotas)
                    ws.write(encabezado, 10, 'FG', stylebnotas)
                    ws.write(encabezado, 11, 'FAG', stylebnotas)
                    aproba = reproba = 0
                    if listamatriculados.exists():
                        i = 0
                        for matriculados in listamatriculados:
                            fil = i + 15
                            ws.write(fil, 0, str(i + 1), stylenotas)
                            ws.write(fil, 1, str(
                                matriculados.matricula) + " - " + matriculados.matricula.inscripcion.carrera.alias, normal)
                            ws.merge(fil, fil, 1, 2, normal)
                            ws.write(fil, 3, str(round(matriculados.notafinal, 2)), stylenotas)
                            datopp = matriculados.matricula.datospropuesta()
                            if datopp:
                                ws.write(fil, 4, str(round(datopp.calificacion, 2)), stylenotas)
                            else:
                                ws.write(fil, 4, '', stylenotas)
                            ws.write(fil, 5, str(round(matriculados.matricula.notafinalcomplexivo(), 2)), stylenotas)
                            if matriculados.matricula.notafinalcomplexivo() >= matriculados.examen.notaminima:
                                aproba += 1
                            else:
                                reproba += 1
                            ws.write(fil, 6, 'APROBADO' if matriculados.matricula.notafinalcomplexivo() >= matriculados.examen.notaminima else 'REPROBADO', stylenotas)
                            fechagrado = fechaactagrado = fecha_egresado = fechapt = fechapp = ''
                            datosg = matriculados.matricula.inscripcion.datos_graduado()
                            datose = matriculados.matricula.inscripcion.datos_egresado()
                            fechapt = str(alternativa.get_cronograma()[0].fechaaprobexameninicio)
                            # if datopp:
                            #     fechapp = str(datopp.fecha_modificacion.date() if datopp.fecha_modificacion else datopp.fechainscripcion)
                            fechadefensapropuesta = ''
                            if matriculados.datospropuesta():
                                if matriculados.datospropuesta().grupo:
                                    if matriculados.datospropuesta().grupo.fechadefensa:
                                        fechadefensapropuesta = matriculados.datospropuesta().grupo.fechadefensa.strftime("%d/%m/%Y")
                            if datosg:
                                fechagrado = str(datosg.fechagraduado)
                                fechaactagrado = str(datosg.fechaactagrado)
                            if datose:
                                fecha_egresado = str(datose.fechaegreso)
                            ws.write(fil, 7, fecha_egresado, stylenotas)
                            ws.write(fil, 8, fechapt, stylenotas)
                            ws.write(fil, 9, fechadefensapropuesta, stylenotas)
                            # ws.write(fil, 9, fechapp, stylebnombre)
                            ws.write(fil, 10, fechagrado, stylenotas)
                            ws.write(fil, 11, fechaactagrado, stylenotas)
                            i = i + 1

                        fil = fil + 2
                        ws.write_merge(fil + 1, fil + 1, 1, 1, u'TOTAL DE ESTUDIANTES', peque)
                        ws.write_merge(fil + 2, fil + 2, 1, 1, u'TOTAL APROBADOS', peque)
                        ws.write_merge(fil + 3, fil + 3, 1, 1, u'TOTAL REPROBADOS', peque)

                        ws.write_merge(fil + 1, fil + 1, 2, 2, str(aproba + reproba), peque)
                        ws.write_merge(fil + 2, fil + 2, 2, 2, str(aproba), peque)
                        ws.write_merge(fil + 3, fil + 3, 2, 2, str(reproba), peque)
                        fil = fil + 3
                        # ws.write_merge(fil+5, fil+5,0,6, '_______________________________________', subtitle)
                        # ws.write_merge(fil+6, fil+6,0,6,'LIC. DIANA MARYLYN PINCAY CANTILLO',subtitle)
                        # ws.write_merge(fil+7, fil+7,0,6,'SECRETARIA GENERAL',subtitle)
                        # ws.write_merge(fil+10,fil+10,0,1, 'Recepción: Mes:     Día:     Hora:', peque)
                        # ws.write_merge(fil+12,fil+12,0,1, '_______________________________________', peque)
                        # ws.write_merge(fil+13,fil+13,0,1, 'Secretaria Responsable:', peque)
                        # ws.write_merge(fil+15,fil+15,0,1, '_______________________________________', peque)
                        wb.save(response)
                        return response

                except Exception as es:
                    pass

            elif action == 'nominaexamen' or action == 'nominagracia':
                try:
                    examen = ComplexivoExamen.objects.get(status=True, id=int(request.GET['id']))
                    __author__ = 'Unemi'
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte 1')
                    # hoja
                    if action == 'nominaexamen':
                        nombre = 'NÓMINA DE EXAMEN COMPLEXIVO'
                        exa = 'EXAMEN COMPLEXIVO'
                        fecha = examen.fechaexamen

                        listamatriculados = ComplexivoExamenDetalle.objects.filter(examen=examen.id).order_by(
                            'matricula__inscripcion__persona__apellido1')
                    else:
                        nombre = 'NÓMINA DE EXAMEN DE GRACIA'
                        exa = 'EXAMEN DE GRACIA'
                        fecha = examen.fechaexamenrecuperacion
                        listamatriculados = ComplexivoExamenDetalle.objects.filter(examen=examen.id, calificacion__lt=examen.notaminima).order_by('matricula__inscripcion__persona__apellido1')
                    if listamatriculados.exists():

                        ws.write_merge(1, 1, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write_merge(2, 2, 0, 4, 'VICERRECTORADO ACADÉMICO Y DE INVESTIGACIÓN', title)
                        ws.write_merge(3, 3, 0, 4, 'GESTIÓN TÉCNICA ACADÉMICA', title)
                        ws.write_merge(4, 4, 0, 4, 'PROCESO DE  TITULACIÓN', title)
                        ws.write(5, 0, str(nombre), subtitle)
                        ws.merge(5, 5, 0, 4)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename = NOMINA DE ESTUDIANTES ' + '.xls'
                        ws.col(0).width = 1000
                        ws.col(1).width = 10000
                        ws.col(2).width = 2500
                        ws.col(3).width = 4000
                        ws.col(4).width = 4000
                        ws.col(5).width = 1500
                        ws.col(6).width = 1300
                        ws.write(6, 0, 'PERIODO: ' + str(examen.alternativa.grupotitulacion.periodogrupo.nombre), subtitle)
                        ws.merge(6, 6, 0, 4)
                        ws.write(7, 0, 'INICIO: ' + str(examen.alternativa.grupotitulacion.fechainicio) + ' FIN: ' + str(examen.alternativa.grupotitulacion.fechafin), subtitle)
                        ws.merge(7, 7, 0, 4)
                        ws.write(9, 0, str(examen.alternativa.facultad), nnormal)
                        ws.merge(9, 9, 0, 1)
                        ws.write(12, 3, 'EXAMEN:' + exa, nnormal)
                        ws.merge(12, 12, 3, 4)
                        ws.write(13, 3, 'FECHA EXAMEN:' + str(fecha), nnormal)
                        ws.merge(13, 13, 3, 4)
                        ws.write(13, 0, 'PARALELO: ' + str(examen.alternativa.paralelo), nnormal)
                        ws.merge(13, 13, 0, 2)
                        ws.write(10, 0, 'CARRERA: ' + str(examen.alternativa.carrera), nnormal)
                        ws.merge(10, 10, 0, 4)
                        ws.write(11, 0, 'ALTERNATIVA DE TITULACIÓN: ' + str(examen.alternativa), nnormal)
                        ws.merge(11, 11, 0, 4)
                        ws.write(12, 0, 'PROFESOR: ' + str(examen.docente), nnormal)
                        ws.merge(12, 12, 0, 2)
                        tiem = datetime.today().date()
                        ws.write(8, 0, 'Milagro, ' + str(tiem), nnormal)
                        ws.merge(8, 8, 0, 4)
                        encabezado = 15
                        ws.write(encabezado, 0, 'Nº', stylebnotas)
                        ws.write(encabezado, 1, 'APELLIDOS Y NOMBRES', stylebnombre)
                        ws.write(encabezado, 2, 'CÉDULA', stylebnotas)
                        ws.write(encabezado, 3, 'FIRMA', stylebnotas)
                        ws.write(encabezado, 4, 'OBSERVACIONES', stylebnotas)
                        i = 0
                        for matriculados in listamatriculados:
                            fil = i + 16
                            ws.write(fil, 0, str(i + 1), stylenotas)
                            ws.write(fil, 1, str(matriculados.matricula), normal)
                            ws.write(fil, 2, str(matriculados.matricula.inscripcion.persona.cedula), stylenotas)
                            ws.write(fil, 3, ' ', stylevacio)
                            ws.write(fil, 4, ' ', stylevacio)
                            i = i + 1
                        ws.write_merge(fil + 2, fil + 2, 0, 4, "Observación: _________________________________________________________________________", nnormal)
                        ws.write_merge(fil + 5, fil + 5, 0, 1, '_______________________________________', subtitle)
                        ws.write(fil + 6, 0, str(examen.docente), subtitle)
                        ws.merge(fil + 6, fil + 6, 0, 1)
                        ws.write_merge(fil + 7, fil + 7, 0, 1, 'PROFESOR', subtitle)
                        ws.write_merge(fil + 5, fil + 5, 2, 4, '_______________________________________', subtitle)
                        ws.write_merge(fil + 6, fil + 6, 2, 4, 'ING. VIVIANA GAIBOR HINOSTROZA,MSC', subtitle)
                        ws.write_merge(fil + 7, fil + 7, 2, 4, u'PROCESO DE TITULACIÓN', subtitle)
                        ws.write_merge(fil + 8, fil + 8, 2, 4, u'GESTIÓN TÉCNICA ACADÉMICA', subtitle)
                        ws.write_merge(fil + 10, fil + 10, 0, 1, 'Recepción: Mes:   Día:    Hora:', peque)
                        ws.write_merge(fil + 12, fil + 12, 0, 1, '_______________________________________', peque)
                        ws.write_merge(fil + 13, fil + 13, 0, 1, 'Secretaria Responsable:', peque)
                        ws.write_merge(fil + 15, fil + 15, 0, 1, '_______________________________________', peque)
                        wb.save(response)
                        return response

                except Exception as es:
                    pass

            # -----------------------REPORTE DE ESTUDIANTES MATRICULADOS POR ALTERNATIVAS-------------------------
            elif action == 'reporte_estudiante_matriculados':
                try:
                    data['alternativa'] = alter = AlternativaTitulacion.objects.get(pk=int(request.GET['ida']))
                    search = None
                    ids = None
                    ide = 0
                    if 'ide' in request.GET:
                        ide = int(request.GET['ide'])
                    if 's' in request.GET:
                        search = request.GET['s']
                        return (reporte_matriculados_alternativa(alter, ide, search))
                    else:
                        return (reporte_matriculados_alternativa(alter, ide, search))
                except Exception as ex:
                    pass
            #guardar en la tabla de egresado y graduado si la fecha de calificacion ya paso y si paso el examen
            elif action == 'addpregraduarestudiante':
                try:
                    data['title'] = u'Graduar estudiantes aprobados'
                    data['alter'] = alter = AlternativaTitulacion.objects.get(status=True, pk=request.GET['id'])
                    if alter.puede_graduar_aprobados_complexivo() or alter.puede_graduar_estudiante_trabajo():
                        return render(request, "adm_alternativatitulacion/confirmar_graduarestudiantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpregraduarestudianteind':
                try:
                    data['title'] = u'Graduar estudiante aprobado'
                    data['alter'] = alter = AlternativaTitulacion.objects.get(status=True, pk=request.GET['ida'])
                    data['mat'] = mat = MatriculaTitulacion.objects.get(status=True, pk=request.GET['id'], alternativa_id=request.GET['ida'])
                    # if mat.puede_graduar_aprobado_complexivo_ind(alter.id) or mat.puede_graduar_aprobado_complexivo_ind(alter.id):
                    return render(request, "adm_alternativatitulacion/confirmar_graduarestudianteind.html", data)
                except Exception as ex:
                    pass


            elif action == 'confirmarcerrarperiodo':
                try:
                    data['title'] = u'Confirmacion de cierre de periodo'
                    data['periodog'] = PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_alternativatitulacion/confirmarcierreperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'confirmarabrirperiodo':
                try:
                    data['title'] = u'Confirmacion de apertura de periodo'
                    data['periodog'] = PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_alternativatitulacion/confirmarabrirperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcronogramaadicional':
                try:
                    data['title'] = u'Cronograma Adicional Examen Complexivo'
                    data['cronograma'] = cron = CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    data['form'] = CronogramaAdicionalExamenComplexivoForm(initial={'fechainicioexamen':cron.fechaaprobexameninicio+timedelta(days=1)})
                    template = get_template("adm_alternativatitulacion/addcronogramaadicional.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'editcronogramaadicional':
                try:
                    data['title'] = u'Cronograma Adicional Examen Complexivo'
                    data['cro'] = conograma = CronogramaAdicionalExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(conograma)
                    data['form'] = CronogramaAdicionalExamenComplexivoForm(initial=initial)
                    template = get_template("adm_alternativatitulacion/editcronogramaadicional.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'delcronogramaadicional':
                try:
                    data['title'] = u'Eliminar Cronograma Adicional Examen Complexivo'
                    data['cro'] = CronogramaAdicionalExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_alternativatitulacion/delcronogramaadicional.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoalumnos':
                try:
                    lista = []
                    listamaterias = []
                    idalter = int(request.GET['idalter'])
                    listado1 = Materia.objects.filter(asignaturamalla__validarequisitograduacion=True, nivel__periodo=periodo, asignaturamalla__status=True, status=True).order_by('asignaturamalla__malla__carrera__nombre', 'paralelo')
                    listado2 = Materia.objects.filter(asignaturamalla__malla_id=383, nivel__periodo=periodo, status=True).order_by('id')
                    listadomaterias = listado1 | listado2
                    alternativa = AlternativaTitulacion.objects.get(pk=idalter, status=True)
                    listadomatriculados = MatriculaTitulacion.objects.filter(alternativa=alternativa, status=True).exclude(inscripcion_id__in=MateriaAsignada.objects.values_list('matricula__inscripcion_id').filter(materia_id__in=listadomaterias.values_list('id'), status=True)).order_by('inscripcion__persona__apellido1')
                    for lismate in listadomaterias:
                        listamaterias.append([lismate.id, str(lismate.asignaturamalla.malla.carrera.nombre + ' - ' + lismate.asignaturamalla.asignatura.nombre + ' - ' + str(lismate.asignaturamalla.nivelmalla.nombre) + ' - ' + lismate.paralelo)])
                    for lis in listadomatriculados:
                        lista.append([lis.inscripcion.id, str(lis.inscripcion.persona.apellido1 + ' ' + lis.inscripcion.persona.apellido2 + ' ' + lis.inscripcion.persona.nombres)])
                    data = {"results": "ok", "listadomaterias": listamaterias, 'listado': lista, 'alternativa': str(alternativa.tipotitulacion.nombre + ' ' + alternativa.paralelo + ' ' + str(alternativa.id))}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listadotitulacion':
                try:
                    data['title'] = 'Listado de alumnos para titulación'
                    sinrequisitos = False
                    search, idfacultad, idcarrera, url_vars = request.GET.get('s', ''), request.GET.get('idf', ''),request.GET.get('idc', ''), ''
                    materiatitulacion = MateriaTitulacion.objects.filter(materiaasignada__materia__nivel__periodo=periodo, materiaasignada__status=True, status=True, materiaasignada__estado_id=1, materiaasignada__retiramateria=False)
                    data['listadocoordinacion'] = materiatitulacion.values_list('materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id', 'materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__nombre').distinct()
                    if idfacultad:
                        data['listadocarrera'] = materiatitulacion.values_list('materiaasignada__materia__asignaturamalla__malla__carrera__id', 'materiaasignada__materia__asignaturamalla__malla__carrera__nombre').filter(materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id=idfacultad).distinct()
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            materiatitulacion = materiatitulacion.filter(Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__cedula__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__pasaporte__icontains=search) |
                                                                       Q(materiaasignada__matricula__inscripcion__persona__usuario__username__icontains=search),
                                                                       materiaasignada__materia__nivel__periodo=periodo, materiaasignada__status=True, status=True, materiaasignada__estado_id=1, materiaasignada__retiramateria=False)

                        else:
                            materiatitulacion = materiatitulacion.filter(Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1]), materiaasignada__materia__nivel__periodo=periodo, materiaasignada__estado_id=1, materiaasignada__status=True, status=True, materiaasignada__retiramateria=False)
                    url_vars += "&action=listadotitulacion"
                    if idfacultad:
                        data['idf'] = int(request.GET['idf'])
                        url_vars += "&idf={}".format(idfacultad)
                        materiatitulacion = materiatitulacion.filter(materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id=idfacultad)
                    if idcarrera:
                        data['idc'] = int(request.GET['idc'])
                        url_vars += "&idc={}".format(idcarrera)
                        materiatitulacion = materiatitulacion.filter(materiaasignada__materia__asignaturamalla__malla__carrera__id=idcarrera)
                    numerofilas = 25
                    materiatitulacion = materiatitulacion.order_by('materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id','materiaasignada__materia__asignaturamalla__malla__carrera__id','materiaasignada__materia__asignaturamalla__asignatura__nombre','materiaasignada__materia__paralelo','materiaasignada__matricula__inscripcion__persona__apellido1', 'materiaasignada__matricula__inscripcion__persona__apellido2', 'materiaasignada__matricula__inscripcion__persona__nombres')
                    paging = MiPaginador(materiatitulacion, numerofilas)
                    p = 1

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
                    data['listado'] = page.object_list
                    return render(request, "adm_alternativatitulacion/listadotitulacion.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Proceso de Titulación'
            coordiciones = persona.mis_coordinaciones()
            data['coordinaciones'] = Coordinacion.objects.filter(pk__in=coordiciones).distinct().exclude(Q(id=MODULO_INGLES_ID)| Q(id=POSGRADO_EDUCACION_ID)|Q(id=MODULOS_COMPUTACION_ID)|Q(id=ADMISION_ID))
            data['periodotitulacion']= PeriodoGrupoTitulacion.objects.filter(status=True).order_by('-id')
            if 'alter' in request.GET:
                periodoid=PeriodoGrupoTitulacion.objects.get(pk=int(request.GET['alter']))
            else:
                if PeriodoGrupoTitulacion.objects.all().exists():
                    periodoid = PeriodoGrupoTitulacion.objects.filter(status=True).order_by('-id')[0]
                else:
                    periodoid = []
            data['periodogrupo'] = periodoid
            return render(request, "adm_alternativatitulacion/view.html", data)


def reporte_matriculados_alternativa(alter, estado, estudiante):
    try:
        borders = Borders()
        borders.left = 1
        borders.right = 1
        borders.top = 1
        borders.bottom = 1
        __author__ = 'Unemi'
        title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
        normal = easyxf('font: name Arial , height 150; alignment: horiz left')
        encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
        normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
        subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
        normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
        style1 = easyxf(num_format_str='D-MMM-YY')
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        normal.borders = borders
        normalc.borders = borders
        normalsub.borders = borders
        subtema.borders = borders
        encabesado_tabla.borders = borders
        wb = Workbook(encoding='utf-8')
        est='TODOS'
        ws = wb.add_sheet('exp_xls_post_part')
        ws.write_merge(1, 1, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
        ws.write_merge(2, 2, 0, 10, 'VICERRECTORADO ACADÉMICO Y DE INVESTIGACIÓN', title)
        ws.write_merge(3, 3, 0, 10, 'GESTIÓN TÉCNICA ACADÉMICA', title)
        ws.write_merge(4, 4, 0, 10, 'PROCESO DE  TITULACIÓN', title)

        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=Matriculados_Proceso_Titulacion' + random.randint(1, 10000).__str__() + '.xls'
        ws.write_merge(6, 6, 0, 1, 'FACULTAD', normalsub)
        ws.write_merge(7, 7, 0, 1, 'CARRERA', normalsub)
        ws.write_merge(6, 6, 2, 6, alter.facultad.nombre, normalsub)
        ws.write_merge(7, 7, 2, 6, alter.carrera.nombre, normalsub)

        row_num = 9
        ide = estado
        ws.col(0).width = 1200
        ws.col(1).width = 3000
        ws.col(2).width = 4000
        ws.col(3).width = 5000
        ws.col(4).width = 5000
        ws.col(5).width = 5000
        ws.col(6).width = 3000
        ws.col(7).width = 3200
        ws.col(8).width = 3000
        ws.col(9).width = 4000
        ws.col(10).width = 3000

        ws.write(row_num, 0, 'Nº', encabesado_tabla)
        ws.write(row_num, 1, 'COD. MATRICULA', encabesado_tabla)
        ws.write(row_num, 2, 'ESTADO MATRICULA', encabesado_tabla)
        ws.write(row_num, 3, 'PRIMER APELLIDO', encabesado_tabla)
        ws.write(row_num, 4, 'SEGUNDO APELLIDO', encabesado_tabla)
        ws.write(row_num, 5, 'NOMBRES', encabesado_tabla)
        ws.write(row_num, 6, 'SEXO', encabesado_tabla)
        ws.write(row_num, 7, 'FECHA INGRESO', encabesado_tabla)
        ws.write(row_num, 8, 'HORA INGRESO', encabesado_tabla)
        ws.write(row_num, 9, 'ESTADO GESTACIÓN', encabesado_tabla)
        ws.write(row_num, 10, 'DISCAPASIDAD', encabesado_tabla)

        if not estudiante is None:
            search = estudiante
            ss = search.split(' ')
            if len(ss) == 1:
                if ide > 0:
                    listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(alternativa=alter) & Q(estado=estado) & Q(status=True) & ( Q(inscripcion__persona__nombres__icontains=estudiante) | Q(inscripcion__persona__apellido1__icontains=estudiante) | Q(inscripcion__persona__apellido2__icontains=estudiante) | Q(inscripcion__persona__cedula__icontains=estudiante))).distinct().order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1','inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                else:
                    listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(alternativa=alter) & (Q(inscripcion__persona__nombres__icontains=search) | Q(inscripcion__persona__apellido1__icontains=search) | Q(inscripcion__persona__apellido2__icontains=search) | Q(inscripcion__persona__cedula__icontains=search))).distinct().order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
            else:
                if estado > 0:
                    listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(alternativa=alter) & Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(inscripcion__persona__apellido2__icontains=ss[1]) & Q(estado=estado)).distinct().order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                else:
                    listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(alternativa=alter) & Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(inscripcion__persona__apellido2__icontains=ss[1])).distinct().order_by('-inscripcion__persona__usuario__is_active','inscripcion__persona__apellido1', 'inscripcion__persona__apellido2','inscripcion__persona__nombres')
        else:
            if ide > 0:
                listamatriculados = MatriculaTitulacion.objects.select_related().filter(alternativa=alter, estado=estado).order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
            else:
                listamatriculados = MatriculaTitulacion.objects.select_related().filter(alternativa=alter).order_by('-inscripcion__persona__usuario__is_active', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

        row_num = 10
        i = 0
        for matriculados in listamatriculados:
            i +=1
            campo0 = matriculados.id
            campo1 = matriculados.get_estado_display()
            campo2 = matriculados.inscripcion.persona.apellido1
            campo3 = matriculados.inscripcion.persona.apellido2
            campo4 = matriculados.inscripcion.persona.nombres
            campo5 = matriculados.inscripcion.persona.sexo.nombre
            campo6 = matriculados.fechainscripcion.strftime("%Y/%m/%d")
            campo7 = matriculados.fecha_creacion.strftime("%H:%M:%S")
            campo8 = 'No'
            if matriculados.estadogestacion_set.filter(estadogestacion= True, status= True).exists():
                campo8 = 'Si'
            campo9 = 'No'
            if matriculados.inscripcion.persona.mi_perfil().tienediscapacidad:
                campo9 = 'Si'

            ws.write(row_num, 0, i, normal)
            ws.write(row_num, 1, campo0, normal)
            ws.write(row_num, 2, campo1, normal)
            ws.write(row_num, 3, campo2, normal)
            ws.write(row_num, 4, campo3, normal)
            ws.write(row_num, 5, campo4, normal)
            ws.write(row_num, 6, campo5, normal)
            ws.write(row_num, 7, campo6, normal)
            ws.write(row_num, 8, campo7, normal)
            ws.write(row_num, 9, campo8, normalc)
            ws.write(row_num, 10, campo9, normalc)
            row_num += 1
        wb.save(response)
        return response
    except Exception as ex:
        pass


def valida_matricular_estudiante(data, alter, inscripcion):
    vali_alter = 0
    vali_tenido = 0
    data['item'] = alter
    data['grupo'] = alter.grupotitulacion
    data['inscripcion'] = inscripcion
    malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
    perfil = inscripcion.persona.mi_perfil()
    data['tiene_discapidad'] = perfil.tienediscapacidad
    excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
    fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()
    if alter.estadofichaestudiantil:
        vali_alter += 1
        ficha = 0
        if inscripcion.persona.nombres and inscripcion.persona.apellido1 and inscripcion.persona.apellido2 and inscripcion.persona.nacimiento and inscripcion.persona.cedula and inscripcion.persona.nacionalidad and inscripcion.persona.email and inscripcion.persona.estado_civil and inscripcion.persona.sexo:
            data['datospersonales'] = True
            ficha += 1
        if inscripcion.persona.paisnacimiento and inscripcion.persona.provincianacimiento and inscripcion.persona.cantonnacimiento and inscripcion.persona.parroquianacimiento:
            data['datosnacimientos'] = True
            ficha += 1
        examenfisico = inscripcion.persona.datos_examen_fisico()
        if inscripcion.persona.sangre and examenfisico.peso and examenfisico.talla:
            data['datosmedicos'] = True
            ficha += 1
        if inscripcion.persona.pais and inscripcion.persona.provincia and inscripcion.persona.canton and inscripcion.persona.parroquia and inscripcion.persona.direccion and inscripcion.persona.direccion2 and inscripcion.persona.num_direccion and inscripcion.persona.telefono_conv or inscripcion.persona.telefono:
            data['datosdomicilio'] = True
            ficha += 1
        if perfil.raza:
            data['etnia'] = True
            ficha += 1
        if ficha == 5:
            vali_tenido += 1
    if alter.estadopracticaspreprofesionales:
        vali_alter += 1
        totalhoras = 0
        practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True, culminada=True)
        data['malla_horas_practicas'] = malla.horas_practicas
        if fechainicioprimernivel > excluiralumnos:
            if practicaspreprofesionalesinscripcion.exists():
                for practicas in practicaspreprofesionalesinscripcion:
                    if practicas.tiposolicitud == 3:
                        totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
                    else:
                        totalhoras += practicas.numerohora
                if totalhoras >= malla.horas_practicas:
                    data['practicaspreprofesionales'] = True
                    vali_tenido += 1
            data['practicaspreprofesionalesvalor'] = totalhoras
        else:
            data['practicaspreprofesionales'] = True
            vali_tenido += 1
            data['practicaspreprofesionalesvalor'] = malla.horas_practicas

    if alter.estadocredito:
        vali_alter += 1
        data['creditos'] = inscripcion.aprobo_asta_penultimo_malla()
        if inscripcion.aprobo_asta_penultimo_malla() and inscripcion.esta_matriculado_ultimo_nivel():
            vali_tenido += 1
        data['cantasigaprobadas'] = inscripcion.cantidad_asig_aprobada_penultimo_malla()
        data['cantasigaprobar'] = inscripcion.cantidad_asig_aprobar_penultimo_malla()
        data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivel()
        # data['creditos'] = inscripcion.tiene_porciento_cumplimiento_malla()
        # vali_tenido += 1
        # malla = inscripcion.malla_inscripcion().malla
        # total_materias_malla = malla.cantidad_materiasaprobadas()
        # cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True,asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
        # data['creditoporcentaje'] = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
    if alter.estadoadeudar:
        vali_alter += 1
        if inscripcion.adeuda_a_la_fecha() == 0:
            data['deudas'] = True
            vali_tenido += 1
        data['deudasvalor'] = inscripcion.adeuda_a_la_fecha()
    if alter.estadoingles:
        vali_alter += 1
        modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
        numero_modulo_ingles = modulo_ingles.count()
        lista = []
        listaid = []
        for modulo in modulo_ingles:
            if inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
                lista.append(modulo.asignatura.nombre)
                listaid.append(modulo.asignatura.id)
        data['modulo_ingles_aprobados'] = lista
        data['modulo_ingles_faltante'] = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid])
        if numero_modulo_ingles == len(listaid):
            data['modulo_ingles'] = True
            vali_tenido += 1
    if alter.estadonivel:
        vali_alter += 1
        total_materias_malla = malla.cantidad_materiasaprobadas()
        cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True,asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
        poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
        data['mi_nivel'] = nivel = inscripcion.mi_nivel()
        inscripcionmalla = inscripcion.malla_inscripcion()
        niveles_maximos = inscripcionmalla.malla.niveles_regulares
        # MOMENTANEO EL AUMENTO DE VALI_TENIDO
        vali_tenido += 1
        if poraprobacion >= 100:
            data['nivel'] = True
            # vali_tenido += 1
        else:
            if niveles_maximos == nivel.nivel.id:
                data['septimo'] = True
    if perfil.tienediscapacidad:
        data['discapacidad'] = perfil
    if inscripcion.persona.sexo.id == ESTADO_GESTACION:
        data['femenino'] = True
    if alter.estadovinculacion:
        vali_alter += 1
        data['malla_horas_vinculacion'] = malla.horas_vinculacion
        horastotal = inscripcion.numero_horas_proyectos_vinculacion()
        # horastotal = horastotal if horastotal else 0
        if fechainicioprimernivel > excluiralumnos:
            horastotal = inscripcion.numero_horas_proyectos_vinculacion()
            if horastotal >= malla.horas_vinculacion:
                data['vinculacion'] = True
                vali_tenido += 1
            data['horas_vinculacion'] = horastotal
        else:
            data['horas_vinculacion'] = malla.horas_vinculacion
            data['vinculacion'] = True
            vali_tenido += 1
    if alter.estadocomputacion:
        vali_alter += 1
        asignatura = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
        data['record_computacion'] = record = RecordAcademico.objects.filter(inscripcion__id=inscripcion.id, asignatura__id__in=asignatura, aprobada=True)
        creditos_computacion = 0
        data['malla_creditos_computacion'] = malla.creditos_computacion
        for comp in record:
            creditos_computacion += comp.creditos
        if creditos_computacion >= malla.creditos_computacion:
            data['computacion'] = True
            vali_tenido += 1
        data['creditos_computacion'] = creditos_computacion
    # if alter.actividadcomplementaria:
    #     vali_alter += 1
    #     data['actividadescomplementarias'] = inscripcion.aprueba_actividades_complementarias(alter.acperiodo.id)
    #     if inscripcion.aprueba_actividades_complementarias(alter.acperiodo.id):
    #         vali_tenido += 1
    #     data['actividades_x_cumplir'] = inscripcion.cantidad_actividadcomplementaria_cumplir(alter.acperiodo.id)
    #     data['cantidad_actividades_registradas'] = inscripcion.cantidad_actividadescomplementarias_registradas(
    #         alter.acperiodo.id)
    #     data['lista_actividades'] = inscripcion.lista_actividades_x_periodo(alter.acperiodo.id)
    if vali_alter == vali_tenido:
        data['aprueba'] = True
    if inscripcion.persona.tipocelular == 0:
        data['tipocelular'] = '-'
    else:
        data['tipocelular'] = TIPO_CELULAR[int(inscripcion.persona.tipocelular) - 1][1]
    return data


def valida_matriculatitulacion_requisitos(data, alter, inscripcion, matriculacion):
    vali_alter = 7
    vali_tenido = 0
    data['item'] = alter
    data['grupo'] = alter.grupotitulacion
    data['inscripcion'] = inscripcion
    malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
    perfil = inscripcion.persona.mi_perfil()
    data['tiene_discapidad'] = perfil.tienediscapacidad
    # if alter.estadofichaestudiantil:
    # vali_alter += 1
    # ficha = 0
    # if inscripcion.persona.nombres and inscripcion.persona.apellido1 and inscripcion.persona.apellido2 and inscripcion.persona.nacimiento and inscripcion.persona.cedula and inscripcion.persona.nacionalidad and inscripcion.persona.email and inscripcion.persona.estado_civil and inscripcion.persona.sexo:
    #     data['datospersonales'] = True
    #     ficha += 1
    # if inscripcion.persona.paisnacimiento and inscripcion.persona.provincianacimiento and inscripcion.persona.cantonnacimiento and inscripcion.persona.parroquianacimiento:
    #     data['datosnacimientos'] = True
    #     ficha += 1
    # examenfisico = inscripcion.persona.datos_examen_fisico()
    # if inscripcion.persona.sangre and examenfisico.peso and examenfisico.talla:
    #     data['datosmedicos'] = True
    #     ficha += 1
    # if inscripcion.persona.pais and inscripcion.persona.provincia and inscripcion.persona.canton and inscripcion.persona.parroquia and inscripcion.persona.direccion and inscripcion.persona.direccion2 and inscripcion.persona.num_direccion and inscripcion.persona.telefono_conv or inscripcion.persona.telefono:
    #     data['datosdomicilio'] = True
    #     ficha += 1
    # if perfil.raza:
    #     data['etnia'] = True
    #     ficha += 1
    # if ficha == 5:
    #     vali_tenido += 1
    # if alter.estadopracticaspreprofesionales:
    # vali_alter += 1
    totalhoras = 0
    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True, culminada=True)
    data['malla_horas_practicas'] = malla.horas_practicas
    if practicaspreprofesionalesinscripcion.exists():
        for practicas in practicaspreprofesionalesinscripcion:
            if practicas.tiposolicitud == 3:
                totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
            else:
                totalhoras += practicas.numerohora
        if totalhoras >= malla.horas_practicas:
            data['practicaspreprofesionales'] = True
            vali_tenido += 1
    data['practicaspreprofesionalesvalor'] = totalhoras
    # if alter.estadocredito:
    #     vali_alter += 1
    data['creditos'] = inscripcion.aprobo_asta_penultimo_malla()
    if inscripcion.aprobo_asta_penultimo_malla() and inscripcion.esta_matriculado_ultimo_nivel():
        vali_tenido += 1
    data['cantasigaprobadas'] = inscripcion.cantidad_asig_aprobada_penultimo_malla()
    data['cantasigaprobar'] = inscripcion.cantidad_asig_aprobar_penultimo_malla()
    data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivel()

    # if alter.estadoadeudar:
    #     vali_alter += 1
    if inscripcion.adeuda_a_la_fecha() == 0:
        data['deudas'] = True
        vali_tenido += 1
    data['deudasvalor'] = inscripcion.adeuda_a_la_fecha()
    # if alter.estadoingles:
    #     vali_alter += 1
    modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
    numero_modulo_ingles = modulo_ingles.count()
    lista = []
    listaid = []
    for modulo in modulo_ingles:
        if inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
            lista.append(modulo.asignatura.nombre)
            listaid.append(modulo.asignatura.id)
    data['modulo_ingles_aprobados'] = lista
    data['modulo_ingles_faltante'] = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid])
    if numero_modulo_ingles == len(listaid):
        data['modulo_ingles'] = True
        vali_tenido += 1
    # if alter.estadonivel:
    #     vali_alter += 1
    total_materias_malla = malla.cantidad_materiasaprobadas()
    cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True,asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
    poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
    data['mi_nivel'] = nivel = inscripcion.mi_nivel()
    inscripcionmalla = inscripcion.malla_inscripcion()
    niveles_maximos = inscripcionmalla.malla.niveles_regulares
    # MOMENTANEO EL AUMENTO DE VALI_TENIDO
    # vali_tenido += 1
    if poraprobacion >= 100:
        data['nivel'] = True
        vali_tenido += 1
    else:
        if niveles_maximos == nivel.nivel.id:
            data['septimo'] = True
    if perfil.tienediscapacidad:
        data['discapacidad'] = perfil
    if inscripcion.persona.sexo.id == ESTADO_GESTACION:
        data['femenino'] = True
    # if alter.estadovinculacion:
    #     vali_alter += 1
    data['malla_horas_vinculacion'] = malla.horas_vinculacion
    horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, proyecto__status=True,inscripcion_id=inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
    horastotal = horastotal if horastotal else 0
    if horastotal >= malla.horas_vinculacion:
        data['vinculacion'] = True
        vali_tenido += 1
    data['horas_vinculacion'] = horastotal
    # if alter.estadocomputacion:
    #     vali_alter += 1
    asignatura = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
    data['record_computacion'] = record = RecordAcademico.objects.filter(inscripcion__id=inscripcion.id, asignatura__id__in=asignatura, aprobada=True)
    creditos_computacion = 0
    data['malla_creditos_computacion'] = malla.creditos_computacion
    for comp in record:
        creditos_computacion += comp.creditos
    if creditos_computacion >= malla.creditos_computacion:
        data['computacion'] = True
        vali_tenido += 1
    data['creditos_computacion'] = creditos_computacion
    cumplerequisitos = False
    if vali_alter == vali_tenido:
        data['aprueba'] = True
        if ComplexivoGrupoTematica.objects.values('id').filter(status=True, activo=True, complexivodetallegrupo__status=True, complexivodetallegrupo__matricula=matriculacion).exists():
            grupo = ComplexivoGrupoTematica.objects.get(status=True, activo=True, complexivodetallegrupo__status=True,  complexivodetallegrupo__matricula=matriculacion)
            if grupo.estado_detalle() != 3:
                if grupo.estado_propuesta():
                    if grupo.estado_propuesta().estado == 2:
                        cumplerequisitos = True
        # cumplerequisitos = True
    return cumplerequisitos

def cerrar_periodo_titulacion(id):
    if PeriodoGrupoTitulacion.objects.filter(pk=id, fechafin__lt=datetime.now().date()).exists():
        for periodo in PeriodoGrupoTitulacion.objects.filter(pk=id, fechafin__lt=datetime.now().date()):
            matriculados = MatriculaTitulacion.objects.filter(alternativa_id__in=AlternativaTitulacion.objects.values_list("id", flat=False).filter(grupotitulacion_id__in=periodo.grupotitulacion_set.values_list("id").filter(status=True), status=True),status=True).exclude(Q(estado=2)| Q(estado=4)| Q(estado=5)| Q(estado=8))
            for matriculado in matriculados:
                notaexamen = ComplexivoExamenDetalle.objects.filter(matricula_id=matriculado.id, status=True)[0].notafinal if ComplexivoExamenDetalle.objects.filter(matricula_id=matriculado.id, status=True).exists() else 0
                notapropuestat = ComplexivoDetalleGrupo.objects.filter(matricula_id=matriculado.id, status=True)[0].calificacion if ComplexivoDetalleGrupo.objects.filter(matricula_id=matriculado.id, status=True).exists() else 0
                notafinal = round(((float(notaexamen) + float(notapropuestat)) / 2), 2)
                if matriculado.estado==1 or matriculado.estado==7:
                    if notafinal >= 70:
                        matriculado.estado=10
                        matriculado.save()
                    else:
                        matriculado.estado=9
                        matriculado.save()
            periodo.abierto = False
            periodo.save()
        return True
    else:
        return False
#----------------------REPORTE POR CARRERA Y POR ALTERNATIVA----------------
def reporte_matrigulados_especificos(alter, grupo, carrera, periodo):
    try:
        tipo =''
        per = ''
        if periodo and grupo:
            per = str(periodo.nombre)+',  De'+str(periodo.fechainicio.strftime('%Y/%m/%d')+' hasta '+periodo.fechafin.strftime('%Y/%m/%d'))
            tipo = 'Grupo '+ str(grupo.nombre.encode('utf8'))
            nombreperiodo = periodo.nombre

        elif periodo:
            per = str(periodo.nombre) + ',  De' + str(periodo.fechainicio.strftime('%Y/%m/%d') + ' hasta ' + periodo.fechafin.strftime('%Y/%m/%d'))
            tipo = 'Periodo ' + str(periodo.nombre.encode('utf8'))
            nombreperiodo = periodo.nombre

        elif grupo and carrera:
            per = str(grupo.periodogrupo.nombre) + ',  De' + str(grupo.periodogrupo.fechainicio.strftime('%Y/%m/%d') + ' hasta ' + grupo.periodogrupo.fechafin.strftime('%Y/%m/%d'))
            tipo = 'Grupo '+str(grupo.nombre.encode('utf8'))
            nombreperiodo = grupo.periodogrupo.nombre

        else:
            per = str(alter.grupotitulacion.periodogrupo.nombre) + ',  De' + str(alter.grupotitulacion.periodogrupo.fechainicio.strftime('%Y/%m/%d') + ' hasta ' + alter.grupotitulacion.periodogrupo.fechafin.strftime('%Y/%m/%d'))
            tipo = str(carrera.nombre.encode('utf8')) if carrera else str(alter.carrera.nombre.encode('utf8'))
            nombreperiodo = str(alter.grupotitulacion.periodogrupo.nombre)

        borders = Borders()
        borders.left = 1
        borders.right = 1
        borders.top = 1
        borders.bottom = 1
        __author__ = 'Unemi'
        normal = easyxf('font: name Arial , height 150; alignment: horiz left')
        encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
        normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
        subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
        normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        normal.borders = borders
        normalc.borders = borders
        normalsub.borders = borders
        subtema.borders = borders
        encabesado_tabla.borders = borders
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('exp_xls_post_part')

        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=Matriculados_Especifico_Proceso_Titulación ' + tipo + random.randint(1, 10000).__str__() + '.xls'

        ws.col(0).width = 1000
        ws.col(1).width = 2500
        ws.col(2).width = 4000
        ws.col(3).width = 3000
        ws.col(4).width = 3000
        ws.col(5).width = 4000
        ws.col(6).width = 4000
        ws.col(7).width = 3200
        ws.col(8).width = 5000
        ws.col(9).width = 4000
        ws.col(10).width = 4000
        ws.col(11).width = 4000
        ws.col(12).width = 4000
        ws.col(13).width = 4000
        ws.col(14).width = 4000
        ws.col(15).width = 4000
        ws.col(16).width = 4000
        ws.col(17).width = 4000
        ws.col(18).width = 4000
        ws.col(19).width = 4000
        ws.col(20).width = 4000
        ws.col(21).width = 4000
        ws.col(22).width = 4000
        ws.col(23).width = 4000
        ws.col(24).width = 4000
        ws.col(25).width = 4000
        ws.col(26).width = 4000
        ws.col(27).width = 4000
        ws.col(28).width = 4000
        ws.col(29).width = 4000
        ws.col(30).width = 4000
        ws.col(31).width = 4000
        ws.col(32).width = 4000
        ws.col(33).width = 4000
        ws.col(34).width = 4000
        ws.col(35).width = 4000
        ws.col(36).width = 4000
        ws.col(37).width = 4000
        ws.col(38).width = 4000
        ws.col(39).width = 4000
        ws.col(40).width = 4000
        ws.col(41).width = 4000
        ws.col(42).width = 4000
        ws.col(43).width = 4000
        ws.col(44).width = 4000
        ws.col(45).width = 4000
        ws.col(46).width = 4000
        ws.col(47).width = 4000
        ws.col(48).width = 4000
        ws.col(49).width = 4000
        ws.col(50).width = 4000
        ws.col(51).width = 4000
        ws.col(52).width = 4000
        ws.col(53).width = 4000
        ws.col(54).width = 4000
        ws.col(55).width = 4000
        ws.col(56).width = 4000
        ws.col(57).width = 4000
        ws.col(58).width = 4000
        ws.col(59).width = 4000
        ws.col(60).width = 4000
        ws.col(61).width = 4000
        ws.col(62).width = 4000
        ws.col(63).width = 4000
        ws.col(64).width = 4000
        ws.col(65).width = 4000
        ws.col(66).width = 4000
        ws.col(67).width = 4000
        ws.col(68).width = 4000
        ws.col(69).width = 4000
        ws.col(70).width = 4000
        ws.col(71).width = 4000
        ws.col(72).width = 4000
        ws.col(73).width = 4000
        ws.col(74).width = 4000
        row_num = 0
        ws.write(row_num, 0, "Nº", encabesado_tabla)
        ws.write(row_num, 1, "COD. \n MATRICULA", encabesado_tabla)
        ws.write(row_num, 2, "FACULTAD", encabesado_tabla)
        ws.write(row_num, 3, "CARRERA", encabesado_tabla)
        ws.write(row_num, 4, u"PARALELO", encabesado_tabla)
        ws.write(row_num, 5, u"CEDULA", encabesado_tabla)
        ws.write(row_num, 6, u"PRIMER APELLIDO", encabesado_tabla)
        ws.write(row_num, 7, u"SEGUNDO APELLIDO", encabesado_tabla)
        ws.write(row_num, 8, u"NOMBRES", encabesado_tabla)
        ws.write(row_num, 9, u"MECANISMO TITULACIÓN", encabesado_tabla)
        ws.write(row_num, 10, u"LINK TESIS", encabesado_tabla)
        ws.write(row_num, 11, u"CODIGO CARRERA SNIESE", encabesado_tabla)
        ws.write(row_num, 12, u"USUARIO", encabesado_tabla)
        ws.write(row_num, 13, u"CARRERA", encabesado_tabla)
        ws.write(row_num, 14, u"PRÁTICAS PRE PROFESIONAL", encabesado_tabla)
        ws.write(row_num, 15, u"VINCULACIÓN", encabesado_tabla)
        ws.write(row_num, 16, u"TELEFONO", encabesado_tabla)
        ws.write(row_num, 17, u"TELEFONO CONVENCIONAL", encabesado_tabla)
        ws.write(row_num, 18, u"E-MAIL", encabesado_tabla)
        ws.write(row_num, 19, u"E-MAIL INSTITUCIONAL", encabesado_tabla)
        ws.write(row_num, 20, u"TIPO DISCAPACIDAD", encabesado_tabla)
        ws.write(row_num, 21, u"LGBTI", encabesado_tabla)
        ws.write(row_num, 22, u"ESTADO DE GESTACION", encabesado_tabla)
        ws.write(row_num, 23, u"ESTADO. MATRICULA", encabesado_tabla)
        ws.write(row_num, 24, u"NIVEL SOCIOECONOMICO", encabesado_tabla)
        ws.write(row_num, 25, u"ID NIVEL", encabesado_tabla)
        ws.write(row_num, 26, u"Nº MATRICULA", encabesado_tabla)
        ws.write(row_num, 27, u"FECHA DE INSCRIPCION", encabesado_tabla)
        ws.write(row_num, 28, u"TUTOR", encabesado_tabla)
        ws.write(row_num, 29, u"INTEGRANTE GRUPO", encabesado_tabla)
        ws.write(row_num, 30, u"NUMERO DE HORAS TUTORIAS", encabesado_tabla)
        ws.write(row_num, 31, u"TEMA", encabesado_tabla)
        ws.write(row_num, 32, u"ESTADO FINAL PREVIO SUSTENTACION", encabesado_tabla)
        ws.write(row_num, 33, 'ESTADO DE REVISIÓN 1', encabesado_tabla)
        ws.write(row_num, 34, 'OBSERVACIÓN DE REVISIÓN 1', encabesado_tabla)
        ws.write(row_num, 35, 'ESTADO DE REVISIÓN 2', encabesado_tabla)
        ws.write(row_num, 36, 'OBSERVACIÓN DE REVISIÓN 2', encabesado_tabla)
        ws.write(row_num, 37, 'ESTADO DE REVISIÓN 3', encabesado_tabla)
        ws.write(row_num, 38, 'OBSERVACIÓN DE REVISIÓN 3', encabesado_tabla)
        ws.write(row_num, 39, 'ESTADO DE REVISIÓN 4', encabesado_tabla)
        ws.write(row_num, 40, 'OBSERVACIÓN DE REVISIÓN 4', encabesado_tabla)
        ws.write(row_num, 41, 'ESTADO DE REVISIÓN 5', encabesado_tabla)
        ws.write(row_num, 42, 'OBSERVACIÓN DE REVISIÓN 5', encabesado_tabla)
        ws.write(row_num, 43, 'ESTADO DE REVISIÓN 6', encabesado_tabla)
        ws.write(row_num, 44, 'OBSERVACIÓN DE REVISIÓN 6', encabesado_tabla)
        ws.write(row_num, 45, 'ESTADO DE REVISIÓN 7', encabesado_tabla)
        ws.write(row_num, 46, 'OBSERVACIÓN DE REVISIÓN 7', encabesado_tabla)
        ws.write(row_num, 47, 'ESTADO DE REVISIÓN 8', encabesado_tabla)
        ws.write(row_num, 48, 'OBSERVACIÓN DE REVISIÓN 8', encabesado_tabla)
        ws.write(row_num, 49, 'ESTADO PARA SUSTENTACION', encabesado_tabla)
        ws.write(row_num, 50, 'ESTADO PRACTICAS PREPROFESIONALLES', encabesado_tabla)
        ws.write(row_num, 51, 'HORAS FALTANTES PPP', encabesado_tabla)
        ws.write(row_num, 52, 'ESTADO MALLLA', encabesado_tabla)
        ws.write(row_num, 53, 'ASIGNATURAS FALTANTES', encabesado_tabla)
        ws.write(row_num, 54, 'ESTADO DEUDA', encabesado_tabla)
        ws.write(row_num, 55, 'VALOR VENCIDO', encabesado_tabla)
        ws.write(row_num, 56, 'ESTADO INGLES', encabesado_tabla)
        ws.write(row_num, 57, 'MODULOS FALTANTES', encabesado_tabla)
        ws.write(row_num, 58, 'ESTADO VINCULACION', encabesado_tabla)
        ws.write(row_num, 59, 'HORAS FALTANTES VINCULACION', encabesado_tabla)
        ws.write(row_num, 60, 'ESTADO COMPUTACION', encabesado_tabla)
        ws.write(row_num, 61, 'CREDITOS FALTANTES COMPUTACION', encabesado_tabla)
        ws.write(row_num, 62, 'MODULOS COMPUTACION CON CREDITOS REALIZADOS', encabesado_tabla)
        ws.write(row_num, 63, 'PRESIDENTE', encabesado_tabla)
        ws.write(row_num, 64, 'SECRETARIO', encabesado_tabla)
        ws.write(row_num, 65, 'INTEGRANTE', encabesado_tabla)
        ws.write(row_num, 66, 'FECHA SUSTENTACION', encabesado_tabla)
        ws.write(row_num, 67, 'HORA INICIO', encabesado_tabla)
        ws.write(row_num, 68, 'LUGAR', encabesado_tabla)
        ws.write(row_num, 69, u"PRUEBA TEÓRICA", encabesado_tabla)
        ws.write(row_num, 70, u"NOTA TRABAJO TITULACIÓN PROYECTO", encabesado_tabla)
        ws.write(row_num, 71, u"NOTA FINAL PERIODO", encabesado_tabla)
        ws.write(row_num, 72, u"ESTADO PRUEBA TEÓRICA", encabesado_tabla)
        ws.write(row_num, 73, u"ESTADO INVESTIGACIÓN", encabesado_tabla)
        ws.write(row_num, 74, u"PERIODO", encabesado_tabla)

        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        data = {}
        if periodo and grupo:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa__status=True), Q(alternativa__grupotitulacion__periodogrupo__id=periodo.id), Q(alternativa__grupotitulacion__id=grupo.id), (Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('alternativa__carrera', 'alternativa', 'inscripcion__persona__apellido1')
        elif periodo:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa__status=True),  Q(alternativa__grupotitulacion__periodogrupo__id=periodo.id), (Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('alternativa__facultad', 'alternativa__carrera', 'alternativa', 'inscripcion__persona__apellido1')
        elif grupo and carrera:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa__grupotitulacion_id=grupo.id), Q(alternativa__carrera_id=carrera.id), (Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('alternativa', 'inscripcion__persona__apellido1')
        elif grupo:

            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa__grupotitulacion_id=grupo.id), (Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('alternativa__carrera', 'alternativa' 'inscripcion__persona__apellido1')
        else:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa=alter),(Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('inscripcion__persona__apellido1')
        row_num = 1
        i = 0
        for matriculados in listamatriculados:
            campo0 = matriculados.id
            campo1 = matriculados.inscripcion.persona.apellido1
            campo2 = matriculados.inscripcion.persona.apellido2
            campo3 = matriculados.inscripcion.persona.nombres

            perfilinscripcion = PerfilInscripcion.objects.get(persona=matriculados.inscripcion.persona, status=True)




            campo25 = matriculados.alternativa.tipotitulacion.nombre
            campo26 = ''  # link de tesis

            campo31 = matriculados.inscripcion.carrera.codigo
            campo32 = matriculados.inscripcion.persona.usuario.username
            campo33 = matriculados.inscripcion.carrera.nombre
            horas_paracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                inscripcion=matriculados.inscripcion, status=True, culminada=True)
            totalhoras = 0
            if horas_paracticas.exists():
                for practicas in horas_paracticas:
                    if practicas.tiposolicitud == 3:
                        if practicas.horahomologacion:
                            totalhoras += practicas.horahomologacion
                    else:
                        totalhoras += practicas.numerohora
            campo34 = totalhoras
            lis = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, proyecto__status=True, inscripcion_id=matriculados.inscripcion.id)
            horas_vinculacion = 0
            for vin in lis:
                horas_vinculacion += vin.horas
            campo35 = horas_vinculacion
            campo38 = matriculados.inscripcion.persona.telefono
            campo40 = matriculados.inscripcion.persona.email


            campo45 = matriculados.inscripcion.persona.emailinst
            campo46 = 'NINGUNA'
            if not perfilinscripcion.tipodiscapacidad == None:
                campo46 = perfilinscripcion.tipodiscapacidad.nombre

            lista_discapacidad = []
            datos_personal = PersonaDatosFamiliares.objects.filter(persona=matriculados.inscripcion.persona, status=True)
            if datos_personal.exists():
                for familiardiscapasidad in datos_personal:
                    if familiardiscapasidad.tienediscapacidad:
                        lista_discapacidad.append([familiardiscapasidad.nombre, familiardiscapasidad.parentesco.nombre])

            campo95 = ''
            if FichaSocioeconomicaINEC.objects.filter(persona=matriculados.inscripcion.persona,status=True).exists():
                ficha = matriculados.inscripcion.persona.mi_ficha()

                campo95 = 'No'
                if matriculados.inscripcion.persona.lgtbi:
                    campo95 = 'Si'
            campo96 = 'No'
            if matriculados.estadogestacion_set.filter(estadogestacion=True, status=True).exists():
                campo96 = 'Si'

            campo97 = 'REPROBADO' if matriculados.reprobo_examen_complexivo() else matriculados.get_estado_display()
            matriculados.reprobo_examen_complexivo()
            telefonoconv = ''
            if not matriculados.inscripcion.persona.telefono_conv == '':
                telefonoconv = matriculados.inscripcion.persona.telefono_conv
            i += 1
            campo98 = ''
            campo99 = ''
            if matriculados.inscripcion.persona.fichasocioeconomicainec_set.exists():
                campo98 = '%s' % matriculados.inscripcion.persona.fichasocioeconomicainec_set.all()[0].grupoeconomico.nombre_corto()
                campo99 = '%s' % matriculados.inscripcion.persona.fichasocioeconomicainec_set.all()[0].grupoeconomico.id
            ws.write(row_num, 0, i, normal)
            ws.write(row_num, 1, campo0, normal)
            ws.write(row_num, 2, matriculados.inscripcion.coordinacion.nombre, normal)
            ws.write(row_num, 3, matriculados.alternativa.carrera.nombre, normal)
            ws.write(row_num, 4, matriculados.alternativa.paralelo, normal)
            ws.write(row_num, 5, matriculados.inscripcion.persona.cedula, normal)
            ws.write(row_num, 6, campo1, normal)
            ws.write(row_num, 7, campo2, normal)
            ws.write(row_num, 8, campo3, normal)
            ws.write(row_num, 9, campo25, normal)
            ws.write(row_num, 10, campo26, normal)
            ws.write(row_num, 11, campo31, normal)
            ws.write(row_num, 12, campo32, normal)
            ws.write(row_num, 13, campo33, normal)
            ws.write(row_num, 14, campo34, normal)
            ws.write(row_num, 15, campo35, normal)
            ws.write(row_num, 16, campo38, normal)
            ws.write(row_num, 17, telefonoconv, normal)
            ws.write(row_num, 18, campo40, normal)
            ws.write(row_num, 19, campo45, normal)
            ws.write(row_num, 20, campo46, normal)
            campo100 = MatriculaTitulacion.objects.values('id').filter(Q(inscripcion=matriculados.inscripcion), (Q(estado=1) | Q(estado=9) | Q(estado=10)), fechainscripcion__lte=matriculados.fechainscripcion).count().__str__()
            campo101 = matriculados.fechainscripcion
            campo102 = ''
            campo103 = ''
            campo104 = ''
            campo105 = ''
            campo106 = ''
            integrante = ""

            if ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True):
                grupo = ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True).order_by('-id')[0]
                campo104 = u"%s" % str(grupo.grupo.horas_totales_tutorias_grupo())
                campo102 = u"%s" % grupo.grupo.tematica.tutor
                campo106 = grupo.grupo.estado_propuesta().get_estado_display() if grupo.grupo.estado_propuesta() else ""
                if grupo.grupo.subtema:
                    campo105 = grupo.grupo.subtema
                for com in grupo.grupo.complexivodetallegrupo_set.filter(status=True, matricula__alternativa__grupotitulacion__periodogrupo=matriculados.alternativa.grupotitulacion.periodogrupo):
                    if matriculados != com.matricula:
                        campo103 = integrante + u"%s" % com.matricula
                col = 33
                tit = 0
                if ComplexivoPropuestaPractica.objects.filter(grupo=grupo.grupo, status=True).exists():
                    for pro in ComplexivoPropuestaPractica.objects.filter(grupo=grupo.grupo, status=True):
                        texto = ''
                        if pro.complexivopropuestapracticaarchivo_set.filter(tipo=1, status=True).exists():
                            fecha = pro.complexivopropuestapracticaarchivo_set.filter(tipo=1, status=True)[0].fecha.strftime('%Y-%m-%d')
                            archivo = 'Si'
                        texto = str(pro.fecharevision) + '-' + str(pro.observacion)
                        ws.write(row_num, tit + col, u"%s" % str(pro.get_estado_display()), normal)
                        col = col + 1
                        ws.write(row_num, tit + col, u"%s" % texto, normal)
                        col = col + 1


            campo107 = 'PENDIENTE PARA SUSTENTAR'
            if matriculados.cumplerequisitos == 2:
                campo107 = 'APTO PARA SUSTENTAR'

            if matriculados.cumplerequisitos == 3:
                campo107 = 'NO APTO PARA SUSTENTAR'


            campo109 = 'NO TIENE PRACTICAS PREPROFESIONALES'
            totalhoras = 0
            malla = matriculados.inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
            practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=matriculados.inscripcion, status=True, culminada=True)
            data['malla_horas_practicas'] = malla.horas_practicas
            tienepracticaspreprofesionales = False
            if practicaspreprofesionalesinscripcion.exists():
                for practicas in practicaspreprofesionalesinscripcion:
                    if practicas.tiposolicitud == 3:
                        totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
                    else:
                        totalhoras += practicas.numerohora
                if totalhoras >= malla.horas_practicas:
                    campo109 = 'TIENE PRACTICAS PREPROFESIONALES'
                    campo110 = 0
                    tienepracticaspreprofesionales = True
            else:
                totalhoras = 0
            if not tienepracticaspreprofesionales:
                horasfaltantes = malla.horas_practicas - totalhoras
                campo110 = horasfaltantes

            total_materias_malla = malla.cantidad_materiasaprobadas()
            cantidad_materias_aprobadas_record = matriculados.inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
            poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
            data['mi_nivel'] = nivel = matriculados.inscripcion.mi_nivel()
            inscripcionmalla = matriculados.inscripcion.malla_inscripcion()

            totalfaltantesmalla = total_materias_malla - cantidad_materias_aprobadas_record
            campo112 = totalfaltantesmalla
            campo111 = 'MALLA IN COMPLETA'
            if poraprobacion >= 100:
                campo111 = 'MALLA COMPLETA'
                campo112 = 0

            campo113 = 'TIENE DEUDA'
            campo114 = matriculados.inscripcion.adeuda_a_la_fecha()
            if matriculados.inscripcion.adeuda_a_la_fecha() == 0:
                campo113 = 'NO TIENE DEUDA'
                campo114 = 0

            campo115 = 'INGLES INCOMPLETO'
            modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
            numero_modulo_ingles = modulo_ingles.count()
            lista = []
            listaid = []
            for modulo in modulo_ingles:
                if matriculados.inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
                    lista.append(modulo.asignatura.nombre)
                    listaid.append(modulo.asignatura.id)
            data['modulo_ingles_aprobados'] = lista
            campo116 = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid]).count()
            if numero_modulo_ingles == len(listaid):
                campo115 = 'INGLES COMPLETO'
                campo116 = 0

            campo117 = 'NO TIENE VINCULACION'
            data['malla_horas_vinculacion'] = malla.horas_vinculacion
            horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, proyecto__status=True, inscripcion_id=matriculados.inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
            horastotal = horastotal if horastotal else 0
            campo118 = malla.horas_vinculacion - horastotal
            if horastotal >= malla.horas_vinculacion:
                campo117 = 'TIENE VINCULACION'
                campo118 = 0

            campo119 = 'NO TIENE COMPUTACION'
            asignatura = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
            record = RecordAcademico.objects.filter(inscripcion__id=matriculados.inscripcion.id, asignatura__id__in=asignatura, aprobada=True)
            creditos_computacion = 0
            malla.creditos_computacion
            listconcreditos = []
            for comp in record:
                listconcreditos.append(comp.asignatura.nombre)
                creditos_computacion += comp.creditos
            campo121 = listconcreditos
            campo120 = malla.creditos_computacion-creditos_computacion
            if creditos_computacion >= malla.creditos_computacion:
                campo119 = 'SI TIENE COMPUTACION'
                campo120 = 0

            presidente = ""
            secretario = ""
            integrantedelegado = ""
            fechagrupo = ""
            horagrupo = ""
            lugargrupo =""
            if ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True):
                grupocomplexivo = ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True)[0]
                if grupocomplexivo.grupo.presidentepropuesta:
                    presidente = u"%s" %grupocomplexivo.grupo.presidentepropuesta.persona

                if grupocomplexivo.grupo.secretariopropuesta:
                    secretario = u"%s" %grupocomplexivo.grupo.secretariopropuesta.persona

                if grupocomplexivo.grupo.delegadopropuesta:
                    integrantedelegado = u"%s" %grupocomplexivo.grupo.delegadopropuesta.persona

                if grupocomplexivo.grupo.fechadefensa:
                    fechagrupo = u"%s" %grupocomplexivo.grupo.fechadefensa

                if grupocomplexivo.grupo.horadefensa:
                    horagrupo = u"%s" %grupocomplexivo.grupo.horadefensa

                if grupocomplexivo.grupo.lugardefensa:
                    lugargrupo = u"%s" %grupocomplexivo.grupo.lugardefensa

            codigoestado = 0
            nomestado = ''
            pexamen = 0
            if matriculados.alternativa.tiene_examen():
                if ComplexivoExamenDetalle.objects.filter(status=True, matricula=matriculados).exists():
                    detalle = ComplexivoExamenDetalle.objects.filter(status=True, matricula=matriculados).order_by('-id')[0]
                    nomestado = detalle.get_estado_display()
                    codigoestado = detalle.estado
                    pexamen = detalle.ponderacion()
            ppropuesta = 0
            ptotal = 0
            if ComplexivoGrupoTematica.objects.values('id').filter(status=True, complexivodetallegrupo__status=True, complexivodetallegrupo__matricula=matriculados).exists():
                ppropuesta = matriculados.notapropuesta()
            if matriculados.alternativa.tipotitulacion.tipo == 1:
                ptotal = ppropuesta
            if matriculados.alternativa.tipotitulacion.tipo == 2:
                ptotal = matriculados.notafinalcomplexivoestado(codigoestado)
            estadotitulacion = matriculados.get_estadotitulacion_display()
            ws.write(row_num, 68, lugargrupo, normal)
            ws.write(row_num, 67, horagrupo, normal)
            ws.write(row_num, 66, fechagrupo, date_format)
            ws.write(row_num, 65, integrantedelegado, normal)
            ws.write(row_num, 64, secretario, normal)
            ws.write(row_num, 63, presidente, normal)
            ws.write(row_num, 62, str(campo121), normal)
            ws.write(row_num, 61, campo120, normal)
            ws.write(row_num, 60, campo119, normal)
            if matriculados.inscripcion.exonerado_practias():
                ws.write(row_num, 59, 'EXONERADO', normal)
            else:
                ws.write(row_num, 59, campo118, normal)
            ws.write(row_num, 58, campo117, normal)
            ws.write(row_num, 57, campo116, normal)
            ws.write(row_num, 56, campo115, normal)
            ws.write(row_num, 55, campo114, normal)
            ws.write(row_num, 54, campo113, normal)
            ws.write(row_num, 53, campo112, normal)
            ws.write(row_num, 52, campo111, normal)
            if matriculados.inscripcion.exonerado_practias():
                ws.write(row_num, 51, 'EXONERADO', normal)
            else:
                ws.write(row_num, 51, campo110, normal)
            ws.write(row_num, 50, campo109, normal)
            ws.write(row_num, 49, campo107, normal)
            ws.write(row_num, 21, campo95, normal)
            ws.write(row_num, 22, campo96, normal)
            ws.write(row_num, 23, campo97, normal)
            ws.write(row_num, 24, campo98, normal)
            ws.write(row_num, 25, campo99, normal)
            ws.write(row_num, 26, campo100, normal)
            ws.write(row_num, 27, campo101, date_format)
            ws.write(row_num, 28, campo102, normal)
            ws.write(row_num, 29, campo103, normal)
            ws.write(row_num, 30, campo104, normal)
            ws.write(row_num, 31, campo105, normal)

            ws.write(row_num, 32, campo106, normal)
            ws.write(row_num, 69, pexamen, normal)
            ws.write(row_num, 70, ppropuesta, normal)
            ws.write(row_num, 71, ptotal, normal)
            ws.write(row_num, 72, nomestado, normal)
            ws.write(row_num, 73, estadotitulacion, normal)
            ws.write(row_num, 74, nombreperiodo, normal)
            row_num += 1
        wb.save(response)
        return response
    except Exception as ex:
        pass


#----------------------REPORTE POR CARRERA Y POR ALTERNATIVA CON VALORES ESPECIFICOS ----------------
def reporte_matrigulados_detalle_carrera(alter, grupo, carrera, periodo):
    try:
        tipo =''
        per = ''
        if periodo and grupo:
            per = str(periodo.nombre)+',  De'+str(periodo.fechainicio.strftime('%Y/%m/%d')+' hasta '+periodo.fechafin.strftime('%Y/%m/%d'))
            tipo = 'Grupo '+ str(grupo.nombre.encode('utf8'))
        elif periodo:
            per = str(periodo.nombre) + ',  De' + str(periodo.fechainicio.strftime('%Y/%m/%d') + ' hasta ' + periodo.fechafin.strftime('%Y/%m/%d'))
            tipo = 'Periodo ' + str(periodo.nombre.encode('utf8'))
        elif grupo and carrera:
            per = str(grupo.periodogrupo.nombre) + ',  De' + str(grupo.periodogrupo.fechainicio.strftime('%Y/%m/%d') + ' hasta ' + grupo.periodogrupo.fechafin.strftime('%Y/%m/%d'))
            tipo = 'Grupo '+str(grupo.nombre.encode('utf8'))
        else:
            per = str(alter.grupotitulacion.periodogrupo.nombre) + ',  De' + str(alter.grupotitulacion.periodogrupo.fechainicio.strftime('%Y/%m/%d') + ' hasta ' + alter.grupotitulacion.periodogrupo.fechafin.strftime('%Y/%m/%d'))
            tipo = str(carrera.nombre.encode('utf8')) if carrera else str(alter.carrera.nombre.encode('utf8'))
        borders = Borders()
        borders.left = 1
        borders.right = 1
        borders.top = 1
        borders.bottom = 1
        __author__ = 'Unemi'
        title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
        normal = easyxf('font: name Arial , height 150; alignment: horiz left')
        encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
        normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
        subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
        normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
        style1 = easyxf(num_format_str='D-MMM-YY')
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        normal.borders = borders
        normalc.borders = borders
        normalsub.borders = borders
        subtema.borders = borders
        encabesado_tabla.borders = borders
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('exp_xls_post_part')

        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=Matriculados_Proceso_Titulación ' + tipo + random.randint(1, 10000).__str__() + '.xls'

        ws.col(0).width = 1000
        ws.col(1).width = 2500
        ws.col(2).width = 4000
        ws.col(3).width = 3000
        ws.col(4).width = 3000
        ws.col(5).width = 4000
        ws.col(6).width = 4000
        ws.col(7).width = 3200
        ws.col(8).width = 5000
        ws.col(9).width = 4000
        ws.col(10).width = 4000
        ws.col(11).width = 4000
        ws.col(12).width = 4000
        ws.col(13).width = 4000
        ws.col(14).width = 4000
        ws.col(15).width = 4000
        ws.col(16).width = 4000
        ws.col(17).width = 4000
        ws.col(18).width = 4000
        ws.col(19).width = 4000
        ws.col(20).width = 4000
        ws.col(21).width = 4000
        ws.col(22).width = 4000
        ws.col(23).width = 4000
        ws.col(24).width = 4000
        ws.col(25).width = 4000
        ws.col(26).width = 4000
        ws.col(27).width = 4000
        ws.col(28).width = 4000
        ws.col(29).width = 4000
        ws.col(30).width = 4000
        ws.col(31).width = 4000
        ws.col(32).width = 4000
        ws.col(33).width = 4000
        ws.col(34).width = 4000
        ws.col(35).width = 4000
        ws.col(36).width = 4000
        ws.col(37).width = 4000
        ws.col(38).width = 4000
        ws.col(39).width = 4000
        ws.col(40).width = 4000
        ws.col(41).width = 4000
        ws.col(42).width = 4000
        ws.col(43).width = 4000
        ws.col(44).width = 4000
        ws.col(45).width = 4000
        ws.col(46).width = 4000
        ws.col(47).width = 4000
        ws.col(48).width = 4000
        ws.col(49).width = 4000
        ws.col(50).width = 4000
        ws.col(51).width = 4000
        ws.col(52).width = 4000
        ws.col(53).width = 4000
        ws.col(54).width = 4000
        ws.col(55).width = 4000
        ws.col(56).width = 4000
        ws.col(57).width = 4000
        ws.col(58).width = 4000
        ws.col(59).width = 4000
        ws.col(60).width = 4000
        ws.col(61).width = 4000
        ws.col(62).width = 4000
        ws.col(63).width = 4000
        ws.col(64).width = 4000
        ws.col(65).width = 4000
        ws.col(66).width = 4000
        ws.col(67).width = 4000
        ws.col(68).width = 4000
        ws.col(69).width = 4000
        ws.col(70).width = 4000
        ws.col(71).width = 4000
        ws.col(72).width = 4000
        ws.col(73).width = 4000
        ws.col(74).width = 4000
        ws.col(75).width = 4000
        ws.col(76).width = 4000
        ws.col(77).width = 4000
        ws.col(78).width = 4000
        ws.col(79).width = 4000
        ws.col(80).width = 4000
        ws.col(81).width = 4000
        ws.col(82).width = 4000
        ws.col(83).width = 4000
        ws.col(84).width = 4000
        ws.col(85).width = 4000
        ws.col(86).width = 4000
        ws.col(87).width = 4000
        ws.col(88).width = 4000
        ws.col(89).width = 4000
        ws.col(90).width = 4000
        ws.col(91).width = 4000
        ws.col(92).width = 4000
        ws.col(93).width = 4000
        ws.col(94).width = 4000
        ws.col(95).width = 4000
        ws.col(96).width = 4000
        ws.col(97).width = 4000
        ws.col(98).width = 4000
        ws.col(99).width = 4000
        ws.col(100).width = 4000
        ws.col(101).width = 4000
        ws.col(102).width = 4000
        ws.col(103).width = 4000
        ws.col(104).width = 4000
        ws.col(105).width = 4000
        ws.col(106).width = 4000
        ws.col(107).width = 10000
        ws.col(108).width = 10000
        ws.col(109).width = 10000
        ws.col(110).width = 10000
        ws.col(111).width = 10000
        ws.col(112).width = 10000
        ws.col(113).width = 10000
        row_num = 0
        ws.write(row_num, 0, "Nº", encabesado_tabla)
        ws.write(row_num, 1, "COD. \n MATRICULA", encabesado_tabla)
        ws.write(row_num, 2, "FACULTAD", encabesado_tabla)
        ws.write(row_num, 3, "CARRERA", encabesado_tabla)
        ws.write(row_num, 4, u"PARALELO", encabesado_tabla)
        ws.write(row_num, 5, u"CEDULA", encabesado_tabla)
        ws.write(row_num, 6, u"PRIMER APELLIDO", encabesado_tabla)
        ws.write(row_num, 7, u"SEGUNDO APELLIDO", encabesado_tabla)
        ws.write(row_num, 8, u"NOMBRES", encabesado_tabla)
        ws.write(row_num, 9, u"SEXO", encabesado_tabla)
        ws.write(row_num, 10, u"ETNIA", encabesado_tabla)
        ws.write(row_num, 11, u"FECHA NACIMIENTO", encabesado_tabla)
        ws.write(row_num, 12, u"PAIS/NACIONALIDAD", encabesado_tabla)
        ws.write(row_num, 13, u"PAIS RESIDENCIA", encabesado_tabla)
        ws.write(row_num, 14, u"PROVINCIA RESIDENCIA", encabesado_tabla)
        ws.write(row_num, 15, u"CANTON RESIDENCIA", encabesado_tabla)
        ws.write(row_num, 16, u"FECHA/INICIO ESTUDIO", encabesado_tabla)
        ws.write(row_num, 17, u"FECHA EGRESAMIENTO", encabesado_tabla)
        ws.write(row_num, 18, u"DURACION", encabesado_tabla)
        ws.write(row_num, 19, u"TIPO DURACION", encabesado_tabla)
        ws.write(row_num, 20, u"TITULO BACHILLER", encabesado_tabla)
        ws.write(row_num, 21, u"TIPO COLEGIO", encabesado_tabla)
        ws.write(row_num, 22, u"RECONOCIMIENTO ESTUDIO PREVIOS", encabesado_tabla)
        ws.write(row_num, 23, u"CARRERA ESTUDIOS PREVIOS", encabesado_tabla)
        ws.write(row_num, 24, u"TIEMPO ESTUDIO RECOMENDACIÓN", encabesado_tabla)
        ws.write(row_num, 25, u"TIPO DE DURACIÓN DE RECONOCIMIENTO", encabesado_tabla)
        ws.write(row_num, 26, u"FECHA ACTA GRADO", encabesado_tabla)
        ws.write(row_num, 27, u"NÚMERO ACTA GRADO", encabesado_tabla)
        ws.write(row_num, 28, u"FECHA REFRENDACIÓN", encabesado_tabla)
        ws.write(row_num, 29, u"MECANISMO TITULACIÓN", encabesado_tabla)
        ws.write(row_num, 30, u"LINK TESIS", encabesado_tabla)
        ws.write(row_num, 31, u"NOTA PROMEDIO ACUMULADO", encabesado_tabla)
        ws.write(row_num, 32, u"NOTA TRABAJO TITULACIÓN GRADUADO", encabesado_tabla)
        ws.write(row_num, 33, u"NOMBRE RECTOR", encabesado_tabla)
        ws.write(row_num, 34, u"OBSERVACIONES", encabesado_tabla)
        ws.write(row_num, 35, u"CODIGO CARRERA SNIESE", encabesado_tabla)
        ws.write(row_num, 36, u"USUARIO", encabesado_tabla)
        ws.write(row_num, 37, u"CARRERA", encabesado_tabla)
        ws.write(row_num, 38, u"PRÁTICAS PRE PROFESIONAL", encabesado_tabla)
        ws.write(row_num, 39, u"VINCULACIÓN", encabesado_tabla)
        ws.write(row_num, 40, u"NOTA GRADO", encabesado_tabla)
        ws.write(row_num, 41, u"REG. SENESCYT", encabesado_tabla)
        ws.write(row_num, 42, u"TELEFONO", encabesado_tabla)
        ws.write(row_num, 43, u"TELEFONO CONVENCIONAL", encabesado_tabla)
        ws.write(row_num, 44, u"TIPO SANGRE", encabesado_tabla)
        ws.write(row_num, 45, u"E-MAIL", encabesado_tabla)
        ws.write(row_num, 46, u"NIVEL/MATRICULA", encabesado_tabla)
        ws.write(row_num, 47, u"FECHA CONVALIDACIÓN", encabesado_tabla)
        ws.write(row_num, 48, u"FECHA PRIMER NIVEL", encabesado_tabla)
        ws.write(row_num, 49, u"ESTADO CIVIL", encabesado_tabla)
        ws.write(row_num, 50, u"E-MAIL INSTITUCIONAL", encabesado_tabla)
        ws.write(row_num, 51, u"TIPO DISCAPACIDAD", encabesado_tabla)
        ws.write(row_num, 52, u"PORCENTAJE DISCAPACIDAD", encabesado_tabla)
        ws.write(row_num, 53, u"HOGAR", encabesado_tabla)
        ws.write(row_num, 54, u"FAMILIAR CON DISCAPACIDAD", encabesado_tabla)
        ws.write(row_num, 55, u"PARENTESCO", encabesado_tabla)
        ws.write(row_num, 56, u"TIPO HOGAR", encabesado_tabla)
        ws.write(row_num, 57, u"¿EL ESTUDIANTE ES CABEZA DE FAMILIA?", encabesado_tabla)
        ws.write(row_num, 58, u"¿EL ESTUDIANTE DEPENDE ECÓNOMICAMENTE DE SUS PADRES U OTRAS PERSONAS", encabesado_tabla)
        ws.write(row_num, 59, u"¿QUIÉN CUBRE LOS GASTOS DEL ESTUDIANTE?", encabesado_tabla)
        ws.write(row_num, 60, u"¿CUAL ES EL TIPO DE VIVIENDA?", encabesado_tabla)
        ws.write(row_num, 61, u"¿SU VIVIENDA ES?", encabesado_tabla)
        ws.write(row_num, 62, u"MATERIAL PREDOMINANTE DE LAS PAREDES", encabesado_tabla)
        ws.write(row_num, 63, u"MATERIAL PREDOMINANTE DEL PISO", encabesado_tabla)
        ws.write(row_num, 64, u"¿CUANTOS CUARTOS DE BAÑO CON DUCHA TIENE SU HOGAR?", encabesado_tabla)
        ws.write(row_num, 65, u"¿EL TIPO DE SERVICIO HIGIÉNICO CON QUE CUENTA SU HOGAR ES?", encabesado_tabla)
        ws.write(row_num, 66, u"¿TIENE EL HOGAR SERVICIO DE TELEFONO CONVENCIONAL?", encabesado_tabla)
        ws.write(row_num, 67, u"¿TIENE EL HOGAR COCINA CON HORNO?", encabesado_tabla)
        ws.write(row_num, 68, u"¿TIENE EL HOGAR UNA REFRIGERADORA?", encabesado_tabla)
        ws.write(row_num, 69, u"¿TIENE EL HOGAR UNA LAVADORA?", encabesado_tabla)
        ws.write(row_num, 70, u"¿TIENE EL HOGAR UN EQUIPO DE SONIDO?", encabesado_tabla)
        ws.write(row_num, 71, u"¿CUÁNTOS TV A COLOR TIENE EN EL HOGAR?", encabesado_tabla)
        ws.write(row_num, 72, u"¿CUÁNTOS VEHÍCULOS DE USO EXCLUSIVO  TIENE EL HOGAR", encabesado_tabla)
        ws.write(row_num, 73, u"SALA", encabesado_tabla)
        ws.write(row_num, 74, u"COMEDOR", encabesado_tabla)
        ws.write(row_num, 75, u"COCINA", encabesado_tabla)
        ws.write(row_num, 76, u"BAÑO", encabesado_tabla)
        ws.write(row_num, 77, u"LUZ", encabesado_tabla)
        ws.write(row_num, 78, u"AGUA", encabesado_tabla)
        ws.write(row_num, 79, u"ALCANTARILLADO", encabesado_tabla)
        ws.write(row_num, 80, u"TELEFONO", encabesado_tabla)
        ws.write(row_num, 81, u"ENFERMEDADES HEREDITARIAS", encabesado_tabla)
        ws.write(row_num, 82, u"DIABETES", encabesado_tabla)
        ws.write(row_num, 83, u"HIPERTENSIÓN", encabesado_tabla)
        ws.write(row_num, 84, u"CÁNCER", encabesado_tabla)
        ws.write(row_num, 85, u"ALZHEIMER", encabesado_tabla)
        ws.write(row_num, 86, u"VITILÍGO", encabesado_tabla)
        ws.write(row_num, 87, u"DESGASTAMIENTO CEREBRAL", encabesado_tabla)
        ws.write(row_num, 88, u"PIEL BLANCA", encabesado_tabla)
        ws.write(row_num, 89, u"OTRAS", encabesado_tabla)
        ws.write(row_num, 90, u"¿EXISTEN CASOS  DE VIH/SIDA EN LA FAMILIA?", encabesado_tabla)
        ws.write(row_num, 91, u"ENFERMEDADES COMUNES EN LA FAMILIA", encabesado_tabla)
        ws.write(row_num, 92, u"¿CUÁL ES EL NIVEL DE ESTUDIOS DE JEFE DE HOGAR?", encabesado_tabla)
        ws.write(row_num, 93, u"¿ALGUIEN EN EL HOGAR ESTÁ \nAFILIADO AL IESS Y/O SEGURO \nISSPOL O ISSFA?", encabesado_tabla)
        ws.write(row_num, 94, u"ALGUIEN EN EL HOGAR TIENE \nSEGURO DE SALUD PRIVADA, CON O \nSIN HOSPITALIZACIÓN Y/O SEGURO \nDE VIDA?",encabesado_tabla)
        ws.write(row_num, 95, u"¿CUAL ES LA OCUPACIÓN DEL JEFE DE HOGAR?", encabesado_tabla)
        ws.write(row_num, 96, u"¿TIENE EL HOGAR SERVICIO DE INTERNET?", encabesado_tabla)
        ws.write(row_num, 97, u"¿TIENE COMPUTADORA DE ESCRITORIO?", encabesado_tabla)
        ws.write(row_num, 98, u"¿TIENE COMPUTADORA PORTÁTIL?", encabesado_tabla)
        ws.write(row_num, 99, u"GÉNERO", encabesado_tabla)
        ws.write(row_num, 100, u"LGBTI", encabesado_tabla)
        ws.write(row_num, 101, u"ESTADO DE GESTACION", encabesado_tabla)
        ws.write(row_num, 102, u"ESTADO. MATRICULA", encabesado_tabla)
        ws.write(row_num, 103, u"NIVEL SOCIOECONOMICO", encabesado_tabla)
        ws.write(row_num, 104, u"ID NIVEL", encabesado_tabla)
        ws.write(row_num, 105, u"Nº MATRICULA", encabesado_tabla)
        ws.write(row_num, 106, u"FECHA DE INSCRIPCION", encabesado_tabla)
        ws.write(row_num, 107, u"TUTOR", encabesado_tabla)
        ws.write(row_num, 108, u"INTEGRANTE GRUPO", encabesado_tabla)
        ws.write(row_num, 109, u"NUMERO DE HORAS TUTORIAS", encabesado_tabla)
        ws.write(row_num, 110, u"TEMA", encabesado_tabla)
        ws.write(row_num, 111, u"ESTADO FINAL PREVIO SUSTENTACION", encabesado_tabla)
        ws.write(row_num, 112, 'ESTADO DE REVISIÓN 1', encabesado_tabla)
        ws.write(row_num, 113, 'OBSERVACIÓN DE REVISIÓN 1', encabesado_tabla)
        ws.write(row_num, 114, 'ESTADO DE REVISIÓN 2', encabesado_tabla)
        ws.write(row_num, 115, 'OBSERVACIÓN DE REVISIÓN 2', encabesado_tabla)
        ws.write(row_num, 116, 'ESTADO DE REVISIÓN 3', encabesado_tabla)
        ws.write(row_num, 117, 'OBSERVACIÓN DE REVISIÓN 3', encabesado_tabla)
        ws.write(row_num, 118, 'ESTADO DE REVISIÓN 4', encabesado_tabla)
        ws.write(row_num, 119, 'OBSERVACIÓN DE REVISIÓN 4', encabesado_tabla)
        ws.write(row_num, 120, 'ESTADO DE REVISIÓN 5', encabesado_tabla)
        ws.write(row_num, 121, 'OBSERVACIÓN DE REVISIÓN 5', encabesado_tabla)
        ws.write(row_num, 122, 'ESTADO DE REVISIÓN 6', encabesado_tabla)
        ws.write(row_num, 123, 'OBSERVACIÓN DE REVISIÓN 6', encabesado_tabla)
        ws.write(row_num, 124, 'ESTADO DE REVISIÓN 7', encabesado_tabla)
        ws.write(row_num, 125, 'OBSERVACIÓN DE REVISIÓN 7', encabesado_tabla)
        ws.write(row_num, 126, 'ESTADO DE REVISIÓN 8', encabesado_tabla)
        ws.write(row_num, 127, 'OBSERVACIÓN DE REVISIÓN 8', encabesado_tabla)
        ws.write(row_num, 128, 'ESTADO PARA SUSTENTACION', encabesado_tabla)
        ws.write(row_num, 129, 'FECHA GENERADA ESTADO SUSTENTACION', encabesado_tabla)
        ws.write(row_num, 130, 'HORA GENERADA ESTADO SUSTENTACION', encabesado_tabla)
        ws.write(row_num, 131, 'ESTADO PRACTICAS PREPROFESIONALLES', encabesado_tabla)
        ws.write(row_num, 132, 'HORAS FALTANTES PPP', encabesado_tabla)
        ws.write(row_num, 133, 'ESTADO MALLLA', encabesado_tabla)
        ws.write(row_num, 134, 'ASIGNATURAS FALTANTES', encabesado_tabla)
        ws.write(row_num, 135, 'ESTADO DEUDA', encabesado_tabla)
        ws.write(row_num, 136, 'VALOR VENCIDO', encabesado_tabla)
        ws.write(row_num, 137, 'ESTADO INGLES', encabesado_tabla)
        ws.write(row_num, 138, 'MODULOS FALTANTES', encabesado_tabla)
        ws.write(row_num, 139, 'ESTADO VINCULACION', encabesado_tabla)
        ws.write(row_num, 140, 'HORAS FALTANTES VINCULACION', encabesado_tabla)
        ws.write(row_num, 141, 'ESTADO COMPUTACION', encabesado_tabla)
        ws.write(row_num, 142, 'CREDITOS FALTANTES COMPUTACION', encabesado_tabla)
        ws.write(row_num, 143, 'MODULOS COMPUTACION CON CREDITOS REALIZADOS', encabesado_tabla)
        ws.write(row_num, 144, 'PRESIDENTE', encabesado_tabla)
        ws.write(row_num, 145, 'SECRETARIO', encabesado_tabla)
        ws.write(row_num, 146, 'INTEGRANTE', encabesado_tabla)
        ws.write(row_num, 147, 'FECHA SUSTENTACION', encabesado_tabla)
        ws.write(row_num, 148, 'HORA INICIO', encabesado_tabla)
        ws.write(row_num, 149, 'LUGAR', encabesado_tabla)
        ws.write(row_num, 150, u"PRUEBA TEÓRICA", encabesado_tabla)
        ws.write(row_num, 151, u"NOTA TRABAJO TITULACIÓN PROYECTO", encabesado_tabla)
        ws.write(row_num, 152, u"NOTA FINAL PERIODO", encabesado_tabla)
        ws.write(row_num, 153, u"ESTADO PRUEBA TEÓRICA", encabesado_tabla)
        ws.write(row_num, 154, u"ESTADO INVESTIGACIÓN", encabesado_tabla)
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        data = {}
        if periodo and grupo:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa__status=True), Q(alternativa__grupotitulacion__periodogrupo__id=periodo.id), Q(alternativa__grupotitulacion__id=grupo.id),
                                                                                    (Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('alternativa__carrera', 'alternativa', 'inscripcion__persona__apellido1')
        elif periodo:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa__status=True),  Q(alternativa__grupotitulacion__periodogrupo__id=periodo.id), (Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('alternativa__facultad', 'alternativa__carrera', 'alternativa', 'inscripcion__persona__apellido1')
        elif grupo and carrera:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa__grupotitulacion_id=grupo.id), Q(alternativa__carrera_id=carrera.id), (Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('alternativa', 'inscripcion__persona__apellido1')
        elif grupo:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa__grupotitulacion_id=grupo.id),
                                                                                    (Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('alternativa__carrera', 'alternativa' 'inscripcion__persona__apellido1')
        else:
            listamatriculados = MatriculaTitulacion.objects.select_related().filter(Q(status=True), Q(alternativa=alter),(Q(estado=1)|Q(estado=9)|Q(estado=10))).order_by('inscripcion__persona__apellido1')
        row_num = 1
        i = 0
        for matriculados in listamatriculados:

            if matriculados.id == 1954:
                c = matriculados.id

            campo0 = matriculados.id
            campo1 = matriculados.inscripcion.persona.apellido1
            campo2 = matriculados.inscripcion.persona.apellido2
            campo3 = matriculados.inscripcion.persona.nombres
            campo4 = matriculados.inscripcion.persona.sexo.nombre
            perfilinscripcion = PerfilInscripcion.objects.get(persona=matriculados.inscripcion.persona, status=True)
            campo5 = perfilinscripcion.raza.nombre
            campo6 = matriculados.inscripcion.persona.nacimiento.strftime('%Y/%m/%d')
            campo7 = matriculados.inscripcion.persona.pais.nombre
            campo8 = matriculados.inscripcion.persona.nacionalidad
            campo9 = matriculados.inscripcion.persona.pais.nombre
            campo10 = matriculados.inscripcion.persona.provincia.nombre
            campo11 = ""
            if not matriculados.inscripcion.persona.canton is None:
                campo11 = matriculados.inscripcion.persona.canton.nombre



            campo12 = ''
            if not matriculados.inscripcion.fechainicioprimernivel is None:
                campo12 = matriculados.inscripcion.fechainicioprimernivel.strftime('%Y/%m/%d')
            campo13 = ''
            if Egresado.objects.filter(inscripcion=matriculados.inscripcion, status=True).exists():
                egresado = Egresado.objects.get(inscripcion=matriculados.inscripcion, status=True)
                campo13 = egresado.fechaegreso.strftime('%Y/%m/%d')
            campo14 = matriculados.duracion_estudio()
            campo15 = ''
            campo16 = matriculados.inscripcion.especialidad.nombre if not matriculados.inscripcion.especialidad is None else ''
            campo17 = matriculados.inscripcion.colegio
            campo18 = ''
            listaestudios_previos = []
            if EstudioInscripcion.objects.filter(status=True, persona=matriculados.inscripcion.persona).exists():
                estudios = EstudioInscripcion.objects.filter(status=True,persona=matriculados.inscripcion.persona)
                for estudios_pervios in estudios:
                    listaestudios_previos.append(estudios_pervios.carrera)  # estudiosde estudios previos'
            campo19 = ''  # carrera estudios previos'
            campo20 = ''  # tiempo de duracion de reconocimiento
            campo21 = ''
            campo22 = ''
            campo23 = ''
            campo24 = ''
            campo28 = ''
            campo36 = ''
            campo37 = ''
            if Graduado.objects.filter(inscripcion=matriculados.inscripcion, status=True).exists():
                graduado = Graduado.objects.get(inscripcion=matriculados.inscripcion, status=True)
                campo22 = graduado.fechaactagrado.strftime('%Y/%m/%d') if graduado.fechaactagrado else ''
                campo23 = graduado.numeroactagrado if graduado.numeroactagrado else ''
                campo24 = graduado.fecharefrendacion.strftime('%Y/%m/%d') if graduado.fecharefrendacion else ''
                campo28 = graduado.promediotitulacion if graduado.promediotitulacion else ''
                campo36 = graduado.notagraduacion if graduado.notagraduacion else ''
                campo37 = graduado.registro if graduado.registro else ''

            campo25 = matriculados.alternativa.tipotitulacion.nombre
            campo26 = ''  # link de tesis
            campo27 = matriculados.inscripcion.promedio_record()
            campo29 = ''  # nombre del rector
            campo30 = ''  # observaciones
            campo31 = matriculados.inscripcion.carrera.codigo
            campo32 = matriculados.inscripcion.persona.usuario.username
            campo33 = matriculados.inscripcion.carrera.nombre
            horas_paracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                inscripcion=matriculados.inscripcion, status=True, culminada=True)
            totalhoras = 0
            if horas_paracticas.exists():
                for practicas in horas_paracticas:
                    if practicas.tiposolicitud == 3:
                        if practicas.horahomologacion:
                            totalhoras += practicas.horahomologacion
                    else:
                        totalhoras += practicas.numerohora
            campo34 = totalhoras
            lis = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, proyecto__status=True, inscripcion_id=matriculados.inscripcion.id)
            horas_vinculacion = 0
            for vin in lis:
                horas_vinculacion += vin.horas
            campo35 = horas_vinculacion
            campo38 = matriculados.inscripcion.persona.telefono
            campo39 = u'%s' % matriculados.inscripcion.persona.sangre if not matriculados.inscripcion.persona.sangre is None  else ''
            campo40 = matriculados.inscripcion.persona.email
            campo41 = str(matriculados.inscripcion.mi_nivel())
            campo42 = ''
            if not matriculados.inscripcion.fechainicioconvalidacion is None:
                campo42 = matriculados.inscripcion.fechainicioconvalidacion.strftime('%Y/%m/%d')
            campo43 = ''
            if not matriculados.inscripcion.fechainicioprimernivel is None:
                campo43 = matriculados.inscripcion.fechainicioprimernivel.strftime('%Y/%m/%d')
            campo44 = str(matriculados.inscripcion.persona.estado_civil())
            campo45 = matriculados.inscripcion.persona.emailinst
            campo46 = 'NINGUNA'
            if not perfilinscripcion.tipodiscapacidad == None:
                campo46 = perfilinscripcion.tipodiscapacidad.nombre
            campo47 = perfilinscripcion.porcientodiscapacidad
            campo48 = ''  # hogar
            campo49 = ''
            campo50 = ''
            lista_discapacidad = []
            datos_personal = PersonaDatosFamiliares.objects.filter(persona=matriculados.inscripcion.persona, status=True)
            if datos_personal.exists():
                for familiardiscapasidad in datos_personal:
                    if familiardiscapasidad.tienediscapacidad:
                        lista_discapacidad.append([familiardiscapasidad.nombre, familiardiscapasidad.parentesco.nombre])
            campo51 = ''
            campo52 = ''
            campo53 = ''
            campo54 = ''
            campo55 = ''
            campo56 = ''
            campo57 = ''
            campo58 = ''
            campo59 = ''
            campo60 = ''
            campo61 = ''
            campo62 = ''
            campo63 = ''
            campo64 = ''
            campo65 = ''
            campo66 = ''
            campo67 = ''
            campo68 = ''
            campo69 = ''
            campo70 = ''
            campo71 = ''
            campo72 = ''
            campo73 = ''
            campo74 = ''
            campo75 = ''
            campo76 = ''
            campo77 = ''
            campo78 = ''
            campo79 = ''
            campo80 = ''
            campo81 = ''
            campo82 = ''
            campo83 = ''
            campo84 = ''
            campo85 = ''
            campo86 = ''
            campo87 = ''
            campo88 = ''
            campo89 = ''
            campo90 = ''
            campo91 = ''
            campo92 = ''
            campo93 = ''
            campo94 = ''
            campo95 = ''
            if FichaSocioeconomicaINEC.objects.filter(persona=matriculados.inscripcion.persona,status=True).exists():
                ficha = matriculados.inscripcion.persona.mi_ficha()
                campo51 = ''
                if not ficha.tipohogar is None:
                    campo51 = str(ficha.tipohogar.nombre)
                campo52 = 'No'
                if ficha.escabezafamilia:
                    campo52 = 'Si'
                campo53 = 'No'
                campo54 = ''
                if ficha.esdependiente:
                    campo53 = 'Si'
                    campo54 = str(ficha.personacubregasto)
                campo55 = ''
                if not ficha.tipovivienda is None:
                    campo55 = ficha.tipovivienda.nombre
                campo56 = ''
                if not ficha.tipoviviendapro is None:
                    campo56 = ficha.tipoviviendapro.nombre
                campo57 = ''
                if not ficha.materialpared is None:
                    campo57 = ficha.materialpared.nombre
                campo58 = ''
                if not ficha.materialpiso is None:
                    campo58 = ficha.materialpiso.nombre
                campo59 = ''
                if not ficha.cantbannoducha is None:
                    campo59 = ficha.cantbannoducha.nombre
                campo60 = ''
                if not ficha.tiposervhig is None:
                    campo60 = ficha.tiposervhig.nombre
                campo61 = 'No'
                if ficha.tienetelefconv:
                    campo61 = 'Si'
                campo62 = 'No'
                if ficha.tienecocinahorno:
                    campo62 = 'Si'
                campo63 = 'No'
                if ficha.tienerefrig:
                    campo63 = 'Si'
                campo64 = 'No'
                if ficha.tienelavadora:
                    campo64 = 'Si'
                campo65 = 'No'
                if ficha.tienemusica:
                    campo65 = 'Si'
                campo66 = ''
                if not ficha.canttvcolor is None:
                    campo66 = ficha.canttvcolor.nombre
                campo67 = ''
                if not ficha.cantvehiculos is None:
                    campo67 = ficha.cantvehiculos.nombre
                campo68 = 'No'
                if ficha.tienesala:
                    campo68 = 'Si'
                campo69 = 'No'
                if ficha.tienecomedor:
                    campo69 = 'Si'
                campo70 = 'No'
                if ficha.tienecocina:
                    campo70 = 'Si'
                campo71 = 'No'
                if ficha.tienebanio:
                    campo71 = 'Si'
                campo72 = 'No'
                if ficha.tieneluz:
                    campo72 = 'Si'
                campo73 = 'No'
                if ficha.tieneagua:
                    campo73 = 'Si'
                campo74 = 'No'
                if ficha.tienealcantarilla:
                    campo74 = 'Si'
                campo75 = 'No'
                if ficha.tienetelefono:
                    campo75 = 'Si'
                campo76 = 'No'
                if ficha.tienetelefono:
                    campo76 = 'Si'
                    #    enfermedades erideritarias
                campo77 = 'No'
                if ficha.tienediabetes:
                    campo77 = 'Si'
                campo78 = 'No'
                if ficha.tienehipertencion:
                    campo78 = 'Si'
                campo79 = 'No'
                if ficha.tienecancer:
                    campo79 = 'Si'
                campo80 = 'No'
                if ficha.tienealzheimer:
                    campo80 = 'Si'
                campo81 = 'No'
                if ficha.tienevitiligo:
                    campo81 = 'Si'
                campo82 = 'No'
                if ficha.tienedesgastamiento:
                    campo82 = 'Si'
                campo83 = 'No'
                if ficha.tienepielblanca:
                    campo83 = 'Si'
                campo84 = ''
                if not ficha.otrasenfermedades is None:
                    campo84 = ficha.otrasenfermedades
                campo85 = 'No'
                if ficha.tienesida:
                    campo85 = 'Si'
                campo86 = ''
                if not ficha.enfermedadescomunes is None:
                    campo86 = ficha.enfermedadescomunes
                campo87 = ''
                if not ficha.niveljefehogar is None:
                    campo87 = ficha.niveljefehogar.nombre
                campo88 = 'No'
                if ficha.alguienafiliado:
                    campo88 = 'Si'
                campo89 = 'No'
                if ficha.alguienseguro:
                    campo89 = 'Si'
                campo90 = ''
                if not ficha.ocupacionjefehogar is None:
                    campo90 = ficha.ocupacionjefehogar.nombre
                campo91 = 'No'
                if ficha.tieneinternet:
                    campo91 = 'Si'
                campo92 = 'No'
                if ficha.tienedesktop:
                    campo92 = 'Si'
                campo93 = 'No'
                if ficha.tienelaptop:
                    campo93 = 'Si'
                campo94 = ''  # genero
                campo95 = 'No'
                if matriculados.inscripcion.persona.lgtbi:
                    campo95 = 'Si'
            campo96 = 'No'
            if matriculados.estadogestacion_set.filter(estadogestacion=True, status=True).exists():
                campo96 = 'Si'
            campo97 = 'REPROBADO' if matriculados.reprobo_examen_complexivo() else matriculados.get_estado_display()
            matriculados.reprobo_examen_complexivo()
            telefonoconv = ''
            if not matriculados.inscripcion.persona.telefono_conv == '':
                telefonoconv = matriculados.inscripcion.persona.telefono_conv
            i += 1
            campo98 = ''
            campo99 = ''
            if matriculados.inscripcion.persona.fichasocioeconomicainec_set.exists():
                campo98 = '%s' % matriculados.inscripcion.persona.fichasocioeconomicainec_set.all()[0].grupoeconomico.nombre_corto()
                campo99 = '%s' % matriculados.inscripcion.persona.fichasocioeconomicainec_set.all()[0].grupoeconomico.id
            ws.write(row_num, 0, i, normal)
            ws.write(row_num, 1, campo0, normal)
            ws.write(row_num, 2, matriculados.inscripcion.coordinacion.nombre, normal)
            ws.write(row_num, 3, matriculados.alternativa.carrera.nombre, normal)
            ws.write(row_num, 4, matriculados.alternativa.paralelo, normal)
            ws.write(row_num, 5, matriculados.inscripcion.persona.cedula, normal)
            ws.write(row_num, 6, campo1, normal)
            ws.write(row_num, 7, campo2, normal)
            ws.write(row_num, 8, campo3, normal)
            ws.write(row_num, 9, campo4, normal)
            ws.write(row_num, 10, campo5, normal)
            ws.write(row_num, 11, str(campo6), normal)
            ws.write(row_num, 12, campo7 + '/' + campo8, normal)
            ws.write(row_num, 13, campo9, normal)
            ws.write(row_num, 14, campo10, normal)
            ws.write(row_num, 15, campo11, normal)
            ws.write(row_num, 16, campo12, normal)
            ws.write(row_num, 17, campo13, normal)
            ws.write(row_num, 18, campo14, normal)
            ws.write(row_num, 19, campo15, normal)
            ws.write(row_num, 20, campo16, normal)
            ws.write(row_num, 21, campo17, normal)
            ws.write(row_num, 22, campo18, normal)
            ws.write(row_num, 23, campo19, normal)
            ws.write(row_num, 24, campo20, normal)
            ws.write(row_num, 25, campo21, normal)
            ws.write(row_num, 26, campo22, normal)
            ws.write(row_num, 27, campo23, normal)
            ws.write(row_num, 28, campo24, normal)
            ws.write(row_num, 29, campo25, normal)
            ws.write(row_num, 30, campo26, normal)
            ws.write(row_num, 31, campo27, normal)
            ws.write(row_num, 32, campo28, normal)
            ws.write(row_num, 33, campo29, normal)
            ws.write(row_num, 34, campo30, normal)
            ws.write(row_num, 35, campo31, normal)
            ws.write(row_num, 36, campo32, normal)
            ws.write(row_num, 37, campo33, normal)
            ws.write(row_num, 38, campo34, normal)
            ws.write(row_num, 39, campo35, normal)
            ws.write(row_num, 40, campo36, normal)
            ws.write(row_num, 41, campo37, normal)
            ws.write(row_num, 42, campo38, normal)
            ws.write(row_num, 43, telefonoconv, normal)
            ws.write(row_num, 44, campo39, normal)
            ws.write(row_num, 45, campo40, normal)
            ws.write(row_num, 46, campo41, normal)
            ws.write(row_num, 47, campo42, normal)
            ws.write(row_num, 48, campo43, normal)
            ws.write(row_num, 49, campo44, normal)
            ws.write(row_num, 50, campo45, normal)
            ws.write(row_num, 51, campo46, normal)
            ws.write(row_num, 52, campo47, normal)
            ws.write(row_num, 53, campo48, normal)
            if len(lista_discapacidad) > 0:
                if not len(lista_discapacidad) == 1:
                    separar = ""
                    for lis in lista_discapacidad:
                        campo49 = str(campo49) + separar + lis[0]
                        campo50 = str(campo50) + separar + lis[1]
                        separar = " - "
                    ws.write(row_num, 54, campo49, normal)
                    ws.write(row_num, 55, campo50, normal)
                else:
                    for lista1 in lista_discapacidad:
                        campo49 = lista1[0]
                        campo50 = lista1[1]
                        ws.write(row_num, 54, campo49, normal)
                        ws.write(row_num, 55, campo50, normal)
            else:
                ws.write(row_num, 54, campo49, normal)
                ws.write(row_num, 55, campo50, normal)
            campo100 = MatriculaTitulacion.objects.values('id').filter(Q(inscripcion=matriculados.inscripcion), (Q(estado=1) | Q(estado=9) | Q(estado=10)), fechainscripcion__lte=matriculados.fechainscripcion).count().__str__()
            campo101 = matriculados.fechainscripcion
            campo102 = ''
            campo103 = ''
            campo104 = ''
            campo105 = ''
            campo106 = ''
            integrante = ""
            if ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True):
                # grupo = ComplexivoDetalleGrupo.objects.get(matricula=matriculados, status=True)
                grupo = ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True).order_by('-id')[0]
                campo104 = u"%s" % str(grupo.grupo.horas_totales_tutorias_grupo())
                campo102 = u"%s" % grupo.grupo.tematica.tutor
                campo106 = grupo.grupo.estado_propuesta().get_estado_display() if grupo.grupo.estado_propuesta() else ""
                if grupo.grupo.subtema:
                    campo105 = grupo.grupo.subtema
                for com in grupo.grupo.complexivodetallegrupo_set.filter(status=True, matricula__alternativa__grupotitulacion__periodogrupo=matriculados.alternativa.grupotitulacion.periodogrupo):
                    if matriculados != com.matricula:
                        campo103 = integrante + u"%s" % com.matricula
                col = 112
                tit = 0
                if ComplexivoPropuestaPractica.objects.filter(grupo=grupo.grupo, status=True).exists():
                    for pro in ComplexivoPropuestaPractica.objects.filter(grupo=grupo.grupo, status=True):
                        texto = ''
                        if pro.complexivopropuestapracticaarchivo_set.filter(tipo=1, status=True).exists():
                            fecha = pro.complexivopropuestapracticaarchivo_set.filter(tipo=1, status=True)[0].fecha.strftime('%Y-%m-%d')
                            archivo = 'Si'
                        texto = str(pro.fecharevision) + '-' + str(pro.observacion)
                        ws.write(row_num, tit + col, u"%s" % str(pro.get_estado_display()), normal)
                        col = col + 1
                        ws.write(row_num, tit + col, u"%s" % texto, normal)
                        col = col + 1

            campo122 = ''
            campo123 = ''
            campo107 = 'PENDIENTE PARA SUSTENTAR'
            if matriculados.cumplerequisitos == 2:
                campo107 = 'APTO PARA SUSTENTAR'
                campo122 = matriculados.fechavalidacumplerequisitos
                campo123 = matriculados.horavalidacumplerequisitos
                if campo122:
                    campo122 = matriculados.fechavalidacumplerequisitos
                else:
                    campo122 = ""

                if campo123:
                    campo123 = matriculados.horavalidacumplerequisitos
                else:
                    campo123 = ""
            if matriculados.cumplerequisitos == 3:
                campo107 = 'NO APTO PARA SUSTENTAR'
            alterna = AlternativaTitulacion.objects.get(pk=matriculados.alternativa_id)

            campo109 = 'NO TIENE PRACTICAS PREPROFESIONALES'
            totalhoras = 0
            malla = matriculados.inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
            practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=matriculados.inscripcion, status=True, culminada=True)
            data['malla_horas_practicas'] = malla.horas_practicas
            tienepracticaspreprofesionales = False
            if practicaspreprofesionalesinscripcion.exists():
                for practicas in practicaspreprofesionalesinscripcion:
                    if practicas.tiposolicitud == 3:
                        totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
                    else:
                        totalhoras += practicas.numerohora
                if totalhoras >= malla.horas_practicas:
                    campo109 = 'TIENE PRACTICAS PREPROFESIONALES'
                    campo110 = 0
                    tienepracticaspreprofesionales = True
            else:
                totalhoras = 0
            if not tienepracticaspreprofesionales:
                horasfaltantes = malla.horas_practicas - totalhoras
                campo110 = horasfaltantes

            total_materias_malla = malla.cantidad_materiasaprobadas()
            cantidad_materias_aprobadas_record = matriculados.inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
            poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
            data['mi_nivel'] = nivel = matriculados.inscripcion.mi_nivel()
            inscripcionmalla = matriculados.inscripcion.malla_inscripcion()
            niveles_maximos = inscripcionmalla.malla.niveles_regulares

            totalfaltantesmalla = total_materias_malla - cantidad_materias_aprobadas_record
            campo112 = totalfaltantesmalla
            campo111 = 'MALLA IN COMPLETA'
            if poraprobacion >= 100:
                campo111 = 'MALLA COMPLETA'
                campo112 = 0

            campo113 = 'TIENE DEUDA'
            campo114 = matriculados.inscripcion.adeuda_a_la_fecha()
            if matriculados.inscripcion.adeuda_a_la_fecha() == 0:
                campo113 = 'NO TIENE DEUDA'
                campo114 = 0

            campo115 = 'INGLES INCOMPLETO'
            modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
            numero_modulo_ingles = modulo_ingles.count()
            lista = []
            listaid = []
            for modulo in modulo_ingles:
                if matriculados.inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
                    lista.append(modulo.asignatura.nombre)
                    listaid.append(modulo.asignatura.id)
            data['modulo_ingles_aprobados'] = lista
            campo116 = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid]).count()
            if numero_modulo_ingles == len(listaid):
                campo115 = 'INGLES COMPLETO'
                campo116 = 0

            campo117 = 'NO TIENE VINCULACION'
            data['malla_horas_vinculacion'] = malla.horas_vinculacion
            horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, proyecto__status=True, inscripcion_id=matriculados.inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
            horastotal = horastotal if horastotal else 0
            campo118 = malla.horas_vinculacion - horastotal
            if horastotal >= malla.horas_vinculacion:
                campo117 = 'TIENE VINCULACION'
                campo118 = 0

            campo119 = 'NO TIENE COMPUTACION'
            asignatura = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
            record = RecordAcademico.objects.filter(inscripcion__id=matriculados.inscripcion.id, asignatura__id__in=asignatura, aprobada=True)
            creditos_computacion = 0
            malla.creditos_computacion
            listconcreditos = []
            for comp in record:
                listconcreditos.append(comp.asignatura.nombre)
                creditos_computacion += comp.creditos
            campo121 = listconcreditos
            campo120 = malla.creditos_computacion-creditos_computacion
            if creditos_computacion >= malla.creditos_computacion:
                campo119 = 'SI TIENE COMPUTACION'
                campo120 = 0

            presidente = ""
            secretario = ""
            integrantedelegado = ""
            fechagrupo = ""
            horagrupo = ""
            lugargrupo =""
            if ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True):
                grupocomplexivo = ComplexivoDetalleGrupo.objects.filter(matricula=matriculados, status=True)[0]
                if grupocomplexivo.grupo.presidentepropuesta:
                    presidente = u"%s" %grupocomplexivo.grupo.presidentepropuesta.persona

                if grupocomplexivo.grupo.secretariopropuesta:
                    secretario = u"%s" %grupocomplexivo.grupo.secretariopropuesta.persona

                if grupocomplexivo.grupo.delegadopropuesta:
                    integrantedelegado = u"%s" %grupocomplexivo.grupo.delegadopropuesta.persona

                if grupocomplexivo.grupo.fechadefensa:
                    fechagrupo = u"%s" %grupocomplexivo.grupo.fechadefensa

                if grupocomplexivo.grupo.horadefensa:
                    horagrupo = u"%s" %grupocomplexivo.grupo.horadefensa

                if grupocomplexivo.grupo.lugardefensa:
                    lugargrupo = u"%s" %grupocomplexivo.grupo.lugardefensa

            codigoestado = 0
            nomestado = ''
            pexamen = 0
            if matriculados.alternativa.tiene_examen():
                if ComplexivoExamenDetalle.objects.filter(status=True, matricula=matriculados).exists():
                    detalle = ComplexivoExamenDetalle.objects.filter(status=True, matricula=matriculados).order_by('-id')[0]
                    nomestado = detalle.get_estado_display()
                    codigoestado = detalle.estado
                    pexamen = detalle.ponderacion()

            ppropuesta = 0
            ptotal = 0
            if ComplexivoGrupoTematica.objects.values('id').filter(status=True, activo=True, complexivodetallegrupo__status=True, complexivodetallegrupo__matricula=matriculados).exists():
                ppropuesta = matriculados.notapropuesta()
            if matriculados.alternativa.tipotitulacion.tipo == 1:
                ptotal = ppropuesta
            if matriculados.alternativa.tipotitulacion.tipo == 2:
                ptotal = matriculados.notafinalcomplexivoestado(codigoestado)
            estadotitulacion = matriculados.get_estadotitulacion_display()
            ws.write(row_num, 149, lugargrupo, normal)
            ws.write(row_num, 148, horagrupo, normal)
            ws.write(row_num, 147, fechagrupo, date_format)
            ws.write(row_num, 146, integrantedelegado, normal)
            ws.write(row_num, 145, secretario, normal)
            ws.write(row_num, 144, presidente, normal)
            ws.write(row_num, 143, str(campo121), normal)
            ws.write(row_num, 142, campo120, normal)
            ws.write(row_num, 141, campo119, normal)
            if matriculados.inscripcion.exonerado_practias():
                ws.write(row_num, 140, 'EXONERADO', normal)
            else:
                ws.write(row_num, 140, campo118, normal)
            ws.write(row_num, 139, campo117, normal)
            ws.write(row_num, 138, campo116, normal)
            ws.write(row_num, 137, campo115, normal)
            ws.write(row_num, 136, campo114, normal)
            ws.write(row_num, 135, campo113, normal)
            ws.write(row_num, 134, campo112, normal)
            ws.write(row_num, 133, campo111, normal)
            if matriculados.inscripcion.exonerado_practias():
                ws.write(row_num, 132, 'EXONERADO', normal)
            else:
                ws.write(row_num, 132, campo110, normal)
            ws.write(row_num, 131, campo109, normal)
            ws.write(row_num, 130, u"%s" % campo123, normal)
            ws.write(row_num, 129, campo122, date_format)
            ws.write(row_num, 128, campo107, normal)
            ws.write(row_num, 56, campo51, normal)
            ws.write(row_num, 57, campo52, normal)
            ws.write(row_num, 58, campo53, normal)
            ws.write(row_num, 59, campo54, normal)
            ws.write(row_num, 60, campo55, normal)
            ws.write(row_num, 61, campo56, normal)
            ws.write(row_num, 62, campo57, normal)
            ws.write(row_num, 63, campo58, normal)
            ws.write(row_num, 64, campo59, normal)
            ws.write(row_num, 65, campo60, normal)
            ws.write(row_num, 66, campo61, normal)
            ws.write(row_num, 67, campo62, normal)
            ws.write(row_num, 68, campo63, normal)
            ws.write(row_num, 69, campo64, normal)
            ws.write(row_num, 70, campo65, normal)
            ws.write(row_num, 71, campo66, normal)
            ws.write(row_num, 72, campo67, normal)
            ws.write(row_num, 73, campo68, normal)
            ws.write(row_num, 74, campo69, normal)
            ws.write(row_num, 75, campo70, normal)
            ws.write(row_num, 76, campo71, normal)
            ws.write(row_num, 77, campo72, normal)
            ws.write(row_num, 78, campo73, normal)
            ws.write(row_num, 79, campo74, normal)
            ws.write(row_num, 80, campo75, normal)
            ws.write(row_num, 81, campo76, normal)
            ws.write(row_num, 82, campo77, normal)
            ws.write(row_num, 83, campo78, normal)
            ws.write(row_num, 84, campo79, normal)
            ws.write(row_num, 85, campo80, normal)
            ws.write(row_num, 86, campo81, normal)
            ws.write(row_num, 87, campo82, normal)
            ws.write(row_num, 88, campo83, normal)
            ws.write(row_num, 89, campo84, normal)
            ws.write(row_num, 90, campo85, normal)
            ws.write(row_num, 91, campo86, normal)
            ws.write(row_num, 92, campo87, normal)
            ws.write(row_num, 93, campo88, normal)
            ws.write(row_num, 94, campo89, normal)
            ws.write(row_num, 95, campo90, normal)
            ws.write(row_num, 96, campo91, normal)
            ws.write(row_num, 97, campo92, normal)
            ws.write(row_num, 98, campo93, normal)
            ws.write(row_num, 99, campo94, normal)
            ws.write(row_num, 100, campo95, normal)
            ws.write(row_num, 101, campo96, normal)
            ws.write(row_num, 102, campo97, normal)
            ws.write(row_num, 103, campo98, normal)
            ws.write(row_num, 104, campo99, normal)
            ws.write(row_num, 105, campo100, normal)
            ws.write(row_num, 106, campo101, date_format)
            ws.write(row_num, 107, campo102, normal)
            ws.write(row_num, 108, campo103, normal)
            ws.write(row_num, 109, campo104, normal)
            ws.write(row_num, 110, campo105, normal)
            ws.write(row_num, 111, campo106, normal)
            ws.write(row_num, 150, pexamen, normal)
            ws.write(row_num, 151, ppropuesta, normal)
            ws.write(row_num, 152, ptotal, normal)
            ws.write(row_num, 153, nomestado, normal)
            ws.write(row_num, 154, estadotitulacion, normal)

            row_num += 1
        wb.save(response)
        return response
    except Exception as ex:
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
        pass

#funcion para graduar
def adicionar_nota_complexivo(idgraduado, nota, item, fecha, request):
    if ExamenComlexivoGraduados.objects.filter(graduado_id=idgraduado, itemexamencomplexivo=item).exists():
        itendetalle = ExamenComlexivoGraduados.objects.get(graduado_id=idgraduado, itemexamencomplexivo=item)
        itendetalle.examen = nota
        itendetalle.ponderacion = null_to_decimal((nota / 2), 2)
        itendetalle.fecha = fecha
        log(u'Adicionó Examen Complexivo graduado por tribunal: %s' % itendetalle, request, "edit")
    else:
        itendetalle = ExamenComlexivoGraduados(graduado_id=idgraduado,
                                               itemexamencomplexivo=item,
                                               examen=nota,
                                               ponderacion=null_to_decimal((nota / 2), 2),
                                               fecha=fecha
                                               )
        log(u'Adicionó Examen Complexivo graduado por tribunal: %s' % itendetalle, request, "add")
    itendetalle.save(request)



