# -*- coding: UTF-8 -*-
import sys

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, connection
from django.db.models import Max, Q, Count, Exists, OuterRef, Subquery
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from datetime import datetime, timedelta
import json
import ast
from django.template.context import Context
from django.template.loader import get_template
from xlwt import *
from xlwt import easyxf
import xlwt
import random
from decorators import last_access, secure_module
from inno.models import ParesInvestigacionVinculacion
from sagest.models import DistributivoPersona, Departamento
from settings import PUESTO_ACTIVO_ID, MATRICULACION_LIBRE, CUPO_POR_MATERIA, USA_EVALUACION_INTEGRAL, \
    TIPO_DOCENTE_PRACTICA, TIPO_PERIODO_REGULAR
from sga.commonviews import adduserdata, traerNotificaciones
from sga.forms import PonderacionAcreditacionForm, ActivacionInstrumentoEvaluacionAcreditacionForm, \
    CaracteristicaAcreditacionForm, PreguntaAcreditacionForm, RubricaAcreditacionForm, \
    TipoCategoriasForm, TipoCategoriasCriteriosForm, ResponsableEvaluacionFrom, FechaEvaluacionAcreditacionForm, \
    CronogramaEncuestaProcesoEvaluativoForm, EncuestaProcesoEvaluativoForm, PreguntaProcesoEvaluativoForm, \
    PreguntaEncuestaForm, ParesInvestigacionVinculacionForm, PonderacionProfesorForm
from sga.funciones import log, MiPaginador, actualizar_resumen, frecuencia_preguntas_hetero, frecuencia_preguntas_auto, \
    frecuencia_preguntas_dir
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, download_html_to_pdf
from sga.funciones_templatepdf import listadodocentescriterios
from django.db.models.functions import Concat
from sga.models import TablaPonderacionInstrumento, Profesor, Persona, \
    DetalleInstrumentoEvaluacionDirectivoAcreditacion, \
    CaracteristicaEvaluacionAcreditacion, TextoPreguntaAcreditacion, Rubrica, RubricaCaracteristica, \
    CriterioDocenciaPeriodo, RubricaCriterioDocencia, CriterioInvestigacionPeriodo, RubricaCriterioInvestigacion, \
    RubricaCriterioGestion, CriterioGestionPeriodo, RubricaPreguntas, PreguntaCaracteristicaEvaluacionAcreditacion, \
    Coordinacion, Carrera, \
    RespuestaEvaluacionAcreditacion, ProfesorDistributivoHoras, null_to_numeric, TipoObservacionEvaluacion, \
    CriterioTipoObservacionEvaluacion, DetalleInstrumentoEvaluacionParAcreditacion, RubricaCoordinacion, \
    ResponsableEvaluacion, CoordinadorCarrera, ResponsableCoordinacion, GradoTitulacion, \
    FechaEvaluacionDirectivoAcreditacion, CronogramaEncuestaProcesoEvaluativo, \
    CronogramaEncuestaProcesoEvaluativo_Nivel, Nivel, EncuestaProcesoEvaluativo, PreguntaProcesoEvaluativo, \
    EncuestaProcesoEvaluativo_Carrera, EncuestaProcesoEvaluativo_Pregunta, EncuestaProcesoEvaluativo_OpcionPregunta, \
    Materia, NivelMalla, Malla, Paralelo, Matricula, ResumenFinalEvaluacionAcreditacionFija, Periodo, Modalidad, \
    RubricaModalidad, TipoProfesor, RubricaTipoProfesor, CronogramaProcesoEvaluativoAcreditacion, \
    RubricaCriterioVinculacion, \
    TablaPonderacionConfiguracion, ProfesorMateria, RubricaModalidadTipoProfesor, Administrativo, RespuestaRubrica, \
    Coordinacion, CUENTAS_CORREOS, Notificacion, DetalleRespuestaRubrica
from bd.models import CronogramaCoordinacion
from bd.forms import CronogramaCoordinacionForm
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from posgrado.models import EncuestaSatisfaccionDocente, PreguntaEncuestaSatisfaccionDocente, \
    OpcionCuadriculaEncuestaSatisfaccionDocente, CohorteMaestria, InscripcionEncuestaSatisfaccionDocente, \
    RespuestaCuadriculaEncuestaSatisfaccionDocente
from posgrado.forms import EncuestaSatisfaccionDocenteForm, PreguntaEncuestaSatisfaccionDocenteForm, OpcionCuadriculaSatisfaccionDocenteForm, \
    EvidenciaColorPreguntaEncuestaForm
unicode =str

import io
import xlsxwriter
from sga.funciones import notificacion, cantidad_evaluacion_auto

def cincoacien(valor):
    if valor is not None:
        return round((valor * 100 / 5), 2)
    else:
        return 0

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['title'] = u'Proaddcategoriaceso de evaluación de profesores'
    data['periodo'] = periodo = data['periodo']
    persona = request.session['persona']
    data['proceso'] = proceso = periodo.proceso_evaluativoacreditacion()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addfechas':
            try:
                #listaaplicar 1 par, 2 directivo, 3 todos
                listaaplicar=[]
                listaaplicar.append(3 if request.POST['appar']=='true' else 2)
                distributivo = ProfesorDistributivoHoras.objects.get(profesor_id=request.POST['idpr'], periodo_id=request.POST['idpe'], status=True)
                fecha = request.POST['fecha']
                cadena = fecha.split('-')
                fechaconvertida = cadena[2] + '-' + cadena[1] + '-' + cadena[0]
                fechasevaluacion = distributivo.asignar_fecha_par_y_directivo_evaluacion(request, request.POST['lugar'], fechaconvertida, request.POST['horaini'], request.POST['horafin'], False, listaaplicar)
                # if FechaEvaluacionDirectivoAcreditacion.objects.filter(profesor_id=request.POST['idpr'],periodo_id=request.POST['idpe'], status=True).exists():
                #     return JsonResponse({"result": "bad", "mensaje": u"Ya existe fecha a ingresar."})
                # else:
                #     fecha = request.POST['fecha']
                #     cadena = fecha.split('-')
                #     fecha = cadena[2]+'-'+cadena[1]+'-'+cadena[0]
                #     fechasevaluacion = FechaEvaluacionDirectivoAcreditacion(profesor_id=request.POST['idpr'],
                #                                                             periodo_id=request.POST['idpe'],
                #                                                             fecha=fecha,
                #                                                             horainicio=request.POST['horaini'],
                #                                                             lugar=request.POST['lugar'],
                #                                                             horafin=request.POST['horafin'])
                #     fechasevaluacion.save(request)
                #     log(u'Adiciono fecha de evaluacion en evaluacion de docentes: id[%s] profesor[%s] - periodo[%s] - [%s - %s - %s - %s]' % (fechasevaluacion.id, fechasevaluacion.profesor, fechasevaluacion.periodo, fechasevaluacion.fecha, fechasevaluacion.horainicio, fechasevaluacion.horafin, fechasevaluacion.lugar), request, "add")
                return JsonResponse({"result": "ok", "creacion": fechasevaluacion.usuario_creacion.__str__(), "idfechasdocentes": fechasevaluacion.id, "profesor": fechasevaluacion.profesor.id, "periodo": fechasevaluacion.periodo.id,"fecha": fechasevaluacion.id, "fecha": fechasevaluacion.fecha, "hinicio": fechasevaluacion.horainicio, "hfin": fechasevaluacion.horafin, "lugar":fechasevaluacion.lugar})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'ingresofechaevaluacion':
            try:
                cadena = request.POST['listascodigos'].split(',')
                id_fini = request.POST['id_fini']
                id_ffin = request.POST['id_ffin']
                for elemento in cadena:
                    materia=Materia.objects.get(pk=elemento)
                    materia.inicioeval = id_fini
                    materia.fineval = id_ffin
                    materia.usaperiodoevaluacion = False
                    materia.save(request)
                log(u'Actualizó fecha de evaluacion en evaluacion en la materia %s' % (materia), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'ingresofechaevaluacionauto':
            try:
                cadena = request.POST['listascodigos'].split(',')
                id_fini = request.POST['id_fini']
                id_ffin = request.POST['id_ffin']
                for elemento in cadena:
                    materia=Materia.objects.get(pk=elemento)
                    materia.inicioevalauto = id_fini
                    materia.finevalauto = id_ffin
                    materia.usaperiodoevaluacion = False
                    materia.save(request)

                    if materia.profesores_materia2() and periodo.tipo.id == 3:
                        eProfesorMateria = materia.profesores_materia2()[0]
                        titulo = 'AUTOEVALUACIÓN PENDIENTE'
                        cuerpo = f'Saludos, Msc. {eProfesorMateria.profesor.persona}, módulo: {eProfesorMateria.materia.asignatura}, paralelo {eProfesorMateria.materia.paralelo}, cohorte {eProfesorMateria.materia.nivel.periodo}. La evaluación estará activa desde {eProfesorMateria.materia.inicioevalauto} hasta {eProfesorMateria.materia.finevalauto}. Por favor, realizarla en el tiempo acordado.'
                        notificacion(titulo, cuerpo,
                                      eProfesorMateria.profesor.persona, None, '/pro_autoevaluacion', eProfesorMateria.profesor.persona.pk, 1, 'sga',
                                      eProfesorMateria.profesor.persona, None)
                        log(u'Notificó autoevaluación: %s' % eProfesorMateria.profesor.persona, request, "edit")

                    log(u'Actualizó fecha de auto evaluacion en evaluacion en la materia %s' % (materia), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'delfechaevaluacion':
            try:
                fechasevaluacion = FechaEvaluacionDirectivoAcreditacion.objects.get(pk=request.POST['id'])
                return JsonResponse({"result": "ok", 'idfecha': fechasevaluacion.id, 'apellido1': fechasevaluacion.profesor.persona.apellido1, 'apellido2': fechasevaluacion.profesor.persona.apellido2, 'nombres': fechasevaluacion.profesor.persona.nombres})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'eliminarfechaevaluacion':
            try:
                # listaaplicar 1 par, 2 directivo, 3 todos
                listaaplicar = []
                listaaplicar.append(3 if request.POST['delpar']=='true' else 2)
                fechasevaluacion = FechaEvaluacionDirectivoAcreditacion.objects.get(pk=request.POST['idfecha'])
                distributivo = ProfesorDistributivoHoras.objects.get(profesor=fechasevaluacion.profesor, periodo=fechasevaluacion.periodo, status=True)
                distributivo.eliminar_fecha_par_y_directivo_evaluacion(request, listaaplicar)
                # fechasevaluacion.status = False
                # fechasevaluacion.save(request)
                # log(u'Elimino fecha de evaluacion en evaluacion de docentes: id[%s] profesor[%s] - periodo[%s] - [%s - %s - %s - %s]' % (fechasevaluacion.id, fechasevaluacion.profesor, fechasevaluacion.periodo, fechasevaluacion.fecha,fechasevaluacion.horainicio, fechasevaluacion.horafin, fechasevaluacion.lugar), request, "del")
                return JsonResponse({"result": "ok", 'idperiodo': fechasevaluacion.periodo.id, 'idprofesor': fechasevaluacion.profesor.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addponderacion':
            try:
                f = PonderacionAcreditacionForm(request.POST)
                if f.is_valid():
                    # if f.cleaned_data['docencia_instrumentohetero'] + f.cleaned_data['docencia_instrumentoauto'] + f.cleaned_data['docencia_instrumentopar'] + f.cleaned_data['docencia_instrumentodirectivo'] != 100:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error: los valores de ponderacion docencia deben sumar 100."})
                    # if f.cleaned_data['investigacion_instrumentohetero'] + f.cleaned_data['investigacion_instrumentoauto'] + f.cleaned_data['investigacion_instrumentopar'] + f.cleaned_data['investigacion_instrumentodirectivo'] != 100:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error: los valores de ponderacion investigacion deben sumar 100."})
                    # if f.cleaned_data['gestion_instrumentohetero'] + f.cleaned_data['gestion_instrumentoauto'] + f.cleaned_data['gestion_instrumentopar'] + f.cleaned_data['gestion_instrumentodirectivo'] != 100:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error: los valores de ponderacion gestion deben sumar 100."})
                    tabla = TablaPonderacionInstrumento(nombre=f.cleaned_data['nombre'],
                                                        docencia_instrumentohetero=f.cleaned_data['docencia_instrumentohetero'],
                                                        docencia_instrumentoauto=f.cleaned_data['docencia_instrumentoauto'],
                                                        docencia_instrumentopar=f.cleaned_data['docencia_instrumentopar'],
                                                        docencia_instrumentodirectivo=f.cleaned_data['docencia_instrumentodirectivo'],
                                                        investigacion_instrumentohetero=f.cleaned_data['investigacion_instrumentohetero'],
                                                        investigacion_instrumentoauto=f.cleaned_data['investigacion_instrumentoauto'],
                                                        investigacion_instrumentopar=f.cleaned_data['investigacion_instrumentopar'],
                                                        investigacion_instrumentodirectivo=f.cleaned_data['investigacion_instrumentodirectivo'],
                                                        gestion_instrumentohetero=f.cleaned_data['gestion_instrumentohetero'],
                                                        gestion_instrumentoauto=f.cleaned_data['gestion_instrumentoauto'],
                                                        gestion_instrumentopar=f.cleaned_data['gestion_instrumentopar'],
                                                        gestion_instrumentodirectivo=f.cleaned_data['gestion_instrumentodirectivo'],
                                                        vincu_instrumentohetero=f.cleaned_data['vincu_instrumentohetero'],
                                                        vincu_instrumentoauto=f.cleaned_data['vincu_instrumentoauto'],
                                                        vincu_instrumentopar=f.cleaned_data['vincu_instrumentopar'],
                                                        vincu_instrumentodirectivo=f.cleaned_data['vincu_instrumentodirectivo'],
                                                        clasificacion=periodo.clasificacion,
                                                        # docencia_instrumentocomision=f.cleaned_data['docencia_instrumentocomision'],
                                                        # investigacion_instrumentocomision=f.cleaned_data['investigacion_instrumentocomision'],
                                                        # gestion_instrumentocomision=f.cleaned_data['gestion_instrumentocomision'],
                                                        # vincu_instrumentocomision=f.cleaned_data['vincu_instrumentocomision']
                                                        )
                    tabla.save(request)
                    log(u'Adiciono tabla ponderacion: %s' % tabla, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editponderacion':
            try:
                f = PonderacionAcreditacionForm(request.POST)
                tabla = TablaPonderacionInstrumento.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    # if f.cleaned_data['docencia_instrumentohetero'] + f.cleaned_data['docencia_instrumentoauto'] + f.cleaned_data['docencia_instrumentopar'] + f.cleaned_data['docencia_instrumentodirectivo'] != 100:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error: los valores de ponderacion docencia deben sumar 100."})
                    # if f.cleaned_data['investigacion_instrumentohetero'] + f.cleaned_data['investigacion_instrumentoauto'] + f.cleaned_data['investigacion_instrumentopar'] + f.cleaned_data['investigacion_instrumentodirectivo'] != 100:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error: los valores de ponderacion investigacion deben sumar 100."})
                    # if f.cleaned_data['gestion_instrumentohetero'] + f.cleaned_data['gestion_instrumentoauto'] + f.cleaned_data['gestion_instrumentopar'] + f.cleaned_data['gestion_instrumentodirectivo'] != 100:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error: los valores de ponderacion gestion deben sumar 100."})
                    tabla.nombre = f.cleaned_data['nombre']
                    tabla.docencia_instrumentohetero = f.cleaned_data['docencia_instrumentohetero']
                    tabla.docencia_instrumentoauto = f.cleaned_data['docencia_instrumentoauto']
                    tabla.docencia_instrumentopar = f.cleaned_data['docencia_instrumentopar']
                    tabla.docencia_instrumentodirectivo = f.cleaned_data['docencia_instrumentodirectivo']
                    tabla.investigacion_instrumentohetero = f.cleaned_data['investigacion_instrumentohetero']
                    tabla.investigacion_instrumentoauto = f.cleaned_data['investigacion_instrumentoauto']
                    tabla.investigacion_instrumentopar = f.cleaned_data['investigacion_instrumentopar']
                    tabla.investigacion_instrumentodirectivo = f.cleaned_data['investigacion_instrumentodirectivo']
                    tabla.gestion_instrumentohetero = f.cleaned_data['gestion_instrumentohetero']
                    tabla.gestion_instrumentoauto = f.cleaned_data['gestion_instrumentoauto']
                    tabla.gestion_instrumentopar = f.cleaned_data['gestion_instrumentopar']
                    tabla.gestion_instrumentodirectivo = f.cleaned_data['gestion_instrumentodirectivo']
                    tabla.vincu_instrumentohetero = f.cleaned_data['vincu_instrumentohetero']
                    tabla.vincu_instrumentoauto = f.cleaned_data['vincu_instrumentoauto']
                    tabla.vincu_instrumentopar = f.cleaned_data['vincu_instrumentopar']
                    tabla.vincu_instrumentodirectivo = f.cleaned_data['vincu_instrumentodirectivo']
                    # tabla.docencia_instrumentocomision = f.cleaned_data['docencia_instrumentocomision']
                    # tabla.investigacion_instrumentocomision = f.cleaned_data['investigacion_instrumentocomision']
                    # tabla.gestion_instrumentocomision = f.cleaned_data['gestion_instrumentocomision']
                    # tabla.vincu_instrumentocomision = f.cleaned_data['vincu_instrumentocomision']
                    tabla.save(request)
                    log(u'Modifico tabla ponderacion: %s' % tabla, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addresponsable':
            try:
                f = ResponsableEvaluacionFrom(request.POST)
                if f.is_valid():
                    # persona = Persona.objects.get(pk=f.cleaned_data['persona'])
                    # distributivopersona = persona.mi_cargo_activo()
                    # r = distributivopersona.id
                    responsable = ResponsableEvaluacion(distributivopersona_id=f.cleaned_data['persona'])
                    responsable.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cambiaestado':
            try:
                periodopoa = ResponsableEvaluacion.objects.get(pk=request.POST['idresponsable'])
                ResponsableEvaluacion.objects.filter(status=True).update(activo=False)
                if periodopoa.activo:
                    periodopoa.activo = False
                else:
                    periodopoa.activo = True
                    periodopoa.save(request)
                return JsonResponse({'result': 'ok', 'valor': periodopoa.activo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteresponsable':
            try:
                responsable = ResponsableEvaluacion.objects.get(pk=request.POST['id'])
                responsable.status = False
                log(u'Elimino responsable: %s' % responsable, request, "del")
                responsable.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addcaracteristica':
            try:
                f = CaracteristicaAcreditacionForm(request.POST)
                if f.is_valid():
                    caracteristica = CaracteristicaEvaluacionAcreditacion(nombre=f.cleaned_data['nombre'],intencionalidad=f.cleaned_data['intencionalidad'])
                    caracteristica.save(request)
                    log(u'Adiciono caracteristica de acreditacion: %s' % caracteristica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addrubrica':
            try:
                f = RubricaAcreditacionForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['para_hetero'] and not f.cleaned_data['para_auto'] and not f.cleaned_data['para_par'] and not f.cleaned_data['para_directivo']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un tipo de instrumento."})
                    if int(f.cleaned_data['tiporubrica']) == 3:
                        tipoprofesor = f.cleaned_data['tipoprofesor']
                    else:
                        tipoprofesor = None

                    if f.cleaned_data['tutores'] and not f.cleaned_data['para_hetero']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar el tipo de instrumento hétero si va marcar esta rúbrica como especial para tutores."})


                    rubrica = Rubrica(proceso=proceso,
                                      nombre=f.cleaned_data['nombre'],
                                      descripcion=f.cleaned_data['descripcion'],
                                      para_hetero=f.cleaned_data['para_hetero'],
                                      # para_materiapractica=f.cleaned_data['para_materiapractica'],
                                      para_nivelacion=f.cleaned_data['para_nivelacion'],
                                      informativa=f.cleaned_data['informativa'],
                                      para_auto=f.cleaned_data['para_auto'],
                                      tiporubrica=f.cleaned_data['tiporubrica'],
                                      tipoprofesor=tipoprofesor,
                                      para_par=f.cleaned_data['para_par'],
                                      para_nivelacionvirtual=f.cleaned_data['para_nivelacionvirtual'],
                                      # para_semestrevirtual=f.cleaned_data['para_semestrevirtual'],
                                      # para_practicasalud=f.cleaned_data['para_practicasalud'],
                                      para_directivo=f.cleaned_data['para_directivo'],
                                      para_tutor=f.cleaned_data['tutores']
                                      # nivelacion_presencial=f.cleaned_data['nivelacion_presencial'],
                                      # nivelacion_virtual=f.cleaned_data['nivelacion_virtual'],
                                      # semestre_presencial=f.cleaned_data['semestre_presencial'],
                                      # semestre_virtual=f.cleaned_data['semestre_virtual'],
                                      )
                    rubrica.save(request)
                    if proceso.periodo.tipo.id == 3 and rubrica.para_hetero and not rubrica.para_tutor:
                        if Rubrica.objects.filter(status=True, para_hetero=True, proceso=proceso).exclude(pk=rubrica.id).exists():
                            eRubricas = Rubrica.objects.filter(status=True, para_hetero=True, proceso=proceso).exclude(pk=rubrica.id)
                            for eRubrica in eRubricas:
                                eRubrica.rvigente = False
                                eRubrica.save(request)

                    if proceso.periodo.tipo.id == 3 and rubrica.para_auto:
                        if Rubrica.objects.filter(status=True, para_auto=True, proceso=proceso).exclude(pk=rubrica.id).exists():
                            eRubricas = Rubrica.objects.filter(status=True, para_auto=True, proceso=proceso).exclude(pk=rubrica.id)
                            for eRubrica in eRubricas:
                                eRubrica.rvigente = False
                                eRubrica.save(request)

                    if proceso.periodo.tipo.id == 3 and rubrica.para_hetero and rubrica.para_tutor:
                        if Rubrica.objects.filter(status=True, para_hetero=True, proceso=proceso, para_tutor=True).exclude(pk=rubrica.id).exists():
                            eRubricas = Rubrica.objects.filter(status=True, para_hetero=True, proceso=proceso, para_tutor=True).exclude(pk=rubrica.id)
                            for eRubrica in eRubricas:
                                eRubrica.rvigente = False
                                eRubrica.save(request)

                    if proceso.periodo.tipo.id == 3 and rubrica.para_directivo:
                        if Rubrica.objects.filter(status=True, para_directivo=True, proceso=proceso).exclude(pk=rubrica.id).exists():
                            eRubricas = Rubrica.objects.filter(status=True, para_directivo=True, proceso=proceso).exclude(pk=rubrica.id)
                            for eRubrica in eRubricas:
                                eRubrica.rvigente = False
                                eRubrica.save(request)

                    listamodalidadtipo = json.loads(request.POST['lista_items2'])
                    if listamodalidadtipo:
                        for listamodtip in listamodalidadtipo:
                            idmodalidad = listamodtip.split('_')
                            if not RubricaModalidadTipoProfesor.objects.filter(rubrica=rubrica, modalidad_id=idmodalidad[0], tipoprofesor_id=idmodalidad[1], status=True):
                                ingresorubmodalidad = RubricaModalidadTipoProfesor(rubrica=rubrica, modalidad_id=idmodalidad[0], tipoprofesor_id=idmodalidad[1])
                                ingresorubmodalidad.save()
                    log(u'Adiciono rubrica de acreditacion: %s' % rubrica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcategoria':
            try:
                f = TipoCategoriasForm(request.POST)
                if f.is_valid():
                    if not TipoObservacionEvaluacion.objects.filter(nombre=f.cleaned_data['nombre'],tipoinstrumento=f.cleaned_data['tipoinstrumento']).exists():
                        tiposcriterios = TipoObservacionEvaluacion(nombre=f.cleaned_data['nombre'],
                                                                   tipo=f.cleaned_data['tipo'],
                                                                   tipoinstrumento=f.cleaned_data['tipoinstrumento'],
                                                                   tipocriterio=f.cleaned_data['tipocriterio']
                                                                   )
                        tiposcriterios.save(request)
                        log(u'Adiciono categoria en evaluacion docente creaditacion: %s - [%s]' % (tiposcriterios,tiposcriterios.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya el tipo categoría esta ingresado."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addtipocategoria':
            try:
                f = TipoCategoriasCriteriosForm(request.POST)
                if f.is_valid():
                    if not CriterioTipoObservacionEvaluacion.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        tiposcriterios = CriterioTipoObservacionEvaluacion(nombre=f.cleaned_data['nombre'])
                        tiposcriterios.save(request)
                        log(u'Adiciono tipo de categoria en evaluacion docente creaditacion: %s - [%s]' % (tiposcriterios, tiposcriterios.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya el tipo de categoría esta ingresado."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcategoria':
            try:
                f = TipoCategoriasForm(request.POST)
                categoria = TipoObservacionEvaluacion.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    categoria.nombre = f.cleaned_data['nombre']
                    categoria.tipo = f.cleaned_data['tipo']
                    categoria.tipoinstrumento = f.cleaned_data['tipoinstrumento']
                    categoria.tipocriterio = f.cleaned_data['tipocriterio']
                    categoria.save(request)
                    log(u'Edito categoria en evaluacion docente creaditacion: %s - [%s]' % (categoria, categoria.id),request, "edi")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edittipocategoria':
            try:
                f = TipoCategoriasCriteriosForm(request.POST)
                tipocategoria = CriterioTipoObservacionEvaluacion.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    tipocategoria.nombre = f.cleaned_data['nombre']
                    tipocategoria.save(request)
                    log(u'Edito categoria en evaluacion docente creaditacion: %s - [%s]' % (tipocategoria, tipocategoria.id),request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcaracteristica':
            try:
                caracteristica = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.POST['id'])
                f = CaracteristicaAcreditacionForm(request.POST)
                if f.is_valid():
                    caracteristica.nombre = f.cleaned_data['nombre']
                    caracteristica.intencionalidad = f.cleaned_data['intencionalidad']
                    caracteristica.save(request)
                    log(u'Modifico caracteristica de acreditacion: %s' % caracteristica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'clonarrubrica':
            try:
                rubrica = Rubrica.objects.get(pk=int(request.POST['id']))
                f = RubricaAcreditacionForm(request.POST)
                if f.is_valid():
                    if Rubrica.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un registro con el mismo nombre de rubrica"})
                    nuevarubrica = Rubrica(nombre=f.cleaned_data['nombre'],
                                           proceso=rubrica.proceso,
                                           descripcion=f.cleaned_data['descripcion'],
                                           para_hetero=rubrica.para_hetero,
                                           para_auto=rubrica.para_auto,
                                           para_directivo=rubrica.para_directivo,
                                           para_materiapractica=rubrica.para_materiapractica,
                                           para_nivelacion=rubrica.para_nivelacion,
                                           para_par=rubrica.para_par,
                                           texto_basico=rubrica.texto_basico,
                                           texto_competente=rubrica.texto_competente,
                                           texto_destacado=rubrica.texto_destacado,
                                           texto_muycompetente=rubrica.texto_muycompetente,
                                           texto_nosatisfactorio=rubrica.texto_nosatisfactorio,
                                           tipo_criterio=rubrica.tipo_criterio)
                    nuevarubrica.save(request)
                    for criteriodocencia in rubrica.rubricacriteriodocencia_set.all():
                        nuevocriteriodocencia = RubricaCriterioDocencia(rubrica=nuevarubrica,
                                                                        criterio=criteriodocencia.criterio)
                        nuevocriteriodocencia.save(request)
                    for criterioinvestigacion in rubrica.rubricacriterioinvestigacion_set.all():
                        nuevocriterioinvestigacion = RubricaCriterioInvestigacion(rubrica=nuevarubrica,
                                                                                  criterio=criterioinvestigacion.criterio)
                        nuevocriterioinvestigacion.save(request)
                    for criteriogestion in rubrica.rubricacriteriogestion_set.all():
                        nuevocriteriogestion = RubricaCriterioGestion(rubrica=nuevarubrica,
                                                                      criterio=criteriogestion.criterio)
                        nuevocriteriogestion.save(request)
                    for caracteristica in rubrica.rubricacaracteristica_set.all():
                        nuevacaracteristica = RubricaCaracteristica(rubrica=nuevarubrica,
                                                                    caracteristica=caracteristica.caracteristica)
                        nuevacaracteristica.save(request)
                    for pregunta in rubrica.rubricapreguntas_set.all():
                        nuevapregunta = RubricaPreguntas(rubrica=nuevarubrica,
                                                         preguntacaracteristica=pregunta.preguntacaracteristica,
                                                         orden=pregunta.orden)
                        nuevapregunta.save(request)
                    log(u'Adiciono clon de rubrica de acreditacion: %s' % nuevarubrica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editrubrica':
            try:
                rubrica = Rubrica.objects.get(pk=request.POST['id'])
                f = RubricaAcreditacionForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['para_nivelacion'] and not f.cleaned_data['para_nivelacionvirtual'] and not f.cleaned_data['para_hetero'] and not f.cleaned_data['para_auto'] and not f.cleaned_data['para_par'] and not f.cleaned_data['para_directivo']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos un tipo de instrumento."})
                    rubrica.nombre = f.cleaned_data['nombre']
                    rubrica.descripcion = f.cleaned_data['descripcion']
                    rubrica.para_hetero = f.cleaned_data['para_hetero']
                    rubrica.informativa = f.cleaned_data['informativa']
                    rubrica.tiporubrica = f.cleaned_data['tiporubrica']
                    # if int(f.cleaned_data['tiporubrica']) == 3:
                    #     rubrica.tipoprofesor = f.cleaned_data['tipoprofesor']
                    # else:
                    #     rubrica.tipoprofesor = None
                    if int(f.cleaned_data['tiporubrica']) == 1:
                        rubrica.tipoprofesor = f.cleaned_data['tipoprofesor']
                    else:
                        rubrica.tipoprofesor = None

                    # rubrica.para_materiapractica = f.cleaned_data['para_materiapractica']
                    rubrica.para_nivelacion = f.cleaned_data['para_nivelacion']
                    rubrica.para_nivelacionvirtual = f.cleaned_data['para_nivelacionvirtual']
                    # rubrica.para_semestrevirtual = f.cleaned_data['para_semestrevirtual']
                    # rubrica.para_practicasalud = f.cleaned_data['para_practicasalud']
                    rubrica.para_auto = f.cleaned_data['para_auto']
                    rubrica.para_par = f.cleaned_data['para_par']
                    rubrica.directivos = f.cleaned_data['directivos']
                    rubrica.para_directivo = f.cleaned_data['para_directivo']
                    # rubrica.nivelacion_presencial = f.cleaned_data['nivelacion_presencial']
                    # rubrica.nivelacion_virtual = f.cleaned_data['nivelacion_virtual']
                    # rubrica.semestre_presencial = f.cleaned_data['semestre_presencial']
                    # rubrica.semestre_virtual = f.cleaned_data['semestre_virtual']
                    rubrica.save(request)
                    # listamodalidad = json.loads(request.POST['lista_items2'])
                    # if listamodalidad:
                    #     if RubricaModalidad.objects.filter(rubrica=rubrica, status=True).exclude(modalidad_id__in=listamodalidad):
                    #         delrubricamodalidad = RubricaModalidad.objects.filter(rubrica=rubrica, status=True).exclude(modalidad_id__in=listamodalidad)
                    #         delrubricamodalidad.delete()
                    #     for idmodalidad in listamodalidad:
                    #         if not RubricaModalidad.objects.filter(rubrica=rubrica, modalidad_id=idmodalidad, status=True):
                    #             ingresorubmodalidad = RubricaModalidad(rubrica=rubrica, modalidad_id=idmodalidad)
                    #             ingresorubmodalidad.save()
                    # else:
                    #     if RubricaModalidad.objects.filter(rubrica=rubrica, status=True):
                    #         delrubricamodalidad = RubricaModalidad.objects.filter(rubrica=rubrica, status=True)
                    #         delrubricamodalidad.delete()

                    # listatipoprofesor = json.loads(request.POST['lista_items3'])
                    # if listatipoprofesor:
                    #     if RubricaTipoProfesor.objects.filter(rubrica=rubrica, status=True).exclude(tipoprofesor_id__in=listatipoprofesor):
                    #         delrubricatipoprofesor = RubricaTipoProfesor.objects.filter(rubrica=rubrica, status=True).exclude(tipoprofesor_id__in=listatipoprofesor)
                    #         delrubricatipoprofesor.delete()
                    #     for idtipoprofesor in listatipoprofesor:
                    #         if not RubricaTipoProfesor.objects.filter(rubrica=rubrica, tipoprofesor_id=idtipoprofesor, status=True):
                    #             ingresorubtipoprofesor = RubricaTipoProfesor(rubrica=rubrica, tipoprofesor_id=idtipoprofesor)
                    #             ingresorubtipoprofesor.save()
                    # else:
                    #     if RubricaTipoProfesor.objects.filter(rubrica=rubrica, status=True):
                    #         delrubricatipoprofesor = RubricaTipoProfesor.objects.filter(rubrica=rubrica, status=True)
                    #         delrubricatipoprofesor.delete()
                    log(u'Modifico rubrica de acreditacion: %s' % rubrica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addpreguntanueva':
            try:
                f = PreguntaAcreditacionForm(request.POST)
                if f.is_valid():
                    pregunta = TextoPreguntaAcreditacion(nombre=f.cleaned_data['texto'])
                    pregunta.save(request)
                    log(u'Adiciono pregunta de evaluacion: %s' % pregunta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletecriterios':
            try:
                criterios = TipoObservacionEvaluacion.objects.get(pk=request.POST['id'])
                log(u'Eliminó categoria: %s - %s - %s' % (criterios,criterios.get_tipo_display(),criterios.get_tipoinstrumento_display()), request, "del")
                criterios.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deletetipocriterios':
            try:
                tipocriterios = CriterioTipoObservacionEvaluacion.objects.get(pk=request.POST['id'])
                log(u'Eliminó tipo categoria: %s' % tipocriterios, request, "del")
                tipocriterios.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editpreguntanueva':
            try:
                f = PreguntaAcreditacionForm(request.POST)
                pregunta = TextoPreguntaAcreditacion.objects.get(pk=int(request.POST['id']))
                if pregunta.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"La pregunta se encuentra en uso."})
                if f.is_valid():
                    pregunta.nombre = f.cleaned_data['texto']
                    pregunta.save(request)
                    log(u'Modifico pregunta de evaluacion: %s' % pregunta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addpregunta':
            try:
                caracteristica = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.POST['id'])
                for pregunta in TextoPreguntaAcreditacion.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not PreguntaCaracteristicaEvaluacionAcreditacion.objects.filter(caracteristica=caracteristica, pregunta=pregunta).exists():
                        preguntacaracteristica = PreguntaCaracteristicaEvaluacionAcreditacion(caracteristica=caracteristica,
                                                                                              pregunta=pregunta)
                        preguntacaracteristica.save(request)
                log(u'Modifico preguntas de la caracteristica: %s' % caracteristica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addpreguntasrubrica':
            try:
                rubrica = Rubrica.objects.get(pk=request.POST['id'])
                for preguntacaracteristica in PreguntaCaracteristicaEvaluacionAcreditacion.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not rubrica.rubricapreguntas_set.filter(preguntacaracteristica=preguntacaracteristica).exists():
                        ultima = null_to_numeric(rubrica.rubricapreguntas_set.aggregate(mayor=Max('orden'))['mayor'])
                        rubricapregunta = RubricaPreguntas(rubrica=rubrica,
                                                           preguntacaracteristica=preguntacaracteristica,
                                                           orden=ultima + 1 if ultima else 1)
                        rubricapregunta.save(request)
                log(u'Modifico preguntas de la rubrica: %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editevidenciacolor':
            try:
                ePregunta = PreguntaCaracteristicaEvaluacionAcreditacion.objects.get(pk=int(request.POST['id']))

                f = EvidenciaColorPreguntaEncuestaForm(request.POST)
                if f.is_valid():
                    ePregunta.tipocolor = f.cleaned_data['tipo']
                    ePregunta.save(request)

                    ePregunta.pregunta.nombre = f.cleaned_data['pregunta']
                    ePregunta.pregunta.save(request)

                    log(u'Adicionó evidencia a pregunta: %s' % ePregunta, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                    return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcaracteristicarubrica':
            try:
                rubrica = Rubrica.objects.get(pk=request.POST['id'])
                for caracteristica in CaracteristicaEvaluacionAcreditacion.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not RubricaCaracteristica.objects.filter(rubrica=rubrica, caracteristica=caracteristica).exists():
                        rubricacaracteristica = RubricaCaracteristica(rubrica=rubrica,
                                                                      caracteristica=caracteristica)
                        rubricacaracteristica.save(request)
                log(u'Adiciono caracteristica a rubrica: %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcriteriodocencia':
            try:
                rubrica = Rubrica.objects.get(pk=request.POST['id'])
                rubrica.tipo_criterio = 1
                rubrica.save(request)
                for criterio in CriterioDocenciaPeriodo.objects.filter(criterio__tipo=1,id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not RubricaCriterioDocencia.objects.filter(rubrica=rubrica, criterio=criterio).exists():
                        criteriodocencia = RubricaCriterioDocencia(rubrica=rubrica,
                                                                   criterio=criterio)
                        criteriodocencia.save(request)
                log(u'Adiciono criterio docencia: %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcriteriovinculacion':
            try:
                rubrica = Rubrica.objects.get(pk=request.POST['id'])
                rubrica.tipo_criterio = 4
                rubrica.save(request)
                for criterio in CriterioDocenciaPeriodo.objects.filter(criterio__tipo=2, id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not RubricaCriterioVinculacion.objects.filter(rubrica=rubrica, criterio=criterio).exists():
                        criteriodocencia = RubricaCriterioVinculacion(rubrica=rubrica,
                                                                      criterio=criterio)
                        criteriodocencia.save(request)
                log(u'Adiciono criterio docencia: %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcriterioinvestigacion':
            try:
                rubrica = Rubrica.objects.get(pk=request.POST['id'])
                rubrica.tipo_criterio = 2
                rubrica.save(request)
                for criterio in CriterioInvestigacionPeriodo.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not RubricaCriterioInvestigacion.objects.filter(rubrica=rubrica, criterio=criterio).exists():
                        criterioinvestigacion = RubricaCriterioInvestigacion(rubrica=rubrica,
                                                                             criterio=criterio)
                        criterioinvestigacion.save(request)
                log(u'Adiciono criterio investigacion: %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcriteriogestion':
            try:
                rubrica = Rubrica.objects.get(pk=request.POST['id'])
                rubrica.tipo_criterio = 3
                rubrica.save(request)
                for criterio in CriterioGestionPeriodo.objects.filter(id__in=[int(x) for x in request.POST['lista'].split(',')]):
                    if not RubricaCriterioGestion.objects.filter(rubrica=rubrica, criterio=criterio).exists():
                        criteriogestion = RubricaCriterioGestion(rubrica=rubrica,
                                                                 criterio=criterio)
                        criteriogestion.save(request)
                log(u'Adiciono criterio gestion: %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delcaracteristica':
            try:
                caracteristica = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.POST['id'])
                log(u'Elimino caracteristica de acreditacion: %s' % caracteristica, request, "edit")
                caracteristica.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delponderacion':
            try:
                tabla = TablaPonderacionInstrumento.objects.get(pk=request.POST['id'])
                if tabla.profesordistributivohoras_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Error: la tabla no puede ser eliminada por estar en uso."})
                log(u'Elimino tabla ponderacion: %s' % tabla, request, "edit")
                tabla.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'profesores':
            try:
                profesores = []
                for profesor in Profesor.objects.filter(profesordistributivohoras__tablaponderacion__isnull=False, profesordistributivohoras__periodo=periodo):
                    mo = {'nombre': unicode(profesor.persona.nombre_completo()), 'id': profesor.id}
                    profesores.append(mo)
                return JsonResponse({"result": "ok", "cantidad": len(profesores), "profesores": profesores})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'profesoresevaluar':
            try:
                # profesores = []
                profesores = ProfesorDistributivoHoras.objects.values('id','profesor_id','profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres').filter(tablaponderacion__isnull=False, periodo=periodo).order_by('profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres')
                # for profesoresdistributivo in ProfesorDistributivoHoras.objects.select_related('profesor').filter(tablaponderacion__isnull=False, periodo=periodo):
                #     mo = {'nombre': unicode(profesoresdistributivo.profesor.persona.nombre_completo()), 'id': profesoresdistributivo.profesor.id}
                #     profesores.append(mo)
                return JsonResponse({"result": "ok", "cantidad": len(profesores), "profesores": list(profesores)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'profesoresevaluarmigrar':
            try:
                profesores = []
                for profesoresdistributivo in ProfesorDistributivoHoras.objects.filter(tablaponderacion__isnull=False, periodo=periodo):
                    mo = {'nombre': unicode(profesoresdistributivo.profesor.persona.nombre_completo()), 'id': profesoresdistributivo.profesor.id}
                    profesores.append(mo)
                return JsonResponse({"result": "ok", "cantidad": len(profesores), "profesores": profesores})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'recalcularprofesor':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                # distributivo = profesor.distributivohoras(periodo)
                distributivo = profesor.distributivohoraseval(periodo)
                resumen = distributivo.resumen_evaluacion_acreditacion()
                resumen.actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'recalcularprofesoresevaluar':
            try:
                # profesor = Profesor.objects.get(pk=request.POST['id'])
                # distributivo = profesor.distributivohoraseval(periodo)
                distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['iddistributivo'])
                # listado = RespuestaEvaluacionAcreditacion.objects.filter(procesada=False, status=True)
                distributivo.calcular_ponderaciones()
                listado = proceso.respuestaevaluacionacreditacion_set.filter(profesor=distributivo.profesor, procesada=False, tipoinstrumento__in=[2, 3, 4], status=True)
                if listado:
                    for recorrelis in listado:
                        listadores = RespuestaRubrica.objects.filter(respuestaevaluacion=recorrelis, status=True)
                        for lrespuesta in listadores:
                            lrespuesta.valor = lrespuesta.actualizar_valor()
                            lrespuesta.save()
                        recorrelis.procesada = True
                        recorrelis.valortotaldocencia = recorrelis.calcula_valor_total_docencia()
                        recorrelis.valortotalinvestigacion = recorrelis.calcula_valor_total_investigacion()
                        recorrelis.valortotalgestion = recorrelis.calcula_valor_total_gestion()
                        recorrelis.save()
                if distributivo.tablaponderacion:
                    resumen = distributivo.resumen_evaluacion_acreditacion()
                    resumen.actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'migrarprofesoresevaluar':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                distributivo = profesor.distributivohoraseval(periodo)
                resumen = distributivo.resumenfinalevaluacionacreditacion_set.filter(status=True)
                if not ResumenFinalEvaluacionAcreditacionFija.objects.filter(distributivo=distributivo):
                    for item in resumen:
                        migracion = ResumenFinalEvaluacionAcreditacionFija(distributivo=distributivo,
                                                                           promedio_docencia_hetero=item.promedio_docencia_hetero,
                                                                           promedio_docencia_auto =item.promedio_docencia_auto,
                                                                           promedio_docencia_par =item.promedio_docencia_par,
                                                                           promedio_docencia_directivo =item.promedio_docencia_directivo,
                                                                           promedio_investigacion_hetero =item.promedio_investigacion_hetero,
                                                                           promedio_investigacion_auto =item.promedio_investigacion_auto,
                                                                           promedio_investigacion_par =item.promedio_investigacion_par,
                                                                           promedio_investigacion_directivo =item.promedio_investigacion_directivo,
                                                                           promedio_gestion_hetero =item.promedio_gestion_hetero,
                                                                           promedio_gestion_auto =item.promedio_gestion_auto,
                                                                           promedio_gestion_par =item.promedio_gestion_par,
                                                                           promedio_gestion_directivo =item.promedio_gestion_directivo,
                                                                           resultado_total = item.resultado_total,
                                                                           horas_tutoria = 0,
                                                                           horas_vinculacion = 0)
                        migracion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addasignarevaluaciondirectivo':
            try:
                idp = int(request.POST['idp'])
                idpe = int(request.POST['idpe'])
                profesor = Profesor.objects.get(pk=idp)
                coordinacionprofesor = ProfesorDistributivoHoras.objects.get(periodo=proceso.periodo, profesor=profesor, status=True).coordinacion
                evaluador = Persona.objects.get(id=idpe)
                if DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(proceso=proceso, evaluado=profesor, evaluador=evaluador).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede adicionar, directivo evaluador ya se encuentra asignado."})

                tipodirector=1
                if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=2, activo=True, status=True).exists():
                    tipodirector=2
                if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=3, activo=True, status=True).exists():
                    tipodirector=3
                detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso,
                                                                            evaluado=profesor,
                                                                            coordinacion=coordinacionprofesor,
                                                                            evaluador=evaluador,
                                                                            tipodirector=tipodirector)
                detalle.save(request)
                asunto = u"EVALUACIÓN DOCENTE"
                correoevaluador = evaluador.emailpersonal()
                datos = {'sistema': request.session['nombresistema'], 'evaluador': evaluador,'evaluado': profesor,'asunto':asunto,'periodo':periodo}
                send_html_mail(asunto, "emails/evaluaciondocentepar.html", datos,
                               correoevaluador,
                               [], [],
                               cuenta=CUENTAS_CORREOS[4][1])
                log(u'Adiciono directivo evaluador en evaluación docente: proceso[%s] - profesor[%s] - direcEva[%s]' % (proceso, profesor, evaluador), request, "add")
                return JsonResponse({"result": "ok", "creacion": detalle.usuario_creacion.__str__()})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasignarevaluaciondirectivopos':
            try:
                idp = int(request.POST['idp'])
                idpe = int(request.POST['idpe'])
                idm = int(request.POST['idm'])
                profesor = Profesor.objects.get(pk=idp)
                eMateria = Materia.objects.get(pk=idm)
                # coordinacionprofesor = ProfesorDistributivoHoras.objects.get(periodo=proceso.periodo, profesor=profesor, status=True).coordinacion
                coordinacionprofesor = Coordinacion.objects.get(pk=7)
                evaluador = Persona.objects.get(id=idpe)
                eProfesorEvaluador = Profesor.objects.get(persona_id=idpe)
                if DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(proceso=proceso, evaluado=profesor, evaluador=evaluador, materia=eMateria).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede adicionar, directivo evaluador ya se encuentra asignado."})

                tipodirector=1
                if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=2, activo=True, status=True).exists():
                    tipodirector=2
                if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=3, activo=True, status=True).exists():
                    tipodirector=3
                detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso,
                                                                            evaluado=profesor,
                                                                            coordinacion=coordinacionprofesor,
                                                                            evaluador=evaluador,
                                                                            tipodirector=tipodirector,
                                                                            materia=eMateria)
                detalle.save(request)

                if periodo.tipo.id != 3:
                    return JsonResponse({"result": "bad", "mensaje": u"Seleccione un periodo de posgrado"})

                if not ProfesorDistributivoHoras.objects.filter(profesor=eProfesorEvaluador, periodo=periodo).exists():
                    distributivo = ProfesorDistributivoHoras(profesor=eProfesorEvaluador,
                                                             periodo=periodo,
                                                             dedicacion=eProfesorEvaluador.dedicacion,
                                                             horasdocencia=0,
                                                             horasinvestigacion=0,
                                                             horasgestion=0,
                                                             horasvinculacion=0,
                                                             coordinacion=eProfesorEvaluador.coordinacion,
                                                             categoria=eProfesorEvaluador.categoria,
                                                             nivelcategoria=eProfesorEvaluador.nivelcategoria,
                                                             cargo=eProfesorEvaluador.cargo,
                                                             nivelescalafon=eProfesorEvaluador.nivelescalafon)
                    distributivo.save(request)
                    log(u'Adiciono profesor distributivo hora en criterio actividad docente: %s - %s - [%s] - periodo: %s' % (eProfesorEvaluador, distributivo, distributivo.id, distributivo.periodo), request, "add")

                log(u'Adiciono directivo evaluador en evaluación docente: proceso[%s] - profesor[%s] - direcEva[%s]' % (proceso, profesor, evaluador), request, "add")
                return JsonResponse({"result": "ok", "creacion": detalle.usuario_creacion.__str__()})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delasignarevaluaciondirectivo':
            try:
                idp = int(request.POST['idp'])
                idpe = int(request.POST['idpe'])
                profesor = Profesor.objects.get(pk=idp)
                evaluador = Persona.objects.get(id=idpe)
                detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.get(proceso=proceso, evaluado=profesor, evaluador=evaluador)
                log(u'Elimino directivo evaluador en evaluación docente: id[%s] - proceso[%s] - profesor[%s] - direcEva[%s]' % (detalle.id, proceso, profesor, evaluador), request, "del")
                detalle.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delasignarevaluaciondirectivopos':
            try:
                idp = int(request.POST['idp'])
                idpe = int(request.POST['idpe'])
                idm = int(request.POST['idm'])
                profesor = Profesor.objects.get(pk=idp)
                evaluador = Persona.objects.get(id=idpe)
                materia = Materia.objects.get(pk=idm)
                detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.get(proceso=proceso, evaluado=profesor, evaluador=evaluador, materia=materia)
                log(u'Elimino directivo evaluador en evaluación docente: id[%s] - proceso[%s] - profesor[%s] - materia[%s] - direcEva[%s]' % (detalle.id, proceso, profesor, materia, evaluador), request, "del")
                detalle.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'adicionarrubricacoordinacion':
            try:
                valor = 0
                if RubricaCoordinacion.objects.filter(rubrica_id=request.POST['rubricaid'], coordinacion_id= request.POST['coordinacionid'], status=True):
                    rubricas = RubricaCoordinacion.objects.get(rubrica_id=request.POST['rubricaid'], coordinacion_id=request.POST['coordinacionid'], status=True)
                    rubricas.delete()
                    log(u'Eliminó una coordinación de rúbrica: %s' % rubricas, request, "add")
                else:
                    rubricas = RubricaCoordinacion(rubrica_id=request.POST['rubricaid'],
                                                   coordinacion_id=request.POST['coordinacionid'])
                    rubricas.save(request)
                    valor = 1
                    log(u'Agregó una coordinación a rúbrica: %s' % rubricas, request, "add")
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'preguntasrubrica':
            try:
                rubrica = Rubrica.objects.get(pk=int(request.POST['id']))
                rubrica.texto_nosatisfactorio = request.POST['texto1']
                rubrica.texto_basico = request.POST['texto2']
                rubrica.texto_competente = request.POST['texto3']
                rubrica.texto_muycompetente = request.POST['texto4']
                rubrica.texto_destacado = request.POST['texto5']
                if request.POST['nosastifactorio'] == '0':
                    rubrica.val_nosastifactorio = False
                else:
                    rubrica.val_nosastifactorio = True
                if request.POST['basico'] == '0':
                    rubrica.val_basico = False
                else:
                    rubrica.val_basico = True
                if request.POST['competente'] == '0':
                    rubrica.val_competente = False
                else:
                    rubrica.val_competente = True
                if request.POST['muycompetente'] == '0':
                    rubrica.val_muycompetente = False
                else:
                    rubrica.val_muycompetente = True
                if request.POST['destacado'] == '0':
                    rubrica.val_destacado = False
                else:
                    rubrica.val_destacado = True
                rubrica.texto_destacado = request.POST['texto5']
                if request.POST['valoractiva'] == '0':
                    rubrica.valorprecalificada = 0
                    rubrica.precalificada = False
                else:
                    rubrica.valorprecalificada = request.POST['valoractiva']
                    rubrica.precalificada = True
                rubrica.save(request)
                rubrica.rubricapreguntas_set.all().delete()
                for elemento in request.POST['lista'].split(';'):
                    individuales = elemento.split(':')
                    rubricapregunta = RubricaPreguntas(preguntacaracteristica=PreguntaCaracteristicaEvaluacionAcreditacion.objects.get(pk=int(individuales[0])),
                                                       rubrica=rubrica,
                                                       orden=int(individuales[1]))
                    rubricapregunta.save(request)
                log(u'Modifico orden y respuestas de rubrica: %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'activacioninstrumento':
            try:
                f = ActivacionInstrumentoEvaluacionAcreditacionForm(request.POST)
                if f.is_valid():
                    desde = f.cleaned_data['desde']
                    hasta = f.cleaned_data['hasta']
                    activo = f.cleaned_data['activo']
                    tipo = int(request.POST['tipo'])
                    if tipo == 1:
                        proceso.instrumentoheteroinicio = desde
                        proceso.instrumentoheterofin = hasta
                        proceso.instrumentoheteroactivo = activo
                    elif tipo == 2:
                        proceso.instrumentoautoinicio = desde
                        proceso.instrumentoautofin = hasta
                        proceso.instrumentoautoactivo = activo
                    elif tipo == 3:
                        proceso.instrumentodirectivoinicio = desde
                        proceso.instrumentodirectivofin = hasta
                        proceso.instrumentodirectivoactivo = activo
                    elif tipo == 4:
                        proceso.instrumentoparinicio = desde
                        proceso.instrumentoparfin = hasta
                        proceso.instrumentoparactivo = activo
                    elif tipo == 5:
                        proceso.instrumentorevisioninicio = desde
                        proceso.instrumentorevisionfin = hasta
                        proceso.instrumentorevisionactivo = activo
                    proceso.save(request)
                    log(u'Modifico activacion del proceso: %s' % proceso, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'desactivar':
            try:
                tipo=TipoObservacionEvaluacion.objects.get(id=request.POST['idcriterio'])
                if tipo.activo == True:
                    tipo.activo=False
                    valor=0
                elif tipo.activo == False :
                    tipo.activo=True
                    valor=1
                tipo.save(request)
                log(u'desactivo criterio evaluacion: %s' % tipo, request, "edit")
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # elif action == 'ejecutarreporte':
        #     try:
        #         idper= request.POST['periodo']
        #         idcarr= request.POST['carrera']
        #         carrera = Carrera.objects.get(id=idcarr,coordinacion__excluir=False)
        #         coordinacion=carrera.coordinacion_set.get(status=True).nombre
        #         periodo=Periodo.objects.get(id=idper)
        #         __author__ = 'Unemi'
        #         style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
        #         style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
        #                           num_format_str='#,##0.00')
        #         style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
        #         title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
        #         style1 = easyxf(num_format_str='D-MMM-YY')
        #         font_style = XFStyle()
        #         font_style.font.bold = True
        #         font_style2 = XFStyle()
        #         font_style2.font.bold = False
        #         borders = Borders()
        #         borders.left = 1
        #         borders.right = 1
        #         borders.top = 1
        #         borders.bottom = 1
        #         title = easyxf(
        #             'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
        #         title2 = easyxf(
        #             'font: name Times New Roman, color-index black, bold on , height 275; alignment: horiz centre')
        #         subtitulo = easyxf(
        #             'font: name Times New Roman, bold on, height 200; align:wrap on, horiz centre, vert centre')
        #         normal = easyxf('font: name Times New Roman, height 200; alignment: horiz left')
        #         nnormal = easyxf('font: name Times New Roman, height 200; alignment: horiz centre')
        #         subtitulo.borders = borders
        #         normal.borders = borders
        #         nnormal.borders = borders
        #         wb = Workbook(encoding='utf-8')
        #         ws = wb.add_sheet('exp_xls_post_part')
        #         ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
        #         ws.write_merge(1, 1, 0, 11, periodo.__str__(), title)
        #         ws.write_merge(2, 2, 0, 10,coordinacion, title)
        #         ws.write_merge(3, 3, 0, 10, carrera.nombre_completo(), title)
        #         response = HttpResponse(content_type="application/ms-excel")
        #         response['Content-Disposition'] = 'attachment; filename=detalle_evaluacion_heterounocarrera_promedio' + random.randint(1, 10000).__str__() + '.xls'
        #         row_num = 5
        #         ws.write_merge(row_num, row_num, 0, 1, u'Encuesta', subtitulo)
        #         cursor = connection.cursor()
        #         # sql="select * from " \
        #         #     "( " \
        #         #     "select pro.id as idprofesor,per.apellido1||' '|| per.apellido2 ||' '|| per.nombres as docente, " \
        #         #     "ru.nombre,substring(carac.nombre,1,4) as tipopregunta,rp.orden as id, " \
        #         #     "count(rea.id) as numero_preguntas,round(avg(drr.valor),1), " \
        #         #     "(select nombre from sga_coordinacion_carrera ccar,sga_coordinacion cor where " \
        #         #     "ccar.coordinacion_id=cor.id and carrera_id="+str(carrera.id)+") as facultad, " \
        #         #     "(select nombre from sga_carrera where id="+str(carrera.id)+") as carreras, " \
        #         #     "(select nombre from sga_periodo where id="+str(periodo.id)+") as periodo " \
        #         #     "from sga_respuestaevaluacionacreditacion rea , sga_respuestarubrica rr, " \
        #         #     "sga_rubrica ru, " \
        #         #     "sga_rubricapreguntas rp, " \
        #         #     "sga_preguntacaracteristicaevaluacionacreditacion rpe, " \
        #         #     "sga_textopreguntaacreditacion txta,sga_profesor pro,sga_persona per, " \
        #         #     "sga_detallerespuestarubrica drr , " \
        #         #     "sga_caracteristicaevaluacionacreditacion carac, " \
        #         #     "sga_procesoevaluativoacreditacion peas " \
        #         #     "where rea.profesor_id=pro.id " \
        #         #     "and pro.persona_id=per.id " \
        #         #     "and rea.tipoinstrumento=1 " \
        #         #     "and rr.respuestaevaluacion_id=rea.id " \
        #         #     "and rr.rubrica_id=ru.id  " \
        #         #     "and rea.proceso_id=peas.id  " \
        #         #     "and peas.periodo_id="+str(periodo.id)+"" \
        #         #     "and ru.tipo_criterio<>0  " \
        #         #     "and ru.para_hetero=true  " \
        #         #     "and rp.rubrica_id=ru.id  " \
        #         #     "and rp.preguntacaracteristica_id=rpe.id  " \
        #         #     "and rpe.pregunta_id=txta.id  " \
        #         #     "and drr.respuestarubrica_id=rr.id  " \
        #         #     "and drr.rubricapregunta_id=rp.id  " \
        #         #     "and rpe.caracteristica_id=carac.id  " \
        #         #     "/*and rea.materiaasignada_id  is not null*/  " \
        #         #     "and substring(carac.nombre,1,4) not like '%B%'  " \
        #         #     "group by ru.tipo_criterio,ru.nombre,pro.id,per.apellido1,per.apellido2,per.nombres,rp.orden,carac.nombre,txta.id  " \
        #         #     "order by 1,2,4  " \
        #         #     ") as d  " \
        #         #     "where idprofesor in(  " \
        #         #     "select distinct reas.profesor_id from sga_respuestaevaluacionacreditacion reas, sga_procesoevaluativoacreditacion pea  " \
        #         #     "where reas.carrera_id="+str(carrera.id)+"  " \
        #         #     "and reas.tipoinstrumento=1  " \
        #         #     "and reas.proceso_id=pea.id  " \
        #         #     "and pea.periodo_id="+str(periodo.id)+" " \
        #         #     ")  " \
        #         #     "order by 1,2,4"
        #         sql="select pro.id as idprofesor,per.apellido1||' '|| per.apellido2 ||' '|| per.nombres as docente,  " \
        #             "ru.nombre,substring(carac.nombre,1,4) as tipopregunta,rp.orden as orden,  " \
        #             "count(rea.id) as numero_preguntas,round(avg(drr.valor),1),  " \
        #             "(select nombre from sga_coordinacion_carrera ccar,sga_coordinacion cor where  " \
        #             "ccar.coordinacion_id=cor.id and carrera_id=22) as facultad,  " \
        #             "(select nombre from sga_carrera where id=22) as carreras, " \
        #             "(select nombre from sga_periodo where id=11) as periodo " \
        #             "from sga_respuestaevaluacionacreditacion rea , sga_respuestarubrica rr, " \
        #             "sga_rubrica ru, " \
        #             "sga_rubricapreguntas rp, " \
        #             "sga_preguntacaracteristicaevaluacionacreditacion rpe, " \
        #             "sga_textopreguntaacreditacion txta,sga_profesor pro,sga_persona per, " \
        #             "sga_detallerespuestarubrica drr , " \
        #             "sga_caracteristicaevaluacionacreditacion carac, " \
        #             "sga_procesoevaluativoacreditacion peas " \
        #             "where rea.profesor_id=pro.id " \
        #             "and pro.persona_id=per.id " \
        #             "and rea.tipoinstrumento=1 " \
        #             "and rr.respuestaevaluacion_id=rea.id " \
        #             "and rr.rubrica_id=ru.id " \
        #             "and rea.proceso_id=peas.id " \
        #             "and peas.periodo_id=11 " \
        #             "and ru.tipo_criterio<>0 " \
        #             "and ru.para_hetero=true " \
        #             "and rp.rubrica_id=ru.id " \
        #             "and rp.preguntacaracteristica_id=rpe.id " \
        #             "and rpe.pregunta_id=txta.id " \
        #             "and drr.respuestarubrica_id=rr.id " \
        #             "and drr.rubricapregunta_id=rp.id " \
        #             "and rpe.caracteristica_id=carac.id " \
        #             "and rea.profesor_id= 234 " \
        #             "and substring(carac.nombre,1,4) not like '%B%' " \
        #             "group by ru.tipo_criterio,ru.nombre,pro.id,per.apellido1,per.apellido2,per.nombres,rp.orden,carac.nombre,txta.id,carac.id,txta.nombre " \
        #             "order by 1,2,4 "
        #         cursor.execute(sql)
        #         results = cursor.fetchall()
        #         rubrica=[]
        #         pregunta=[]
        #         for res in results:
        #             if not res[2] in rubrica:
        #                 rubrica.append(res[2])
        #         for res in results:
        #             if pregunta.__len__()>0:
        #                 if not res[4] in pregunta:
        #                     pregunta.append([res[2],res[4]])
        #             else:
        #                 pregunta.append([res[2], res[4]])
        #
        #         for col_num in range(len(pregunta)):
        #             ws.write(row_num, col_num, columns[col_num][0], font_style)
        #             ws.col(col_num).width = columns[col_num][1]
        #
        #         # columns = [
        #         #     (u"No.", 1500),
        #         #     (u"FACULTAD", 6000),
        #         #     (u"CARRERA", 6000),
        #         #     (u"CEDULA", 3000),
        #         #     (u"ALUMNO", 6000),
        #         #     (u"ENCUESTA", 6000),
        #         #     (u"FECHA DE ENCUESTA", 3000),
        #         #     (u"INICIO PRIMER NIVEL", 3000),
        #         #     (u"FECHA GRADUACION", 3000),
        #         #     (u"NOTA FINAL", 6000),
        #         #     (u"PAIS", 6000),
        #         #     (u"PROVINCIA", 6000),
        #         #     (u"CANTON", 6000),
        #         #     (u"PARROQUIA", 6000),
        #         #     (u"CALLE PRINCIPAL", 6000),
        #         #     (u"CALLE SECUNDARIA", 6000),
        #         #     (u"EMAIL", 6000),
        #         #     (u"EMAIL INSTITUCIONAL", 6000),
        #         #     (u"TELEFONO", 4000),
        #         #     (u"TELEFONO CONVENCIONAL", 4000),
        #         #     (u"SEXO", 6000),
        #         #     (u"LGBTI", 3000),
        #         #     (u"INICIO CONVALIDACION", 3000)
        #         # # ]
        #         # for col_num in range(len(columns)):
        #         #     ws.write(row_num, col_num, columns[col_num][0], font_style)
        #         #     ws.col(col_num).width = columns[col_num][1]
        #         # cursor = connection.cursor()
        #         # date_format = xlwt.XFStyle()
        #         # date_format.num_format_str = 'yyyy/mm/dd'
        #         # sql = "select co.nombre as Facultad, (ca.nombre||' '||ca.mencion) as Carrera,  " \
        #         #       "p.cedula,(p.apellido1||' '||p.apellido2||' '||p.nombres) as alumno,  " \
        #         #       "(case when res.fecha_creacion IS NULL  then 'NO ENCUESTADO' else 'ENCUESTADO' end) as encuestado,  " \
        #         #       "res.fecha_creacion as fechaencuesta,i.fechainicioprimernivel,gr.fechagraduado, gr.notafinal, " \
        #         #       "(select nombre from sga_pais where id=p.pais_id) as pais, (select nombre from sga_provincia where id=p.provincia_id) as provincia, " \
        #         #       "(select nombre from sga_canton where id=p.canton_id) as canton,(select nombre from sga_parroquia where id=p.parroquia_id) as parroquia, " \
        #         #       "p.direccion,p.direccion2,p.email,p.emailinst,p.telefono,p.telefono_conv, (select nombre from sga_sexo sexo where sexo.id=p.sexo_id ) as sexo, " \
        #         #       "p.lgtbi,i.fechainicioconvalidacion " \
        #         #       "from sga_persona p  join sga_inscripcion i on i.persona_id=p.id " \
        #         #       "join sga_graduado gr on gr.inscripcion_id=i.id " \
        #         #       "join sga_carrera ca on i.carrera_id=ca.id " \
        #         #       "join sga_coordinacion_carrera cc on cc.carrera_id=ca.id " \
        #         #       "join sga_coordinacion co on co.id = cc.coordinacion_id left join sga_sagresultadoencuesta res on res.inscripcion_id=i.id  " \
        #         #       " and res.sagperiodo_id=" + idp + " order by co.nombre,ca.nombre,gr.fechagraduado "
        #         # cursor.execute(sql)
        #         # results = cursor.fetchall()
        #         # row_num = 4
        #         # i = 0
        #         # for r in results:
        #         #     campo1 = r[0]
        #         #     campo2 = r[1]
        #         #     campo3 = r[2]
        #         #     campo4 = r[3]
        #         #     campo5 = r[4]
        #         #     if r[5]:
        #         #         campo6 = r[5]
        #         #     else:
        #         #         campo6 = ''
        #         #     campo7 = r[6]
        #         #     campo8 = r[7]
        #         #     campo9 = r[8]
        #         #     campo10 = r[9]
        #         #     campo11 = r[10]
        #         #     campo12 = r[11]
        #         #     campo13 = r[12]
        #         #     campo14 = r[13]
        #         #     campo15 = r[14]
        #         #     campo16 = r[15]
        #         #     campo17 = r[16]
        #         #     campo18 = r[17]
        #         #     campo19 = r[18]
        #         #     campo20 = r[19]
        #         #     if r[20]:
        #         #         campo21 = 'SI'
        #         #     else:
        #         #         campo21 = 'NO'
        #         #     campo22 = r[21]
        #         #     i += 1
        #         #     ws.write(row_num, 0, i, font_style2)
        #         #     ws.write(row_num, 1, campo1, font_style2)
        #         #     ws.write(row_num, 2, campo2, font_style2)
        #         #     ws.write(row_num, 3, campo3, font_style2)
        #         #     ws.write(row_num, 4, campo4, font_style2)
        #         #     ws.write(row_num, 5, campo5, font_style2)
        #         #     ws.write(row_num, 6, campo6, style1)
        #         #     ws.write(row_num, 7, campo7, date_format)
        #         #     ws.write(row_num, 8, campo8, style1)
        #         #     ws.write(row_num, 9, campo9, font_style2)
        #         #     ws.write(row_num, 10, campo10, font_style2)
        #         #     ws.write(row_num, 11, campo11, font_style2)
        #         #     ws.write(row_num, 12, campo12, font_style2)
        #         #     ws.write(row_num, 13, campo13, font_style2)
        #         #     ws.write(row_num, 14, campo14, font_style2)
        #         #     ws.write(row_num, 15, campo15, font_style2)
        #         #     ws.write(row_num, 16, campo16, font_style2)
        #         #     ws.write(row_num, 17, campo17, font_style2)
        #         #     ws.write(row_num, 18, campo18, font_style2)
        #         #     ws.write(row_num, 19, campo19, font_style2)
        #         #     ws.write(row_num, 20, campo20, font_style2)
        #         #     ws.write(row_num, 21, campo21, font_style2)
        #         #     ws.write(row_num, 22, campo22, date_format)
        #         #     row_num += 1
        #         wb.save(response)
        #         return response
        #     except Exception as ex:
        #         pass
        #

        elif action == 'actualizayasignaciondirectivo':
            try:
                vicerectorado = DistributivoPersona.objects.filter((Q(denominacionpuesto__id=796) | Q(denominacionpuesto__id=115)), Q(estadopuesto__id=PUESTO_ACTIVO_ID))
                vinculacion = DistributivoPersona.objects.filter(denominacionpuesto__id=797, status=True)
                periodo.actualizar_carrera_profesores()
                log(u'Actualizo carreras y coordinación según a la mayor carga horarias de los docentes desde evaluacion docente acreditacion [Persona: %s, Periodo: %s]' % (persona.nombre_completo_inverso(), periodo), request, "add")
                # coordinaciones = Coordinacion.objects.filter(excluir=False).exclude(id__in=[9,7])
                coordinaciones = Coordinacion.objects.filter(excluir=False).exclude(id__in=[9])
                # decanosfacultades = ResponsableCoordinacion.objects.filter(periodo=proceso.periodo, persona__profesor__isnull=False, tipo=1, coordinacion__in=coordinaciones)
                # directorescarreras = CoordinadorCarrera.objects.filter(periodo=proceso.periodo, persona__profesor__isnull=False, carrera__coordinacion__in=coordinaciones).exclude(persona__id__in=decanosfacultades.values_list('persona__id')).distinct('persona')
                # idprofesores_asignadosdirectivo = []

                # if vicerectorado.exists():
                #     # DECANOS SE REGISTRA COMO DIRECTIVO A VICERECTORADO E INVESTIGACION
                #     for decanofacultad in decanosfacultades:
                #         profesor = Profesor.objects.get(persona=decanofacultad.persona)
                #         idprofesores_asignadosdirectivo.append(profesor.id)
                #         detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso, evaluado=profesor, coordinacion=decanofacultad.coordinacion, evaluador=vicerectorado[0].persona)
                #         detalle.save(request)
                # DIRECTORES DE CARRERA SE REGISTRA COMO DIRECTIVO A SU DECANO DE FACULTAD
                # for directorcarrera in directorescarreras:
                #     profesor = Profesor.objects.get(persona=directorcarrera.persona)
                #     idprofesores_asignadosdirectivo.append(profesor.id)
                #     DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(proceso=proceso, evaluado=profesor).delete()
                #     coordinacionprofesor = ProfesorDistributivoHoras.objects.get(periodo=proceso.periodo, profesor=profesor, status=True)
                #     decano = coordinacionprofesor.coordinacion.responsable_periododos(proceso.periodo, 1)
                #     detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso, evaluado=profesor, coordinacion=coordinacionprofesor.coordinacion, evaluador=decano.persona)
                #     detalle.save(request)

                # PROFESORES CON NORMALES SE LE ASIGNA AL DECANO DE CARRERA EXCEPTO ADMISION
                # profesoresnormales = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, status=True, coordinacion__in=coordinaciones, carrera__isnull=False).exclude(profesor__id__in=idprofesores_asignadosdirectivo)

                opc = int(request.POST['opc'])
                if opc == 1:
                    DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(proceso=proceso, tipodirector=1).delete()
                    profesoresnormales = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, status=True, coordinacion__in=coordinaciones, profesor__persona__real=True).distinct()
                    for profesornormal in profesoresnormales:
                        if profesornormal.coordinacion.id == 11:
                            if vinculacion:
                                detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso, evaluado=profesornormal.profesor, coordinacion=profesornormal.coordinacion, evaluador=vinculacion[0].persona)
                                detalle.save(request)
                        else:
                            if ResponsableCoordinacion.objects.filter(coordinacion_id=profesornormal.coordinacion.id, periodo_id=proceso.periodo.id, status=True).exists():
                                directorcarrera = ResponsableCoordinacion.objects.filter(coordinacion_id=profesornormal.coordinacion.id, periodo_id=proceso.periodo.id, status=True)[0]
                                detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso, evaluado=profesornormal.profesor, coordinacion=profesornormal.coordinacion, evaluador=directorcarrera.persona)
                                detalle.save(request)

                if opc == 2:
                    DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(proceso=proceso, tipodirector=1).delete()
                    profesoresnormales = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, status=True, coordinacion__in=coordinaciones,detalledistributivo__criteriodocenciaperiodo__criterio__tipo=1,  carrera__isnull=False, profesor__persona__real=True).distinct().exclude(coordinacion_id=9)
                    for profesornormal in profesoresnormales:
                        if CoordinadorCarrera.objects.filter(carrera_id=profesornormal.carrera.id, periodo_id=proceso.periodo.id, tipo=3, status=True).exists():
                            directorcarrera = CoordinadorCarrera.objects.filter(carrera_id=profesornormal.carrera.id, periodo_id=proceso.periodo.id, tipo=3, status=True)[0]
                            if not DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values("id").filter(proceso=proceso, evaluado=profesornormal.profesor, coordinacion=profesornormal.coordinacion, evaluador=directorcarrera.persona, tipodirector=1).exists():
                                detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso, evaluado=profesornormal.profesor, coordinacion=profesornormal.coordinacion, evaluador=directorcarrera.persona)
                                detalle.save(request)

                if opc == 3:
                    DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(proceso=proceso, tipodirector=2).delete()
                    profesoresnormales = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, detalledistributivo__criterioinvestigacionperiodo__isnull=False, status=True, profesor__persona__real=True).exclude(coordinacion_id=9).distinct()
                    directorinvestigacion = ParesInvestigacionVinculacion.objects.filter(tipo=2, status=True)[0]
                    for profesornormal in profesoresnormales:
                        if not DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values("id").filter(proceso=proceso, evaluado=profesornormal.profesor, coordinacion=profesornormal.coordinacion, evaluador=directorinvestigacion.persona, tipodirector=2).exists():
                            detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso, evaluado=profesornormal.profesor, coordinacion=profesornormal.coordinacion, evaluador=directorinvestigacion.persona, tipodirector=2)
                            detalle.save(request)

                if opc == 4:
                    DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(proceso=proceso, tipodirector=3).delete()
                    profesoresnormales = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, detalledistributivo__criteriodocenciaperiodo__criterio__tipo=2, status=True, profesor__persona__real=True).exclude(coordinacion_id=9).distinct()
                    directorvinculacion = ParesInvestigacionVinculacion.objects.filter(tipo=3, status=True)[0]
                    for profesornormal in profesoresnormales:
                        if not DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values("id").filter(proceso=proceso, evaluado=profesornormal.profesor, coordinacion=profesornormal.coordinacion, evaluador=directorvinculacion.persona, tipodirector=3).exists():
                            detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso, evaluado=profesornormal.profesor, coordinacion=profesornormal.coordinacion, evaluador=directorvinculacion.persona, tipodirector=3)
                            detalle.save(request)

                # if vicerectorado.exists():
                #     # PROFESORES DE ADMISION SE LE ASIGNA VICERECTORADO
                #     profesoresnormalesadmision = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, status=True, coordinacion__id=9).exclude(profesor__id__in=idprofesores_asignadosdirectivo)
                #     for profesoresnormaladmision in profesoresnormalesadmision:
                #         detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso, evaluado=profesoresnormaladmision.profesor, coordinacion=profesoresnormaladmision.coordinacion, evaluador=vicerectorado[0].persona)
                #         detalle.save(request)
                log(u'Asigno docentes directivo desde evaluacion docente acreditacion [Persona: %s, Periodo: %s]' % (persona.nombre_completo_inverso(), periodo), request, "add")
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'actualizayasignaciondirectivopos':
            try:
                opc = int(request.POST['opc'])
                if opc == 1:
                    evaluador = None
                    eProfesoresMaterias = ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=periodo, tipoprofesor__id__in=[11], materia__cerrado=True)
                    eCarrera = eProfesoresMaterias[0].materia.asignaturamalla.malla.carrera
                    coordinacionprofesor = Coordinacion.objects.get(pk=7)

                    if eCarrera.escuelaposgrado:
                        if eCarrera.escuelaposgrado.id == 1:
                            evaluador = Persona.objects.get(pk=Departamento.objects.get(pk=216).responsable.id)
                        elif eCarrera.escuelaposgrado.id == 2:
                            evaluador = Persona.objects.get(pk=Departamento.objects.get(pk=215).responsable.id)
                        elif eCarrera.escuelaposgrado.id == 3:
                            evaluador = Persona.objects.get(pk=Departamento.objects.get(pk=163).responsable.id)
                        else:
                            raise NameError("No existe director de escuela para esta carrera")
                    else:
                        raise NameError("No existe director de escuela para esta carrera")

                    tipodirector = 1
                    if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=2, activo=True, status=True).exists():
                        tipodirector = 2
                    if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=3, activo=True, status=True).exists():
                        tipodirector = 3

                    for eProfesorMateria in eProfesoresMaterias:
                        if not DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True, proceso=proceso, coordinacion__id=7, evaluado=eProfesorMateria.profesor, materia=eProfesorMateria.materia).exists():
                            detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso,
                                                                                        evaluado=eProfesorMateria.profesor,
                                                                                        coordinacion=coordinacionprofesor,
                                                                                        evaluador=evaluador,
                                                                                        tipodirector=tipodirector,
                                                                                        materia=eProfesorMateria.materia)
                            detalle.save(request)

                            log(u'Adiciono directivo evaluador en evaluación docente: proceso[%s] - profesor[%s] - direcEva[%s]' % (proceso, eProfesorMateria.profesor, evaluador), request, "add")

                if opc == 2:
                    evaluador = None
                    eProfesoresMaterias = ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=periodo, tipoprofesor__id__in=[11], materia__cerrado=True)
                    eCarrera = eProfesoresMaterias[0].materia.asignaturamalla.malla.carrera
                    coordinacionprofesor = Coordinacion.objects.get(pk=7)

                    evaluador = 0

                    if CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=eCarrera).exists():
                        evaluador = CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=eCarrera).order_by('-id').first().coordinador
                    else:
                        raise NameError("No existe coordinador de escuela para esta carrera")

                    tipodirector = 1
                    if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=2, activo=True, status=True).exists():
                        tipodirector = 2
                    if proceso.paresinvestigacionvinculacion_set.values('id').filter(persona=evaluador, tipo=3, activo=True, status=True).exists():
                        tipodirector = 3

                    for eProfesorMateria in eProfesoresMaterias:
                        if not DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.filter(status=True, proceso=proceso, coordinacion__id=7, evaluado=eProfesorMateria.profesor, materia=eProfesorMateria.materia).exists():
                            detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion(proceso=proceso,
                                                                                        evaluado=eProfesorMateria.profesor,
                                                                                        coordinacion=coordinacionprofesor,
                                                                                        evaluador=evaluador,
                                                                                        tipodirector=tipodirector,
                                                                                        materia=eProfesorMateria.materia)
                            detalle.save(request)

                            log(u'Adiciono directivo evaluador en evaluación docente: proceso[%s] - profesor[%s] - direcEva[%s]' % (proceso, eProfesorMateria.profesor, evaluador), request, "add")
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'informedocentessindirectivos':
            try:
                detalle = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values_list('evaluado__id').filter(proceso=proceso, status=True).distinct()
                profesoresdistributivo = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, profesor__persona__real=True, status=True).exclude(coordinacion_id=9).exclude(profesor__id__in=detalle).distinct().order_by('profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres')
                return conviert_html_to_pdf('adm_evaluaciondocentesacreditacion/informe_docentes_sindirectivos_pdf.html', {'pagesize': 'A4', 'profesoresdistributivo': profesoresdistributivo, 'periodo':proceso.periodo})
            except Exception as ex:
                pass

        elif action == 'addcronogramaencuesta':
            try:
                f = CronogramaEncuestaProcesoEvaluativoForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['fechainicio'] <= f.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor a la fecha de fin."})
                    cronograma = CronogramaEncuestaProcesoEvaluativo(periodo=periodo, fechainicio=f.cleaned_data['fechainicio'], fechafin=f.cleaned_data['fechafin'], nombre=f.cleaned_data['nombre'])
                    cronograma.save(request)
                    log(u'Adiciono cronograma de encuesta del proceso evaluativo: %s - %s' % (cronograma.fechainicio, cronograma.fechafin), request, "add")
                    for nivel in f.cleaned_data['niveles']:
                        cronogramanivel = CronogramaEncuestaProcesoEvaluativo_Nivel(cronogramaencuesta = cronograma, nivel = nivel)
                        cronogramanivel.save(request)
                        log(u'Adiciono cronograma de encuesta del proceso evaluativo a nivel: %s - %s' % (cronogramanivel.cronogramaencuesta, cronogramanivel.nivel), request,"add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editcronogramaencuesta':
            try:
                f = CronogramaEncuestaProcesoEvaluativoForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['fechainicio'] <= f.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor a la fecha de fin."})
                    cronograma = CronogramaEncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                    cronograma.nombre = f.cleaned_data['nombre']
                    cronograma.fechainicio = f.cleaned_data['fechainicio']
                    cronograma.fechafin = f.cleaned_data['fechafin']
                    cronograma.save(request)
                    log(u'Edito cronograma de encuesta del proceso evaluativo: %s - %s' % (cronograma.fechainicio, cronograma.fechafin), request, "edit")
                    for nivel in f.cleaned_data['niveles']:
                        if not CronogramaEncuestaProcesoEvaluativo_Nivel.objects.values('id').filter(cronogramaencuesta = cronograma, nivel = nivel).exists():
                            cronogramanivel = CronogramaEncuestaProcesoEvaluativo_Nivel(cronogramaencuesta = cronograma, nivel = nivel)
                            cronogramanivel.save(request)
                            log(u'Adiciono cronograma de encuesta del proceso evaluativo a nivel: %s - %s' % (cronogramanivel.cronogramaencuesta, cronogramanivel.nivel), request,"add")
                    for niveleliminar in CronogramaEncuestaProcesoEvaluativo_Nivel.objects.filter(cronogramaencuesta = cronograma).exclude(nivel__in = f.cleaned_data['niveles']):
                        if niveleliminar.puede_eliminar_nivel():
                            log(u'Elimino cronograma de encuesta del proceso evaluativo a nivel: %s - %s' % (niveleliminar.cronogramaencuesta, niveleliminar.nivel), request,"del")
                            niveleliminar.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delcronogramaencuesta':
            try:
                cronogramaencuesta = CronogramaEncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                if not cronogramaencuesta.puede_eliminar_cronograma():
                    return JsonResponse({"result": "bad", "mensaje": "No puede eliminar cronograma porque se esta usando."})
                log(u'Elimino cronograma de encuesta del proceso evaluativo: %s - %s' % ( cronogramaencuesta.fechainicio, cronogramaencuesta.fechafin), request, "del")
                cronogramaencuesta.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        # ENCUESTA
        elif action == 'addencuesta':
            try:
                f = EncuestaProcesoEvaluativoForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['fechainicio'] <= f.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor a la fecha de fin."})
                    cronogramaencuesta = CronogramaEncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                    encuesta = EncuestaProcesoEvaluativo(cronogramaencuesta=cronogramaencuesta,
                                                         titulo=f.cleaned_data['titulo'],
                                                         fechainicio=f.cleaned_data['fechainicio'],
                                                         fechafin=f.cleaned_data['fechafin'],
                                                         estudiante=f.cleaned_data['estudiante'],
                                                         profesor=f.cleaned_data['profesor'],
                                                         encuestaobligatoria=f.cleaned_data['encuestaobligatoria'],
                                                         activo=f.cleaned_data['activo'])
                    encuesta.save(request)
                    log(u'Adiciono encuesta del proceso evaluativo: %s - %s - %s - %s - %s - %s' % (encuesta.titulo, encuesta.fechainicio, encuesta.fechafin, encuesta.estudiante, encuesta.profesor, encuesta.activo), request, "add")
                    for carrera in f.cleaned_data['carrera']:
                        encuestacarrera = EncuestaProcesoEvaluativo_Carrera(encuestaproceso=encuesta, carrera=carrera)
                        encuestacarrera.save(request)
                        log(u'Adiciono encuesta del proceso evaluativo la carrera: encuesta [%s - %s - %s - %s - %s - %s] - carrera[%s]' % (encuesta.titulo, encuesta.fechainicio, encuesta.fechafin, encuesta.estudiante, encuesta.profesor, encuesta.activo, encuestacarrera.carrera), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editencuesta':
            try:
                f = EncuestaProcesoEvaluativoForm(request.POST)
                if f.is_valid():
                    if not f.cleaned_data['fechainicio'] <= f.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": "La fecha de inicio no puede ser mayor a la fecha de fin."})
                    encuesta = EncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                    encuesta.titulo = f.cleaned_data['titulo']
                    encuesta.fechainicio = f.cleaned_data['fechainicio']
                    encuesta.fechafin = f.cleaned_data['fechafin']
                    encuesta.estudiante = f.cleaned_data['estudiante']
                    encuesta.profesor = f.cleaned_data['profesor']
                    encuesta.encuestaobligatoria = f.cleaned_data['encuestaobligatoria']
                    encuesta.activo = f.cleaned_data['activo']
                    encuesta.save(request)
                    log(u'Edito encuesta del proceso evaluativo: %s - %s - %s - %s - %s - %s' % (encuesta.titulo, encuesta.fechainicio, encuesta.fechafin, encuesta.estudiante, encuesta.profesor, encuesta.activo), request, "edit")
                    for carrera in f.cleaned_data['carrera']:
                        if not EncuestaProcesoEvaluativo_Carrera.objects.values('id').filter(encuestaproceso=encuesta, carrera=carrera).exists():
                            encuestacarrera = EncuestaProcesoEvaluativo_Carrera(encuestaproceso=encuesta, carrera=carrera)
                            encuestacarrera.save(request)
                            log(u'Adiciono por editar encuesta del proceso evaluativo la carrera: encuesta [%s - %s - %s - %s - %s - %s] - carrera[%s]' % (encuesta.titulo, encuesta.fechainicio, encuesta.fechafin, encuesta.estudiante, encuesta.profesor, encuesta.activo, encuestacarrera.carrera), request, "add")
                    for carreraeliminar in EncuestaProcesoEvaluativo_Carrera.objects.filter(encuestaproceso=encuesta).exclude(carrera__in=f.cleaned_data['carrera']):
                        log(u'Elimino carrera porque se deseleccionado por editar la encuesta del proceso evaluativo la carrera: encuesta [%s - %s - %s - %s - %s - %s] - carrera[%s]' % (encuesta.titulo, encuesta.fechainicio, encuesta.fechafin, encuesta.estudiante, encuesta.profesor, encuesta.activo, carreraeliminar.carrera), request, "add")
                        carreraeliminar.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delencuesta':
            try:
                encuesta = EncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino encuesta del proceso evaluativo: %s - %s - %s - %s - %s - %s' % (encuesta.titulo, encuesta.fechainicio, encuesta.fechafin, encuesta.estudiante, encuesta.profesor, encuesta.activo), request, "del")
                encuesta.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        # PREGUNTA
        elif action == 'addpreguntaproceso':
            try:
                f = PreguntaProcesoEvaluativoForm(request.POST)
                if f.is_valid():
                    pregunta = PreguntaProcesoEvaluativo(nombre=f.cleaned_data['nombre'], activo=f.cleaned_data['activo'])
                    pregunta.save(request)
                    log(u'Adiciono pregunta del proceso evaluativo: %s - %s' % (pregunta.nombre, pregunta.activo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editpreguntaproceso':
            try:
                f = PreguntaProcesoEvaluativoForm(request.POST)
                if f.is_valid():
                    pregunta = PreguntaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                    pregunta.nombre = f.cleaned_data['nombre']
                    pregunta.activo = f.cleaned_data['activo']
                    pregunta.save(request)
                    log(u'Edito pregunta del proceso evaluativo: %s - %s' % (pregunta.nombre, pregunta.activo), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delpreguntaproceso':
            try:
                pregunta = PreguntaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                log(u'Elimino pregunta del proceso evaluativo: %s - %s' % (pregunta.nombre, pregunta.activo), request, "del")
                pregunta.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        # ENCUESTA PREGUNTA
        elif action == 'elegirpregunta':
            try:
                listaspregunta = json.loads(request.POST['listaspregunta'])
                preguntas = PreguntaProcesoEvaluativo.objects.filter(activo=True, status=True).exclude(pk__in=[int(encrypt(lista['id'])) for lista in listaspregunta])
                if 'id' in request.POST:
                    preguntaencuesta = EncuestaProcesoEvaluativo_Pregunta.objects.get(pk=int(encrypt(request.POST['id'])))
                    opcionencuesta = EncuestaProcesoEvaluativo_OpcionPregunta.objects.values_list('preguntaproceso__id', flat=True).filter(encuestaprocesoevaluativo_detallerespuestapregunta__isnull=False, encuestaprocesoevaluativo_detallerespuestapregunta__status=True, preguntaencuesta=preguntaencuesta, status=True).distinct()
                    preguntas = preguntas.exclude(pk__in=opcionencuesta)
                data['preguntas'] =  preguntas
                template = get_template("adm_evaluaciondocentesacreditacion/elegirpregunta.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'extraerpreguntas':
            try:
                listaspregunta = json.loads(request.POST['listaspregunta'])
                listas = []
                for lista in PreguntaProcesoEvaluativo.objects.filter(pk__in=[int(encrypt(lista)) for lista in listaspregunta]):
                    listas.append([encrypt(lista.id), lista.nombre])
                return JsonResponse({"result": "ok", 'listas': listas})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addpreguntaencuesta':
            try:
                f = PreguntaEncuestaForm(request.POST)
                if f.is_valid():
                    encuesta = EncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                    encuestapregunta = EncuestaProcesoEvaluativo_Pregunta(encuestaproceso=encuesta,
                                                                          nombre=f.cleaned_data['nombre'],
                                                                          obligatorio=f.cleaned_data['obligatorio'],
                                                                          activo=f.cleaned_data['activo'])
                    encuestapregunta.save(request)
                    log(u'Adiciono pregunta a encuesta: %s - %s' % (encuestapregunta.nombre, encuestapregunta.id), request, "add")
                    if 'lista_items1' in request.POST:
                        for pregunta in json.loads(request.POST['lista_items1']):
                            preguntaproceso = PreguntaProcesoEvaluativo.objects.get(pk=int(encrypt(pregunta['id'])))
                            opcionpregunta = EncuestaProcesoEvaluativo_OpcionPregunta(preguntaencuesta=encuestapregunta, preguntaproceso=preguntaproceso)
                            opcionpregunta.save(request)
                            log(u'Adiciono opcion pregunta: %s[%s] - pregunta de encuesta: %s' % (opcionpregunta.preguntaencuesta, opcionpregunta.id, opcionpregunta.preguntaproceso),request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'editpreguntaencuesta':
            try:
                f = PreguntaEncuestaForm(request.POST)
                if f.is_valid():
                    encuestapregunta = EncuestaProcesoEvaluativo_Pregunta.objects.get(pk=int(encrypt(request.POST['id'])))
                    encuestapregunta.nombre = f.cleaned_data['nombre']
                    encuestapregunta.obligatorio = f.cleaned_data['obligatorio']
                    encuestapregunta.activo = f.cleaned_data['activo']
                    encuestapregunta.save(request)
                    log(u'Edito pregunta a encuesta: %s - %s' % (encuestapregunta.nombre, encuestapregunta.id), request, "edit")
                    if 'lista_items1' in request.POST:
                        lista_items1 = json.loads(request.POST['lista_items1'])
                        for pregunta in lista_items1:
                            preguntaproceso = PreguntaProcesoEvaluativo.objects.get(pk=int(encrypt(pregunta['id'])))
                            if not EncuestaProcesoEvaluativo_OpcionPregunta.objects.values('id').filter(preguntaencuesta=encuestapregunta, preguntaproceso=preguntaproceso).exists():
                                opcionpregunta = EncuestaProcesoEvaluativo_OpcionPregunta(preguntaencuesta=encuestapregunta, preguntaproceso=preguntaproceso)
                                opcionpregunta.save(request)
                                log(u'Adiciono opcion pregunta: %s[%s] - pregunta de encuesta: %s' % (opcionpregunta.preguntaencuesta, opcionpregunta.id, opcionpregunta.preguntaproceso),request, "add")
                        for eliminaropcionpregunta in EncuestaProcesoEvaluativo_OpcionPregunta.objects.filter(preguntaencuesta=encuestapregunta).exclude(preguntaproceso__id__in=[int(encrypt(pregunta['id'])) for pregunta in lista_items1]):
                            if eliminaropcionpregunta.puede_eliminar_opcionpregunta():
                                log(u'Elimino opcion pregunta: %s[%s] - pregunta de encuesta: %s' % (eliminaropcionpregunta.preguntaencuesta, eliminaropcionpregunta.id, eliminaropcionpregunta.preguntaproceso),request, "del")
                                eliminaropcionpregunta.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'delpreguntaencuesta':
            try:
                preguntaencuesta = EncuestaProcesoEvaluativo_Pregunta.objects.get(pk=int(encrypt(request.POST['id'])))
                if not preguntaencuesta.puede_eliminar_preguntaencuesta():
                    return JsonResponse({"result": "bad", "mensaje": "No puede eliminar pregunta de la encuesta."})
                log(u'Elimino pregunta del proceso evaluativo: %s - %s' % (preguntaencuesta.nombre, preguntaencuesta.id), request, "del")
                preguntaencuesta.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'addcronogramafacultadproceso':
            try:
                if not 'id' in request.POST and request.POST['id']:
                    raise NameError(u"Tipo de proceso no identificado")
                id = int(request.POST['id'])
                detalle = CronogramaProcesoEvaluativoAcreditacion.objects.get(pk=id)
                f = CronogramaCoordinacionForm(request.POST)
                if not f.is_valid():
                    raise NameError(u"Complete todos los campos del formulario")
                cronograma = CronogramaCoordinacion(coordinacion=f.cleaned_data['coordinacion'],
                                                    fechainicio=f.cleaned_data['fechainicio'],
                                                    fechafin=f.cleaned_data['fechafin'],
                                                    activo=f.cleaned_data['activo'])
                cronograma.save(request)
                log(u'Adiciono cronograma coordinación %s' % cronograma, request, "add")
                if detalle.cronogramas().filter(coordinacion=f.cleaned_data['coordinacion']).exists():
                    raise NameError(u"Cronograma de la coordinación ya ha sido planificada")
                detalle.cronograma.add(cronograma)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. %s" % ex})

        elif action == 'editcronogramafacultadproceso':
            try:
                if not 'id' in request.POST and request.POST['id']:
                    raise NameError(u"Tipo de proceso no identificado")
                if not 'idc' in request.POST and request.POST['idc']:
                    raise NameError(u"Cronograma no identificado")
                id = int(request.POST['id'])
                idc = int(request.POST['idc'])
                detalle = CronogramaProcesoEvaluativoAcreditacion.objects.get(pk=id)
                cronograma = CronogramaCoordinacion.objects.get(pk=idc)
                f = CronogramaCoordinacionForm(request.POST)
                if not f.is_valid():
                    raise NameError(u"Complete todos los campos del formulario")
                cronograma.fechainicio = f.cleaned_data['fechainicio']
                cronograma.fechafin = f.cleaned_data['fechafin']
                cronograma.activo = f.cleaned_data['activo']
                cronograma.save(request)
                log(u'Edito cronograma coordinación %s' % cronograma, request, "edit")
                # if detalle.cronogramas().filter(coordinacion=f.cleaned_data['coordinacion']).exists():
                #     raise NameError(u"Cronograma de la coordinación ya ha sido planificada")
                # detalle.cronograma.add(cronograma)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. %s" % ex})

        elif action == 'activeProcesoCronograma':
            try:
                if not 'id' in request.POST and request.POST['id']:
                    raise NameError(u"Tipo de proceso no identificado")
                if not 'value' in request.POST and request.POST['value']:
                    raise NameError(u"Cronograma no identificado")
                id = int(request.POST['id'])
                active = True if int(request.POST['value']) == 1 else False
                detalle = CronogramaProcesoEvaluativoAcreditacion.objects.get(pk=id)
                detalle.activo = active
                detalle.save(request)
                if active:
                    messages.success(request, 'Se activo el cronograma')
                    log(u'Activo cronograma del proceso %s' % detalle, request, "edit")
                else:
                    messages.success(request, 'Se inactivo el cronograma')
                    log(u'Inactivo cronograma del proceso %s' % detalle, request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. %s" % ex})

        elif action == 'deletecronogramafacultadproceso':
            try:
                if not 'id' in request.POST and request.POST['id']:
                    raise NameError(u"Tipo de proceso no identificado")
                if not 'idc' in request.POST and request.POST['idc']:
                    raise NameError(u"Cronograma no identificado")
                id = int(request.POST['id'])
                idc = int(request.POST['idc'])
                detalle = CronogramaProcesoEvaluativoAcreditacion.objects.get(pk=id)
                cronograma = CronogramaCoordinacion.objects.get(pk=idc)
                log(u'Quito cronograma del proceso %s' % detalle, request, "del")
                detalle.cronograma.remove(cronograma)
                detalle.save(request)
                log(u'Elimino cronograma %s' % cronograma, request, "del")
                cronograma.delete()
                messages.success(request, 'Se elimino correctamente el cronograma')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. %s" % ex})

        elif action == 'delcaracteristicasrubrica':
            try:
                caracteristica = RubricaCaracteristica.objects.get(pk=request.POST['id'])
                rubrica = caracteristica.rubrica
                log(u'Elimino característica de rubrica: %s' % proceso, request, "add")
                caracteristica.delete()
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'delcriteriodocencia':
            try:
                criterio = RubricaCriterioDocencia.objects.get(pk=request.POST['id'])
                rubrica = criterio.rubrica
                log(u'Elimino criterio docencia: %s' % rubrica, request, "add")
                criterio.delete()
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'delcriteriovinculacion':
            try:
                criterio = RubricaCriterioVinculacion.objects.get(pk=request.POST['id'])
                rubrica = criterio.rubrica
                log(u'Elimino criterio vinculacion: %s' % rubrica, request, "add")
                criterio.delete()
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'delrubrica':
            try:
                rubrica = Rubrica.objects.get(pk=request.POST['id'])
                log(u'Elimino rubrica: %s' % rubrica, request, "add")
                rubrica.delete()
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'delmodalidadtipo':
            try:
                rubricamodeltipo = RubricaModalidadTipoProfesor.objects.get(pk=request.POST['id'])
                rubricamodeltipo.delete()
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'verdetalledocentescriterios':
            try:
                htmlrequisitos = listadodocentescriterios(request.POST['idcriterio'], request.POST['opc'])
                return htmlrequisitos
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'activacriterioponderacion':
            try:
                idcriterio = int(request.POST['id'])
                tipocriterio = int(request.POST['tipocriterio'])
                idponderativa = int(request.POST['idponderativa'])
                if tipocriterio == 1:
                    if periodo.tablaponderacionconfiguracion_set.filter(tablaponderacion_id=idponderativa, criteriodocenciaperiodo_id=idcriterio, criteriodocenciaperiodo__criterio__tipo=1, status=True).exists():
                        configuraciones = periodo.tablaponderacionconfiguracion_set.get(tablaponderacion_id=idponderativa, criteriodocenciaperiodo_id=idcriterio, criteriodocenciaperiodo__criterio__tipo=1, status=True)
                        configuraciones.delete()
                    else:
                        configuraciones = TablaPonderacionConfiguracion(criteriodocenciaperiodo_id=idcriterio,
                                                                        periodo=periodo,
                                                                        tablaponderacion_id=idponderativa)
                        configuraciones.save(request)
                if tipocriterio == 2:
                    if periodo.tablaponderacionconfiguracion_set.filter(tablaponderacion_id=idponderativa, criterioinvestigacionperiodo_id=idcriterio, status=True).exists():
                        configuraciones = periodo.tablaponderacionconfiguracion_set.get(tablaponderacion_id=idponderativa, criterioinvestigacionperiodo_id=idcriterio, status=True)
                        configuraciones.delete()
                    else:
                        configuraciones = TablaPonderacionConfiguracion(criterioinvestigacionperiodo_id=idcriterio,
                                                                        periodo=periodo,
                                                                        tablaponderacion_id=idponderativa)
                        configuraciones.save(request)
                if tipocriterio == 3:
                    if periodo.tablaponderacionconfiguracion_set.filter(tablaponderacion_id=idponderativa, criteriogestionperiodo_id=idcriterio, status=True).exists():
                        configuraciones = periodo.tablaponderacionconfiguracion_set.get(tablaponderacion_id=idponderativa, criteriogestionperiodo_id=idcriterio, status=True)
                        configuraciones.delete()
                    else:
                        configuraciones = TablaPonderacionConfiguracion(criteriogestionperiodo_id=idcriterio,
                                                                        periodo=periodo,
                                                                        tablaponderacion_id=idponderativa)
                        configuraciones.save(request)
                if tipocriterio == 4:
                    if periodo.tablaponderacionconfiguracion_set.filter(tablaponderacion_id=idponderativa, criteriodocenciaperiodo_id=idcriterio, criteriodocenciaperiodo__criterio__tipo=2, status=True).exists():
                        configuraciones = periodo.tablaponderacionconfiguracion_set.get(tablaponderacion_id=idponderativa, criteriodocenciaperiodo_id=idcriterio, criteriodocenciaperiodo__criterio__tipo=2, status=True)
                        configuraciones.delete()
                    else:
                        configuraciones = TablaPonderacionConfiguracion(criteriodocenciaperiodo_id=idcriterio,
                                                                        periodo=periodo,
                                                                        tablaponderacion_id=idponderativa)
                        configuraciones.save(request)
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'actualizatablaponderativa':
            try:
                listado = []
                iddocentes = request.POST['id']
                idtablaponderativa = request.POST['idtablaponderativa']
                for l in iddocentes.split(','):
                    listado.append(l)
                listadoditributivo = ProfesorDistributivoHoras.objects.filter(pk__in=listado)
                for lis in listadoditributivo:
                    lis.tablaponderacion_id=idtablaponderativa
                    lis.save(request)
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'savemodalidadtipoprofesor':
            try:
                idrubrica = request.POST['idrubrica']
                lista = request.POST['lista'].split(',')
                for listamodtip in request.POST['lista'].split(','):
                    idmodalidad = listamodtip.split('_')
                    if not RubricaModalidadTipoProfesor.objects.filter(rubrica_id=idrubrica, modalidad_id=idmodalidad[0], tipoprofesor_id=idmodalidad[1], status=True):
                        ingresorubmodalidad = RubricaModalidadTipoProfesor(rubrica_id=idrubrica, modalidad_id=idmodalidad[0], tipoprofesor_id=idmodalidad[1])
                        ingresorubmodalidad.save()
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'carrerasdistributivo':
            try:
                lista = []
                facultad = Coordinacion.objects.get(pk=int(request.POST['id']))
                carrera = Carrera.objects.filter(coordinacion=facultad, pk__in=ProfesorDistributivoHoras.objects.values_list('carrera_id').filter(periodo_id=periodo.id, profesor__coordinacion_id=facultad.id,carrera_id__isnull=False, status=True)).order_by('nombre')
                for c in carrera:
                    lista.append([c.id, c.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'tableresumenevadocente':
            try:
                listado = ProfesorDistributivoHoras.objects.values_list('profesor__persona__apellido1', 'profesor__persona__apellido2',
                                                                        'profesor__persona__nombres', 'coordinacion__nombre','carrera__nombre',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_par',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_directivo',
                                                                        'resumenfinalevaluacionacreditacion__promedio_investigacion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_investigacion_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_investigacion_par',
                                                                        'resumenfinalevaluacionacreditacion__promedio_investigacion_directivo',
                                                                        'resumenfinalevaluacionacreditacion__promedio_gestion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_gestion_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_gestion_par',
                                                                        'resumenfinalevaluacionacreditacion__promedio_gestion_directivo',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_docencia_hetero',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_docencia_auto',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_docencia_par',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_docencia_directivo',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_investigacion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_investigacion_auto',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_investigacion_par',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_investigacion_directivo',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_gestion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_gestion_auto',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_gestion_par',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_gestion_directivo',
                                                                        'resumenfinalevaluacionacreditacion__total_tabla_docencia',
                                                                        'horasdocencia',
                                                                        'ponderacion_horas_docencia',
                                                                        'resumenfinalevaluacionacreditacion__resultado_docencia',
                                                                        'resumenfinalevaluacionacreditacion__total_tabla_investigacion',
                                                                        'horasinvestigacion',
                                                                        'ponderacion_horas_investigacion',
                                                                        'resumenfinalevaluacionacreditacion__resultado_investigacion',
                                                                        'resumenfinalevaluacionacreditacion__total_tabla_gestion',
                                                                        'horasgestion',
                                                                        'ponderacion_horas_gestion',
                                                                        'resumenfinalevaluacionacreditacion__resultado_gestion',
                                                                        'resumenfinalevaluacionacreditacion__total_tabla_vinculacion',
                                                                        'horasvinculacion',
                                                                        'ponderacion_horas_vinculacion',
                                                                        'resumenfinalevaluacionacreditacion__resultado_vinculacion',
                                                                        'resumenfinalevaluacionacreditacion__resultado_total',
                                                                        'coordinacion_id',
                                                                        'coordinacion_id',
                                                                        'resumenfinalevaluacionacreditacion__promedio_vinculacion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_vinculacion_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_vinculacion_par',
                                                                        'resumenfinalevaluacionacreditacion__promedio_vinculacion_directivo',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_vinculacion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_vinculacion_auto',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_vinculacion_par',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_vinculacion_directivo',
                                                                        'materia__identificacion',
                                                                        'materia__paralelo',
                                                                        'materia__asignaturamalla__nivelmalla__nombre'). \
                    filter(periodo_id=periodo.id, activoevaldocente=True, profesor__persona__real=True, status=True). \
                    exclude(coordinacion_id=9).order_by('coordinacion__nombre','carrera__nombre','profesor__persona__apellido1', 'profesor__persona__apellido2')

                codigocarrera = request.POST["carr"]
                if codigocarrera == '':
                    codigocarrera=0
                if int(codigocarrera) > 0:
                    listado = listado.filter(carrera_id=int(codigocarrera))
                else:
                    if int(request.POST["idfacu"]) > 0:
                        listado = listado.filter(coordinacion_id=int(request.POST["idfacu"]))

                data['distributivos'] = listado
                data['clasificacion'] = periodo.clasificacion
                template = get_template("adm_evaluaciondocentesacreditacion/tableresumenevadocente.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "listado": json_content})
            except Exception as ex:
                pass

        elif action == 'tablepromedioevadocente':
            try:

                listado = ProfesorDistributivoHoras.objects.values_list('profesor__persona__apellido1', 'profesor__persona__apellido2',
                                                                        'profesor__persona__nombres', 'coordinacion__nombre', 'carrera__nombre',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_par',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_directivo',
                                                                        'resumenfinalevaluacionacreditacion__promedio_investigacion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_investigacion_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_investigacion_par',
                                                                        'resumenfinalevaluacionacreditacion__promedio_investigacion_directivo',
                                                                        'resumenfinalevaluacionacreditacion__promedio_gestion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_gestion_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_gestion_par',
                                                                        'resumenfinalevaluacionacreditacion__promedio_gestion_directivo',
                                                                        'resumenfinalevaluacionacreditacion__resultado_total',
                                                                        'coordinacion_id',
                                                                        'coordinacion_id',
                                                                        'resumenfinalevaluacionacreditacion__promedio_vinculacion_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_vinculacion_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_vinculacion_par',
                                                                        'resumenfinalevaluacionacreditacion__promedio_vinculacion_directivo',
                                                                        'nivelcategoria__nombre'). \
                    filter(periodo_id=periodo.id, activoevaldocente=True, profesor__persona__real=True, status=True). \
                    exclude(coordinacion_id=9).order_by('coordinacion__nombre','carrera__nombre','profesor__persona__apellido1', 'profesor__persona__apellido2')

                codigocarrera = request.POST["carr"]
                if codigocarrera == '':
                    codigocarrera=0
                if int(codigocarrera) > 0:
                    listado = listado.filter(carrera_id=int(codigocarrera))
                else:
                    if int(request.POST["idfacu"]) > 0:
                        listado = listado.filter(coordinacion_id=int(request.POST["idfacu"]))

                data['distributivos'] = listado
                template = get_template("adm_evaluaciondocentesacreditacion/tablepromedioevadocente.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "listado": json_content})
            except Exception as ex:
                pass

        elif action == 'tieneevaldocente':
            try:
                with transaction.atomic():
                    distributivo = ProfesorDistributivoHoras.objects.get(pk=int(request.POST['id']))
                    if distributivo.activoevaldocente:
                        distributivo.activoevaldocente = False
                    else:
                        distributivo.activoevaldocente = True
                    distributivo.save(request)
                    log(u'cambio estado eval docente en distributivo: %s' % distributivo, request, "estadoactivar")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addeval':
            try:
                f = ParesInvestigacionVinculacionForm(request.POST)
                id_resp = request.POST['persona']
                if not id_resp:
                    raise NameError("El campo persona es obligatorio!")
                f.edit(id_resp)
                if not f.is_valid():
                    raise NameError(f"{[{k:v[0]} for k,v in f.errors.items()]}")
                if f.is_valid():
                    if ParesInvestigacionVinculacion.objects.values("id").filter(proceso=proceso, tipo=f.cleaned_data['tipo']).exists():
                        raise NameError("Registro ya existe!")
                    parinvestigador = ParesInvestigacionVinculacion(persona=f.cleaned_data['persona'],
                                                                    proceso=proceso,
                                                                    tipo=f.cleaned_data['tipo'],
                                                                    activo=f.cleaned_data['activo'])
                    parinvestigador.save(request)
                    log(u'Adiciono evaluador docente: %s' % parinvestigador, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editeval':
            try:
                f = ParesInvestigacionVinculacionForm(request.POST)
                id = request.POST['id']
                parinvestigador = ParesInvestigacionVinculacion.objects.get(id=id)
                id_resp = request.POST['persona']
                if not id_resp:
                    raise NameError("El campo persona es obligatorio!")
                f.edit(id_resp)
                if not f.is_valid():
                    raise NameError(f"{[{k:v[0]} for k,v in f.errors.items()]}")
                if f.is_valid():
                    parinvestigador.persona=f.cleaned_data['persona']
                    parinvestigador.tipo=f.cleaned_data['tipo']
                    parinvestigador.activo=f.cleaned_data['activo']
                    parinvestigador.save(request)
                    log(u'Edito evaluador docente: %s' % parinvestigador, request, "edit")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteevaluador':
            try:
                id = int(encrypt(request.POST['id']))
                reg = ParesInvestigacionVinculacion.objects.get(status=True, id=id)
                reg.delete()
                log(f"Eliminó Evaluador: {reg}", request, 'del')
                res_json = {"error": False}
            except Exception as ex:
                err_ = "{}({})".format(ex, sys.exc_info()[-1].tb_lineno)
                transaction.set_rollback(True)
                res_json = {'error':True, "mensaje":err_}
            return JsonResponse(res_json)

        if action == 'tablaponderativa':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['id'])
                f = PonderacionProfesorForm(request.POST)
                if f.is_valid():
                    tienetablaponderacion = True if distributivo.tablaponderacion else False
                    distributivo.tablaponderacion = f.cleaned_data['ponderacion']
                    distributivo.save(request)
                    distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                    log(u'Modifico tabla de ponderacion del profesor: %s  - periodo: %s' % (distributivo.profesor, distributivo.periodo), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletepreguntac':
            try:
                ePregunta = PreguntaCaracteristicaEvaluacionAcreditacion.objects.get(pk=int(request.POST['id']))
                ePregunta.delete()
                log(u'Eliminó la pregunta: %s' % ePregunta, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Pregunta eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        if action == 'notificardirectivos':
            try:
                if proceso.dir_sin_realizar():
                    for detalle in proceso.dir_sin_realizar():
                        titulo = 'EVALUACIÓN DE DIRECTIVOS PENDIENTE'
                        cuerpo = f'Saludos, el docente a evaluar es: Msc. {detalle.evaluado.persona}, módulo: {detalle.materia.asignatura}, paralelo {detalle.materia.paralelo}, cohorte {detalle.materia.nivel.periodo}. La evaluación estará activa desde {proceso.instrumentodirectivoinicio} hasta {proceso.instrumentodirectivofin}. Por favor, realizarla en el tiempo acordado.'
                        notificacion(titulo, cuerpo,
                                      detalle.evaluador, None, '/pro_personaevaluacion', detalle.evaluador.pk, 1, 'sga',
                                      detalle.evaluador, None)
                        log(u'Notificó evaluación de directivos: %s' % detalle.evaluador, request, "edit")

                return JsonResponse({"result": 'ok', "mensaje": u"Notificación ejecutada"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        elif action == 'planificarfechassatisfaccion':
            try:
                idm = int(request.POST['listascodigos'])
                profesormateria = ProfesorMateria.objects.filter(status=True, materia_id=idm, tipoprofesor_id=11).first()
                if not InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                             profesormateria=profesormateria,
                                                                             encuesta_id=int(request.POST['ide'])).exists():
                    eInscripcion = InscripcionEncuestaSatisfaccionDocente(encuesta_id=int(request.POST['ide']),
                                                                          profesormateria=profesormateria,
                                                                          inicio=request.POST['id_fini'],
                                                                          fin=request.POST['id_ffin'])
                    eInscripcion.save(request)

                    log(u'Adicionó encuesta de satisfacción: %s' % eInscripcion, request, "add")
                else:
                    eInscripcion = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True,
                                                                                         profesormateria=profesormateria,
                                                                                         encuesta_id=int(request.POST['ide'])).first()
                    eInscripcion.inicio = request.POST['id_fini']
                    eInscripcion.fin = request.POST['id_ffin']
                    eInscripcion.save(request)
                    log(u'Actualizó fechas de encuestado de satisfacción: %s' % eInscripcion, request, "add")

                titulo = 'ENCUESTA DE SATISFACCIÓN'
                cuerpo = f'Saludos, Msc. {profesormateria.profesor.persona}, módulo: {profesormateria.materia.asignatura}, paralelo {profesormateria.materia.paralelo}, cohorte {profesormateria.materia.nivel.periodo}. La ENCUESTA estará activa desde {eInscripcion.inicio} hasta {eInscripcion.fin}. Por favor, realizarla en el tiempo acordado.'
                notificacion(titulo, cuerpo,
                             profesormateria.profesor.persona, None, '/pro_autoevaluacion',
                             profesormateria.profesor.persona.pk, 1, 'sga',
                             profesormateria.profesor.persona, None)
                log(u'Notificó encuesta de satisfacción: %s' % profesormateria.profesor.persona, request, "edit")
                return JsonResponse({"result": "ok", 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'tablaresumenposgrado':
            try:
                data['title'] = u'Resumen de evaluación docente de Posgrado'
                # data['ePeriodo'] = ePeriodo = Periodo.objects.filter(status=True, pk=int(request.GET['idperiodo']))
                data['eProceso'] = periodo.proceso_evaluativoacreditacion()
                eProfesores = ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=periodo, tipoprofesor__id__in=[11])

                iddis = []
                c = 1
                for eProfesor in eProfesores:
                    frecuencia_preguntas_hetero(eProfesor)
                    frecuencia_preguntas_auto(eProfesor)
                    frecuencia_preguntas_dir(eProfesor)

                    distributivo = eProfesor.profesor.distributivohoraseval(periodo)
                    if distributivo:
                        resumen = distributivo.resumen_evaluacion_acreditacion()
                        actualizar_resumen(resumen, eProfesor.materia.id)
                        iddis.append(distributivo.id)

                    print(f'{c}/{eProfesores.count()}')
                    c += 1

                listado = ProfesorDistributivoHoras.objects.values_list('profesor__persona__apellido1', 'profesor__persona__apellido2',
                                                                        'profesor__persona__nombres', 'carrera__nombre',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_hetero',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_auto',
                                                                        'resumenfinalevaluacionacreditacion__promedio_docencia_directivo',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_docencia_hetero',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_docencia_auto',
                                                                        'resumenfinalevaluacionacreditacion__valor_tabla_docencia_directivo',
                                                                        'horasdocencia',
                                                                        'resumenfinalevaluacionacreditacion__resultado_docencia',
                                                                        'resumenfinalevaluacionacreditacion__resultado_total',
                                                                        'materia__asignaturamalla__asignatura__nombre',
                                                                        'materia__identificacion',
                                                                        'materia__paralelo',
                                                                        'materia__asignaturamalla__nivelmalla__nombre',
                                                                        'materia__inicio',
                                                                        'materia__fin',
                                                                        'materia__cerrado'). \
                    filter(periodo_id=periodo.id, status=True, id__in=iddis)
                data['distributivos'] = listado
                template = get_template("adm_evaluaciondocentesacreditacion/tablaresumenposgrado.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "listado": json_content})
            except Exception as ex:
                pass

        elif action == 'delcriteriogestion':
            try:
                criterio = RubricaCriterioGestion.objects.get(pk=request.POST['id'])
                rubrica = criterio.rubrica
                log(u'Elimino criterio gestion: %s' % rubrica, request, "add")
                criterio.delete()
                return JsonResponse({'error': False, "mensaje": u"Se guardo correctamente."})
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'descargarlistado':
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
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_inscritos' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"CEDULA", 4000),
                        (u"NOMBRES", 15000),
                        (u"COORDINACION", 10000),
                        (u"CARRERA", 10000),
                        (u"CATEGORIA", 10000),
                        (u"CARGO", 10000),
                        (u"EVALUADOR", 15000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, detalledistributivo__evaluadirectivo=True, profesor__persona__real=True).exclude(coordinacion_id=9).distinct().order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        campo2 = lista.profesor.persona.cedula
                        campo3 = lista.profesor.persona.apellido1 + ' ' + lista.profesor.persona.apellido2 + ' ' + lista.profesor.persona.nombres
                        campo4 = ''
                        if lista.coordinacion:
                            campo4 = lista.coordinacion.nombre
                        campo5 = ''
                        if lista.carrera:
                            campo5 = lista.carrera.nombre
                        campo6 = ''
                        if lista.profesor.categoria:
                            campo6 = lista.profesor.categoria.nombre
                        campo7 = ''
                        if lista.profesor.cargo:
                            campo7 = lista.profesor.cargo.nombre
                        campo8 = ''
                        if proceso.detalleinstrumentoevaluaciondirectivoacreditacion_set.filter(evaluado=lista.profesor):
                            campo8 = proceso.detalleinstrumentoevaluaciondirectivoacreditacion_set.filter(evaluado=lista.profesor)[0].evaluador

                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8.__str__(), font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'excellfaltantesdirectivos':
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
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=faltantes_directivos' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"EVALUADO", 15000),
                        (u"EMAIL EVALUADOR", 8000),
                        (u"EVALUADOR", 15000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = proceso.dir_sin_realizar()
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        campo2 = lista.evaluado.persona.nombre_completo_inverso().__str__()
                        campo3 = lista.evaluador.emailinst
                        campo4 = lista.evaluador.nombre_completo_inverso().__str__()

                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'excellfaltantespares':
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
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=faltantes_pares' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"EVALUADO", 15000),
                        (u"EMAIL EVALUADOR", 8000),
                        (u"EVALUADOR", 15000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = proceso.par_sin_realizar()
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        campo2 = lista.evaluado.persona.nombre_completo_inverso().__str__()
                        campo3 = lista.evaluador.emailinst
                        campo4 = lista.evaluador.nombre_completo_inverso().__str__()

                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'addponderacion':
                try:
                    data['title'] = u'Adicionar tabla ponderación'
                    data['form'] = PonderacionAcreditacionForm()
                    return render(request, "adm_evaluaciondocentesacreditacion/addponderacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editponderacion':
                try:
                    data['title'] = u'Editar tabla ponderación'
                    data['tabla'] = tabla = TablaPonderacionInstrumento.objects.get(pk=request.GET['id'])
                    data['form'] = PonderacionAcreditacionForm(initial={'nombre': tabla.nombre,
                                                                        'docencia_instrumentohetero': tabla.docencia_instrumentohetero,
                                                                        'docencia_instrumentoauto': tabla.docencia_instrumentoauto,
                                                                        'docencia_instrumentopar': tabla.docencia_instrumentopar,
                                                                        'docencia_instrumentodirectivo': tabla.docencia_instrumentodirectivo,
                                                                        'investigacion_instrumentohetero': tabla.investigacion_instrumentohetero,
                                                                        'investigacion_instrumentoauto': tabla.investigacion_instrumentoauto,
                                                                        'investigacion_instrumentopar': tabla.investigacion_instrumentopar,
                                                                        'investigacion_instrumentodirectivo': tabla.investigacion_instrumentodirectivo,
                                                                        'gestion_instrumentohetero': tabla.gestion_instrumentohetero,
                                                                        'gestion_instrumentoauto': tabla.gestion_instrumentoauto,
                                                                        'gestion_instrumentopar': tabla.gestion_instrumentopar,
                                                                        'gestion_instrumentodirectivo': tabla.gestion_instrumentodirectivo,
                                                                        'vincu_instrumentohetero': tabla.vincu_instrumentohetero,
                                                                        'vincu_instrumentoauto': tabla.vincu_instrumentoauto,
                                                                        'vincu_instrumentopar': tabla.vincu_instrumentopar,
                                                                        'vincu_instrumentodirectivo': tabla.vincu_instrumentodirectivo
                                                                        # 'docencia_instrumentocomision': tabla.docencia_instrumentocomision,
                                                                        # 'investigacion_instrumentocomision': tabla.investigacion_instrumentocomision,
                                                                        # 'gestion_instrumentocomision': tabla.gestion_instrumentocomision,
                                                                        # 'vincu_instrumentocomision': tabla.vincu_instrumentocomision
                                                                        })
                    return render(request, "adm_evaluaciondocentesacreditacion/editponderacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delponderacion':
                try:
                    data['title'] = u'Eliminar tabla ponderación'
                    data['tabla'] = tabla = TablaPonderacionInstrumento.objects.get(pk=request.GET['id'])
                    return render(request, "adm_evaluaciondocentesacreditacion/delponderacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'activacioninstrumento':
                try:
                    data['title'] = u'Activacion de instrumento'
                    data['tipo'] = tipo = int(request.GET['id'])
                    if tipo == 1:
                        fi = proceso.instrumentoheteroinicio
                        ff = proceso.instrumentoheterofin
                        activo = proceso.instrumentoheteroactivo
                    elif tipo == 2:
                        fi = proceso.instrumentoautoinicio
                        ff = proceso.instrumentoautofin
                        activo = proceso.instrumentoautoactivo
                    elif tipo == 3:
                        fi = proceso.instrumentodirectivoinicio
                        ff = proceso.instrumentodirectivofin
                        activo = proceso.instrumentodirectivoactivo
                    elif tipo == 4:
                        fi = proceso.instrumentoparinicio
                        ff = proceso.instrumentoparfin
                        activo = proceso.instrumentoparactivo
                    elif tipo == 5:
                        fi = proceso.instrumentorevisioninicio
                        ff = proceso.instrumentorevisionfin
                        activo = proceso.instrumentorevisionactivo
                    data['form'] = ActivacionInstrumentoEvaluacionAcreditacionForm(initial={'desde': fi,
                                                                                            'hasta': ff,
                                                                                            'activo': activo})
                    return render(request, "adm_evaluaciondocentesacreditacion/activacioninstrumento.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignarevaluaciondirectivo':
                try:
                    data['title'] = u'Selección de directivos para evaluación de profesores'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        url_vars += f'&s={search}'
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listadodistributivo = ProfesorDistributivoHoras.objects.filter(Q(profesor__persona__nombres__icontains=search) |
                                                                                           Q(profesor__persona__apellido1__icontains=search) |
                                                                                           Q(profesor__persona__apellido2__icontains=search) |
                                                                                           Q(profesor__persona__cedula__icontains=search) |
                                                                                           Q(profesor__persona__pasaporte__icontains=search),
                                                                                           profesor__persona__real=True ,periodo=proceso.periodo, detalledistributivo__evaluadirectivo=True).distinct(). \
                                order_by('coordinacion__nombre','profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')
                        else:
                            listadodistributivo = ProfesorDistributivoHoras.objects.filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                                                           Q(profesor__persona__apellido2__icontains=ss[1]),
                                                                                           profesor__persona__real=True ,periodo=proceso.periodo, detalledistributivo__evaluadirectivo=True).distinct(). \
                                order_by('coordinacion__nombre','profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')

                    else:
                        listadodistributivo = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, detalledistributivo__evaluadirectivo=True, profesor__persona__real=True).distinct().order_by('coordinacion__nombre','profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')
                    numerofilas = 15
                    paging = MiPaginador(listadodistributivo, numerofilas)
                    p = 1
                    url_vars += '&action={}'.format(action)
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
                    data['distributivoshora'] = page.object_list
                    # data['distributivoshora'] = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, detalledistributivo__evaluadirectivo=True).distinct().order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')
                    data['directorescarrera'] = CoordinadorCarrera.objects.filter(periodo=periodo, status=True, tipo=3).order_by('persona__apellido1', 'persona__apellido1', 'persona__nombres').distinct('persona__apellido1', 'persona__apellido1', 'persona__nombres')
                    data['persocoor'] = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, tipo=1)
                    # codigo denominacion puesto 373 Rector --->>>>>
                    data['vicerectorado'] = DistributivoPersona.objects.filter((Q(denominacionpuesto__id=796) | Q(denominacionpuesto__id=115) | Q(denominacionpuesto__id=795)| Q(denominacionpuesto__id=373)| Q(denominacionpuesto__id=113)| Q(denominacionpuesto__id=263)), Q(estadopuesto__id=PUESTO_ACTIVO_ID))
                    data['vinculacion'] = DistributivoPersona.objects.filter(denominacionpuesto__id=797, status=True)
                    data['listadoevaluadores_vin_inv'] = proceso.paresinvestigacionvinculacion_set.filter(status=True)
                    data['proceso_modificable'] = not proceso.instrumentodirectivoactivo
                    data['form2'] = FechaEvaluacionAcreditacionForm()
                    return render(request, "adm_evaluaciondocentesacreditacion/asignarevaluaciondirectivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'asignarevaluaciondirectivopos':
                try:
                    data['title'] = u'Selección de directivos para evaluación de profesores'
                    search = request.GET.get('s', '')
                    url_vars = '&action=asignarevaluaciondirectivopos'
                    filtros = Q(status=True, materia__nivel__periodo=periodo, tipoprofesor__id__in=[11])

                    if search:
                        data['search'] = search
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtros = filtros & (Q(profesor__persona__apellido1__icontains=search) |
                                                     Q(profesor__persona__apellido2__icontains=search) |
                                                     Q(profesor__persona__nombres__icontains=search) |
                                                     Q(profesor__persona__cedula__icontains=search)|
                                                     Q(materia__asignatura__nombre__icontains=search))
                            url_vars += "&s={}".format(search)
                        elif len(ss) == 2:
                            filtros = filtros & (Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                     Q(profesor__persona__apellido2__icontains=ss[1]))
                            url_vars += "&s={}".format(ss)
                        else:
                            filtros = filtros & (Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                Q(profesor__persona__apellido2__icontains=ss[1]) &
                                               Q(profesor__persona__nombres__icontains=ss[2]))
                            url_vars += "&s={}".format(ss)

                    eProfesoresMaterias = ProfesorMateria.objects.filter(filtros).order_by('profesor__id', 'materia__paralelo', 'materia__cerrado')
                    eCarrera = eProfesoresMaterias[0].materia.asignaturamalla.malla.carrera
                    lis = []
                    if CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=eCarrera).exists():
                        coodinador = CohorteMaestria.objects.filter(status=True, maestriaadmision__carrera=eCarrera).order_by('-id').first().coordinador
                        lis.append(coodinador.id)
                    if eCarrera.escuelaposgrado:
                        if eCarrera.escuelaposgrado.id == 1:
                            lista = Persona.objects.filter(pk=Departamento.objects.get(pk=216).responsable.id)
                        elif eCarrera.escuelaposgrado.id == 2:
                            lista = Persona.objects.filter(pk=Departamento.objects.get(pk=215).responsable.id)
                        elif eCarrera.escuelaposgrado.id == 3:
                            lista = Persona.objects.filter(pk=Departamento.objects.get(pk=163).responsable.id)
                        else:
                            lista = Persona.objects.filter(id__in=Departamento.objects.filter(id__in=[163, 215, 216]).values_list('responsable__id', flat=True))
                    else:
                        lista = Persona.objects.filter(id__in=Departamento.objects.filter(id__in=[163, 215, 216]).values_list('responsable__id', flat=True))

                    for li in lista:
                        lis.append(li.id)

                    numerofilas = 20
                    paging = MiPaginador(eProfesoresMaterias, numerofilas)
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
                    # data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['eProfesoresMaterias'] = page.object_list
                    # data['distributivoshora'] = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, detalledistributivo__evaluadirectivo=True).distinct().order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')
                    data['directoresescuela'] = Persona.objects.filter(id__in=lis).order_by('apellido1', 'apellido2', 'nombres').distinct('apellido1', 'apellido2', 'nombres')
                    # data['directorescarrera'] = CoordinadorCarrera.objects.filter(periodo=periodo, status=True, tipo=3).order_by('persona__apellido1', 'persona__apellido1', 'persona__nombres').distinct('persona__apellido1', 'persona__apellido1', 'persona__nombres')
                    # data['persocoor'] = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, tipo=1)
                    # data['vicerectorado'] = DistributivoPersona.objects.filter((Q(denominacionpuesto__id=796) | Q(denominacionpuesto__id=115)), Q(estadopuesto__id=PUESTO_ACTIVO_ID))
                    # data['vinculacion'] = DistributivoPersona.objects.filter(denominacionpuesto__id=797, status=True)
                    data['listadoevaluadores_vin_inv'] = proceso.paresinvestigacionvinculacion_set.filter(status=True)
                    data['proceso_modificable'] = not proceso.instrumentodirectivoactivo
                    data['form2'] = FechaEvaluacionAcreditacionForm()
                    return render(request, "adm_evaluaciondocentesacreditacion/asignarevaluaciondirectivopos.html", data)
                except Exception as ex:
                    pass

            elif action == 'caracteristicas':
                try:
                    data['title'] = u'Caracteristicas de evaluación de profesores'
                    data['caracteristicas'] = CaracteristicaEvaluacionAcreditacion.objects.all()
                    return render(request, "adm_evaluaciondocentesacreditacion/caracteristicas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcaracteristica':
                try:
                    data['title'] = u'Adicionar caracteristica'
                    data['form'] = CaracteristicaAcreditacionForm()
                    return render(request, "adm_evaluaciondocentesacreditacion/addcaracteristica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcaracteristica':
                try:
                    data['title'] = u'Editar caracteristica'
                    data['caracteristica'] = caracteristica = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.GET['id'])
                    data['form'] = CaracteristicaAcreditacionForm(initial={'nombre': caracteristica.nombre,'intencionalidad':caracteristica.intencionalidad})
                    return render(request, "adm_evaluaciondocentesacreditacion/editcaracteristica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcaracteristica':
                try:
                    data['title'] = u'Eliminar caracteristica'
                    data['caracteristica'] = caracteristica = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_evaluaciondocentesacreditacion/delcaracteristica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delpregunta':
                try:
                    preguntacaracteristica = PreguntaCaracteristicaEvaluacionAcreditacion.objects.get(pk=request.GET['id'])
                    caracteristica = preguntacaracteristica.caracteristica
                    log(u'Elimino pregunta de caracteristica de evaluación: %s' % caracteristica, request, "del")
                    preguntacaracteristica.delete()
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion?action=preguntas&id=' + str(caracteristica.id))
                except Exception as ex:
                    pass

            elif action == 'preguntas':
                try:
                    data['title'] = u'Preguntas de evaluación de profesores'
                    data['caracteristica'] = caracteristica = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.GET['id'])
                    data['preguntascaracteristica'] = caracteristica.mis_preguntas()
                    data['ePeriodo'] = periodo
                    return render(request, "adm_evaluaciondocentesacreditacion/preguntas.html", data)
                except Exception as ex:
                    pass

            elif action == 'editevidenciacolor':
                try:
                    data['title'] = u'Editar evidencia de la pregunta'
                    data['action'] = 'editevidenciacolor'
                    data['id'] = request.GET['id']
                    ePregunta = PreguntaCaracteristicaEvaluacionAcreditacion.objects.get(pk=int(request.GET['id']))
                    form = EvidenciaColorPreguntaEncuestaForm(initial={'pregunta': ePregunta.pregunta,
                                                                       'tipo': ePregunta.get_tipocolor_display() if ePregunta.tipocolor else ''})
                    data['form2'] = form
                    template = get_template("adm_evaluaciondocentesacreditacion/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'addpregunta':
                try:
                    data['title'] = u'Adicionar pregunta'
                    data['caracteristica'] = caracteristica = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.GET['id'])
                    data['preguntas'] = TextoPreguntaAcreditacion.objects.all()
                    return render(request, "adm_evaluaciondocentesacreditacion/addpregunta.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpreguntanueva':
                try:
                    data['title'] = u'Adicionar nueva pregunta'
                    data['caracteristica'] = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.GET['id'])
                    data['form'] = PreguntaAcreditacionForm()
                    return render(request, "adm_evaluaciondocentesacreditacion/addpreguntanueva.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpreguntanueva':
                try:
                    data['title'] = u'Editar pregunta'
                    data['caracteristica'] = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.GET['idc'])
                    data['pregunta'] = pregunta = TextoPreguntaAcreditacion.objects.get(pk=request.GET['id'])
                    data['form'] = PreguntaAcreditacionForm(initial={'texto': pregunta.nombre})
                    return render(request, "adm_evaluaciondocentesacreditacion/editpreguntanueva.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadocoordinaciones':
                try:
                    data['title'] = u'Listado Coordinaciones'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['rubricacoordinaciones'] = listacoordinaciones = RubricaCoordinacion.objects.filter(rubrica=rubrica,status=True)
                    listacoordinaciones = listacoordinaciones.values_list('coordinacion')
                    data['listadocoordinaciones'] = Coordinacion.objects.filter(status=True).exclude(pk__in=listacoordinaciones).order_by('nombre')
                    return render(request, "adm_evaluaciondocentesacreditacion/listadocoordinaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'rubricas':
                try:
                    data['title'] = u'Rubrica de evaluación de profesores'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    data['rubricalistadomodalidades'] = rubricalistadomodalidades = RubricaModalidadTipoProfesor.objects.values_list('modalidad_id', 'modalidad__nombre', 'tipoprofesor_id', 'tipoprofesor__nombre', 'modalidad__abreviatura', 'tipoprofesor__abreviatura').filter(rubrica__proceso__periodo_id=periodo.id, rubrica__para_hetero=True, status=True).order_by('modalidad_id', 'tipoprofesor_id').distinct()
                    data['totalrubmodal'] = rubricalistadomodalidades.count() + 12
                    data['registrorubricalistadomodalidades'] = RubricaModalidadTipoProfesor.objects.values_list('rubrica_id','modalidad_id', 'modalidad__abreviatura', 'tipoprofesor_id', 'tipoprofesor__abreviatura', 'modalidad__abreviatura', 'tipoprofesor__abreviatura').filter(rubrica__proceso__periodo_id=periodo.id, status=True).distinct()
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        url_vars += '&s={}'.format(search)
                        listadorubricas = proceso.rubrica_set.filter(Q(nombre__icontains=search) | Q(descripcion__icontains=search), status=True).order_by('tipo_criterio', 'tiporubrica')
                    else:
                        listadorubricas = proceso.rubrica_set.filter(status=True).order_by('tipo_criterio', 'tiporubrica')
                    numerofilas = 15
                    paging = MiPaginador(listadorubricas, numerofilas)
                    p = 1
                    url_vars += '&action={}'.format(action)
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
                    ids_rubrica_pagina = [rubrica.id for rubrica in page.object_list]
                    listadorubricas = Rubrica.objects.filter(id__in=ids_rubrica_pagina).\
                        annotate(tieneevaluaciones=Exists(RespuestaRubrica.objects.filter(status=True, rubrica_id=OuterRef('id')))).\
                        annotate(totalcaracteristica=Count('rubricacaracteristica', distinct=True)).\
                        annotate(totalpreguntas=Count('rubricapreguntas', distinct=True)).\
                        annotate(totalcriteriodocencia=Count('rubricacriteriodocencia', rubricacriteriodocencia__criterio__criterio__tipo=1, distinct=True)).\
                        annotate(totalcriterioinvestigacion=Count('rubricacriterioinvestigacion', distinct=True)).\
                        annotate(totalcriteriogestion=Count('rubricacriteriogestion', distinct=True)).\
                        annotate(totalcriteriovinculacion=Count('rubricacriteriovinculacion', rubricacriteriodocencia__criterio__criterio__tipo=2, distinct=True))
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['rubricas'] = listadorubricas
                    return render(request, "adm_evaluaciondocentesacreditacion/rubricas.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadistributivo':
                try:
                    data['title'] = u'Listado docentes distributivo'
                    search, url_vars = request.GET.get('s', ''), f'&action={action}'
                    listado = periodo.profesordistributivohoras_set.filter(profesor__persona__real=True, status=True).exclude(coordinacion_id=9).order_by('profesor__persona_apellido1', 'profesor__persona_apellido2', 'profesor__persona_nombres')
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            listado = listado.filter(Q(profesor__persona__nombres__icontains=search) |
                                                     Q(profesor__persona__apellido1__icontains=search) |
                                                     Q(profesor__persona__apellido2__icontains=search) |
                                                     Q(profesor__persona__cedula__icontains=search) |
                                                     Q(profesor__persona__pasaporte__icontains=search))
                        else:
                            listado = listado.filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                     Q(profesor__persona__apellido2__icontains=ss[1]))
                    numerofilas = 20
                    paging = MiPaginador(listado, numerofilas)
                    p = 1
                    url_vars += "&action=listadistributivo"
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
                    data['page'] = page
                    data['numeropagina'] = p
                    data['numerofilasguiente'] = numerofilasguiente
                    data["url_vars"] = url_vars
                    data['search'] = search if search else ""
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['distributivo'] = page.object_list
                    return render(request, "adm_evaluaciondocentesacreditacion/listadistributivo.html", data)
                except Exception as ex:
                    pass

            if action == 'tablaponderativa':
                try:
                    data['title'] = u'Cambio de tabla ponderativa'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = distributivo = profesor.distributivohoraseval(periodo)
                    data['form'] = PonderacionProfesorForm(initial={'ponderacion': distributivo.tablaponderacion})
                    return render(request, "adm_evaluaciondocentesacreditacion/tablaponderativa.html", data)
                except Exception as ex:
                    pass

            if action == 'listadistributivoxls':
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
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=docentes' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"APELLIDOS Y NOMBRES", 15000),
                        (u"EVALUACIÓN DOCENTE", 8000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = periodo.profesordistributivohoras_set.filter(profesor__persona__real=True, status=True).exclude(coordinacion_id=9).order_by('profesor__persona_apellido1', 'profesor__persona_apellido2', 'profesor__persona_nombres')
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        campo2 = lista.profesor.persona.nombre_completo_inverso().__str__()
                        campo3 = 'NO'
                        if lista.activoevaldocente:
                            campo3 = 'SI'
                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'tablasponderativas':
                try:
                    data['title'] = u'Tablas de ponderación'
                    tablaponderacion = TablaPonderacionInstrumento.objects.all()
                    clasificacion = periodo.clasificacion
                    if clasificacion == 2:
                        tablaponderacion = tablaponderacion.filter(clasificacion=clasificacion)
                    data['ponderaciones'] = tablaponderacion
                    data['periodo'] = periodo
                    return render(request, "adm_evaluaciondocentesacreditacion/tablasponderativas.html", data)
                except Exception as ex:
                    pass

            elif action == 'configurarcriterios':
                try:
                    data['title'] = u'Criterios y actividades del distributivo'
                    lista = []
                    # data['tablaponderativa'] = tablaponderativa = TablaPonderacionInstrumento.objects.get(pk=int(encrypt(request.GET['idtablaponderativa'])))
                    # data['configuraciones'] = configuraciones = tablaponderativa.tablaponderacionconfiguracion_set.filter(periodo=periodo, status=True).order_by('criteriodocenciaperiodo__criterio__tipo', 'criteriodocenciaperiodo_id', 'criterioinvestigacionperiodo', 'criteriogestionperiodo_id')
                    # listadodocencia = configuraciones.values_list('criteriodocenciaperiodo_id', flat=True).filter(criteriodocenciaperiodo_id__isnull=False).order_by('criteriodocenciaperiodo_id')
                    # listadoinvestigacion = configuraciones.values_list('criterioinvestigacionperiodo_id', flat=True).filter(criterioinvestigacionperiodo_id__isnull=False).order_by('criterioinvestigacionperiodo_id')
                    # listadogestion = configuraciones.values_list('criteriogestionperiodo_id', flat=True).filter(criteriogestionperiodo_id__isnull=False).order_by('criteriogestionperiodo_id')
                    #
                    # lst_doc = [str(a) for a in listadodocencia]
                    # listacriteriosdocenciavincu = ",".join(lst_doc)
                    #
                    # lst_inv = [str(a) for a in listadoinvestigacion]
                    # listacriteriosinvestigacion = ",".join(lst_inv)
                    #
                    # lst_ges = [str(a) for a in listadogestion]
                    # listacriteriosgestion = ",".join(lst_ges)

                    cursor = connection.cursor()
                    sql = """
                    SELECT COUNT(profesor_id) AS totaldocentes, criteriodocencia, 
                    criterioinvestigacion,criteriogestion,criteriovinculacion, 
                    array_to_string(array_agg(id),',') AS iddistributivo,
                    array_to_string(array_agg(tablaponderacion_id),',') AS tablaponderacion_id 
                    FROM (SELECT dis.id,dis.tablaponderacion_id,dis.profesor_id,per.apellido1,per.apellido2,per.nombres,
                    (SELECT array_to_string(array_agg('* ' || cridoc.nombre 
                    order by cridoc.id),'<br>') FROM sga_criteriodocenciaperiodo cripe,
                    sga_criteriodocencia cridoc,sga_detalledistributivo deta
                    WHERE deta.criteriodocenciaperiodo_id=cripe.id
                    and cripe.criterio_id=cridoc.id
                    AND cridoc.tipo=1
                    AND deta.distributivo_id=dis.id) AS criteriodocencia,
                    (SELECT array_to_string(array_agg('* ' || cridoc.nombre 
                    order by cridoc.id),'<br>') FROM sga_criterioinvestigacionperiodo cripe,
                    sga_criterioinvestigacion cridoc,sga_detalledistributivo deta
                    WHERE deta.criterioinvestigacionperiodo_id=cripe.id
                    and cripe.criterio_id=cridoc.id
                    AND deta.distributivo_id=dis.id) AS criterioinvestigacion,
                    (SELECT array_to_string(array_agg('* ' || cridoc.nombre 
                    order by cridoc.id),'<br>') FROM sga_criteriogestionperiodo cripe,
                    sga_criteriogestion cridoc,sga_detalledistributivo deta
                    WHERE deta.criteriogestionperiodo_id=cripe.id
                    and cripe.criterio_id=cridoc.id
                    AND deta.distributivo_id=dis.id) AS criteriogestion,
                    (SELECT array_to_string(array_agg('* ' || cridoc.nombre 
                    order by cridoc.id),'<br>') FROM sga_criteriodocenciaperiodo cripe,
                    sga_criteriodocencia cridoc,sga_detalledistributivo deta
                    WHERE deta.criteriodocenciaperiodo_id=cripe.id
                    and cripe.criterio_id=cridoc.id
                    AND cridoc.tipo=2
                    AND deta.distributivo_id=dis.id) AS criteriovinculacion
                    FROM sga_profesordistributivohoras dis,sga_profesor pro,sga_persona per
                    WHERE dis.periodo_id=%s
                    AND dis.profesor_id=pro.id
                    AND pro.persona_id=per.id
                    and per.real=True
                    GROUP BY per.apellido1,per.apellido2,per.nombres,dis.id
                    ) AS tableotra
                    GROUP BY criteriodocencia, criterioinvestigacion,criteriogestion,criteriovinculacion
                    ORDER BY totaldocentes
                    """ % (periodo.id)
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    for lis in results:
                        lista.append([lis[0],lis[1],lis[2],lis[3],lis[4],lis[5],lis[6]])
                    data['lista'] = lista
                    tablaponderacion = TablaPonderacionInstrumento.objects.all()
                    clasificacion = periodo.clasificacion
                    if clasificacion == 2:
                        tablaponderacion = tablaponderacion.filter(clasificacion=clasificacion)
                    data['ponderaciones'] = tablaponderacion
                    return render(request, "adm_evaluaciondocentesacreditacion/configurarcriterios.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrubrica':
                try:
                    data['title'] = u'Adicionar rubrica'
                    data['form'] = RubricaAcreditacionForm()
                    data['listadomodalidades'] = ProfesorMateria.objects. \
                        values_list('materia__nivel__modalidad_id',
                                    'materia__nivel__modalidad__nombre',
                                    'tipoprofesor_id',
                                    'tipoprofesor__nombre'). \
                        filter(materia__nivel__periodo=periodo, materia__nivel__status=True, materia__status=True, status=True). \
                        order_by().distinct('materia__nivel__modalidad_id', 'tipoprofesor_id')
                    return render(request, "adm_evaluaciondocentesacreditacion/addrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrubrica':
                try:
                    data['title'] = u'Editar rubrica'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['form'] = RubricaAcreditacionForm(initial={'nombre': rubrica.nombre,
                                                                    'descripcion': rubrica.descripcion,
                                                                    'para_hetero': rubrica.para_hetero,
                                                                    'informativa': rubrica.informativa,
                                                                    'para_materiapractica': rubrica.para_materiapractica,
                                                                    'para_nivelacion': rubrica.para_nivelacion,
                                                                    'para_nivelacionvirtual': rubrica.para_nivelacionvirtual,
                                                                    'para_semestrevirtual': rubrica.para_semestrevirtual,
                                                                    'para_practicasalud': rubrica.para_practicasalud,
                                                                    'para_auto': rubrica.para_auto,
                                                                    'para_par': rubrica.para_par,
                                                                    'directivos': rubrica.directivos,
                                                                    'tiporubrica': rubrica.tiporubrica,
                                                                    'tipoprofesor': rubrica.tipoprofesor,
                                                                    'para_directivo': rubrica.para_directivo
                                                                    # 'nivelacion_presencial': rubrica.nivelacion_presencial,
                                                                    # 'nivelacion_virtual': rubrica.nivelacion_virtual,
                                                                    # 'semestre_presencial': rubrica.semestre_presencial,
                                                                    # 'semestre_virtual': rubrica.semestre_virtual,
                                                                    })
                    data['modalidadselecta'] = rubrica.rubricamodalidad_set.values_list('modalidad_id', flat=True).filter(status=True)
                    data['listadomodalidad'] = Nivel.objects.values_list('modalidad_id', 'modalidad__nombre').filter(periodo=periodo, status=True).distinct()
                    data['tipoprofesorselecta'] = rubrica.rubricatipoprofesor_set.values_list('tipoprofesor_id', flat=True).filter(status=True)
                    data['listadotipoprofesor'] = ProfesorMateria.objects.values_list('tipoprofesor_id','tipoprofesor__nombre').filter(materia__nivel__periodo=periodo, status=True).order_by('tipoprofesor__nombre').distinct()
                    data['listadomodalidades'] = rubrica.rubricamodalidadtipoprofesor_set.filter(status=True).order_by('modalidad_id','tipoprofesor_id')
                    return render(request, "adm_evaluaciondocentesacreditacion/editrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'clonarrubrica':
                try:
                    data['title'] = u'Duplicar rubrica'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    form = RubricaAcreditacionForm(initial={'nombre': rubrica.nombre,
                                                            'descripcion': rubrica.descripcion})
                    form.duplicar()
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/clonarrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'caracteristicasrubrica':
                try:
                    data['title'] = u'Caracteristicas de rubrica de evaluación de profesores'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['caracteristicas'] = rubrica.rubricacaracteristica_set.all()
                    return render(request, "adm_evaluaciondocentesacreditacion/caracteristicasrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'preguntasrubrica':
                try:
                    data['title'] = u'Preguntas y respuestas de la rúbrica de evaluación de profesores'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['rubricaenuso'] = rubrica.en_uso()
                    data['preguntas'] = rubrica.mis_preguntas()
                    data['tiene_orden'] = rubrica.rubricapreguntas_set.exists()
                    return render(request, "adm_evaluaciondocentesacreditacion/preguntasrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delpreguntarubrica':
                try:
                    rubricapregunta = RubricaPreguntas.objects.get(pk=request.GET['id'])
                    rubrica = rubricapregunta.rubrica
                    log(u'Elimino pregunta de la rubrica: %s' % rubrica, request, "del")
                    rubricapregunta.delete()
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion?action=preguntasrubrica&id=' + str(rubrica.id))
                except Exception as ex:
                    pass

            elif action == 'addpreguntasrubrica':
                try:
                    data['title'] = u'Adicionar preguntas a la rubrica de evaluación de profesores'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['preguntascaracteristica'] = rubrica.mis_preguntas_caracteristicas()
                    return render(request, "adm_evaluaciondocentesacreditacion/addpreguntasrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcaracteristicarubrica':
                try:
                    data['title'] = u'Adicionar característica a rúbrica'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['caracteristicas'] = CaracteristicaEvaluacionAcreditacion.objects.exclude(id__in=[x.caracteristica.id for x in rubrica.rubricacaracteristica_set.all()])
                    return render(request, "adm_evaluaciondocentesacreditacion/addcaracteristicarubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'criteriosrubrica':
                try:
                    data['title'] = u'Criterios de rubrica de evaluación de profesores'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['rubricaenuso'] = rubrica.en_uso()
                    data['criteriosdocencia'] = rubrica.rubricacriteriodocencia_set.filter(criterio__criterio__tipo=1)
                    data['criteriosinvestigacion'] = rubrica.rubricacriterioinvestigacion_set.all()
                    data['criteriosgestion'] = rubrica.rubricacriteriogestion_set.all()
                    data['criteriosvinculacion'] = rubrica.rubricacriteriovinculacion_set.filter(criterio__criterio__tipo=2)
                    return render(request, "adm_evaluaciondocentesacreditacion/criteriosrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcriteriodocencia':
                try:
                    data['title'] = u'Adicionar criterio docencia'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['criteriodocencia'] = CriterioDocenciaPeriodo.objects.filter(periodo=proceso.periodo,criterio__tipo=1)
                    return render(request, "adm_evaluaciondocentesacreditacion/addcriteriodocencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcriteriovinculacion':
                try:
                    data['title'] = u'Adicionar criterio vinculación'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['criteriodocencia'] = CriterioDocenciaPeriodo.objects.filter(periodo=proceso.periodo,criterio__tipo=2)
                    return render(request, "adm_evaluaciondocentesacreditacion/addcriteriovinculacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcriterioinvestigacion':
                try:
                    data['title'] = u'Adicionar criterio investigación'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['criterioinvestigacion'] = CriterioInvestigacionPeriodo.objects.filter(periodo=proceso.periodo)
                    return render(request, "adm_evaluaciondocentesacreditacion/addcriterioinvestigacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcriteriogestion':
                try:
                    data['title'] = u'Adicionar criterio gestion'
                    data['rubrica'] = rubrica = Rubrica.objects.get(pk=request.GET['id'])
                    data['criteriogestion'] = CriterioGestionPeriodo.objects.filter(periodo=proceso.periodo)
                    return render(request, "adm_evaluaciondocentesacreditacion/addcriteriogestion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcriterioinvestigacion':
                try:
                    criterio = RubricaCriterioInvestigacion.objects.get(pk=request.GET['id'])
                    rubrica = criterio.rubrica
                    log(u'Elimino criterio investigacion: %s' % rubrica, request, "add")
                    criterio.delete()
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion?action=criteriosrubrica&id=' + str(rubrica.id))
                except Exception as ex:
                    pass

            elif action == 'delcriteriogestion':
                try:
                    criterio = RubricaCriterioGestion.objects.get(pk=request.GET['id'])
                    rubrica = criterio.rubrica
                    log(u'Elimino criterio gestion: %s' % rubrica, request, "add")
                    criterio.delete()
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion?action=criteriosrubrica&id=' + str(rubrica.id))
                except Exception as ex:
                    pass

            elif action == 'delpreguntanueva':
                try:
                    pregunta = TextoPreguntaAcreditacion.objects.get(pk=request.GET['id'])
                    caracteristica = CaracteristicaEvaluacionAcreditacion.objects.get(pk=request.GET['idc'])
                    if not pregunta.en_uso():
                        log(u'Elimino pregunta de evaluacion: %s' % pregunta, request, "del")
                        pregunta.delete()
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion?action=addpregunta&id=' + str(caracteristica.id))
                except Exception as ex:
                    pass

            elif action == 'mostrarresultados':
                try:
                    proceso.mostrarresultados = True
                    proceso.save(request)
                    log(u'Habilito mostrar resultados de proceso evaluativo: %s' % proceso, request, "del")
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion')
                except Exception as ex:
                    pass

            elif action == 'ocultarresultados':
                try:
                    proceso.mostrarresultados = False
                    proceso.save(request)
                    log(u'Deshabilito mostrar resultados de proceso evaluativo: %s' % proceso, request, "del")
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion')
                except Exception as ex:
                    pass

            elif action == 'mostrarfirmas':
                try:
                    proceso.mostrarfirmas = True
                    proceso.save(request)
                    log(u'Habilito mostrar firmas de proceso evaluativo: %s' % proceso, request, "del")
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion')
                except Exception as ex:
                    pass

            elif action == 'ocultarfirmas':
                try:
                    proceso.mostrarfirmas = False
                    proceso.save(request)
                    log(u'Deshabilito mostrar firmas de proceso evaluativo: %s' % proceso, request, "del")
                    return HttpResponseRedirect('/adm_evaluaciondocentesacreditacion')
                except Exception as ex:
                    pass

            elif action == 'consultarevaluacion':
                try:
                    data['title'] = u'Resumen de evaluación docente'
                    data['distributivos'] = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor__persona__real=True).exclude(tablaponderacion__isnull=True)
                    return render(request, "adm_evaluaciondocentesacreditacion/consultarevaluacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'consultarevaluacionfac':
                try:
                    data['title'] = u'Resumen de evaluación docente'
                    data['facultad'] = Coordinacion.objects.filter(pk__in=ProfesorDistributivoHoras.objects.values_list('coordinacion_id').filter(periodo_id=periodo.id)).order_by('nombre')
                    return render(request, "adm_evaluaciondocentesacreditacion/consultarevaluacionfac.html", data)
                except Exception as ex:
                    pass

            elif action == 'consultarevaluacionpos':
                try:
                    data['title'] = u'Resumen de evaluación docente de Posgrado'
                    data['ePeriodo'] = ePeriodo = Periodo.objects.get(status=True, pk=int(request.GET['idperiodo']))
                    data['eProceso'] = ePeriodo.proceso_evaluativoacreditacion()
                    return render(request, "adm_evaluaciondocentesacreditacion/consultaevaluacionpos.html", data)
                except Exception as ex:
                    pass

            elif action == 'consulpromeval':
                try:
                    data['title'] = u'PROMEDIOS DE EVALUACIONES'
                    data['facultad'] = Coordinacion.objects.filter(pk__in=[1,2,3,4,5,7])
                    data['carreras'] = 0
                    data['codifacu'] = 0
                    return render(request, "adm_evaluaciondocentesacreditacion/consultapromevaluacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'consulprometotalvalfacxls':
                try:
                    # periodo = request.GET['periodo']
                    cursor = connection.cursor()
                    idproceso = int(proceso.id)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_promedioevaluaciones.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('EVALUACIONXFACULTAD')
                    decimal_style = xlwt.XFStyle()
                    decimal_style.num_format_str = '0.00'
                    estilo1 = xlwt.easyxf('font: height 200, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 53, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.write_merge(2, 2, 4, 19, 'PROMEDIOS DE EVALUACIONES', estilo1)
                    ws.write_merge(2, 2, 20, 35, 'RESULTADOS SEGUN PONDERACIONES', estilo1)
                    ws.write_merge(2, 2, 36, 51, 'PONDERACION SEGUN DISTRIBUTIVO', estilo1)
                    ws.write_merge(3, 3, 4, 7, 'DOCENCIA', estilo1)
                    ws.write_merge(3, 3, 8, 11, 'INVESTIGACION', estilo1)
                    ws.write_merge(3, 3, 12, 15, 'GESTION', estilo1)
                    ws.write_merge(3, 3, 16, 19, 'VINCULACION', estilo1)
                    ws.write_merge(3, 3, 20, 23, 'DOCENCIA', estilo1)
                    ws.write_merge(3, 3, 24, 27, 'INVESTIGACION', estilo1)
                    ws.write_merge(3, 3, 28, 31, 'GESTION', estilo1)
                    ws.write_merge(3, 3, 32, 35, 'VINCULACION', estilo1)
                    ws.write_merge(3, 3, 36, 39, 'DOCENCIA', estilo1)
                    ws.write_merge(3, 3, 40, 43, 'INVESTIGACION', estilo1)
                    ws.write_merge(3, 3, 44, 47, 'GESTION', estilo1)
                    ws.write_merge(3, 3, 48, 51, 'VINCULACION', estilo1)
                    ws.write_merge(3, 3, 52, 53, 'COMPONENTE', estilo1)
                    ws.col(0).width = 1000
                    ws.col(1).width = 10000
                    ws.col(2).width = 10000
                    ws.col(3).width = 10000
                    ws.col(4).width = 2000
                    ws.col(5).width = 2000
                    ws.col(6).width = 2000
                    ws.col(7).width = 2000
                    ws.col(8).width = 2000
                    ws.col(9).width = 2000
                    ws.col(10).width = 2000
                    ws.col(11).width = 2000
                    ws.col(12).width = 2000
                    ws.col(13).width = 2000
                    ws.col(14).width = 2000
                    ws.col(15).width = 2000
                    ws.col(16).width = 2000
                    ws.col(17).width = 2000
                    ws.col(18).width = 2000
                    ws.col(19).width = 2000
                    ws.col(20).width = 2000
                    ws.col(21).width = 2000
                    ws.col(22).width = 2000
                    ws.col(23).width = 2000
                    ws.col(24).width = 2000
                    ws.col(25).width = 2000
                    ws.col(26).width = 2000
                    ws.col(27).width = 2000
                    ws.col(28).width = 2000
                    ws.col(29).width = 2000
                    ws.col(30).width = 2000
                    ws.col(31).width = 2000
                    ws.col(32).width = 2000
                    ws.col(33).width = 2000
                    ws.col(34).width = 2000
                    ws.col(35).width = 2000
                    ws.col(36).width = 2000
                    ws.col(37).width = 2000
                    ws.col(38).width = 2000
                    ws.col(39).width = 2000
                    ws.col(40).width = 2000
                    ws.col(41).width = 2000
                    ws.col(42).width = 2000
                    ws.col(43).width = 2000
                    ws.col(44).width = 2000
                    ws.col(45).width = 2000
                    ws.col(46).width = 2000
                    ws.col(47).width = 2000
                    ws.col(48).width = 2000
                    ws.col(49).width = 2000
                    ws.col(50).width = 2000
                    ws.col(51).width = 2000
                    ws.col(52).width = 4000
                    ws.col(53).width = 4000
                    ws.write(4, 0, 'N.')
                    ws.write(4, 1, 'APELLIDOS Y NOMBRES DEL DOCENTE')
                    ws.write(4, 2, 'FACULTAD')
                    ws.write(4, 3, 'CARRERA')
                    ws.write(4, 4, 'Heter.')
                    ws.write(4, 5, 'Auto')
                    ws.write(4, 6, 'Par.')
                    ws.write(4, 7, 'Dire.')
                    ws.write(4, 8, 'Heter.')
                    ws.write(4, 9, 'Auto')
                    ws.write(4, 10, 'Par.')
                    ws.write(4, 11, 'Dire.')
                    ws.write(4, 12, 'Heter.')
                    ws.write(4, 13, 'Auto')
                    ws.write(4, 14, 'Par.')
                    ws.write(4, 15, 'Dire.')
                    ws.write(4, 16, 'Heter.')
                    ws.write(4, 17, 'Auto')
                    ws.write(4, 18, 'Par.')
                    ws.write(4, 19, 'Dire.')
                    ws.write(4, 20, 'Heter.')
                    ws.write(4, 21, 'Auto')
                    ws.write(4, 22, 'Par.')
                    ws.write(4, 23, 'Dire.')
                    ws.write(4, 24, 'Heter.')
                    ws.write(4, 25, 'Auto')
                    ws.write(4, 26, 'Par.')
                    ws.write(4, 27, 'Dire.')
                    ws.write(4, 28, 'Heter.')
                    ws.write(4, 29, 'Auto')
                    ws.write(4, 30, 'Par.')
                    ws.write(4, 31, 'Dire.')
                    ws.write(4, 32, 'Heter.')
                    ws.write(4, 33, 'Auto')
                    ws.write(4, 34, 'Par.')
                    ws.write(4, 35, 'Dire.')
                    ws.write(4, 36, 'Total.')
                    ws.write(4, 37, 'Hrs')
                    ws.write(4, 38, 'Pond.')
                    ws.write(4, 39, 'Valor.')
                    ws.write(4, 40, 'Total.')
                    ws.write(4, 41, 'Hrs')
                    ws.write(4, 42, 'Pond.')
                    ws.write(4, 43, 'Valor.')
                    ws.write(4, 44, 'Total.')
                    ws.write(4, 45, 'Hrs')
                    ws.write(4, 46, 'Pond.')
                    ws.write(4, 47, 'Valor.')
                    ws.write(4, 48, 'Total.')
                    ws.write(4, 49, 'Hrs')
                    ws.write(4, 50, 'Pond.')
                    ws.write(4, 51, 'Valor.')
                    ws.write(4, 52, 'Escala 1:5')
                    ws.write(4, 53, 'Escala 1:100')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    if int(request.GET["idfacu"]) == 0:
                        cursor.execute("select distinct per.apellido1,per.apellido2,per.nombres,"
                                       "CASE WHEN coor.nombre IS NULL THEN (select distinct coord.nombre "
                                       "from sga_coordinacion coord where pro.coordinacion_id=coord.id ) "
                                       "ELSE coor.nombre END as facultad,CASE WHEN car.nombre IS NULL THEN '-' "
                                       "ELSE car.nombre END as nomcarrera,"
                                       "ra.promedio_docencia_hetero,"
                                       "ra.promedio_docencia_auto,ra.promedio_docencia_par,ra.promedio_docencia_directivo,"
                                       "ra.promedio_investigacion_hetero,ra.promedio_investigacion_auto,"
                                       "ra.promedio_investigacion_par,ra.promedio_investigacion_directivo,"
                                       "ra.promedio_gestion_hetero,ra.promedio_gestion_auto,ra.promedio_gestion_par,"
                                       "ra.promedio_gestion_directivo, "
                                       "ra.promedio_vinculacion_hetero, ra.promedio_vinculacion_auto,ra.promedio_vinculacion_par, ra.promedio_vinculacion_directivo,"
                                       "ra.valor_tabla_docencia_hetero,"
                                       "ra.valor_tabla_docencia_auto,ra.valor_tabla_docencia_par, "
                                       "ra.valor_tabla_docencia_directivo,ra.valor_tabla_investigacion_hetero,"
                                       "ra.valor_tabla_investigacion_auto,ra.valor_tabla_investigacion_par,"
                                       "ra.valor_tabla_investigacion_directivo,ra.valor_tabla_gestion_hetero,"
                                       "ra.valor_tabla_gestion_auto,ra.valor_tabla_gestion_par,ra.valor_tabla_gestion_directivo,"
                                       "ra.valor_tabla_vinculacion_hetero, ra.valor_tabla_vinculacion_auto,ra.valor_tabla_vinculacion_par, ra.valor_tabla_vinculacion_directivo,"
                                       "ra.total_tabla_docencia,dh.horasdocencia,dh.ponderacion_horas_docencia,"
                                       "ra.resultado_docencia,ra.total_tabla_investigacion,dh.horasinvestigacion,"
                                       "dh.ponderacion_horas_investigacion,ra.resultado_investigacion,ra.total_tabla_gestion,"
                                       "dh.horasgestion,dh.ponderacion_horas_gestion,ra.resultado_gestion,"
                                       "ra.total_tabla_vinculacion,dh.horasvinculacion,dh.ponderacion_horas_vinculacion, ra.resultado_vinculacion,"
                                       "ra.resultado_total,"
                                       "round((ra.resultado_total*100/5),2) as escala,"
                                       "CASE WHEN coor.id IS NULL THEN (select distinct coord.id from sga_coordinacion coord "
                                       "where pro.coordinacion_id=coord.id )ELSE coor.id END as idfacultad "
                                       "from sga_profesordistributivohoras dh "
                                       "right join sga_detalledistributivo detdis on dh.id=detdis.distributivo_id "
                                       "left join sga_respuestaevaluacionacreditacion rea on dh.profesor_id=rea.profesor_id and rea.proceso_id= %s "
                                       "left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id "
                                       "left join sga_coordinacion coor on coor.id=rea.coordinacion_id "
                                       "left join sga_carrera car on car.id=rea.carrera_id "
                                       "left join sga_profesor pro on pro.id=dh.profesor_id "
                                       "left join sga_persona per on per.id=pro.persona_id "
                                       "where dh.periodo_id='" + request.GET["idper"] + "' and dh.activoevaldocente=True and per.real=True order by 1", [idproceso])
                    else:
                        cursor.execute("select * from (select distinct per.apellido1,per.apellido2,per.nombres,"
                                       "CASE WHEN coor.nombre IS NULL THEN (select distinct coord.nombre "
                                       "from sga_coordinacion coord where pro.coordinacion_id=coord.id ) "
                                       "ELSE coor.nombre END as facultad,CASE WHEN car.nombre IS NULL THEN '-' "
                                       "ELSE car.nombre END as nomcarrera,"
                                       "ra.promedio_docencia_hetero,"
                                       "ra.promedio_docencia_auto,ra.promedio_docencia_par,ra.promedio_docencia_directivo,"
                                       "ra.promedio_investigacion_hetero,ra.promedio_investigacion_auto,"
                                       "ra.promedio_investigacion_par,ra.promedio_investigacion_directivo,"
                                       "ra.promedio_gestion_hetero,ra.promedio_gestion_auto,ra.promedio_gestion_par,"
                                       "ra.promedio_gestion_directivo, "
                                       "ra.promedio_vinculacion_hetero, ra.promedio_vinculacion_auto,ra.promedio_vinculacion_par, ra.promedio_vinculacion_directivo,"
                                       "ra.valor_tabla_docencia_hetero,"
                                       "ra.valor_tabla_docencia_auto,ra.valor_tabla_docencia_par, "
                                       "ra.valor_tabla_docencia_directivo,ra.valor_tabla_investigacion_hetero,"
                                       "ra.valor_tabla_investigacion_auto,ra.valor_tabla_investigacion_par,"
                                       "ra.valor_tabla_investigacion_directivo,ra.valor_tabla_gestion_hetero,"
                                       "ra.valor_tabla_gestion_auto,ra.valor_tabla_gestion_par,ra.valor_tabla_gestion_directivo,"
                                       "ra.valor_tabla_vinculacion_hetero, ra.valor_tabla_vinculacion_auto,ra.valor_tabla_vinculacion_par, ra.valor_tabla_vinculacion_directivo,"
                                       "ra.total_tabla_docencia,dh.horasdocencia,dh.ponderacion_horas_docencia,"
                                       "ra.resultado_docencia,ra.total_tabla_investigacion,dh.horasinvestigacion,"
                                       "dh.ponderacion_horas_investigacion,ra.resultado_investigacion,ra.total_tabla_gestion,"
                                       "dh.horasgestion,dh.ponderacion_horas_gestion,ra.resultado_gestion,"
                                       "ra.total_tabla_vinculacion,dh.horasvinculacion,dh.ponderacion_horas_vinculacion, ra.resultado_vinculacion,"
                                       "ra.resultado_total,"
                                       "round((ra.resultado_total*100/5),2) as escala,"
                                       "CASE WHEN coor.id IS NULL THEN (select distinct coord.id from sga_coordinacion coord "
                                       "where pro.coordinacion_id=coord.id )ELSE coor.id END as idfacultad "
                                       "from sga_profesordistributivohoras dh "
                                       "right join sga_detalledistributivo detdis on dh.id=detdis.distributivo_id "
                                       "left join sga_respuestaevaluacionacreditacion rea on dh.profesor_id=rea.profesor_id and rea.proceso_id= %s "
                                       "left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id "
                                       "left join sga_coordinacion coor on coor.id=rea.coordinacion_id "
                                       "left join sga_carrera car on car.id=rea.carrera_id "
                                       "left join sga_profesor pro on pro.id=dh.profesor_id "
                                       "left join sga_persona per on per.id=pro.persona_id "
                                       "where dh.periodo_id='" + request.GET["idper"] + "' and dh.activoevaldocente=True and per.real=True order by 1) as d where idfacultad='" + request.GET["idfacu"] + "'", [idproceso])
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, a - 4)
                        ws.write(a, 1, per[0] + ' ' + per[1] + ' ' + per[2])
                        ws.write(a, 2, per[3])
                        ws.write(a, 3, per[4])
                        ws.write(a, 4, per[5], decimal_style)
                        ws.write(a, 5, per[6], decimal_style)
                        ws.write(a, 6, per[7], decimal_style)
                        ws.write(a, 7, per[8], decimal_style)
                        ws.write(a, 8, per[9], decimal_style)
                        ws.write(a, 9, per[10], decimal_style)
                        ws.write(a, 10, per[11], decimal_style)
                        ws.write(a, 11, per[12], decimal_style)
                        ws.write(a, 12, per[13], decimal_style)
                        ws.write(a, 13, per[14], decimal_style)
                        ws.write(a, 14, per[15], decimal_style)
                        ws.write(a, 15, per[16], decimal_style)
                        ws.write(a, 16, per[17], decimal_style)
                        ws.write(a, 17, per[18], decimal_style)
                        ws.write(a, 18, per[19], decimal_style)
                        ws.write(a, 19, per[20], decimal_style)
                        ws.write(a, 20, per[21], decimal_style)
                        ws.write(a, 21, per[22], decimal_style)
                        ws.write(a, 22, per[23], decimal_style)
                        ws.write(a, 23, per[24], decimal_style)
                        ws.write(a, 24, per[25], decimal_style)
                        ws.write(a, 25, per[26], decimal_style)
                        ws.write(a, 26, per[27], decimal_style)
                        ws.write(a, 27, per[28], decimal_style)
                        ws.write(a, 28, per[29], decimal_style)
                        ws.write(a, 29, per[30], decimal_style)
                        ws.write(a, 30, per[31], decimal_style)
                        ws.write(a, 31, per[32], decimal_style)
                        ws.write(a, 32, per[33], decimal_style)
                        ws.write(a, 33, per[34], decimal_style)
                        ws.write(a, 34, per[35], decimal_style)
                        ws.write(a, 35, per[36], decimal_style)
                        ws.write(a, 36, per[37], decimal_style)
                        ws.write(a, 37, per[38], decimal_style)
                        ws.write(a, 38, per[39], decimal_style)
                        ws.write(a, 39, per[40], decimal_style)
                        ws.write(a, 40, per[41], decimal_style)
                        ws.write(a, 41, per[42], decimal_style)
                        ws.write(a, 42, per[43], decimal_style)
                        ws.write(a, 43, per[44], decimal_style)
                        ws.write(a, 44, per[45], decimal_style)
                        ws.write(a, 45, per[46], decimal_style)
                        ws.write(a, 46, per[47], decimal_style)
                        ws.write(a, 47, per[48], decimal_style)
                        ws.write(a, 48, per[49], decimal_style)
                        ws.write(a, 49, per[50], decimal_style)
                        ws.write(a, 50, per[51], decimal_style)
                        ws.write(a, 51, per[52], decimal_style)
                        ws.write(a, 52, per[53], decimal_style)
                        ws.write(a, 53, per[54], decimal_style)
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'consulprometotalvalcarrxls':
                try:
                    # periodo = request.GET['periodo']
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_promedioevaluaciones.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('EVALUACIONXCARRERA')
                    decimal_style = xlwt.XFStyle()
                    decimal_style.num_format_str = '0.00'
                    estilo1 = xlwt.easyxf('font: height 200, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 53, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.write_merge(2, 2, 4, 19, 'PROMEDIOS DE EVALUACIONES', estilo1)
                    ws.write_merge(2, 2, 20, 35, 'RESULTADOS SEGUN PONDERACIONES', estilo1)
                    ws.write_merge(2, 2, 36, 51, 'PONDERACION SEGUN DISTRIBUTIVO', estilo1)
                    ws.write_merge(3, 3, 4, 7, 'DOCENCIA', estilo1)
                    ws.write_merge(3, 3, 8, 11, 'INVESTIGACION', estilo1)
                    ws.write_merge(3, 3, 12, 15, 'GESTION', estilo1)
                    ws.write_merge(3, 3, 16, 19, 'VINCULACION', estilo1)
                    ws.write_merge(3, 3, 20, 23, 'DOCENCIA', estilo1)
                    ws.write_merge(3, 3, 24, 27, 'INVESTIGACION', estilo1)
                    ws.write_merge(3, 3, 28, 31, 'GESTION', estilo1)
                    ws.write_merge(3, 3, 32, 35, 'VINCULACION', estilo1)
                    ws.write_merge(3, 3, 36, 39, 'DOCENCIA', estilo1)
                    ws.write_merge(3, 3, 40, 43, 'INVESTIGACION', estilo1)
                    ws.write_merge(3, 3, 44, 47, 'GESTION', estilo1)
                    ws.write_merge(3, 3, 48, 51, 'VINCULACION', estilo1)
                    ws.write_merge(3, 3, 52, 53, 'COMPONENTE', estilo1)
                    ws.col(0).width = 1000
                    ws.col(1).width = 10000
                    ws.col(2).width = 10000
                    ws.col(3).width = 10000
                    ws.col(4).width = 2000
                    ws.col(5).width = 2000
                    ws.col(6).width = 2000
                    ws.col(7).width = 2000
                    ws.col(8).width = 2000
                    ws.col(9).width = 2000
                    ws.col(10).width = 2000
                    ws.col(11).width = 2000
                    ws.col(12).width = 2000
                    ws.col(13).width = 2000
                    ws.col(14).width = 2000
                    ws.col(15).width = 2000
                    ws.col(16).width = 2000
                    ws.col(17).width = 2000
                    ws.col(18).width = 2000
                    ws.col(19).width = 2000
                    ws.col(20).width = 2000
                    ws.col(21).width = 2000
                    ws.col(22).width = 2000
                    ws.col(23).width = 2000
                    ws.col(24).width = 2000
                    ws.col(25).width = 2000
                    ws.col(26).width = 2000
                    ws.col(27).width = 2000
                    ws.col(28).width = 2000
                    ws.col(29).width = 2000
                    ws.col(30).width = 2000
                    ws.col(31).width = 2000
                    ws.col(32).width = 2000
                    ws.col(33).width = 2000
                    ws.col(34).width = 2000
                    ws.col(35).width = 2000
                    ws.col(36).width = 2000
                    ws.col(37).width = 2000
                    ws.col(38).width = 2000
                    ws.col(39).width = 2000
                    ws.col(40).width = 2000
                    ws.col(41).width = 2000
                    ws.col(42).width = 2000
                    ws.col(43).width = 2000
                    ws.col(44).width = 2000
                    ws.col(45).width = 2000
                    ws.col(46).width = 2000
                    ws.col(47).width = 2000
                    ws.col(48).width = 2000
                    ws.col(49).width = 2000
                    ws.col(50).width = 2000
                    ws.col(51).width = 2000
                    ws.col(52).width = 4000
                    ws.col(53).width = 4000
                    ws.write(4, 0, 'N.')
                    ws.write(4, 1, 'APELLIDOS Y NOMBRES DEL DOCENTE')
                    ws.write(4, 2, 'FACULTAD')
                    ws.write(4, 3, 'CARRERA')
                    ws.write(4, 4, 'Heter.')
                    ws.write(4, 5, 'Auto')
                    ws.write(4, 6, 'Par.')
                    ws.write(4, 7, 'Dire.')
                    ws.write(4, 8, 'Heter.')
                    ws.write(4, 9, 'Auto')
                    ws.write(4, 10, 'Par.')
                    ws.write(4, 11, 'Dire.')
                    ws.write(4, 12, 'Heter.')
                    ws.write(4, 13, 'Auto')
                    ws.write(4, 14, 'Par.')
                    ws.write(4, 15, 'Dire.')
                    ws.write(4, 16, 'Heter.')
                    ws.write(4, 17, 'Auto')
                    ws.write(4, 18, 'Par.')
                    ws.write(4, 19, 'Dire.')
                    ws.write(4, 20, 'Heter.')
                    ws.write(4, 21, 'Auto')
                    ws.write(4, 22, 'Par.')
                    ws.write(4, 23, 'Dire.')
                    ws.write(4, 24, 'Heter.')
                    ws.write(4, 25, 'Auto')
                    ws.write(4, 26, 'Par.')
                    ws.write(4, 27, 'Dire.')
                    ws.write(4, 28, 'Heter.')
                    ws.write(4, 29, 'Auto')
                    ws.write(4, 30, 'Par.')
                    ws.write(4, 31, 'Dire.')
                    ws.write(4, 32, 'Heter.')
                    ws.write(4, 33, 'Auto')
                    ws.write(4, 34, 'Par.')
                    ws.write(4, 35, 'Dire.')
                    ws.write(4, 36, 'Total.')
                    ws.write(4, 37, 'Hrs')
                    ws.write(4, 38, 'Pond.')
                    ws.write(4, 39, 'Valor.')
                    ws.write(4, 40, 'Total.')
                    ws.write(4, 41, 'Hrs')
                    ws.write(4, 42, 'Pond.')
                    ws.write(4, 43, 'Valor.')
                    ws.write(4, 44, 'Total.')
                    ws.write(4, 45, 'Hrs')
                    ws.write(4, 46, 'Pond.')
                    ws.write(4, 47, 'Valor.')
                    ws.write(4, 48, 'Total.')
                    ws.write(4, 49, 'Hrs')
                    ws.write(4, 50, 'Pond.')
                    ws.write(4, 51, 'Valor.')
                    ws.write(4, 52, 'Escala 1:5')
                    ws.write(4, 53, 'Escala 1:100')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    if request.GET["idcarrera"] == '':
                        listaestudiante = "select distinct per.apellido1,per.apellido2,per.nombres,coor.nombre as facultad,car.nombre as nomcarrera," \
                                          "ra.promedio_docencia_hetero,ra.promedio_docencia_auto,ra.promedio_docencia_par,ra.promedio_docencia_directivo," \
                                          "ra.promedio_investigacion_hetero,ra.promedio_investigacion_auto,ra.promedio_investigacion_par,ra.promedio_investigacion_directivo," \
                                          "ra.promedio_gestion_hetero,ra.promedio_gestion_auto,ra.promedio_gestion_par, ra.promedio_gestion_directivo, " \
                                          "ra.promedio_vinculacion_hetero, ra.promedio_vinculacion_auto,ra.promedio_vinculacion_par, ra.promedio_vinculacion_directivo," \
                                          "ra.valor_tabla_docencia_hetero," \
                                          "ra.valor_tabla_docencia_auto,ra.valor_tabla_docencia_par, " \
                                          "ra.valor_tabla_docencia_directivo,ra.valor_tabla_investigacion_hetero," \
                                          "ra.valor_tabla_investigacion_auto,ra.valor_tabla_investigacion_par," \
                                          "ra.valor_tabla_investigacion_directivo,ra.valor_tabla_gestion_hetero," \
                                          "ra.valor_tabla_gestion_auto,ra.valor_tabla_gestion_par,ra.valor_tabla_gestion_directivo," \
                                          "ra.valor_tabla_vinculacion_hetero, ra.valor_tabla_vinculacion_auto,ra.valor_tabla_vinculacion_par, ra.valor_tabla_vinculacion_directivo," \
                                          "ra.total_tabla_docencia,dh.horasdocencia,dh.ponderacion_horas_docencia," \
                                          "ra.resultado_docencia,ra.total_tabla_investigacion,dh.horasinvestigacion," \
                                          "dh.ponderacion_horas_investigacion,ra.resultado_investigacion,ra.total_tabla_gestion," \
                                          "dh.horasgestion,dh.ponderacion_horas_gestion,ra.resultado_gestion," \
                                          "ra.total_tabla_vinculacion,dh.horasvinculacion,dh.ponderacion_horas_vinculacion, ra.resultado_vinculacion," \
                                          "ra.resultado_total," \
                                          "round((ra.resultado_total*100/5),2) as escala from sga_respuestaevaluacionacreditacion rea " \
                                          "left join sga_procesoevaluativoacreditacion pea on pea.id=rea.proceso_id " \
                                          "left join sga_profesordistributivohoras dh on dh.profesor_id=rea.profesor_id and dh.periodo_id=pea.periodo_id " \
                                          "left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id " \
                                          "left join sga_coordinacion coor on coor.id=rea.coordinacion_id left join sga_carrera car on car.id=rea.carrera_id " \
                                          "left join sga_profesor pro on pro.id=rea.profesor_id left join sga_persona per on per.id=pro.persona_id " \
                                          "where pea.periodo_id='" + request.GET["idper"] + "' and dh.activoevaldocente=True and coor.id='" + request.GET["idfacu"] + "' order by 1"
                    else:
                        listaestudiante = "select distinct per.apellido1,per.apellido2,per.nombres,coor.nombre as facultad,car.nombre as nomcarrera," \
                                          "ra.promedio_docencia_hetero,ra.promedio_docencia_auto,ra.promedio_docencia_par,ra.promedio_docencia_directivo," \
                                          "ra.promedio_investigacion_hetero,ra.promedio_investigacion_auto,ra.promedio_investigacion_par,ra.promedio_investigacion_directivo," \
                                          "ra.promedio_gestion_hetero,ra.promedio_gestion_auto,ra.promedio_gestion_par, ra.promedio_gestion_directivo, " \
                                          "ra.promedio_vinculacion_hetero, ra.promedio_vinculacion_auto,ra.promedio_vinculacion_par, ra.promedio_vinculacion_directivo," \
                                          "ra.valor_tabla_docencia_hetero," \
                                          "ra.valor_tabla_docencia_auto,ra.valor_tabla_docencia_par, " \
                                          "ra.valor_tabla_docencia_directivo,ra.valor_tabla_investigacion_hetero," \
                                          "ra.valor_tabla_investigacion_auto,ra.valor_tabla_investigacion_par," \
                                          "ra.valor_tabla_investigacion_directivo,ra.valor_tabla_gestion_hetero," \
                                          "ra.valor_tabla_gestion_auto,ra.valor_tabla_gestion_par,ra.valor_tabla_gestion_directivo," \
                                          "ra.valor_tabla_vinculacion_hetero, ra.valor_tabla_vinculacion_auto,ra.valor_tabla_vinculacion_par, ra.valor_tabla_vinculacion_directivo," \
                                          "ra.total_tabla_docencia,dh.horasdocencia,dh.ponderacion_horas_docencia," \
                                          "ra.resultado_docencia,ra.total_tabla_investigacion,dh.horasinvestigacion," \
                                          "dh.ponderacion_horas_investigacion,ra.resultado_investigacion,ra.total_tabla_gestion," \
                                          "dh.horasgestion,dh.ponderacion_horas_gestion,ra.resultado_gestion," \
                                          "ra.total_tabla_vinculacion,dh.horasvinculacion,dh.ponderacion_horas_vinculacion, ra.resultado_vinculacion," \
                                          "ra.resultado_total," \
                                          "round((ra.resultado_total*100/5),2) as escala " \
                                          "from sga_respuestaevaluacionacreditacion rea left join sga_procesoevaluativoacreditacion pea on pea.id=rea.proceso_id " \
                                          "left join sga_profesordistributivohoras dh on dh.profesor_id=rea.profesor_id and dh.periodo_id=pea.periodo_id " \
                                          "left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id " \
                                          "left join sga_coordinacion coor on coor.id=rea.coordinacion_id left join sga_carrera car on car.id=rea.carrera_id " \
                                          "left join sga_profesor pro on pro.id=rea.profesor_id left join sga_persona per on per.id=pro.persona_id " \
                                          "where pea.periodo_id='" + request.GET["idper"] + "' and dh.activoevaldocente=True and coor.id='" + request.GET["idfacu"] + \
                                          "' and car.id='" + request.GET["idcarrera"] + "' order by 1"
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, a - 4)
                        ws.write(a, 1, per[0] + ' ' + per[1] + ' ' + per[2])
                        ws.write(a, 2, per[3])
                        ws.write(a, 3, per[4])
                        ws.write(a, 4, per[5], decimal_style)
                        ws.write(a, 5, per[6], decimal_style)
                        ws.write(a, 6, per[7], decimal_style)
                        ws.write(a, 7, per[8], decimal_style)
                        ws.write(a, 8, per[9], decimal_style)
                        ws.write(a, 9, per[10], decimal_style)
                        ws.write(a, 10, per[11], decimal_style)
                        ws.write(a, 11, per[12], decimal_style)
                        ws.write(a, 12, per[13], decimal_style)
                        ws.write(a, 13, per[14], decimal_style)
                        ws.write(a, 14, per[15], decimal_style)
                        ws.write(a, 15, per[16], decimal_style)
                        ws.write(a, 16, per[17], decimal_style)
                        ws.write(a, 17, per[18], decimal_style)
                        ws.write(a, 18, per[19], decimal_style)
                        ws.write(a, 19, per[20], decimal_style)
                        ws.write(a, 20, per[21], decimal_style)
                        ws.write(a, 21, per[22], decimal_style)
                        ws.write(a, 22, per[23], decimal_style)
                        ws.write(a, 23, per[24], decimal_style)
                        ws.write(a, 24, per[25], decimal_style)
                        ws.write(a, 25, per[26], decimal_style)
                        ws.write(a, 26, per[27], decimal_style)
                        ws.write(a, 27, per[28], decimal_style)
                        ws.write(a, 28, per[29], decimal_style)
                        ws.write(a, 29, per[30], decimal_style)
                        ws.write(a, 30, per[31], decimal_style)
                        ws.write(a, 31, per[32], decimal_style)
                        ws.write(a, 32, per[33], decimal_style)
                        ws.write(a, 33, per[34], decimal_style)
                        ws.write(a, 34, per[35], decimal_style)
                        ws.write(a, 35, per[36], decimal_style)
                        ws.write(a, 36, per[37], decimal_style)
                        ws.write(a, 37, per[38], decimal_style)
                        ws.write(a, 38, per[39], decimal_style)
                        ws.write(a, 39, per[40], decimal_style)
                        ws.write(a, 40, per[41], decimal_style)
                        ws.write(a, 41, per[42], decimal_style)
                        ws.write(a, 42, per[43], decimal_style)
                        ws.write(a, 43, per[44], decimal_style)
                        ws.write(a, 44, per[45], decimal_style)
                        ws.write(a, 45, per[46], decimal_style)
                        ws.write(a, 46, per[47], decimal_style)
                        ws.write(a, 47, per[48], decimal_style)
                        ws.write(a, 48, per[49], decimal_style)
                        ws.write(a, 49, per[50], decimal_style)
                        ws.write(a, 50, per[51], decimal_style)
                        ws.write(a, 51, per[52], decimal_style)
                        ws.write(a, 52, per[53], decimal_style)
                        ws.write(a, 53, per[54], decimal_style)
                    # ws.write_merge(a + 2, a + 2, 0, 1, datetime.today(), date_format)
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'descargarevalmigracion':
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
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_'+ periodo.nombre + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"CEDULA", 4000),
                        (u"APELLIDO 1", 6000),
                        (u"APELLIDO 2", 6000),
                        (u"NOMBRE", 6000),
                        (u"SEXO", 4000),
                        (u"promedio_docencia_hetero", 4000),
                        (u"promedio_docencia_auto", 4000),
                        (u"promedio_docencia_par", 4000),
                        (u"promedio_docencia_directivo", 4000),
                        (u"promedio_investigacion_hetero", 4000),
                        (u"promedio_investigacion_auto", 4000),
                        (u"promedio_investigacion_par", 4000),
                        (u"promedio_investigacion_directivo", 4000),
                        (u"promedio_gestion_hetero", 4000),
                        (u"promedio_gestion_auto", 4000),
                        (u"promedio_gestion_par", 4000),
                        (u"promedio_gestion_directivo", 4000),
                        (u"resultado_total", 4000),
                        (u"horas_tutoria", 4000),
                        (u"horas_vinculacion", 4000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = ResumenFinalEvaluacionAcreditacionFija.objects.filter(distributivo__periodo=periodo)
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        campo2 = lista.distributivo.profesor.persona.cedula
                        campo3 = lista.distributivo.profesor.persona.apellido1
                        campo4 = lista.distributivo.profesor.persona.apellido2
                        campo5 = lista.distributivo.profesor.persona.nombres
                        campo6 = lista.distributivo.profesor.persona.sexo.nombre
                        campo7 = lista.promedio_docencia_hetero
                        campo8 = lista.promedio_docencia_auto
                        campo9 = lista.promedio_docencia_par
                        campo10 = lista.promedio_docencia_directivo
                        campo11 = lista.promedio_investigacion_hetero
                        campo12 = lista.promedio_investigacion_auto
                        campo13 = lista.promedio_investigacion_par
                        campo14 = lista.promedio_investigacion_directivo
                        campo15 = lista.promedio_gestion_hetero
                        campo16 = lista.promedio_gestion_auto
                        campo17 = lista.promedio_gestion_par
                        campo18 = lista.promedio_gestion_directivo
                        campo19 = lista.resultado_total
                        campo20 = lista.horas_tutoria
                        campo21 = lista.horas_vinculacion

                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        ws.write(row_num, 11, campo12, font_style2)
                        ws.write(row_num, 12, campo13, font_style2)
                        ws.write(row_num, 13, campo14, font_style2)
                        ws.write(row_num, 14, campo15, font_style2)
                        ws.write(row_num, 15, campo16, font_style2)
                        ws.write(row_num, 16, campo17, font_style2)
                        ws.write(row_num, 17, campo18, font_style2)
                        ws.write(row_num, 18, campo19, font_style2)
                        ws.write(row_num, 19, campo20, font_style2)
                        ws.write(row_num, 20, campo21, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'docentesdistributivoexcel':
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"N#", 3000),
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 10000),
                        (u"TABLA PONDERATIVA", 10000),
                        (u"COORDINACION", 15000),
                        (u"CARRERA", 15000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 4
                    i = 0
                    listadodistributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo).order_by('profesor__persona_apellido1', 'profesor__persona_apellido2', 'profesor__persona_nombres')
                    for lista in listadodistributivo:
                        i += 1
                        if lista.profesor.persona.cedula:
                            campo1 = lista.profesor.persona.cedula
                        else:
                            campo1 = lista.profesor.persona.pasaporte
                        campo2 = lista.profesor.persona.nombre_completo_inverso().__str__()
                        campo3 = 'NO TIENE TABLA PONDERATIVA'
                        if lista.tablaponderacion:
                            campo3 = lista.tablaponderacion.nombre
                        campo4 = 'NO TIENE COORDINACION'
                        if lista.coordinacion:
                            campo4 = lista.coordinacion.nombre
                        campo5 = 'NO TIENE CARRERA'
                        if lista.carrera:
                            campo5 = lista.carrera.nombre
                        ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'faltantescriteriodocentesdistributivo':
                try:
                    listadistributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo).order_by('profesor__persona_apellido1', 'profesor__persona_apellido2', 'profesor__persona_nombres')
                    listadocentessinevaluar = []
                    cont = 0
                    for lista in listadistributivo:
                        listalcriterios = []
                        if lista.detalledistributivo_set.filter(criteriodocenciaperiodo_id__isnull=False, status=True):
                            listahtml = ''
                            if not RubricaCriterioDocencia.objects.filter(Q(rubrica__para_hetero=True) | Q(rubrica__para_semestrevirtual=True), criterio_id__in=lista.detalledistributivo_set.values_list('criteriodocenciaperiodo_id').filter(criteriodocenciaperiodo_id__isnull=False, status=True)):
                                listahtml += "<ul class='list-group'>"
                                for lcriterios in lista.detalledistributivo_set.filter(criteriodocenciaperiodo_id__isnull=False, status=True):
                                    listahtml += "<li class='list-group-item'>" + lcriterios.criteriodocenciaperiodo.criterio.nombre + "</li>"
                                listahtml += "</ul>"
                                cont += 1
                                listadocentessinevaluar.append([cont, lista.profesor.persona.nombre_completo_inverso().__str__(), listalcriterios, listahtml])
                    data = {"results": "ok", 'listadoprofesores': listadocentessinevaluar}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'consulpromevalfacxls':
                try:
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_promedioevaluaciones.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('EVALUACIONXFACULTAD')
                    decimal_style = xlwt.XFStyle()
                    decimal_style.num_format_str = '0.00'
                    estilo1 = xlwt.easyxf('font: height 200, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 17, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.write_merge(3, 3, 4, 7, 'DOCENCIA', estilo1)
                    ws.write_merge(3, 3, 8, 11, 'INVESTIGACION', estilo1)
                    ws.write_merge(3, 3, 12, 15, 'GESTION', estilo1)
                    ws.write_merge(3, 3, 16, 19, 'VINCULACION', estilo1)
                    ws.write_merge(3, 3, 20, 21, 'COMPONENTE', estilo1)
                    ws.col(0).width = 1000
                    ws.col(1).width = 10000
                    ws.col(2).width = 10000
                    ws.col(3).width = 10000
                    ws.col(4).width = 7000
                    ws.col(5).width = 2000
                    ws.col(6).width = 2000
                    ws.col(7).width = 2000
                    ws.col(8).width = 2000
                    ws.col(9).width = 2000
                    ws.col(10).width = 2000
                    ws.col(11).width = 2000
                    ws.col(12).width = 2000
                    ws.col(13).width = 2000
                    ws.col(14).width = 2000
                    ws.col(15).width = 2000
                    ws.col(16).width = 2000
                    ws.col(17).width = 4000
                    ws.col(18).width = 4000
                    ws.write(4, 0, 'N.')
                    ws.write(4, 1, 'APELLIDOS Y NOMBRES DEL DOCENTE')
                    ws.write(4, 2, 'FACULTAD')
                    ws.write(4, 3, 'CARRERA')
                    ws.write(4, 4, 'TIPO')
                    ws.write(4, 5, 'Heter.')
                    ws.write(4, 6, 'Auto')
                    ws.write(4, 7, 'Par.')
                    ws.write(4, 8, 'Dire.')
                    ws.write(4, 9, 'Heter.')
                    ws.write(4, 10, 'Auto')
                    ws.write(4, 11, 'Par.')
                    ws.write(4, 12, 'Dire.')
                    ws.write(4, 13, 'Heter.')
                    ws.write(4, 14, 'Auto')
                    ws.write(4, 15, 'Par.')
                    ws.write(4, 16, 'Dire.')
                    ws.write(4, 17, 'Heter.')
                    ws.write(4, 18, 'Auto')
                    ws.write(4, 19, 'Par.')
                    ws.write(4, 20, 'Dire.')
                    ws.write(4, 21, 'Resultado Escala 1:5')
                    ws.write(4, 22, 'Resultado Escala 1:100')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    listado = ProfesorDistributivoHoras.objects.values_list('profesor__persona__apellido1', 'profesor__persona__apellido2',
                                                                            'profesor__persona__nombres', 'coordinacion__nombre',
                                                                            'carrera__nombre','carrera__mencion',
                                                                            'resumenfinalevaluacionacreditacion__promedio_docencia_hetero',
                                                                            'resumenfinalevaluacionacreditacion__promedio_docencia_auto',
                                                                            'resumenfinalevaluacionacreditacion__promedio_docencia_par',
                                                                            'resumenfinalevaluacionacreditacion__promedio_docencia_directivo',
                                                                            'resumenfinalevaluacionacreditacion__promedio_investigacion_hetero',
                                                                            'resumenfinalevaluacionacreditacion__promedio_investigacion_auto',
                                                                            'resumenfinalevaluacionacreditacion__promedio_investigacion_par',
                                                                            'resumenfinalevaluacionacreditacion__promedio_investigacion_directivo',
                                                                            'resumenfinalevaluacionacreditacion__promedio_gestion_hetero',
                                                                            'resumenfinalevaluacionacreditacion__promedio_gestion_auto',
                                                                            'resumenfinalevaluacionacreditacion__promedio_gestion_par',
                                                                            'resumenfinalevaluacionacreditacion__promedio_gestion_directivo',
                                                                            'resumenfinalevaluacionacreditacion__resultado_total',
                                                                            'coordinacion_id',
                                                                            'coordinacion_id',
                                                                            'resumenfinalevaluacionacreditacion__promedio_vinculacion_hetero',
                                                                            'resumenfinalevaluacionacreditacion__promedio_vinculacion_auto',
                                                                            'resumenfinalevaluacionacreditacion__promedio_vinculacion_par',
                                                                            'resumenfinalevaluacionacreditacion__promedio_vinculacion_directivo',
                                                                            'nivelcategoria__nombre'). \
                        filter(periodo_id=periodo.id, activoevaldocente=True, profesor__persona__real=True, status=True). \
                        exclude(coordinacion_id=9).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')

                    codigocarrera = request.GET.get('carr','')
                    if codigocarrera == '':
                        codigocarrera = 0
                    if int(codigocarrera) > 0:
                        listado = listado.filter(carrera_id=int(codigocarrera))
                    else:
                        if int(request.GET["idfacu"]) > 0:
                            listado = listado.filter(coordinacion_id=int(request.GET["idfacu"]))

                    for per in listado:
                        a += 1
                        ws.write(a, 0, a - 4)
                        ws.write(a, 1, per[0] + ' ' + per[1] + ' ' + per[2])
                        ws.write(a, 2, per[3])
                        ws.write(a, 3, per[4] if per[4] else '-' + ' ' + per[5] if per[5] else '')
                        ws.write(a, 4, per[25], decimal_style)
                        ws.write(a, 5, per[6], decimal_style)
                        ws.write(a, 6, per[7], decimal_style)
                        ws.write(a, 7, per[8], decimal_style)
                        ws.write(a, 8, per[9], decimal_style)
                        ws.write(a, 9, per[10], decimal_style)
                        ws.write(a, 10, per[11], decimal_style)
                        ws.write(a, 11, per[12], decimal_style)
                        ws.write(a, 12, per[13], decimal_style)
                        ws.write(a, 13, per[14], decimal_style)
                        ws.write(a, 14, per[15], decimal_style)
                        ws.write(a, 15, per[16], decimal_style)
                        ws.write(a, 16, per[17], decimal_style)
                        ws.write(a, 17, per[21], decimal_style)
                        ws.write(a, 18, per[22], decimal_style)
                        ws.write(a, 19, per[23], decimal_style)
                        ws.write(a, 20, per[24], decimal_style)
                        ws.write(a, 21, per[18], decimal_style)
                        ws.write(a, 22, round((per[18] * 100 / 5), 2), decimal_style)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'consulpromevalfacpdf':
                mensaje = "Problemas al generar el informe."
                try:
                    cursor = connection.cursor()
                    idproceso = int(proceso.id)
                    if int(request.GET["idfacu"]) == 0:
                        cursor.execute("select distinct per.apellido1,per.apellido2,per.nombres,CASE WHEN coor.nombre IS NULL THEN (select distinct coord.nombre from sga_coordinacion coord where pro.coordinacion_id=coord.id )ELSE coor.nombre END as facultad,CASE WHEN car.nombre IS NULL THEN '-' ELSE car.nombre END as nomcarrera, CASE WHEN car.mencion IS NULL THEN '-' ELSE CONCAT(' CON MENCION EN',car.mencion) END as mencarrera, ra.promedio_docencia_hetero,ra.promedio_docencia_auto,ra.promedio_docencia_par,ra.promedio_docencia_directivo,ra.promedio_investigacion_hetero,ra.promedio_investigacion_auto,ra.promedio_investigacion_par,ra.promedio_investigacion_directivo,ra.promedio_gestion_hetero,ra.promedio_gestion_auto,ra.promedio_gestion_par,ra.promedio_gestion_directivo,ra.resultado_total,round((ra.resultado_total*100/5),2) as escala, per.cedula from sga_profesordistributivohoras dh right join sga_detalledistributivo detdis on dh.id=detdis.distributivo_id left join sga_respuestaevaluacionacreditacion rea on dh.profesor_id=rea.profesor_id and rea.proceso_id= %s left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id left join sga_coordinacion coor on coor.id=dh.coordinacion_id left join sga_carrera car on car.id=dh.carrera_id left join sga_profesor pro on pro.id=dh.profesor_id left join sga_persona per on per.id=pro.persona_id where dh.periodo_id='" + request.GET["idper"] + "' and dh.activoevaldocente=True and dh.vercertificado=True and per.real=True order by 1", [idproceso])
                    else:
                        cursor.execute("select * from(select distinct per.apellido1,per.apellido2,per.nombres,CASE WHEN coor.nombre IS NULL THEN (select distinct coord.nombre from sga_coordinacion coord where pro.coordinacion_id=coord.id )ELSE coor.nombre END as facultad,CASE WHEN car.nombre IS NULL THEN '-' ELSE CONCAT(car.nombre,' ',car.mencion) END as nomcarrera,CASE WHEN car.mencion IS NULL THEN '-' ELSE CONCAT(' CON MENCION EN',car.mencion) END as mencarrera,ra.promedio_docencia_hetero,ra.promedio_docencia_auto,ra.promedio_docencia_par,ra.promedio_docencia_directivo,ra.promedio_investigacion_hetero,ra.promedio_investigacion_auto,ra.promedio_investigacion_par,ra.promedio_investigacion_directivo,ra.promedio_gestion_hetero,ra.promedio_gestion_auto,ra.promedio_gestion_par,ra.promedio_gestion_directivo,ra.resultado_total,round((ra.resultado_total*100/5),2) as escala, per.cedula, CASE WHEN coor.id IS NULL THEN (select distinct coord.id from sga_coordinacion coord where pro.coordinacion_id=coord.id ) ELSE coor.id END as idfacultad from sga_profesordistributivohoras dh right join sga_detalledistributivo detdis on dh.id=detdis.distributivo_id left join sga_respuestaevaluacionacreditacion rea on dh.profesor_id=rea.profesor_id and rea.proceso_id= %s left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id left join sga_coordinacion coor on coor.id=dh.coordinacion_id left join sga_carrera car on car.id=dh.carrera_id left join sga_profesor pro on pro.id=dh.profesor_id left join sga_persona per on per.id=pro.persona_id where dh.periodo_id='" + request.GET["idper"] + "' and dh.activoevaldocente=True and dh.vercertificado=True and per.real=True order by 1 ) as d where idfacultad='" + request.GET["idfacu"] + "'", [idproceso])
                    results = cursor.fetchall()
                    distributivopersona = DistributivoPersona.objects.filter(denominacionpuesto__id=470, estadopuesto__id=PUESTO_ACTIVO_ID)
                    if distributivopersona:
                        distributivopersona = distributivopersona[0]
                    return download_html_to_pdf('adm_evaluaciondocentesacreditacion/informe_evaluacion_promedio_pdf.html',
                                                {'pagesize': 'A4', 'promedioevaluaciones': results, 'periodo': periodo,
                                                 'distributivopersona': distributivopersona, 'hoy': datetime.now(), 'totalregistro': results.__len__()})
                except Exception as ex:
                    return HttpResponseRedirect("/adm_evaluaciondocentesacreditacion?info=%s" % mensaje)

            elif action == 'consulrubparesexcel':
                try:
                    data['title'] = u'Detallado de resultados Evaluación por Pares'
                    idproceso = int(proceso.id)
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_alumnos.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 1000
                    ws.col(1).width = 6000
                    ws.col(2).width = 3000
                    ws.col(3).width = 3000
                    ws.col(4).width = 3000
                    ws.col(5).width = 6000
                    ws.col(6).width = 6000
                    ws.col(7).width = 6000
                    ws.col(8).width = 6000
                    ws.col(9).width = 6000
                    ws.col(10).width = 6000
                    ws.col(11).width = 1000
                    ws.col(12).width = 1000
                    ws.col(13).width = 1000
                    ws.write(4, 0, 'N.')
                    ws.write(4, 1, 'DOCENTE')
                    ws.write(4, 2, '1.1')
                    ws.write(4, 3, '1.2')
                    ws.write(4, 4, '1.3')
                    ws.write(4, 5, '2')
                    ws.write(4, 6, '3')
                    ws.write(4, 7, '4')
                    ws.write(4, 8, '5')
                    ws.write(4, 9, '6')
                    ws.write(4, 10, '7')
                    ws.write(4, 11, '8')
                    ws.write(4, 12, '9')
                    ws.write(4, 13, '10')
                    a = 4
                    cursor.execute("select distinct per.apellido1 , per.apellido2,per.nombres, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 1.1' and tipo_criterio=1 then drr.valor end),2) rdoc11, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 1.2' and tipo_criterio=1 then drr.valor end),2) rdoc12, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 1.3' and tipo_criterio=1 then drr.valor end),2) rdoc13, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 2' and tipo_criterio=1 then drr.valor end),2) rdoc2, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 3' and tipo_criterio=1 then drr.valor end),2) rdoc3, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 4' and tipo_criterio=1 then drr.valor end),2) rdoc4, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 5' and tipo_criterio=1 then drr.valor end),2) rdoc5, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 6' and tipo_criterio=1 then drr.valor end),2) rdoc6, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 7' and tipo_criterio=1 then drr.valor end),2) rdoc7, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 8' and tipo_criterio=1 then drr.valor end),2) rdoc8, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 9' and tipo_criterio=1 then drr.valor end),2) rdoc9, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 10' and tipo_criterio=1 then drr.valor end),2) rdoc10, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 1' and tipo_criterio=2 then drr.valor end),2) rinve1, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 2' and tipo_criterio=2 then drr.valor end),2) rinve2, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 3' and tipo_criterio=2 then drr.valor end),2) rinve3, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 4' and tipo_criterio=2 then drr.valor end),2) rinve4, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 1' and tipo_criterio=3 then drr.valor end),2) rgest1, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 2' and tipo_criterio=3 then drr.valor end),2) rgest2, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 3' and tipo_criterio=3 then drr.valor end),2) rgest3, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 4' and tipo_criterio=3 then drr.valor end),2) rgest4, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 5' and tipo_criterio=3 then drr.valor end),2) rgest5, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 6' and tipo_criterio=3 then drr.valor end),2) rgest6, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 7' and tipo_criterio=3 then drr.valor end),2) rgest7, "
                                   "round(avg(case when substring(ru.nombre,3,12) = 'BRICA 8' and tipo_criterio=3 then drr.valor end),2) rgest8 "
                                   "from sga_respuestaevaluacionacreditacion rea , sga_respuestarubrica rr, "
                                   "sga_rubrica ru, sga_rubricapreguntas rp, "
                                   "sga_preguntacaracteristicaevaluacionacreditacion rpe, "
                                   "sga_textopreguntaacreditacion txta,sga_profesor pro,sga_persona per, "
                                   "sga_detallerespuestarubrica drr "
                                   "where rea.profesor_id=pro.id and pro.persona_id=per.id "
                                   "and rea.proceso_id=%s and rea.tipoinstrumento=3 and rr.respuestaevaluacion_id=rea.id "
                                   "and rr.rubrica_id=ru.id and ru.proceso_id=%s and ru.para_par=true "
                                   "and rp.rubrica_id=ru.id and rp.preguntacaracteristica_id=rpe.id "
                                   "and rpe.pregunta_id=txta.id and drr.respuestarubrica_id=rr.id and ru.informativa=false "
                                   "group by per.apellido1,per.apellido2,per.nombres;", [idproceso, idproceso])
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, a - 4)
                        ws.write(a, 1, per[0] + ' ' + per[1] + ' ' + per[2])
                        ws.write(a, 2, per[4])
                        ws.write(a, 3, per[5])
                        ws.write(a, 4, per[6])
                        ws.write(a, 5, per[7])
                        ws.write(a, 6, per[8])
                        ws.write(a, 7, per[9])
                        ws.write(a, 8, per[10])
                        ws.write(a, 9, per[11])
                        ws.write(a, 10, per[12])
                        ws.write(a, 11, per[13])
                        ws.write(a, 12, per[14])
                        ws.write(a, 13, per[15])
                    data['distributivos'] = results
                    ws.write_merge(a + 2, a + 2, 0, 1)
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'resultados_generales_coordinacion':
                try:
                    data['title'] = u'Resultados de evaluación docente por facultades'
                    data['coordinaciones'] = Coordinacion.objects.all()
                    return render(request, "adm_evaluaciondocentesacreditacion/resultados_generales_coordinacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'resultados_matriz_evaluacion':
                try:
                    data['title'] = u'Resultados de matriz de evaluación'
                    evaluacion = RespuestaEvaluacionAcreditacion.objects.values_list('carrera_id').filter(proceso=proceso, tipoinstrumento=1).distinct()
                    coordinacionevaluacion = RespuestaEvaluacionAcreditacion.objects.values_list('coordinacion_id').filter(proceso=proceso, tipoinstrumento=2).distinct()
                    data['carreras'] = Carrera.objects.filter(pk__in=evaluacion,status=True).order_by('nombre')
                    data['coordinaciones'] = Coordinacion.objects.filter(pk__in=coordinacionevaluacion,status=True).order_by('nombre')
                    coordinacionespares = DetalleInstrumentoEvaluacionParAcreditacion.objects.values_list('coordinacion_id').filter(proceso=proceso,status=True).distinct()
                    coordinacionesdirectivos = DetalleInstrumentoEvaluacionDirectivoAcreditacion.objects.values_list('coordinacion_id').filter(proceso=proceso,status=True).distinct()
                    data['coordinacionespares'] = Coordinacion.objects.filter(pk__in=coordinacionespares, status=True).order_by('nombre')
                    data['coordinacionesdirectivos'] = Coordinacion.objects.filter(pk__in=coordinacionesdirectivos, status=True).order_by('nombre')
                    return render(request, "adm_evaluaciondocentesacreditacion/resultados_matriz_evaluacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletecriterios':
                try:
                    data['title'] = u'Eliminar categoría'
                    data['criterio'] = TipoObservacionEvaluacion.objects.get(pk=request.GET['idcriterio'])
                    return render(request, "adm_evaluaciondocentesacreditacion/deletecriterios.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteresponsable':
                try:
                    data['title'] = u'Eliminar Responsable'
                    data['participante'] = ResponsableEvaluacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_evaluaciondocentesacreditacion/deleteresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletetipocriterios':
                try:
                    data['title'] = u'Eliminar tipo categoría'
                    data['tipocriterio'] = CriterioTipoObservacionEvaluacion.objects.get(pk=request.GET['idtipocriterio'])
                    return render(request, "adm_evaluaciondocentesacreditacion/deletetipocriterios.html", data)
                except Exception as ex:
                    pass

            elif action == 'consulcriterios':
                try:
                    data['title'] = u'Categorías'
                    data['idperiodo'] = request.GET['idperiodo']
                    search = None
                    ids = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        periodo = TipoObservacionEvaluacion.objects.filter(pk=ids)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            periodo = TipoObservacionEvaluacion.objects.select_related().filter(pk=search, status=True)
                        else:
                            periodo = TipoObservacionEvaluacion.objects.select_related().filter(
                                Q(nombre__icontains=search) , status=True).order_by('tipoinstrumento', 'tipo',
                                                                                    'tipocriterio__nombre',
                                                                                    'nombre')
                    else:
                        tipo = TipoObservacionEvaluacion.objects.filter(status=True).order_by('tipoinstrumento', 'tipo', 'tipocriterio__nombre', 'nombre')
                    paging = MiPaginador(tipo, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['tiposcriterios'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_evaluaciondocentesacreditacion/tiposcriterios.html", data)
                except Exception as ex:
                    pass

            elif action == 'responsableevaluacion':
                try:
                    data['title'] = u'Responsable de Evaluación'
                    data['responsables'] = ResponsableEvaluacion.objects.filter(status=True).order_by('id')
                    return render(request, "adm_evaluaciondocentesacreditacion/responsableevaluacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addresponsable':
                try:
                    data['title'] = u'Responsable de Evaluación'
                    data['form'] = ResponsableEvaluacionFrom
                    return render(request, "adm_evaluaciondocentesacreditacion/addresponsable.html", data)
                except Exception as ex:
                    pass

            elif action == 'consultipocriterios':
                try:
                    data['title'] = u'Tipos Categorías'
                    data['periodo'] = periodo
                    data['listacriterios'] = CriterioTipoObservacionEvaluacion.objects.filter(status=True).order_by('nombre')
                    return render(request, "adm_evaluaciondocentesacreditacion/consultipocriterios.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcategoria':
                try:
                    data['title'] = u'Editar Categorías'
                    data['categoria'] = categoria = TipoObservacionEvaluacion.objects.get(pk=request.GET['id'])
                    form = TipoCategoriasForm(initial={'nombre': categoria.nombre,
                                                       'tipo': categoria.tipo,
                                                       'tipoinstrumento': categoria.tipoinstrumento,
                                                       'tipocriterio': categoria.tipocriterio})
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/editcategoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittipocategoria':
                try:
                    data['title'] = u'Editar Tipo Categorías'
                    data['tipocategoria'] = tipocategoria = CriterioTipoObservacionEvaluacion.objects.get(pk=request.GET['id'])
                    form = TipoCategoriasCriteriosForm(initial={'nombre': tipocategoria.nombre})
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/edittipocategoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcategoria':
                try:
                    data['title'] = u'Adicionar Categoria'
                    data['periodo'] = periodo
                    form = TipoCategoriasForm()
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/addcategoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipocategoria':
                try:
                    data['title'] = u'Adicionar Tipo Categoria'
                    data['periodo'] = periodo
                    form = TipoCategoriasCriteriosForm()
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/addtipocategoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'resultados_generales_coordinacion_grafico':
                try:
                    data['title_docencia'] = u'Resultados de evaluación docente por facultades (DOCENCIA)'
                    data['title_investigacion'] = u'Resultados de evaluación docente por facultades (INVESTIGACION)'
                    data['title_gestion'] = u'Resultados de evaluación docente por facultades (GESTION)'
                    data['coordinaciones'] = coordinaciones = Coordinacion.objects.all()[:4]
                    lista_hetero_docencia = []
                    lista_auto_docencia = []
                    lista_par_docencia = []
                    lista_directivo_docencia = []
                    lista_hetero_investigacion = []
                    lista_auto_investigacion = []
                    lista_par_investigacion = []
                    lista_directivo_investigacion = []
                    lista_hetero_gestion = []
                    lista_auto_gestion = []
                    lista_par_gestion = []
                    lista_directivo_gestion = []
                    for coordinacion in coordinaciones:
                        lista_hetero_docencia.append(coordinacion.promedio_estudiantes_docencia(periodo))
                        lista_auto_docencia.append(coordinacion.promedio_autoevaluacion_docencia(periodo))
                        lista_par_docencia.append(coordinacion.promedio_par_docencia(periodo))
                        lista_directivo_docencia.append(coordinacion.promedio_directivo_docencia(periodo))
                        lista_hetero_investigacion.append(coordinacion.promedio_estudiantes_investigacion(periodo))
                        lista_auto_investigacion.append(coordinacion.promedio_autoevaluacion_investigacion(periodo))
                        lista_par_investigacion.append(coordinacion.promedio_par_investigacion(periodo))
                        lista_directivo_investigacion.append(coordinacion.promedio_directivo_investigacion(periodo))
                        lista_hetero_gestion.append(coordinacion.promedio_estudiantes_gestion(periodo))
                        lista_auto_gestion.append(coordinacion.promedio_autoevaluacion_gestion(periodo))
                        lista_par_gestion.append(coordinacion.promedio_par_gestion(periodo))
                        lista_directivo_gestion.append(coordinacion.promedio_directivo_gestion(periodo))
                    data['lista_hetero_docencia'] = lista_hetero_docencia
                    data['lista_auto_docencia'] = lista_auto_docencia
                    data['lista_par_docencia'] = lista_par_docencia
                    data['lista_directivo_docencia'] = lista_directivo_docencia
                    data['lista_hetero_investigacion'] = lista_hetero_investigacion
                    data['lista_auto_investigacion'] = lista_auto_investigacion
                    data['lista_par_investigacion'] = lista_par_investigacion
                    data['lista_directivo_investigacion'] = lista_directivo_investigacion
                    data['lista_hetero_gestion'] = lista_hetero_gestion
                    data['lista_auto_gestion'] = lista_auto_gestion
                    data['lista_par_gestion'] = lista_par_gestion
                    data['lista_directivo_gestion'] = lista_directivo_gestion
                    return render(request, "adm_evaluaciondocentesacreditacion/resultados_generales_coordinacion_grafico.html", data)
                except Exception as ex:
                    pass

            elif action == 'resultados_generales_carrera':
                try:
                    data['title'] = u'Resultados de evaluación docente por carreras'
                    data['carreras'] = Carrera.objects.filter(activa=True)
                    return render(request, "adm_evaluaciondocentesacreditacion/resultados_generales_carrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'resultados_docentes_coordinacion':
                try:
                    data['title'] = u'Resultados de evaluación por docentes y tipos de intrumentos por facultades'
                    data['coordinaciones'] = coordinaciones = Coordinacion.objects.all()
                    if 'idc' in request.GET:
                        data['coordinacion'] = coordinacion = coordinaciones.filter(id=int(request.GET['idc']))[0]
                        data['idc'] = int(request.GET['idc'])
                    else:
                        data['coordinacion'] = coordinacion = coordinaciones[0]
                        data['idc'] = coordinaciones[0].id
                    if 'idcriterio' in request.GET:
                        data['idcriterio'] = int(request.GET['idcriterio'])
                    else:
                        data['idcriterio'] = 1
                    data['profesores'] = Profesor.objects.filter(Q(profesormateria__materia__nivel__periodo=periodo, profesormateria__principal=True, profesormateria__materia__nivel__nivellibrecoordinacion__coordinacion=coordinacion) |
                                                                 Q(Q(profesordistributivohoras__horasdocencia__gt=0) |
                                                                   Q(profesordistributivohoras__horasinvestigacion__gt=0) |
                                                                   Q(profesordistributivohoras__horasgestion__gt=0)), coordinacion=coordinacion, persona__real=True).distinct()
                    return render(request, "adm_evaluaciondocentesacreditacion/resultados_docentes_coordinacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'consultacarreras':
                if not request.user.has_perm('sga.puede_visible_periodo'):
                    if not request.session['periodo'].visible:
                        return HttpResponseRedirect("/?info=Periodo Inactivo.")
                r = False
                data['title'] = u'Niveles académicos'
                data['periodo'] = request.session['periodo']
                data['coordinaciones'] = persona.mis_coordinaciones()
                return render(request, "adm_evaluaciondocentesacreditacion/viewcoordinaciones.html", data)

            elif action == 'materias':
                try:
                    data['title'] = u'Materias del nivel académico'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    carreras = persona.mis_carreras()
                    # carreras = carreras.filter(id__in=nivel.coordinacion().carrera.all())
                    carreras = Carrera.objects.filter(id__in=nivel.coordinacion().carrera.all())
                    # mallas = Malla.objects.filter(carrera__in=carreras).distinct()
                    materiasn = nivel.materia_set.values_list('asignaturamalla__malla__carrera_id').filter(asignaturamalla__malla__carrera__in=carreras,status=True).distinct()
                    mallas = Malla.objects.filter(carrera__in=materiasn).distinct()
                    malla = None
                    nivelmalla = None
                    if 'mallaid' in request.GET:
                        malla = mallas.get(pk=int(request.GET['mallaid']))
                    else:
                        if mallas.exists():
                            malla = mallas[0]
                    if MATRICULACION_LIBRE:
                        paraleloid = '0'
                        finieval = ''
                        ffineval = ''
                        if 'paraleloid' in request.GET:
                            paraleloid = request.GET['paraleloid']
                        data['paraleloid'] = paraleloid
                        if 'finieval' in request.GET:
                            finieval = request.GET['finieval']
                        data['finieval'] = finieval
                        if 'ffineval' in request.GET:
                            ffineval = request.GET['ffineval']
                        data['ffineval'] = ffineval
                        data['malla'] = malla
                        data['mallaid'] = malla.id if malla else 0
                        if 'nivelmallaid' in request.GET and int(request.GET['nivelmallaid']) > 0:
                            nivelmalla = NivelMalla.objects.get(pk=int(request.GET['nivelmallaid']))
                            data['nivelmalla'] = nivelmalla
                            data['nivelmallaid'] = nivelmalla.id if nivelmalla else ""
                        if nivelmalla:
                            if paraleloid == '0':
                                if finieval == '':
                                    materias = nivel.materia_set.filter(asignaturamalla__malla=malla, asignaturamalla__nivelmalla=nivelmalla).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
                                else:
                                    materias = nivel.materia_set.filter(inicio__gte=finieval,fin__lte=ffineval,asignaturamalla__malla=malla, asignaturamalla__nivelmalla=nivelmalla).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
                            else:
                                materias = nivel.materia_set.filter(asignaturamalla__malla=malla, paralelo=paraleloid, asignaturamalla__nivelmalla=nivelmalla).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
                        else:
                            if paraleloid == '0':
                                if finieval == '':
                                    materias = nivel.materia_set.filter(asignaturamalla__malla=malla).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
                                else:
                                    materias = nivel.materia_set.filter(inicio__gte=finieval,fin__lte=ffineval,asignaturamalla__malla=malla).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion','id')
                            else:
                                materias = nivel.materia_set.filter(asignaturamalla__malla=malla, paralelo=paraleloid).order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
                        data['materias'] = materias
                        data['mallas'] = mallas
                    else:
                        data['materias'] = materias = nivel.materia_set.all().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
                    data['bloqueado'] = nivel.bloqueado() and not persona.usuario.groups.filter(id__in=[143])
                    data['nivelesmalla'] = NivelMalla.objects.all()
                    data['nobloqueadocupos'] = nivel.extension().puedematricular
                    data['nobloqueadodocente'] = nivel.extension().modificardocente if MATRICULACION_LIBRE else True
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['cupo_por_materia'] = CUPO_POR_MATERIA
                    data['usa_evaluacion_integral'] = USA_EVALUACION_INTEGRAL
                    data['TIPO_DOCENTE_PRACTICA'] = TIPO_DOCENTE_PRACTICA
                    data['paralelos'] = Paralelo.objects.filter(nombre__in=nivel.materia_set.values_list('paralelo', flat=True).filter(status=True, asignaturamalla__malla=malla).distinct(), status=True)
                    data['eEncuestasSatisfaccion'] = EncuestaSatisfaccionDocente.objects.filter(status=True).order_by('id')
                    return render(request, "adm_evaluaciondocentesacreditacion/materias.html", data)
                except Exception as ex:
                    pass

            elif action == 'resultados_docentes_carrera':
                try:
                    data['title'] = u'Resultados de evaluación por docentes y tipos de intrumentos por carreras'
                    data['carreras'] = carreras = Carrera.objects.filter(activa=True)
                    if 'idc' in request.GET:
                        data['carrera'] = carrera = carreras.filter(id=int(request.GET['idc']))[0]
                        data['idc'] = int(request.GET['idc'])
                    else:
                        data['carrera'] = carrera = carreras[0]
                        data['idc'] = carreras[0].id
                    if 'idcriterio' in request.GET:
                        data['idcriterio'] = int(request.GET['idcriterio'])
                    else:
                        data['idcriterio'] = 1
                    data['profesores'] = Profesor.objects.filter(profesormateria__materia__nivel__periodo=periodo, profesormateria__principal=True, profesormateria__materia__asignaturamalla__malla__carrera=carrera).distinct()
                    return render(request, "adm_evaluaciondocentesacreditacion/resultados_docentes_carrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleautoxevaluar':
                try:
                    # proceso = periodo.proceso_evaluativoacreditacion()
                    # data['profesordh'] = proceso.auto_sin_realizar()
                    data['profesordh'] = True
                    data['admisionpresencial'] = proceso.auto_sin_realizar_admision(1)
                    data['admisionenlinea'] = proceso.auto_sin_realizar_admision(3)
                    data['semestrepresencial'] = proceso.auto_sin_realizar_semestre(1)
                    data['semestreenlinea'] = proceso.auto_sin_realizar_semestreenlinea(3)
                    data['docentessinmaterias'] = proceso.auto_sin_realizar_docsinmateria()
                    template = get_template("adm_evaluaciondocentesacreditacion/detallexevaluar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'auto_sin_realizar_admision':
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 15000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INST", 10000),
                        (u"COORDINACION", 10000),
                        (u"CARRERA", 15000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    modalidad = int(request.GET['modalidad'])
                    yaevaluaron = RespuestaEvaluacionAcreditacion.objects.values_list('profesor_id').filter(proceso__periodo=proceso.periodo, tipoinstrumento=2)
                    listadoprofesores = Profesor.objects.filter(profesormateria__materia__nivel__periodo=proceso.periodo, profesormateria__materia__status=True, profesormateria__materia__nivel__modalidad_id=modalidad, profesormateria__materia__asignaturamalla__malla__carrera__coordinacion=9).distinct().exclude(pk__in=yaevaluaron).order_by('persona__apellido1','persona__apellido2')
                    row_num = 4
                    for lista in listadoprofesores:
                        i = 0
                        campo1 = lista.persona.cedula
                        campo2 = lista.persona.nombre_completo_inverso().__str__()
                        campo3 = lista.persona.email
                        campo4 = lista.persona.emailinst
                        campo5 = ''
                        campo6 = ''
                        if lista.profesordistributivohoras_set.filter(periodo=proceso.periodo, status=True):
                            distri = lista.profesordistributivohoras_set.filter(periodo=proceso.periodo, status=True)[0]
                            if distri.coordinacion:
                                campo5 = distri.coordinacion.nombre
                            if distri.carrera:
                                campo6 = distri.carrera.nombre
                        if distri.coordinacion:
                            campo5 = distri.coordinacion.nombre
                        if distri.carrera:
                            campo6 = distri.carrera.nombre
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

            elif action == 'auto_sin_realizar_semestre':
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 15000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INST", 10000),
                        (u"COORDINACION", 10000),
                        (u"CARRERA", 15000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    yaevaluaron = RespuestaEvaluacionAcreditacion.objects.values_list('profesor_id').filter(proceso__periodo=proceso.periodo, tipoinstrumento=2)
                    listadoprofesores = ProfesorMateria.objects.values_list('profesor_id').filter(materia__nivel__periodo=proceso.periodo, materia__nivel__modalidad_id__in=[1, 2], profesor__persona__real=True).distinct().exclude(profesor_id__in=yaevaluaron).exclude(materia__asignaturamalla__malla__carrera__coordinacion=9)
                    row_num = 4
                    for lista in listadoprofesores:
                        i = 0
                        profe = Profesor.objects.get(pk=lista[0])
                        campo1 = profe.persona.cedula
                        campo2 = profe.persona.nombre_completo_inverso().__str__()
                        campo3 = profe.persona.email
                        campo4 = profe.persona.emailinst
                        campo5 = ''
                        campo6 = ''
                        if profe.profesordistributivohoras_set.filter(periodo=proceso.periodo, status=True):
                            distri = profe.profesordistributivohoras_set.filter(periodo=proceso.periodo, status=True)[0]
                            if distri.coordinacion:
                                campo5 = distri.coordinacion.nombre
                            if distri.carrera:
                                campo6 = distri.carrera.nombre
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

            elif action == 'auto_sin_realizar_semestreenlinea':
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 15000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INST", 10000),
                        (u"COORDINACION", 10000),
                        (u"CARRERA", 15000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    yaevaluaron = RespuestaEvaluacionAcreditacion.objects.values_list('profesor_id').filter(proceso__periodo=proceso.periodo, tipoinstrumento=2)
                    listadoprofesores = ProfesorMateria.objects.values_list('profesor_id').filter(materia__nivel__periodo=proceso.periodo,materia__nivel__modalidad_id=3, profesor__persona__real=True).distinct().exclude(profesor_id__in=yaevaluaron).exclude(materia__asignaturamalla__malla__carrera__coordinacion=9)
                    row_num = 4
                    for lista in listadoprofesores:
                        profe = Profesor.objects.get(pk=lista[0])
                        i = 0
                        campo1 = profe.persona.cedula
                        campo2 = profe.persona.nombre_completo_inverso().__str__()
                        campo3 = profe.persona.email
                        campo4 = profe.persona.emailinst
                        campo5 = ''
                        campo6 = ''
                        if profe.profesordistributivohoras_set.filter(periodo=proceso.periodo, status=True):
                            distri = profe.profesordistributivohoras_set.filter(periodo=proceso.periodo, status=True)[0]
                            if distri.coordinacion:
                                campo5 = distri.coordinacion.nombre
                            if distri.carrera:
                                campo6 = distri.carrera.nombre
                        if distri.coordinacion:
                            campo5 = distri.coordinacion.nombre
                        if distri.carrera:
                            campo6 = distri.carrera.nombre
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

            elif action == 'auto_sin_realizar_docsinmateria':
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
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 15000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INST", 10000),
                        (u"COORDINACION", 10000),
                        (u"CARRERA", 15000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    yaevaluaron = RespuestaEvaluacionAcreditacion.objects.values_list('profesor_id').filter(proceso__periodo=proceso.periodo, tipoinstrumento=2)
                    listadoprofesormateria = ProfesorMateria.objects.values_list('profesor_id').filter(materia__nivel__periodo=proceso.periodo, profesor__persona__real=True).distinct().exclude(materia__asignaturamalla__malla__carrera__coordinacion=9)
                    listadoprofesores = ProfesorDistributivoHoras.objects.filter(periodo=proceso.periodo, profesor__persona__real=True, status=True).exclude(profesor_id__in=listadoprofesormateria).exclude(profesor_id__in=yaevaluaron)
                    row_num = 4
                    for lista in listadoprofesores:
                        i = 0
                        campo1 = lista.profesor.persona.cedula
                        campo2 = lista.profesor.persona.nombre_completo_inverso().__str__()
                        campo3 = lista.profesor.persona.email
                        campo4 = lista.profesor.persona.emailinst
                        campo5 = ''
                        campo6 = ''
                        if lista.coordinacion:
                            campo5 = lista.coordinacion.nombre
                        if lista.carrera:
                            campo6 = lista.carrera.nombre
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

            elif action == 'detalledirxevaluar':
                try:
                    data['title'] = u'Coevaluación'
                    data['directivos'] = proceso.dir_sin_realizar()
                    template = get_template("adm_evaluaciondocentesacreditacion/detallexevaluar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detalleparesxevaluar':
                try:
                    data['title'] = u'Coevaluación'
                    data['pares'] = proceso.par_sin_realizar()
                    template = get_template("adm_evaluaciondocentesacreditacion/detallexevaluar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cronogramaencuesta':
                try:
                    data['title'] = u'Cronograma de encuesta'
                    search = None
                    ids = None
                    cronogramasencuestas = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        cronogramasencuestas = CronogramaEncuestaProcesoEvaluativo.objects.filter(pk=ids, periodo=periodo, status=True)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            cronogramasencuestas = CronogramaEncuestaProcesoEvaluativo.objects.filter(pk=search, periodo=periodo, status=True)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    cronogramasencuestas = CronogramaEncuestaProcesoEvaluativo.objects.filter(Q(nombre__icontains=s[0]), Q(status=True), Q(periodo=periodo))
                                elif len(s) == 2:
                                    cronogramasencuestas = CronogramaEncuestaProcesoEvaluativo.objects.filter(Q(nombre__icontains=s[0]), Q(nombre__icontains=s[1]), Q(periodo=periodo), Q(status=True))
                                elif len(s) == 3:
                                    cronogramasencuestas = CronogramaEncuestaProcesoEvaluativo.objects.filter(Q(nombre__icontains=s[0]), Q(nombre__icontains=s[1]), Q(nombre__icontains=s[2]), Q(periodo=periodo), Q(status=True))
                    else:
                        cronogramasencuestas = CronogramaEncuestaProcesoEvaluativo.objects.filter(status=True)
                    paging = MiPaginador(cronogramasencuestas, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['cronogramasencuestas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_evaluaciondocentesacreditacion/viewcronogramaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcronogramaencuesta':
                try:
                    data['title'] = u'Adicionar cronograma de encuesta'
                    form = CronogramaEncuestaProcesoEvaluativoForm()
                    form.cargar_niveles(periodo)
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/addcronogramaencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcronogramaencuesta':
                try:
                    data['title'] = u'Editar cronograma de encuesta'
                    data['cronogramaencuesta'] = cronograma = CronogramaEncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CronogramaEncuestaProcesoEvaluativoForm(initial={'fechainicio': cronograma.fechainicio,
                                                                            'fechafin': cronograma.fechafin,
                                                                            'nombre': cronograma.nombre,
                                                                            'niveles': Nivel.objects.filter(status=True, pk__in=cronograma.cronograma_nivel().values_list('nivel__id'))})
                    form.cargar_niveles(cronograma.periodo)
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/editcronogramaencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcronogramaencuesta':
                try:
                    data['title'] = u'Eliminar cronograma de encuesta'
                    data['cronogramaencuesta'] = CronogramaEncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "adm_evaluaciondocentesacreditacion/delcronogramaencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'encuesta':
                try:
                    data['title'] = u'Encuesta'
                    search = None
                    ids = None
                    encuestas = None
                    data['cronogramaencuesta'] = cronogramaencuesta = CronogramaEncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])))
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            encuestas = cronogramaencuesta.encuestaprocesoevaluativo_set.filter(pk=search, status=True)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    encuestas = cronogramaencuesta.encuestaprocesoevaluativo_set.filter(Q(titulo__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    encuestas = cronogramaencuesta.encuestaprocesoevaluativo_set.filter(Q(titulo__icontains=s[0]), Q(titulo__icontains=s[1]), Q(status=True))
                                elif len(s) == 3:
                                    encuestas = cronogramaencuesta.encuestaprocesoevaluativo_set.filter(Q(titulo__icontains=s[0]), Q(titulo__icontains=s[1]), Q(titulo__icontains=s[2]), Q(status=True))
                    else:
                        encuestas = cronogramaencuesta.encuestaprocesoevaluativo_set.filter(status=True)
                    paging = MiPaginador(encuestas, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['encuestas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_evaluaciondocentesacreditacion/viewencuestaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addencuesta':
                try:
                    data['title'] = u'Adicionar encuesta'
                    data['cronogramaencuesta'] = cronogramaencuesta = CronogramaEncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = EncuestaProcesoEvaluativoForm(initial={'cronogramaencuesta': cronogramaencuesta})
                    form.deshabilitar_cronograma()
                    form.cargar_carrera(cronogramaencuesta)
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/addencuestaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editencuesta':
                try:
                    data['title'] = u'Editar encuesta'
                    data['encuesta'] = encuesta = EncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = EncuestaProcesoEvaluativoForm(initial={'titulo': encuesta.titulo,
                                                                  'cronogramaencuesta': encuesta.cronogramaencuesta,
                                                                  'fechainicio': encuesta.fechainicio,
                                                                  'fechafin': encuesta.fechafin,
                                                                  'estudiante': encuesta.estudiante,
                                                                  'profesor': encuesta.profesor,
                                                                  'activo': encuesta.activo,
                                                                  'encuestaobligatoria': encuesta.encuestaobligatoria,
                                                                  'carrera': Carrera.objects.filter(pk__in=encuesta.encuesta_carreras().values_list('carrera__id', flat=True), activa=True, status=True)})
                    form.deshabilitar_cronograma()
                    form.cargar_carrera(encuesta.cronogramaencuesta)
                    data['form'] = form
                    return render(request, "adm_evaluaciondocentesacreditacion/editencuestaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delencuesta':
                try:
                    data['title'] = u'Eliminar encuesta'
                    data['encuesta'] = EncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "adm_evaluaciondocentesacreditacion/delencuestaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'preguntaproceso':
                try:
                    data['title'] = u'Pregunta'
                    search = None
                    ids = None
                    preguntas = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        preguntas = PreguntaProcesoEvaluativo.objects.filter(pk=ids, status=True)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            preguntas = PreguntaProcesoEvaluativo.objects.filter(pk=search, status=True)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    preguntas = PreguntaProcesoEvaluativo.objects.filter(Q(nombre__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    preguntas = PreguntaProcesoEvaluativo.objects.filter(Q(nombre__icontains=s[0]), Q(nombre__icontains=s[1]), Q(status=True))
                                elif len(s) == 3:
                                    preguntas = PreguntaProcesoEvaluativo.objects.filter(Q(nombre__icontains=s[0]), Q(nombre__icontains=s[1]), Q(nombre__icontains=s[2]), Q(status=True))
                    else:
                        preguntas = PreguntaProcesoEvaluativo.objects.filter(status=True)
                    paging = MiPaginador(preguntas, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['preguntas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_evaluaciondocentesacreditacion/viewpreguntaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpreguntaproceso':
                try:
                    data['title'] = u'Adicionar pregunta'
                    data['form'] = PreguntaProcesoEvaluativoForm()
                    return render(request, "adm_evaluaciondocentesacreditacion/addpreguntaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpreguntaproceso':
                try:
                    data['title'] = u'Editar pregunta'
                    data['pregunta'] = pregunta = PreguntaProcesoEvaluativo.objects.get( pk=int(encrypt(request.GET['id'])))
                    data['form'] = PreguntaProcesoEvaluativoForm(initial={'nombre': pregunta.nombre, 'activo': pregunta.activo})
                    return render(request, "adm_evaluaciondocentesacreditacion/editpreguntaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delpreguntaproceso':
                try:
                    data['title'] = u'Eliminar pregunta'
                    data['pregunta'] = PreguntaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "adm_evaluaciondocentesacreditacion/delpreguntaprocesoevaluativo.html", data)
                except Exception as ex:
                    pass

            # PREGUNTAS DE ENCUESTAS
            elif action == 'preguntaencuesta':
                try:
                    data['title'] = u'Preguntas de encuesta'
                    search = None
                    ids = None
                    preguntasencuesta = None
                    data['encuesta'] = encuesta = EncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            preguntasencuesta = encuesta.encuestaprocesoevaluativo_pregunta_set.filter(pk=search, status=True)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    preguntasencuesta = encuesta.encuestaprocesoevaluativo_pregunta_set.filter(Q(nombre__icontains=s[0]), Q(status=True))
                                elif len(s) == 2:
                                    preguntasencuesta = encuesta.encuestaprocesoevaluativo_pregunta_set.filter(Q(nombre__icontains=s[0]), Q(nombre__icontains=s[1]), Q(status=True))
                                elif len(s) == 3:
                                    preguntasencuesta = encuesta.encuestaprocesoevaluativo_pregunta_set.filter(Q(nombre__icontains=s[0]), Q(nombre__icontains=s[1]), Q(nombre__icontains=s[2]), Q(status=True))
                    else:
                        preguntasencuesta = encuesta.encuestaprocesoevaluativo_pregunta_set.filter(status=True)
                    paging = MiPaginador(preguntasencuesta, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['preguntaencuesta'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_evaluaciondocentesacreditacion/viewpreguntaencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpreguntaencuesta':
                try:
                    data['title'] = u'Adicionar pregunta de encuesta'
                    data['encuesta'] = EncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['form'] = PreguntaEncuestaForm()
                    return render(request, "adm_evaluaciondocentesacreditacion/addpreguntaencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpreguntaencuesta':
                try:
                    data['title'] = u'Adicionar pregunta de encuesta'
                    data['encuestapregunta'] = encuestapregunta = EncuestaProcesoEvaluativo_Pregunta.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['form'] = PreguntaEncuestaForm(initial={'nombre':encuestapregunta.nombre, 'activo':encuestapregunta.activo, 'obligatorio':encuestapregunta.obligatorio})
                    return render(request, "adm_evaluaciondocentesacreditacion/editpreguntaencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'delpreguntaencuesta':
                try:
                    data['title'] = u'Eliminar pregunta de encuesta'
                    data['encuestapregunta'] = EncuestaProcesoEvaluativo_Pregunta.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "adm_evaluaciondocentesacreditacion/delpreguntaencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'evaluacionencuesta':
                try:
                    data['title'] = u'Evaluacion de encuesta'
                    data['cronogramaencuesta'] = cronogramaencuesta = CronogramaEncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['preguntasencuesta'] = preguntasencuesta = cronogramaencuesta.encuestas_cronograma()
                    preguntaencuesta = None
                    encuestaselect = None
                    matricula_evaluaron = None
                    search = None
                    if 'ide' in request.GET:
                        preguntaencuesta = preguntasencuesta.get(pk=int(encrypt(request.GET['ide'])))
                        preguntaencuesta.totales_estudiantes_encuesta_evaluacion(data)
                        encuestaselect = request.GET['ide']
                        matriculados = preguntaencuesta.estudiante_evaluaron()
                        if 's' in request.GET:
                            search = request.GET['s']
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    matricula_evaluaron = matriculados.filter((Q(inscripcion__persona__apellido1__icontains=s[0])|
                                                                               Q(inscripcion__persona__apellido2__icontains=s[0])|
                                                                               Q(inscripcion__persona__nombres__icontains=s[0]))&
                                                                              Q(status=True))
                                elif len(s) == 2:
                                    matricula_evaluaron = matriculados.filter(((Q(inscripcion__persona__apellido1__icontains=s[0]) &
                                                                                Q(inscripcion__persona__apellido2__icontains=s[1])) |
                                                                               (Q(inscripcion__persona__nombres__icontains=s[0]) &
                                                                                Q(inscripcion__persona__nombres__icontains=s[1]))) &
                                                                              Q(status=True))
                                elif len(s) == 3:
                                    matricula_evaluaron = matriculados.filter(Q(inscripcion__persona__apellido1__icontains=s[0]) &
                                                                              Q(inscripcion__persona__apellido2__icontains=s[1]) &
                                                                              Q(inscripcion__persona__nombres__icontains=s[2]) &
                                                                              Q(status=True))
                                elif len(s) == 4:
                                    matricula_evaluaron = matriculados.filter(Q(inscripcion__persona__apellido1__icontains=s[0]) &
                                                                              Q(inscripcion__persona__apellido2__icontains=s[1]) &
                                                                              Q(inscripcion__persona__nombres__icontains=s[2]) &
                                                                              Q(inscripcion__persona__nombres__icontains=s[3]) &
                                                                              Q(status=True))
                        else:
                            matricula_evaluaron = matriculados
                        paging = MiPaginador(matricula_evaluaron, 25)
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
                        data['page'] = page
                        data['rangospaging'] = paging.rangos_paginado(p)
                        matricula_evaluaron = page.object_list
                    data['matricula_evaluaron'] = matricula_evaluaron
                    data['search'] = search if search else ""
                    data['encuestaselect'] = encuestaselect
                    data['preguntaencuesta'] = preguntaencuesta
                    return render(request, "adm_evaluaciondocentesacreditacion/viewevaluacionencuesta.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteprofesores':
                try:
                    periodos = Periodo.objects.filter(pk__in=[encrypt(peri) for peri in json.loads(request.GET['periodos'])])
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporteprofesor.xls'
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, bold on , height 350; alignment: horiz centre')
                    subtitle = easyxf('font: name Times New Roman, bold on , height 260; alignment: horiz left')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.col(0).width = 3000
                    ws.col(1).width = 8000
                    ws.col(2).width = 8000
                    ws.col(3).width = 8000
                    ws.col(4).width = 8000
                    ws.col(5).width = 6000
                    ws.col(6).width = 6000
                    ws.col(7).width = 6000
                    ws.col(8).width = 6000
                    ws.col(9).width = 6000
                    ws.col(10).width = 6000
                    row_num = 0
                    ws.write(3, 0, 'CÉDULA', subtitle)
                    ws.write(3, 1, 'NOMBRES Y APELLIDOS PROFESOR', subtitle)
                    ws.write(3, 2, 'FACULTAD', subtitle)
                    ws.write(3, 3, 'CARRERA A LA QUE PERTENECE EL DOCENTE (MAYOR CARGA HORARIA)', subtitle)
                    ws.write(3, 4, 'CAPACITACIONES', subtitle)
                    colum = 5
                    for per in periodos:
                        ws.write(3, colum, u'ASIGNATURAS %s'% per.nombre.__str__(), subtitle)
                        colum += 1
                        ws.write(3, colum, u'CARRERA DE LA ASIGNATURA ', subtitle)
                        colum += 1
                        ws.write(3, colum, u'CALIFICACIÓN OBTENIDA %s'% per.nombre.__str__(), subtitle)
                        colum += 1
                    a = 4
                    colum1 = 5
                    for peri in periodos:
                        distributivos = ProfesorDistributivoHoras.objects.filter(periodo=peri, profesor__id__in=peri.lista_profesores_evaluados()).distinct().order_by('periodo', 'profesor')
                        for distributivo in distributivos:
                            campo1 = distributivo.profesor.persona.cedula
                            campo2 = distributivo.profesor.persona.nombre_completo_inverso()
                            campo3 = distributivo.coordinacion if distributivo.coordinacion else ''
                            campo4 = distributivo.carrera if distributivo.carrera else ''
                            for capacitacion in distributivo.profesor.persona.mis_capacitaciones():
                                campo5 = u'%s (%s - %s)'% (capacitacion.nombre, capacitacion.fechainicio, capacitacion.fechafin)
                                ws.write(a, 0, u'%s' % campo1.__str__())
                                ws.write(a, 1, u'%s' % campo2.__str__())
                                ws.write(a, 2, u'%s' % campo3.__str__())
                                ws.write(a, 3, u'%s' % campo4.__str__())
                                ws.write(a, 4, u'%s' % campo5.__str__())
                                a += 1
                            for profesormateria in distributivo.profesor_materias():
                                campo6 = profesormateria.materia.nombre_completo_sin_carrera()
                                campo7 = profesormateria.resultado_evaluacion_estudiantes_docencia()
                                carreramateria=profesormateria.materia.carrera()
                                ws.write(a, 0, u'%s' % campo1.__str__())
                                ws.write(a, 1, u'%s' % campo2.__str__())
                                ws.write(a, 2, u'%s' % campo3.__str__())
                                ws.write(a, 3, u'%s' % campo4.__str__())
                                ws.write(a, colum1, u'%s' % campo6.__str__())
                                ws.write(a, colum1+1, u'%s' % carreramateria.__str__())
                                ws.write(a, colum1+2, u'%s' % campo7.__str__())
                                a += 1
                        colum1 += 2
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'generarreportedirect':
                try:
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reportedirectivosevaluacion.xls'
                    _author_ = 'Unemi'
                    title = easyxf('font: name Times New Roman, bold on , height 350; alignment: horiz centre')
                    subtitle = easyxf('font: name Times New Roman, bold on , height 260; alignment: horiz left')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.col(0).width = 8000
                    ws.col(1).width = 8000
                    ws.col(2).width = 8000
                    ws.col(3).width = 8000
                    ws.col(4).width = 8000
                    ws.col(5).width = 6000
                    ws.col(6).width = 6000
                    ws.write(3, 0, 'EVALUADOR', subtitle)
                    ws.write(3, 1, 'EVALUADO', subtitle)
                    ws.write(3, 2, 'FACULTAD', subtitle)
                    ws.write(3, 3, 'CARRERA', subtitle)
                    ws.write(3, 4, 'CRITERIO', subtitle)
                    ws.write(3, 5, 'PREGUNTA', subtitle)
                    ws.write(3, 6, 'RESPUESTA', subtitle)
                    ws.write(3, 7, 'JUSTIFICACIÓN', subtitle)
                    row = 4

                    respuesta = RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=periodo,
                                                tipoinstrumento__in=(4, 5),respuestarubrica__detallerespuestarubrica__justificacion__isnull=False).order_by('evaluador').distinct()
                    for res in respuesta:
                        rubricas = RespuestaRubrica.objects.filter(respuestaevaluacion=res,
                                                                   detallerespuestarubrica__justificacion__isnull=False).distinct('rubrica')
                        if profesor := ProfesorDistributivoHoras.objects.get(periodo=periodo,profesor=res.profesor,status=True):
                            if rubricas is not None:
                                for rubrica in rubricas:
                                    valor_map = {
                                        1: rubrica.rubrica.texto_nosatisfactorio,
                                        2: rubrica.rubrica.texto_basico,
                                        3: rubrica.rubrica.texto_competente,
                                        4: rubrica.rubrica.texto_muycompetente,
                                        5: rubrica.rubrica.texto_destacado,
                                    }
                                    mis_preguntas = RubricaPreguntas.objects.filter(rubrica=rubrica.rubrica.id)
                                    detalle = DetalleRespuestaRubrica.objects.filter(
                                        respuestarubrica__rubrica=rubrica.rubrica,
                                        respuestarubrica__respuestaevaluacion=res, rubricapregunta__in=mis_preguntas,
                                        justificacion__isnull=False)
                                    for det in detalle:
                                        campo1 = res.evaluador.nombre_completo_inverso()
                                        campo2 = res.profesor.persona.nombre_completo_inverso()
                                        campo3 = res.profesor.coordinacion if res.profesor.coordinacion else ''
                                        campo4 = profesor.carrera if profesor.carrera else ''
                                        campo5 = rubrica.rubrica
                                        ws.write(row, 0, u'%s' % str(campo1))
                                        ws.write(row, 1, u'%s' % str(campo2))
                                        ws.write(row, 2, u'%s' % str(campo3))
                                        ws.write(row, 3, u'%s' % str(campo4))
                                        ws.write(row, 4, u'%s' % str(campo5))
                                        ws.write(row, 5, str(det.rubricapregunta.preguntacaracteristica.pregunta))
                                        ws.write(row, 6, str(valor_map.get(int(det.valor))))
                                        ws.write(row, 7, str(det.justificacion))
                                        row += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'generarreportepar':
                try:
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporteparesevaluacion.xls'
                    _author_ = 'Unemi'
                    title = easyxf('font: name Times New Roman, bold on , height 350; alignment: horiz centre')
                    subtitle = easyxf('font: name Times New Roman, bold on , height 260; alignment: horiz left')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.col(0).width = 8000
                    ws.col(1).width = 8000
                    ws.col(2).width = 8000
                    ws.col(3).width = 8000
                    ws.col(4).width = 8000
                    ws.col(5).width = 6000
                    ws.col(6).width = 6000
                    ws.write(3, 0, 'EVALUADOR', subtitle)
                    ws.write(3, 1, 'EVALUADO', subtitle)
                    ws.write(3, 2, 'FACULTAD', subtitle)
                    ws.write(3, 3, 'CARRERA', subtitle)
                    ws.write(3, 4, 'CRITERIO', subtitle)
                    ws.write(3, 5, 'PREGUNTA', subtitle)
                    ws.write(3, 6, 'RESPUESTA', subtitle)
                    ws.write(3, 7, 'JUSTIFICACIÓN', subtitle)
                    row = 4

                    respuesta = RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=periodo,
                                            tipoinstrumento=3,respuestarubrica__detallerespuestarubrica__justificacion__isnull=False
                                               ).order_by('evaluador').distinct()
                    for res in respuesta:
                        rubricas = RespuestaRubrica.objects.filter(respuestaevaluacion=res,detallerespuestarubrica__justificacion__isnull=False).distinct('rubrica')
                        if profesor := ProfesorDistributivoHoras.objects.get(periodo=periodo,profesor=res.profesor,status=True):
                            if rubricas is not None:
                                for rubrica in rubricas:
                                    valor_map = {
                                        1: rubrica.rubrica.texto_nosatisfactorio,
                                        2: rubrica.rubrica.texto_basico,
                                        3: rubrica.rubrica.texto_competente,
                                        4: rubrica.rubrica.texto_muycompetente,
                                        5: rubrica.rubrica.texto_destacado,
                                    }
                                    mis_preguntas = RubricaPreguntas.objects.filter(rubrica=rubrica.rubrica.id)
                                    detalle = DetalleRespuestaRubrica.objects.filter(respuestarubrica__rubrica=rubrica.rubrica,
                                                respuestarubrica__respuestaevaluacion=res, rubricapregunta__in=mis_preguntas,justificacion__isnull=False )
                                    for det in detalle:
                                        campo1 = res.evaluador.nombre_completo_inverso()
                                        campo2 = res.profesor.persona.nombre_completo_inverso()
                                        campo3 = res.profesor.coordinacion if res.profesor.coordinacion else ''
                                        campo4 = profesor.carrera if profesor.carrera else ''
                                        campo5 = rubrica.rubrica
                                        ws.write(row, 0, u'%s' % str(campo1))
                                        ws.write(row, 1, u'%s' % str(campo2))
                                        ws.write(row, 2, u'%s' % str(campo3))
                                        ws.write(row, 3, u'%s' % str(campo4))
                                        ws.write(row, 4, u'%s' % str(campo5))
                                        ws.write(row, 5, str(det.rubricapregunta.preguntacaracteristica.pregunta))
                                        ws.write(row, 6, str(valor_map.get(int(det.valor))))
                                        ws.write(row, 7, str(det.justificacion))
                                        row += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'cronogramafacultadproceso':
                try:
                    data['title'] = u'Cronograma de Evaluación'
                    if not 'id' in request.GET and request.GET['id']:
                        raise NameError(u"Tipo de proceso no identificado")
                    tipo_id = int(request.GET['id'])
                    detalles = CronogramaProcesoEvaluativoAcreditacion.objects.filter(proceso=proceso, tipocronograma=tipo_id, status=True)
                    detalle = None
                    if not detalles.exists():
                        detalle = CronogramaProcesoEvaluativoAcreditacion(proceso=proceso,
                                                                          tipocronograma=tipo_id,
                                                                          activo=False)
                        detalle.save(request)
                    else:
                        detalle = detalles.first()
                    data['detalle'] = detalle
                    return render(request, "adm_evaluaciondocentesacreditacion/viewcronogramaproceso.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcronogramafacultadproceso':
                try:
                    if not 'id' in request.GET and request.GET['id']:
                        raise NameError(u"Tipo de proceso no identificado")
                    id = int(request.GET['id'])
                    detalle = CronogramaProcesoEvaluativoAcreditacion.objects.get(pk=id)
                    data['title'] = u'Adicionar cronograma %s' % detalle.get_tipocronograma_display()
                    data['detalle'] = detalle
                    f = CronogramaCoordinacionForm()
                    f.adicionar(detalle)
                    data['form'] = f
                    return render(request, "adm_evaluaciondocentesacreditacion/addcronogramaproceso.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcronogramafacultadproceso':
                try:
                    if not 'id' in request.GET and request.GET['id']:
                        raise NameError(u"Tipo de proceso no identificado")
                    if not 'idc' in request.GET and request.GET['idc']:
                        raise NameError(u"Cronograma no identificado")
                    id = int(request.GET['id'])
                    idc = int(request.GET['idc'])
                    detalle = CronogramaProcesoEvaluativoAcreditacion.objects.get(pk=id)
                    cronograma = CronogramaCoordinacion.objects.get(pk=idc)
                    data['title'] = u'Editar cronograma %s - %s' % (detalle.get_tipocronograma_display(), cronograma.coordinacion)
                    f = CronogramaCoordinacionForm(initial=model_to_dict(cronograma))
                    f.editar(cronograma)
                    data['form'] = f
                    data['detalle'] = detalle
                    data['cronograma'] = cronograma
                    return render(request, "adm_evaluaciondocentesacreditacion/editcronogramaproceso.html", data)
                except Exception as ex:
                    pass

            elif action == 'vertotales':
                try:
                    total = proceso.hetero_total()
                    realizadas = proceso.hetero_realizadas()
                    porcentaje = (realizadas * 100) / total
                    data = {"results": "ok", 'total': total, 'realizadas': realizadas, 'porcentaje': porcentaje}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'docentesrelacionados':
                try:
                    listado = []
                    lista = []
                    iddocentes = request.GET['iddocentes']
                    for l in iddocentes.split(','):
                        listado.append(l)
                    # data['tablaponderativa'] = tablaponderativa = TablaPonderacionInstrumento.objects.get(pk=int(encrypt(request.GET['idtablaponderativa'])))
                    # data['configuraciones'] = configuraciones = tablaponderativa.tablaponderacionconfiguracion_set.filter(periodo=periodo, status=True).order_by('criteriodocenciaperiodo__criterio__tipo', 'criteriodocenciaperiodo_id', 'criterioinvestigacionperiodo', 'criteriogestionperiodo_id')
                    # listadodocencia = configuraciones.values_list('criteriodocenciaperiodo_id', flat=True).filter(criteriodocenciaperiodo_id__isnull=False).order_by('criteriodocenciaperiodo_id')
                    # listadoinvestigacion = configuraciones.values_list('criterioinvestigacionperiodo_id', flat=True).filter(criterioinvestigacionperiodo_id__isnull=False).order_by('criterioinvestigacionperiodo_id')
                    # listadogestion = configuraciones.values_list('criteriogestionperiodo_id', flat=True).filter(criteriogestionperiodo_id__isnull=False).order_by('criteriogestionperiodo_id')
                    #
                    # lst_doc = [str(a) for a in listadodocencia]
                    # listacriteriosdocenciavincu = ",".join(lst_doc)
                    #
                    # lst_inv = [str(a) for a in listadoinvestigacion]
                    # listacriteriosinvestigacion = ",".join(lst_inv)
                    #
                    # lst_ges = [str(a) for a in listadogestion]
                    # listacriteriosgestion = ",".join(lst_ges)
                    #
                    # cursor = connection.cursor()
                    # sql = """
                    #         SELECT * FROM (
                    #         SELECT dis.id,dis.profesor_id,per.apellido1,per.apellido2,per.nombres,
                    #         array_to_string(array_agg(det.criteriodocenciaperiodo_id order by det.criteriodocenciaperiodo_id),',') AS criteriodocenciavinculacion,
                    #         array_to_string(array_agg(det.criterioinvestigacionperiodo_id order by det.criterioinvestigacionperiodo_id),',') AS criterioinvestigacion,
                    #         array_to_string(array_agg(det.criteriogestionperiodo_id order by det.criteriogestionperiodo_id),',') AS criteriogestion
                    #         FROM sga_profesordistributivohoras dis,sga_detalledistributivo det,sga_profesor pro,sga_persona per
                    #         WHERE det.distributivo_id=dis.id
                    #         and dis.periodo_id=%s
                    #         AND dis.profesor_id=pro.id
                    #         AND pro.persona_id=per.id
                    #         GROUP BY per.apellido1,per.apellido2,per.nombres, dis.id) AS tableotra
                    #         WHERE criteriodocenciavinculacion ='%s'
                    #         AND criterioinvestigacion='%s'
                    #         AND criteriogestion='%s'
                    #         """ % (periodo.id, listacriteriosdocenciavincu, listacriteriosinvestigacion, listacriteriosgestion)
                    # cursor.execute(sql)
                    # results = cursor.fetchall()
                    # for lis in results:
                    #     lista.append([lis[0], str(lis[2] + ' ' + lis[3] + ' ' + lis[4])])
                    # data = {"results": "ok", 'listadoprofesores': lista}
                    # return JsonResponse(data)

                    listadistributivo = ProfesorDistributivoHoras.objects.filter(pk__in=listado).order_by('profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres')
                    cont = 0
                    for lis in listadistributivo:
                        cont += 1
                        nombretablaponderativa = ''
                        if lis.tablaponderacion:
                            nombretablaponderativa = lis.tablaponderacion.nombre
                        # para posgrado
                        materia_identificacion = lis.materia.identificacion if lis.materia and lis.materia.identificacion else ''
                        paralelo = lis.materia.paralelo if lis.materia and lis.materia.paralelo else ''
                        nivel = lis.materia.asignaturamalla.nivelmalla.nombre if lis.materia and lis.materia.asignaturamalla and lis.materia.asignaturamalla.nivelmalla and lis.materia.asignaturamalla.nivelmalla.nombre else ''
                        lista.append([lis.id, str(lis.profesor.persona.apellido1 + ' ' + lis.profesor.persona.apellido2 + ' ' + lis.profesor.persona.nombres),cont, nombretablaponderativa, materia_identificacion, paralelo, nivel])
                    data = {"results": "ok", 'listadoprofesores': lista, 'periodo': periodo.clasificacion}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listamodalidadtipoprofesor':
                try:
                    lista = []
                    listamodalrubricas = []
                    rubrica = Rubrica.objects.get(pk=request.GET['idrubrica'])
                    rubricalistadomodalidades = rubrica.rubricamodalidadtipoprofesor_set.filter(status=True).order_by('modalidad_id', 'tipoprofesor_id')
                    for rubmodal in rubricalistadomodalidades:
                        listamodalrubricas.append(str(rubmodal.modalidad.id) + '' + str(rubmodal.tipoprofesor.id))

                    listadomodalidadesperiodo = ProfesorMateria.objects. \
                        values_list('materia__nivel__modalidad_id',
                                    'materia__nivel__modalidad__nombre',
                                    'tipoprofesor_id',
                                    'tipoprofesor__nombre'). \
                        annotate(sumatoria=Concat('materia__nivel__modalidad_id', 'tipoprofesor_id')). \
                        filter(materia__nivel__periodo=periodo, materia__nivel__status=True, materia__status=True, status=True). \
                        order_by('materia__nivel__modalidad_id','tipoprofesor_id').distinct()
                    cont = 0
                    for lis in listadomodalidadesperiodo:
                        cont += 1
                        if lis[4] not in listamodalrubricas:
                            lista.append([lis[0], lis[1], lis[2], lis[3], cont])
                    data = {"results": "ok", 'listadoprofesores': lista}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            # if action == 'listapreguntas':
            #     import openpyxl
            #     workbook = openpyxl.load_workbook("preguntas.xlsx")
            #     lista = workbook.get_sheet_by_name('Hoja1')
            #     linea = 0
            #     listadocentessinevaluar = []
            #     totallista = lista.rows
            #     for filas in totallista:
            #         linea += 1
            #         if linea > 1:
            #             listadocentessinevaluar.append([filas[0].value,filas[1].value,filas[2].value,filas[3].value])
            #         linea += 1
            #     data['listadocentessinevaluar'] = listadocentessinevaluar
            #     return render(request, "adm_evaluaciondocentesacreditacion/lpreguntas.html", data)

            if action == 'modalidadesevaluar':
                data['title'] = u'Listado de modalidades a evaluar heteroevaluación'
                listamodalrubricas = []
                rubricalistadomodalidades = RubricaModalidadTipoProfesor.objects.values_list('modalidad_id', 'tipoprofesor_id').filter(rubrica__proceso__periodo=periodo, rubrica__para_hetero=True, status=True).distinct()
                for rubmodal in rubricalistadomodalidades:
                    listamodalrubricas.append(str(rubmodal[0]) + '' + str(rubmodal[1]))
                data['tipoprofesorevalua'] = TipoProfesor.objects.values_list('id', flat=True).filter(evaluahetero=True, status=True)
                listadomodalidades = ProfesorMateria.objects. \
                    values_list('materia__nivel__modalidad_id',
                                'materia__nivel__modalidad__nombre',
                                'tipoprofesor_id',
                                'tipoprofesor__nombre'). \
                    annotate(sumatoria=Concat('materia__nivel__modalidad_id', 'tipoprofesor_id')). \
                    annotate(numprofe=Count('profesor', distinct=True)). \
                    filter(materia__nivel__periodo=periodo, materia__nivel__status=True, profesor__persona__real=True, materia__status=True, status=True).exclude(tipoprofesor_id__in=[4,16,17])

                data['listadomodalidades'] = listadomodalidades
                data['listamodalrubricas'] = listamodalrubricas
                return render(request, "adm_evaluaciondocentesacreditacion/modalidadesevaluar.html", data)

            if action == 'eva_inv_vinc':
                data['title'] = u'Listado de evaluadores de las actividades investigación y vinculación'
                listaevaluador = proceso.paresinvestigacionvinculacion_set.filter(status=True)
                data['listaevaluador'] = listaevaluador
                return render(request, "adm_evaluaciondocentesacreditacion/evaluador_inv_vinc.html", data)

            if action == 'addeval':
                try:
                    form = ParesInvestigacionVinculacionForm()
                    data['form2'] = form
                    template = get_template("adm_evaluaciondocentesacreditacion/addevaluador_inv_vinc.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filtro = Q(usuario__isnull=False, status=True)
                    if len(s) == 1:
                        filtro &= ((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(
                            apellido2__icontains=q) | Q(cedula__contains=q)))
                    elif len(s) == 2:
                        filtro &= ((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                   (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                   (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1])))
                    else:
                        filtro &= ((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(
                            apellido2__contains=s[2])) |
                                   (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(
                                       apellido1__contains=s[2])))
                    cod_personas = Administrativo.objects.values_list('persona_id').filter(status=True)
                    per = Persona.objects.filter(filtro, pk__in=cod_personas).exclude(cedula='').order_by('apellido1', 'apellido2', 'nombres').distinct()[:20]
                    return JsonResponse({"result": "ok", "results": [{"id": x.id, "name": "%s %s" % (
                        f"<img src='{x.get_foto()}' width='25' height='25' style='border-radius: 20%;' alt='...'>",
                        x.nombre_completo_inverso())} for x in per]})
                except Exception as ex:
                    pass

            if action == 'editeval':
                try:
                    data['id'] = request.GET['id']
                    parevaluador = ParesInvestigacionVinculacion.objects.get(
                        pk=request.GET['id'], status=True)

                    form = ParesInvestigacionVinculacionForm(initial= model_to_dict(parevaluador))
                    form.edit(parevaluador.persona.id)

                    data['form2'] = form
                    template = get_template("adm_evaluaciondocentesacreditacion/addevaluador_inv_vinc.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            if action == 'docentesevaluar':
                data['title'] = u'Listado de docentes que serán evaluados'
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                data['modalidad'] = modalidad = Modalidad.objects.get(pk=request.GET['idmodalidad'])
                data['tipoprofesor'] = tipoprofesor = TipoProfesor.objects.get(pk=request.GET['idtipoprofesor'])
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        listadoprofesores = ProfesorMateria.objects.filter(Q(profesor__persona__nombres__icontains=search) |
                                                                           Q(profesor__persona__apellido1__icontains=search) |
                                                                           Q(profesor__persona__apellido2__icontains=search) |
                                                                           Q(profesor__persona__cedula__icontains=search) |
                                                                           Q(profesor__persona__pasaporte__icontains=search) |
                                                                           Q(profesor__persona__usuario__username__icontains=search),
                                                                           materia__nivel__periodo=periodo,materia__nivel__modalidad=modalidad, tipoprofesor=tipoprofesor, materia__nivel__status=True, materia__status=True, status=True). \
                            order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres', 'materia__paralelo')
                    else:
                        listadoprofesores = ProfesorMateria.objects.filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                                           Q(profesor__persona__apellido2__icontains=ss[1]),
                                                                           materia__nivel__periodo=periodo, materia__nivel__modalidad=modalidad, tipoprofesor=tipoprofesor, materia__nivel__status=True, materia__status=True, status=True). \
                            order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres', 'materia__paralelo')
                else:
                    listadoprofesores = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, materia__nivel__modalidad=modalidad, tipoprofesor=tipoprofesor, materia__nivel__status=True, materia__status=True, status=True). \
                        order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres', 'materia__paralelo')
                numerofilas = 25
                paging = MiPaginador(listadoprofesores, numerofilas)
                p = 1
                url_vars += "&action=docentesevaluar&idmodalidad="+request.GET['idmodalidad']+"&idtipoprofesor="+request.GET['idtipoprofesor']
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
                data['listadoprofesores'] = page.object_list
                return render(request, "adm_evaluaciondocentesacreditacion/docentesevaluar.html", data)

            if action == 'verrubricadocentes':
                try:
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
                    data['idmodalidad'] = idmodalidad = int(request.GET['idmodalidad'])
                    data['rubricas'] = rubricas = profesormateria.mis_rubricas_heteropregrado()
                    data['combomejoras'] = TipoObservacionEvaluacion.objects.filter(tipoinstrumento=1, tipo=1, status=True,activo=True).order_by('nombre')
                    data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                    data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                    data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                    return render(request, "pro_aluevaluacion/verrubricadocentes.html", data)
                except Exception as ex:
                    pass

            if action == 'reporteresumenevalposgrado':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('resumen')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 30)
                    ws.set_column(2, 2, 30)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 15)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 15)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 15)
                    ws.set_column(10, 10, 15)
                    ws.set_column(11, 11, 15)
                    ws.set_column(12, 12, 15)
                    ws.set_column(13, 13, 15)
                    ws.set_column(14, 14, 15)
                    ws.set_column(15, 15, 15)
                    ws.set_column(16, 16, 15)
                    ws.set_column(17, 17, 15)
                    ws.set_column(18, 18, 15)
                    ws.set_column(19, 19, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '#,##0.00 %', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '#,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    cohorte = 0
                    desde = hasta = ''

                    if 'cohorte' in request.GET:
                        cohorte = request.GET['cohorte']

                    ws.merge_range('A1:U1', f'RESUMEN DE EVALUACIÓN DOCENTE POSGRADO - {periodo}', formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Asignatura', formatoceldacab)
                    ws.write(2, 2, 'Docente', formatoceldacab)
                    ws.write(2, 3, 'Paralelo', formatoceldacab)
                    ws.write(2, 4, 'Inicio', formatoceldacab)
                    ws.write(2, 5, 'Fin', formatoceldacab)
                    ws.write(2, 6, 'Estado', formatoceldacab)
                    ws.write(2, 7, 'Hetero valor general', formatoceldacab)
                    ws.write(2, 8, 'Hetero valor general (%)', formatoceldacab)
                    ws.write(2, 9, 'Auto valor general', formatoceldacab)
                    ws.write(2, 10, 'Auto valor general (%)', formatoceldacab)
                    ws.write(2, 11, 'Directivos valor general', formatoceldacab)
                    ws.write(2, 12, 'Directivos valor general (%)', formatoceldacab)

                    ws.write(2, 13, 'Hetero valor ponderado', formatoceldacab)
                    ws.write(2, 14, 'Hetero valor ponderado (%)', formatoceldacab)
                    ws.write(2, 15, 'Auto valor ponderado', formatoceldacab)
                    ws.write(2, 16, 'Auto valor ponderado (%)', formatoceldacab)
                    ws.write(2, 17, 'Directivos valor ponderado', formatoceldacab)
                    ws.write(2, 18, 'Directivos valor ponderado (%)', formatoceldacab)
                    ws.write(2, 19, 'Total 1:5', formatoceldacab)
                    ws.write(2, 20, 'TOTAL 1:100', formatoceldacab)

                    eProfesores = ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=periodo, tipoprofesor__id__in=[11])

                    iddis = []
                    for eProfesor in eProfesores:
                        distributivo = eProfesor.profesor.distributivohoraseval(periodo)
                        if distributivo:
                            iddis.append(distributivo.id)

                    listado = ProfesorDistributivoHoras.objects.values_list('profesor__persona__apellido1',
                                                                            'profesor__persona__apellido2',
                                                                            'profesor__persona__nombres',
                                                                            'carrera__nombre',
                                                                            'resumenfinalevaluacionacreditacion__promedio_docencia_hetero',
                                                                            'resumenfinalevaluacionacreditacion__promedio_docencia_auto',
                                                                            'resumenfinalevaluacionacreditacion__promedio_docencia_directivo',
                                                                            'resumenfinalevaluacionacreditacion__valor_tabla_docencia_hetero',
                                                                            'resumenfinalevaluacionacreditacion__valor_tabla_docencia_auto',
                                                                            'resumenfinalevaluacionacreditacion__valor_tabla_docencia_directivo',
                                                                            'horasdocencia',
                                                                            'resumenfinalevaluacionacreditacion__resultado_docencia',
                                                                            'resumenfinalevaluacionacreditacion__resultado_total',
                                                                            'materia__asignaturamalla__asignatura__nombre',
                                                                            'materia__identificacion',
                                                                            'materia__paralelo',
                                                                            'materia__asignaturamalla__nivelmalla__nombre',
                                                                            'materia__inicio',
                                                                            'materia__fin',
                                                                            'materia__cerrado'). \
                        filter(periodo_id=periodo.id, status=True, id__in=iddis)

                    filas_recorridas = 4
                    cont = 1
                    for lista in listado:
                        if lista[19]:
                            estado = 'CERRADA'
                        else:
                            estado = 'ABIERTA'
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)  # Columna A: N°
                        ws.write('B%s' % filas_recorridas, lista[13], formatoceldaleft)  # Columna B: Asignatura (nombre de la asignatura)
                        ws.write('C%s' % filas_recorridas, f'{lista[0]} {lista[1]} {lista[2]}', formatoceldaleft)  # Columna C: Docente (apellido1, apellido2, nombres)
                        ws.write('D%s' % filas_recorridas, lista[15], formatoceldaleft)  # Columna D: Paralelo
                        ws.write('E%s' % filas_recorridas, str(lista[17]), formatoceldaleft)  # Columna E: Inicio
                        ws.write('F%s' % filas_recorridas, str(lista[18]), formatoceldaleft)  # Columna F: Fin

                        ws.write('G%s' % filas_recorridas, str(estado), formatoceldaleft)  # Columna F: Fin
                        # Columna G: Hetero valor general
                        ws.write('H%s' % filas_recorridas, lista[4], decimalformat2)  # Porcentaje hetero general
                        ws.write('I%s' % filas_recorridas, cincoacien(lista[4]), formatoceldaleft)  # Porcentaje hetero general
                        # Columna H: Auto valor general
                        ws.write('J%s' % filas_recorridas, lista[5], decimalformat2)  # Porcentaje auto general
                        ws.write('K%s' % filas_recorridas, cincoacien(lista[5]), formatoceldaleft)  # Porcentaje auto general
                        # Columna I: Directivos valor general
                        ws.write('L%s' % filas_recorridas, lista[6], decimalformat2)  # Porcentaje directivo general
                        ws.write('M%s' % filas_recorridas, cincoacien(lista[6]), formatoceldaleft)  # Porcentaje directivo general
                        # Columna J: Hetero valor ponderado
                        ws.write('N%s' % filas_recorridas, lista[7], decimalformat2)  # Valor hetero ponderado
                        ws.write('O%s' % filas_recorridas, cincoacien(lista[7]), formatoceldaleft)  # Valor hetero ponderado

                        # Columna K: Auto valor ponderado
                        ws.write('P%s' % filas_recorridas, lista[8], decimalformat2)  # Valor auto ponderado
                        ws.write('Q%s' % filas_recorridas, cincoacien(lista[8]), formatoceldaleft)  # Valor auto ponderado

                        # Columna L: Directivos valor ponderado
                        ws.write('R%s' % filas_recorridas, lista[9], decimalformat2)  # Valor directivo ponderado
                        ws.write('S%s' % filas_recorridas, cincoacien(lista[9]), formatoceldaleft)  # Valor directivo ponderado

                        # Columna M: Total 1:5
                        ws.write('T%s' % filas_recorridas, lista[12], decimalformat2)  # Total 1:5

                        # Columna N: TOTAL 1:100
                        ws.write('U%s' % filas_recorridas, cincoacien(lista[12]), formatoceldaleft)  # TOTAL 1:100

                        filas_recorridas += 1
                        print(f'{cont}/{listado.count()}')
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Resumenevaldocentepos_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Proceso de evaluación de profesores'
                evaluacionmigrada = False
                data['noprocesadas'] = proceso.respuestaevaluacionacreditacion_set.values("id").filter(procesada=False, status=True).count()
                if ResumenFinalEvaluacionAcreditacionFija.objects.values_list('id').filter(distributivo__periodo=periodo).exists():
                    evaluacionmigrada = True
                data['evaluacionmigrada'] = evaluacionmigrada
                data['listaperiodos'] = Periodo.objects.filter(status=True)
                # data['carrera']=Carrera.objects.filter(status=True)
                # data['periodo']=Periodo.objects.filter(status=True,tipo=2)
                if proceso.periodo.tipo.id == 3:
                    subjects = '<ul>'
                    for detalle in proceso.dir_sin_realizar():
                        materia = paralelo = ''
                        if detalle.materia:
                            materia = detalle.materia.asignatura
                            paralelo = detalle.materia.paralelo
                        subjects += f'<li>Evaluado: <b>{detalle.evaluado.persona}</b> - Evaluador: <b>{detalle.evaluador}</b> - Módulo: <b>{materia}</b> paralelo <b>{paralelo}</b></li>'
                    subjects = subjects + '</ul>'
                    data['subjects'] = subjects
                return render(request, "adm_evaluaciondocentesacreditacion/view.html", data)
            except Exception as ex:
                pass