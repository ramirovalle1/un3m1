# -*- coding: UTF-8 -*-
import datetime
import calendar
import os
import io
import subprocess
import random
import sys
import zipfile
from datetime import *
from decimal import Decimal
from dateutil.rrule import MONTHLY, rrule, YEARLY
import time
import fitz
import urllib.request
from django.core.files import File as DjangoFile
import xlsxwriter
import xlwt
import math
from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection, connections
from django.db.models import Q, Sum, Count, Avg, Case, When, Value, BooleanField, F, Sum, OuterRef, Subquery, IntegerField, CharField, Value as V
from django.db.models.functions import Coalesce, Concat
# from django.forms import IntegerField
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from reportlab.lib.colors import HexColor
from xlwt import *
import collections
from django.forms import  model_to_dict

from core.firmar_documentos import firmararchivogenerado, firmarmasivo, obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module, last_access
from inno.models import ActividadDocentePeriodo, HistorialInformeMensual, SubactividadDocentePeriodo, SubactividadDetalleDistributivo, HorarioTutoriaAcademica, SolicitudTutoriaIndividual, HistorialInforme, InformeMensualDocente, TerminosCondiciones, RegistroClaseTutoriaDocente, \
    SolicitudAperturaClaseVirtual, HistorialRecordatorioGenerarInforme, DetalleSolicitudHorarioTutoria, HistorialJustificaInforme
from inno.forms import TerminosCondicionesForm, GestionarAperturaClaseVirtualForm, SubactividadDetalleDistributivoForm
from pdip.models import ContratoDip
from sagest.models import LogDia, PermisoInstitucional, PermisoInstitucionalDetalle, DistributivoPersona, Departamento, \
    PermisoAprobacion, ESTADO_PERMISOS_APROBADOR, ESTADO_PERMISOS, IngresoPersonal
from settings import CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, \
    CRITERIO_HORAS_CLASE_PRACTICA, CRITERIO_HORAS_CLASE_AYUDANTIA, SITE_STORAGE, TIPO_DOCENTE_TEORIA, PUESTO_ACTIVO_ID, \
    EMAIL_DOMAIN, JR_JAVA_COMMAND, DATABASES, JR_USEROUTPUT_FOLDER, JR_RUN, MEDIA_URL, SUBREPOTRS_FOLDER, MEDIA_ROOT, \
    SITE_ROOT, DEBUG, TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID
from sga.commonviews import adduserdata, obtener_reporte, traerNotificaciones
from sga.excelbackground import reporte_recurso_aprendizaje_background, \
    reporte_general_porcentaje_cumplimiento_background,reporte_criterios_nuevo, reporte_distributivo_asignaturas_background, reporte_criterios_actividades_formacion_docente_background, reporte_cumplimiento_background_v3, reporte_titulos_academicos_docente_background
from sga.forms import HorasCriterioForm, ActividadCriterioForm, DedicacionProfesorForm, PonderacionProfesorForm, \
    ProfesorTipoForm, DistributivoProfesorForm, DocenteDistributivoForm, FechaNotificacionEvaluacionForm, \
    RechazarCronogramaActividadFrom, DocentePlanificarForm, InformeForm, JustificarInformeForm
from sga.funciones import MiPaginador, log, puede_realizar_accion, convertir_fecha, \
    remover_caracteres_especiales_unicode, convertir_fecha_invertida, sumar_hora, null_to_numeric, null_to_decimal, variable_valor, \
    convertir_fecha_hora, ok_json, bad_json, notificacion, generar_nombre, remover_caracteres_tildes_unicode, cuenta_email_disponible_para_envio, actualiza_usuario_revisa_actividad
from sga.funcionesxhtml2pdf import conviert_html_to_pdf,conviert_html_to_pdf_name, generar_pdf_reportlab, add_graficos_circular_reporlab, \
    add_tabla_reportlab, add_titulo_reportlab, add_tabla_firma, html_to_pdfsave_informemensualdocente
from sga.models import Profesor, CriterioDocenciaPeriodo, DetalleDistributivo, \
    CriterioInvestigacionPeriodo, CriterioGestionPeriodo, ActividadDetalleDistributivo, ProfesorDistributivoHoras, \
    CriterioDocencia, CriterioInvestigacion, CriterioGestion, EncargadoCriterioPeriodo, \
    EvidenciaActividadDetalleDistributivo, Carrera, ActividadDetalleDistributivoCarrera, Clase, Turno, \
    ClaseActividadEstado, ClaseActividad, Leccion, DiasNoLaborable, Materia, AvTutoriasAlumnos, AvPreguntaRespuesta, \
    ProfesorMateria, Sesion, Periodo, MESES_CHOICES, Coordinacion, PaeActividadesPeriodoAreas, AvTutorias, \
    EvaluacionGenerica, Persona, ComplexivoClase, TipoProfesor, Titulacion, MotivoCriterioDetalleDistributivo, \
    ParticipantesArticulos, ArticulosBaseIndexada, CronogramaActividad, DetalleRecoridoCronogramaActividad, \
    DetalleInstrumentoEvaluacionParAcreditacion, ArticuloInvestigacionDocente, PonenciaInvestigacionDocente, \
    LibroInvestigacionDocente, CapituloLibroInvestigacionDocente, InvestigacionDocenteAprobacion, \
    TipoObservacionEvaluacion, ProgramaAnaliticoAsignatura, AsignaturaMallaPreferencia, \
    PreferenciaDetalleActividadesCriterio, AsignaturaMallaPreferenciaPosgrado, HorarioPreferencia, \
    TipoObservacionEvaluacion, ProgramaAnaliticoAsignatura, AsignaturaMallaPreferencia, MateriaAsignada, Asignatura, \
    ProfesorAsignaturaActividadRecursoAprendizaje, RecursoAprendizajeTipoProfesor, RecursoAprendizaje, \
    ActividadGestionRecursoAprendizaje, ActividadInvestigacionRecursoAprendizaje, ActividadDocenciaRecursoAprendizaje, \
    Reporte, ProfesorConfigurarHoras, TiempoDedicacionDocente, ProfesorTipo, PerfilAccesoUsuario, Matricula, \
    Inscripcion, CategorizacionDocente, ParticipantesMatrices, Capacitacion, CriterioVinculacionPeriodo, \
    CriterioVinculacion, CoordinadorCarrera, Notificacion, HistorialAprobacionEvidenciaActividad, EvidenciaActividadAudi, CUENTAS_CORREOS, miinstitucion, ResponsableCoordinacion, Malla
from sagest.models import ExperienciaLaboral, LogMarcada
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt, diaenletra, nombremes
from sga.reportes import elimina_tildes, fixparametro
from typing import Any, Hashable, Iterable, Optional
from inno.funciones import actualiza_vigencia_criterios_docente, actualiza_registro_horario_docente
ACTIVIDAD_MACRO_INVESTIGACION = 68
unicode = str


def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['periodo'] = periodo = request.session['periodo']
    persona = request.session['persona']
    hoy = datetime.now().date()
    #########################VERIFICAR SI ES DIRECTOR DE CARRERA###############################
    data['es_director_carr'] = es_director_carr = False
    data['es_decano'] = es_decano = False
    director_car = periodo.coordinadorcarrera_set.filter(tipo=3, persona=persona, status=True,
                                                         carrera__coordinacion__id__in=[1, 2, 3, 4, 5])
    if director_car.exists():
        data['es_director_carr'] = es_director_carr = True
    querydecano = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, coordinacion__in=[1, 2, 3, 4, 5],
                                                         persona=persona, tipo=1)
    if querydecano.exists():
        data['es_decano'] = es_decano = True
    # es_director, carreras = verificar_director_carrera(persona, periodo)
    # if es_director and len(carreras) > 0:
    #     data['es_director_carr'] = es_director_carr = True
    ############################################################################################
    user = request.user
    SESION_ID = [19, 15] if periodo.clasificacion == 2 else [15]

    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://localhost:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema

    if 'action' in request.POST:
        action = request.POST['action']

        if action == 'generar_informe_mensual':
            try:
                mes = int(request.POST['mes'])
                fechaactual = datetime.now().date()
                fechafininforme = date(fechaactual.year, mes, calendar.monthrange(fechaactual.year, mes)[1])
                fechainiinforme = fechafininforme.replace(day=1)
                estado, _ = generar_informe_mensual_docente(request.POST['id'], fechainiinforme, fechafininforme)
                if not estado:
                    raise NameError(_)
                log(f'GENERÓ INFORME MENSUAL {fechafininforme.month} - {persona}', request, 'add')
                return JsonResponse({'result': 'ok', 'porcentaje_total': _})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': f'{ex=}'})

        if action == 'addaprobacionpermiso':
            try:
                permiso = PermisoInstitucional.objects.get(pk=request.POST['id'])
                aprobar = PermisoAprobacion(permisoinstitucional=permiso,
                                            fechaaprobacion=datetime.now().date(),
                                            observacion=request.POST['obse'],
                                            aprueba=persona,
                                            estadosolicitud=int(request.POST['esta']))
                aprobar.save(request)
                permiso.actulizar_estado(request)
                aprobar.mail_notificar_jefe_departamento(request.session['nombresistema'])
                log(u'Aprobar solicitud(Director) SGA: %s' % aprobar, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'criteriosdocencia':
            try:
                hoy = datetime.now()
                profesor = Profesor.objects.get(pk=int(request.POST['id']))
                distributivo = ProfesorDistributivoHoras.objects.get(pk=int(request.POST['iddistri']))
                hrs_actividad = ActividadDetalleDistributivo.objects.filter(status=True,
                                                                            criterio__distributivo__profesor__persona=distributivo.profesor.persona,
                                                                            desde__lte=hoy.date(),
                                                                            hasta__gte=hoy.date()
                                                                            ).aggregate(hrs_doce=Sum('horas'))['hrs_doce']
                total_hrs = 0
                for lista in request.POST['lista'].split('#'):
                    actualizaadmision = False
                    distributivoadm = None
                    criterio = CriterioDocenciaPeriodo.objects.get(pk=int(lista.split(',')[0]))
                    valor = float(lista.split(',')[1])
                    total_hrs += valor
                    if valor > criterio.maximo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es mayor que el maximo permitido."})
                    if valor < criterio.minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es menor que el minimo permitido."})
                    if not DetalleDistributivo.objects.filter(distributivo=distributivo, criteriodocenciaperiodo=criterio).exists():
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=criterio,
                                                      criterioinvestigacionperiodo=None,
                                                      criteriogestionperiodo=None,
                                                      criteriovinculacionperiodo=None,
                                                      horas=valor)
                        detalle.save(request)
                        detalle.verifica_actividades(horas=detalle.horas)
                        log(u'Adiciono criterio docencia a docente: %s - perido: %s' % (detalle, detalle.distributivo.periodo), request, "add")
                        if periodo.fechadesdenotificacion:
                            if periodo.fechadesdenotificacion <= datetime.now().date():
                                descripcion = u'Se adicionó criterio de docencia: %s al profesor: %s con %s horas en el periodo de %s' % (criterio.criterio, profesor.persona.nombre_completo_inverso(), valor, criterio.periodo)
                                profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, distributivo.periodo)
                    if criterio.criterio.admision and criterio.periodosrelacionados.filter(Q(status=True), Q(Q(tipo_id=1)|Q(clasificacion=3))).exists():
                        periodoadm = criterio.periodosrelacionados.filter(Q(status=True), Q(Q(tipo_id=1)|Q(clasificacion=3))).first()
                        if CriterioDocenciaPeriodo.objects.filter(status=True, criterio=criterio.criterio, periodo=periodoadm).exists():
                            criterioadm = CriterioDocenciaPeriodo.objects.filter(status=True, criterio=criterio.criterio, periodo=periodoadm)[0]
                            if ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodoadm, profesor=profesor).exists():
                                distributivoadm = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodoadm, profesor=profesor).first()
                            else:
                                distributivoadm = ProfesorDistributivoHoras(periodo=periodoadm,
                                                                            profesor=profesor,
                                                                            dedicacion=distributivo.dedicacion,
                                                                            horasdocencia=0,
                                                                            horasinvestigacion=0,
                                                                            horasgestion=0,
                                                                            horasvinculacion=0,
                                                                            coordinacion=profesor.coordinacion,
                                                                            categoria=profesor.categoria,
                                                                            nivelcategoria=profesor.nivelcategoria,
                                                                            cargo=profesor.cargo,
                                                                            nivelescalafon=profesor.nivelescalafon)
                                distributivoadm.save(request)
                            if not DetalleDistributivo.objects.filter(distributivo=distributivoadm,
                                                                      criteriodocenciaperiodo=criterioadm).exists():
                                detalleadm = DetalleDistributivo(distributivo=distributivoadm,
                                                                 criteriodocenciaperiodo=criterioadm,
                                                                 criterioinvestigacionperiodo=None,
                                                                 criteriogestionperiodo=None,
                                                                 criteriovinculacionperiodo=None,
                                                                 horas=valor)
                                detalleadm.save(request)
                                actualizaadmision = True
                                detalleadm.verifica_actividades(horas=detalleadm.horas)
                                log(u'Adiciono criterio docencia a docente: %s - perido: %s' % (
                                    detalleadm, detalleadm.distributivo.periodo), request, "add")
                                if periodoadm.fechadesdenotificacion:
                                    if periodoadm.fechadesdenotificacion <= datetime.now().date():
                                        descripcion = u'Se adicionó criterio de docencia: %s al profesor: %s con %s horas en el periodo de %s' % (
                                            criterioadm.criterio, profesor.persona.nombre_completo_inverso(), valor,
                                            criterioadm.periodo)
                                        profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'],
                                                                                  descripcion, persona,
                                                                                  distributivo.periodo)

                    distributivo.save(request)
                    distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                    if actualizaadmision and distributivoadm:
                        distributivoadm.save(request)
                        distributivoadm.resumen_evaluacion_acreditacion().actualizar_resumen()
                # if periodo.tipo.id in [3, 4]:
                #     contrato = ContratoDip.objects.filter(status=True,
                #                                           persona=profesor.persona,
                #                                           fechainicio__lte=hoy.date(),
                #                                           fechafin__gte=hoy.date()).order_by('-id').first()
                #     if contrato:
                #         hrs_totales = contrato.get_tiempo_dedicacion()
                #         actividades_hrs = total_hrs + hrs_actividad
                #         if actividades_hrs > hrs_totales: raise NameError(f'Suma un total de {actividades_hrs} horas semanales y su maximo de horas semanales es {hrs_totales}')

                if distributivo.sobrepasa_horas():
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Limite de horas a sobrepasado."})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex} ({sys.exc_info()[-1].tb_lineno})"})

        if action == 'deletedistributivo':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['id'])
                if distributivo.bloqueardistributivo:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar este distributivo"})
                log(u'Elimino distributivo: %s - periodo: %s' % (remover_caracteres_especiales_unicode(distributivo.profesor.persona.apellido1) + ' ' +
                                                                 remover_caracteres_especiales_unicode(distributivo.profesor.persona.apellido2) + ' ' + remover_caracteres_especiales_unicode(distributivo.profesor.persona.nombres), distributivo.periodo), request, "add")
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        descripcion = u'Se eliminó del distributivo al profesor: %s con dedicación %s con %s horas de docencia, %s horas de gestión, %s horas de investigación con tabla de ponderación %s en el periodo de %s' % (distributivo.profesor.persona.nombre_completo_inverso(), distributivo.dedicacion, distributivo.horasdocencia, distributivo.horasgestion, distributivo.horasinvestigacion, distributivo.tablaponderacion, distributivo.periodo)
                        distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, distributivo.periodo)
                distributivo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addaprobacion':
            try:
                profesor = Profesor.objects.get(pk=int(request.POST['idprofesor']))
                actividad = ClaseActividadEstado(periodo=periodo,
                                                 profesor=profesor,
                                                 personaaprueba=persona,
                                                 obseaprueba=request.POST['obsaprueba'],
                                                 estadosolicitud=request.POST['idtipo'])
                actividad.save(request)
                estadosactividades = ClaseActividad.objects.filter(activo=True, detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo).distinct()
                for estados in estadosactividades:
                    estados.estadosolicitud = request.POST['idtipo']
                    estados.finalizado = int(request.POST['idtipo']) == 2
                    estados.save(request, update_fields=['estadosolicitud', 'finalizado'])
                    if estados.tipodistributivo == 1:
                        if int(request.POST['idtipo']) == 2 and estados.detalledistributivo.criteriodocenciaperiodo.criterio.procesotutoriaacademica:
                            # if ProfesorMateria.objects.filter(status=True, profesor=profesor, materia__nivel__periodo=periodo, activo=True).exists():
                            # cant1 = ProfesorMateria.objects.values('id').filter(status=True, profesor=profesor, materia__nivel__periodo=periodo,
                            #                                                     activo=True, tipoprofesor__id__in=[8]).count()
                            # cant2 = ProfesorMateria.objects.values('id').filter(status=True, profesor=profesor, materia__nivel__periodo=periodo, activo=True).count()
                            # if not cant1 == cant2:
                            if not HorarioTutoriaAcademica.objects.filter(profesor=profesor, periodo=periodo, dia=estados.dia, turno=estados.turno, claseactividad=estados).exists():
                                tuto = HorarioTutoriaAcademica(profesor=profesor, periodo=periodo, dia=estados.dia, turno=estados.turno,  claseactividad=estados)
                                tuto.save(request)
                                log(u'Ingreso un horario de tutoría académica: %s' % tuto, request, "add")
                        # asistencia_tutoria(periodo.pk, periodo.inicio, datetime.now().date(), int(request.POST['idprofesor']))
                distributivo = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor, periodo=periodo).first()
                distributivo.horariofinalizado = int(request.POST['idtipo']) == 2
                distributivo.save(request, update_fields=['horariofinalizado'])
                log(u'Aprobacion o no criterio actividades docencia: %s - %s - [%s] - periodo: %s' % (profesor, actividad, estadosactividades, actividad.periodo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'adddesaprobacion':
            try:
                profesor = Profesor.objects.get(pk=int(request.POST['idprofesor']))
                actividad = ClaseActividadEstado(periodo=periodo,
                                                 profesor=profesor,
                                                 personaaprueba=persona,
                                                 obseaprueba=request.POST['obsaprueba'],
                                                 estadosolicitud=request.POST['idtipo'])
                actividad.save(request)
                estadosactividades = ClaseActividad.objects.filter(activo=True, detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo).distinct()
                for estados in estadosactividades:
                    estados.estadosolicitud = request.POST['idtipo']
                    estados.save(request)
                log(u'Desaprobacion o no criterio actividades docencia: %s - %s - [%s] - periodo: %s' % (profesor, actividad, estadosactividades, actividad.periodo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # se comento porque estaba repetida la aprobacion
        # if action == 'addaprobacion':
        #     try:
        #         profesor = Profesor.objects.get(pk=int(request.POST['idprofesor']))
        #         actividad = ClaseActividadEstado(periodo=periodo,
        #                                          profesor=profesor,
        #                                          personaaprueba=persona,
        #                                          obseaprueba=request.POST['obsaprueba'],
        #                                          estadosolicitud=request.POST['idtipo'])
        #         actividad.save(request)
        #         estadosactividades = ClaseActividad.objects.filter(activo=True, detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo).distinct()
        #         for estados in estadosactividades:
        #             estados.estadosolicitud = request.POST['idtipo']
        #             estados.save(request)
        #         log(u'Aprobacion o no criterio actividades docencia - Vicerrectorado: %s - %s - [%s] - periodo: %s' % (profesor, actividad, estadosactividades, actividad.periodo), request, "add")
        #         return JsonResponse({"result": "ok"})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'desaprobar':
            try:
                profesor = Profesor.objects.get(pk=int(request.POST['idprofesor']))
                actividad = ClaseActividadEstado.objects.filter(status=True, periodo=periodo,
                                                                profesor=profesor)
                if actividad.exists():
                    actividad = actividad.first()
                    actividad.status = False
                    actividad.save(request)
                estadosactividades = ClaseActividad.objects.filter(activo=True, detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo).distinct()
                estadosactividades.update(estadosolicitud=1, finalizado=False)
                distributivo = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor, periodo=periodo).first()
                distributivo.horariofinalizado = False
                distributivo.save(request, update_fields=['horariofinalizado'])
                # for estados in estadosactividades:
                #     estados.estadosolicitud = 1
                #     estados.save(request)
                log(u'Desaprobacion o no criterio actividades docencia: %s - %s - [%s] - periodo: %s' % (profesor, actividad, estadosactividades, actividad.periodo), request, "add")
                return JsonResponse({"result": "ok", "mensaje": u"Se desaproobo "})
            except Exception as ex:
                transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addprofesor':
            try:
                f = DocenteDistributivoForm(request.POST)
                if f.is_valid():
                    profesorid = Profesor.objects.get(pk=f.cleaned_data['profesor'])
                    if ProfesorDistributivoHoras.objects.filter(profesor=profesorid, periodo=periodo).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El docente ya existe."})
                    distributivo = ProfesorDistributivoHoras(profesor=profesorid,
                                                             periodo=periodo,
                                                             dedicacion=profesorid.dedicacion,
                                                             horasdocencia=0,
                                                             horasinvestigacion=0,
                                                             horasgestion=0,
                                                             horasvinculacion=0,
                                                             coordinacion=profesorid.coordinacion,
                                                             categoria=profesorid.categoria,
                                                             nivelcategoria=profesorid.nivelcategoria,
                                                             cargo=profesorid.cargo,
                                                             nivelescalafon=profesorid.nivelescalafon)
                    distributivo.save(request)
                    log(u'Adiciono profesor distributivo hora en criterio actividad docente: %s - %s - [%s] - periodo: %s' % (profesorid, distributivo, distributivo.id, distributivo.periodo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addprofesorplanificar':
            try:
                f = DocentePlanificarForm(request.POST)
                if f.is_valid():
                    profesorid = Profesor.objects.get(pk=f.cleaned_data['profesor'])
                    if ProfesorConfigurarHoras.objects.filter(profesor=profesorid, periodo=periodo).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El docente ya existe."})
                    profesorconfigurar = ProfesorConfigurarHoras(profesor=profesorid,
                                                                 periodo=periodo,
                                                                 dedicacion=f.cleaned_data['dedicacion'],
                                                                 horaminima=f.cleaned_data['horaminima'],
                                                                 horamaxima=f.cleaned_data['horamaxima'],
                                                                 nivelcategoria=f.cleaned_data['tipo'],
                                                                 horamaximaasignatura=f.cleaned_data['horamaximaasignatura'])
                    profesorconfigurar.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'horarioactividadespdf':
            try:
                data = {}
                data['title'] = u'Horarios de las Actividades del Profesor'
                profesor = Profesor.objects.get(pk=int(request.POST['profesorid']))
                data['profesor'] = profesor
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                hoy = datetime.now().date()
                data['misclases'] = clases = Clase.objects.filter(activo=True, fin__gte=hoy, materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True).order_by('inicio')
                data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
                idper = int(request.POST['periodoid'])
                data['periodo'] = Periodo.objects.get(pk=idper)
                return conviert_html_to_pdf(
                    'pro_horarios/actividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'delactividaddocente':
            try:
                actividad = ClaseActividad.objects.get(pk=request.POST['id'])
                idactividad = actividad.id
                tipo = actividad.tipodistributivo
                if tipo == 1:
                    des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                if tipo == 2:
                    des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                if tipo == 3:
                    des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                turno = actividad.turno_id
                dia = actividad.dia
                return JsonResponse({"result": "ok", 'idactividad': idactividad, 'turno': turno, 'dia': dia, 'des': des})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'edittipo':
            try:
                codigo = request.POST['id']
                cod = codigo.split('_')
                if periodo.clasificacion == 2:
                    distributivo = ProfesorDistributivoHoras.objects.get(periodo_id=cod[1], profesor_id=cod[0], materia_id=cod[2])
                else:
                    distributivo = ProfesorDistributivoHoras.objects.get(periodo_id=cod[1], profesor_id=cod[0])
                f = ProfesorTipoForm(request.POST)
                if f.is_valid():
                    distributivo.nivelcategoria = f.cleaned_data['tipo']
                    distributivo.nivelescalafon = f.cleaned_data['escalafon']
                    distributivo.categoria = f.cleaned_data['categoria']
                    distributivo.dedicacion = f.cleaned_data['dedicacion']
                    distributivo.coordinacion = f.cleaned_data['coordinacion']
                    distributivo.carrera = f.cleaned_data['carrera']
                    distributivo.observacion = f.cleaned_data['observacion']
                    distributivo.vercertificado = f.cleaned_data['vercertificado']
                    distributivo.verinforme = f.cleaned_data['verinforme']
                    distributivo.save(request)
                    log(u'Edito tipo profesor distributivo hora en criterio actividad docente: %s - %s - [%s] - periodo: %s' % (distributivo, distributivo.nivelcategoria, distributivo.id, distributivo.periodo), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addhorascarrera':
            try:
                actividad = request.POST['actividad']
                actividaddeta = ActividadDetalleDistributivo.objects.get(pk=int(actividad))
                lista = request.POST['listacarrerasactividad']
                actividaddetalles = ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle_id=int(actividad))
                actividaddetalles.delete()
                lista = request.POST['listacarrerasactividad']
                if lista:
                    elementos = lista.split(',')
                    for elemento in elementos:
                        individuales = elemento.split('_')
                        detalle = ActividadDetalleDistributivoCarrera(actividaddetalle_id=int(actividad),
                                                                      carrera_id=int(individuales[0]),
                                                                      horas=float(individuales[1]))
                        detalle.save(request)
                log(u'Adiciono horas a carrera en actividad docente: %s - periodo: %s' % (lista, actividaddeta.criterio.distributivo.periodo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addhorascarrerapracticas':
            try:
                actividad = request.POST['actividad']
                actividaddeta = ActividadDetalleDistributivo.objects.get(pk=int(actividad))
                lista = request.POST['listacarrerasactividad']
                lista_carreras = []
                if lista:
                    elementos = lista.split(',')
                    actividades = ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle_id=int(actividad))
                    for elemento in elementos:
                        lista_carreras.append(elemento.split('_'))
                    act_no_existentes = ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle_id=int(actividad)).exclude(carrera__in=lista_carreras)

                    for elemento in elementos:
                        individuales = elemento.split('_')
                        if ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle_id=int(actividad), carrera_id=int(individuales[0])).exists():
                            filtro = ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle_id=int(actividad), carrera_id=int(individuales[0])).first()
                            filtro.horas = float(individuales[1])
                            filtro.save(request)
                        else:
                            detalle = ActividadDetalleDistributivoCarrera(actividaddetalle_id=int(actividad),
                                                                          carrera_id=int(individuales[0]),
                                                                          horas=float(individuales[1]))
                            detalle.save(request)

                actividaddetalles = ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle_id=int(actividad))
                actividaddetalles.delete()
                lista = request.POST['listacarrerasactividad']
                if lista:
                    elementos = lista.split(',')
                    for elemento in elementos:
                        individuales = elemento.split('_')
                        detalle = ActividadDetalleDistributivoCarrera(actividaddetalle_id=int(actividad),
                                                                      carrera_id=int(individuales[0]),
                                                                      horas=float(individuales[1]))
                        detalle.save(request)
                log(u'Adiciono horas a carrera en actividad docente: %s - periodo: %s' % (lista, actividaddeta.criterio.distributivo.periodo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcantidad':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    valoractual = int(request.POST['value'])
                    valoranterior = ActividadDetalleDistributivoCarrera.objects.get(pk=id)
                    totalhoras = ActividadDetalleDistributivoCarrera.objects.filter(status=True, actividaddetalle=valoranterior.actividaddetalle).exclude(pk=valoranterior.pk).aggregate(totalhoras=Coalesce(Sum(F('horas'), output_field=IntegerField()), 0)).get('totalhoras')
                    totalhorasactual = totalhoras + valoractual
                    bandera = True
                    filtro = ActividadDetalleDistributivoCarrera.objects.get(pk=id)
                    if filtro.total_alumnos_x_hora() > 0:
                        horasnecesarias = math.ceil(valoranterior.alumnosxhoras / filtro.total_alumnos_x_hora())
                    if valoranterior.horas == valoractual:
                        bandera = False
                        return JsonResponse({'error': True, "message": 'EL valor es el mismo, cambio no aplicado', 'valor': valoranterior.horas}, safe=False)
                    if totalhorasactual > valoranterior.actividaddetalle.horas:
                        bandera = False
                        return JsonResponse({'error': True, "message": 'El valor asignado supera el máximo de ({}) horas planificadas en la actividad'.format(valoranterior.actividaddetalle.horas), 'valor': valoranterior.horas}, safe=False)

                    if filtro.total_alumnos_x_hora() > 0:
                        if horasnecesarias > valoractual:
                            bandera = False
                            return JsonResponse({'error': True, "messvaloranterior.alumnosxhorasage": 'El valor asignado es menor al requerido por la cantidad de alumnos asignados.\nHoras Requeridas ({}) - Horas Asignadas ({})'.format(horasnecesarias, valoractual), 'valor': valoranterior.horas}, safe=False)
                    if bandera:
                        filtro.horas = valoractual
                        filtro.save(request)
                        log(u'Edito cantidad de horas distributivo docente: %s' % filtro, request, "edit")
                        icono = '<i class="{} tb"></i>'.format(filtro.get_estado_disponibilidad())
                        color = '#ffffff'
                        if filtro.get_estado_disponibilidad_int() == 0:
                            color = '#EAFAF1'
                        elif filtro.get_estado_disponibilidad_int() == 2:
                            color = '#FDEDEC'
                        res_json = {"error": False, 'icono': icono, 'totalxhora': filtro.total_alumnos_x_hora(), 'totaldisponible': filtro.get_disponbile(), 'pk': filtro.pk, 'color': color, 'texto': filtro.get_estado_disponibilidad_txt()}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'deletehoracarrera':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    filtro = ActividadDetalleDistributivoCarrera.objects.get(pk=id)
                    log(u'Elimino horas a carrera en actividad docente: %s - periodo: %s' % (filtro, filtro.actividaddetalle.criterio.distributivo.periodo), request, "add")
                    filtro.delete()
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'consultarvalor':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    valoranterior = ActividadDetalleDistributivoCarrera.objects.get(pk=id)
                    res_json = {"error": False, 'horas': valoranterior.horas}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'adicionarcarrera':
            try:
                postar = ActividadDetalleDistributivo.objects.get(id=int(request.POST['id']))
                carreraids = request.POST['ids'].split(',')
                for a in carreraids:
                    carrera = Carrera.objects.get(pk=a)
                    actividad = ActividadDetalleDistributivoCarrera(actividaddetalle=postar, carrera=carrera, horas=0)
                    actividad.save(request)
                    log(u'Adiciono horas a carrera en actividad docente: %s - periodo: %s' % (actividad, actividad.actividaddetalle.criterio.distributivo.periodo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'delcriteriodocencia':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                distributivo = detalle.distributivo
                log(u'Elimino detalle docencia: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "del")
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        descripcion = u'Se eliminó criterio de docencia: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criteriodocenciaperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                        detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detalle.distributivo.periodo)
                detalle.delete()
                distributivo.actualiza_hijos()
                distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delcriteriodocencia_aux':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                distributivo = detalle.distributivo
                log(u'Elimino detalle docencia Materia: %s  - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "del")
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        descripcion = u'Se eliminó criterio de docencia: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criteriodocenciaperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                        detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detalle.distributivo.periodo)
                detalle.delete()
                distributivo.actualiza_hijos()
                distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editcriteriodocencia':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                f = HorasCriterioForm(request.POST)
                if f.is_valid():
                    detalle.horas = float(f.cleaned_data['horas'])
                    detalle.save(request)
                    distributivo = detalle.distributivo
                    distributivo.save(request)
                    if detalle.horas > detalle.criteriodocenciaperiodo.maximo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es mayor que el maximo permitido."})
                    if detalle.horas < detalle.criteriodocenciaperiodo.minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es menor que el minimo permitido."})
                    sobrepasa = distributivo.total_horas() - distributivo.dedicacion.horas
                    if sobrepasa > 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Ha sobrepasado en %s hrs el limite de horas totales." % sobrepasa})
                    distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                    log(u'Modifico detalle docencia: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "edit")
                    if periodo.fechadesdenotificacion:
                        if periodo.fechadesdenotificacion <= datetime.now().date():
                            descripcion = u'Se editó las horas de criterio de docencia: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criteriodocenciaperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                            detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detalle.distributivo.periodo)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'pdflistaafinidad':
            try:
                from reportlab.lib import colors
                data = {}
                cursor = connections['default'].cursor()
                data['fechaactual'] = datetime.now()
                listaestudiante = "select afinidadcampoamplio, count(afinidadcampoamplio) as totalcampo,afinidadcampodetallado, count(afinidadcampodetallado) as totalcampodetalle,afinidadcampoespecifico, count(afinidadcampoespecifico) as totalespecifo " \
                                  "from(select distinct perso.apellido1, perso.apellido2, perso.nombres, " \
                                  "(select coor.nombre from sga_coordinacion_carrera ccar,sga_coordinacion coor " \
                                  "where ccar.coordinacion_id=coor.id and ccar.carrera_id=carr.id) as profesor,asi.nombre, " \
                                  "carr.nombre as carrera, pm.afinidadcampoamplio,pm.afinidadcampodetallado, pm.afinidadcampoespecifico , " \
                                  "(select ti.nombre from sga_titulo ti where ti.id=pm.tituloafin_id) as tituloafin, " \
                                  "per.nombre as nomperiodo " \
                                  "from sga_profesormateria pm,sga_materia mat,sga_nivel ni,sga_periodo per, " \
                                  "sga_asignaturamalla asimalla,sga_asignatura asi,sga_malla malla,sga_carrera carr, " \
                                  "sga_profesor pro,sga_persona perso " \
                                  "where pm.materia_id=mat.id " \
                                  "and mat.nivel_id=ni.id and ni.periodo_id=per.id and mat.asignaturamalla_id=asimalla.id " \
                                  "and asimalla.malla_id=malla.id and malla.carrera_id=carr.id and asimalla.asignatura_id=asi.id " \
                                  "and pm.profesor_id=pro.id and pro.persona_id=perso.id and per.id=" + str(periodo.id) + " " \
                                                                                                                          "and pm.tipoprofesor_id=1) as totales group by afinidadcampoamplio, afinidadcampodetallado, afinidadcampoespecifico "
                cursor.execute(listaestudiante)
                results = cursor.fetchall()
                data['listado'] = results
                nocampoamplio = 0
                sicampoamplio = 0
                nocampodet = 0
                sicampodet = 0
                nocampoesp = 0
                sicampoesp = 0
                for r in results:
                    if r[0]:
                        sicampoamplio += r[1]
                    else:
                        nocampoamplio += r[1]
                    if r[2]:
                        sicampodet += r[3]
                    else:
                        nocampodet += r[3]
                    if r[4]:
                        sicampoesp += r[5]
                    else:
                        nocampoesp += r[5]
                data['sicampoamplio'] = sicampoamplio
                data['nocampoamplio'] = nocampoamplio
                data['totalcampoamplio'] = totalcampoamplio = sicampoamplio + nocampoamplio
                data['siporcampoamplio'] = siporcampoamplio = round((sicampoamplio * 100) / totalcampoamplio, 2)
                data['noporcampoamplio'] = noporcampoamplio = round((nocampoamplio * 100) / totalcampoamplio, 2)
                data['sicampodet'] = sicampodet
                data['nocampodet'] = nocampodet
                data['totaldetallado'] = totaldetallado = nocampodet + sicampodet
                data['siporcampodetallado'] = siporcampodetallado = round((sicampodet * 100) / totaldetallado, 2)
                data['noporcampodetallado'] = noporcampodetallado = round((nocampodet * 100) / totaldetallado, 2)
                data['sicampoesp'] = sicampoesp
                data['nocampoesp'] = nocampoesp
                data['totalespecifico'] = totalespecifico = nocampoesp + sicampoesp
                data['siporcampoespecifico'] = siporcampoespecifico = round((sicampoesp * 100) / totalespecifico, 2)
                data['noporcampoespecifico'] = noporcampoespecifico = round((nocampoesp * 100) / totalespecifico, 2)
                data['periodo'] = periodo
                add_titulo_reportlab(descripcion="REPORTE DE AFINIDAD DE ASIGNATURAS", tamano=16, espacios=19)
                add_titulo_reportlab(descripcion=periodo.nombre, tamano=16, espacios=19)
                add_titulo_reportlab(descripcion="&nbsp;", tamano=16, espacios=19)
                from reportlab.lib import colors
                verdeinstitucional = HexColor(0x008000)
                add_titulo_reportlab(descripcion="CAMPO AMPLIO", tamano=14, espacios=50)
                add_tabla_reportlab(encabezado=[('Nº', 'ASIGNATURAS', 'TOTAL', '% PORCENTAJE')],
                                    detalles=[(1, 'AFIN', sicampoamplio, siporcampoamplio),
                                              (2, 'NO AFIN', nocampoamplio, noporcampoamplio)
                                              ],
                                    anchocol=[50, 70, 70, 70],
                                    cabecera_left_center=[True, False, True, True],
                                    detalle_left_center=[True, False, True, True],
                                    tamano_letra_cabecera=7)
                add_graficos_circular_reporlab(datavalor=[(siporcampoamplio), (noporcampoamplio)],
                                               datanombres=[u'%s' % ('AFIN'),
                                                            u'%s' % ('NO AFIN')
                                                            ],
                                               anchografico=120, altografico=120,
                                               colores=[verdeinstitucional, colors.gray],
                                               labelspie=['AFIN - ' + str(siporcampoamplio) + '%', 'NO AFIN - ' + str(noporcampoamplio) + '%'],
                                               posiciongrafico_x=200, posiciongrafico_y=20,
                                               titulo='', tamanotitulo=10,
                                               ubicaciontitulo_x=90, ubicaciontitulo_y=12)
                add_titulo_reportlab(descripcion="CAMPO DETALLADO", tamano=14, espacios=50)
                add_tabla_reportlab(encabezado=[('Nº', 'ASIGNATURAS', 'TOTAL', '% PORCENTAJE')],
                                    detalles=[(1, 'AFIN', sicampodet, siporcampodetallado),
                                              (2, 'NO AFIN', nocampodet, noporcampodetallado)
                                              ],
                                    anchocol=[50, 70, 70, 70],
                                    cabecera_left_center=[True, False, True, True],
                                    detalle_left_center=[True, False, True, True],
                                    tamano_letra_cabecera=7)
                add_graficos_circular_reporlab(datavalor=[(siporcampodetallado), (noporcampodetallado)],
                                               datanombres=[u'%s' % ('AFIN'),
                                                            u'%s' % ('NO AFIN')
                                                            ],
                                               anchografico=120, altografico=120,
                                               colores=[verdeinstitucional, colors.gray],
                                               labelspie=['AFIN - ' + str(siporcampodetallado) + '%', 'NO AFIN - ' + str(noporcampodetallado) + '%'],
                                               posiciongrafico_x=200, posiciongrafico_y=20,
                                               titulo='', tamanotitulo=10,
                                               ubicaciontitulo_x=90, ubicaciontitulo_y=12)
                add_titulo_reportlab(descripcion="CAMPO ESPECÍFICO", tamano=14, espacios=50)
                add_tabla_reportlab(encabezado=[('Nº', 'ASIGNATURAS', 'TOTAL', '% PORCENTAJE')],
                                    detalles=[(1, 'AFIN', sicampoesp, siporcampoespecifico),
                                              (2, 'NO AFIN', nocampoesp, noporcampoespecifico)
                                              ],
                                    anchocol=[50, 70, 70, 70],
                                    cabecera_left_center=[True, False, True, True],
                                    detalle_left_center=[True, False, True, True],
                                    tamano_letra_cabecera=7)
                add_graficos_circular_reporlab(datavalor=[(siporcampoespecifico), (noporcampoespecifico)],
                                               datanombres=[u'%s' % ('AFIN'),
                                                            u'%s' % ('NO AFIN')
                                                            ],
                                               anchografico=120, altografico=120,
                                               colores=[verdeinstitucional, colors.gray],
                                               labelspie=['AFIN - ' + str(siporcampoespecifico) + '%', 'NO AFIN - ' + str(noporcampoespecifico) + '%'],
                                               posiciongrafico_x=200, posiciongrafico_y=50,
                                               titulo='', tamanotitulo=10,
                                               ubicaciontitulo_x=90, ubicaciontitulo_y=12)
                add_tabla_firma(
                    detalles=[('______________________________________________________ VICERRECTORADO ACADÉMICO Y DE INVESTIGACIÓN',)],
                    anchocol=[300, ],
                    anchofila=100,
                    cabecera_left_center=[True, ],
                    detalle_left_center=[True, ])
                return generar_pdf_reportlab()
                # return conviert_html_to_pdf(
                #     'adm_criteriosactividadesdocente/listaafinidades_pdf.html',
                #     {
                #         'pagesize': 'A4',
                #         'data': data,
                #     }
                # )
            except Exception as ex:
                pass

        if action == 'pdflistaafinidadfacultades':
            try:
                from reportlab.lib import colors
                data = {}
                cursor = connections['default'].cursor()
                data['fechaactual'] = datetime.now()
                add_titulo_reportlab(descripcion="REPORTE DE AFINIDAD DE ASIGNATURAS", tamano=16, espacios=19)
                add_titulo_reportlab(descripcion=periodo.nombre, tamano=16, espacios=19)
                add_titulo_reportlab(descripcion="&nbsp;", tamano=16, espacios=19)
                listadoccordinaciones = Coordinacion.objects.values_list("id").filter(id__in=[x.coordinacion_id for x in PerfilAccesoUsuario.objects.filter(grupo__in=persona.grupos())]).distinct()
                if persona.responsablecoordinacion_set.filter(coordinacion_id__in=listadoccordinaciones, periodo=periodo, tipo=1).exists():
                    coordinaciones = Coordinacion.objects.filter(pk__in=persona.responsablecoordinacion_set.values_list('coordinacion_id').filter(coordinacion_id__in=listadoccordinaciones, periodo=periodo, tipo=1), status=True)
                else:
                    coordinaciones = Coordinacion.objects.filter(status=True)
                for coor in coordinaciones:
                    listaestudiante = "select afinidadcampoamplio, count(afinidadcampoamplio) as totalcampo,afinidadcampodetallado, count(afinidadcampodetallado) as totalcampodetalle,afinidadcampoespecifico, count(afinidadcampoespecifico) as totalespecifo " \
                                      "from(select distinct perso.apellido1, perso.apellido2, perso.nombres, " \
                                      "(select coor.nombre from sga_coordinacion_carrera ccar,sga_coordinacion coor " \
                                      "where ccar.coordinacion_id=coor.id and ccar.carrera_id=carr.id) as profesor,asi.nombre, " \
                                      "carr.nombre as carrera, pm.afinidadcampoamplio,pm.afinidadcampodetallado, pm.afinidadcampoespecifico , " \
                                      "(select ti.nombre from sga_titulo ti where ti.id=pm.tituloafin_id) as tituloafin, " \
                                      "per.nombre as nomperiodo " \
                                      "from sga_profesormateria pm,sga_materia mat,sga_nivel ni,sga_periodo per, " \
                                      "sga_asignaturamalla asimalla,sga_asignatura asi,sga_malla malla,sga_carrera carr, " \
                                      "sga_profesor pro,sga_persona perso,sga_coordinacion_carrera coorcar " \
                                      "where pm.materia_id=mat.id " \
                                      "and mat.nivel_id=ni.id and ni.periodo_id=per.id and mat.asignaturamalla_id=asimalla.id " \
                                      "and asimalla.malla_id=malla.id and malla.carrera_id=carr.id and asimalla.asignatura_id=asi.id " \
                                      "and pm.profesor_id=pro.id and pro.persona_id=perso.id and per.id=" + str(periodo.id) + " " \
                                                                                                                              "and coorcar.carrera_id=carr.id and coorcar.coordinacion_id=" + str(coor.id) + " and pm.tipoprofesor_id=1) as totales group by afinidadcampoamplio, afinidadcampodetallado, afinidadcampoespecifico "
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    data['listado'] = results
                    nocampoamplio = 0
                    sicampoamplio = 0
                    nocampodet = 0
                    sicampodet = 0
                    nocampoesp = 0
                    sicampoesp = 0
                    if results:
                        for r in results:
                            if r[0]:
                                sicampoamplio += r[1]
                            else:
                                nocampoamplio += r[1]
                            if r[2]:
                                sicampodet += r[3]
                            else:
                                nocampodet += r[3]
                            if r[4]:
                                sicampoesp += r[5]
                            else:
                                nocampoesp += r[5]
                        data['sicampoamplio'] = sicampoamplio
                        data['nocampoamplio'] = nocampoamplio
                        data['totalcampoamplio'] = totalcampoamplio = sicampoamplio + nocampoamplio
                        data['siporcampoamplio'] = siporcampoamplio = round((sicampoamplio * 100) / totalcampoamplio, 2)
                        data['noporcampoamplio'] = noporcampoamplio = round((nocampoamplio * 100) / totalcampoamplio, 2)
                        data['sicampodet'] = sicampodet
                        data['nocampodet'] = nocampodet
                        data['totaldetallado'] = totaldetallado = nocampodet + sicampodet
                        data['siporcampodetallado'] = siporcampodetallado = round((sicampodet * 100) / totaldetallado, 2)
                        data['noporcampodetallado'] = noporcampodetallado = round((nocampodet * 100) / totaldetallado, 2)
                        data['sicampoesp'] = sicampoesp
                        data['nocampoesp'] = nocampoesp
                        data['totalespecifico'] = totalespecifico = nocampoesp + sicampoesp
                        data['siporcampoespecifico'] = siporcampoespecifico = round((sicampoesp * 100) / totalespecifico, 2)
                        data['noporcampoespecifico'] = noporcampoespecifico = round((nocampoesp * 100) / totalespecifico, 2)
                        data['periodo'] = periodo
                        from reportlab.lib import colors
                        verdeinstitucional = HexColor(0x008000)
                        add_titulo_reportlab(descripcion=coor.nombre, tamano=14, espacios=50)
                        add_titulo_reportlab(descripcion="CAMPO AMPLIO", tamano=14, espacios=50)
                        add_tabla_reportlab(encabezado=[('Nº', 'ASIGNATURAS', 'TOTAL', '% PORCENTAJE')],
                                            detalles=[(1, 'AFIN', sicampoamplio, siporcampoamplio),
                                                      (2, 'NO AFIN', nocampoamplio, noporcampoamplio)
                                                      ],
                                            anchocol=[50, 70, 70, 70],
                                            cabecera_left_center=[True, False, True, True],
                                            detalle_left_center=[True, False, True, True],
                                            tamano_letra_cabecera=7)
                        add_graficos_circular_reporlab(datavalor=[(siporcampoamplio), (noporcampoamplio)],
                                                       datanombres=[u'%s' % ('AFIN'),
                                                                    u'%s' % ('NO AFIN')
                                                                    ],
                                                       anchografico=120, altografico=120,
                                                       colores=[verdeinstitucional, colors.gray],
                                                       labelspie=['AFIN - ' + str(siporcampoamplio) + '%', 'NO AFIN - ' + str(noporcampoamplio) + '%'],
                                                       posiciongrafico_x=200, posiciongrafico_y=20,
                                                       titulo='', tamanotitulo=10,
                                                       ubicaciontitulo_x=90, ubicaciontitulo_y=12)
                        add_titulo_reportlab(descripcion="CAMPO DETALLADO", tamano=14, espacios=50)
                        add_tabla_reportlab(encabezado=[('Nº', 'ASIGNATURAS', 'TOTAL', '% PORCENTAJE')],
                                            detalles=[(1, 'AFIN', sicampodet, siporcampodetallado),
                                                      (2, 'NO AFIN', nocampodet, noporcampodetallado)
                                                      ],
                                            anchocol=[50, 70, 70, 70],
                                            cabecera_left_center=[True, False, True, True],
                                            detalle_left_center=[True, False, True, True],
                                            tamano_letra_cabecera=7)
                        add_graficos_circular_reporlab(datavalor=[(siporcampodetallado), (noporcampodetallado)],
                                                       datanombres=[u'%s' % ('AFIN'),
                                                                    u'%s' % ('NO AFIN')
                                                                    ],
                                                       anchografico=120, altografico=120,
                                                       colores=[verdeinstitucional, colors.gray],
                                                       labelspie=['AFIN - ' + str(siporcampodetallado) + '%', 'NO AFIN - ' + str(noporcampodetallado) + '%'],
                                                       posiciongrafico_x=200, posiciongrafico_y=20,
                                                       titulo='', tamanotitulo=10,
                                                       ubicaciontitulo_x=90, ubicaciontitulo_y=12)
                        add_titulo_reportlab(descripcion="CAMPO ESPECÍFICO", tamano=14, espacios=50)
                        add_tabla_reportlab(encabezado=[('Nº', 'ASIGNATURAS', 'TOTAL', '% PORCENTAJE')],
                                            detalles=[(1, 'AFIN', sicampoesp, siporcampoespecifico),
                                                      (2, 'NO AFIN', nocampoesp, noporcampoespecifico)
                                                      ],
                                            anchocol=[50, 70, 70, 70],
                                            cabecera_left_center=[True, False, True, True],
                                            detalle_left_center=[True, False, True, True],
                                            tamano_letra_cabecera=7)
                        add_graficos_circular_reporlab(datavalor=[(siporcampoespecifico), (noporcampoespecifico)],
                                                       datanombres=[u'%s' % ('AFIN'),
                                                                    u'%s' % ('NO AFIN')
                                                                    ],
                                                       anchografico=120, altografico=120,
                                                       colores=[verdeinstitucional, colors.gray],
                                                       labelspie=['AFIN - ' + str(siporcampoespecifico) + '%', 'NO AFIN - ' + str(noporcampoespecifico) + '%'],
                                                       posiciongrafico_x=200, posiciongrafico_y=50,
                                                       titulo='', tamanotitulo=10,
                                                       ubicaciontitulo_x=90, ubicaciontitulo_y=12)
                add_tabla_firma(detalles=[('______________________________________________________ ' + persona.apellido1 + ' ' + persona.apellido2 + ' ' + persona.nombres + '<br /> DECANO(A)',)],
                                anchocol=[300, ],
                                anchofila=100,
                                cabecera_left_center=[True, ],
                                detalle_left_center=[True, ])
                return generar_pdf_reportlab()
                # return conviert_html_to_pdf(
                #     'adm_criteriosactividadesdocente/listaafinidades_pdf.html',
                #     {
                #         'pagesize': 'A4',
                #         'data': data,
                #     }
                # )
            except Exception as ex:
                pass

        elif action == 'carrerascoordinacion':
            try:
                facultad = Coordinacion.objects.get(pk=request.POST['id'])
                lista = []
                idcarreras = ProfesorMateria.objects.values_list('materia__asignaturamalla__malla__carrera_id',
                                                                 flat=True).filter(tipoprofesor_id__in=[1, 14],
                                                                                   materia__nivel__periodo=periodo,
                                                                                   materia__asignaturamalla__malla__carrera__coordinacion=facultad,
                                                                                   materia__status=True,
                                                                                   status=True).exclude(
                    materia_id__in=Materia.objects.values_list('id').filter(
                        asignaturamalla__malla__carrera_id__in=[1, 3], asignaturamalla__nivelmalla_id__in=[7, 8, 9],
                        nivel__periodo=periodo, status=True))
                carreras = Carrera.objects.filter(pk__in=idcarreras)
                for carrera in carreras:
                    lista.append([carrera.id, carrera.__str__()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'criteriosinvestigacion':
            try:
                profesor = Profesor.objects.get(pk=int(request.POST['id']))
                distributivo = ProfesorDistributivoHoras.objects.get(pk=int(request.POST['iddistri']))
                for lista in request.POST['lista'].split('#'):
                    criterio = CriterioInvestigacionPeriodo.objects.get(pk=int(lista.split(',')[0]))
                    valor = float(lista.split(',')[1])
                    if valor > criterio.maximo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es mayor que el maximo permitido."})
                    if valor < criterio.minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es menor que el minimo permitido."})
                    if not DetalleDistributivo.objects.filter(distributivo=distributivo, criterioinvestigacionperiodo=criterio).exists():
                        detalle = DetalleDistributivo(distributivo=distributivo,
                                                      criteriodocenciaperiodo=None,
                                                      criterioinvestigacionperiodo=criterio,
                                                      criteriogestionperiodo=None,
                                                      criteriovinculacionperiodo=None,
                                                      horas=valor)
                        detalle.save(request)
                        detalle.verifica_actividades(horas=detalle.horas)
                        es_actividad_macro(detalle, periodo, request)
                        log(u'Adiciono criterio investigacion a docente: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "add")
                        if periodo.fechadesdenotificacion:
                            if periodo.fechadesdenotificacion <= datetime.now().date():
                                descripcion = u'Se adicionó criterio de investigacion: %s al profesor: %s con %s horas en el periodo de %s' % (criterio.criterio, profesor.persona.nombre_completo_inverso(), valor, criterio.periodo)
                                profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, periodo)
                    distributivo.save(request)
                    distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delcriterioinvestigacion':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                distributivo = detalle.distributivo
                log(u'Elimino detalle investigacion: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "del")
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        descripcion = u'Se eliminó criterio de investigación: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criterioinvestigacionperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                        detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, distributivo.periodo)
                detalle.delete()
                distributivo.actualiza_hijos()
                distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editcriterioinvestigacion':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                f = HorasCriterioForm(request.POST)
                if f.is_valid():
                    detalle.horas = float(f.cleaned_data['horas'])
                    detalle.save(request)
                    distributivo = detalle.distributivo
                    distributivo.save(request)
                    if detalle.horas > detalle.criterioinvestigacionperiodo.maximo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es mayor que el maximo permitido."})
                    if detalle.horas < detalle.criterioinvestigacionperiodo.minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es menor que el minimo permitido."})
                    sobrepasa = distributivo.total_horas() - distributivo.dedicacion.horas
                    # if sobrepasa > 0:
                    #     transaction.set_rollback(True)
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ha sobrepasado en %s hrs el limite de horas totales." % sobrepasa})
                    distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                    log(u'Modifico detalle investigacion: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "edit")
                    if periodo.fechadesdenotificacion:
                        if periodo.fechadesdenotificacion <= datetime.now().date():
                            descripcion = u'Se editó las horas de criterio de investigación: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criterioinvestigacionperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                            detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detalle.distributivo.periodo)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f'{ex}'})

        if action == 'criteriosgestion':
            try:
                profesor = Profesor.objects.get(pk=int(request.POST['id']))
                distributivo = ProfesorDistributivoHoras.objects.get(pk=int(request.POST['iddistri']))
                for lista in request.POST['lista'].split('#'):
                    criterio = CriterioGestionPeriodo.objects.get(pk=int(lista.split(',')[0]))
                    valor = float(lista.split(',')[1])
                    if valor > criterio.maximo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es mayor que el maximo permitido."})
                    if valor < criterio.minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es menor que el minimo permitido."})
                    if DetalleDistributivo.objects.filter(distributivo=distributivo, criteriogestionperiodo=criterio).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El criterio ya existe."})
                    detalle = DetalleDistributivo(distributivo=distributivo,
                                                  criteriodocenciaperiodo=None,
                                                  criterioinvestigacionperiodo=None,
                                                  criteriogestionperiodo=criterio,
                                                  criteriovinculacionperiodo=None,
                                                  horas=valor)
                    detalle.save(request)
                    detalle.verifica_actividades(horas=detalle.horas)
                    actualiza_usuario_revisa_actividad(request, profesor, criterio, distributivo, 'add')
                    log(u'Adiciono criterio gestion a docente: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "add")
                    if periodo.fechadesdenotificacion:
                        if periodo.fechadesdenotificacion <= datetime.now().date():
                            descripcion = u'Se adicionó criterio de gestión: %s al profesor: %s con %s horas en el periodo de %s' % (criterio.criterio, profesor.persona.nombre_completo_inverso(), valor, criterio.periodo)
                            profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, periodo)
                    distributivo.save(request)
                    distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'criteriosvinculacion':
            try:
                profesor = Profesor.objects.get(pk=int(request.POST['id']))
                distributivo = ProfesorDistributivoHoras.objects.get(pk=int(request.POST['iddistri']))
                for lista in request.POST['lista'].split('#'):
                    # criterio = CriterioVinculacionPeriodo.objects.get(pk=int(lista.split(',')[0]))
                    criterio = CriterioDocenciaPeriodo.objects.get(pk=int(lista.split(',')[0]))
                    valor = float(lista.split(',')[1])
                    if valor > criterio.maximo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es mayor que el maximo permitido."})
                    if valor < criterio.minimo:
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es menor que el minimo permitido."})
                    if DetalleDistributivo.objects.filter(distributivo=distributivo, criteriodocenciaperiodo=criterio).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El criterio ya existe."})
                    detalle = DetalleDistributivo(distributivo=distributivo,
                                                  criterioinvestigacionperiodo=None,
                                                  criteriogestionperiodo=None,
                                                  criteriodocenciaperiodo=criterio,
                                                  horas=valor)
                    detalle.save(request)
                    detalle.verifica_actividades(horas=detalle.horas)
                    log(u'Adiciono criterio vinculacion a docente: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "add")
                    if periodo.fechadesdenotificacion:
                        if periodo.fechadesdenotificacion <= datetime.now().date():
                            descripcion = u'Se adicionó criterio de vinculación: %s al profesor: %s con %s horas en el periodo de %s' % (criterio.criterio, profesor.persona.nombre_completo_inverso(), valor, criterio.periodo)
                            profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, periodo)
                    distributivo.save(request)
                    # distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addactividadvalor':
            try:
                idprofesor = int(request.POST['idprofesor'])
                idcriterio = int(request.POST['idcriterio'])
                valorcriterio = float(request.POST['valor'])
                tipo = request.POST['tipo']
                suma = 0
                for lista in request.POST['lista'].split('#'):
                    valor = float(lista.split(',')[2])
                    suma = suma + valor
                if suma > valorcriterio:
                    return JsonResponse({"result": "bad", "mensaje": u"Valores superan al valor del criterio."})

                for lista in request.POST['lista'].split('#'):
                    ida = int(lista.split(',')[0])
                    idr = int(lista.split(',')[1])
                    valor = float(lista.split(',')[2])
                    idmodalidad = int(lista.split(',')[3])
                    idtipoprofesor = int(lista.split(',')[4])
                    if tipo == '1':
                        actividad = ActividadDocenciaRecursoAprendizaje.objects.get(status=True, criterio_id=idcriterio, recurso__recursoaprendizaje_id=idr, recurso__periodoacademico=periodo, recurso__tipoprofesor_id=idtipoprofesor)
                        paaraaux = ProfesorAsignaturaActividadRecursoAprendizaje.objects.filter(status=True, asignatura_id=ida, profesor_id=idprofesor, actividaddocencia=actividad, modalidad=idmodalidad)
                        if not paaraaux:
                            paara = ProfesorAsignaturaActividadRecursoAprendizaje(asignatura_id=ida,
                                                                                  profesor_id=idprofesor,
                                                                                  actividaddocencia=actividad,
                                                                                  modalidad=idmodalidad,
                                                                                  valor=valor)
                        else:
                            paara = paaraaux[0]
                            paara.valor = valor
                    if tipo == '2':
                        actividad = ActividadInvestigacionRecursoAprendizaje.objects.get(status=True, criterio_id=idcriterio, recurso__recursoaprendizaje_id=idr, recurso__periodoacademico=periodo, recurso__tipoprofesor_id=idtipoprofesor)
                        paaraaux = ProfesorAsignaturaActividadRecursoAprendizaje.objects.filter(status=True, asignatura_id=ida, profesor_id=idprofesor, actividadinvestigacion=actividad, modalidad=idmodalidad)
                        if not paaraaux:
                            paara = ProfesorAsignaturaActividadRecursoAprendizaje(asignatura_id=ida,
                                                                                  profesor_id=idprofesor,
                                                                                  actividadinvestigacion=actividad,
                                                                                  modalidad=idmodalidad,
                                                                                  valor=valor)
                        else:
                            paara = paaraaux[0]
                            paara.valor = valor
                    if tipo == '3':
                        actividad = ActividadGestionRecursoAprendizaje.objects.get(status=True, criterio_id=idcriterio, recurso__recursoaprendizaje_id=idr, recurso__periodoacademico=periodo, recurso__tipoprofesor_id=idtipoprofesor)
                        paaraaux = ProfesorAsignaturaActividadRecursoAprendizaje.objects.filter(status=True, asignatura_id=ida, profesor_id=idprofesor, actividadgestion=actividad, modalidad=idmodalidad)
                        if not paaraaux:
                            paara = ProfesorAsignaturaActividadRecursoAprendizaje(asignatura_id=ida,
                                                                                  profesor_id=idprofesor,
                                                                                  actividadgestion=actividad,
                                                                                  modalidad=idmodalidad,
                                                                                  valor=valor)
                        else:
                            paara = paaraaux[0]
                            paara.valor = valor
                    paara.save(request)
                    log(u'Adiciono valor actividad recurso aprendizaje: %s' % (paara), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delcriteriogestion':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                distributivo = detalle.distributivo
                log(u'Elimino detalle gestion: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "del")
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        descripcion = u'Se eliminó criterio de gestión: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criteriogestionperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                        detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, distributivo.periodo)
                actualiza_usuario_revisa_actividad(request, detalle.distributivo.profesor, detalle.criteriogestionperiodo, distributivo, 'del')
                detalle.delete()
                distributivo.actualiza_hijos()
                distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'delcriteriovinculacion':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                distributivo = detalle.distributivo
                log(u'Elimino detalle vinculacion: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "del")
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        descripcion = u'Se eliminó criterio de vinculación: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criteriovinculacionperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                        detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, distributivo.periodo)
                detalle.delete()
                distributivo.actualiza_hijos()
                # distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'actualiza':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['id'])
                distributivo.profesor.actualizar_todo_distributivo_docente(request, distributivo.periodo)
                distributivo.actualiza_hijos()
                distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                log(u'Actualizo distributivo hijos: %s - periodo: %s' % (distributivo, distributivo.periodo), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'actualizatodo':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['iddistributivo'])
                distributivo.profesor.actualizar_todo_distributivo_docente(request, distributivo.periodo)
                distributivo.actualiza_hijos()
                distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'contaradmision':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=int(request.POST['id']))
                if not distributivo.cuentaadmision:
                    distributivo.cuentaadmision = True
                    distributivo.save(request)
                    tiposprofesores = TipoProfesor.objects.all().exclude(pk__in=[3, 4])
                    for tipoprofesor in tiposprofesores:
                        distributivo.profesor.actualizar_distributivo_horas(request, distributivo.periodo, tipoprofesor.id)
                    log(u'No cuenta admision en distributivo del docente: %s - %s - %s' % (distributivo, distributivo.cuentaadmision, distributivo.periodo), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'nocontaradmision':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=int(request.POST['id']))
                if distributivo.cuentaadmision:
                    distributivo.cuentaadmision = False
                    distributivo.save(request)
                    tiposprofesores = TipoProfesor.objects.all().exclude(pk__in=[3, 4])
                    for tipoprofesor in tiposprofesores:
                        distributivo.profesor.actualizar_distributivo_horas(request, distributivo.periodo, tipoprofesor.id)
                    log(u'Cuenta admision en distributivo del docente: %s - %s - %s' % (distributivo, distributivo.cuentaadmision, distributivo.periodo), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delactividad':
            try:
                actividad = ActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                detalledistributivo = actividad.criterio
                criterio = actividad.criterio
                log(u'Elimino actividad de criterio: %s - periodo: %s' % (actividad, actividad.criterio.distributivo.periodo), request, "del")
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        descripcion = u'Se Eliminó la actividad %s con fechas desde %s hasta %s con %s horas al profesor %s en el periodo de %s' % (actividad.nombre, actividad.desde, actividad.hasta, actividad.horas, actividad.criterio.distributivo.profesor.persona.nombre_completo_inverso(), actividad.criterio.distributivo.periodo)
                        actividad.criterio.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, actividad.criterio.distributivo.periodo)
                actividad.delete()
                # criterio.verifica_actividades()
                detalledistributivo.horas = detalledistributivo.total_horas()
                detalledistributivo.save()
                detalledistributivo.actualiza_padre()
                criterio.distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editcriteriogestion':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                f = HorasCriterioForm(request.POST)
                if f.is_valid():
                    detalle.horas = float(f.cleaned_data['horas'])
                    detalle.save(request)
                    distributivo = detalle.distributivo
                    distributivo.save(request)
                    if detalle.horas > detalle.criteriogestionperiodo.maximo:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es mayor que el maximo permitido."})
                    if detalle.horas < detalle.criteriogestionperiodo.minimo:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es menor que el minimo permitido."})
                    distributivo = detalle.distributivo
                    sobrepasa = distributivo.total_horas() - distributivo.dedicacion.horas
                    if sobrepasa > 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Ha sobrepasado en %s hrs el limite de horas totales." % sobrepasa})
                    distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                    log(u'Modifico detalle gestion: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "edit")
                    if periodo.fechadesdenotificacion:
                        if periodo.fechadesdenotificacion <= datetime.now().date():
                            descripcion = u'Se editó las horas de criterio de gestión: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criteriogestionperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                            detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detalle.distributivo.periodo)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcriteriovinculacion':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                f = HorasCriterioForm(request.POST)
                if f.is_valid():
                    detalle.horas = float(f.cleaned_data['horas'])
                    detalle.save(request)
                    distributivo = detalle.distributivo
                    distributivo.save(request)
                    if detalle.horas > detalle.criteriodocenciaperiodo.maximo:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es mayor que el maximo permitido."})
                    if detalle.horas < detalle.criteriodocenciaperiodo.minimo:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"El valor de horas es menor que el minimo permitido."})
                    distributivo = detalle.distributivo
                    sobrepasa = distributivo.total_horas() - distributivo.dedicacion.horas
                    if sobrepasa > 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Ha sobrepasado en %s hrs el limite de horas totales." % sobrepasa})
                    # distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                    log(u'Modifico detalle vinculacion: %s - periodo: %s' % (detalle, detalle.distributivo.periodo), request, "edit")
                    if periodo.fechadesdenotificacion:
                        if periodo.fechadesdenotificacion <= datetime.now().date():
                            descripcion = u'Se editó las horas de criterio de vinculación: %s al profesor: %s con %s horas en el periodo de %s' % (detalle.criteriogestionperiodo.criterio, detalle.distributivo.profesor.persona.nombre_completo_inverso(), detalle.horas, detalle.distributivo.periodo)
                            detalle.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detalle.distributivo.periodo)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminaractividaddocente':
            try:
                actividad = ClaseActividad.objects.get(pk=request.POST['idactividad'])
                nomturno = actividad.turno
                nomdia = actividad.dia
                if actividad.tipodistributivo == 1:
                    tipodes = 'DOCENCIA'
                    des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                if actividad.tipodistributivo == 2:
                    tipodes = 'INVESTIGACION'
                    des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                if actividad.tipodistributivo == 3:
                    tipodes = 'GESTION'
                    des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                idturno = actividad.turno
                iddia = actividad.dia
                actividad.delete()
                log(u'Eliminó horario de actividad: %s - %s  turno: %s dia: %s - periodo: %s' % (des, tipodes, str(nomturno), str(nomdia), actividad.detalledistributivo.distributivo.periodo), request, "add")
                datatemplate = {}
                datatemplate['idturno'] = idturno
                datatemplate['iddia'] = iddia
                datatemplate['periodo'] = periodo
                datatemplate['tipoelimina'] = request.POST['tipoelimina']
                datatemplate['profe'] = actividad.detalledistributivo.distributivo.profesor
                template = get_template("adm_criteriosactividadesdocente/listaactividadesdocente.html")
                json_content = template.render(datatemplate)
                return JsonResponse({"result": "ok", 'datos': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'editar_fecha':
            try:
                actividad = ClaseActividad.objects.get(pk=request.POST['idactividad'])
                actividad.inicio = convertir_fecha(request.POST['fecha_desde'])
                actividad.fin = convertir_fecha(request.POST['fecha_hasta'])
                idturno = actividad.turno
                iddia = actividad.dia
                actividad.save(request)
                log(u'Gestion Academica modifico las fechas %s - periodo: %s' % (actividad, actividad.detalledistributivo.distributivo.periodo), request, "edit")
                datatemplate = {}
                datatemplate['idturno'] = idturno
                datatemplate['iddia'] = iddia
                datatemplate['periodo'] = periodo
                datatemplate['tipoelimina'] = '0'
                datatemplate['profe'] = actividad.detalledistributivo.distributivo.profesor
                template = get_template("adm_criteriosactividadesdocente/listaactividadesdocente.html")
                json_content = template.render(datatemplate)
                return JsonResponse({"result": "ok", 'datos': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar las fechas."})

        if action == 'addactividaddocente':
            try:
                periodo = request.session['periodo']
                detalle = DetalleDistributivo.objects.filter(pk=request.POST['idactividad'], status=True)[0]
                if ClaseActividad.objects.filter(Q(inicio__lte=request.POST['feinicio'], fin__gte=request.POST['feinicio'], turno_id=request.POST['idturno'], dia=request.POST['iddia'], detalledistributivo__distributivo__id=detalle.distributivo_id) | Q(inicio__lte=request.POST['fefin'], fin__gte=request.POST['fefin'], turno_id=request.POST['idturno'], dia=request.POST['iddia'], detalledistributivo__distributivo__id=detalle.distributivo_id)).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Fecha ya existe."})
                actividad = ClaseActividad(detalledistributivo_id=request.POST['idactividad'],
                                           tipodistributivo=request.POST['tipoactividad'],
                                           turno_id=request.POST['idturno'],
                                           dia=request.POST['iddia'],
                                           inicio=request.POST['feinicio'],
                                           fin=request.POST['fefin'],
                                           estadosolicitud=1)
                actividad.save(request)
                tipo = actividad.tipodistributivo
                if tipo == '1':
                    tipodes = 'DOCENCIA'
                    des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                if tipo == '2':
                    tipodes = 'INVESTIGACION'
                    des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                if tipo == '3':
                    tipodes = 'GESTION'
                    des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                # Template para rellenar de nuevo e div
                datatemplate = {}
                datatemplate['idturno'] = actividad.turno
                datatemplate['iddia'] = actividad.dia
                datatemplate['periodo'] = periodo
                datatemplate['profe'] = detalle.distributivo.profesor
                template = get_template("adm_criteriosactividadesdocente/listaactividadesdocente.html")
                json_content = template.render(datatemplate)
                log(u'Adicionó horario de actividad: %s - %s  turno: %s dia: %s - periodo: %s' % (des, tipodes, str(actividad.turno), str(actividad.dia), actividad.detalledistributivo.distributivo.periodo), request, "add")
                return JsonResponse({"result": "ok", "codiactividad": actividad.id, 'datos': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addactividad':
            try:
                detalle = DetalleDistributivo.objects.get(pk=request.POST['id'])
                f = ActividadCriterioForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['desde'] > f.cleaned_data['hasta']:
                        return JsonResponse({"result": "bad", "mensaje": u"Fechas incorrectas."})
                    if ActividadDetalleDistributivo.objects.values_list('id').filter(status=True, criterio=detalle, nombre=f.cleaned_data['texto'].upper()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Registro ya existe."})
                    actividad = ActividadDetalleDistributivo(criterio=detalle,
                                                             nombre=f.cleaned_data['texto'],
                                                             desde=f.cleaned_data['desde'],
                                                             hasta=f.cleaned_data['hasta'],
                                                             horas=f.cleaned_data['horas'], vigente=True)
                    actividad.save(request)
                    actualiza_registro_horario_docente(actividad, 'add')
                    actividad.actualiza_padre()
                    log(u'Adiciono actividad de criterio: %s - periodo: %s' % (actividad, actividad.criterio.distributivo.periodo), request, "edit")
                    if periodo.fechadesdenotificacion:
                        if periodo.fechadesdenotificacion <= datetime.now().date():
                            descripcion = u'Se adicionó la actividad %s con fechas desde %s hasta %s con %s horas al profesor %s en el periodo de %s' % (actividad.nombre, actividad.desde, actividad.hasta, actividad.horas, actividad.criterio.distributivo.profesor.persona.nombre_completo_inverso(), actividad.criterio.distributivo.periodo)
                            actividad.criterio.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, actividad.criterio.distributivo.periodo)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al guardar los datos. {ex.__str__()}"})

        if action == 'pdf_horarios':
            try:
                data = {}
                data['periodo'] = periodo = request.session['periodo']
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=No tiene permiso para imprimir en el periodo seleccionado.")
                data['profesor'] = profesor = Profesor.objects.filter().distinct().get(pk=request.POST['profesor'])
                data['puede_ver_horario'] = periodo.visible == True and periodo.visiblehorario == True
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],
                                  [6, 'Sabado'], [7, 'Domingo']]
                turnoclases = Turno.objects.filter(status=True, clase__activo=True, clase__materia__nivel__periodo=periodo, clase__materia__profesormateria__profesor=profesor, clase__materia__profesormateria__principal=True).values_list('id', flat=True).distinct().order_by('comienza')
                if ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo, detalledistributivo__distributivo__profesor=profesor).exists():
                    turnoactividades = Turno.objects.filter(status=True, claseactividad__detalledistributivo__distributivo__periodo=periodo, claseactividad__detalledistributivo__distributivo__profesor=profesor).values_list('id', flat=True).distinct().order_by('comienza')
                else:
                    turnoactividades = Turno.objects.filter(status=True, claseactividad__actividaddetalle__criterio__distributivo__periodo=periodo, claseactividad__actividaddetalle__criterio__distributivo__profesor=profesor).values_list('id', flat=True).distinct().order_by('comienza')
                # data['turnos'] = turnoclases | turnoactividades
                data['turnos'] = Turno.objects.filter(Q(status=True), Q(id__in=turnoclases) | Q(id__in=turnoactividades)).distinct('comienza', 'termina')
                data['aprobado'] = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True, estadosolicitud=2).order_by('-id').exists()
                return conviert_html_to_pdf(
                    'docentes/horario_pfd.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as e:
                print(e)

        if action == 'editactividad':
            try:
                hoy = datetime.now()
                actividad = ActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                hrs_actividad = ActividadDetalleDistributivo.objects.filter(status=True,
                                                                            criterio__distributivo__profesor__persona=actividad.criterio.distributivo.profesor.persona,
                                                                            desde__lte=hoy.date(),
                                                                            hasta__gte=hoy.date()
                                                                            ).aggregate(hrs_doce=Sum('horas'))['hrs_doce']
                f = ActividadCriterioForm(request.POST)
                if f.is_valid():
                    if ActividadDetalleDistributivo.objects.values_list('id').filter(status=True, criterio=actividad.criterio, nombre=f.cleaned_data['texto'].upper()).exclude(pk=actividad.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Registro ya existe."})
                    dif_hrs = actividad.horas - f.cleaned_data['horas']
                    if f.cleaned_data['desde'] > f.cleaned_data['hasta']:
                        return JsonResponse({"result": "bad", "mensaje": u"Fechas incorrectas."})

                    actividad.nombre = f.cleaned_data['texto']
                    actividad.desde = f.cleaned_data['desde']
                    actividad.hasta = f.cleaned_data['hasta']
                    actividad.horas = f.cleaned_data['horas']
                    actividad.save(request)
                    actividad.actualiza_padre()
                    if periodo.tipo.id in [3, 4]:
                        contrato = ContratoDip.objects.filter(status=True,
                                                              persona=actividad.criterio.distributivo.profesor.persona,
                                                              fechainicio__lte=hoy.date(),
                                                              fechafin__gte=hoy.date()).order_by('-id').first()
                        if contrato:
                            hrs_totales = contrato.get_tiempo_dedicacion()
                            actividades_hrs =  hrs_actividad + dif_hrs
                            if actividades_hrs > hrs_totales: raise NameError(f'Suma un total de {actividades_hrs} horas semanales y su maximo de horas semanales es {hrs_totales}')

                    if actividad.criterio.distributivo.sobrepasa_horas():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Limite de horas a sobrepasado."})
                    log(u'Modifico actividad de criterio: %s - periodo: %s ' % (actividad, actividad.criterio.distributivo.periodo), request, "edit")
                    if periodo.fechadesdenotificacion:
                        if periodo.fechadesdenotificacion <= datetime.now().date():
                            descripcion = u'Se edito la actividad %s con fechas desde %s hasta %s con %s horas al profesor %s en el periodo de %s' % (actividad.nombre, actividad.desde, actividad.hasta, actividad.horas, actividad.criterio.distributivo.profesor.persona.nombre_completo_inverso(), actividad.criterio.distributivo.periodo)
                            actividad.criterio.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, actividad.criterio.distributivo.periodo)

                    actualiza_registro_horario_docente(actividad, 'edit')
                    # Actualizamos la fecha de las subactividades
                    actividad.subactividaddetalledistributivo_set.filter(status=True).update(fechainicio=actividad.desde, fechafin=actividad.hasta)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                # return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                return JsonResponse({"result": "bad", "mensaje": str(ex)})

        if action == 'evaluaestudiante':
            try:
                valor = 0
                detdistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['idactividad'])), status=True)
                if detdistributivo.hetero:
                    detdistributivo.hetero = False
                    detdistributivo.save(request)
                    descripcion = u'Se %s el criterio %s para evaluar hetero al profesor %s en el periodo de %s' % (('activo' if detdistributivo.hetero else 'desactivo'), detdistributivo.nombre(), detdistributivo.distributivo.profesor.persona.nombre_completo_inverso(), detdistributivo.distributivo.periodo)
                    log(descripcion, request, "edit")
                    # log(u'Se desactivo la actividad hetero: %s - periodo: %s' % (detdistributivo, detdistributivo.distributivo.periodo), request, "edit")
                else:
                    detdistributivo.hetero = True
                    detdistributivo.save(request)
                    valor = 1
                    descripcion = u'Se %s el criterio %s para evaluar hetero al profesor %s en el periodo de %s' % (('activo' if detdistributivo.hetero else 'desactivo'), detdistributivo.nombre(), detdistributivo.distributivo.profesor.persona.nombre_completo_inverso(), detdistributivo.distributivo.periodo)
                    log(descripcion, request, "edit")
                    # log(u'Se activo la actividad hetero: %s - periodo: %s' % (detdistributivo, detdistributivo.distributivo.periodo), request, "edit")
                if detdistributivo.criteriodocenciaperiodo:
                    if 'motivo' in request.POST:
                        motivocriterio = MotivoCriterioDetalleDistributivo(detalledistributivo=detdistributivo,
                                                                           motivo=request.POST['motivo'],
                                                                           estado='Evalúan estudiantes' if detdistributivo.hetero else 'No evalúan estudiantes')
                        motivocriterio.save(request)
                        log(u'Se adiciono auditoria el motivo criterio de detalle de distributivo: %s - periodo: %s' % (motivocriterio, detdistributivo.distributivo.periodo), request, "add")
                        descripcion = u'%s con motivo %s quedando el estado %s' % (descripcion, motivocriterio.motivo, motivocriterio.estado)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos, debe digitar un motivo."})
                detdistributivo.distributivo.calcular_ponderaciones()
                detdistributivo.distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        detdistributivo.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detdistributivo.distributivo.periodo)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'evaluadirectivo':
            try:
                valor = 0
                detdistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['idactividad'])), status=True)
                if detdistributivo.evaluadirectivo:
                    detdistributivo.evaluadirectivo = False
                    detdistributivo.save(request)
                    descripcion = u'Se %s el criterio %s para evaluar directivo al profesor %s en el periodo de %s' % (('activo' if detdistributivo.evaluadirectivo else 'desactivo'), detdistributivo.nombre(), detdistributivo.distributivo.profesor.persona.nombre_completo_inverso(), detdistributivo.distributivo.periodo)
                    log(descripcion, request, "edit")
                    # log(u'Se desactivo la actividad directivo: %s - periodo: %s' % (detdistributivo, detdistributivo.distributivo.periodo), request, "edit")
                else:
                    detdistributivo.evaluadirectivo = True
                    detdistributivo.save(request)
                    valor = 1
                    descripcion = u'Se %s el criterio %s para evaluar directivo al profesor %s en el periodo de %s' % (('activo' if detdistributivo.evaluadirectivo else 'desactivo'), detdistributivo.nombre(), detdistributivo.distributivo.profesor.persona.nombre_completo_inverso(), detdistributivo.distributivo.periodo)
                    log(descripcion, request, "edit")
                    # log(u'Se activo la actividad directivo: %s - periodo: %s' % (detdistributivo, detdistributivo.distributivo.periodo), request, "edit")
                if detdistributivo.criteriodocenciaperiodo:
                    if 'motivo' in request.POST:
                        motivocriterio = MotivoCriterioDetalleDistributivo(detalledistributivo=detdistributivo,
                                                                           motivo=request.POST['motivo'],
                                                                           estado='Evalúan directivos' if detdistributivo.evaluadirectivo else 'No evalúan directivos')
                        motivocriterio.save(request)
                        log(u'Se adiciono auditoria el motivo criterio de detalle de distributivo: %s - periodo: %s' % (motivocriterio, detdistributivo.distributivo.periodo), request, "add")
                        descripcion = u'%s con motivo %s quedando el estado %s' % (descripcion, motivocriterio.motivo, motivocriterio.estado)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos, debe digitar un motivo."})
                detdistributivo.distributivo.calcular_ponderaciones()
                detdistributivo.distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        detdistributivo.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detdistributivo.distributivo.periodo)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'auditoriacriterio':
            try:
                data['detalle'] = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id'])))
                template = get_template("adm_criteriosactividadesdocente/auditoriadetalledistributivo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        if action == 'evaluapar':
            try:
                valor = 0
                detdistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['idactividad'])), status=True)
                if detdistributivo.evaluapar:
                    detdistributivo.evaluapar = False
                    detdistributivo.save(request)
                    descripcion = u'Se %s el criterio %s para evaluar par al profesor %s en el periodo de %s' % (('activo' if detdistributivo.evaluapar else 'desactivo'), detdistributivo.nombre(), detdistributivo.distributivo.profesor.persona.nombre_completo_inverso(), detdistributivo.distributivo.periodo)
                    log(descripcion, request, "edit")
                    # log(u'Se desactivo la actividad evalua par: %s - periodo: %s' % (detdistributivo, detdistributivo.distributivo.periodo), request, "edit")
                else:
                    detdistributivo.evaluapar = True
                    detdistributivo.save(request)
                    valor = 1
                    descripcion = u'Se %s el criterio %s para evaluar par al profesor %s en el periodo de %s' % (('activo' if detdistributivo.evaluapar else 'desactivo'), detdistributivo.nombre(), detdistributivo.distributivo.profesor.persona.nombre_completo_inverso(), detdistributivo.distributivo.periodo)
                    log(descripcion, request, "edit")
                    # log(u'Se activo la actividad evalua par: %s - periodo: %s' % (detdistributivo, detdistributivo.distributivo.periodo), request, "edit")
                if detdistributivo.criteriodocenciaperiodo:
                    if 'motivo' in request.POST:
                        motivocriterio = MotivoCriterioDetalleDistributivo(detalledistributivo=detdistributivo,
                                                                           motivo=request.POST['motivo'],
                                                                           estado='Evalúan par' if detdistributivo.evaluapar else 'No evalúan par')
                        motivocriterio.save(request)
                        log(u'Se adiciono auditoria el motivo criterio de detalle de distributivo: %s - periodo: %s' % (motivocriterio, detdistributivo.distributivo.periodo), request, "add")
                        descripcion = u'%s con motivo %s quedando el estado %s' % (descripcion, motivocriterio.motivo, motivocriterio.estado)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos, debe digitar un motivo."})
                detdistributivo.distributivo.calcular_ponderaciones()
                detdistributivo.distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        detdistributivo.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detdistributivo.distributivo.periodo)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'evaluaauto':
            try:
                valor = 0
                detdistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['idactividad'])), status=True)
                if detdistributivo.evaluaauto:
                    detdistributivo.evaluaauto = False
                    detdistributivo.save(request)
                    descripcion = u'Se %s el criterio %s para evaluar autoevaluacion al profesor %s en el periodo de %s' % (('activo' if detdistributivo.evaluaauto else 'desactivo'), detdistributivo.nombre(), detdistributivo.distributivo.profesor.persona.nombre_completo_inverso(), detdistributivo.distributivo.periodo)
                    log(descripcion, request, "edit")
                    # log(u'Se desactivo la actividad evalua par: %s - periodo: %s' % (detdistributivo, detdistributivo.distributivo.periodo), request, "edit")
                else:
                    detdistributivo.evaluaauto = True
                    detdistributivo.save(request)
                    valor = 1
                    descripcion = u'Se %s el criterio %s para evaluar autoevaluacion al profesor %s en el periodo de %s' % (('activo' if detdistributivo.evaluaauto else 'desactivo'), detdistributivo.nombre(), detdistributivo.distributivo.profesor.persona.nombre_completo_inverso(), detdistributivo.distributivo.periodo)
                    log(descripcion, request, "edit")
                    # log(u'Se activo la actividad evalua par: %s - periodo: %s' % (detdistributivo, detdistributivo.distributivo.periodo), request, "edit")
                if detdistributivo.criteriodocenciaperiodo:
                    if 'motivo' in request.POST:
                        motivocriterio = MotivoCriterioDetalleDistributivo(detalledistributivo=detdistributivo,
                                                                           motivo=request.POST['motivo'],
                                                                           estado='Evalúan autoevaluacion' if detdistributivo.evaluaauto else 'No evalúan autoevaluacion')
                        motivocriterio.save(request)
                        log(u'Se adiciono auditoria el motivo criterio de detalle de distributivo: %s - periodo: %s' % (motivocriterio, detdistributivo.distributivo.periodo), request, "add")
                        descripcion = u'%s con motivo %s quedando el estado %s' % (descripcion, motivocriterio.motivo, motivocriterio.estado)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos, debe digitar un motivo."})
                detdistributivo.distributivo.calcular_ponderaciones()
                detdistributivo.distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                if periodo.fechadesdenotificacion:
                    if periodo.fechadesdenotificacion <= datetime.now().date():
                        detdistributivo.distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, detdistributivo.distributivo.periodo)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'cambiodedicacion':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['id'])
                idtipoprofesor = 0
                if distributivo.profesor.profesormateria_set.all().exists():
                    idtipoprofesor = distributivo.profesor.profesormateria_set.all()[0].tipoprofesor_id
                f = DedicacionProfesorForm(request.POST)
                if f.is_valid():
                    distributivo.dedicacion = f.cleaned_data['dedicacion']
                    distributivo.save(request)
                    # distributivohoras = distributivo.detalledistributivo_set.filter((Q(criteriodocenciaperiodo__criterio__id=CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID) | Q(criteriodocenciaperiodo__criterio__id=CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID) | Q(criteriodocenciaperiodo__criterio__id=CRITERIO_HORAS_CLASE_PARCIAL_ID)), criteriodocenciaperiodo__isnull=False).delete()
                    if idtipoprofesor > 0:
                        distributivo.profesor.actualizar_distributivo_horas(request, distributivo.periodo, idtipoprofesor)
                    distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
                    log(u'Modifico dedicacion de profesor: %s - periodo: %s' % (distributivo.profesor, distributivo.periodo), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'adddocente':
            try:
                f = DistributivoProfesorForm(request.POST)
                if f.is_valid():
                    programas = ProfesorDistributivoHoras(profesor_id=f.cleaned_data['profesor'],
                                                          coordinacion_id=request.POST['coordinacion'],
                                                          carrera=f.cleaned_data['carrera'],
                                                          periodo=periodo
                                                          )
                    programas.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

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
                    # if tienetablaponderacion:
                    #     if periodo.fechadesdenotificacion:
                    #         if periodo.fechadesdenotificacion <= datetime.now().date():
                    #             descripcion = u'Se %s tabla de ponderación %s al profesor %s en el periodo de %s' % (('editó' if tienetablaponderacion else 'adicionó'), distributivo.tablaponderacion.nombre, distributivo.profesor.persona.nombre_completo_inverso(), distributivo.periodo)
                    #             distributivo.profesor.mail_notificar_procesoevaluacion(request.session['nombresistema'], descripcion, persona, distributivo.periodo)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'guardarresponsable':
            try:
                profesor = Profesor.objects.get(pk=request.POST['idprofesor'])
                coordinacion = persona.mis_coordinaciones()[0]
                if request.POST['idtipo'] == '1':
                    criterio = CriterioDocencia.objects.filter(pk=request.POST['idcriterio'])[0]
                    if EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinacion, profesor=profesor, criteriodocencia=criterio).exists():
                        encargadocriterioperiodo = EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinacion, profesor=profesor, criteriodocencia=criterio)[0]
                        encargadocriterioperiodo.profesor = profesor
                    else:
                        encargadocriterioperiodo = EncargadoCriterioPeriodo(periodo=periodo,
                                                                            coordinacion=coordinacion,
                                                                            profesor=profesor,
                                                                            criteriodocencia=criterio)
                    encargadocriterioperiodo.save(request)
                elif request.POST['idtipo'] == '2':
                    criterio = CriterioInvestigacion.objects.filter(pk=request.POST['idcriterio'])[0]
                    if EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinacion, profesor=profesor, criterioinvestigacion=criterio).exists():
                        encargadocriterioperiodo = EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinacion, profesor=profesor, criterioinvestigacion=criterio)[0]
                        encargadocriterioperiodo.profesor = profesor
                    else:
                        encargadocriterioperiodo = EncargadoCriterioPeriodo(periodo=periodo,
                                                                            coordinacion=coordinacion,
                                                                            profesor=profesor,
                                                                            criterioinvestigacion=criterio)
                    encargadocriterioperiodo.save(request)
                elif request.POST['idtipo'] == '3':
                    criterio = CriterioGestion.objects.filter(pk=request.POST['idcriterio'])[0]
                    if EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinacion, profesor=profesor, criteriogestion=criterio).exists():
                        encargadocriterioperiodo = EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinacion, profesor=profesor, criteriogestion=criterio)[0]
                        encargadocriterioperiodo.profesor = profesor
                    else:
                        encargadocriterioperiodo = EncargadoCriterioPeriodo(periodo=periodo,
                                                                            coordinacion=coordinacion,
                                                                            profesor=profesor,
                                                                            criteriogestion=criterio)
                    encargadocriterioperiodo.save(request)

                else:
                    criterio = CriterioVinculacion.objects.filter(pk=request.POST['idcriterio'])[0]
                    if EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinacion,
                                                               profesor=profesor, criteriovinculacion=criterio).exists():
                        encargadocriterioperiodo = EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinacion, profesor=profesor, criteriovinculacion=criterio)[0]
                        encargadocriterioperiodo.profesor = profesor
                    else:
                        encargadocriterioperiodo = EncargadoCriterioPeriodo(periodo=periodo,
                                                                            coordinacion=coordinacion,
                                                                            profesor=profesor,
                                                                            criteriovinculacion=criterio)
                    encargadocriterioperiodo.save(request)
                log(u'Modifico responsable de criterio: %s - %s - periodo: %s' % (encargadocriterioperiodo, criterio, encargadocriterioperiodo.periodo), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'marcadas':
            try:
                fechai = convertir_fecha(request.POST['fecha_desde'])
                fechaf = convertir_fecha(request.POST['fecha_hasta'])
                coordinaciones = persona.mis_coordinaciones()
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'asistencias'))
                __author__ = 'Unemi'
                style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                style0_red = easyxf('font: name Times New Roman, color-index red, bold off', num_format_str='#,##0.00')
                style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = easyxf('font: name Times New Roman, color-index black, bold on; alignment: horiz centre')
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                nombre = "AVANCE_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                ruta = "media/asistencias/" + nombre
                filename = os.path.join(output_folder, nombre)
                for coord in coordinaciones:
                    ws = wb.add_sheet(coord.alias)
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write(1, 0, "Periodo: " + periodo.nombre, font_style2)
                    ws.write(2, 0, "Fecha Desde: " + request.POST['fecha_desde'], font_style2)
                    ws.write(3, 0, "Fecha Hasta: " + request.POST['fecha_hasta'], font_style2)
                    ws.write(4, 0, "Facultad: %s" % coord, font_style2)
                    book = xlwt.Workbook()
                    columns = [
                        (u"CEDULA", 4000),
                        (u"DOCENTE", 9000),
                        (u"H. DISTR. SEMANAL", 3500),
                        (u"H. CLASES MENSUAL.", 3500),
                        (u"H. ACTIVIDAD MENSUAL.", 3500),
                        (u"H. ASISTENCIAS SGA", 3500),
                        (u"H. CLASES FERIADOS O EXAMEN", 3500),
                        (u"H. ACTIVIDAD FERIADOS O EXAMEN", 3500),
                        (u"H. FALTAS SGA", 3500),
                        (u"H. MARCAJE BIOMETRICO", 3500),
                        (u"H. FALTAS BIOMETRICO", 3500),
                        (u"H. ATRASO BIOMETRICO", 3500),
                    ]
                    row_num = 6
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 7
                    for dis in ProfesorDistributivoHoras.objects.filter(coordinacion=coord, periodo=periodo).order_by('profesor').exclude(horasdocencia=0, horasgestion=0, horasinvestigacion=0):
                        ws.write(row_num, 0, dis.profesor.persona.cedula, font_style2)
                        ws.write(row_num, 1, dis.profesor.persona.nombre_completo_inverso(), font_style2)
                        ws.write(row_num, 2, dis.profesor.cantidad_total_horas_criterios(periodo=periodo), style0)
                        fecha = fechai
                        cancla = cancla_acti = canasi = diafer = diafer_acti = hbiome = fbiome = 0
                        atraso = "00:00:00"
                        while fecha <= fechaf:
                            cladia = cladia_acti = 0
                            clases = Clase.objects.filter(activo=True, inicio__lte=fecha, fin__gte=fecha, dia=fecha.isoweekday(), materia__profesormateria__profesor=dis.profesor, materia__profesormateria__principal=True, materia__profesormateria__tipoprofesor_id__in=[1, 2, 5, 6], tipoprofesor_id__in=[1, 2, 5, 6]).order_by('turno__comienza')
                            clasesactividad = ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=dis.profesor, inicio__lte=fecha, fin__gte=fecha, dia=fecha.isoweekday(), status=True, estadosolicitud__in=[1, 2]).order_by("turno__comienza")
                            intout = []
                            for cl in clases:
                                if cladia == 0:
                                    intout.append(cl.turno.comienza)
                                cladia += 1
                                if cladia == clases.count():
                                    intout.append(cl.turno.termina)
                            for cl in clasesactividad:
                                if len(intout) == 2:
                                    if intout[0] > cl.turno.comienza:
                                        intout[0] = cl.turno.comienza
                                    if intout[1] < cl.turno.termina:
                                        intout[1] = cl.turno.termina
                                    cladia_acti += 1
                                else:
                                    if cladia_acti == 0:
                                        intout.append(cl.turno.comienza)
                                    cladia_acti += 1
                                    if cladia_acti == clasesactividad.count():
                                        intout.append(cl.turno.termina)

                            cancla += cladia
                            cancla_acti += cladia_acti
                            if not DiasNoLaborable.objects.filter(fecha=fecha).exclude(periodo__isnull=True).exists():
                                canasi += Leccion.objects.filter(fecha=fecha, clase__materia__profesormateria__profesor=dis.profesor, status=True, clase__materia__profesormateria__principal=True, clase__materia__profesormateria__tipoprofesor_id=TIPO_DOCENTE_TEORIA).count()
                                if LogDia.objects.filter(fecha=fecha, status=True, persona=dis.profesor.persona).exists():
                                    logmarcada = LogDia.objects.get(fecha=fecha, status=True, persona=dis.profesor.persona).logmarcada_set.filter(status=True).order_by("time")
                                    if logmarcada.count() >= 2:
                                        hbiome += cladia_acti
                                        hbiome += cladia
                                        mintout = []
                                        c = 0
                                        for lm in logmarcada:
                                            if c == 0:
                                                mintout.append(lm.time.time())
                                            c += 1
                                            if c == logmarcada.count():
                                                mintout.append(lm.time.time())
                                        if len(intout) > 0 and len(mintout) > 0:
                                            if mintout[0] > intout[0]:
                                                atraso = sumar_hora(str(atraso), str(datetime.combine(date.today(), mintout[0]) - datetime.combine(date.today(), intout[0])))
                                            if intout[1] > mintout[1]:
                                                atraso = sumar_hora(str(atraso), str(datetime.combine(date.today(), intout[1]) - datetime.combine(date.today(), mintout[1])))
                                    else:
                                        fbiome += cladia
                                        fbiome += cladia_acti
                                else:
                                    fbiome += cladia
                                    fbiome += cladia_acti
                            else:
                                diafer += cladia
                                diafer_acti += cladia_acti
                            fecha = fecha + timedelta(hours=24)
                        (h, m, s) = [int(x) for x in atraso.split(":")]
                        if m > 50:
                            h += 1
                        ws.write(row_num, 3, cancla, style0)
                        ws.write(row_num, 4, cancla_acti, style0)
                        ws.write(row_num, 5, canasi, style0)
                        ws.write(row_num, 6, diafer, style0_red)
                        ws.write(row_num, 7, diafer_acti, style0_red)
                        ws.write(row_num, 8, (cancla - (canasi + diafer)) if (cancla - (canasi + diafer)) > 0 else 0, style0_red if (cancla - (canasi + diafer)) > 0 else style0)
                        ws.write(row_num, 9, (hbiome - h), style0)
                        ws.write(row_num, 10, fbiome, style0_red if fbiome > 0 else style0)
                        ws.write(row_num, 11, h, style0_red if h > 0 else style0)
                        row_num += 1
                wb.save(filename)
                # return book
                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                pass

        if action == 'reporteindividual':
            try:
                idmat = request.POST['idmat']
                tutorias = AvPreguntaRespuesta.objects.filter(status=True, avpreguntadocente__status=True,
                                                              avpreguntadocente__materiaasignada__matricula__inscripcion__persona__status=True,
                                                              avpreguntadocente__materiaasignada__materia__status=True,
                                                              avpreguntadocente__materiaasignada__materia__id=idmat)
                materia = Materia.objects.get(pk=idmat)
                carrera = materia.asignaturamalla.malla.carrera.nombre_completo()
                asignatura = materia.asignatura.nombre
                docente = materia.profesormateria_set.get(status=True, principal=True, activo=True)
                docente = docente.profesor.persona.nombre_completo()
                periodo = materia.nivel.periodo
                paralelo = materia.paralelo
                nivel = materia.asignaturamalla.nivelmalla
                carrera1 = materia.asignaturamalla.malla.carrera
                facultad = carrera1.coordinaciones()
                for x in facultad:
                    facultad = x.nombre
                return conviert_html_to_pdf('adm_criteriosactividadesdocente/reporteindividual_pdf.html',
                                            {'pagesize': 'A4 landscape',
                                             'facultad': facultad,
                                             'carrera': carrera,
                                             'periodo': periodo,
                                             'docente': docente,
                                             'asignatura': asignatura,
                                             'tutorias': tutorias,
                                             'paralelo': paralelo,
                                             'nivel': nivel
                                             })
            except Exception as ex:
                pass

        if action == 'pdfconfiguracionpares':

            try:
                data = {}
                carrera = Carrera.objects.get(pk=request.POST['idcarr'])
                coordinacion = carrera.coordinacion_carrera()
                data['fechaactual'] = datetime.now()
                data['periodo'] = periodo
                data['carrera'] = carrera
                listadoprofesores = carrera.profesordistributivohoras_set.values_list('profesor_id', flat=True).filter(periodo=periodo, status=True)
                data['listadoopares'] = coordinacion.detalleinstrumentoevaluacionparacreditacion_set.filter(proceso__periodo=periodo, evaluado_id__in=listadoprofesores, status=True).order_by('evaluado__persona__apellido1', 'evaluado__persona__apellido2', 'evaluado__persona__nombres')
                return conviert_html_to_pdf(
                    'adm_criteriosactividadesdocente/pdfconfiguracionpares.html',
                    {
                        'pagesize': 'A4 landscape',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'reporteimasivo':
            try:
                idmat = request.POST['idmat']
                tutorias = AvTutoriasAlumnos.objects.filter(status=True, avtutorias__materia=idmat)
                materia = Materia.objects.get(pk=idmat)
                carrera = materia.asignaturamalla.malla.carrera.nombre_completo()
                asignatura = materia.asignatura.nombre
                docente = materia.profesormateria_set.get(status=True, principal=True, activo=True)
                docente = docente.profesor.persona.nombre_completo()
                periodo = materia.nivel.periodo
                paralelo = materia.paralelo
                nivel = materia.asignaturamalla.nivelmalla
                carrera1 = materia.asignaturamalla.malla.carrera
                facultad = carrera1.coordinaciones()
                for x in facultad:
                    facultad = x.nombre
                return conviert_html_to_pdf('adm_criteriosactividadesdocente/reportemasivo_pdf.html',
                                            {'pagesize': 'A4 landscape',
                                             'carrera': carrera,
                                             'periodo': periodo,
                                             'docente': docente,
                                             'asignatura': asignatura,
                                             'paralelo': paralelo,
                                             'nivel': nivel,
                                             'tutorias': tutorias,
                                             'facultad': facultad
                                             })
            except Exception as ex:
                pass

        if action == 'reporteasistenciadocentepdf':
            try:
                listaasistenciadocente = []
                lista_fechas = []
                idcoordinacion = int(request.POST['c'])
                coordinacion = Coordinacion.objects.get(pk=idcoordinacion)
                fechainicio = datetime.strptime(request.POST['ini'], "%d-%m-%Y").date()
                fechafin = datetime.strptime(request.POST['fin'], "%d-%m-%Y").date()
                if fechainicio < periodo.inicio:
                    fechainicio = periodo.inicio
                if fechafin >= datetime.now().date():
                    fechafin = datetime.now().date() + timedelta(days=-1)
                for dia in daterange(fechainicio, (fechafin + timedelta(days=1))):
                    lista_fechas.append(dia)
                profesores = ProfesorDistributivoHoras.objects.select_related().filter(Q(coordinacion__id=idcoordinacion) & Q(periodo=periodo) & (Q(horasdocencia__gt=0) | Q(horasinvestigacion__gt=0) | Q(horasgestion__gt=0))).order_by('-profesor__persona__usuario__is_active', 'profesor')
                dias_laborales = contar_dias_sin_finsemana(fechainicio, fechafin, periodo)
                for profesor in profesores:
                    # profesormateria*********************************************
                    profesormaterias = ProfesorMateria.objects.filter(profesor=profesor.profesor, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 2, 5, 6], activo=True).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # asistencia
                    total_asistencias_registradas = 0
                    total_asistencias_no_registradas = 0
                    total_asistencias_dias_feriados = 0
                    total_asistencias_dias_examen = 0
                    total_asistencias_dias_suspension = 0
                    total_asistencias_dias_tutoria = 0
                    lista_clases_dia_x_fecha = []
                    porcentaje_asistencia = 0
                    suma_segundos_biometrico = 0
                    suma_segundos_permiso = 0
                    falta_biometrico = 0
                    for profesormateria in profesormaterias:
                        data_asistencia = profesormateria.asistencia_docente(fechainicio, fechafin, periodo, True, lista_clases_dia_x_fecha)
                        total_asistencias_registradas += data_asistencia['total_asistencias_registradas']
                        total_asistencias_no_registradas += data_asistencia['total_asistencias_no_registradas']
                        total_asistencias_dias_feriados += data_asistencia['total_asistencias_dias_feriados']
                        total_asistencias_dias_suspension += data_asistencia['total_asistencias_dias_suspension']
                        total_asistencias_dias_examen += data_asistencia['total_asistencias_dias_examen']
                        total_asistencias_dias_tutoria += data_asistencia['total_asistencias_dias_tutoria']
                        lista_clases_dia_x_fecha = data_asistencia['lista_clases_dia_x_fecha']
                    for fechalista in lista_fechas:
                        # EXTRAE LAS MARCADAS EN EL BIOMETRICO Y LAS NO MARCADAS
                        cuenta_feriado = False
                        logdia = LogDia.objects.filter(fecha=fechalista, status=True, persona=profesor.profesor.persona)
                        if not DiasNoLaborable.objects.values('id').filter(fecha=fechalista).exclude(periodo__isnull=True).exists():
                            cuenta_feriado = True
                        else:
                            cuenta_feriado = logdia.exists()
                        if cuenta_feriado:
                            if logdia.exists():
                                logdia = logdia[0]
                                if logdia.cantidadmarcadas >= 2:
                                    hora_minuto_seg = logdia.restarhoras()
                                    suma_segundos_biometrico += hora_minuto_seg.total_seconds()
                                else:
                                    if fechalista in lista_clases_dia_x_fecha:
                                        posicion = lista_clases_dia_x_fecha.index(fechalista)
                                        falta_biometrico += lista_clases_dia_x_fecha[posicion + 1]
                            else:
                                if fechalista in lista_clases_dia_x_fecha:
                                    posicion = lista_clases_dia_x_fecha.index(fechalista)
                                    falta_biometrico += lista_clases_dia_x_fecha[posicion + 1]
                        # EXTRAE TODOS LOS PERMISOS
                        permisosdetalles = PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=profesor.profesor.persona, permisoinstitucional__estadosolicitud=3, fechainicio__lte=fechalista, fechafin__gte=fechalista)
                        for perdetalles in permisosdetalles:
                            lista_dia_hora_seg = perdetalles.extraer_dias_horas()
                            if lista_dia_hora_seg:
                                horas_justificada = int(lista_dia_hora_seg[1].strftime("%H"))
                                # if clases_no_registrada_x_fecha >= horas_justificada:
                                #     asistencias_no_registradas = asistencias_no_registradas - horas_justificada
                                horastotales = timedelta(hours=horas_justificada, minutes=int(lista_dia_hora_seg[1].strftime("%M")), seconds=int(lista_dia_hora_seg[1].strftime("%S")))
                                suma_segundos_permiso += horastotales.total_seconds()
                    total_asistencia = total_asistencias_registradas + total_asistencias_dias_feriados + total_asistencias_dias_suspension + total_asistencias_dias_examen + total_asistencias_dias_tutoria
                    if total_asistencia > 0:
                        porcentaje_asistencia = Decimal(((total_asistencia * 100) / (total_asistencia + total_asistencias_no_registradas))).quantize(Decimal('.01'))
                    total_horas_marcadas = suma_segundos_biometrico // 3600
                    total_horas_permisos = suma_segundos_permiso // 3600
                    campo1 = profesor.profesor.persona.nombre_completo_inverso()
                    campo2 = profesor.dedicacion.horas
                    campo3 = ''
                    if profesor.dedicacion.id == 1:
                        campo3 = dias_laborales * 8
                    elif profesor.dedicacion.id == 2:
                        campo3 = dias_laborales * 4
                    elif profesor.dedicacion.id == 3:
                        campo2 = profesor.profesor.cantidad_total_horas_criterios(periodo)
                        campo3 = Decimal(Decimal(campo2 / 5) * dias_laborales).quantize(Decimal('.01'))
                    if not campo3 == '':
                        if total_horas_permisos > campo3:
                            total_horas_permisos = campo3
                    campo4 = total_horas_permisos
                    campo5 = total_asistencia
                    campo6 = total_asistencias_no_registradas
                    campo7 = total_asistencia + total_asistencias_no_registradas
                    campo8 = porcentaje_asistencia.__str__() + " %"
                    # campo9 = total_horas_marcadas
                    if total_horas_marcadas > campo3:
                        campo9 = campo3 - falta_biometrico
                    else:
                        campo9 = total_horas_marcadas
                    campo10 = falta_biometrico
                    # campo11 = total_horas_marcadas + falta_biometrico
                    campo11 = campo9 + falta_biometrico
                    if campo11 > campo3:
                        campo11 = campo3
                    listaasistenciadocente.append([campo1, campo2, campo3, campo4, campo5, campo6, campo7, campo8, campo9, campo10, campo11])
                return conviert_html_to_pdf('adm_criteriosactividadesdocente/reporteasistenciadocentepdf.html',
                                            {'pagesize': 'A4 landscape',
                                             'coordinacion': coordinacion,
                                             'fechainicio': fechainicio,
                                             'fechafin': fechafin,
                                             'listaasistenciadocente': listaasistenciadocente,
                                             'periodo': periodo
                                             })
            except Exception as ex:
                pass

        if action == 'reporteasistenciadocente':
            try:
                idcoordinacion = int(request.POST['c'])
                coordinacion = Coordinacion.objects.get(pk=idcoordinacion)
                fechainicio = datetime.strptime(request.POST['ini'], "%d-%m-%Y").date()
                fechafin = datetime.strptime(request.POST['fin'], "%d-%m-%Y").date()
                if fechafin >= datetime.now().date():
                    fechafin = datetime.now().date() + timedelta(days=-1)
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
                response['Content-Disposition'] = 'attachment; filename=REPORTE_DOCENTES_' + coordinacion.alias + "_" + random.randint(1, 10000).__str__() + '.xls'
                ws = wb.add_sheet('Asistencia_docentes')
                ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                ws.write_merge(1, 1, 0, 12, u'%s' % "REPORTE DE ASISTENCIA DOCENTE DE " + periodo.nombre, title2)
                ws.write_merge(2, 2, 0, 12, u'%s (%s a %s)' % (coordinacion.nombre, fechainicio, fechafin), title2)
                ws.col(0).width = 11000
                ws.col(1).width = 5000
                ws.col(2).width = 5000
                ws.col(3).width = 5000
                ws.col(4).width = 7000
                ws.col(5).width = 7000
                ws.col(6).width = 7000
                ws.col(7).width = 4000
                ws.col(8).width = 4000
                ws.col(9).width = 5000
                ws.col(10).width = 5000
                ws.col(11).width = 5000
                ws.col(12).width = 5000
                row_num = 3
                ws.write_merge(row_num, row_num + 2, 0, 0, u'Docente', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 1, 1, u'Horas semanales por dedicación', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 2, 2, u'Horas reales mensuales por dedicación', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 3, 3, u'Horas justificadas (permisos aprobados)', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 4, 4, u'Asistencias registradas (+horas feriados)', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 5, 5, u'Asistencias no registradas (tener en cuenta los feriados)', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 6, 6, u'Suma de asistencia registradas y no registradas', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 7, 7, u'% Asistencia', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 8, 8, u'Horas registradas', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 9, 9, u'Horas no registradas', subtitulo)
                ws.write_merge(row_num + 1, row_num + 2, 10, 10, u'Suma registradas y no registradas', subtitulo)
                ws.write_merge(row_num, row_num, 1, 2, u'Dedicación', subtitulo)
                ws.write_merge(row_num, row_num, 3, 3, u'Permisos', subtitulo)
                ws.write_merge(row_num, row_num, 4, 7, u'SGA', subtitulo)
                ws.write_merge(row_num, row_num, 8, 10, u'Biométrico', subtitulo)
                ws.write_merge(row_num, row_num + 2, 11, 11, u'Cédula', subtitulo)
                ws.write_merge(row_num, row_num + 2, 12, 12, u'Estructura', subtitulo)
                row_num = 6
                profesores = ProfesorDistributivoHoras.objects.select_related().filter(Q(coordinacion__id=idcoordinacion) & Q(periodo=periodo) & (Q(horasdocencia__gt=0) | Q(horasinvestigacion__gt=0) | Q(horasgestion__gt=0))).order_by('-profesor__persona__usuario__is_active', 'profesor')
                dias_laborales = contar_dias_sin_finsemana(fechainicio, fechafin, periodo)
                lista_fechas = []
                for dia in daterange(fechainicio, (fechafin + timedelta(days=1))):
                    lista_fechas.append(dia)
                for profesor in profesores:
                    # profesormateria*********************************************
                    profesormaterias = ProfesorMateria.objects.filter(profesor=profesor.profesor, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 2, 5, 6, 11, 12, 14, 15, 17]).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # asistencia
                    total_asistencias_registradas = 0
                    total_asistencias_no_registradas = 0
                    total_asistencias_dias_feriados = 0
                    total_asistencias_dias_suspension = 0
                    total_asistencias_dias_examen = 0
                    total_asistencias_dias_tutoria = 0
                    lista_clases_dia_x_fecha = []
                    porcentaje_asistencia = 0
                    suma_segundos_biometrico = 0
                    suma_segundos_permiso = 0
                    falta_biometrico = 0
                    for profesormateria in profesormaterias:
                        data_asistencia = profesormateria.asistencia_docente(fechainicio, fechafin, periodo, True, lista_clases_dia_x_fecha)
                        total_asistencias_registradas += data_asistencia['total_asistencias_registradas']
                        total_asistencias_no_registradas += data_asistencia['total_asistencias_no_registradas']
                        total_asistencias_dias_feriados += data_asistencia['total_asistencias_dias_feriados']
                        total_asistencias_dias_suspension += data_asistencia['total_asistencias_dias_suspension']
                        total_asistencias_dias_examen += data_asistencia['total_asistencias_dias_examen']
                        total_asistencias_dias_tutoria += data_asistencia['total_asistencias_dias_tutoria']
                        lista_clases_dia_x_fecha = data_asistencia['lista_clases_dia_x_fecha']
                    for fechalista in lista_fechas:
                        # EXTRAE LAS MARCADAS EN EL BIOMETRICO Y LAS NO MARCADAS
                        cuenta_feriado = True
                        logdia = LogDia.objects.filter(fecha=fechalista, status=True, persona=profesor.profesor.persona)
                        if not DiasNoLaborable.objects.values('id').filter(fecha=fechalista).exclude(periodo__isnull=True).exists():
                            cuenta_feriado = True
                        else:
                            cuenta_feriado = logdia.exists()
                        if cuenta_feriado:
                            if logdia.exists():
                                logdia = logdia[0]
                                if logdia.cantidadmarcadas >= 2:
                                    hora_minuto_seg = logdia.restarhoras()
                                    suma_segundos_biometrico += hora_minuto_seg.total_seconds()
                                else:
                                    if fechalista in lista_clases_dia_x_fecha:
                                        posicion = lista_clases_dia_x_fecha.index(fechalista)
                                        falta_biometrico += lista_clases_dia_x_fecha[posicion + 1]
                            else:
                                if fechalista in lista_clases_dia_x_fecha:
                                    posicion = lista_clases_dia_x_fecha.index(fechalista)
                                    falta_biometrico += lista_clases_dia_x_fecha[posicion + 1]
                        # EXTRAE TODOS LOS PERMISOS
                        permisosdetalles = PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=profesor.profesor.persona, permisoinstitucional__estadosolicitud=3, fechainicio__lte=fechalista, fechafin__gte=fechalista)
                        for perdetalles in permisosdetalles:
                            lista_dia_hora_seg = perdetalles.extraer_dias_horas()
                            if lista_dia_hora_seg:
                                horas_justificada = int(lista_dia_hora_seg[1].strftime("%H"))
                                # if clases_no_registrada_x_fecha >= horas_justificada:
                                #     asistencias_no_registradas = asistencias_no_registradas - horas_justificada
                                horastotales = timedelta(hours=horas_justificada, minutes=int(lista_dia_hora_seg[1].strftime("%M")), seconds=int(lista_dia_hora_seg[1].strftime("%S")))
                                suma_segundos_permiso += horastotales.total_seconds()
                    total_asistencia = total_asistencias_registradas + total_asistencias_dias_feriados + total_asistencias_dias_suspension + total_asistencias_dias_examen + total_asistencias_dias_tutoria
                    if total_asistencia > 0:
                        porcentaje_asistencia = Decimal(((total_asistencia * 100) / (total_asistencia + total_asistencias_no_registradas))).quantize(Decimal('.01'))
                    total_horas_marcadas = suma_segundos_biometrico // 3600
                    total_horas_permisos = suma_segundos_permiso // 3600
                    campo1 = profesor.profesor.persona.nombre_completo_inverso()
                    campo12 = '%s' % profesor.profesor.persona.identificacion()
                    campo13 = ''
                    if profesor.profesor.persona.tiene_plantilla():
                        campo13 = '%s' % profesor.profesor.persona.mi_plantilla_actual().estructuraprogramatica if profesor.profesor.persona.mi_plantilla_actual().estructuraprogramatica else ''
                    campo2 = profesor.dedicacion.horas
                    campo3 = ''
                    if profesor.dedicacion.id == 1:
                        campo3 = dias_laborales * 8
                    elif profesor.dedicacion.id == 2:
                        campo3 = dias_laborales * 4
                    elif profesor.dedicacion.id == 3:
                        campo2 = profesor.profesor.cantidad_total_horas_criterios(periodo)
                        campo3 = Decimal(Decimal(campo2 / 5) * dias_laborales).quantize(Decimal('.01'))
                    if not campo3 == '':
                        if total_horas_permisos > campo3:
                            total_horas_permisos = campo3
                    campo4 = total_horas_permisos
                    campo5 = total_asistencia
                    campo6 = total_asistencias_no_registradas
                    campo7 = total_asistencia + total_asistencias_no_registradas
                    campo8 = porcentaje_asistencia.__str__() + " %"
                    # campo9 = total_horas_marcadas
                    if total_horas_marcadas > campo3:
                        campo9 = campo3 - falta_biometrico
                    else:
                        campo9 = total_horas_marcadas
                    campo10 = falta_biometrico
                    # campo11 = total_horas_marcadas + falta_biometrico
                    campo11 = campo9 + falta_biometrico
                    if campo11 > campo3:
                        campo11 = campo3
                    ws.write(row_num, 0, campo1.__str__(), normal)
                    ws.write(row_num, 1, campo2.__str__(), nnormal)
                    ws.write(row_num, 2, campo3.__str__(), nnormal)
                    ws.write(row_num, 3, campo4.__str__(), nnormal)
                    ws.write(row_num, 4, campo5.__str__(), nnormal)
                    ws.write(row_num, 5, campo6.__str__(), nnormal)
                    ws.write(row_num, 6, campo7.__str__(), nnormal)
                    ws.write(row_num, 7, campo8.__str__(), nnormal)
                    ws.write(row_num, 8, campo9.__str__(), nnormal)
                    ws.write(row_num, 9, campo10.__str__(), nnormal)
                    ws.write(row_num, 10, campo11.__str__(), nnormal)
                    ws.write(row_num, 11, campo12, nnormal)
                    ws.write(row_num, 12, campo13, nnormal)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        if action == 'carreraprofesores':
            try:
                periodo.actualizar_carrera_profesores()
                log(u'Actualizo carreras y coordinación según a la mayor carga horarias de los docentes desde distributivo docente [Persona: %s, Periodo: %s]' % (persona.nombre_completo_inverso(), periodo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar las carreras."})

        if action == 'actualizacriteriosdocenciaprofesores':
            try:
                listaidprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id').filter(periodo=periodo)
                profesores = Profesor.objects.filter(pk__in=listaidprofesores)
                for profesor in profesores:
                    profesor.actualizar_todo_distributivo_docente(request, periodo)
                log(u'Actualizo criterios y actividades de docencia a profesores [Persona: %s, Periodo: %s]' % (persona.nombre_completo_inverso(), periodo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los criterios y actividades de docencia a los profesores."})

        if action == 'reportepracticas_excel':
            try:
                idcoord = request.POST['c']
                coordinacion = Coordinacion.objects.get(id=idcoord)
                tuto = AvTutorias.objects.filter(materia__asignaturamalla__malla__carrera__coordinacion=coordinacion,
                                                 materia__nivel__periodo_id=periodo.id).order_by("materia__asignaturamalla__malla__carrera").distinct()
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet(str(coordinacion.alias))
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=reporte_tutorias_coordinacion' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"Coordinación", 6000),
                    (u"Carrera.", 6000),
                    (u"Docente.", 6000),
                    (u"Asignatura", 6000),
                    (u"Nivel", 6000),
                    (u"Paralelo", 6000),
                    (u"Tema", 6000),
                    (u"Total Asitencias", 1500),
                    (u"Porcentaje Asistencia", 1500)
                ]
                row_num = 1
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                row_num = 2
                for r in tuto:
                    asistieron = int(r.participantes())
                    tomanmateria = r.materia.cantidad_asignados_a_esta_materia_sinretirados()
                    campo1 = coordinacion.nombre
                    campo2 = r.materia.asignaturamalla.malla.carrera.nombre_completo().__str__()
                    docente = r.materia.profesormateria_set.filter(status=True, principal=True, activo=True)[0]
                    # docente = r.materia.profesormateria_set.get(status=True, principal=True, activo=True)
                    docente = docente.profesor.persona.nombre_completo()
                    campo3 = docente
                    campo4 = r.materia.asignaturamalla.asignatura.nombre.__str__()
                    campo5 = r.materia.asignaturamalla.nivelmalla.nombre.__str__()
                    campo6 = r.materia.paralelo.__str__()
                    campo7 = r.observacion.__str__()
                    campo8 = r.participantes().__str__()
                    total = round(null_to_numeric((asistieron * 100) / tomanmateria), 2)
                    campo9 = str(total) + " %"
                    ws.write(row_num, 0, campo1, font_style2)
                    ws.write(row_num, 1, campo2, font_style2)
                    ws.write(row_num, 2, campo3, font_style2)
                    ws.write(row_num, 3, campo4, font_style2)
                    ws.write(row_num, 4, campo5, font_style2)
                    ws.write(row_num, 5, campo6, font_style2)
                    ws.write(row_num, 6, campo7, font_style2)
                    ws.write(row_num, 7, campo8, font_style2)
                    ws.write(row_num, 8, campo9, font_style2)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        if action == 'reportepracticas_pdf':
            try:
                idcoord = request.POST['c']
                coordinacion = Coordinacion.objects.get(id=idcoord)
                data['tutorias'] = AvTutorias.objects.filter(materia__asignaturamalla__malla__carrera__coordinacion=coordinacion,
                                                             materia__nivel__periodo_id=periodo.id).order_by("materia__asignaturamalla__malla__carrera").distinct()
                data['periodo'] = periodo.nombre
                data['coordinacion'] = coordinacion
                data['fecha'] = datetime.now().date()
                return conviert_html_to_pdf(
                    'adm_criteriosactividadesdocente/reporte_tutoria_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'reporteseguimiento_pdf':
            try:
                cursor = connections['default'].cursor()
                idcoord = request.POST['c']
                coordinacion = Coordinacion.objects.get(id=idcoord)
                # data['profesores'] = Persona.objects.filter(profesor__profesormateria__materia__asignaturamalla__malla__carrera__coordinacion=coordinacion,profesor__profesormateria__materia__nivel__periodo_id=periodo.id).order_by("profesormateria__materia__asignaturamalla__malla__carrera").distinct()
                sql = "SELECT pe.id, (pe.apellido1||' '||pe.apellido2||' '||pe.nombres) AS docente, asi.nombre, m.paralelo, " \
                      " (SELECT array_agg(dm.id||'-'||dm.nombre||'-'|| COALESCE((SELECT COUNT(*) FROM sga_planificacionmateria pm " \
                      " WHERE pm.materia_id=m.id and pm.paraevaluacion=true AND pm.status= TRUE AND pm.tipoevaluacion_id=dm.id " \
                      " GROUP BY pm.tipoevaluacion_id),0)||'-'|| COALESCE((select sum(tabla.p) from " \
                      " (select (CASE WHEN sum(map.calificacion)=0 THEN 0 ELSE 1 END) as p from sga_planificacionmateria pm, sga_materiaasignadaplanificacion map " \
                      " where pm.materia_id=m.id and pm.status=true and map.planificacion_id=pm.id and map.status=true and pm.paraevaluacion=true and pm.tipoevaluacion_id=dm.id " \
                      " GROUP by pm.tipoevaluacion_id, pm.id) as tabla),0) order by dm.orden) FROM sga_detallemodeloevaluativo dm " \
                      " WHERE dm.status= TRUE AND dm.modelo_id=m.modeloevaluativo_id AND (dm.nombre LIKE 'N%' OR dm.nombre LIKE 'EX%') " \
                      " ORDER BY 1) AS modelo, m.id, (select count(mat.id) from sga_materiaasignada mas, sga_matricula mat " \
                      " where mas.materia_id=m.id and mas.status=true and mat.id=mas.matricula_id and mat.status=true and mat.estado_matricula in (2,3)) as matriculado " \
                      " FROM sga_profesor p, sga_persona pe, sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma, sga_carrera ca, sga_coordinacion_carrera cc, sga_asignatura asi " \
                      " WHERE p.status= TRUE AND pe.id=p.persona_id AND pe.status= TRUE AND pm.profesor_id=p.id AND pm.status= TRUE AND m.id=pm.materia_id AND m.status= TRUE " \
                      " AND m.nivel_id=n.id AND n.status= TRUE AND n.periodo_id=" + str(periodo.id) + " AND am.id=m.asignaturamalla_id AND am.status= TRUE AND ma.id=am.malla_id AND ma.status= TRUE" \
                                                                                                      " AND ca.id=ma.carrera_id AND ca.status= TRUE AND ca.id=cc.carrera_id AND asi.id=m.asignatura_id AND asi.status= TRUE AND cc.coordinacion_id=" + str(coordinacion.id) + " " \
                                                                                                                                                                                                                                                                              " GROUP BY pe.id, asi.id, m.id  ORDER BY 1;"
                cursor.execute(sql)
                results = cursor.fetchall()
                docentes = []
                planificaciones = []
                for docente in results:
                    materia1 = docente[2] + " - " + docente[3]
                    # para la planificacion
                    planificaciones = []
                    for planificacion in docente[4]:
                        inicial = (planificacion.split('-')[1])[0:2]
                        a = 0
                        evaluacion = planificacion.split('-')[3]
                        if inicial == 'EX':
                            a = 1
                            #     sacar examnen
                            # evaluacion = null_to_decimal(EvaluacionGenerica.objects.filter(materiaasignada__materia__id=int(docente[5]), status=True, valor__gt=0, detallemodeloevaluativo__id=int(planificacion.split('-')[0])).aggregate(valor1=Contar('valor'))['valor1'])
                            evaluacion = EvaluacionGenerica.objects.filter(materiaasignada__materia__id=int(docente[5]), status=True, valor__gt=0, detallemodeloevaluativo__id=int(planificacion.split('-')[0])).count()
                        else:
                            a = 0
                            #     sacar examnen
                            # evaluacion = null_to_decimal(EvaluacionGenerica.objects.filter(materiaasignada__materia__id=int(docente[5]), status=True, valor__gt=0, detallemodeloevaluativo__id=int(planificacion.split('-')[0])).aggregate(valor1=Contar('valor'))['valor1'])
                            evaluacion = EvaluacionGenerica.objects.filter(materiaasignada__materia__id=int(docente[5]), status=True, valor__gt=0, detallemodeloevaluativo__id=int(planificacion.split('-')[0])).count()

                        planificaciones.append([planificacion.split('-')[0], planificacion.split('-')[1], planificacion.split('-')[2], evaluacion, a])

                    docentes.append([docente[1], materia1, planificaciones, docente[6]])

                # data['profesores'] = Profesor.objects.filter(profesormateria__materia__nivel__periodo=periodo,profesormateria__materia__asignaturamalla__malla__carrera__coordinacion=coordinacion, profesormateria__principal=True).distinct()
                data['profesores'] = docentes
                data['periodo'] = periodo
                data['coordinacion'] = coordinacion
                data['fecha'] = datetime.now().date()
                # connection.close()
                return conviert_html_to_pdf(
                    'adm_criteriosactividadesdocente/reporte_seguimiento_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'fechanotificacionevaluacion':
            try:
                f = FechaNotificacionEvaluacionForm(request.POST)
                if f.is_valid():
                    fechadesdenotificacion = periodo.fechadesdenotificacion
                    periodo.fechadesdenotificacion = f.cleaned_data['fechadesdenotificacion']
                    periodo.save(request)
                    log(u'Configuro fecha de notificacion de evaluacion en periodo: %s - fecha antes [%s] - nueva fecha: [%s]' % (periodo, fechadesdenotificacion, periodo.fechadesdenotificacion), request, "add")
                    return JsonResponse({"result": "ok", 'fechanotificacion': periodo.fechadesdenotificacion.strftime("%d-%m-%Y") if periodo.fechadesdenotificacion else None})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'abrirdistributivo':
            try:
                periododistributivo = Periodo.objects.get(pk=int(encrypt(request.POST['id'])))
                periododistributivo.cerradodistributivo = False
                periododistributivo.save(request)
                log(u'Abrio distributivo en el periodo: %s - fecha: %s' % (periododistributivo, datetime.now()), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al desactivar los datos."})

        if action == 'cerrardistributivo':
            try:
                periododistributivo = Periodo.objects.get(pk=int(encrypt(request.POST['id'])))
                periododistributivo.cerradodistributivo = True
                periododistributivo.save(request)
                log(u'Cerro distributivo en el periodo: %s - fecha: %s' % (periododistributivo, datetime.now()), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al activar los datos."})

        if action == 'activar':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=int(encrypt(request.POST['id'])))
                distributivo.activo = True
                distributivo.save(request)
                log(u'Activo al profesor en el distributivo: %s[%s] (%s horas docencia - %s horas investigacion - %s horas gestion) en el periodo: %s' % (distributivo.profesor, distributivo.id, distributivo.horasdocencia, distributivo.horasinvestigacion, distributivo.horasgestion, periodo), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        if action == 'desactivar':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=int(encrypt(request.POST['id'])))
                distributivo.activo = False
                distributivo.save(request)
                log(u'Desactivo al profesor en el distributivo: %s[%s] (%s horas docencia - %s horas investigacion - %s horas gestion) en el periodo: %s' % (distributivo.profesor, distributivo.id, distributivo.horasdocencia, distributivo.horasinvestigacion, distributivo.horasgestion, periodo), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                pass

        if action == 'formaciondocente_excel':
            try:
                if 'idc' in request.POST:
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Profesores_formacion_terminada ' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"Nombres", 6000),
                        (u"Nivel", 6000),
                        (u"Tipo", 6000),
                        (u"Grado", 6000),
                        (u"Amplio", 6000),
                        (u"Específico", 6000),
                        (u"Detallado", 6000),
                        (u"Verificada por UATH", 6000),
                        (u"Revisado SENESCYT", 6000),
                        (u"Facultad", 6000),
                        (u"Carrera", 6000)
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 1
                    if int(request.POST['idc']) > 0:
                        distributivo = ProfesorDistributivoHoras.objects.filter(coordinacion__id=int(request.POST['idc']), periodo=periodo).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                    else:
                        distributivo = ProfesorDistributivoHoras.objects.filter(coordinacion__status=True, periodo=periodo).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                    for d in distributivo:
                        if d.profesor.persona.titulacion_set.filter(titulo__nivel__id__in=[3, 4]).exists():
                            for t in d.profesor.persona.titulacion_set.filter(titulo__nivel__id__in=[3, 4]):
                                ws.write(row_num, 0, str(d.profesor.persona.nombre_completo_inverso()), font_style2)
                                ws.write(row_num, 1, t.titulo.nivel.nombre if t.titulo else '', font_style2)
                                ws.write(row_num, 2, t.titulo.nombre if t.titulo else '', font_style2)
                                ws.write(row_num, 3, t.titulo.grado.nombre if t.titulo.grado else '', font_style2)
                                ws.write(row_num, 4, t.titulo.areaconocimiento.nombre if t.titulo.areaconocimiento else '' if t.titulo else '', font_style2)
                                ws.write(row_num, 5, t.titulo.subareaconocimiento.nombre if t.titulo.subareaconocimiento else '' if t.titulo else '', font_style2)
                                ws.write(row_num, 6, t.titulo.subareaespecificaconocimiento.nombre if t.titulo.subareaespecificaconocimiento else '' if t.titulo else '', font_style2)
                                ws.write(row_num, 7, 'SI' if t.verificado else 'NO', font_style2)
                                ws.write(row_num, 8, 'SI' if t.verisenescyt else 'NO', font_style2)
                                ws.write(row_num, 9, d.coordinacion.nombre if d.coordinacion else '', font_style2)
                                ws.write(row_num, 10, d.carrera.nombre_completo() if d.carrera else '', font_style2)
                                row_num += 1
                        else:
                            ws.write(row_num, 0, str(d.profesor.persona.nombre_completo_inverso()), font_style2)
                            ws.write(row_num, 1, '', font_style2)
                            ws.write(row_num, 2, '', font_style2)
                            ws.write(row_num, 3, '', font_style2)
                            ws.write(row_num, 4, '', font_style2)
                            ws.write(row_num, 5, '', font_style2)
                            ws.write(row_num, 6, '', font_style2)
                            ws.write(row_num, 7, '', font_style2)
                            ws.write(row_num, 8, '', font_style2)
                            ws.write(row_num, 9, d.coordinacion.nombre if d.coordinacion else '', font_style2)
                            ws.write(row_num, 10, d.carrera.nombre_completo() if d.carrera else '', font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Error al general el excel."})

        if action == 'activacion_actividad':
            try:
                actividad = ActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                if request.POST['val'] == 'y':
                    actividad.vigente = True
                else:
                    actividad.vigente = False
                actividad.save(request)

                if actividad.criterio.es_actividadmacro():
                    if actividad.criterio.actividades().filter(vigente=True, status=True).count() >= 2:
                        raise NameError(f"Lo sentimos, las actividades macro no admiten más de una actividad vigente")

                actualiza_registro_horario_docente(actividad, 'check')
                actividad.actualiza_padre()
                log(u'Cambio vigencia de sub actividad : %s' % (actividad), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": ex.__str__()})

        if action == 'reportearticuloexcel':
            try:
                __author__ = 'Unemi'
                anio = int(request.POST['anio'])
                coordinacion = Coordinacion.objects.get(id=int(request.POST['idc']))
                periodos = Periodo.objects.filter(anio=anio)
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('exp_xls_post_part')
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = u'attachment; filename=Listas_articulos_%s%s' % (anio.__str__(), '.xls')
                columns = [
                    (u"TIPO DE ARTICULOS", 2500),
                    (u"CODIGO", 4500),
                    (u"ARTICULO", 10000),
                    (u"VOL.", 2000),
                    (u"NUM.", 2000),
                    (u"PAG.", 2000),
                    (u"CODIGO ISSN", 2000),
                    (u"BASE INDEXADA", 2000),
                    (u"NOMBRE BASE INDEXADA", 10000),
                    (u"REVISTA", 10000),
                    (u"SJR", 2000),
                    (u"FECHA PUBLICACION", 3000),
                    (u"AREA DE CONOCIMIENTO", 10000),
                    (u"SUBAREA DE CONOCIMIENTO", 10000),
                    (u"SUBAREA ESPECIFICA", 10000),
                    (u"ESTADO", 3000),
                    (u"CEDULA", 3000),
                    (u"TIPO PARTICIPANTE", 3000),
                    (u"PARTICIPANTE", 15000),
                    (u"TIPO PARTICIPACION", 4000),
                    (u"JCR", 1000),
                    (u"SJR", 1000),
                    (u"FACULTAD", 4000),
                    (u"CARRERAS", 4000),
                    (u"AÑO", 4000),
                ]
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                listaarticulos = ParticipantesArticulos.objects.filter(status=True, articulo__fechapublicacion__year=anio, profesor__profesordistributivohoras__activo=True, profesor__profesordistributivohoras__periodo__in=periodos, profesor__profesordistributivohoras__coordinacion=coordinacion).order_by('articulo__nombre')
                row_num = 4
                for articulos in listaarticulos:
                    listabesesindex = ""
                    if ArticulosBaseIndexada.objects.values('id').filter(articulo=articulos.articulo.id, status=True).exists():
                        listabases = ArticulosBaseIndexada.objects.filter(articulo=articulos.articulo.id, status=True)
                        for bases in listabases:
                            listabesesindex = listabesesindex + bases.baseindexada.nombre + ','
                    i = 0
                    campo8 = None
                    campo1 = articulos.articulo.id
                    campo2 = articulos.articulo.nombre
                    campo4 = articulos.articulo.revista.nombre
                    campo5 = articulos.articulo.areaconocimiento.nombre
                    campo6 = articulos.articulo.subareaconocimiento.nombre
                    campo7 = articulos.articulo.subareaespecificaconocimiento.nombre
                    if articulos.profesor:
                        campo8 = articulos.profesor.persona.nombre_completo_inverso()
                        campo9 = articulos.get_tipoparticipanteins_display()
                        campo10 = articulos.profesor.persona.cedula
                    if articulos.administrativo:
                        campo8 = articulos.administrativo.persona.nombre_completo_inverso()
                        campo9 = articulos.get_tipoparticipanteins_display()
                        campo10 = articulos.administrativo.persona.cedula
                    if articulos.articulo.indexada:
                        campo3 = 'SI'
                    else:
                        campo3 = 'NO'
                    campo11 = articulos.articulo.jcr
                    campo12 = articulos.articulo.sjr
                    campo13 = coordinacion.__str__()
                    campo14 = ''
                    for distributivo in articulos.profesor.distributivos_profesor(anio):
                        if distributivo.carrera:
                            campo14 += distributivo.carrera.__str__() + ', '
                    if campo14:
                        campo14 = campo14[:campo14.__len__() - 2]
                    campo15 = anio.__str__()
                    ws.write(row_num, 0, 'REVISTA', font_style2)
                    ws.write(row_num, 1, articulos.articulo.revista.codigoissn + ' ' + str(articulos.articulo.id) + '-ART', font_style2)
                    ws.write(row_num, 2, campo2, font_style2)
                    ws.write(row_num, 3, articulos.articulo.volumen, font_style2)
                    ws.write(row_num, 4, articulos.articulo.numero, font_style2)
                    ws.write(row_num, 5, articulos.articulo.paginas, font_style2)
                    ws.write(row_num, 6, articulos.articulo.revista.codigoissn, font_style2)
                    ws.write(row_num, 7, campo3, font_style2)
                    ws.write(row_num, 8, listabesesindex, font_style2)
                    ws.write(row_num, 9, campo4, font_style2)
                    ws.write(row_num, 10, articulos.articulo.revista.sjr, font_style2)
                    ws.write(row_num, 11, articulos.articulo.fechapublicacion, date_format)
                    ws.write(row_num, 12, campo5, font_style2)
                    ws.write(row_num, 13, campo6, font_style2)
                    ws.write(row_num, 14, campo7, font_style2)
                    ws.write(row_num, 15, articulos.articulo.get_estado_display(), font_style2)
                    ws.write(row_num, 16, campo10, font_style2)
                    ws.write(row_num, 17, articulos.get_tipo_display(), font_style2)
                    ws.write(row_num, 18, campo8, font_style2)
                    ws.write(row_num, 19, campo9, font_style2)
                    ws.write(row_num, 20, campo11, font_style2)
                    ws.write(row_num, 21, campo12, font_style2)
                    ws.write(row_num, 22, campo13, font_style2)
                    ws.write(row_num, 23, campo14, font_style2)
                    ws.write(row_num, 24, campo15, font_style2)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=Error al generar el reporte de articulos.")

        if action == 'detalleobservacion':
            try:
                data['cron'] = cron = CronogramaActividad.objects.get(pk=int(request.POST['id']))
                data['detalles'] = cron.detallerecoridocronogramaactividad_set.filter(status=True).order_by('-fecha')
                template = get_template("adm_criteriosactividadesdocente/detalleobservacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'aprobar_cronograma':
            try:
                cro = CronogramaActividad.objects.get(pk=int(request.POST['id']))
                rec = DetalleRecoridoCronogramaActividad(cronogramaactividad=cro,
                                                         fecha=datetime.now().date(),
                                                         observacion=u'Aprobado Cronograma de actividades',
                                                         estado=2)
                rec.save(request)
                cro.estado = 2
                cro.save(request)
                log(u'Aprobo el cronograma de actividades de docente: %s criterio: %s' % (rec.cronogramaactividad, rec.cronogramaactividad.criterio()), request, "apr")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar el cronograma"})

        if action == 'rechazar_cronograma':
            try:
                form = RechazarCronogramaActividadFrom(request.POST)
                if form.is_valid():
                    cro = CronogramaActividad.objects.get(pk=int(request.POST['id']))
                    rec = DetalleRecoridoCronogramaActividad(cronogramaactividad=cro,
                                                             fecha=datetime.now().date(),
                                                             observacion=form.cleaned_data['observacion'],
                                                             estado=3)
                    rec.save(request)
                    cro.estado = 3
                    cro.save(request)
                    log(u'Rechazo el cronograma de actividades de docente: %s criterio: %s' % (rec.cronogramaactividad, rec.cronogramaactividad.criterio()), request, "apr")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Erro al rechazar elcronograma de actividades"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Erro al rechazar elcronograma de actividades"})

        if action == 'activaradmision':
            try:
                valor = 0
                if DetalleDistributivo.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio = DetalleDistributivo.objects.get(id=request.POST['id'], status=True)
                    if not criterio.es_admision:
                        criterio.es_admision = True
                        valor = 1
                    elif criterio.es_admision == False:
                        criterio.es_admision = True
                        valor = 1
                    else:
                        criterio.es_admision = False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'informe_seguimiento_general':
            mensaje = "Problemas al generar el informe"
            try:
                materias = []
                lista1 = ""
                listacarreras = []
                coord = 0
                suma = 0
                coordinacion = None
                profesormateria = None
                profesormateriaparacoordinacion = None
                finio = request.POST['fini']
                ffino = request.POST['ffin']
                finic = convertir_fecha(finio)
                ffinc = convertir_fecha(ffino)
                opcionreport = int(request.POST['opcionreport'])
                profesor = Profesor.objects.get(id=int(encrypt(request.POST['idprof'])))
                # 1: grado virtual
                if opcionreport == 1:
                    profesormateriaparacoordinacion = profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3,
                                                                                                       materia__nivel__periodo=periodo,
                                                                                                       activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                # 2 virtual admision
                if opcionreport == 2:
                    coord = 9
                    profesormateriaparacoordinacion = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3,
                                                                                     materia__nivel__periodo=periodo, activo=True,
                                                                                     materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    profesormateria = profesormateriaparacoordinacion.filter(hora__gt=0).distinct()

                # 3 presencial admision
                if opcionreport == 3:
                    coord = 9
                    # profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo,
                    #                                                  activo=True,
                    #                                                  materia__nivel__nivellibrecoordinacion__coordinacion_id=9, hora__gt=0).exclude(materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')

                    profesormateriaparacoordinacion = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo,
                                                                                     activo=True,
                                                                                     materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')
                    profesormateria = profesormateriaparacoordinacion.filter(hora__gt=0).distinct()

                if profesormateria:
                    suma = profesormateria.aggregate(total=Sum('hora'))['total']
                if profesormateriaparacoordinacion:
                    lista = []
                    for x in profesormateriaparacoordinacion:
                        materias.append(x.materia)
                        if x.materia.carrera():
                            carrera = x.materia.carrera()
                            if not carrera in listacarreras:
                                listacarreras.append(carrera)
                            lista.append(carrera)
                    cuenta1 = collections.Counter(lista).most_common(1)
                    carrera = cuenta1[0][0]
                    coordinacion = carrera.coordinacionvalida
                    # coordinacion = Coordinacion.objects.get(id=4)
                    matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True, matricula__estado_matricula__in=[2, 3], materia__id__in=profesormateriaparacoordinacion.values_list('materia__id', flat=True)).distinct()
                    for x in matriculados:
                        if x.id != matriculados.order_by('-id')[0].id:
                            if x.matricula.inscripcion.persona.idusermoodle:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                        else:
                            lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                titulaciones = distributivo.profesor.persona.mis_titulaciones()
                titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])
                if opcionreport == 3:
                    # asistencia
                    asistencias_registradas = 0
                    asistencias_no_registradas = 0
                    asistencias_dias_feriados = 0
                    asistencias_dias_suspension = 0
                    resultado = []
                    fechas_clases = []
                    lista_clases_dia_x_fecha = []
                    for profesormate in profesormateria:
                        data_asistencia = profesormate.asistencia_docente(finic, ffinc, periodo, True,
                                                                          lista_clases_dia_x_fecha)
                        asistencias_registradas += data_asistencia['total_asistencias_registradas']
                        asistencias_no_registradas += data_asistencia['total_asistencias_no_registradas']
                        asistencias_dias_feriados += data_asistencia['total_asistencias_dias_feriados']
                        asistencias_dias_suspension += data_asistencia['total_asistencias_dias_suspension']
                        lista_clases_dia_x_fecha = data_asistencia['lista_clases_dia_x_fecha']
                        for fecha_clase in data_asistencia['lista_fechas_clases']:
                            if (fecha_clase in fechas_clases) == 0:
                                fechas_clases.append(fecha_clase)

                    # marcadas
                    marcadas = None
                    marcadas = LogDia.objects.filter(persona=distributivo.profesor.persona, fecha__in=fechas_clases,
                                                     status=True).order_by('fecha')
                    total = None
                    i = 0
                    subtotal = None
                    totalfinal = 0
                    if marcadas:
                        for m in marcadas:
                            if m.procesado:
                                i = i + 1
                                logmarcada = m.logmarcada_set.filter(status=True).order_by('time')
                                if logmarcada.count() >= 2:
                                    horas1 = logmarcada[0]
                                    horas2 = logmarcada[1]
                                    formato = "%H:%M:%S"
                                    subtotal = datetime.strptime(str(horas2.time.time()), formato) - datetime.strptime(
                                        str(horas1.time.time()), formato)
                                    if logmarcada.count() == 4:
                                        horas3 = logmarcada[2]
                                        horas4 = logmarcada[3]
                                        subtotal += datetime.strptime(str(horas4.time.time()),
                                                                      formato) - datetime.strptime(
                                            str(horas3.time.time()), formato)
                                    if i == 1:
                                        total = subtotal
                                    else:
                                        total = total + subtotal
                    if total:
                        sec = total.total_seconds()
                        hours = sec // 3600
                        minutes = (sec // 60) - (hours * 60)
                        totalfinal = str(int(hours)) + ':' + str(int(minutes)) + ': 00'
                    # -------------------------------------------------------------
                    porcentaje = 0
                    # asistencias_reg = asistencias_registradas + asistencias_dias_feriados + asistencias_dias_suspension
                    asistencias_reg = asistencias_registradas
                    if (asistencias_reg + asistencias_no_registradas) > 0:
                        porcentaje = Decimal(((asistencias_reg * 100) / (asistencias_reg + asistencias_no_registradas))).quantize(Decimal('.01'))
                    resultado.append((asistencias_reg, asistencias_no_registradas, porcentaje))

                if periodo.id == 99 and opcionreport == 3:
                    reporte = Reporte.objects.get(nombre='informe_admision_mensual_cumplimiento_actividades')
                    if reporte.archivo:
                        tipo = 'pdf'
                        output_folder = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(request.user.username))
                        try:
                            os.makedirs(output_folder)
                        except Exception as ex:
                            pass
                        d = datetime.now()
                        pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
                        runjrcommand = [JR_JAVA_COMMAND, '-jar',
                                        os.path.join(JR_RUN, 'jasperstarter.jar'),
                                        'pr', reporte.archivo.file.name,
                                        '--jdbc-dir', JR_RUN,
                                        '-f', tipo,
                                        '-t', 'postgres',
                                        '-H', DATABASES['sga_select']['HOST'],
                                        '-n', DATABASES['sga_select']['NAME'],
                                        '-u', DATABASES['sga_select']['USER'],
                                        '-p', f"'{DATABASES['sga_select']['PASSWORD']}'",
                                        '-o', output_folder + os.sep + pdfname]

                        paRequest = {'conexion_moodle': "jdbc:postgresql://10.10.100.148:5432/nivelacion",
                                     'user_bd': "moocweb",
                                     'password_bd': "Un3M12o18?m00C",
                                     'coordinacion_id': 9,
                                     'date_begin': convertir_fecha(finio).strftime('%Y-%m-%d') + ' 00:00',
                                     'date_end': convertir_fecha(ffino).strftime('%Y-%m-%d') + ' 23:59',
                                     'horas': 16,
                                     'periodo_id': periodo.id,
                                     'porcentaje_asistencia': porcentaje,
                                     'profesor_id': profesor.id,
                                     'total_hora_no_registradas': asistencias_no_registradas,
                                     'total_hora_registradas': asistencias_reg}
                        parametros = reporte.parametros()
                        paramlist = []
                        for p in parametros:
                            if p.tipo == 1 or p.tipo == 6:
                                paramlist.append('%s="%s"' % (p.nombre, fixparametro(p.tipo, paRequest[p.nombre])))
                            else:
                                paramlist.append('%s=%s' % (p.nombre, fixparametro(p.tipo, paRequest[p.nombre])))
                        if paramlist:
                            runjrcommand.append('-P')
                            for parm in paramlist:
                                runjrcommand.append(parm)
                        else:
                            runjrcommand.append('-P')
                        runjrcommand.append(u'SUBREPORT_DIR=' + unicode(SUBREPOTRS_FOLDER))
                        runjrcommand.append(u'userweb=' + unicode(request.user.username))
                        mens = ''
                        mensaje = ''
                        for m in runjrcommand:
                            mens += ' ' + m
                        if DEBUG:
                            runjr = subprocess.run(mens, shell=True, check=True)
                            # print('runjr:', runjr.returncode)
                        else:
                            runjr = subprocess.call(mens.encode("latin1"), shell=True)

                        sp = os.path.split(reporte.archivo.file.name)
                        return HttpResponseRedirect("/".join(
                            [MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username),
                             pdfname + "." + tipo]))
                        # return ok_json({"r": mensaje, 'reportfile': "/".join(
                        #     [MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username),
                        #      pdfname + "." + tipo])})
                else:
                    return conviert_html_to_pdf('pro_cronograma/informe_seguimiento.html', {'pagesize': 'A4',
                                                                                            'data': {
                                                                                                'distributivo': distributivo,
                                                                                                'periodo': periodo,
                                                                                                'fini': finio,
                                                                                                'ffin': ffino,
                                                                                                'finic': finic,
                                                                                                'ffinc': ffinc,
                                                                                                'suma': suma,
                                                                                                'materias': materias,
                                                                                                'titulaciones': titulaciones,
                                                                                                'opcionreport': opcionreport,
                                                                                                'resultado': resultado if opcionreport == 3 else None,
                                                                                                'coord': coord, 'coordinacion': coordinacion,
                                                                                                'listacarreras': listacarreras,
                                                                                                'lista': lista1}})
            except Exception as ex:
                return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=%s" % mensaje)

        elif action == 'reporte_mensajes':
            mensaje = "Problemas al generar el reporte"
            try:
                profesor = None
                coord = 0
                opcionreport = int(request.POST['opcionreport'])
                profesor = Profesor.objects.get(id=int(encrypt(request.POST['idprofesor'])))
                if opcionreport == 1:
                    coord = 0
                # 2 virtual admision
                if opcionreport == 2 or opcionreport == 3:
                    coord = 9
                return conviert_html_to_pdf('pro_cronograma/reporte_mensajes.html',
                                            {'pagesize': 'A4', 'data': {'profesor': profesor, 'coord': coord}})
            except Exception as ex:
                return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=%s" % mensaje)

        elif action == 'reporte_foros':
            mensaje = "Problemas al generar el reporte"
            try:
                profesor = None
                opcionreport = int(request.POST['opcionreport'])
                profesor = Profesor.objects.get(id=int(encrypt(request.POST['idprofesor'])))
                coord = 0
                materias = []
                profesormateria = None
                if opcionreport == 1:
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor,
                                                                     materia__nivel__modalidad_id=3,
                                                                     materia__nivel__periodo=periodo,
                                                                     activo=True).exclude(
                        materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde',
                                                                                                       'materia__asignatura__nombre')
                # 2 virtual admision
                if opcionreport == 2:
                    coord = 9
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor,
                                                                     materia__nivel__modalidad_id=3,
                                                                     materia__nivel__periodo=periodo, activo=True,
                                                                     materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by(
                        'desde', 'materia__asignatura__nombre')
                # 3 presencial admision
                if opcionreport == 3:
                    coord = 9
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor,
                                                                     materia__nivel__periodo=periodo, activo=True,
                                                                     materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(
                        materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')
                if profesormateria:
                    for x in profesormateria:
                        materias.append(x.materia)
                return conviert_html_to_pdf('pro_cronograma/reporte_foros.html', {'pagesize': 'A4',
                                                                                  'data': {'profesor': profesor,
                                                                                           'coord': coord,
                                                                                           'materias': materias}})
            except Exception as ex:
                return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=%s" % mensaje)

        elif action == 'addaprobacionproductoinvestigacion':
            try:
                tipo = int(request.POST['tipo'])
                if tipo == 1:
                    producto = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    aprobar = InvestigacionDocenteAprobacion(articulo=producto,
                                                             fechaaprobacion=datetime.now().date(),
                                                             observacion=request.POST['obse'],
                                                             aprueba=persona,
                                                             estado=int(request.POST['esta']))
                elif tipo == 2:
                    producto = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    aprobar = InvestigacionDocenteAprobacion(ponencia=producto,
                                                             fechaaprobacion=datetime.now().date(),
                                                             observacion=request.POST['obse'],
                                                             aprueba=persona,
                                                             estado=int(request.POST['esta']))
                elif tipo == 3:
                    producto = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    aprobar = InvestigacionDocenteAprobacion(libro=producto,
                                                             fechaaprobacion=datetime.now().date(),
                                                             observacion=request.POST['obse'],
                                                             aprueba=persona,
                                                             estado=int(request.POST['esta']))
                else:
                    producto = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    aprobar = InvestigacionDocenteAprobacion(capitulolibro=producto,
                                                             fechaaprobacion=datetime.now().date(),
                                                             observacion=request.POST['obse'],
                                                             aprueba=persona,
                                                             estado=int(request.POST['esta']))

                if aprobar:
                    aprobar.save(request)
                    producto.actualizar_estado(request)
                log(u'Aprobar solicitud producto investigacion docente (Director): %s' % aprobar, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'imprimirproductopdf':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                distributivo = profesor.distributivohoraseval(periodo)
                decano = None
                director = None
                if distributivo:
                    decano = distributivo.coordinacion.responsable_periododos(periodo, 1)
                    director = distributivo.carrera.coordinador(periodo, distributivo.coordinacion.sede)
                return conviert_html_to_pdf('adm_criteriosactividadesdocente/imprimirproductopdf.html',
                                            {'pagesize': 'A4',
                                             'data': data,
                                             'profesor': profesor,
                                             'periodo': periodo,
                                             'distributivo': distributivo,
                                             'decano': decano,
                                             'director': director
                                             })
            except Exception as ex:
                pass

        elif action == 'imprimirproductoexcel':
            try:
                __author__ = 'Unemi'
                profesor = Profesor.objects.get(pk=request.POST['id'])
                distributivo = profesor.distributivohoraseval(periodo)
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
                cont = 0
                for producto in range(4):
                    cont += 1
                    if cont == 1:
                        ws = wb.add_sheet("Artículo")
                    elif cont == 2:
                        ws = wb.add_sheet("Revista")
                    elif cont == 3:
                        ws = wb.add_sheet("Libro")
                    elif cont == 4:
                        ws = wb.add_sheet("Capítulo Liro")
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write(1, 0, "Docente: " + str(profesor), font_style2)
                    ws.write(2, 0, "Periodo: " + periodo.nombre, font_style2)
                    ws.write(3, 0, "Facultad: " + str(distributivo.coordinacion), font_style2)
                    ws.write(4, 0, "Carrera: " + str(distributivo.carrera), font_style2)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte' + random.randint(1, 10000).__str__() + '.xls'
                    if cont == 1:
                        columns = [
                            (u"No.", 1000),
                            (u"CRITERIO", 9000),
                            (u"TEMÁTICA", 9000),
                            (u"REVISTA", 6000),
                            (u"METODOLOGIA", 6000),
                            (u"ESTADO", 6000),
                        ]
                        row_num = 6
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 7
                        i = 0
                        if distributivo.detalle_horas_investigacion():
                            for detalle in distributivo.detalle_horas_investigacion():
                                if detalle.dato_producto_investigacion_articulo():
                                    for producto in detalle.dato_producto_investigacion_articulo():
                                        i += 1
                                        campo1 = i
                                        campo2 = str(detalle.criterioinvestigacionperiodo.criterio)
                                        campo3 = producto.tematica
                                        campo4 = producto.revista
                                        campo5 = producto.metodologia
                                        campo6 = producto.get_estado_display()
                                        ws.write(row_num, 0, campo1, font_style2)
                                        ws.write(row_num, 1, campo2, font_style2)
                                        ws.write(row_num, 2, campo3, font_style2)
                                        ws.write(row_num, 3, campo4, font_style2)
                                        ws.write(row_num, 4, campo5, font_style2)
                                        ws.write(row_num, 5, campo6, font_style2)
                                        row_num += 1
                    elif cont == 2:
                        columns = [
                            (u"No.", 1000),
                            (u"CRITERIO", 9000),
                            (u"TEMATICA", 6000),
                            (u"CONGRESO", 6000),
                            (u"ESTADO", 6000),
                        ]
                        row_num = 6
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 7
                        i = 0
                        if distributivo.detalle_horas_investigacion():
                            for detalle in distributivo.detalle_horas_investigacion():
                                if detalle.dato_producto_investigacion_ponencia():
                                    for producto in detalle.dato_producto_investigacion_ponencia():
                                        i += 1
                                        campo1 = i
                                        campo2 = str(detalle.criterioinvestigacionperiodo.criterio)
                                        campo3 = producto.tematica
                                        campo4 = producto.congreso
                                        campo5 = producto.get_estado_display()
                                        ws.write(row_num, 0, campo1, font_style2)
                                        ws.write(row_num, 1, campo2, font_style2)
                                        ws.write(row_num, 2, campo3, font_style2)
                                        ws.write(row_num, 3, campo4, font_style2)
                                        ws.write(row_num, 4, campo5, font_style2)
                                        row_num += 1
                    elif cont == 3:
                        columns = [
                            (u"No.", 1000),
                            (u"CRITERIO", 9000),
                            (u"NOMBRE", 6000),
                            (u"ESTADO", 6000),
                        ]
                        row_num = 6
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 7
                        i = 0
                        if distributivo.detalle_horas_investigacion():
                            for detalle in distributivo.detalle_horas_investigacion():
                                if detalle.dato_producto_investigacion_libro():
                                    for producto in detalle.dato_producto_investigacion_libro():
                                        i += 1
                                        campo1 = i
                                        campo2 = str(detalle.criterioinvestigacionperiodo.criterio)
                                        campo3 = producto.nombre
                                        campo4 = producto.get_estado_display()
                                        ws.write(row_num, 0, campo1, font_style2)
                                        ws.write(row_num, 1, campo2, font_style2)
                                        ws.write(row_num, 2, campo3, font_style2)
                                        ws.write(row_num, 3, campo4, font_style2)
                                        row_num += 1
                    elif cont == 4:
                        columns = [
                            (u"No.", 1000),
                            (u"CRITERIO", 9000),
                            (u"NOMBRE", 6000),
                            (u"ESTADO", 6000),
                        ]
                        row_num = 6
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 7
                        i = 0
                        if distributivo.detalle_horas_investigacion():
                            for detalle in distributivo.detalle_horas_investigacion():
                                if detalle.dato_producto_investigacion_capitulolibro():
                                    for producto in detalle.dato_producto_investigacion_capitulolibro():
                                        i += 1
                                        campo1 = i
                                        campo2 = str(detalle.criterioinvestigacionperiodo.criterio)
                                        campo3 = producto.nombre
                                        campo4 = producto.get_estado_display()
                                        ws.write(row_num, 0, campo1, font_style2)
                                        ws.write(row_num, 1, campo2, font_style2)
                                        ws.write(row_num, 2, campo3, font_style2)
                                        ws.write(row_num, 3, campo4, font_style2)
                                        row_num += 1

                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'imprimirproductoexcel_filtros':
            try:
                __author__ = 'Unemi'
                idcoordinacion = int(request.POST['coordinacion'])
                if idcoordinacion > 0:
                    coordinacion = Coordinacion.objects.get(id=idcoordinacion)
                    distributivos = ProfesorDistributivoHoras.objects.filter(status=True, coordinacion=coordinacion, activo=True, periodo=periodo)
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                cont = 0
                for producto in range(4):
                    cont += 1
                    if cont == 1:
                        ws = wb.add_sheet("Artículo")
                    elif cont == 2:
                        ws = wb.add_sheet("Revista")
                    elif cont == 3:
                        ws = wb.add_sheet("Libro")
                    elif cont == 4:
                        ws = wb.add_sheet("Capítulo Liro")
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte' + random.randint(1, 10000).__str__() + '.xls'
                    if cont == 1:
                        columns = [
                            (u"No.", 1000),
                            (u"DOCENTE", 9000),
                            (u"PERIODO", 9000),
                            (u"FACULTAD", 9000),
                            (u"CARRERA", 9000),
                            (u"CRITERIO", 9000),
                            (u"TEMÁTICA", 9000),
                            (u"REVISTA", 6000),
                            (u"METODOLOGIA", 6000),
                            (u"ESTADO", 6000),
                        ]
                        row_num = 6
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 7
                        i = 0
                        for distributivo in distributivos:
                            if distributivo.detalle_horas_investigacion():
                                for detalle in distributivo.detalle_horas_investigacion():
                                    if detalle.dato_producto_investigacion_articulo():
                                        for producto in detalle.dato_producto_investigacion_articulo():
                                            i += 1
                                            campo1 = i
                                            campo2 = str(distributivo.profesor.persona.nombre_completo_inverso())
                                            campo3 = str(periodo)
                                            campo4 = str(distributivo.coordinacion)
                                            campo5 = str(distributivo.carrera)
                                            campo6 = str(detalle.criterioinvestigacionperiodo.criterio)
                                            campo7 = producto.tematica
                                            campo8 = producto.revista
                                            campo9 = producto.metodologia
                                            campo10 = producto.get_estado_display()
                                            ws.write(row_num, 0, campo1, font_style2)
                                            ws.write(row_num, 1, campo2, font_style2)
                                            ws.write(row_num, 2, campo3, font_style2)
                                            ws.write(row_num, 3, campo4, font_style2)
                                            ws.write(row_num, 4, campo5, font_style2)
                                            ws.write(row_num, 5, campo6, font_style2)
                                            ws.write(row_num, 6, campo7, font_style2)
                                            ws.write(row_num, 7, campo8, font_style2)
                                            ws.write(row_num, 8, campo9, font_style2)
                                            ws.write(row_num, 9, campo9, font_style2)
                                            row_num += 1
                    elif cont == 2:
                        columns = [
                            (u"No.", 1000),
                            (u"DOCENTE", 9000),
                            (u"PERIODO", 9000),
                            (u"FACULTAD", 9000),
                            (u"CARRERA", 9000),
                            (u"CRITERIO", 9000),
                            (u"TEMATICA", 6000),
                            (u"CONGRESO", 6000),
                            (u"ESTADO", 6000),
                        ]
                        row_num = 6
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 7
                        i = 0
                        if distributivo.detalle_horas_investigacion():
                            for detalle in distributivo.detalle_horas_investigacion():
                                if detalle.dato_producto_investigacion_ponencia():
                                    for producto in detalle.dato_producto_investigacion_ponencia():
                                        i += 1
                                        campo1 = i
                                        campo2 = str(distributivo.profesor.persona.nombre_completo_inverso())
                                        campo3 = str(periodo)
                                        campo4 = str(distributivo.coordinacion)
                                        campo5 = str(distributivo.carrera)
                                        campo6 = str(detalle.criterioinvestigacionperiodo.criterio)
                                        campo7 = producto.tematica
                                        campo8 = producto.congreso
                                        campo9 = producto.get_estado_display()
                                        ws.write(row_num, 0, campo1, font_style2)
                                        ws.write(row_num, 1, campo2, font_style2)
                                        ws.write(row_num, 2, campo3, font_style2)
                                        ws.write(row_num, 3, campo4, font_style2)
                                        ws.write(row_num, 4, campo5, font_style2)
                                        ws.write(row_num, 5, campo6, font_style2)
                                        ws.write(row_num, 6, campo7, font_style2)
                                        ws.write(row_num, 7, campo8, font_style2)
                                        ws.write(row_num, 8, campo9, font_style2)
                                        row_num += 1
                    elif cont == 3:
                        columns = [
                            (u"No.", 1000),
                            (u"DOCENTE", 9000),
                            (u"PERIODO", 9000),
                            (u"FACULTAD", 9000),
                            (u"CARRERA", 9000),
                            (u"CRITERIO", 9000),
                            (u"NOMBRE", 6000),
                            (u"ESTADO", 6000),
                        ]
                        row_num = 6
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 7
                        i = 0
                        if distributivo.detalle_horas_investigacion():
                            for detalle in distributivo.detalle_horas_investigacion():
                                if detalle.dato_producto_investigacion_libro():
                                    for producto in detalle.dato_producto_investigacion_libro():
                                        i += 1
                                        campo1 = i
                                        campo2 = str(distributivo.profesor.persona.nombre_completo_inverso())
                                        campo3 = str(periodo)
                                        campo4 = str(distributivo.coordinacion)
                                        campo5 = str(distributivo.carrera)
                                        campo6 = str(detalle.criterioinvestigacionperiodo.criterio)
                                        campo7 = producto.nombre
                                        campo8 = producto.get_estado_display()
                                        ws.write(row_num, 0, campo1, font_style2)
                                        ws.write(row_num, 1, campo2, font_style2)
                                        ws.write(row_num, 2, campo3, font_style2)
                                        ws.write(row_num, 3, campo4, font_style2)
                                        ws.write(row_num, 4, campo5, font_style2)
                                        ws.write(row_num, 5, campo6, font_style2)
                                        ws.write(row_num, 6, campo7, font_style2)
                                        ws.write(row_num, 7, campo8, font_style2)
                                        row_num += 1
                    elif cont == 4:
                        columns = [
                            (u"No.", 1000),
                            (u"DOCENTE", 9000),
                            (u"PERIODO", 9000),
                            (u"FACULTAD", 9000),
                            (u"CARRERA", 9000),
                            (u"CRITERIO", 9000),
                            (u"NOMBRE", 6000),
                            (u"ESTADO", 6000),
                        ]
                        row_num = 6
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        date_format = xlwt.XFStyle()
                        date_format.num_format_str = 'yyyy/mm/dd'
                        row_num = 7
                        i = 0
                        if distributivo.detalle_horas_investigacion():
                            for detalle in distributivo.detalle_horas_investigacion():
                                if detalle.dato_producto_investigacion_capitulolibro():
                                    for producto in detalle.dato_producto_investigacion_capitulolibro():
                                        i += 1
                                        campo1 = i
                                        campo2 = str(distributivo.profesor.persona.nombre_completo_inverso())
                                        campo3 = str(periodo)
                                        campo4 = str(distributivo.coordinacion)
                                        campo5 = str(distributivo.carrera)
                                        campo6 = str(detalle.criterioinvestigacionperiodo.criterio)
                                        campo7 = producto.nombre
                                        campo8 = producto.get_estado_display()
                                        ws.write(row_num, 0, campo1, font_style2)
                                        ws.write(row_num, 1, campo2, font_style2)
                                        ws.write(row_num, 2, campo3, font_style2)
                                        ws.write(row_num, 3, campo4, font_style2)
                                        ws.write(row_num, 4, campo5, font_style2)
                                        ws.write(row_num, 5, campo6, font_style2)
                                        ws.write(row_num, 6, campo7, font_style2)
                                        ws.write(row_num, 7, campo8, font_style2)
                                        row_num += 1

                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'reporteactividadespendientes':
            import json
            try:
                __author__ = 'Unemi'
                idcarrera = int(request.POST['idcarrera'])
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=actividades_pendientes' + random.randint(1, 10000).__str__() + '.xls'
                cursor = connections['default'].cursor()
                columns = [
                    (u"No.", 6000),
                    (u"FACULTAD", 6000),
                    (u"CARRERA", 6000),
                    (u"CEDULA", 3000),
                    (u"ALUMNO", 6000),
                    (u"MATERIA", 6000),
                    (u"CODIGO MATERIA", 6000),
                    (u"TIPO ACTIVIDAD", 6000),
                    (u"ACTIVIDAD", 6000),
                    (u"FECHA INICIO", 6000),
                    (u"FECHA FIN", 6000),
                    (u"CATEGORIA", 6000),
                    (u"NOTA MAXIMA CATEGORIA", 6000),
                    (u"NOTA INICIAL", 6000),
                    (u"NOTA FINAL", 6000),
                    (u"ENVIO TAREA ", 3000),
                    (u"COMENTARIO DOCENTE", 3000),
                    (u"APORTE FORO", 3000),
                ]
                ws = wb.add_sheet('exp_xls_post_part1')
                ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                row_num = 3
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 4
                if idcarrera > 0:
                    carrera = Carrera.objects.get(id=idcarrera)
                    if carrera.coordinacion_set.filter(status=True)[0].id == 9:
                        cursormoodle = connections['db_moodle_virtual'].cursor()
                    else:
                        cursormoodle = connections['moodle_db'].cursor()
                    sql_carrera = """
                        SELECT DISTINCT sga_materia.idcursomoodle
                        FROM "sga_materia"
                        INNER JOIN "sga_asignaturamalla" ON ("sga_materia"."asignaturamalla_id" = "sga_asignaturamalla"."id")
                        INNER JOIN "sga_nivelmalla" ON ("sga_asignaturamalla"."nivelmalla_id" = "sga_nivelmalla"."id")
                        INNER JOIN "sga_asignatura" ON ("sga_materia"."asignatura_id" = "sga_asignatura"."id")
                        INNER JOIN sga_malla malla ON malla.id = sga_asignaturamalla.malla_id
                        INNER JOIN sga_carrera carrera ON carrera.id = malla.carrera_id
                        INNER JOIN sga_coordinacion_carrera coordinacioncarrera ON coordinacioncarrera.carrera_id = carrera.id
                        INNER JOIN sga_coordinacion coordinacion ON coordinacion.id = coordinacioncarrera.coordinacion_id
                        WHERE carrera.id=%s
                    """ % (idcarrera)
                    cursor.execute(sql_carrera)
                    resultscarreras = cursor.fetchall()

                    sql_carrera_ultima = """
                                            SELECT DISTINCT sga_materia.idcursomoodle
                                            FROM "sga_materia"
                                            INNER JOIN "sga_asignaturamalla" ON ("sga_materia"."asignaturamalla_id" = "sga_asignaturamalla"."id")
                                            INNER JOIN "sga_nivelmalla" ON ("sga_asignaturamalla"."nivelmalla_id" = "sga_nivelmalla"."id")
                                            INNER JOIN "sga_asignatura" ON ("sga_materia"."asignatura_id" = "sga_asignatura"."id")
                                            INNER JOIN sga_malla malla ON malla.id = sga_asignaturamalla.malla_id
                                            INNER JOIN sga_carrera carrera ON carrera.id = malla.carrera_id
                                            INNER JOIN sga_coordinacion_carrera coordinacioncarrera ON coordinacioncarrera.carrera_id = carrera.id
                                            INNER JOIN sga_coordinacion coordinacion ON coordinacion.id = coordinacioncarrera.coordinacion_id
                                            WHERE carrera.id=%s
                                            ORDER BY  sga_materia.idcursomoodle DESC LIMIT 1 
                                        """ % (idcarrera)
                    cursor.execute(sql_carrera_ultima)
                    resultsultimacarrera = cursor.fetchall()

                    lista = ""
                    for res in resultscarreras:
                        if int(res[0]) != int(resultsultimacarrera[0][0]):
                            lista += str(res[0]) + ","
                        else:
                            lista += str(res[0])

                    sql = """
                    SELECT e.idnumber,e.firstname   ||' ' ||e.lastname AS alumno,c.fullname,c.shortname,  b.itemmodule AS Modulo,
                                    b.itemname AS Actividad,COALESCE(g.fullname,'CATEGORIA_PRINCIPAL') AS categoria,
                                    COALESCE(ROUND(d.rawgrademax,2),0) AS NotaMaximaCATE,
                                    COALESCE(ROUND(d.rawgrade,2),0) AS NotaInicial, 
                                    COALESCE(ROUND(d.finalgrade,2),0) AS NotaFInal,COALESCE(UPPER(a.fullname),g.fullname),
                                    (
                                    SELECT usuario.username
                                    FROM mooc_assign_submission submission
                                    INNER JOIN mooc_assign AS assign ON submission.ASSIGNMENT=assign.id
                                    INNER JOIN mooc_user AS usuario ON submission.userid=usuario.id
                                    INNER JOIN mooc_course AS course ON course.id=assign.course
                                    WHERE course.id=c.id AND assign.id=b.iteminstance and usuario.id=e.id AND submission.status='submitted'
                                    ) AS envio_tarea,
                                    (
                                    SELECT TO_TIMESTAMP( tarea.allowsubmissionsfromdate) 
                                    FROM mooc_assign tarea
                                    WHERE tarea.id=b.iteminstance
                                    ) AS fecha_inicio_tarea,
                                    (
                                    SELECT TO_TIMESTAMP( tarea.duedate ) 
                                    FROM mooc_assign tarea
                                    WHERE tarea.id=b.iteminstance
                                    ) AS fecha_fin_tarea,
                                    (
                                    SELECT com.commenttext
                                    FROM mooc_assignfeedback_comments com
                                    INNER JOIN mooc_assign_grades grades ON grades.id=com.grade
                                    WHERE com.assignment=b.iteminstance AND grades.userid=e.id
                                    ) AS comentario, 
                                    (
                                    SELECT COUNT(DISTINCT posts.id)
                                    FROM mooc_forum_posts posts
                                    INNER JOIN mooc_forum_discussions discussions ON posts.discussion=discussions.id
                                    INNER JOIN mooc_forum forum ON discussions.forum=forum.id
                                    INNER JOIN mooc_user usuario ON posts.userid=usuario.id
                                    INNER JOIN mooc_course course ON forum.course=course.id
                                    WHERE course.id=c.id AND forum.id=b.iteminstance AND usuario.id =e.id
                                    ) AS aporte_foro, b.iteminstance AS idactividad
                                    FROM mooc_grade_grades d
                                    INNER JOIN mooc_grade_items b ON d.itemid=b.id 
                                    left JOIN mooc_grade_categories a ON a.courseid=b.courseid AND a.id=b.iteminstance AND a.depth=2
                                    left JOIN mooc_grade_categories g ON g.id=b.categoryid AND g.courseid=b.courseid
                                    INNER JOIN mooc_user e ON d.userid=e.id
                                    INNER JOIN mooc_course AS c ON c.id=b.courseid
                                    LEFT JOIN mooc_user AS f ON f.id=d.usermodified
                                    WHERE c.id in (%s) AND b.itemmodule IN ('assign','forum') AND g.fullname !='?' AND d.rawgrade<1
                                    ORDER BY g.fullname
      
                                    """ % lista
                    cursormoodle.execute(sql)
                    results = cursormoodle.fetchall()
                    i = 0
                    for r in results:
                        aux = 0
                        tipo = r[4]
                        fechainicio = ""
                        fechafin = ""
                        envio_tarea = ""
                        if tipo == 'assign':
                            fechainicio = r[12].__str__()
                            fechafin = r[13].__str__()
                            if r[11] != '':
                                envio_tarea = "SI"
                                if r[14] == '':
                                    aux = 1
                            else:
                                envio_tarea = "NO"
                        elif tipo == 'forum':
                            if int(r[15]) == 1:
                                aux = 1
                                sql_fecha_foro = """
                                SELECT cm.availability
                                FROM mooc_modules md
                                JOIN mooc_course_modules cm ON cm.module = md.id
                                JOIN mooc_forum foro ON foro.id=cm.instance
                                WHERE foro.id = %s AND md.NAME ='forum' AND cm.availability IS NOT NULL AND foro.assessed>0 AND foro.introformat>0
                                                                        """ % (int(r[16]))
                                cursormoodle.execute(sql_fecha_foro)
                                resultfecha = cursormoodle.fetchall()
                                fechafin = ""
                                fechainicio = ""
                                for rf in resultfecha:
                                    fechas = json.loads(rf[0])
                                    fechainicio = ""
                                    fechafin = ""
                                    for x in fechas['c']:
                                        try:
                                            signo = x['d']
                                            fecha = x['t']
                                            if signo == '>=':
                                                fechainicio = fecha
                                            else:
                                                fechafin = fecha
                                        except Exception as ex:
                                            pass
                                    if fechafin:
                                        fechainicio = time.localtime(fechainicio)
                                        fechainicio = convertir_fecha_hora("%s-%s-%s 00:00" % (
                                            fechainicio.tm_mday, fechainicio.tm_mon, fechainicio.tm_year))
                                        fechafin = time.localtime(fechafin)
                                        fechafin = convertir_fecha_hora("%s-%s-%s 23:59" % (
                                            fechafin.tm_mday, fechafin.tm_mon, fechafin.tm_year))
                                    elif fechainicio:
                                        fechainicio = time.localtime(fechainicio)
                                        fechainicio = convertir_fecha_hora("%s-%s-%s 00:00" % (
                                            fechainicio.tm_mday, fechainicio.tm_mon, fechainicio.tm_year))
                                        fechafin = fechainicio + timedelta(days=7)
                        if aux == 1:
                            i += 1
                            row_num += 1
                            ws.write(row_num, 0, i, font_style2)
                            ws.write(row_num, 1, str(carrera.coordinaciones()[0].nombre), font_style2)
                            ws.write(row_num, 2, str(carrera.nombre_completo()).__str__(), font_style2)
                            ws.write(row_num, 3, r[0].__str__(), font_style2)
                            ws.write(row_num, 4, r[1].__str__(), font_style2)
                            ws.write(row_num, 5, r[2].__str__(), font_style2)
                            ws.write(row_num, 6, r[3].__str__(), font_style2)
                            ws.write(row_num, 7, r[4].__str__(), font_style2)
                            ws.write(row_num, 8, r[5].__str__(), font_style2)
                            ws.write(row_num, 9, fechainicio.__str__(), font_style2)
                            ws.write(row_num, 10, fechafin.__str__(), font_style2)
                            ws.write(row_num, 11, r[6].__str__(), font_style2)
                            ws.write(row_num, 12, r[7].__str__(), font_style2)
                            ws.write(row_num, 13, r[8].__str__(), font_style2)
                            ws.write(row_num, 14, r[9].__str__(), font_style2)
                            ws.write(row_num, 15, envio_tarea, font_style2)
                            ws.write(row_num, 16, r[14].__str__(), font_style2)
                            ws.write(row_num, 17, r[15].__str__(), font_style2)
                    wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'informe_autor':
            mensaje = "Problemas al generar el informe"
            try:
                paralelos = []
                carreras = []
                suma = 0
                profesor = None
                finio = request.POST['fini']
                ffino = request.POST['ffin']
                idmateria = int(encrypt(request.POST['idmateriaaautor']))
                materia = Materia.objects.filter(status=True, id=idmateria)
                if ProfesorMateria.objects.filter(status=True, materia=materia, tipoprofesor_id=9, activo=True).exists():
                    profesor = ProfesorMateria.objects.filter(status=True, materia=materia, tipoprofesor_id=9, activo=True)[0].profesor
                finic = convertir_fecha(finio)
                ffinc = convertir_fecha(ffino)
                idmaterias = ProfesorMateria.objects.values_list('materia__id').filter(profesor=profesor,
                                                                                       tipoprofesor__id=9,
                                                                                       materia__nivel__periodo=periodo,
                                                                                       activo=True).distinct()
                materias = Materia.objects.filter(status=True, asignatura=materia[0].asignatura, nivel__periodo=periodo, id__in=idmaterias)
                if materias:
                    for x in materias:
                        if x.paralelo not in paralelos:
                            paralelos.append(x.paralelo)
                        if x.carrera().nombre_completo not in carreras:
                            carreras.append(x.carrera().nombre_completo)
                distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                titulaciones = distributivo.profesor.persona.mis_titulaciones()
                titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])
                return conviert_html_to_pdf('pro_cronograma/informe_seguimiento_autor.html', {'pagesize': 'A4',
                                                                                              'data': {
                                                                                                  'distributivo': distributivo,
                                                                                                  'periodo': periodo,
                                                                                                  'fini': finio,
                                                                                                  'ffin': ffino,
                                                                                                  'finic': finic,
                                                                                                  'ffinc': ffinc,
                                                                                                  'suma': suma,
                                                                                                  'materia1': materia[0],
                                                                                                  'materiasg': materia,
                                                                                                  'paralelos': paralelos, 'carreras': carreras,
                                                                                                  'titulaciones': titulaciones}})
            except Exception as ex:
                return HttpResponseRedirect("/pro_cronograma?info=%s" % mensaje)

        elif action == 'informe_actividades_autor':
            mensaje = "Problemas al generar el informe"
            try:
                idcarrera = int(request.POST['idcarrera'])
                carrera = Carrera.objects.filter(status=True, id=idcarrera)[0]
                materias = Materia.objects.filter(status=True, nivel__periodo=periodo, esintroductoria=False, asignaturamalla__malla__carrera=carrera).distinct('asignatura')
                return conviert_html_to_pdf('pro_cronograma/informe_actividades_recurso_aprendizaje.html', {'pagesize': 'A4',
                                                                                                            'data': {
                                                                                                                'carrera': carrera,
                                                                                                                'periodo': periodo,
                                                                                                                'materias': materias
                                                                                                            }})
            except Exception as ex:
                return HttpResponseRedirect("/pro_cronograma?info=%s" % mensaje)

        elif action == 'informe_actividades_autor1':
            mensaje = "Problemas al generar el informe"
            try:
                idprofesor = int(encrypt(request.POST['idprofesor']))
                profesor = Profesor.objects.get(id=idprofesor)
                materias = Materia.objects.filter(status=True, nivel__periodo=periodo, esintroductoria=False, profesormateria__profesor=profesor, profesormateria__tipoprofesor__id=9, profesormateria__activo=True).distinct('asignatura')
                return conviert_html_to_pdf('pro_cronograma/informe_actividades_recurso_aprendizaje1.html', {'pagesize': 'A4',
                                                                                                             'data': {
                                                                                                                 'profesor': profesor,
                                                                                                                 'periodo': periodo,
                                                                                                                 'materias': materias
                                                                                                             }})
            except Exception as ex:
                return HttpResponseRedirect("/pro_cronograma?info=%s" % mensaje)

        elif action == 'informe_seguimiento_tutor_pregrado_criterio':
            mensaje = "Problemas al generar el informe"
            try:
                materias = []
                listacarreras = []
                coord = 0
                suma = 0
                profesormateria = None
                finio = request.POST['fini']
                ffino = request.POST['ffin']
                finic = convertir_fecha(finio)
                ffinc = convertir_fecha(ffino)
                opcionreport = int(request.POST['opcionreport'])
                profesor = Profesor.objects.get(id=int(encrypt(request.POST['idprof'])))
                # 1: grado virtual
                if opcionreport == 1:
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3,
                                                                     materia__nivel__periodo=periodo,
                                                                     activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                # 2 virtual admision
                if opcionreport == 2:
                    coord = 9
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3,
                                                                     materia__nivel__periodo=periodo, activo=True,
                                                                     materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # coordinacion = profesormateria[0].materia.carrera.coordinacionvalida
                # 3 presencial admision
                if opcionreport == 3:
                    coord = 9
                    profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo,
                                                                     activo=True,
                                                                     materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # coordinacion = profesormateria[0].materia.carrera.coordinacionvalida
                if profesormateria:
                    suma = profesormateria.aggregate(total=Sum('hora'))['total']
                    lista = []
                    for x in profesormateria:
                        materias.append(x.materia)
                        if x.materia.carrera():
                            carrera = x.materia.carrera()
                            if not carrera in listacarreras:
                                listacarreras.append(carrera)
                            lista.append(carrera)
                    cuenta1 = collections.Counter(lista).most_common(1)
                    carrera = cuenta1[0][0]
                    coordinacion = carrera.coordinacionvalida

                distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                evidencias = EvidenciaActividadDetalleDistributivo.objects.filter(
                    Q(criterio__distributivo=distributivo) & ((Q(desde__gte=finic) & Q(hasta__lte=ffinc)) | (
                            Q(desde__lte=finic) & Q(hasta__gte=ffinc)) | (Q(desde__lte=ffinc) & Q(desde__gte=finic)) | (
                                                                      Q(hasta__gte=ffinc) & Q(
                                                                  hasta__lte=ffinc)))).distinct().order_by('desde')
                titulaciones = distributivo.profesor.persona.mis_titulaciones()
                titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])
                if opcionreport == 3:
                    # asistencia
                    asistencias_registradas = 0
                    asistencias_no_registradas = 0
                    asistencias_dias_feriados = 0
                    asistencias_dias_suspension = 0
                    resultado = []
                    fechas_clases = []
                    lista_clases_dia_x_fecha = []
                    for profesormate in profesormateria:
                        data_asistencia = profesormate.asistencia_docente(finic, ffinc, periodo, True,
                                                                          lista_clases_dia_x_fecha)
                        asistencias_registradas += data_asistencia['total_asistencias_registradas']
                        asistencias_no_registradas += data_asistencia['total_asistencias_no_registradas']
                        asistencias_dias_feriados += data_asistencia['total_asistencias_dias_feriados']
                        asistencias_dias_suspension += data_asistencia['total_asistencias_dias_suspension']
                        lista_clases_dia_x_fecha = data_asistencia['lista_clases_dia_x_fecha']
                        for fecha_clase in data_asistencia['lista_fechas_clases']:
                            if (fecha_clase in fechas_clases) == 0:
                                fechas_clases.append(fecha_clase)

                    # marcadas
                    marcadas = None
                    marcadas = LogDia.objects.filter(persona=distributivo.profesor.persona, fecha__in=fechas_clases,
                                                     status=True).order_by('fecha')
                    total = None
                    i = 0
                    subtotal = None
                    totalfinal = 0
                    if marcadas:
                        for m in marcadas:
                            if m.procesado:
                                i = i + 1
                                logmarcada = m.logmarcada_set.filter(status=True).order_by('time')
                                if logmarcada.count() >= 2:
                                    horas1 = logmarcada[0]
                                    horas2 = logmarcada[1]
                                    formato = "%H:%M:%S"
                                    subtotal = datetime.strptime(str(horas2.time.time()), formato) - datetime.strptime(
                                        str(horas1.time.time()), formato)
                                    if logmarcada.count() == 4:
                                        horas3 = logmarcada[2]
                                        horas4 = logmarcada[3]
                                        subtotal += datetime.strptime(str(horas4.time.time()),
                                                                      formato) - datetime.strptime(
                                            str(horas3.time.time()), formato)
                                    if i == 1:
                                        total = subtotal
                                    else:
                                        total = total + subtotal
                    if total:
                        sec = total.total_seconds()
                        hours = sec // 3600
                        minutes = (sec // 60) - (hours * 60)
                        totalfinal = str(int(hours)) + ':' + str(int(minutes)) + ': 00'
                    # -------------------------------------------------------------
                    porcentaje = 0
                    asistencias_reg = asistencias_registradas + asistencias_dias_feriados + asistencias_dias_suspension
                    if (asistencias_reg + asistencias_no_registradas) > 0:
                        porcentaje = Decimal(
                            ((asistencias_reg * 100) / (asistencias_reg + asistencias_no_registradas))).quantize(
                            Decimal('.01'))
                    resultado.append((asistencias_reg, asistencias_no_registradas, porcentaje))
                return conviert_html_to_pdf('pro_cronograma/informe_seguimiento_tutor_pregrado_criterio.html', {'pagesize': 'A4',
                                                                                                                'data': {
                                                                                                                    'distributivo': distributivo,
                                                                                                                    'periodo': periodo,
                                                                                                                    'fini': finio,
                                                                                                                    'ffin': ffino,
                                                                                                                    'finic': finic,
                                                                                                                    'ffinc': ffinc,
                                                                                                                    'suma': suma,
                                                                                                                    'materias': materias,
                                                                                                                    'titulaciones': titulaciones,
                                                                                                                    'opcionreport': opcionreport,
                                                                                                                    'resultado': resultado if opcionreport == 3 else None,
                                                                                                                    'coord': coord, 'coordinacion': coordinacion,
                                                                                                                    'listacarreras': listacarreras,
                                                                                                                    'evidencias': evidencias}})
            except Exception as ex:
                return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=%s" % mensaje)

        if action == 'actualizarpreferenciaperiodo':
            try:
                codigoperiodo = Periodo.objects.get(pk=request.POST['codigoperiodo'])
                codigoperiodo.preferenciaactividad = True
                codigoperiodo.save(request)
                log(u'Se migro criterio y actividades de preferencias: periodo[%s]' % (codigoperiodo), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        if action == 'profesoresmigraractividad':
            try:
                profesores = ProfesorDistributivoHoras.objects.values('id', 'profesor_id', 'profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres').filter(periodo=periodo).exclude(profesor__persona__apellido1__icontains='DEFINIR').exclude(profesor__persona__apellido1__icontains='VIRTUAL').exclude(profesor__persona__apellido1__icontains='APELLIDOVIRT').exclude(profesor__persona__nombres__icontains='DEFINIR').exclude(
                    profesor__persona__nombres__icontains='VIRTUAL').exclude(profesor__persona__apellido2__icontains='VIRTUAL').order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')
                return JsonResponse({"result": "ok", "cantidad": len(profesores), "profesores": list(profesores)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'profesorescalcularhoras':
            try:
                profesores = ProfesorDistributivoHoras.objects.values('id', 'profesor_id', 'profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres').filter(periodo=periodo).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')
                return JsonResponse({"result": "ok", "cantidad": len(profesores), "profesores": list(profesores)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'migraactividadpreferencia':
            try:
                distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['iddistributivo'])
                listadocriteriosdocente = PreferenciaDetalleActividadesCriterio.objects.filter(criteriodocenciaperiodo__periodo=distributivo.periodo, profesor=distributivo.profesor, status=True).exclude(criteriodocenciaperiodo__criterio__id__in=[30, 56, 46, 57, 70, 68, 92, 100, 71, 11])
                listadocriteriosinvestigacion = PreferenciaDetalleActividadesCriterio.objects.filter(criterioinvestigacionperiodo__periodo=distributivo.periodo, profesor=distributivo.profesor, status=True)
                listadocriteriosgestion = PreferenciaDetalleActividadesCriterio.objects.filter(criteriogestionperiodo__periodo=distributivo.periodo, profesor=distributivo.profesor, status=True)
                for lisdoc in listadocriteriosdocente:
                    if not DetalleDistributivo.objects.filter(distributivo=distributivo, criteriodocenciaperiodo=lisdoc.criteriodocenciaperiodo):
                        detalledistributivo = DetalleDistributivo(distributivo=distributivo,
                                                                  criteriodocenciaperiodo=lisdoc.criteriodocenciaperiodo,
                                                                  horas=lisdoc.horas)
                        detalledistributivo.save(request)
                        detalledistributivo.verifica_actividades(horas=detalledistributivo.horas)

                for lisinv in listadocriteriosinvestigacion:
                    if not DetalleDistributivo.objects.filter(distributivo=distributivo, criterioinvestigacionperiodo=lisinv.criterioinvestigacionperiodo):
                        detalledistributivo = DetalleDistributivo(distributivo=distributivo,
                                                                  criterioinvestigacionperiodo=lisinv.criterioinvestigacionperiodo,
                                                                  horas=lisinv.horas)
                        detalledistributivo.save(request)
                        detalledistributivo.verifica_actividades(horas=detalledistributivo.horas)

                for lisges in listadocriteriosgestion:
                    if not DetalleDistributivo.objects.filter(distributivo=distributivo, criteriogestionperiodo=lisges.criteriogestionperiodo):
                        detalledistributivo = DetalleDistributivo(distributivo=distributivo,
                                                                  criteriogestionperiodo=lisges.criteriogestionperiodo,
                                                                  horas=lisges.horas)
                        detalledistributivo.save(request)
                        detalledistributivo.verifica_actividades(horas=detalledistributivo.horas)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'reporterecursosadm':
            try:
                data['periodo'] = periodo
                data['fechaactual'] = datetime.now().date()
                distri = DistributivoPersona.objects.values_list('persona_id').filter(estadopuesto_id=1, regimenlaboral_id=1, status=True)
                promate = ProfesorMateria.objects.values_list('profesor_id').filter(profesor__persona_id__in=distri, status=True, materia__nivel__periodo=periodo).distinct()
                data['listadodocentes'] = Profesor.objects.filter(pk__in=promate, status=True)
                data['listadorecurso'] = [[1, 'TAREA'], [2, 'FORO'], [3, 'TEST'], [4, 'COMPENDIO'],
                                          [5, 'GUÍA DEL DOCENTE'], [6, 'GUÍA DEL ESTUDIANTE'],
                                          [7, 'MATERIALES COMPLEMENTARIOS'], [8, 'PRESENTACIÓN']]
                return conviert_html_to_pdf(
                    'adm_criteriosactividadesdocente/recursosilaboadm_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        if action == 'actualizahorasplanificadas':
            try:
                profesorhora = ProfesorConfigurarHoras.objects.get(pk=request.POST['codigo'])
                profesorhora.horaminima = request.POST['horminima']
                profesorhora.horamaxima = request.POST['hormaxima']
                profesorhora.horamaximaasignatura = request.POST['horamaximaasignatura']
                profesorhora.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'tipocategorizacion':
            try:
                rango = CategorizacionDocente.objects.filter(profesortipo=request.POST['id'])
                if rango.values('id').count() > 0:
                    rangos = []
                    for r in rango:
                        rangos.append({"id": r.id, "valor": unicode(r)})
                    return JsonResponse({"result": "ok", "data": rangos})
                return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        if action == 'updatehorasdedicacion':
            try:
                cmbdedicacion = request.POST['cmbdedicacion']
                id_hmin = request.POST['id_hmin']
                id_hmax = request.POST['id_hmax']
                id_hmaxasignatura = request.POST['id_hmaxasignatura']
                cmbtipo = request.POST['cmbtipo']
                cmbcate = request.POST['cmbcate']
                profesorhora = ProfesorConfigurarHoras.objects.filter(periodo=periodo, dedicacion_id=cmbdedicacion, nivelcategoria_id=cmbtipo, categoria_id=cmbcate, status=True)
                profesorhora.update(horaminima=id_hmin, horamaxima=id_hmax, horamaximaasignatura=id_hmaxasignatura, categoria_id=cmbcate)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        if action == 'updatedocentes':
            try:
                listadodistrivutibo = ProfesorDistributivoHoras.objects.filter(periodo_id=request.POST['cmbperiodos'], status=True)
                for lperiodo in listadodistrivutibo:
                    if not ProfesorConfigurarHoras.objects.filter(periodo=periodo, profesor=lperiodo.profesor, status=True):
                        profesorhoras = ProfesorConfigurarHoras(periodo=periodo,
                                                                profesor=lperiodo.profesor,
                                                                dedicacion=lperiodo.dedicacion,
                                                                categoria=lperiodo.categoria,
                                                                nivelcategoria=lperiodo.nivelcategoria)
                        profesorhoras.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})
        if action == 'delhorario':
            try:
                horario = HorarioTutoriaAcademica.objects.get(id=int(encrypt(request.POST['id'])))
                exed = True if 'max' in request.POST and request.POST['max'] == '1' else False
                # if horario.en_uso() and not exed:
                #     return JsonResponse({"result": "bad", "mensaje": u"Ya existen horario creado."})
                horario.status = False
                horario.save(request)
                log(u'Eliminó un horario de tutoría académica: %s' % horario, request, "add")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'buscarturnos':
            try:
                dia = int(request.POST['dia'])
                profesor = request.POST['idprofesor']
                idturnostutoria = []
                if HorarioTutoriaAcademica.objects.filter(status=True, dia=dia, profesor__id=profesor, periodo=periodo).exists():
                    idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id', flat=True).filter(status=True, dia=dia, profesor=profesor, periodo=periodo).distinct()
                turnosadd = Turno.objects.filter(status=True, mostrar=True, sesion_id__in=SESION_ID).exclude(id__in=idturnostutoria).distinct().order_by('comienza')

                # else:
                #     turnosparatutoria = Turno.objects.filter(status=True, sesion_id=SESION_ID).distinct().order_by('comienza')
                #     idturnos = []
                #     idturnoscomplexivo = []
                #     idturnoactividades = []
                #     idturnostutoria = []
                #     idmatriculas = []
                #     idmaterias_matricula = []
                #     idturnos_matricula = []
                #     profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, activo=True).distinct()
                #     idmaterias = profesormaterias.values_list('materia_id')
                #
                #     for profemate in profesormaterias:
                #         idmatriculas += MateriaAsignada.objects.values_list('matricula_id').filter(
                #             materia=profemate.materia,
                #             status=True, estado_id=3,
                #             materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(materia__asignaturamalla__malla_id__in=[353, 22]).distinct()
                #         idmaterias_matricula = MateriaAsignada.objects.values_list('materia_id').filter(
                #             matricula_id__in=idmatriculas,
                #             status=True, estado_id=3,
                #             materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(materia__asignaturamalla__malla_id__in=[353, 22]).distinct().distinct()
                #
                #     if Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                #                                                      materia__nivel__periodo=periodo,
                #                                                      materia_id__in=idmaterias_matricula, dia=dia).exists():
                #         idturnos_matricula = Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                #                                                                            materia__nivel__periodo=periodo,
                #                                                                            materia_id__in=idmaterias_matricula,
                #                                                                            dia=dia).distinct()
                #
                #     if Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                #                                                      materia__nivel__periodo=periodo,
                #                                                      materia_id__in=idmaterias, dia=dia).exists():
                #         idturnos = Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                #                                                                  materia__nivel__periodo=periodo,
                #                                                                  materia_id__in=idmaterias, dia=dia).distinct()
                #
                #     if ComplexivoClase.objects.values_list('turno__id').filter(activo=True,
                #                                                                materia__profesor__profesorTitulacion=profesor,
                #                                                                materia__status=True, dia=dia).exists():
                #         idturnoscomplexivo = ComplexivoClase.objects.values_list('turno__id').filter(activo=True,
                #                                                                                      materia__profesor__profesorTitulacion=profesor,
                #                                                                                      materia__status=True, dia=dia).distinct()
                #
                #     if ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo,
                #                                      detalledistributivo__distributivo__profesor=profesor, dia=dia).exists():
                #         idturnoactividades = ClaseActividad.objects.values_list('turno__id').filter(
                #             detalledistributivo__distributivo__periodo=periodo,
                #             detalledistributivo__distributivo__profesor=profesor, dia=dia).distinct()
                #     else:
                #         if ClaseActividad.objects.values_list('turno__id').filter(
                #                 actividaddetalle__criterio__distributivo__periodo=periodo,
                #                 actividaddetalle__criterio__distributivo__profesor=profesor, dia=dia).exists():
                #             idturnoactividades = ClaseActividad.objects.values_list('turno__id').filter(
                #                 actividaddetalle__criterio__distributivo__periodo=periodo,
                #                 actividaddetalle__criterio__distributivo__profesor=profesor, dia=dia).distinct()
                #     if HorarioTutoriaAcademica.objects.filter(status=True, dia=dia, profesor=profesor, periodo=periodo).exists():
                #         idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, dia=dia, profesor=profesor, periodo=periodo).distinct()
                #     turnoclases = Turno.objects.filter(Q(id__in=idturnos) |
                #                                        Q(id__in=idturnoscomplexivo) |
                #                                        Q(id__in=idturnoactividades) |
                #                                        Q(id__in=idturnostutoria) |
                #                                        Q(id__in=idturnos_matricula)
                #                                        ).distinct().order_by('comienza')
                #
                #     idturnosadd = []
                #     for turnotutoria in turnosparatutoria:
                #         for turnoclase in turnoclases:
                #             if turnotutoria.comienza <= turnoclase.termina and turnotutoria.termina >= turnoclase.comienza:
                #                 idturnosadd.append(turnotutoria.id)

                # turnosadd = Turno.objects.filter(status=True, sesion_id=SESION_ID).exclude(id__in=idturnostutoria).distinct().order_by('comienza')
                lista, lista_materias = [], []
                profmaterias = ProfesorMateria.objects.filter(status=True, profesor=profesor, materia__nivel__periodo=periodo, activo=True)
                for turno in turnosadd:
                    turno_comienza, turno_termina = turno.comienza.strftime("%H:%M %p"), turno.termina.strftime("%H:%M %p")
                    if periodo.tipo_id in [3, 4]:
                        if turno.sesion_id == 19:
                            lista.append([turno.id, u'Turno %s [%s a %s]' % (str(turno.turno), turno_comienza, turno_termina)])
                    else:
                        lista.append([turno.id, u'Turno %s [%s a %s]' % (str(turno.turno), turno_termina, turno_termina)])

                for profmateria in profmaterias:
                    lista_materias.append([profmateria.id, profmateria.materia.nombre_mostrar_solo()])

                return JsonResponse({'result': 'ok', 'lista': lista, 'lista_materias':lista_materias})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datoos."})

        elif action == 'edithorariotutoria':
            try:
                pm = ProfesorMateria.objects.get(pk=request.POST['idprofmate'])

                fi, ff = request.POST.get('fi', ''), request.POST.get('ff', '')

                if not fi or not ff:
                    return JsonResponse({'result': 'bad', 'mensaje': u'Algunos campos se encuentran vacíos.'})

                fi = convertir_fecha_invertida(fi)
                ff = convertir_fecha_invertida(ff)

                if not ff > fi:
                    return JsonResponse({'result': 'bad', 'mensaje': u'La fecha fin no puede ser menor que la fecha de inicio.'})

                fecha_min_limite, fecha_max_limite = pm.materia.inicio, periodo.get_periodoacademia().fecha_fin_horario_tutoria

                if fi < fecha_min_limite:
                    return JsonResponse({'result': 'bad',
                                         'mensaje': u'La fecha de inicio ingresada es menor a la fecha (%s) que corresponde al inicio de la materia.' % fecha_min_limite.strftime('%d-%m-%Y')})

                if ff > fecha_max_limite:
                    return JsonResponse({'result': 'bad',
                                         'mensaje': u'La fecha fin ingresada es mayor a la fecha (%s) que corresponde a la fecha fin de la tutoría académica.' % fecha_max_limite.strftime('%d-%m-%Y')})


                horario = HorarioTutoriaAcademica.objects.get(pk=request.POST['id_tutoria'])
                if not HorarioTutoriaAcademica.objects.values('id').filter(dia=horario.dia, turno=horario.turno, profesormateria=pm, fecha_inicio_horario_tutoria=fi, fecha_fin_horario_tutoria=ff, status=True).exists():
                    horario.fecha_inicio_horario_tutoria, horario.fecha_fin_horario_tutoria = fi, ff
                    horario.profesormateria = pm
                    horario.save()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({'result': 'bad',
                                         'mensaje': u'Ya existe un horario de tutoría registrado en esta fecha.'})

            except Exception as ex:
                pass
        if action == 'addhorariotutoria':
            try:
                iddia = int(request.POST['iddia'])
                idturno = int(request.POST['idturno'])
                profesor = request.POST['profesor']
                iddistri = request.POST['iddistri']
                distributivo = ProfesorDistributivoHoras.objects.filter(id=iddistri).first()
                #profmateria = ProfesorMateria.objects.get(status=True, profesor=profesor, materia=distributivo.materia, materia__nivel__periodo=periodo, activo=True)
                profmateria = ProfesorMateria.objects.get(id=int(request.POST['idprofmate']))

                turno = Turno.objects.get(id=idturno)

                fi = request.POST.get('fi', '')
                ff = request.POST.get('ff', '')
                if fi and ff:
                    fi = convertir_fecha_invertida(fi)
                    ff = convertir_fecha_invertida(ff)

                fecha_min_limite = profmateria.materia.inicio
                fecha_max_limite = periodo.get_periodoacademia().fecha_fin_horario_tutoria if periodo.get_periodoacademia().fecha_fin_horario_tutoria else profmateria.materia.fin

                if fi < fecha_min_limite:
                    return JsonResponse({'result': 'bad', 'mensaje': u'La fecha de inicio ingresada es menor a la fecha inicio de la materia %s.' % fecha_min_limite.strftime('%d-%m-%Y')})

                if ff > fecha_max_limite:
                    return JsonResponse({'result': 'bad', 'mensaje': u'La fecha fin ingresada es mayor a la fecha fin de la tutoría %s.' % fecha_max_limite.strftime('%d-%m-%Y')})
                # suma = 0
                # sumaactividad = 2
                if not HorarioTutoriaAcademica.objects.filter(status=True, profesor__id=profesor, periodo=periodo, dia=iddia, turno=turno, profesormateria=profmateria, fecha_inicio_horario_tutoria=fi, fecha_fin_horario_tutoria=ff).exists():
                    # if HorarioTutoriaAcademica.objects.filter(status=True, profesor__id=profesor, periodo=periodo, profesormateria=profmateria).exists():
                    #     suma = HorarioTutoriaAcademica.objects.filter(status=True, profesor__id=profesor, periodo=periodo).aggregate(total=Sum('turno__horas'))['total']
                    # if DetalleDistributivo.objects.filter(distributivo__profesor__id=profesor,
                    #                                       distributivo__periodo=periodo,
                    #                                       criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                    #     sumaactividad = DetalleDistributivo.objects.filter(distributivo__profesor__id=profesor,
                    #                                                        distributivo__periodo=periodo,
                    #                                                        criteriodocenciaperiodo__criterio_id__in=[7]).aggregate(total=Sum('horas'))['total']
                    # if int(suma) < int(sumaactividad):
                    horario = HorarioTutoriaAcademica(profesor_id=profesor, periodo=periodo, dia=iddia, turno=turno, profesormateria=profmateria, fecha_inicio_horario_tutoria=fi, fecha_fin_horario_tutoria=ff)
                    horario.save(request)
                    log(u'Ingreso un horario de tutoría académica: %s' % horario, request, "add")
                    return JsonResponse({"result": "ok"})
                    # else:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya cumple con sus horas de tutoria planificada."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un horario ingresado."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # if action == 'solicitudeshorariotutoria':
        #     try:
        #         from inno.models import DetalleSolicitudHorarioTutoria
        #         solicitud = DetalleSolicitudHorarioTutoria.objects.get(id=int(request.POST['id']))
        #         solicitud.estadosolicitud = 1 if request.POST['aprobar'] == 'true' else 2
        #         if request.POST['aprobar'] == 'true':
        #             if not request.POST['fecha']:
        #                 raise NameError(u"Es obligatorio poner una fecha límite para el ingreso de horario")
        #         solicitud.fecha = request.POST['fecha'] if request.POST['fecha'] else None
        #         solicitud.repuestadirector = request.POST['observacion']
        #         solicitud.save(request)
        #         aprobar = 'Aprobo' if solicitud.estadosolicitud == 1 else 'Rechazo'
        #         log('{} solicitud de horario de tutorias (Director) SGA: {}'.format(aprobar, solicitud), request, "edit")
        #         return JsonResponse({"result": "ok"})
        #     except Exception as e:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error. %s" % str(e)})
        # return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

        if action == 'addactividaddoc':
            from inno.pro_horarios_actividades import verificar_turno_tutoria
            try:
                profesor = Profesor.objects.get(id=request.POST['idprofesor'])
                hoy = datetime.now().date()
                periodo = request.session['periodo']
                turno = Turno.objects.get(id=request.POST['idturno'])
                if turno:
                    detalle = DetalleDistributivo.objects.get(id=request.POST['idactividad'])
                    tutoria = True if request.POST['tipoactividad'] == '1' and detalle.criteriodocenciaperiodo.criterio.procesotutoriaacademica else False
                    turnotuto = verificar_turno_tutoria(periodo, request.POST['iddia'], profesor, turno.id) if tutoria else None
                    if tutoria and not turnotuto:
                        return JsonResponse({"result": "bad", "mensaje": "Lo sentimos este horario no está disponible para la actividad: <b>" + str(detalle.criteriodocenciaperiodo.criterio) + "</b><br> intente con otro horario u otra actividad"})
                    elif tutoria and turnotuto:
                        turno = turnotuto
                    actividadesdia = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo,
                                                                   dia=request.POST['iddia']).values('id', 'modalidad', 'turno__comienza')
                    clasesdia = Clase.objects.filter(profesor=profesor, materia__nivel__periodo__visible=True, materia__nivel__periodo=periodo, materia__nivel__periodo__visiblehorario=True, activo=True, dia=request.POST['iddia'], materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True, materia__profesormateria__activo=True, materia__profesormateria__status=True, fin__gte=hoy).order_by('inicio')
                    if actividadesdia.filter(Q(turno__comienza__range=(turno.comienza, turno.termina)) | Q(turno__termina__range=(turno.comienza, turno.termina))).exists() or clasesdia.filter(Q(turno__comienza__range=(turno.comienza, turno.termina)) | Q(turno__termina__range=(turno.comienza, turno.termina))).exists():
                        return JsonResponse({"result": "bad", "mensaje": "Lo sentimos el horario que intenta elegir da conflicto con una o más horas de su horario, elija otro turno para continuar"})
                    actividad = ClaseActividad(detalledistributivo_id=request.POST['idactividad'],
                                               tipodistributivo=request.POST['tipoactividad'],
                                               turno=turno,
                                               dia=request.POST['iddia'],
                                               inicio=periodo.inicio,
                                               fin=periodo.fin,
                                               estadosolicitud=1,
                                               modalidad=None,
                                               ordenmarcada=None
                                               )

                    actividad.save(request)
                    tipo = actividad.tipodistributivo
                    if tipo == '1':
                        tipodes = 'DOCENCIA'
                        des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                    elif tipo == '2':
                        tipodes = 'INVESTIGACION'
                        des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                    else:
                        tipodes = 'GESTION'
                        des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                    log(u'Adicionó horario de actividad: %s - %s  turno: %s dia: %s' % (des, tipodes, str(actividad.turno), str(actividad.dia)), request, "add")
                    return JsonResponse({"result": "ok", "codiactividad": actividad.id})
                else:
                    JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'delactividaddoc':
            try:
                des=''
                actividad = ClaseActividad.objects.get(pk=request.POST['id'])
                idactividad = actividad.id
                tipo = actividad.tipodistributivo
                if actividad.detalledistributivo:
                    if tipo in (1, 4):
                        des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                    if tipo == 2:
                        des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                    if tipo == 3:
                        des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                if actividad.actividaddetalle:
                    des = actividad.actividaddetalle.nombre
                turno = actividad.turno_id
                dia = actividad.dia
                return JsonResponse({"result": "ok", 'idactividad': idactividad, 'turno': turno, 'dia': dia, 'des': des})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addaprobacionevidencia':
            try:
                obse = request.POST['obse']
                esta = request.POST['esta']
                client_address = get_client_ip(request)
                capippriva = request.POST['capippriva'] if 'capippriva' in request.POST else ''
                browser = request.POST['navegador']
                ops = request.POST['os']
                cookies = request.POST['cookies']
                screensize = request.POST['screensize']
                evidencia = EvidenciaActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                evidencia.estadoaprobacion = esta
                evidencia.save(request)
                historial = HistorialAprobacionEvidenciaActividad(evidencia=evidencia,
                                                                  aprobacionpersona=persona,
                                                                  observacion=obse,
                                                                  fechaaprobacion=datetime.now().date(),
                                                                  estadoaprobacion=esta)

                historial.save(request)
                estadoevidencia = evidencia.get_estadoaprobacion_display()
                send_html_mail("Notificación de estado de evidencia.", "emails/estadoevidenciadocente.html", {'sistema': 'SGA-EVIDENCIA', 'estadoevidencia': estadoevidencia,'evidencia': evidencia,'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminaractividad':
            try:
                actividad = ClaseActividad.objects.get(pk=request.POST['idactividad'])
                nomturno = actividad.turno
                nomdia = actividad.dia
                id = actividad.detalledistributivo_id
                if actividad.detalledistributivo:
                    if actividad.tipodistributivo == 1:
                        tipodes = 'DOCENCIA'
                        des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                    elif actividad.tipodistributivo == 2:
                        tipodes = 'INVESTIGACION'
                        des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                    elif actividad.tipodistributivo == 3:
                        tipodes = 'GESTION'
                        des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                    else:
                        tipodes = 'VINCULACIÓN'
                        des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                if actividad.actividaddetalle:
                    tipodes = 'SUB ACTIVIDADES'
                    des = actividad.actividaddetalle.nombre
                actividad.delete()
                # ordenar_marcada(request.session['periodo'], id, nomdia, profesor)
                log(u'Eliminó horario de actividad: %s - %s  turno: %s dia: %s' % (des, tipodes, str(nomturno), str(nomdia)), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'bloqueardistributivo':
            try:
                pk=request.POST['id']
                distributivo = ProfesorDistributivoHoras.objects.get(id=pk)
                if distributivo.bloqueardistributivo:
                    mensaje='Desbloqueó'
                    distributivo.bloqueardistributivo = False
                else:
                    mensaje = 'Bloqueó'
                    distributivo.bloqueardistributivo = True
                distributivo.save(request)
                log(u'%s el distributivo del docente: %s' % (mensaje, str(distributivo.profesor.persona.nombre_completo())), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error en la transacción. {}".format(str(ex))})

        if action == 'firmadocumento':
            try:
                import json
                # Parametros
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    raise NameError("Debe seleccionar ubicación de la firma")
                x = txtFirmas[-1]
                idevidencia = int(encrypt(request.POST['id_objeto']))
                evidenciaactividad = EvidenciaActividadDetalleDistributivo.objects.get(pk=idevidencia)
                responsables = request.POST.getlist('responsables[]')
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                url_archivo = (SITE_STORAGE + request.POST["url_archivo"]).replace('\\', '/')
                _name = generar_nombre(f'evidencia_{request.user.username}_{idevidencia}_', 'firmada')
                folder = os.path.join(SITE_STORAGE, 'media', 'evidenciafirmadas', '')

                # Firmar y guardar archivo en folder definido.
                firma = firmararchivogenerado(request, passfirma, firma, url_archivo, folder, _name, x["numPage"], x["x"], x["y"], x["width"], x["height"])
                if firma != True:
                    raise NameError(firma)
                log(u'Firmo Documento: {}'.format(_name), request, "add")

                folder_save = os.path.join('evidenciafirmadas', '').replace('\\', '/')
                url_file_generado = f'{folder_save}{_name}.pdf'
                evidenciaactividad.archivofirmado = url_file_generado
                evidenciaactividad.save(request)
                historial = HistorialAprobacionEvidenciaActividad(evidencia=evidenciaactividad,
                                                                  aprobacionpersona=persona,
                                                                  observacion='DOCUMENTO FIRMADO',
                                                                  fechaaprobacion=datetime.now().date(),
                                                                  estadoaprobacion=2)

                historial.save(request)
                auditoria = EvidenciaActividadAudi(evidencia=evidenciaactividad,
                                                   archivo=url_file_generado)

                auditoria.save(request)
                log(u'Guardo archivo firmado: {}'.format(evidenciaactividad), request, "add")
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

        if action == 'recalcularhorario':
            try:
                pk = request.POST['id']
                distributivo = ProfesorDistributivoHoras.objects.get(id=pk)
                horarioactividades = ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=distributivo.profesor, detalledistributivo__distributivo__periodo=distributivo.periodo)
                criteriosnew = list(DetalleDistributivo.objects.filter(Q(distributivo__profesor=distributivo.profesor, distributivo__periodo=distributivo.periodo),Q(criteriodocenciaperiodo_id__isnull=False) | Q(
                    criterioinvestigacionperiodo_id__isnull=False) | Q(criteriogestionperiodo_id__isnull=False)).exclude(
                    criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '118',
                                                              '28', '30', '46', '7']).values_list('id', flat=True))
                # for h in horarioactividades:
                #     if not h.actividaddetallehorario.criterio_vigente():
                #         new = h.detalledistributivo.detalleactividadcriterio().horas
                #         old = h.actividaddetallehorario.horas
                #         if new > old:
                #             criteriosnew.append(h.detalledistributivo.id)
                for horario in horarioactividades:
                    horastotales = horario.actividaddetallehorario.horas
                    if horario.actividaddetallehorario:
                        if not horario.actividaddetallehorario.criterio_vigente():
                            vigentenew = horario.detalledistributivo.detalleactividadcriterio()
                            horasnew = vigentenew.horas
                            sumahoras = len(ClaseActividad.objects.filter(actividaddetallehorario=vigentenew).values('id'))
                            horasold = len(ClaseActividad.objects.filter(actividaddetallehorario=horario.actividaddetallehorario).values('id'))
                            if sumahoras < horasnew:
                                hor = ClaseActividad(detalledistributivo=horario.detalledistributivo,
                                                     tipodistributivo=horario.tipodistributivo,
                                                     turno=horario.turno,
                                                     dia=horario.dia,
                                                     inicio=vigentenew.desde,
                                                     fin=vigentenew.hasta,
                                                     estadosolicitud= 2,
                                                     modalidad=None,
                                                     ordenmarcada=None, actividaddetallehorario=vigentenew)
                                hor.save(request)
                            # elif horasold > sumahoras:
                            else:
                                if criteriosnew:
                                    for crtn in criteriosnew:
                                        crtn = DetalleDistributivo.objects.get(id=crtn)
                                        critn = crtn.detalleactividadcriterio()
                                        horasnew = len(ClaseActividad.objects.filter(detalledistributivo=crtn, actividaddetallehorario=critn))
                                        horasold = critn.horas
                                        if horasold > horasnew:
                                            hor = ClaseActividad(detalledistributivo=crtn,
                                                                 tipodistributivo=crtn.tipo(),
                                                                 turno=horario.turno,
                                                                 dia=horario.dia,
                                                                 inicio=critn.desde,
                                                                 fin=critn.hasta,
                                                                 estadosolicitud=2,
                                                                 modalidad=None,
                                                                 ordenmarcada=None, actividaddetallehorario=critn)
                                            hor.save(request)
                                            break
                log("Recalculó el horario de actividades del docente {}".format(str(distributivo.profesor)), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as e:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error en la transacción. {}".format(str(ex))})

        if action == 'descargainformes':
            try:
                idmeses = request.POST['idmeses'].split(',')
                es_decano = ResponsableCoordinacion.objects.values('id').filter(periodo=periodo, status=True, persona=persona, tipo=1).exists()
                es_coordinador = CoordinadorCarrera.objects.values('id').filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True).exists()
                if es_decano or es_coordinador:
                    listadoinformes = HistorialInforme.objects.filter(informe__distributivo__periodo=periodo, personafirmas=persona, informe__fechafin__month__in=idmeses, firmado=True, estado=4, status=True)
                else:
                    listadoinformes = HistorialInforme.objects.filter(informe__distributivo__periodo=periodo, informe__fechafin__month__in=idmeses, firmado=True, estado=4, informe__estado=4, status=True)
                dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                directory = os.path.join(SITE_STORAGE, 'media/informemensualdocente')

                try:
                    os.stat(directory)
                except:
                    os.mkdir(directory)

                url = os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', 'listadoinformes.zip')
                url_zip = url
                fantasy_zip = zipfile.ZipFile(url, 'w')
                if listadoinformes:
                    for infor in listadoinformes:
                        if infor.informe.archivo:
                            # carpeta_infor = f"Carpeta_{infor.distributivo.profesor}/"
                            # Agregar el archivo PDF a la carpeta de la inscripción dentro del ZIP
                            fantasy_zip.write(infor.informe.archivo.path, os.path.basename(infor.informe.archivo.path))
                            # fantasy_zip.write(ins.rutapdf.path)
                else:
                    raise NameError('Erro al generar')
                fantasy_zip.close()
                response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=listadoinformes.zip'
                return response
            except Exception as es:
                pass

        if action == 'descargainformesxtipo':
            try:
                codigo = request.POST['codigo']
                idtipo = request.POST['idtipo']
                numeromes = request.POST['numeromes']
                if int(idtipo) == 1:
                    listadoinformes = HistorialInforme.objects.filter(informe__distributivo__periodo=periodo, informe__fechafin__month__in=numeromes, informe__distributivo__coordinacion_id=codigo, firmado=True, estado=4, informe__estado=4, status=True)
                if int(idtipo) == 2:
                    listadoinformes = HistorialInforme.objects.filter(informe__distributivo__periodo=periodo, informe__fechafin__month__in=numeromes, informe__distributivo__carrera_id=codigo, firmado=True, estado=4, informe__estado=4, status=True)
                dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                directory = os.path.join(SITE_STORAGE, 'media/informemensualdocente')

                try:
                    os.stat(directory)
                except:
                    os.mkdir(directory)

                url = os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', 'listadoinformes.zip')
                url_zip = url
                fantasy_zip = zipfile.ZipFile(url, 'w')
                if listadoinformes:
                    for infor in listadoinformes:
                        if infor.informe.archivo:
                            # carpeta_infor = f"Carpeta_{infor.distributivo.profesor}/"
                            # Agregar el archivo PDF a la carpeta de la inscripción dentro del ZIP
                            fantasy_zip.write(infor.informe.archivo.path, os.path.basename(infor.informe.archivo.path))
                            # fantasy_zip.write(ins.rutapdf.path)
                else:
                    raise NameError('Erro al generar')
                fantasy_zip.close()
                response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                response['Content-Disposition'] = 'attachment; filename=listadoinformes.zip'
                return response
            except Exception as es:
                pass

        if action == 'recordatorioinforme':
            try:
                numeromes = request.POST['numeromes']
                nommesoculto = request.POST['nommesoculto']
                yearmesoculto = request.POST['yearmesoculto']
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]
                listadofaltantes = []
                if CoordinadorCarrera.objects.filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True).exists():
                    carreras = CoordinadorCarrera.objects.values_list('carrera_id').filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True)
                    docentesfirmaron = HistorialInforme.objects.values_list('informe__distributivo__profesor_id').filter(informe__fechafin__month=numeromes, informe__distributivo__periodo=periodo, informe__distributivo__carrera_id__in=carreras, estado=2, status=True)
                    listadofaltantes = ProfesorDistributivoHoras.objects.filter(periodo=periodo, carrera_id__in=carreras, profesor__persona__real=True, status=True).exclude(profesor_id__in=docentesfirmaron).order_by('profesor__persona__apellido1')

                if not listadofaltantes:
                    raise NameError(f'Esta opción se encuentra habilitada solo para directores de carrera.')

                for ldoc in listadofaltantes:
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    send_html_mail("Recordatorio de entrega informe mensual..",
                                   "emails/recordatorioinformemensual.html", {'sistema': 'SGA-INFORME',  'distributivo': ldoc,
                                                                              'nommesoculto': nommesoculto, 'yearmesoculto': yearmesoculto,
                                                                              'fecha': datetime.now().date(), 'hora': datetime.now().time(), 't': miinstitucion()}, ldoc.profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[cuenta][1])
                    noti = Notificacion(titulo='¡Tiene un nuevo recordatorio¡',
                                        cuerpo='Usted no ha realizado la generación o legalización de su informe mensual de cumplimiento de sus actividades correspondientes al mes: ' + str(nommesoculto) + ' - ' + str(yearmesoculto) +'.' +
                                               '<br>Recuerde que el informe se debe entregar hasta los primeros cinco (5) del mes siguiente.',
                                        destinatario=ldoc.profesor.persona,
                                        url='',
                                        prioridad=2, app_label='SGA',
                                        fecha_hora_visible=datetime.now(), tipo=1,
                                        en_proceso=False)
                    noti.save(request)

                    y, m = int(yearmesoculto), int(numeromes)
                    fechainicioinforme, fechafininforme = date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
                    h = HistorialRecordatorioGenerarInforme(distributivo=ldoc, fechanotificacion=datetime.now(), fechainicioinforme=fechainicioinforme, fechafininforme=fechafininforme)
                    h.save(request)

                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addinforme':
            try:
                form = InformeForm(request.POST)
                newfile = None
                historial = HistorialInforme.objects.get(pk=request.POST['id'])
                if 'archivoinforme' in request.FILES:
                    newfile = request.FILES['archivoinforme']
                    if newfile:
                        if newfile.size > 20971520:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                nombrepersona = remover_caracteres_especiales_unicode(historial.informe.distributivo.profesor.persona.apellido1 + ' ' + historial.informe.distributivo.profesor.persona.apellido2 + ' ' + historial.informe.distributivo.profesor.persona.nombres)
                                nombrepdf = f'{nombrepersona}_{nombremes(historial.informe.fechafin.month).upper()}_{historial.informe.fechafin.year}_'
                                newfile._name = generar_nombre(nombrepdf, newfile._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extensión. pdf."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta de subir informe."})

                folder_save = os.path.join('informemensualdocente', '').replace('\\', '/')
                historial.archivo = newfile
                historial.fechafirma = datetime.now().date()
                historial.firmado = True
                historial.save(request)

                historial.informe.estado = historial.estado
                historial.informe.archivo = historial.archivo
                historial.informe.save(request)

                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addjustificacion':
            try:
                form = JustificarInformeForm(request.POST)
                newfile = None
                historial = HistorialInforme.objects.get(pk=request.POST['id'])
                informe = historial.informe
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        if newfile.size > 20971520:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                nombrepersona = remover_caracteres_especiales_unicode(historial.informe.distributivo.profesor.persona.apellido1 + ' ' + historial.informe.distributivo.profesor.persona.apellido2 + ' ' + historial.informe.distributivo.profesor.persona.nombres)
                                nombrepdf = f'JUSTIFICA_{nombrepersona}_{nombremes(historial.informe.fechafin.month).upper()}_{historial.informe.fechafin.year}_'
                                newfile._name = generar_nombre(nombrepdf, newfile._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extensión. pdf."})

                    folder_save = os.path.join('justificacioninformedocente', '').replace('\\', '/')
                historial = HistorialJustificaInforme(informe=informe,
                                                        descripcion=request.POST['descripcion'],
                                                        archivo=newfile,
                                                        fecha=datetime.now().date(),
                                                        persona=persona)
                historial.save(request)
                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'firmarinformemasivo':
            try:
                import json
                informesselect = request.POST['ids'].split(',')
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                for idinforme in informesselect:
                    historial = HistorialInforme.objects.get(pk=idinforme)
                    pdf = historial.informe.archivo
                    # obtener la posicion xy de la firma del doctor en el pdf
                    pdfname = SITE_STORAGE + '/media/' + str(historial.informe.archivo)
                    if HistorialInforme.objects.values('id').filter(informe=historial.informe, personafirmas=persona, status=True).count()>1:
                        # tipofirma = 'REVISADO'
                        # persona.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, coordinacion=historial.informe.distributivo.coordinacion, status=True).exists():
                        #     tipofirma = 'APROBADO'
                        palabras = u"%s %s" % (persona, historial.get_estado_display().upper())
                    else:
                        palabras = u"%s" % persona

                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                    x = x + 5
                    y= y + 20
                    datau = JavaFirmaEc(
                        archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(numpaginafirma), reason='', lx=x, ly=y
                    ).sign_and_get_content_bytes()
                    pdf = io.BytesIO()
                    pdf.write(datau)
                    pdf.seek(0)
                    _name = generar_nombre(f'{historial.informe.distributivo.profesor}_{nombremes(historial.informe.fechafin.month).upper()}_{historial.informe.fechafin.year}_', 'firmada')
                    file_obj = DjangoFile(pdf, name=f"{remover_caracteres_especiales_unicode(_name)}.pdf")

                    historial.archivo = file_obj
                    historial.fechafirma = datetime.now().date()
                    historial.firmado = True
                    historial.save(request)

                    historial.informe.estado = historial.estado
                    historial.informe.archivo = historial.archivo
                    historial.informe.save(request)
                    if persona.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, coordinacion_id__in=[1, 2, 3, 4, 5], status=True).exists():
                        noti = Notificacion(cuerpo='Su informe mensual de cumplimiento correspondiente al mes de ' + str(nombremes(historial.informe.fechafin)) + ' del año ' + str(historial.informe.fechafin.year) + ', ha sido legalizado.',
                                            titulo='¡Tiene un nuevo informe mensual de cumplimiento aprobado¡',
                                            destinatario=historial.informe.distributivo.profesor.persona,
                                            url='/media/' + str(historial.archivo),
                                            prioridad=2, app_label='SGA',
                                            fecha_hora_visible=datetime.now(), tipo=3,
                                            en_proceso=False)
                        noti.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                eline = 'Error on line {} {}'.format(sys.exc_info()[-1].tb_lineno, ex.__str__())
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % eline})

        if action == 'removefinalizar':
            try:
                actividad = ClaseActividad.objects.filter(finalizado=True, detalledistributivo__distributivo__periodo_id=request.POST['idperiodo'], detalledistributivo__distributivo__profesor_id=request.POST['idprofesor'])
                distributivo = ProfesorDistributivoHoras.objects.filter(status=True,  profesor_id=request.POST['idprofesor'], periodo=periodo).first()
                if not actividad:
                    if not  distributivo.horariofinalizado:
                        raise NameError('Lo sentimos este docente no tiene finalizado su horario')
                if ClaseActividadEstado.objects.filter(periodo_id=request.POST['idperiodo'], profesor_id=request.POST['idprofesor'], estadosolicitud=2, status=True).exists():
                    raise NameError('Lo sentimos el horario de actividades de este docente ya se encuetra aprobado')
                actividad.update(finalizado=False)
                distributivo.horariofinalizado = False
                distributivo.save(request, update_fields=['horariofinalizado'])
                # ordenar_marcada(request.session['periodo'], id, nomdia, profesor)
                log(u'Permitió edición del horario de actividades del docente: {}'.format(distributivo.profesor.persona.nombre_completo_minus()), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": str(ex)})

        if action == 'addterminoscondiciones':
            try:
                f = TerminosCondicionesForm(request.POST)
                if not f.is_valid():
                    return JsonResponse({'result': False, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})

                terms = TerminosCondiciones(titulo=f.cleaned_data.get('titulo'), detalle=f.cleaned_data.get('detalle'), periodo=periodo, visible=f.cleaned_data.get('visible'), legalizar=f.cleaned_data.get('legalizar'))
                terms.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': ex.__str__()})

        if action == 'editterminoscondiciones':
            try:

                terms = TerminosCondiciones.objects.get(id=request.POST['id'])
                f = TerminosCondicionesForm(request.POST)
                if not f.is_valid():
                    return JsonResponse({'result': False, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})

                terms.titulo = f.cleaned_data.get('titulo')
                terms.detalle = f.cleaned_data.get('detalle')
                terms.visible = f.cleaned_data.get('visible')
                terms.legalizar = f.cleaned_data.get('legalizar')
                # terms.periodo = periodo

                terms.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': ex.__str__()})

        if action == 'delterminoscondiciones':
            try:
                terms = TerminosCondiciones.objects.get(id=request.POST['id'])
                terms.status = False
                terms.save(request)

                log(u"%s eliminó termino y condicion." % persona, request, "del")
                return JsonResponse({'result': 'ok', 'error': False})
            except Exception as ex:
                return JsonResponse({'result': False, 'mensaje': ex.__str__()})

        if action == 'justificarclasetutoria':
            try:
                registro = RegistroClaseTutoriaDocente.objects.get(id=request.POST.get('id'))
                estado, registro.justificada = 3, not registro.justificada

                if registro.justificada:
                    estado, registro.fechajustificacion = 2, datetime.now()

                registro.estadojustificacion = estado
                registro.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'gestionarsolicitud':
            try:
                form = GestionarAperturaClaseVirtualForm(request.POST)
                if form.is_valid():
                    data['solicitud'] = solicitud = SolicitudAperturaClaseVirtual.objects.filter(status=True, id=int(encrypt(request.POST['id']))).first()
                    if not solicitud:
                        raise NameError('Solicitud no encontrada')
                    if not form.cleaned_data['todoperiodo'] and  not form.cleaned_data['fechainicio'] < form.cleaned_data['fechafin']:
                        raise NameError('Debe ingresar la fecha fin mayor a la fecha inicial')
                    solicitud.estadosolicitud = form.cleaned_data['estadosolicitud']
                    solicitud.totalperiodo = form.cleaned_data['todoperiodo']
                    solicitud.fechainicio = form.cleaned_data['fechainicio'] if not form.cleaned_data['todoperiodo'] else periodo.inicio
                    solicitud.fechafin = form.cleaned_data['fechafin'] if not form.cleaned_data['todoperiodo'] else periodo.fin
                    solicitud.estadosolicitud = form.cleaned_data['estadosolicitud']
                    solicitud.fechaaprobacion = datetime.now().date()
                    solicitud.aprobador = persona
                    solicitud.descripcionaprobador = form.cleaned_data['descripcionaprobador']
                    solicitud.save(request, update_fields=['totalperiodo','estadosolicitud', 'descripcionaprobador', 'fechaaprobacion', 'aprobador', 'fechafin', 'fechainicio'])
                    log('Gestionó solicitud de apertura de clase virtual: {} - {}'.format(
                        solicitud.profesor.persona.nombre_completo_minus(), solicitud.periodo), request, "edit")
                    notificacion('Solicitud de apertura de clases',
                                 'Estimado docente: {} su solicitud de apertura de clases virtuales fue {}'.format(
                                     solicitud.profesor.persona.nombre_completo_minus(), solicitud.get_estadosolicitud_display()), solicitud.profesor.persona,
                                 None, '/pro_cronograma', solicitud.profesor.persona_id, 2, 'sga', solicitud, request)
                    return JsonResponse({'result': False})
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        if action == 'deletesolicitud':
            try:
                solicitud = SolicitudAperturaClaseVirtual.objects.filter(status=True, id=int(encrypt(request.POST['id']))).first()
                if not solicitud:
                    raise NameError('Solicitud no encontrada')
                solicitud.status = False
                solicitud.save(request, update_fields=['status'])
                log('Eliminó solicitud de apertura de clases virtuales: {}'.format(solicitud.profesor.persona.nombre_completo_minus()), request, "delete")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "{}".format(ex)})

        if action == 'totalactividadesdocentesmaterias_nuevo':
            try:
                data = {"periodo_id": periodo.id}
                eNotificacion = Notificacion(cuerpo="Generación de reporte de excel en progreso",
                                             titulo=f"Reporte actividad docente tercer y cuarto nivel",
                                             destinatario=persona, url="", prioridad=1, app_label="SGA",
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2, en_proceso=True)
                eNotificacion.save(request)
                reporte_criterios_actividades_formacion_docente_background(request=request, data=data,
                                                                           notiid=eNotificacion.id,
                                                                           periodo=periodo.id).start()
                return JsonResponse({"result": True,
                                     "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                     "btn_notificaciones": traerNotificaciones(request, data, persona)})
            except Exception as ex:
                return JsonResponse({"result": False, "mensaje": f"Error al generar el reporte {ex}"})

        if action == 'titulosacaademicosdocentes':
            try:
                data = {"periodo_id": periodo.id}
                eNotificacion = Notificacion(cuerpo="Generación de reporte de excel en progreso",
                                             titulo=f"Reporte de Docentes con Registro de Títulos Académicos",
                                             destinatario=persona, url="", prioridad=1, app_label="SGA",
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2, en_proceso=True)
                eNotificacion.save(request)
                reporte_titulos_academicos_docente_background(request=request, data=data,
                                                                           notiid=eNotificacion.id,
                                                                           periodo=periodo.id).start()
                return JsonResponse({"result": True,
                                     "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                     "btn_notificaciones": traerNotificaciones(request, data, persona)})
            except Exception as ex:
                return JsonResponse({"result": False, "mensaje": f"Error al generar el reporte {ex}"})

        if action == 'nuevoreporte': #reporte_totalactividadesdocentesmaterias
            try:
                data = {"periodo_id": periodo.id}
                eNotificacion = Notificacion(cuerpo="Generación de reporte de excel en progreso",
                                             titulo=f"Reporte Criterios, actividades, horas, asignaturas, formación de los docentes",
                                             destinatario=persona, url="", prioridad=1, app_label="SGA",
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2, en_proceso=True)
                eNotificacion.save(request)
                reporte_criterios_nuevo(request=request, data=data,
                                                                           notiid=eNotificacion.id,
                                                                           periodo=periodo.id).start()
                return JsonResponse({"result": True,
                                     "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                     "btn_notificaciones": traerNotificaciones(request, data, persona)})
            except Exception as ex:
                return JsonResponse({"result": False, "mensaje": f"Error al generar el reporte {ex}"})

        if action == 'del-subactividaddistributivo':
            try:
                subactividad = SubactividadDetalleDistributivo.objects.get(id=request.POST['id'])
                subactividad.delete()
                log(f'Elimino registro de subactividad: {subactividad} - {subactividad.actividaddetalledistributivo.criterio.distributivo.profesor.persona}', request, "del")
                return JsonResponse({'error': False})
            except Exception as ex:
                return JsonResponse({'message': ex.__str__()})

        if action == 'add-subactividad':
            try:
                f = SubactividadDetalleDistributivoForm(request.POST)
                if len(f.fields['subactividaddocenteperiodo'].choices):
                    del f.fields['subactividaddocenteperiodo']

                actividad = ActividadDetalleDistributivo.objects.get(id=request.POST['id'])
                filtro = Q(actividad__criterio__status=True, criterio__status=True, status=True)

                if doc := actividad.criterio.criteriodocenciaperiodo:
                    filtro &= Q(actividad__criteriodocenciaperiodo=doc)

                if inv := actividad.criterio.criterioinvestigacionperiodo:
                    filtro &= Q(actividad__criterioinvestigacionperiodo=inv)

                if f.is_valid():
                    subactividaddocenteperiodo = request.POST['subactividaddocenteperiodo']
                    if subactividaddocenteperiodo == '*':
                        for subactividad in SubactividadDocentePeriodo.objects.filter(filtro):
                            if subactivity := SubactividadDetalleDistributivo.objects.filter(subactividaddocenteperiodo=subactividad, actividaddetalledistributivo=actividad, status=True).first():
                                subactivity.fechainicio = f.cleaned_data['fechainicio']
                                subactivity.fechafin = f.cleaned_data['fechafin']
                            else:
                                subactivity = SubactividadDetalleDistributivo(fechafin=f.cleaned_data['fechafin'], fechainicio=f.cleaned_data['fechainicio'], actividaddetalledistributivo=actividad, subactividaddocenteperiodo=subactividad)

                            subactivity.save(request)
                    else:
                        subactividad = SubactividadDetalleDistributivo(fechafin=f.cleaned_data['fechafin'], fechainicio=f.cleaned_data['fechainicio'], actividaddetalledistributivo=actividad, subactividaddocenteperiodo_id=subactividaddocenteperiodo)
                        subactividad.save(request)
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({'result': 'bad', "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        if action == 'edit-subactividad':
            try:
                f = SubactividadDetalleDistributivoForm(request.POST)
                f.ocultar_campo('subactividaddocenteperiodo')
                subactividad = SubactividadDetalleDistributivo.objects.get(id=request.POST['id'])
                if f.is_valid():
                    subactividad.fechafin = f.cleaned_data['fechafin']
                    subactividad.fechainicio = f.cleaned_data['fechainicio']
                    subactividad.save(request)
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({'result': 'bad', "form": [{k: v[0]} for k, v in f.errors.items()]})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        elif action == 'generainformefirmar':
            try:
                n_infor_g=0;
                n_infor_v=0;
                mes_actual = datetime.now()
                es_decano = ResponsableCoordinacion.objects.filter(persona=persona, periodo=periodo, tipo=1, status=True).exclude(coordinacion=9)
                contador = es_decano.count()
                carrerasin = None
                if contador > 1:
                    carrerasin = es_decano[0].coordinacion.carrera.filter(status=True)
                    for i in range(1, contador):
                        carrerasin = carrerasin.union(
                            es_decano[i].coordinacion.carrera.filter(status=True))
                else:
                    carrerasin = es_decano[0].coordinacion.carrera.filter(status=True)
                carrerasin_lista = list(carrerasin)
                mallacarrerasdecano = Malla.objects.filter(status=True, carrera__in=carrerasin_lista)
                carreras = []
                for carr in mallacarrerasdecano:
                    if carr.uso_en_periodo(periodo):
                        carreras.append(carr.carrera.id)
                idmeses = request.POST['idmes']
                idanio = request.POST['idanio']
                peri = request.POST['anual']
                data['facultad']=es_decano[0].coordinacion
                # carreras = es_decano.coordinacion.carrera.all()
                idsdocentesexcluir = excluir_docentes_inicio_fin_actividad(idanio, idmeses, periodo)
                datos_coordinadores = []
                for carrera in carreras:
                    if carr := Carrera.objects.filter(status=True,pk=carrera).first():
                        directorcarrera = carr.get_director(periodo)
                        if directorcarrera:
                            if peri == 'periodo':
                                informes = HistorialInforme.objects.filter(
                                    informe__distributivo__periodo=periodo,
                                    personafirmas=directorcarrera.persona,
                                    firmado=True,
                                    status=True
                                ).filter(Q(informe__fechafin__month__lte=mes_actual.month)).exclude(informe__distributivo__profesor__id__in=idsdocentesexcluir)
                            else:
                                informes = HistorialInforme.objects.filter(
                                    informe__distributivo__periodo=periodo,
                                    personafirmas=directorcarrera.persona,
                                    informe__fechafin__month=int(idmeses),  # Cambié __in='3' a __month='3'
                                    firmado=True,
                                    status=True
                                ).exclude(informe__distributivo__profesor__id__in=idsdocentesexcluir)

                            total_promedio = round(informes.aggregate(total_avg=Avg('informe__promedio'))['total_avg'],2)
                            cantidad_informes_estado = informes.exclude(estado=1).count()
                            if cantidad_informes_estado > 0:
                                validacion = int((cantidad_informes_estado/informes.count()) * 100)
                            else:
                                validacion = 0
                            n_infor_g += informes.count();
                            n_infor_v += cantidad_informes_estado;
                            datos_coordinadores.append({
                                'carrera': carr.nombre,
                                'director_carrera': directorcarrera.persona,
                                'total_informe':informes.count(),
                                'informes_estado': cantidad_informes_estado,
                                'validacion': validacion,
                                'promedio': total_promedio
                            })
                mes = int(idmeses) if idmeses else None
                anio = int(idanio) if idanio else None
                if mes and anio:
                    fecha_inicio = datetime(anio, mes, 1)
                    if mes == 12:
                        fecha_fin = datetime(anio + 1, 1, 1) - timedelta(days=1)
                    else:
                        fecha_fin = datetime(anio, mes + 1, 1) - timedelta(days=1)
                if peri == 'periodo':
                    fecha_fin = min(mes_actual.date(), periodo.fin)
                    fecha_inicio = periodo.inicio

                sum_validacion_total = sum(item['validacion'] for item in datos_coordinadores)
                promedios_validos = [item['promedio'] for item in datos_coordinadores if item['promedio'] is not None]
                sum_promedio_total = sum(float(promedio) for promedio in promedios_validos)
                count = len(datos_coordinadores)
                average_validacion_total = sum_validacion_total / count if count > 0 else 0
                average_promedio_total = sum_promedio_total / count if count > 0 else 0
                data['avge_validacion'] = round(average_validacion_total,2)
                data['avg_promedio'] = round(average_promedio_total,2)
                data['decano'] = es_decano.first().persona
                data['listadoinformes'] = datos_coordinadores
                data['periodo'] = periodo.nombre
                data['inicio'] = fecha_inicio
                data['fin'] = fecha_fin
                data['infge']=n_infor_g
                data['infva'] = n_infor_v
                data['fecha'] = datetime.now()

                return conviert_html_to_pdf_name(
                    'adm_criteriosactividadesdocente/reportevalidacioninformes.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    },f"INFORME ACTIVIDADES"
                )
            except Exception as ex:
                pass

    else:
        data['title'] = u'Criterios de actividades academicas'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            s = None
            idc = None
            if 's' in request.GET:
                request.session['search_criterio'] = s = request.GET['s']
            elif 'search_criterio' in request.session:
                s = request.session['search_criterio'] if request.session['search_criterio'] else None
            if 'idc' in request.GET:
                request.session['idc_criterio'] = idc = request.GET['idc']
            elif 'idc_criterio' in request.session:
                idc = request.session['idc_criterio'] if request.session['idc_criterio'] else None
            data['search'] = s
            data['idc'] = idc

            if action == 'add-subactividad':
                try:
                    f = SubactividadDetalleDistributivoForm()
                    actividad = ActividadDetalleDistributivo.objects.get(id=request.GET['id'])
                    f.fields['fechafin'].initial = actividad.hasta
                    f.fields['fechainicio'].initial = actividad.desde
                    filtro = Q(actividad__criterio__status=True, criterio__status=True, status=True)
                    if doc := actividad.criterio.criteriodocenciaperiodo:
                        filtro &= Q(actividad__criteriodocenciaperiodo=doc)
                    if inv := actividad.criterio.criterioinvestigacionperiodo:
                        filtro &= Q(actividad__criterioinvestigacionperiodo=inv)
                    exclude = actividad.subactividaddetalledistributivo_set.filter(status=True).values_list('subactividaddocenteperiodo', flat=True)
                    f.fields['subactividaddocenteperiodo'].queryset = SubactividadDocentePeriodo.objects.filter(filtro).exclude(id__in=exclude).order_by('criterio__nombre')
                    if len(f.fields['subactividaddocenteperiodo'].choices):
                        f.fields['subactividaddocenteperiodo'].choices = list(f.fields['subactividaddocenteperiodo'].choices)
                        f.fields['subactividaddocenteperiodo'].choices[0] = ('*', '--Agregar todas--')
                    data['id'] = actividad.pk
                    data['form2'] = f
                    template = get_template("proyectovinculaciondocente/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'html': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'replicar-fecha-actividad':
                try:
                    actividad = ActividadDetalleDistributivo.objects.get(id=request.GET['id'])
                    for subactividad in actividad.subactividaddetalledistributivo_set.filter(status=True):
                        subactividad.fechainicio, subactividad.fechafin = actividad.desde, actividad.hasta
                        subactividad.save(request)

                    return JsonResponse({'reload': True})
                except Exception as ex:
                    return JsonResponse({"result": 'bad', 'mensaje': f'{ex}'})

            if action == 'edit-subactividad':
                try:
                    subactividad = SubactividadDetalleDistributivo.objects.get(id=request.GET['id'])
                    f = SubactividadDetalleDistributivoForm(initial=model_to_dict(subactividad))
                    f.ocultar_campo('subactividaddocenteperiodo')
                    data['form2'] = f
                    data['id'] = subactividad.pk
                    template = get_template("proyectovinculaciondocente/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'html': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'reportehoraseingresos':
                try:
                    __author__ = 'Unemi'

                    periodo = request.GET['periodo']
                    periodo_nombre = request.GET['periodo_nombre']

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    url = "https://sga.unemi.edu.ec/static/images/LOGO-UNEMI-2020.png"
                    image_data = io.BytesIO(urllib.request.urlopen(url).read())
                    ws = workbook.add_worksheet('horas_ingresos_tutorias')
                    ws.set_column(0, 10, 30)
                    # ws.insert_image('A1', url, {'image_data': image_data}, {''})
                    formatotitulo = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'valign': 'middle',
                         'fg_color': '#A2D0EC'})
                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.merge_range('A1:D1', 'REPORTE DE ASIGNACIÓN DE HORAS E INGRESO A TUTORÍAS', formatotitulo)
                    ws.merge_range('E1:F1', 'PERIODO', formatoceldacab)
                    ws.merge_range('G1:I1', str(periodo_nombre), formatoceldaleft)

                    ws.write(1, 0, 'IDENTIFICACIÓN', formatoceldacab)
                    ws.write(1, 1, 'DOCENTE', formatoceldacab)
                    ws.write(1, 2, 'CARRERA', formatoceldacab)
                    ws.write(1, 3, 'TIPO', formatoceldacab)
                    ws.write(1, 4, 'CATEGORÍA', formatoceldacab)
                    ws.write(1, 5, 'DEDICACIÓN', formatoceldacab)
                    ws.write(1, 6, 'CRITERIO', formatoceldacab)
                    ws.write(1, 7, 'HORAS', formatoceldacab)
                    ws.write(1, 8, 'HORAS REGISTRADAS', formatoceldacab)

                    detalledis = DetalleDistributivo.objects.filter(status=True,
                                                                    criteriodocenciaperiodo__criterio__tipocriterioactividad=3,
                                                                    distributivo__periodo=periodo).values_list('id', flat=True)
                    actividades = ActividadDetalleDistributivo.objects.filter(status=True, criterio__in=detalledis).order_by('criterio__distributivo__profesor')

                    # print(actividad.criterio.distributivo.profesor.persona.cedula,
                    #       ' - ', actividad.criterio.distributivo.profesor,
                    #       ' - ', actividad.criterio.distributivo.carrera,
                    #       ' - ', actividad.criterio.distributivo.nivelcategoria,
                    #       ' - ', actividad.criterio.distributivo.categoria,
                    #       ' - ', actividad.criterio.distributivo.dedicacion,
                    #       ' - ', actividad.criterio.criteriodocenciaperiodo.criterio,
                    #       ' - ', actividad.horas,
                    #       ' - ', horas)

                    fila_det = 3

                    for actividad in actividades:
                        horarios = HorarioTutoriaAcademica.objects.filter(status=True,
                                                                          profesor=actividad.criterio.distributivo.profesor,
                                                                          periodo=periodo)
                        horas = 0
                        if horarios.exists():
                            horas = int(horarios.aggregate(total=Sum('turno__horas'))['total'])

                        ws.write('A%s' % fila_det, str(actividad.criterio.distributivo.profesor.persona.cedula if actividad.criterio.distributivo.profesor.persona.cedula else actividad.criterio.distributivo.profesor.persona.pasaporte), formatoceldaleft)
                        ws.write('B%s' % fila_det, str(actividad.criterio.distributivo.profesor if actividad.criterio.distributivo.profesor else 'NO EXISTE REGISTRO'), formatoceldaleft)
                        ws.write('C%s' % fila_det, str(actividad.criterio.distributivo.carrera if actividad.criterio.distributivo.carrera else 'NO EXISTE REGISTRO'), formatoceldaleft)
                        ws.write('D%s' % fila_det, str(actividad.criterio.distributivo.nivelcategoria if actividad.criterio.distributivo.nivelcategoria else 'NO EXISTE REGISTRO'), formatoceldaleft)
                        ws.write('E%s' % fila_det, str(actividad.criterio.distributivo.categoria if actividad.criterio.distributivo.categoria else 'NO EXISTE REGISTRO'), formatoceldaleft)
                        ws.write('F%s' % fila_det, str(actividad.criterio.distributivo.dedicacion if actividad.criterio.distributivo.dedicacion else 'NO EXISTE REGISTRO'), formatoceldaleft)
                        ws.write('G%s' % fila_det, str(actividad.criterio.criteriodocenciaperiodo.criterio if actividad.criterio.criteriodocenciaperiodo.criterio else 'NO EXISTE REGISTRO'), formatoceldaleft)
                        ws.write('H%s' % fila_det, round(actividad.horas if actividad.horas else 'NO EXISTE REGISTRO'), formatoceldaleft)
                        ws.write('I%s' % fila_det, horas, formatoceldaleft)
                        fila_det += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte de asignacion de horas e ingresos de tutorías académicas.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            if action == 'delhorario':
                try:
                    data['idprofesor'] = request.GET['idprofesor']
                    data['title'] = u'Eliminar horario'
                    data['horario'] = HorarioTutoriaAcademica.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['max'] = 1 if 'max' in request.GET and request.GET['max'] == '1' else 0
                    data['iddistri'] = request.GET.get('iddistri', '')
                    return render(request, "adm_criteriosactividadesdocente/delhorario.html", data)
                except Exception as ex:
                    pass

            if action == 'get_materia_date':
                try:
                    pm = ProfesorMateria.objects.get(pk=request.GET['pk'])
                    return JsonResponse({'result': 'ok', 'fi': pm.materia.inicio, 'ff': pm.materia.fin})
                except Exception as ex:
                    pass

            elif action == 'cargar_facultad':
                try:
                    lista = []
                    facultades = Coordinacion.objects.filter(status=True).distinct()

                    for facultad in facultades:
                        if not buscar_dicc(lista, 'id', facultad.id):
                            lista.append({'id': facultad.id, 'nombre': facultad.nombre})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_carrera':
                try:
                    lista = []
                    carreras = Carrera.objects.filter(status=True, coordinacion=request.GET['id']).distinct()

                    for carrera in carreras:
                        if not buscar_dicc(lista, 'id', carrera.id):
                            lista.append({'id': carrera.id, 'nombre': carrera.nombre})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_periodo':
                try:
                    lista = []
                    periodos = Periodo.objects.filter(status=True, activo=True).order_by('tipo')

                    for periodo in periodos:
                        if not buscar_dicc(lista, 'id', periodo.id):
                            lista.append({'id': periodo.id, 'tipo': periodo.tipo.nombre, 'nombre': periodo.nombre})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'criterios':
                try:
                    data['title'] = u'Criterios de actividades del docente'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = distributivo = ProfesorDistributivoHoras.objects.get(pk=request.GET['iddistri'])
                    data['c1'] = CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID
                    data['c2'] = CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID
                    data['c3'] = CRITERIO_HORAS_CLASE_PRACTICA
                    data['c4'] = CRITERIO_HORAS_CLASE_AYUDANTIA

                    if periodo.id < 113:
                        data['arregloc'] = [CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PRACTICA, CRITERIO_HORAS_CLASE_AYUDANTIA, 27, variable_valor('CRITERIO_IMPARTICION_CLASE_ID'), 7]
                    else:
                        data['arregloc'] = [CRITERIO_HORAS_CLASE_TIEMPO_COMPLETO_ID, CRITERIO_HORAS_CLASE_MEDIO_TIEMPO_ID, CRITERIO_HORAS_CLASE_PRACTICA,  27]
                    data['t'] = None
                    if 't' in request.GET:
                        data['t'] = int(request.GET['t'])
                    actualiza_vigencia_criterios_docente(distributivo)
                    return render(request, "adm_criteriosactividadesdocente/criterios.html", data)
                except Exception as ex:
                    msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
                    return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=SysError: %s" % msg_ex)

            elif action == 'actividadrecurso':
                try:
                    data['tipo'] = tipo = request.GET['tipo']
                    data['idprofesor'] = request.GET['idprofesor']
                    data['valor'] = request.GET['valor']
                    detalle = DetalleDistributivo.objects.get(pk=int(request.GET['id']))
                    data['distributivo1'] = False
                    if tipo == '1':
                        data['criterio'] = criterio = detalle.criteriodocenciaperiodo
                        data['recursos'] = recursos = RecursoAprendizaje.objects.filter(status=True, recursoaprendizajetipoprofesor__actividaddocenciarecursoaprendizaje__criterio=criterio, recursoaprendizajetipoprofesor__status=True).distinct()
                        if recursos:
                            data['distributivo1'] = ActividadDocenciaRecursoAprendizaje.objects.filter(recurso__recursoaprendizaje=recursos[0], status=True)[0].distributivo
                    if tipo == '2':
                        data['criterio'] = criterio = detalle.criterioinvestigacionperiodo
                        data['recursos'] = recursos = RecursoAprendizaje.objects.filter(status=True, recursoaprendizajetipoprofesor__actividadinvestigacionrecursoaprendizaje__criterio=criterio, recursoaprendizajetipoprofesor__status=True).distinct()
                        if recursos:
                            data['distributivo1'] = ActividadInvestigacionRecursoAprendizaje.objects.filter(recurso__recursoaprendizaje=recursos[0], status=True)[0].distributivo
                    if tipo == '3':
                        data['criterio'] = criterio = detalle.criteriogestionperiodo
                        data['recursos'] = recursos = RecursoAprendizaje.objects.filter(status=True, recursoaprendizajetipoprofesor__actividadgestionrecursoaprendizaje__criterio=criterio, recursoaprendizajetipoprofesor__status=True).distinct()
                        if recursos:
                            data['distributivo1'] = ActividadGestionRecursoAprendizaje.objects.filter(recurso__recursoaprendizaje=recursos[0], status=True)[0].distributivo
                    data['periodo'] = periodo
                    profesorsele = detalle.distributivo.profesor
                    data['asignaturas_presencial'] = Asignatura.objects.filter(asignaturamalla__materia__nivel__periodo=periodo, asignaturamalla__materia__nivel__modalidad_id__in=[1, 2], asignaturamalla__materia__profesormateria__profesor=profesorsele).distinct()
                    data['asignaturas_enlinea'] = Asignatura.objects.filter(asignaturamalla__materia__nivel__periodo=periodo, asignaturamalla__materia__nivel__modalidad_id__in=[3], asignaturamalla__materia__profesormateria__profesor=profesorsele).distinct()
                    data['tiposprofesorpresencial'] = TipoProfesor.objects.filter(profesormateria__materia__nivel__modalidad_id__in=[1, 2], profesormateria__profesor=profesorsele, status=True, profesormateria__status=True, profesormateria__materia__nivel__periodo=periodo).distinct()
                    data['tiposprofesorlinea'] = TipoProfesor.objects.filter(profesormateria__materia__nivel__modalidad_id__in=[3], profesormateria__profesor=profesorsele, status=True, profesormateria__status=True, profesormateria__materia__nivel__periodo=periodo).distinct()
                    data['id'] = request.GET['id']
                    data['modalidadpresencial'] = [1, 2]
                    data['modalidadlinea'] = [3]
                    return render(request, "adm_criteriosactividadesdocente/actividadrecurso.html", data)
                except Exception as ex:
                    pass

            elif action == 'confighorarioprof':
                try:
                    data['title'] = u'Horarios de las Actividades del Profesor'
                    data['idprof'] = idprof = int(encrypt(request.GET['idprof']))
                    data['idper'] = int(encrypt(request.GET['idper']))
                    # data['idc'] =  request.GET['idc']
                    data['profesor'] = profesor = Profesor.objects.get(pk=idprof)
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    hoy = datetime.now().date()
                    data['mostrar'] = 0
                    estadoactividad = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True)
                    data['ver'] = False
                    if estadoactividad.exists():
                        data['mostrar'] = 1
                        data['detalleestados'] = estadoactividad
                        data['estadoactividad'] = claseactividadestado = estadoactividad.order_by('-id').first()
                        # claseactividadestado = estadoactividad.order_by('-id')
                        data['ver'] = claseactividadestado.estadosolicitud == 2
                        # if claseactividadestado:
                        #     if claseactividadestado[0].estadosolicitud == 2:
                        #         data['ver'] = True
                        #     else:
                        #         data['ver'] = False

                    # data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(profesor=profesor, hasta__gt=hoy, activo=True, principal=True).exclude(materia__clase__id__isnull=False)
                    data['misclases'] = clases = Clase.objects.filter(materia__nivel__periodo__visible=True, activo=True,
                                                                      fin__gte=hoy,
                                                                      materia__profesormateria__profesor=profesor,
                                                                      materia__profesormateria__principal=True).order_by('inicio')
                    data['sesiones'] = Sesion.objects.filter(pk__in=[1, 4, 5, 7, 13], status=True).distinct()
                    # data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
                    data['periodo'] = request.session['periodo']
                    if not request.session['periodo'].visible:
                        return HttpResponseRedirect("/?info=Periodo Inactivo.")
                    return render(request, "adm_criteriosactividadesdocente/horarios_actividades.html", data)
                except Exception as ex:
                    print(ex)

            elif action == 'listactividades':
                try:
                    data['idprof'] = idprof = request.GET['idprof']
                    data['profesor'] = profesor = Profesor.objects.get(pk=idprof)
                    actidocencia = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                      distributivo__periodo=periodo,
                                                                      criteriodocenciaperiodo_id__isnull=False).exclude(criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '19', '30'])
                    actiinvestigacion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                           distributivo__periodo=periodo,
                                                                           criterioinvestigacionperiodo_id__isnull=False)
                    actigestion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                     distributivo__periodo=periodo,
                                                                     criteriogestionperiodo_id__isnull=False)
                    data['actividades'] = actidocencia | actiinvestigacion | actigestion
                    return render(request, "adm_criteriosactividadesdocente/actividadesdocentes.html", data)
                except Exception as ex:
                    pass

            elif action == 'formaciondocentesactivos':
                try:
                    periodo = request.GET['periodo']
                    cursor = connections['default'].cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_docentes activos.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 1000
                    ws.col(1).width = 3000
                    ws.col(2).width = 10000
                    ws.col(3).width = 5000
                    ws.col(4).width = 4000
                    ws.col(5).width = 10000
                    ws.col(6).width = 4000
                    ws.col(7).width = 10000
                    ws.col(8).width = 10000
                    ws.col(9).width = 6000
                    ws.write(4, 0, 'N.')
                    ws.write(4, 1, 'CEDULA')
                    ws.write(4, 2, 'NOMBRES')
                    ws.write(4, 3, 'SEXO')
                    ws.write(4, 4, 'FECHATITULO')
                    ws.write(4, 5, 'TITULO')
                    ws.write(4, 6, 'NIVEL')
                    ws.write(4, 7, 'GRADOTITULO')
                    ws.write(4, 8, 'INSTITUCION')
                    ws.write(4, 9, 'VERIFICADO')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listadocentes = "select distinct p.cedula,p.apellido1,p.apellido2,p.nombres," \
                                    "ti.fechaobtencion,tit.nombre as titulo,nti.nombre as nivel," \
                                    "gti.nombre as gradotitulo, sup.nombre as institucion,ti.verificado,sex.nombre as sexo " \
                                    "from sga_profesordistributivohoras dis " \
                                    "left join sga_profesor pro on pro.id=dis.profesor_id " \
                                    "left join  sga_persona p on p.id=pro.persona_id " \
                                    "left join sga_sexo sex on p.sexo_id=sex.id " \
                                    "left join sga_titulacion ti on ti.persona_id=p.id " \
                                    "left join sga_titulo tit on tit.id=ti.titulo_id " \
                                    "left join sga_niveltitulacion nti on nti.id=tit.nivel_id " \
                                    "left join sga_gradotitulacion gti on gti.id=tit.grado_id " \
                                    "left join sga_institucioneducacionsuperior sup on sup.id = ti.institucion_id " \
                                    "where p.cedula IS NOT NULL " \
                                    "and dis.periodo_id='" + periodo.id + "' " \
                                                                          "and dis.status=True " \
                                                                          "order by p.apellido1,p.apellido2,p.nombres"
                    cursor.execute(listadocentes)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, a - 4)
                        ws.write(a, 1, per[0])
                        ws.write(a, 2, per[1] + ' ' + per[2] + ' ' + per[3])
                        ws.write(a, 3, per[10])
                        ws.write(a, 4, per[4], date_format)
                        ws.write(a, 5, per[5])
                        ws.write(a, 6, per[6])
                        ws.write(a, 7, per[7])
                        ws.write(a, 8, per[8])
                        ws.write(a, 9, per[9])
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'criteriosdocencia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Adicionar criterios de actividades de docencia'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = distributivo = ProfesorDistributivoHoras.objects.get(pk=request.GET['iddistri'])
                    data['horas_asignadas_docencia'] = distributivo.horasdocencia
                    # data['criterios'] = CriterioDocenciaPeriodo.objects.filter(Q(criterio__dedicacion=distributivo.dedicacion) | Q(criterio__dedicacion__isnull=True), periodo=periodo, maximo__gt=0)
                    if periodo.clasificacion == 2:
                        data['criterios'] = CriterioDocenciaPeriodo.objects.filter(criterio__posgrado=True, periodo=periodo, status=True)
                    else:
                        data['criterios'] = CriterioDocenciaPeriodo.objects.filter(Q(criterio__dedicacion=distributivo.dedicacion) | Q(criterio__dedicacion__isnull=True), periodo=periodo, maximo__gt=0, status=True)
                    return render(request, "adm_criteriosactividadesdocente/criteriosdocencia.html", data)
                except Exception as ex:
                    pass

            if action == 'horarioactividades':
                try:
                    persona = request.session['persona']
                    data['periodolectivo'] = request.session['periodo']
                    periodo = request.session['periodo']
                    coordinaciones = persona.mis_coordinaciones()
                    carreras = persona.mis_carreras()
                    data['distributivodocente'] = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=coordinaciones, carrera__id__in=carreras, periodo=periodo)
                    return render(request, "adm_criteriosactividadesdocente/horarioactividades.html", data)
                except Exception as ex:
                    pass

            if action == 'planificarhoras':
                try:
                    search = None
                    persona = request.session['persona']
                    data['listadoperiodos'] = Periodo.objects.filter(tipo_id=2, status=True).order_by('-id')[:10]
                    data['periodolectivo'] = periodolectivo = request.session['periodo']
                    ids = None
                    idc = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 2:
                            profesores = periodolectivo.profesorconfigurarhoras_set.filter(periodo=periodo).filter(
                                Q(profesor__persona__apellido1__icontains=ss[0]) &
                                Q(profesor__persona__apellido2__icontains=ss[1])).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()

                        else:
                            profesores = periodolectivo.profesorconfigurarhoras_set.filter(periodo=periodo).filter(
                                Q(profesor__persona__nombres__icontains=search) |
                                Q(profesor__persona__apellido1__icontains=search) |
                                Q(profesor__persona__apellido2__icontains=search) |
                                Q(profesor__persona__cedula__icontains=search)).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                    else:
                        profesores = periodolectivo.profesorconfigurarhoras_set.filter(status=True).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                    numerofilas = 25
                    paging = MiPaginador(profesores, numerofilas)
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
                    data['listadodedicacion'] = TiempoDedicacionDocente.objects.filter(status=True)
                    data['listadoprofesortipo'] = ProfesorTipo.objects.filter(status=True)
                    # data['listadoprofesorcategorizacion'] = CategorizacionDocente.objects.filter(status=True)
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['idc'] = idc if idc else "0"
                    data['distributivoshoraasplanificadas'] = page.object_list
                    return render(request, "adm_criteriosactividadesdocente/planificarhoras.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriodocencia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Eliminar criterios de actividad docencia'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    return render(request, "adm_criteriosactividadesdocente/delcriteriodocencia.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriodocencia_aux':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Eliminar criterios de actividad docencia'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    return render(request, "adm_criteriosactividadesdocente/delcriteriodocencia_aux.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriteriodocencia':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Editar criterio de actividad de docencia'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    form = HorasCriterioForm()
                    form.horas_criterio(detalle.criteriodocenciaperiodo)
                    data['form'] = form
                    return render(request, "adm_criteriosactividadesdocente/editcriteriodocencia.html", data)
                except Exception as ex:
                    pass

            if action == 'criteriosinvestigacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Adicionar criterios de actividades de investigación del docente'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = distributivo = ProfesorDistributivoHoras.objects.get(pk=request.GET['iddistri'])
                    data['horas_asignadas_investigacion'] = distributivo.horasinvestigacion
                    data['criterios'] = CriterioInvestigacionPeriodo.objects.filter(periodo=periodo, maximo__gt=0)
                    return render(request, "adm_criteriosactividadesdocente/criteriosinvestigacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriterioinvestigacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Eliminar criterios de actividad investigación del docente'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    return render(request, "adm_criteriosactividadesdocente/delcriterioinvestigacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriterioinvestigacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Editar criterio de actividad de investigación del docente'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    data['iddistri'] = detalle.distributivo_id
                    form = HorasCriterioForm()
                    form.horas_criterio(detalle.criterioinvestigacionperiodo)
                    data['form'] = form
                    return render(request, "adm_criteriosactividadesdocente/editcriterioinvestigacion.html", data)
                except Exception as ex:
                    pass

            if action == 'criteriosgestion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Adicionar criterios de actividades de gestión del docente'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = distributivo = ProfesorDistributivoHoras.objects.get(pk=request.GET['iddistri'])
                    data['horas_asignadas_gestion'] = distributivo.horasgestion
                    data['criterios'] = CriterioGestionPeriodo.objects.filter(periodo=periodo, maximo__gt=0)
                    return render(request, "adm_criteriosactividadesdocente/criteriosgestion.html", data)
                except Exception as ex:
                    pass

            if action == 'criteriosvinculacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Adicionar criterios de actividades de vinculación del docente'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = distributivo = ProfesorDistributivoHoras.objects.get(pk=request.GET['iddistri'])
                    data['horas_asignadas_vinculacion'] = distributivo.horasvinculacion
                    if distributivo.coordinacion.id == 11:
                        # data['criterios'] = CriterioVinculacionPeriodo.objects.filter(periodo=periodo, maximo__gt=0, criterio__vicevinculacion=True)
                        data['criterios'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, maximo__gt=0, criterio__vicevinculacion=True, criterio__tipo=2)
                    else:
                        # data['criterios'] = CriterioVinculacionPeriodo.objects.filter(periodo=periodo, maximo__gt=0, criterio__vicevinculacion=False)
                        data['criterios'] = CriterioDocenciaPeriodo.objects.filter(periodo=periodo, maximo__gt=0, criterio__vicevinculacion=False, criterio__tipo=2)
                    return render(request, "adm_criteriosactividadesdocente/criteriosvinculacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriogestion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Eliminar criterios de actividad gestión del docente'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    return render(request, "adm_criteriosactividadesdocente/delcriteriogestion.html", data)
                except Exception as ex:
                    pass

            if action == 'delcriteriovinculacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Eliminar criterios de actividad vinculación del docente'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    return render(request, "adm_criteriosactividadesdocente/delcriteriovinculacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriteriogestion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Editar criterio de actividad de gestión del docente'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    form = HorasCriterioForm()
                    form.horas_criterio(detalle.criteriogestionperiodo)
                    data['form'] = form
                    data['idd'] = request.GET.get('idd', '')
                    return render(request, "adm_criteriosactividadesdocente/editcriteriogestion.html", data)
                except Exception as ex:
                    pass

            if action == 'editcriteriovinculacion':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Editar criterio de actividad de vinculación del docente'
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['profesor'] = detalle.distributivo.profesor
                    form = HorasCriterioForm()
                    # form.horas_criterio(detalle.criteriovinculacionperiodo)
                    form.horas_criterio(detalle.criteriodocenciaperiodo)
                    data['form'] = form
                    return render(request, "adm_criteriosactividadesdocente/editcriteriovinculacion.html", data)
                except Exception as ex:
                    pass

            if action == 'actividadescriterio':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    puede_adicionar = True
                    data['detalle'] = detalle = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    if detalle.es_criteriogestion():
                        data['title'] = u'Actividades de criterios - Gestión'
                    elif detalle.es_criterioinvestigacion():
                        data['title'] = u'Actividades de criterios - Investigación'
                    elif detalle.es_criteriodocencia():
                        data['title'] = u'Actividades de criterios - Docencia'
                    else:
                        data['title'] = u'Actividades de criterios - Vinculación'

                    if actividad := detalle.actividaddetalledistributivo_set.filter(status=True, vigente=True).first():
                        data['subactividades'] = subactividades = SubactividadDetalleDistributivo.objects.filter(actividaddetalledistributivo=actividad, subactividaddocenteperiodo__criterio__status=True, status=True)
                        data['actividades'] = ActividadDocentePeriodo.objects.filter(pk__in=subactividades.values_list('subactividaddocenteperiodo__actividad', flat=True), criterio__status=True, status=True)
                        data['es_actividad_macro'] = subactividades.exists()
                        data['actividadvigente'] = actividad
                    data['actualiza_horario'] = variable_valor('ACTUALIZAR_HORARIO_DOCENTE') if variable_valor('ACTUALIZAR_HORARIO_DOCENTE') else False
                    data['bloqueado'] = detalle.distributivo.bloqueardistributivo
                    return render(request, "adm_criteriosactividadesdocente/actividadescriterio.html", data)
                except Exception as ex:
                    pass

            if action == 'registrarhorario':
                try:
                    data['title'] = u'Horario de profesor'
                    nivel = periodo.nivel_set.filter(status=True).first()
                    es_posgrado = False
                    if nivel and nivel.coordinacion():
                        es_posgrado = nivel.coordinacion().id == 7

                    semana = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado']]
                    if es_posgrado or periodo.es_posgrado():
                        semana.append([7, 'Domingo'])
                    data['semana'] = semana
                    data['sumaactividad'] = 0
                    data['suma'] = 0
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = ProfesorDistributivoHoras.objects.filter(profesor_id=request.GET['id']).first()
                    data['iddistri'] = request.GET['iddistri']
                    data['distri'] = distri = ProfesorDistributivoHoras.objects.filter(id=request.GET['iddistri']).first()
                    data['profesormateria'] =profesormateria= ProfesorMateria.objects.filter(profesor=profesor, materia=distri.materia).first()

                    data['puede_registrar'] = True
                    data['solicitud_caduca'] = True
                    periodoacademia = periodo.periodo_academia()
                    profesor = Profesor.objects.get(pk=request.GET['id'])
                    if DetalleDistributivo.objects.filter(distributivo__id=distri.pk, distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                        data['sumaactividad'] = int(DetalleDistributivo.objects.filter(distributivo__id=distri.pk, distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo__criterio_id__in=[7]).aggregate(total=Sum('horas'))['total'])
                    idturnostutoria = []
                    turnosparatutoria = None
                    if HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo,profesormateria=profesormateria).exists():
                        horarios = HorarioTutoriaAcademica.objects.filter(status=True, profesor=profesor, periodo=periodo,profesormateria=profesormateria)
                        data['suma'] = int(horarios.aggregate(total=Sum('turno__horas'))['total'])
                        idturnostutoria = horarios.values_list('turno_id').distinct()
                        idsesiones=horarios.filter(turno__sesion_id=15).values_list('turno__sesion_id',flat=True).distinct()
                        if idsesiones:
                            turnosparatutoria = Turno.objects.filter(status=True, sesion_id__in=SESION_ID, id__in=idturnostutoria).distinct().order_by('comienza')
                        else:
                            turnosparatutoria = Turno.objects.filter(status=True, sesion_id=19).order_by('comienza')

                    data['turnos'] = turnosparatutoria
                    data['solicitud'] = solicitud = periodo.solicitud_horario_tutoria_docente(profesor)
                    carrera = profesor.profesordistributivohoras_set.filter(periodo=periodo).first()
                    data['director'] = CoordinadorCarrera.objects.filter(carrera=carrera.carrera, periodo=periodo, tipo=3).first()
                    data['diahoy'] = datetime.now().date().isoweekday()
                    return render(request, "adm_criteriosactividadesdocente/registrarhorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsolicitudhorario':
                try:
                    director = request.POST['iddirector']
                    if not DetalleSolicitudHorarioTutoria.objects.filter(periodo=periodo, profesor=profesor, director=director, estadosolicitud=1).exists():
                        solicitudhorario = DetalleSolicitudHorarioTutoria(periodo=periodo, profesor=profesor, director_id=director, observacion=request.POST['observacion'])
                        solicitudhorario.save(request)
                        asunto = u"SOLICITUD DE HORARIO DE TUTORIA ACADEMICA "
                        observacion = 'Se le comunica que el docente: {} de la carrera: {} en el periodo {} le ha solicitado una nueva fecha para cargar el horario de tutoria. Para acceder debe selecionar el periodo correspondiente y el perfil administrativo'.format(
                            profesor.persona, solicitudhorario.director.carrera, periodo.nombre)
                        notificacion(asunto, observacion, solicitudhorario.director.persona, None,
                                     '/adm_criteriosactividadesdocente?s=' + str(solicitudhorario.profesor.persona.apellido1) + '%20' + str(solicitudhorario.profesor.persona.apellido2) + '&idc=0',
                                     solicitudhorario.pk, 1, 'sga', DetalleSolicitudHorarioTutoria, request)
                        log(u'Ingreso solicitud para subir horario de tutorias: %s' % solicitudhorario, request, "add")
                        return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe una solicitud pendiente de este docente."})
                except Exception as e:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % str(e)})

            # return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

            if action == 'addactividad':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Adicionar actividad a criterio'
                    data['detalle'] = DetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['form'] = ActividadCriterioForm(initial={'desde': datetime.now().date(),
                                                                  'hasta': datetime.now().date()})
                    return render(request, "adm_criteriosactividadesdocente/addactividad.html", data)
                except Exception as ex:
                    pass

            if action == 'editactividad':
                try:
                    data['title'] = u'Editar actividad a criterio'
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['actividad'] = actividad = ActividadDetalleDistributivo.objects.get(pk=request.GET['id'])
                    form = ActividadCriterioForm(initial={'texto': actividad.nombre,
                                                          'desde': actividad.desde,
                                                          'hasta': actividad.hasta,
                                                          'horas': actividad.horas})
                    data['form'] = form
                    return render(request, "adm_criteriosactividadesdocente/editactividad.html", data)
                except Exception as ex:
                    pass

            if action == 'addhorascarrera':
                try:
                    data['title'] = u'Adicionar horas por carrera'
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['actividad'] = actividad = ActividadDetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['carreras'] = Carrera.objects.filter(status=True).order_by('nombre')
                    data['espractica'] = practica = False
                    if actividad.criterio.criteriodocenciaperiodo:
                        if actividad.criterio.criteriodocenciaperiodo.criterio.pk in [6, 154, 144]:
                            data['espractica'] = practica = True
                    data['actividadcarrera'] = ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle=actividad).order_by('carrera__nombre')
                    if practica:
                        return render(request, "adm_criteriosactividadesdocente/addcarrerashoraspracticas.html", data)
                    else:
                        return render(request, "adm_criteriosactividadesdocente/addcarrerashoras.html", data)
                except Exception as ex:
                    pass

            if action == 'delactividad':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Eliminar actividad'
                    data['actividad'] = ActividadDetalleDistributivo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividadesdocente/delactividad.html", data)
                except Exception as ex:
                    pass

            if action == 'actualiza':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Actualizar'
                    data['profesordistributivohoras'] = ProfesorDistributivoHoras.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividadesdocente/actualiza.html", data)
                except Exception as ex:
                    pass

            elif action == 'contaradmision':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'Tomar en cuenta admisión'
                    data['profesordistributivohora'] = ProfesorDistributivoHoras.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividadesdocente/contaradmision.html", data)
                except Exception as ex:
                    pass

            elif action == 'nocontaradmision':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['title'] = u'No tomar en cuenta admisión'
                    data['profesordistributivohora'] = ProfesorDistributivoHoras.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividadesdocente/nocontaradmision.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiodedicacion':
                try:
                    data['title'] = u'Cambio de dedicación'
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = distributivo = profesor.distributivohoraseval(periodo)
                    data['form'] = DedicacionProfesorForm(initial={'dedicacion': distributivo.dedicacion})
                    return render(request, "adm_criteriosactividadesdocente/cambiodedicacion.html", data)
                except Exception as ex:
                    pass

            if action == 'tablaponderativa':
                try:
                    data['title'] = u'Cambio de tabla ponderativa'
                    puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['distributivo'] = distributivo = profesor.distributivohoraseval(periodo)
                    data['form'] = PonderacionProfesorForm(initial={'dedicacion': distributivo.tablaponderacion})
                    return render(request, "adm_criteriosactividadesdocente/tablaponderativa.html", data)
                except Exception as ex:
                    pass

            if action == 'responsableactividad':
                try:
                    data['title'] = u'Responsable Actividad'
                    data['coordinacion'] = coordinaciones = persona.mis_coordinaciones()[0]
                    data['periodo'] = periodo
                    data['criteriodocencia'] = CriterioDocencia.objects.filter(criteriodocenciaperiodo__detalledistributivo__distributivo__profesor__coordinacion=coordinaciones, criteriodocenciaperiodo__periodo=periodo).distinct()
                    data['criterioinvestigacion'] = CriterioInvestigacion.objects.filter(criterioinvestigacionperiodo__detalledistributivo__distributivo__profesor__coordinacion=coordinaciones, criterioinvestigacionperiodo__periodo=periodo).distinct()
                    data['criteriogestion'] = CriterioGestion.objects.filter(criteriogestionperiodo__detalledistributivo__distributivo__profesor__coordinacion=coordinaciones, criteriogestionperiodo__periodo=periodo).distinct()
                    # data['criteriovinculacion'] = CriterioVinculacion.objects.filter(criteriovinculacionperiodo__detalledistributivo__distributivo__profesor__coordinacion=coordinaciones, criteriovinculacionperiodo__periodo=periodo).distinct()
                    data['criteriovinculacion'] = CriterioDocencia.objects.filter(criteriodocenciaperiodo__detalledistributivo__distributivo__profesor__coordinacion=coordinaciones, criteriodocencianperiodo__periodo=periodo).distinct()
                    data['profesor'] = Profesor.objects.filter(profesordistributivohoras__periodo=periodo).distinct().order_by('persona__apellido1')
                    data['encargadocriterioperiodo'] = EncargadoCriterioPeriodo.objects.filter(periodo=periodo, coordinacion=coordinaciones)
                    data['permite_modificar'] = False
                    return render(request, "adm_criteriosactividadesdocente/responsableactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'totalpreferenciaspregrado':
                try:
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('asignaturas_preferencias')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte_preferencias' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 3000),
                        (u"DOCENTE.", 15000),
                        (u"ASIGNATURA.", 9000),
                        (u"COORDINACION", 9000),
                        (u"CARRERA", 9000),
                        (u"NIVEL", 3000),
                        (u"JORNADA", 3000),
                        (u"TIPO", 3000),
                        (u"CATEGORIA", 3000),
                        (u"DEDICACION", 5000),
                        (u"PERIODO", 8500),
                        (u"DOCENTE CON LA MISMA ASIGNATURA", 15000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 2
                    listadistributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=90, status=True).exclude(profesor__persona__apellido1__icontains='APELLIDOVIRTUAL').exclude(profesor__persona__nombres__icontains='POR DEFINIR').exclude(profesor__persona__apellido1__icontains='POR DEFINIR').exclude(profesor__persona__apellido2__icontains='POR DEFINIR').order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
                    for listadis in listadistributivo:
                        listadopreferencia = AsignaturaMallaPreferencia.objects.filter(profesor=listadis.profesor, periodo=periodo, status=True)
                        if listadopreferencia:
                            for lista in listadopreferencia:
                                grupodocentes = AsignaturaMallaPreferencia.objects.values_list('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres').filter(periodo=lista.periodo, asignaturamalla=lista.asignaturamalla, status=True).exclude(profesor=lista.profesor).order_by('profesor__persona__apellido1')
                                campo1 = lista.profesor.persona.cedula
                                campo2 = lista.profesor.persona.apellido1 + ' ' + lista.profesor.persona.apellido2 + ' ' + lista.profesor.persona.nombres
                                campo3 = lista.asignaturamalla.asignatura.nombre
                                campo4 = lista.asignaturamalla.malla.carrera.nombre
                                campo10 = lista.asignaturamalla.malla.carrera.coordinacion_carrera().nombre
                                campo5 = lista.asignaturamalla.nivelmalla.nombre
                                if lista.sesion:
                                    campo6 = lista.sesion.nombre
                                else:
                                    campo6 = ''
                                if listadis.nivelcategoria:
                                    campo7 = listadis.nivelcategoria.nombre
                                else:
                                    campo7 = ''
                                if listadis.categoria:
                                    campo8 = listadis.categoria.nombre
                                else:
                                    campo8 = ''
                                if listadis.dedicacion:
                                    campo9 = listadis.dedicacion.nombre
                                else:
                                    campo9 = ''
                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo10, font_style2)
                                ws.write(row_num, 4, campo4, font_style2)
                                ws.write(row_num, 5, campo5, font_style2)
                                ws.write(row_num, 6, campo6, font_style2)
                                ws.write(row_num, 7, campo7, font_style2)
                                ws.write(row_num, 8, campo8, font_style2)
                                ws.write(row_num, 9, campo9, font_style2)
                                ws.write(row_num, 10, periodo.nombre, font_style2)
                                ws.write(row_num, 11, str(list(grupodocentes)), font_style2)
                                row_num += 1
                        else:
                            campo1 = listadis.profesor.persona.cedula
                            campo2 = listadis.profesor.persona.apellido1 + ' ' + listadis.profesor.persona.apellido2 + ' ' + listadis.profesor.persona.nombres
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, '---', font_style2)
                            ws.write(row_num, 10, periodo.nombre, font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'totalpreferenciasposgrado':
                try:
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('asigpreferenciasposgrado')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte_preferenciasposgrado' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 3000),
                        (u"DOCENTE.", 15000),
                        (u"ASIGNATURA.", 9000),
                        (u"COORDINACION", 9000),
                        (u"CARRERA", 9000),
                        (u"NIVEL", 3000),
                        (u"JORNADA", 3000),
                        (u"TIPO", 3000),
                        (u"CATEGORIA", 3000),
                        (u"DEDICACION", 5000),
                        (u"PERIODO COHORTE", 5000),
                        (u"TITULAR", 5000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 2
                    listadistributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=90, status=True).exclude(profesor__persona__apellido1__icontains='APELLIDOVIRTUAL').exclude(profesor__persona__nombres__icontains='POR DEFINIR').exclude(profesor__persona__apellido1__icontains='POR DEFINIR').exclude(profesor__persona__apellido2__icontains='POR DEFINIR').order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
                    for listadis in listadistributivo:
                        listadopreferencia = AsignaturaMallaPreferenciaPosgrado.objects.filter(profesor=listadis.profesor, status=True)
                        if listadopreferencia:
                            for lista in listadopreferencia:
                                campo1 = lista.profesor.persona.cedula
                                campo2 = lista.profesor.persona.apellido1 + ' ' + lista.profesor.persona.apellido2 + ' ' + lista.profesor.persona.nombres
                                campo3 = lista.asignaturamalla.asignatura.nombre
                                campo4 = lista.asignaturamalla.malla.carrera.nombre
                                campo10 = lista.asignaturamalla.malla.carrera.coordinacion_carrera().nombre
                                campo11 = lista.periodo.nombre
                                campo5 = lista.asignaturamalla.nivelmalla.nombre
                                if lista.sesion:
                                    campo6 = lista.sesion.nombre
                                else:
                                    campo6 = ''
                                if listadis.nivelcategoria:
                                    campo7 = listadis.nivelcategoria.nombre
                                else:
                                    campo7 = ''
                                if listadis.categoria:
                                    campo8 = listadis.categoria.nombre
                                else:
                                    campo8 = ''
                                if listadis.dedicacion:
                                    campo9 = listadis.dedicacion.nombre
                                else:
                                    campo9 = ''
                                campo12 = 'NO'
                                if IngresoPersonal.objects.filter(persona=lista.profesor.persona, regimenlaboral_id=2,
                                                                  estado=1, nombramiento=True, status=True):
                                    campo12 = 'SI'
                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo10, font_style2)
                                ws.write(row_num, 4, campo4, font_style2)
                                ws.write(row_num, 5, campo5, font_style2)
                                ws.write(row_num, 6, campo6, font_style2)
                                ws.write(row_num, 7, campo7, font_style2)
                                ws.write(row_num, 8, campo8, font_style2)
                                ws.write(row_num, 9, campo9, font_style2)
                                ws.write(row_num, 10, campo11, font_style2)
                                ws.write(row_num, 11, campo12, font_style2)
                                row_num += 1
                        else:
                            campo1 = listadis.profesor.persona.cedula
                            campo2 = listadis.profesor.persona.apellido1 + ' ' + listadis.profesor.persona.apellido2 + ' ' + listadis.profesor.persona.nombres
                            campo12 = 'NO'
                            if IngresoPersonal.objects.filter(persona=listadis.profesor.persona, regimenlaboral_id=2,
                                                              estado=1, nombramiento=True, status=True):
                                campo12 = 'SI'
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, '---', font_style2)
                            ws.write(row_num, 11, campo12, font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'totalpreferenciasactividades':
                try:
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('actividadpreferencias')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte_preferenciasactividad' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 3000),
                        (u"DOCENTE.", 15000),
                        (u"TIPO ACTIVIDAD", 4000),
                        (u"HORAS", 2000),
                        (u"ACTIVIDAD", 15000),
                        (u"TIPO", 3000),
                        (u"CATEGORIA", 3000),
                        (u"DEDICACION", 5000),
                        (u"PERIODO", 5000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 2
                    listadistributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=90, status=True).exclude(profesor__persona__apellido1__icontains='APELLIDOVIRTUAL').exclude(profesor__persona__nombres__icontains='POR DEFINIR').exclude(profesor__persona__apellido1__icontains='POR DEFINIR').exclude(profesor__persona__apellido2__icontains='POR DEFINIR').order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
                    for listadis in listadistributivo:
                        listadopreferenciadocencia = PreferenciaDetalleActividadesCriterio.objects.filter(criteriodocenciaperiodo__periodo=periodo, profesor=listadis.profesor, status=True)
                        if listadopreferenciadocencia:
                            for lista in listadopreferenciadocencia:
                                campo1 = lista.profesor.persona.cedula
                                campo2 = lista.profesor.persona.apellido1 + ' ' + lista.profesor.persona.apellido2 + ' ' + lista.profesor.persona.nombres
                                campo3 = 'DOCENCIA'
                                campo4 = lista.horas
                                campo5 = lista.criteriodocenciaperiodo.criterio.nombre
                                if listadis.nivelcategoria:
                                    campo6 = listadis.nivelcategoria.nombre
                                else:
                                    campo6 = ''
                                if listadis.categoria:
                                    campo7 = listadis.categoria.nombre
                                else:
                                    campo7 = ''
                                if listadis.dedicacion:
                                    campo8 = listadis.dedicacion.nombre
                                else:
                                    campo8 = ''
                                campo9 = lista.criteriodocenciaperiodo.periodo.nombre
                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo4, font_style2)
                                ws.write(row_num, 4, campo5, font_style2)
                                ws.write(row_num, 5, campo6, font_style2)
                                ws.write(row_num, 6, campo7, font_style2)
                                ws.write(row_num, 7, campo8, font_style2)
                                ws.write(row_num, 8, campo9, font_style2)
                                row_num += 1
                        listadopreferenciainvestigacion = PreferenciaDetalleActividadesCriterio.objects.filter(criterioinvestigacionperiodo__periodo=periodo, profesor=listadis.profesor, status=True)
                        if listadopreferenciainvestigacion:
                            for lista in listadopreferenciainvestigacion:
                                campo1 = lista.profesor.persona.cedula
                                campo2 = lista.profesor.persona.apellido1 + ' ' + lista.profesor.persona.apellido2 + ' ' + lista.profesor.persona.nombres
                                campo3 = 'INVESTIGACION'
                                campo4 = lista.horas
                                campo5 = lista.criterioinvestigacionperiodo.criterio.nombre
                                if listadis.nivelcategoria:
                                    campo6 = listadis.nivelcategoria.nombre
                                else:
                                    campo6 = ''
                                if listadis.categoria:
                                    campo7 = listadis.categoria.nombre
                                else:
                                    campo7 = ''
                                if listadis.dedicacion:
                                    campo8 = listadis.dedicacion.nombre
                                else:
                                    campo8 = ''
                                campo9 = lista.criterioinvestigacionperiodo.periodo.nombre
                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo4, font_style2)
                                ws.write(row_num, 4, campo5, font_style2)
                                ws.write(row_num, 5, campo6, font_style2)
                                ws.write(row_num, 6, campo7, font_style2)
                                ws.write(row_num, 7, campo8, font_style2)
                                ws.write(row_num, 8, campo9, font_style2)
                                row_num += 1
                        listadopreferenciagestion = PreferenciaDetalleActividadesCriterio.objects.filter(criteriogestionperiodo__periodo=periodo, profesor=listadis.profesor, status=True)
                        if listadopreferenciagestion:
                            for lista in listadopreferenciagestion:
                                campo1 = lista.profesor.persona.cedula
                                campo2 = lista.profesor.persona.apellido1 + ' ' + lista.profesor.persona.apellido2 + ' ' + lista.profesor.persona.nombres
                                campo3 = 'GESTION'
                                campo4 = lista.horas
                                campo5 = lista.criteriogestionperiodo.criterio.nombre
                                if listadis.nivelcategoria:
                                    campo6 = listadis.nivelcategoria.nombre
                                else:
                                    campo6 = ''
                                if listadis.categoria:
                                    campo7 = listadis.categoria.nombre
                                else:
                                    campo7 = ''
                                if listadis.dedicacion:
                                    campo8 = listadis.dedicacion.nombre
                                else:
                                    campo8 = ''
                                campo9 = lista.criteriogestionperiodo.periodo.nombre
                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo4, font_style2)
                                ws.write(row_num, 4, campo5, font_style2)
                                ws.write(row_num, 5, campo6, font_style2)
                                ws.write(row_num, 6, campo7, font_style2)
                                ws.write(row_num, 7, campo8, font_style2)
                                ws.write(row_num, 8, campo9, font_style2)
                                row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'totalpreferenciashorarios':
                try:
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('horariospreferencias')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte_preferenciashorario' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 3000),
                        (u"DOCENTE.", 15000),
                        (u"DIA", 4000),
                        # (u"JORNADA", 4000),
                        (u"TURNO", 5500),
                        (u"TIPO", 3000),
                        (u"CATEGORIA", 3000),
                        (u"DEDICACION", 5000),
                        (u"PERIODO", 5000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 2
                    listadistributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=90, status=True).exclude(profesor__persona__apellido1__icontains='APELLIDOVIRTUAL').exclude(profesor__persona__nombres__icontains='POR DEFINIR').exclude(profesor__persona__apellido1__icontains='POR DEFINIR').exclude(profesor__persona__apellido2__icontains='POR DEFINIR').order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
                    for listadis in listadistributivo:
                        listadopreferenciadocencia = HorarioPreferencia.objects.filter(periodo=periodo, profesor=listadis.profesor, status=True)
                        if listadopreferenciadocencia:
                            for lista in listadopreferenciadocencia:
                                campo1 = lista.profesor.persona.cedula
                                campo2 = lista.profesor.persona.apellido1 + ' ' + lista.profesor.persona.apellido2 + ' ' + lista.profesor.persona.nombres
                                campo3 = diaenletra(lista.dia)
                                # campo4 = lista.turno.sesion.nombre
                                campo5 = str(lista.turno.comienza) + ' - ' + str(lista.turno.termina)
                                if listadis.nivelcategoria:
                                    campo6 = listadis.nivelcategoria.nombre
                                else:
                                    campo6 = ''
                                if listadis.categoria:
                                    campo7 = listadis.categoria.nombre
                                else:
                                    campo7 = ''
                                if listadis.dedicacion:
                                    campo8 = listadis.dedicacion.nombre
                                else:
                                    campo8 = ''
                                campo9 = periodo.nombre
                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                # ws.write(row_num, 3, campo4, font_style2)
                                ws.write(row_num, 3, campo5, font_style2)
                                ws.write(row_num, 4, campo6, font_style2)
                                ws.write(row_num, 5, campo7, font_style2)
                                ws.write(row_num, 6, campo8, font_style2)
                                ws.write(row_num, 7, campo9, font_style2)
                                row_num += 1
                        else:
                            campo1 = listadis.profesor.persona.cedula
                            campo2 = listadis.profesor.persona.apellido1 + ' ' + listadis.profesor.persona.apellido2 + ' ' + listadis.profesor.persona.nombres
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, '---', font_style2)
                            ws.write(row_num, 7, periodo.nombre, font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'edittipos':
                try:
                    data['title'] = u'Editar Tipos'
                    data['periodolectivo'] = int(request.GET['periodolectivo'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['profesor']))
                    if periodo.clasificacion == 2:
                        data['profesor']
                        data['idmateria'] = idmateria = int(request.GET['idm'])
                        distributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=int(request.GET['periodolectivo']), profesor=profesor, materia_id=idmateria)[0]
                    else:
                        distributivo = ProfesorDistributivoHoras.objects.get(periodo_id=int(request.GET['periodolectivo']), profesor=profesor)
                    form = ProfesorTipoForm(initial={'tipo': distributivo.nivelcategoria,
                                                     'escalafon': distributivo.nivelescalafon,
                                                     'categoria': distributivo.categoria,
                                                     'dedicacion': distributivo.dedicacion,
                                                     'coordinacion': distributivo.coordinacion,
                                                     'carrera': distributivo.carrera,
                                                     'vercertificado': distributivo.vercertificado,
                                                     'verinforme': distributivo.verinforme,
                                                     'observacion': distributivo.observacion
                                                     })
                    form.editar(distributivo.coordinacion.id)
                    data['form'] = form
                    return render(request, "adm_criteriosactividadesdocente/edittipo.html", data)
                except:
                    pass

            if action == 'horario':
                try:
                    data['title'] = u'Horario de profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['excluidos'] = excluidos = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo_id__isnull=False, criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '30', '46', '7'])
                    distributivo = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor, periodo=periodo).first()
                    mensaje = ''
                    if excluidos:
                        for excluido in excluidos:
                            mensaje += str(excluido.criteriodocenciaperiodo.criterio.nombre)
                        data['message'] = mensaje
                    detalledsit = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo)
                    actidocencia = detalledsit.filter(criteriodocenciaperiodo_id__isnull=False).exclude(criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '30', '46', '7'])
                    actiinvestigacion = detalledsit.filter(criterioinvestigacionperiodo_id__isnull=False)
                    actigestion = detalledsit.filter(criteriogestionperiodo_id__isnull=False)
                    horasdi = actidocencia | actiinvestigacion | actigestion
                    if not horasdi:
                        if excluidos:
                            return HttpResponseRedirect('/adm_criteriosactividadesdocente?info=Lo sentimos este docente tiene criterios no validos: {}'.format(mensaje))
                    totalhoras = horasdi.aggregate(valor=Sum('horas'))
                    tienedetalledistributivo = 0
                    if ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo, detalledistributivo__distributivo__profesor=profesor).exists():
                        claseactividad = ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo, detalledistributivo__distributivo__profesor=profesor).count()
                    else:
                        tienedetalledistributivo = 1
                        claseactividad = ClaseActividad.objects.filter(actividaddetalle__criterio__distributivo__periodo=periodo, actividaddetalle__criterio__distributivo__profesor=profesor).count()
                    clase = Clase.objects.filter(Q(status=True, activo=True, profesor=profesor, materia__nivel__periodo=periodo, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True), Q(Q(inicio__lte=datetime.now().date()), Q(fin__gte=datetime.now().date()))).distinct().order_by('turno__inicio')
                    if distributivo.carrera and distributivo.carrera.mi_coordinacion2() == 1:
                        clase = Clase.objects.filter(status=True, activo=True, profesor=profesor, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, fin__gte=datetime.now().date()).distinct().order_by('turno__inicio')
                    clase = clase.filter(fin__gte=datetime.now().date()).exclude(tipoprofesor_id=5).exclude(materia__asignaturamalla__malla__carrera__coordinacion=7).exclude(materia__inicio__gt=datetime.now().date())
                    if clase.exists():
                        claseactividad += int(clase.values('dia', 'turno').count())
                    materias_transversal = profesor.profesormateria_set.filter(materia__nivel__periodo=periodo,
                                                                               materia__asignaturamalla__transversal=True,
                                                                               hasta__gte=datetime.now().date(), activo=True)
                    if materias_transversal:
                        if not clase.filter(materia__asignaturamalla__transversal=True):
                            claseactividad += int(materias_transversal.aggregate(total=Sum('hora'))['total'])
                    # clasenivelacion = Clase.objects.filter(Q(status=True, activo=True, profesor=profesor, materia__nivel__periodo=periodo,
                    #                                          materia__nivel__periodo__visible=True, materia__asignaturamalla__malla__carrera__coordinacion=9,
                    #                                          materia__nivel__periodo__visiblehorario=True)).distinct().order_by('turno__inicio').exclude(materia__inicio__gt=datetime.now().date())
                    # if clasenivelacion:
                    #     claseactividad += int(clasenivelacion.values('dia', 'turno').count())

                    data['totalhorasact'] = claseactividad


                    data['completo'] = 0
                    data['totalhorasdis'] = totalhorasdis = totalhoras.get('valor')
                    if claseactividad:
                        if claseactividad >= totalhorasdis > 0:
                            data['completo'] = 1
                    data['mostrar'] = 0
                    claseactividadestado = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True).order_by('-id').first()
                    # if ClaseActividadEstado.objects.filter(profesor=profesor,periodo=periodo,estadosolicitud=2,status=True).exists():
                    if claseactividadestado:
                        if claseactividadestado.estadosolicitud == 2:
                            data['mostrar'] = 1
                            data['detalleestados'] = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True)
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    # turnos = profesor.extrae_turnos_y_clases_docente(periodo)[1]
                    # COMPLEXIVO
                    # complexivo = ComplexivoClase.objects.values_list('turno__id').filter(activo=True, materia__profesor__profesorTitulacion=profesor, materia__status=True)
                    # if tienedetalledistributivo == 0:
                    #     actividades = ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo, detalledistributivo__distributivo__profesor=profesor)
                    # else:
                    #     actividades = ClaseActividad.objects.filter(actividaddetalle__criterio__distributivo__periodo=periodo, actividaddetalle__criterio__distributivo__profesor=profesor)
                    # turnoclases = Turno.objects.filter(Q(id__in=turnos) | Q(id__in=complexivo)).distinct().order_by('comienza')
                    # turnoactividades_old = Turno.objects.filter(id__in=actividades.values_list('turno__id')).distinct().order_by('comienza')
                    if periodo.id <= 177:
                        turnoclases = Turno.objects.filter(status=True, clase__activo=True, clase__materia__nivel__periodo=periodo, clase__materia__profesormateria__profesor=profesor, clase__materia__profesormateria__principal=True).values_list('id', flat=True).distinct().order_by('comienza')
                        if ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo, detalledistributivo__distributivo__profesor=profesor).exists():
                            turnoactividades = Turno.objects.filter(status=True, claseactividad__detalledistributivo__distributivo__periodo=periodo, claseactividad__detalledistributivo__distributivo__profesor=profesor).values_list('id', flat=True).distinct().order_by('comienza')
                        else:
                            turnoactividades = Turno.objects.filter(status=True, claseactividad__actividaddetalle__criterio__distributivo__periodo=periodo,claseactividad__actividaddetalle__criterio__distributivo__profesor=profesor).values_list('id', flat=True).distinct().order_by('comienza')
                        data['turnos'] = turnoactividades = Turno.objects.filter(Q(status=True), Q(id__in=turnoclases) | Q(id__in=turnoactividades)).distinct('comienza', 'termina')
                    else:
                        turnoactividades = Turno.objects.filter(Q(Q(sesion_id=20), Q(status=True), Q(mostrar=True))).distinct().order_by('comienza', 'termina')
                    # data['turnos'] = turnoclases | turnoactividades
                    detalledistdocencia = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo__isnull=False)

                    if detalledistdocencia.filter(criteriodocenciaperiodo__criterio__tipo=2, criteriodocenciaperiodo__criterio__vicevinculacion=True).exists():
                        turnoactividades = Turno.objects.filter(Q(sesion_id=20), Q(status=True))
                    elif detalledistdocencia.filter(criteriodocenciaperiodo__criterio__tipo=2, criteriodocenciaperiodo__criterio__vicevinculacion=True).exists() and detalledistdocencia.filter(criteriodocenciaperiodo__criterio__tipo=1).exists():
                        turnoactividades = Turno.objects.filter(Q(sesion_id=20), Q(status=True), Q(mostrar=True))
                    data['turnos'] = turnoactividades
                    data['finalizado'] = ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo, detalledistributivo__distributivo__profesor=profesor, finalizado=True).exists() or distributivo.horariofinalizado or claseactividad == totalhorasdis
                    data['reporte_0'] = obtener_reporte('horario_profesor')
                    data['puede_ver_horario'] = periodo.visible and periodo.visiblehorario
                    data['aprobado'] = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo,status=True, estadosolicitud=2).exists()
                    return render(request, "adm_criteriosactividadesdocente/horario.html", data)
                except Exception as ex:
                    pass

            # add actividad docente
            if action == 'listactividades':
                try:
                    profesor = Profesor.objects.get(id=request.GET['idprofesor'])
                    actidocencia = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo_id__isnull=False).exclude(criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '19', '30', '46', '7'])
                    actiinvestigacion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criterioinvestigacionperiodo_id__isnull=False)
                    actigestion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriogestionperiodo_id__isnull=False)
                    data['actividades'] = actidocencia | actiinvestigacion | actigestion
                    return render(request, "pro_horarios/actividadesdocentes.html", data)
                except Exception as ex:
                    pass

            if action == 'evidenciasactividades':
                try:
                    data['title'] = u'Evidencias Actividad de los Docentes'
                    # puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    # data['coordinacion'] = coordinaciones = persona.mis_coordinaciones()
                    data['coordinacion'] = coordinaciones = persona.mis_coordinaciones()
                    data['periodo'] = periodo
                    data['permite_modificar'] = False
                    data['evidenciaactividaddetalledistributivodocencia'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor__coordinacion__in=coordinaciones, criterio__distributivo__periodo=periodo, criterio__criteriodocenciaperiodo__isnull=False).distinct().order_by('criterio__distributivo__profesor', 'desde')
                    data['evidenciaactividaddetalledistributivoinvestigacion'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor__coordinacion__in=coordinaciones, criterio__distributivo__periodo=periodo, criterio__criterioinvestigacionperiodo__isnull=False).distinct().order_by('criterio__distributivo__profesor', 'desde')
                    data['evidenciaactividaddetalledistributivogestion'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__profesor__coordinacion__in=coordinaciones, criterio__distributivo__periodo=periodo, criterio__criteriogestionperiodo__isnull=False).distinct().order_by('criterio__distributivo__profesor', 'desde')
                    return render(request, "adm_criteriosactividadesdocente/evidenciasactividades.html", data)
                except Exception as ex:
                    pass

            if action == 'verevidencia':
                try:
                    data['title'] = u'Evidencias Actividad'
                    # puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    # data['coordinacion'] = coordinaciones = persona.mis_coordinaciones()
                    data['profesor'] = profesor = Profesor.objects.filter(pk=request.GET['id'])[0]
                    data['coordinacion'] = coordinaciones = persona.mis_coordinaciones()
                    data['periodo'] = periodo
                    data['permite_modificar'] = False
                    data['evidenciaactividaddetalledistributivodocencia'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__periodo=periodo, criterio__criteriodocenciaperiodo__isnull=False, criterio__criteriodocenciaperiodo__criterio__tipo=1, criterio__distributivo__profesor=profesor).distinct().order_by('criterio__criteriodocenciaperiodo__criterio__nombre', 'desde')
                    data['evidenciaactividaddetalledistributivoinvestigacion'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__periodo=periodo, criterio__criterioinvestigacionperiodo__isnull=False, criterio__distributivo__profesor=profesor).distinct().order_by('criterio__distributivo__profesor', 'desde')
                    data['evidenciaactividaddetalledistributivogestion'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__periodo=periodo, criterio__criteriogestionperiodo__isnull=False, criterio__distributivo__profesor=profesor).distinct().order_by('criterio__distributivo__profesor', 'desde')
                    data['evidenciaactividaddetalledistributivovincu'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__periodo=periodo, criterio__criteriodocenciaperiodo__isnull=False, criterio__criteriodocenciaperiodo__criterio__tipo=2, criterio__distributivo__profesor=profesor).distinct().order_by('criterio__criteriodocenciaperiodo__criterio__nombre', 'desde')
                    return render(request, "adm_criteriosactividadesdocente/verevidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesor':
                try:
                    data['title'] = u'Adicionar Profesor'
                    data['periodo'] = periodo
                    data['form'] = DocenteDistributivoForm
                    return render(request, "adm_criteriosactividadesdocente/addprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesorplanificar':
                try:
                    data['title'] = u'Adicionar Profesor'
                    data['periodo'] = periodo
                    data['form'] = DocentePlanificarForm
                    return render(request, "adm_criteriosactividadesdocente/addprofesorplanificar.html", data)
                except Exception as ex:
                    pass

            if action == 'imprimiracompanamiento':
                try:
                    data['title'] = u'Reportes de acompañamiento por asignatura'
                    data['iddocente'] = iddocente = request.GET['iddocente']
                    data['periodo'] = periodo = request.GET['periodo']
                    data['docente'] = request.GET['docente']
                    data['materia'] = Materia.objects.filter(profesormateria__profesor=iddocente,
                                                             profesormateria__principal=True,
                                                             nivel__periodo=periodo).distinct().order_by('inicio')
                    return render(request, "adm_criteriosactividadesdocente/acompanamiento.html", data)
                except Exception as ex:
                    pass

            if action == 'deletedistributivo':
                try:
                    data['title'] = u'Eliminar Distributivo'
                    data['distributivo'] = ProfesorDistributivoHoras.objects.get(pk=request.GET['iddistributivo'])
                    return render(request, "adm_criteriosactividadesdocente/deletedistributivo.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadodereportes':
                try:
                    data['title'] = u'Reportes del Distributivo del Docente'
                    data['listadocarreras'] = carreras = Carrera.objects.filter(status=True).order_by('nombre')
                    data['listadocarreraspregradovirtual'] = carreras
                    data['periodosesion'] = periodo = request.session['periodo']
                    #data['meses'] = list(filter(lambda m: m[0] in set([d.month for d in daterange(periodo.inicio, (periodo.fin + timedelta(days=1)))]), MESES_CHOICES))
                    data['meses'] = extraer_meses_periodo(periodo)
                    if es_decano:
                        contador = querydecano.count()
                        carrerasin = None
                        if contador > 1:
                            carrerasin = querydecano[0].coordinacion.carrera.filter(status=True)
                            for i in range(1, contador):
                                carrerasin = carrerasin.union(
                                    querydecano[i].coordinacion.carrera.filter(status=True))
                        else:
                            carrerasin = querydecano[0].coordinacion.carrera.filter(status=True)
                        carrerasin_lista = list(carrerasin)
                        mallacarrerasdecano = Malla.objects.filter(status=True, carrera__in=carrerasin_lista)
                        carreras = []
                        for carr in mallacarrerasdecano:
                            if carr.uso_en_periodo(periodo):
                                carreras.append(carr.carrera.id)
                        data['carreras_decano'] = Carrera.objects.filter(id__in=carreras, status=True)
                    return render(request, "adm_criteriosactividadesdocente/reportescriterioactividaddocente.html", data)
                except Exception as ex:
                    pass

            elif action == 'totalactividadesdocentes':
                try:
                    periodo = request.GET['periodo']
                    cursor = connections['default'].cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_actividaddocente.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.col(0).width = 1000
                    ws.col(1).width = 3000
                    ws.col(2).width = 10000
                    ws.col(3).width = 4000
                    ws.col(4).width = 10000
                    ws.col(5).width = 0
                    ws.col(6).width = 6000
                    ws.col(7).width = 2000
                    ws.col(8).width = 6000
                    ws.col(9).width = 6000
                    ws.col(10).width = 6000
                    ws.write(0, 0, 'N.')
                    ws.write(0, 1, 'CRITERIO')
                    ws.write(0, 2, 'FACULTAD')
                    ws.write(0, 3, 'CEDULA')
                    ws.write(0, 4, 'APELLIDOS Y NOMBRES')
                    ws.write(0, 5, 'USUARIO')
                    ws.write(0, 6, 'ACTIVIDAD')
                    ws.write(0, 7, 'HORAS')
                    ws.write(0, 8, 'DEDICACION')
                    ws.write(0, 9, 'TIPO PRPFESOR')
                    ws.write(0, 10, u'CATEGORIZACIÓN')
                    ws.write(0, 11, u'ESCALAFON')
                    ws.write(0, 12, 'SEXO')
                    a = 0
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaestudiante = "select 'Docencia' as criterio,coor.nombre as facultad,per.apellido1, per.apellido2 , per.nombres as docente, " \
                                      " cri.nombre as actividad,detdis.horas,us.username, td.nombre,(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ), per.cedula, " \
                                      "(select sex.nombre from sga_sexo sex where sex.id=per.sexo_id ) as sexo , (select cat.nombre from sga_profesortipo cat where cat.id=dis.nivelcategoria_id) as nivelcategoria, " \
                                      " (select cat.nombre from sga_nivelescalafondocente cat where cat.id=dis.nivelescalafon_id) as nivelcategoria " \
                                      " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                                      " sga_tiempodedicaciondocente td, " \
                                      " sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                      " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id " \
                                      " and pro.persona_id=per.id " \
                                      " and per.usuario_id=us.id " \
                                      " and dis.coordinacion_id=coor.id  " \
                                      " and dis.id=detdis.distributivo_id " \
                                      " and detdis.criteriodocenciaperiodo_id=critd.id " \
                                      " and critd.criterio_id=cri.id " \
                                      " and detdis.criteriodocenciaperiodo_id is not null " \
                                      " and dis.periodo_id='" + periodo + "' " \
                                                                          " union all " \
                                                                          " select 'Investigacion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2, per.nombres as docente, " \
                                                                          " cri.nombre as actividad,detdis.horas,us.username , td.nombre,(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ), per.cedula, " \
                                                                          " (select sex.nombre from sga_sexo sex where sex.id=per.sexo_id ) as sexo , (select cat.nombre from sga_profesortipo cat where cat.id=dis.nivelcategoria_id) as nivelcategoria, " \
                                                                          " (select cat.nombre from sga_nivelescalafondocente cat where cat.id=dis.nivelescalafon_id) as nivelcategoria " \
                                                                          " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                                          " sga_tiempodedicaciondocente td, " \
                                                                          " sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                          " where dis.profesor_id=pro.id " \
                                                                          " and td.id=dis.dedicacion_id " \
                                                                          " and pro.persona_id=per.id " \
                                                                          " and per.usuario_id=us.id " \
                                                                          " and dis.coordinacion_id=coor.id " \
                                                                          " and dis.id=detdis.distributivo_id " \
                                                                          " and detdis.criterioinvestigacionperiodo_id=critd.id " \
                                                                          " and critd.criterio_id=cri.id  " \
                                                                          " and detdis.criterioinvestigacionperiodo_id is not null " \
                                                                          " and dis.periodo_id='" + periodo + "'  " \
                                                                                                              " union all  " \
                                                                                                              " select 'Gestion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente, " \
                                                                                                              " cri.nombre as actividad,detdis.horas,us.username , td.nombre,(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ), per.cedula, " \
                                                                                                              " (select sex.nombre from sga_sexo sex where sex.id=per.sexo_id ) as sexo , (select cat.nombre from sga_profesortipo cat where cat.id=dis.nivelcategoria_id) as nivelcategoria, " \
                                                                                                              " (select cat.nombre from sga_nivelescalafondocente cat where cat.id=dis.nivelescalafon_id) as nivelcategoria " \
                                                                                                              " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                                                                              " sga_tiempodedicaciondocente td,  " \
                                                                                                              " sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                                                              " where dis.profesor_id=pro.id  " \
                                                                                                              " and td.id=dis.dedicacion_id   " \
                                                                                                              " and pro.persona_id=per.id  " \
                                                                                                              " and per.usuario_id=us.id  " \
                                                                                                              " and dis.coordinacion_id=coor.id " \
                                                                                                              " and dis.id=detdis.distributivo_id  " \
                                                                                                              " and detdis.criteriogestionperiodo_id=critd.id " \
                                                                                                              " and critd.criterio_id=cri.id  " \
                                                                                                              " and detdis.criteriogestionperiodo_id is not null " \
                                                                                                              " and dis.periodo_id='" + periodo + "';"
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, a)
                        ws.write(a, 1, per[0])
                        ws.write(a, 2, per[1])
                        ws.write(a, 3, per[10])
                        ws.write(a, 4, per[2] + ' ' + per[3] + ' ' + per[4])
                        ws.write(a, 5, per[7])
                        ws.write(a, 6, per[5])
                        ws.write(a, 7, per[6])
                        ws.write(a, 8, per[8])
                        ws.write(a, 9, per[12])
                        ws.write(a, 10, per[9])
                        ws.write(a, 11, per[13])
                        ws.write(a, 12, per[11])
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelldistributivo':
                try:
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = u'attachment; filename=DISTRIBUTIVO %s.xls' % periodo.nombre.__str__()
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.col(0).width = 1000
                    ws.col(1).width = 8000
                    ws.col(2).width = 3000
                    ws.col(3).width = 10000
                    ws.col(4).width = 3000
                    ws.col(5).width = 4000
                    ws.col(6).width = 4000
                    ws.col(7).width = 4000
                    ws.col(8).width = 4000
                    ws.col(9).width = 4000
                    ws.col(10).width = 2000
                    ws.col(11).width = 7000
                    ws.col(12).width = 7000
                    ws.col(13).width = 3000
                    ws.col(14).width = 8000
                    ws.col(15).width = 8000
                    ws.col(16).width = 8000
                    ws.write(0, 0, 'N.')
                    ws.write(0, 1, 'PERIODO')
                    ws.write(0, 2, 'CEDULA')
                    ws.write(0, 3, 'NOMBRES')
                    ws.write(0, 4, 'SEXO')
                    ws.write(0, 5, 'FACULTAD')
                    ws.write(0, 6, 'DEDICACION')
                    ws.write(0, 7, 'TIPO')
                    ws.write(0, 8, 'CATEGORIA')
                    ws.write(0, 9, 'ESCALAFON')
                    ws.write(0, 10, 'TOTAL HORAS')
                    ws.write(0, 11, 'HORAS ACTIVIDADES PLANIFICADAS')
                    ws.write(0, 12, 'HORAS ACTIVIDADES SOLICITADAS')
                    ws.write(0, 13, 'ACTIVIDADES COMPLETAS')
                    ws.write(0, 14, 'TELÉFONO')
                    ws.write(0, 15, 'CIUDAD')
                    ws.write(0, 16, 'DIRECCIÓN')
                    ws.write(0, 17, 'CARRERA')
                    ws.write(0, 18, 'CORREO')
                    a = 0
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listadodistributivo = ProfesorDistributivoHoras.objects.select_related('profesor', 'periodo''').filter(periodo_id=int(encrypt(request.GET['periodo'])), status=True).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
                    for per in listadodistributivo:
                        actidocencia = DetalleDistributivo.objects.select_related().filter(distributivo__profesor=per.profesor, distributivo__periodo=per.periodo, criteriodocenciaperiodo_id__isnull=False).exclude(criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '19'])
                        actiinvestigacion = DetalleDistributivo.objects.select_related().filter(distributivo__profesor=per.profesor, distributivo__periodo=per.periodo, criterioinvestigacionperiodo_id__isnull=False)
                        actigestion = DetalleDistributivo.objects.select_related().filter(distributivo__profesor=per.profesor, distributivo__periodo=per.periodo, criteriogestionperiodo_id__isnull=False)
                        horasdi = actidocencia | actiinvestigacion | actigestion
                        horasplan = horasdi.aggregate(valor=Sum('horas'))
                        horasplanificadas = horasplan.get('valor')
                        if horasplanificadas:
                            horasplanificadas = horasplanificadas
                        else:
                            horasplanificadas = 0
                        claseactividad = ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=per.periodo, detalledistributivo__distributivo__profesor=per.profesor, status=True).count()
                        if horasplanificadas == 0 and claseactividad == 0:
                            completo = 'NO TIENE HORAS ACTIVIDADES PLANIFICADAS'
                        else:
                            if horasplanificadas == claseactividad:
                                completo = 'SI'
                            else:
                                completo = 'NO'
                        a += 1
                        dedicacion = ''
                        if per.dedicacion:
                            dedicacion = per.dedicacion.nombre
                        nivelcategoria = ''
                        if per.nivelcategoria:
                            nivelcategoria = per.nivelcategoria.nombre
                        categoria = ''
                        if per.categoria:
                            categoria = per.categoria.nombre
                        nivelescalafon = ''
                        if per.nivelescalafon:
                            nivelescalafon = per.nivelescalafon.nombre
                        telefono = ''
                        if per.profesor.persona.telefono or per.profesor.persona.telefono_conv:
                            telefono = per.profesor.persona.telefono.__str__() + " - " + per.profesor.persona.telefono_conv.__str__()
                        ciudad = ''
                        if per.profesor.persona.canton:
                            ciudad = per.profesor.persona.canton.__str__()
                        direccion = ''
                        if per.profesor.persona.direccion or per.profesor.persona.direccion2:
                            direccion = per.profesor.persona.direccion.__str__() + " - " + per.profesor.persona.direccion2.__str__()
                        carrera = per.carrera.__str__() if per.carrera else ""
                        correo = u"%s" % per.profesor.persona.emailinst
                        ws.write(a, 0, a)
                        ws.write(a, 1, per.periodo.nombre)
                        ws.write(a, 2, per.profesor.persona.cedula)
                        ws.write(a, 3, per.profesor.persona.apellido1 + ' ' + per.profesor.persona.apellido2 + ' ' + per.profesor.persona.nombres)
                        ws.write(a, 4, per.profesor.persona.sexo.nombre)
                        ws.write(a, 5, per.coordinacion.alias)
                        ws.write(a, 6, dedicacion)
                        ws.write(a, 7, nivelcategoria)
                        ws.write(a, 8, categoria)
                        ws.write(a, 9, nivelescalafon)
                        ws.write(a, 10, per.total_horas())
                        ws.write(a, 11, horasplanificadas)
                        ws.write(a, 12, claseactividad)
                        ws.write(a, 13, completo)
                        ws.write(a, 14, telefono)
                        ws.write(a, 15, ciudad)
                        ws.write(a, 16, direccion)
                        ws.write(a, 17, carrera)
                        ws.write(a, 18, correo)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportedocenteinvestigacioncriterios':
                try:
                    response = HttpResponse(
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    periodo = periodo.id
                    response[
                        'Content-Disposition'] = f'attachment; filename="investigacioncriteriodocenteperiodo {periodo}.xlsx"'
                    output = io.BytesIO()
                    __author__ = 'Unemi'
                    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                    ws = workbook.add_worksheet("Listado")
                    formatolista = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'text_wrap': True})

                    fuentecabecera = workbook.add_format({
                        'align': 'center',
                        'bg_color': 'silver',
                        'border': 1,
                        'bold': 1
                    })

                    formatoceldacenter = workbook.add_format({
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'})

                    formatoceldacenter = workbook.add_format({
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'})

                    fuenteencabezado = workbook.add_format({
                        'align': 'center',
                        'bg_color': '#1C3247',
                        'font_color': 'white',
                        'border': 1,
                        'font_size': 24,
                        'bold': 1
                    })

                    columnas = [
                        (u"CEDULA", 60),
                        (u"NOMBRES", 60),
                        (u"EMAIL INSTITUCIONAL", 60),
                        (u"COORDINACION", 40),
                        (u"CARGO DOCENTE", 40),
                        (u"ACTIVIDAD PRINCIPAL", 40),
                        (u"HORAS ACTIVIDAD PRINCIPAL", 40),
                        (u"TIPO DE PROFESOR", 40),
                        (u"DEDICACION", 40),
                        (u" ", 80),
                        (u" ", 80),
                        (u" ", 80),
                        (u" ", 80),
                        (u" ", 80),
                        (u" ", 80),
                        (u" ", 100),

                    ]

                    ws.merge_range(0, 0, 0, columnas.__len__() - 1, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO',
                                   fuenteencabezado)
                    ws.merge_range(1, 0, 1, columnas.__len__() - 1,
                                   f'DISTRIBUTIVO DE ACTIVIDADES Y ASIGNATURAS - CRITERIOS DE INVESTIGACION',
                                   fuenteencabezado)
                    row_num, numcolum = 2, 0
                    for col_name in columnas:
                        ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                        ws.set_column(numcolum, numcolum, col_name[1])
                        numcolum += 1
                    row_num += 1

                    cabdistributivo = ProfesorDistributivoHoras.objects.filter(horasinvestigacion__gt=0, status=True,
                                                                               periodo_id=periodo,
                                                                               activo=True).values_list('id', flat=True)

                    detalles = DetalleDistributivo.objects.filter(
                        distributivo_id__in=cabdistributivo,
                        criterioinvestigacionperiodo_id__isnull=False

                    )

                    for rec in detalles:
                        persona = rec.distributivo.profesor.persona
                        data = actividad_macro_actividades_investigacion(rec, persona)
                        rel = {}
                        if data:
                            if data["actividades"] and data["subactividades"]:
                                for i in data["actividades"]:
                                    sub = []
                                    for x in data["subactividades"]:
                                        if i == x.subactividaddocenteperiodo.actividad:
                                            evdd = x.total_evidencias()
                                            criterio = x.subactividaddocenteperiodo.criterio.nombre if x.subactividaddocenteperiodo.criterio else " "
                                            sub.append("--" + criterio + " [ "
                                                       + " F.I:" + x.fechainicio.strftime("%d/%m/%Y") + " "
                                                       + " F.F: " + x.fechafin.strftime("%d/%m/%Y") + " "
                                                       + " Evdd: " + str(evdd) + " ] ")
                                    rel[i.criterio.nombre] = sub
                        ws.write(row_num, 0, rec.distributivo.profesor.persona.cedula, formatoceldacenter)
                        ws.write(row_num, 1, rec.distributivo.profesor.persona.nombre_completo_inverso(),
                                 formatoceldacenter)
                        ws.write(row_num, 2,
                                 rec.distributivo.profesor.persona.emailinst if rec.distributivo.profesor.persona.emailinst else " ",
                                 formatoceldacenter)
                        ws.write(row_num, 3,
                                 rec.distributivo.profesor.coordinacion.nombre if rec.distributivo.profesor.coordinacion else " ",
                                 formatoceldacenter)
                        ws.write(row_num, 4,
                                 rec.distributivo.profesor.cargo.nombre if rec.distributivo.profesor.cargo else " ",
                                 formatoceldacenter)
                        ws.write(row_num, 5,
                                 rec.criterioinvestigacionperiodo.criterio.nombre if rec.criterioinvestigacionperiodo else " ",
                                 formatoceldacenter)
                        ws.write(row_num, 6, rec.horas if rec else "0", formatoceldacenter)
                        ws.write(row_num, 7,
                                 rec.distributivo.profesor.nivelcategoria.nombre if rec.distributivo.profesor.nivelcategoria else " ",
                                 formatoceldacenter)
                        ws.write(row_num, 8,
                                 rec.distributivo.profesor.dedicacion.nombre if rec.distributivo.profesor.dedicacion else " ",
                                 formatoceldacenter)
                        # ws.write(row_num, 6, per[9], formatoceldacenter)
                        # ws.write(row_num, 7, per[10].strftime("%d/%m/%Y") if per[10] else '', formatoceldacenter)
                        # ws.write(row_num, 8, per[11].strftime("%d/%m/%Y") if per[11] else '', formatoceldacenter)
                        # ws.write(row_num, 9, per[12], formatoceldacenter)
                        # ws.write(row_num, 10, per[13], formatoceldacenter)
                        # ws.write(row_num, 11, per[14], formatoceldacenter)
                        # ws.write(row_num, 12, per[2] + ' ' + per[3] + ' ' + per[4], formatoceldacenter)
                        # ws.write(row_num, 13, per[0], formatoceldacenter)
                        # ws.write(row_num, 14, per[19], formatoceldacenter)
                        # ws.write(row_num, 15, per[21] + '@unemi.edu.ec', formatoceldacenter)
                        # ws.write(row_num, 16, per[17], formatoceldacenter)
                        # ws.write(row_num, 17, per[29], formatoceldacenter)
                        # ws.write(row_num, 18, per[16], formatoceldacenter)
                        # ws.write(row_num, 19, per[1], formatoceldacenter)
                        # ws.write(row_num, 20, per[22], formatoceldacenter)
                        # ws.write(row_num, 21, per[28], formatoceldacenter)
                        # ws.write(row_num, 22, per[23], formatoceldacenter)
                        # ws.write(row_num, 23, per[24], formatoceldacenter)
                        # ws.write(row_num, 24, per[25], formatoceldacenter)
                        # ws.write(row_num, 25, per[26], formatoceldacenter)
                        celd = 9
                        if rel:
                            for celda, lista in rel.items():
                                union = celda + '\n' + '___________________________________________' + '\n' + '\n'.join(
                                    lista)
                                ws.write(row_num, celd, union, formatolista)

                                celd += 1
                        row_num += 1
                    workbook.close()
                    response.write(output.getvalue())
                    output.close()
                    return response
                except Exception as ex:
                    return HttpResponseRedirect(f"/?info={ex}")

            elif action == 'excelltutoriasfacultades':
                try:
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = u'attachment; filename=tutorias %s.xls' % periodo.nombre.__str__()
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.col(0).width = 1000
                    ws.col(1).width = 8000
                    ws.col(2).width = 8000
                    ws.col(3).width = 8000
                    ws.col(4).width = 8000
                    ws.col(5).width = 5000
                    ws.col(6).width = 4000
                    ws.col(7).width = 2000
                    ws.write(0, 0, 'N.')
                    ws.write(0, 1, 'PERIODO')
                    ws.write(0, 2, 'FACULTAD')
                    ws.write(0, 3, 'CARRERA')
                    ws.write(0, 4, 'DOCENTE')
                    ws.write(0, 5, 'ASIGNATURA')
                    ws.write(0, 6, 'TEMA')
                    ws.write(0, 7, 'TOTAL')
                    a = 0
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listadotutorias = AvTutorias.objects.filter(materia__nivel__periodo_id=int(encrypt(request.GET['periodo']))).order_by("materia__asignaturamalla__malla__carrera").distinct()
                    for tut in listadotutorias:
                        a += 1
                        profesor = ''
                        if tut.materia.profesor_materia_principal:
                            profesor = tut.materia.profesor_materia_principal().profesor.persona.nombre_completo().__str__()
                        asignatura = tut.materia.asignaturamalla.asignatura.nombre + '-' + tut.materia.asignaturamalla.nivelmalla.nombre + '-' + tut.materia.paralelo
                        ws.write(a, 0, a)
                        ws.write(a, 1, periodo.nombre)
                        ws.write(a, 2, tut.materia.asignaturamalla.malla.carrera.mi_coordinacion())
                        ws.write(a, 3, tut.materia.asignaturamalla.malla.carrera.nombre)
                        ws.write(a, 4, profesor)
                        ws.write(a, 5, asignatura)
                        ws.write(a, 6, tut.observacion)
                        ws.write(a, 7, tut.participantes())
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'totalactividadesdocentesmaterias':
                try:
                    periodo = request.GET['periodo']
                    cursor = connections['default'].cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_actividaddocente_materia.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf(
                        'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    # ws.write_merge(0, 0, 0, 5, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 10000
                    ws.col(1).width = 4000
                    ws.col(2).width = 4000
                    ws.col(3).width = 4000
                    ws.col(4).width = 2000
                    ws.col(5).width = 6000
                    ws.col(6).width = 2000
                    ws.col(7).width = 10000
                    ws.col(8).width = 3000
                    ws.col(9).width = 3000
                    ws.col(10).width = 6000
                    ws.col(11).width = 6000
                    ws.col(12).width = 4000
                    ws.col(13).width = 6000
                    ws.col(14).width = 4000
                    ws.col(15).width = 10000
                    ws.col(16).width = 10000
                    ws.col(17).width = 5000
                    ws.col(18).width = 5000
                    ws.col(19).width = 5000
                    ws.col(20).width = 5000
                    ws.col(21).width = 5000
                    ws.write(0, 0, 'CARRERA')
                    ws.write(0, 1, 'MALLA')
                    ws.write(0, 2, 'SECCION')
                    ws.write(0, 3, 'NIVEL')
                    ws.write(0, 4, 'PARALELO')
                    ws.write(0, 5, 'ACTIVIDADES/MATERIAS')
                    ws.write(0, 6, 'HORAS')
                    ws.write(0, 7, 'APELLIDOS Y NOMBRES')
                    ws.write(0, 8, 'CRITERIO')
                    ws.write(0, 9, 'CEDULA')
                    ws.write(0, 10, 'CORREO INSTITUCIONAL')
                    ws.write(0, 11, u'CATEGORIZACIÓN')
                    ws.write(0, 12, u'TIPO')
                    ws.write(0, 13, 'DEDICACION')
                    ws.write(0, 14, 'FACULTAD')
                    ws.write(0, 15, 'TIPO PROFESOR')
                    ws.write(0, 16, 'TITULO TERCER NIVEL')
                    ws.write(0, 17, 'TITULO MASTER')
                    ws.write(0, 18, 'TITULO PHD')
                    ws.write(0, 19, 'ETNIA')
                    ws.write(0, 20, 'SEXO')
                    ws.write(0, 21, 'LGTBI')
                    a = 0
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaestudiante = "select 'Docencia' as criterio,coor.nombre as facultad,per.apellido1, per.apellido2 , per.nombres as docente, " \
                                      "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username, td.nombre, " \
                                      "(select cat.nombre from sga_categorizaciondocente cat  " \
                                      "where cat.id=dis.categoria_id ),null,per.cedula,per.emailinst,us.username, " \
                                      "null as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                      " left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                      "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                      "where tc.persona_id=per.id " \
                                      "and tit.nivel_id=4 " \
                                      "and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master , " \
                                      "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
                                      "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd, " \
                                      "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True) as etnia,  " \
                                      "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi, " \
                                      "(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                      "left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                      "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                      "where tc.persona_id=per.id " \
                                      "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,  " \
                                      "(select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0 " \
                                      "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd,  " \
                                      "sga_tiempodedicaciondocente td,  " \
                                      "sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us  " \
                                      "where dis.profesor_id=pro.id  " \
                                      "and td.id=dis.dedicacion_id  " \
                                      "and pro.persona_id=per.id   " \
                                      "and per.usuario_id=us.id  " \
                                      "and dis.coordinacion_id=coor.id  " \
                                      "and dis.id=detdis.distributivo_id  " \
                                      "and detdis.criteriodocenciaperiodo_id=critd.id  " \
                                      "and critd.criterio_id=cri.id  " \
                                      "and detdis.criteriodocenciaperiodo_id is not null  " \
                                      "and dis.periodo_id='" + periodo + "' and cri.id not in (15,16,17,18)  " \
                                                                         "union all  " \
                                                                         "select 'Investigacion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2, per.nombres as docente,  " \
                                                                         "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username , td.nombre, " \
                                                                         "(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ), " \
                                                                         "null,per.cedula,per.emailinst,us.username,null as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                         " left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                         "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                         "where tc.persona_id=per.id " \
                                                                         "and tit.nivel_id=4 " \
                                                                         "and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master , " \
                                                                         "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
                                                                         "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd,  " \
                                                                         "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True) as etnia,  " \
                                                                         "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi, " \
                                                                         "(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                         "left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                         "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                         "where tc.persona_id=per.id " \
                                                                         "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,  " \
                                                                         "(select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0 " \
                                                                         "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd,  " \
                                                                         "sga_tiempodedicaciondocente td,  " \
                                                                         "sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us  " \
                                                                         "where dis.profesor_id=pro.id   " \
                                                                         "and td.id=dis.dedicacion_id  " \
                                                                         "and pro.persona_id=per.id  " \
                                                                         "and per.usuario_id=us.id  " \
                                                                         "and dis.coordinacion_id=coor.id  " \
                                                                         "and dis.id=detdis.distributivo_id  " \
                                                                         "and detdis.criterioinvestigacionperiodo_id=critd.id  " \
                                                                         "and critd.criterio_id=cri.id  " \
                                                                         "and detdis.criterioinvestigacionperiodo_id is not null  " \
                                                                         "and dis.periodo_id='" + periodo + "' " \
                                                                                                            "union all  " \
                                                                                                            "select 'Gestion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente,  " \
                                                                                                            "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username , td.nombre, " \
                                                                                                            "(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ),null, " \
                                                                                                            "per.cedula,per.emailinst,us.username,null as tipoprofesor ,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                                                            " left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                                                            "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                                                            "where tc.persona_id=per.id " \
                                                                                                            "and tit.nivel_id=4 " \
                                                                                                            "and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master , " \
                                                                                                            "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
                                                                                                            "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd,  " \
                                                                                                            "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia, " \
                                                                                                            "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi, " \
                                                                                                            "(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                                                            "left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                                                            "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                                                            "where tc.persona_id=per.id " \
                                                                                                            "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,  " \
                                                                                                            "(select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0 " \
                                                                                                            "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd,  " \
                                                                                                            "sga_tiempodedicaciondocente td,  " \
                                                                                                            "sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us  " \
                                                                                                            "where dis.profesor_id=pro.id  " \
                                                                                                            "and td.id=dis.dedicacion_id   " \
                                                                                                            "and pro.persona_id=per.id  " \
                                                                                                            "and per.usuario_id=us.id  " \
                                                                                                            "and dis.coordinacion_id=coor.id  " \
                                                                                                            "and dis.id=detdis.distributivo_id  " \
                                                                                                            "and detdis.criteriogestionperiodo_id=critd.id  " \
                                                                                                            "and critd.criterio_id=cri.id  " \
                                                                                                            "and detdis.criteriogestionperiodo_id is not null  " \
                                                                                                            "and dis.periodo_id='" + periodo + "' " \
                                                                                                                                               "union all  " \
                                                                                                                                               "select 'Materias' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente,  " \
                                                                                                                                               "mat.paralelo,nmalla.nombre as nivel,carr.nombre || ' ' || carr.mencion as carreras, asig.nombre as actividad,mat.horassemanales,us.username ,  " \
                                                                                                                                               "td.nombre,(select cat.nombre from sga_categorizaciondocente cat, sga_profesordistributivohoras dist " \
                                                                                                                                               "where cat.id=dist.categoria_id and dist.periodo_id='" + periodo + "' and dist.profesor_id=pro.id ),ses.nombre as sesion, " \
                                                                                                                                                                                                                  "per.cedula,per.emailinst,us.username,tipro.nombre as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                                                                                                                                                                  " left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                                                                                                                                                                  "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                                                                                                                                                                  "where tc.persona_id=per.id " \
                                                                                                                                                                                                                  "and tit.nivel_id=4 " \
                                                                                                                                                                                                                  "and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master , " \
                                                                                                                                                                                                                  "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
                                                                                                                                                                                                                  "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd,  " \
                                                                                                                                                                                                                  "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia,  " \
                                                                                                                                                                                                                  "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi, " \
                                                                                                                                                                                                                  "(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                                                                                                                                                                  "left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                                                                                                                                                                  "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                                                                                                                                                                  "where tc.persona_id=per.id " \
                                                                                                                                                                                                                  "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,  " \
                                                                                                                                                                                                                  "(select pt1.nombre from sga_profesortipo pt1, sga_profesordistributivohoras dist where pt1.id=dist.nivelcategoria_id and dist.periodo_id='" + periodo + "' and dist.profesor_id=pro.id) as tipoprofesor,extract(year from malla.inicio) as anio " \
                                                                                                                                                                                                                                                                                                                                                                           "from sga_profesormateria pmat,sga_materia mat,sga_nivel niv,sga_profesor pro,sga_persona per,  " \
                                                                                                                                                                                                                                                                                                                                                                           "sga_asignaturamalla asimalla,sga_malla malla,sga_carrera carr,sga_asignatura asig,  " \
                                                                                                                                                                                                                                                                                                                                                                           "sga_nivelmalla nmalla,auth_user us,sga_coordinacion_carrera corcar,sga_coordinacion coor,  " \
                                                                                                                                                                                                                                                                                                                                                                           "sga_tiempodedicaciondocente td ,sga_sesion ses, sga_tipoprofesor tipro  " \
                                                                                                                                                                                                                                                                                                                                                                           "where pmat.profesor_id=pro.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and pro.persona_id=per.id   " \
                                                                                                                                                                                                                                                                                                                                                                           "and per.usuario_id=us.id    " \
                                                                                                                                                                                                                                                                                                                                                                           "and pro.dedicacion_id=td.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and pmat.materia_id=mat.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and mat.nivel_id=niv.id and niv.sesion_id=ses.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and mat.asignaturamalla_id=asimalla.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and asimalla.malla_id=malla.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and malla.carrera_id=carr.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and corcar.carrera_id=carr.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and corcar.coordinacion_id=coor.id and tipro.id not in (4) " \
                                                                                                                                                                                                                                                                                                                                                                           "and asimalla.asignatura_id=asig.id and asimalla.nivelmalla_id=nmalla.id and pmat.tipoprofesor_id=tipro.id  " \
                                                                                                                                                                                                                                                                                                                                                                           "and niv.periodo_id='" + periodo + "'"
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, "%s" % per[7])
                        ws.write(a, 1, per[25] if per[25] != 0 else '')
                        ws.write(a, 2, "%s" % per[13])
                        ws.write(a, 3, "%s" % per[6])
                        ws.write(a, 4, "%s" % per[5])
                        ws.write(a, 5, "%s" % per[8])
                        ws.write(a, 6, "%s" % per[9])
                        ws.write(a, 7, "%s" % (per[2] + ' ' + per[3] + ' ' + per[4]))
                        ws.write(a, 8, "%s" % per[0])
                        ws.write(a, 9, "%s" % per[14])
                        ws.write(a, 10, "%s" % per[16] + '@unemi.edu.ec')
                        ws.write(a, 11, "%s" % per[12])
                        ws.write(a, 12, "%s" % per[24])
                        ws.write(a, 13, "%s" % per[11])
                        ws.write(a, 14, "%s" % per[1])
                        ws.write(a, 15, "%s" % per[17])
                        ws.write(a, 16, "%s" % per[23])
                        ws.write(a, 17, "%s" % per[18])
                        ws.write(a, 18, "%s" % per[19])
                        ws.write(a, 19, "%s" % per[20])
                        ws.write(a, 20, "%s" % per[21])
                        if per[22]:
                            lgtbi = 'SI'
                        else:
                            lgtbi = 'NO'
                        ws.write(a, 21, lgtbi)
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'totalactividadesdocentescarrera':
                try:
                    periodo = request.GET['periodo']
                    cursor = connections['default'].cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_actividaddocente_materia.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf(
                        'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    # ws.write_merge(0, 0, 0, 5, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 10000
                    ws.col(1).width = 4000
                    ws.col(2).width = 4000
                    ws.col(3).width = 4000
                    ws.col(4).width = 2000
                    ws.col(5).width = 6000
                    ws.col(6).width = 6000
                    ws.col(7).width = 3000
                    ws.col(8).width = 3000
                    ws.col(9).width = 2000
                    ws.col(10).width = 6000
                    ws.col(11).width = 2000
                    ws.col(12).width = 10000
                    ws.col(13).width = 3000
                    ws.col(14).width = 3000
                    ws.col(15).width = 6000
                    ws.col(16).width = 6000
                    ws.col(17).width = 4000
                    ws.col(18).width = 6000
                    ws.col(19).width = 4000
                    ws.col(20).width = 10000
                    ws.col(21).width = 10000
                    ws.col(22).width = 5000
                    ws.col(23).width = 5000
                    ws.col(24).width = 5000
                    ws.col(25).width = 5000
                    ws.col(26).width = 5000
                    ws.write(0, 0, 'CARRERA')
                    ws.write(0, 1, 'MALLA')
                    ws.write(0, 2, 'SECCION')
                    ws.write(0, 3, 'NIVEL')
                    ws.write(0, 4, 'PARALELO')
                    ws.write(0, 5, 'ACTIVIDADES')
                    ws.write(0, 6, 'SUBACTIVIDADES')
                    ws.write(0, 7, 'SUBACTIVIDADES FECHA DESDE')
                    ws.write(0, 8, 'SUBACTIVIDADES FECHA FIN')
                    ws.write(0, 9, 'SUBACTIVIDADES HORAS')
                    ws.write(0, 10, 'MATERIAS')
                    ws.write(0, 11, 'HORAS')
                    ws.write(0, 12, 'APELLIDOS Y NOMBRES')
                    ws.write(0, 13, 'CRITERIO')
                    ws.write(0, 14, 'CEDULA')
                    ws.write(0, 15, 'CORREO INSTITUCIONAL')
                    ws.write(0, 16, u'CATEGORIZACIÓN')
                    ws.write(0, 17, u'TIPO')
                    ws.write(0, 18, 'DEDICACION')
                    ws.write(0, 19, 'FACULTAD')
                    ws.write(0, 20, 'TIPO PROFESOR')
                    ws.write(0, 21, 'TITULO TERCER NIVEL')
                    ws.write(0, 22, 'TITULO MASTER')
                    ws.write(0, 23, 'TITULO PHD')
                    ws.write(0, 24, 'ETNIA')
                    ws.write(0, 25, 'SEXO')
                    ws.write(0, 26, 'LGTBI')
                    a = 0
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaestudiante = "select 'Docencia' as criterio,coor.nombre as facultad,per.apellido1, per.apellido2 , per.nombres as docente,  " \
                                      "null,null as nivel,null, cri.nombre as actividad, actdetdis.nombre as subactividades, actdetdis.desde as subactividades_fechadesde, actdetdis.hasta as subactividades_fechahasta, actdetdis.horas as subactividades_horas, null as materia,detdis.horas,us.username, td.nombre,  " \
                                      "(select cat.nombre from sga_categorizaciondocente cat   " \
                                      "where cat.id=dis.categoria_id ),null,per.cedula,per.emailinst,us.username,  " \
                                      "null as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                      "left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                      "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                      "where tc.persona_id=per.id  " \
                                      "and tit.nivel_id=4  " \
                                      "and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master ,  " \
                                      "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit   " \
                                      "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd, " \
                                      "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True) as etnia, " \
                                      "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi,  " \
                                      "(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                      "left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                      "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                      "where tc.persona_id=per.id  " \
                                      "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,   " \
                                      "(select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0,0  " \
                                      "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd,   " \
                                      "sga_tiempodedicaciondocente td,   " \
                                      "sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us, sga_actividaddetalledistributivo actdetdis  " \
                                      "where dis.profesor_id=pro.id   " \
                                      "and td.id=dis.dedicacion_id   " \
                                      "and pro.persona_id=per.id    " \
                                      "and per.usuario_id=us.id   " \
                                      "and dis.coordinacion_id=coor.id   " \
                                      "and dis.id=detdis.distributivo_id   " \
                                      "and detdis.criteriodocenciaperiodo_id=critd.id   " \
                                      "and critd.criterio_id=cri.id   " \
                                      "and detdis.criteriodocenciaperiodo_id is not null   " \
                                      "and actdetdis.criterio_id = detdis.id " \
                                      "and dis.periodo_id= '" + periodo + "' and cri.id not in (15,16,17,18) " \
                                                                          "union all   " \
                                                                          "select distinct 'Investigacion' as criterio,tables.facultad,tables.apellido1,tables.apellido2,tables.docente,null, " \
                                                                          "null,null,tables.actividad,detdistribu.nombre as subactividades, " \
                                                                          "detdistribu.desde as subactividades_fechadesde, " \
                                                                          "detdistribu.hasta as subactividades_fechahasta,detdistribu.horas as subactividades_horas,null,tables.horas, " \
                                                                          "tables.username,tables.nombre,tables.nocategoriadocente,null,tables.cedula, " \
                                                                          "tables.emailinst,tables.user1,tables.tipoprofesor,tables.master,tables.phd,tables.etnia, " \
                                                                          "tables.sexo,tables.lgtbi,tables.tercernivel,null,tables.zeta,tables.idinvestigacion " \
                                                                          "from (select '' as ade,coor.nombre as facultad,per.apellido1 , per.apellido2, per.nombres as docente, " \
                                                                          "cri.nombre as actividad,detdis.horas,us.username , td.nombre, " \
                                                                          "(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ) as nocategoriadocente,  " \
                                                                          " per.cedula,per.emailinst,us.username as user1,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')   FROM sga_titulacion tc  " \
                                                                          "  left join sga_titulo tit  on tc.titulo_id=tit.id   " \
                                                                          "  left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                                                          "  where tc.persona_id=per.id  " \
                                                                          "  and tit.nivel_id=4  " \
                                                                          "  and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master ,  " \
                                                                          "  (SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit " \
                                                                          "  where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd, " \
                                                                          "  (select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia,  " \
                                                                          "  (select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi,  " \
                                                                          "  (SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                                                          "  left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                                                          "  left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                                                          "  where tc.persona_id=per.id  " \
                                                                          "  and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,   " \
                                                                          "  (select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0 as zeta,detdis.id as idinvestigacion " \
                                                                          "  from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd,   " \
                                                                          "  sga_tiempodedicaciondocente td,   " \
                                                                          "  sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                          "  where dis.profesor_id=pro.id " \
                                                                          "  and td.id=dis.dedicacion_id   " \
                                                                          "  and pro.persona_id=per.id " \
                                                                          "  and per.usuario_id=us.id  " \
                                                                          "  and dis.coordinacion_id=coor.id " \
                                                                          "  and dis.id=detdis.distributivo_id   " \
                                                                          "  and detdis.criterioinvestigacionperiodo_id=critd.id   " \
                                                                          "  and critd.criterio_id=cri.id   " \
                                                                          "  and detdis.criterioinvestigacionperiodo_id is not null   " \
                                                                          "  and dis.periodo_id= '" + periodo + "' " \
                                                                                                                "  ) as tables " \
                                                                                                                "left join sga_actividaddetalledistributivo detdistribu on detdistribu.criterio_id=idinvestigacion " \
                                                                                                                "union all   " \
                                                                                                                "select distinct 'Gestion' as criterio,tables.facultad,tables.apellido1,tables.apellido2,tables.docente,null, " \
                                                                                                                "null,null,tables.actividad,detdistribu.nombre as subactividades, " \
                                                                                                                "detdistribu.desde as subactividades_fechadesde, " \
                                                                                                                "detdistribu.hasta as subactividades_fechahasta,detdistribu.horas as subactividades_horas,null,tables.horas, " \
                                                                                                                "tables.username,tables.nombre,tables.nocategoriadocente,null,tables.cedula, " \
                                                                                                                "tables.emailinst,tables.user1,tables.tipoprofesor,tables.master,tables.phd,tables.etnia, " \
                                                                                                                "tables.sexo,tables.lgtbi,tables.tercernivel,null,tables.zeta,tables.idinvestigacion " \
                                                                                                                "from (select '' as ade,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente, " \
                                                                                                                "cri.nombre as actividad, detdis.horas,us.username , td.nombre as nombre, " \
                                                                                                                "(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ) as nocategoriadocente, " \
                                                                                                                " per.cedula,per.emailinst,us.username as user1,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                                                                " left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                                                                " left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                                                                " where tc.persona_id=per.id " \
                                                                                                                " and tit.nivel_id=4 " \
                                                                                                                " and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master , " \
                                                                                                                " (SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit " \
                                                                                                                " where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd, " \
                                                                                                                " (select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia, " \
                                                                                                                " (select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi, " \
                                                                                                                " (SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                                                                "left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                                                                "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                                                                "where tc.persona_id=per.id " \
                                                                                                                "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel, " \
                                                                                                                "(select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0 as zeta,detdis.id as idinvestigacion " \
                                                                                                                "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                                                                                "sga_tiempodedicaciondocente td, " \
                                                                                                                "sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                                                                "where dis.profesor_id=pro.id " \
                                                                                                                "and td.id=dis.dedicacion_id " \
                                                                                                                "and pro.persona_id=per.id " \
                                                                                                                "and per.usuario_id=us.id " \
                                                                                                                "and dis.coordinacion_id=coor.id " \
                                                                                                                "and dis.id=detdis.distributivo_id " \
                                                                                                                "and detdis.criteriogestionperiodo_id=critd.id " \
                                                                                                                "and critd.criterio_id=cri.id " \
                                                                                                                "and detdis.criteriogestionperiodo_id is not null " \
                                                                                                                "and dis.periodo_id= '" + periodo + "') as tables " \
                                                                                                                                                    "left join sga_actividaddetalledistributivo detdistribu on detdistribu.criterio_id=idinvestigacion " \
                                                                                                                                                    "union all " \
                                                                                                                                                    "select 'Materias' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente,   " \
                                                                                                                                                    "mat.paralelo,nmalla.nombre as nivel,carr.nombre || ' ' || carr.mencion as carreras, null as actividad, null as subactividades, null as subactividades_fechadesde, null as subactividades_fechahasta, null as subactividades_horas, asig.nombre as materia,pmat.hora,us.username ,  " \
                                                                                                                                                    "td.nombre,(select cat.nombre from sga_categorizaciondocente cat, sga_profesordistributivohoras dist  " \
                                                                                                                                                    "where cat.id=dist.categoria_id and dist.periodo_id= '" + periodo + "'  and dist.profesor_id=pro.id ),ses.nombre as sesion,  " \
                                                                                                                                                                                                                        "per.cedula,per.emailinst,us.username,tipro.nombre as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                                                                                                                                                                                                        " left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                                                                                                                                                                                                        "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                                                                                                                                                                                                        "where tc.persona_id=per.id  " \
                                                                                                                                                                                                                        "and tit.nivel_id=4  " \
                                                                                                                                                                                                                        "and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master ,  " \
                                                                                                                                                                                                                        "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
                                                                                                                                                                                                                        "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd,   " \
                                                                                                                                                                                                                        "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia,   " \
                                                                                                                                                                                                                        "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi,  " \
                                                                                                                                                                                                                        "(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                                                                                                                                                                                                        "left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                                                                                                                                                                                                        "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                                                                                                                                                                                                        "where tc.persona_id=per.id  " \
                                                                                                                                                                                                                        "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,   " \
                                                                                                                                                                                                                        "(select pt1.nombre from sga_profesortipo pt1, sga_profesordistributivohoras dist where pt1.id=dist.nivelcategoria_id and dist.periodo_id= '" + periodo + "'  and dist.profesor_id=pro.id) as tipoprofesor,extract(year from malla.inicio) as anio,0  " \
                                                                                                                                                                                                                                                                                                                                                                                  "from sga_profesormateria pmat,sga_materia mat,sga_nivel niv,sga_profesor pro,sga_persona per,   " \
                                                                                                                                                                                                                                                                                                                                                                                  "sga_asignaturamalla asimalla,sga_malla malla,sga_carrera carr,sga_asignatura asig,   " \
                                                                                                                                                                                                                                                                                                                                                                                  "sga_nivelmalla nmalla,auth_user us,sga_coordinacion_carrera corcar,sga_coordinacion coor,   " \
                                                                                                                                                                                                                                                                                                                                                                                  "sga_tiempodedicaciondocente td ,sga_sesion ses, sga_tipoprofesor tipro   " \
                                                                                                                                                                                                                                                                                                                                                                                  "where pmat.profesor_id=pro.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and pro.persona_id=per.id    " \
                                                                                                                                                                                                                                                                                                                                                                                  "and per.usuario_id=us.id     " \
                                                                                                                                                                                                                                                                                                                                                                                  "and pro.dedicacion_id=td.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and pmat.materia_id=mat.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and mat.nivel_id=niv.id and niv.sesion_id=ses.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and mat.asignaturamalla_id=asimalla.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and asimalla.malla_id=malla.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and malla.carrera_id=carr.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and corcar.carrera_id=carr.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and corcar.coordinacion_id=coor.id and tipro.id not in (4)  " \
                                                                                                                                                                                                                                                                                                                                                                                  "and asimalla.asignatura_id=asig.id and asimalla.nivelmalla_id=nmalla.id and pmat.tipoprofesor_id=tipro.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and niv.periodo_id= '" + periodo + "'"
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, per[7])
                        ws.write(a, 1, per[30] if per[30] != 0 else '')
                        ws.write(a, 2, per[18])
                        ws.write(a, 3, per[6])
                        ws.write(a, 4, per[5])
                        ws.write(a, 5, per[8])
                        ws.write(a, 6, per[9])
                        ws.write(a, 7, per[10].strftime("%d/%m/%Y") if per[10] else '')
                        ws.write(a, 8, per[11].strftime("%d/%m/%Y") if per[11] else '')
                        ws.write(a, 9, per[12])
                        ws.write(a, 10, per[13])
                        ws.write(a, 11, per[14])
                        ws.write(a, 12, per[2] + ' ' + per[3] + ' ' + per[4])
                        ws.write(a, 13, per[0])
                        ws.write(a, 14, per[19])
                        ws.write(a, 15, per[21] + '@unemi.edu.ec')
                        ws.write(a, 16, per[17])
                        ws.write(a, 17, per[29])
                        ws.write(a, 18, per[16])
                        ws.write(a, 19, per[1])
                        ws.write(a, 20, per[22])
                        ws.write(a, 21, per[28])
                        ws.write(a, 22, per[23])
                        ws.write(a, 23, per[24])
                        ws.write(a, 24, per[25])
                        ws.write(a, 25, per[26])
                        if per[27]:
                            lgtbi = 'SI'
                        else:
                            lgtbi = 'NO'
                        ws.write(a, 26, lgtbi)
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportedocentes_con_estudiantes_discapacitados':
                try:
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte')
                    response = HttpResponse(content_type="application/ms-excel")
                    nombre_archivo = 'reporte_actividades_docente'
                    response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1, 10000).__str__() + '.xls'
                    style_title = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    style_title_2 = xlwt.easyxf('font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    cursor = connections['default'].cursor()
                    columns = [
                        # (u"N.", 1500),
                        # (u"CARRERA.", 1500),
                        # (u"MALLA", 1500),
                        # (u"SECCION", 12000),
                        # (u"NIVEL", 3000),
                        # (u"PARALELO", 3000),
                        # (u"MATERIAS", 3000),
                        # (u"HORAS", 3000),
                        # (u"APELLIDOS Y NOMBRES", 4000),
                        # (u"CRITERIO", 4000),
                        # (u"CORREO INSTITUCIONAL", 5000),
                        # (u"CATEGORIZACIÓN", 5000),
                        # (u"TIPO", 5000),
                        # (u"DEDICACION", 8000),
                        # (u"FACULTAD", 8000),
                        # (u"TIPO PROFESOR", 8000),
                        # (u"TITULO TERCER NIVEL", 8000),
                        # (u"TITULO MASTER", 8000),
                        # (u"TITULO PHD", 8000),
                        # (u"ETNIA", 8000),
                        # (u"SEXO", 2500),
                        # (u"LGTBI", 2500),
                        # (u"AULA ASIGNADA", 2500),
                        # (u"LABORATORIO ASIGNADA", 2500),
                        # (u"CUENTA CON ESTUDIANTES CON DISCPACIDADES", 2500),
                        # (u"TIPOS DISCAPACIDADES", 2500),
                        (u"APELLIDO PATERNO", 3500),
                        (u"APELLIDO MATERNO", 3500),
                        (u"NOMBRES", 5500),
                        (u"CEDULA", 3500),
                        (u"SEXO", 3000),
                        (u"EMAIL", 3000),
                        (u"TELEFONO", 3000),
                        (u"CONVENCIONAL", 3000),
                        (u"DEDICACION", 3000),
                        (u"COORDINACION", 5000),
                    ]
                    ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
                    ws.write_merge(1, 1, 0, len(columns), 'REPORTE DE DOCENTES CON ALUMNOS CON DISCAPACIDAD', style_title_2)
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num += 1
                    # actividades = ActividadDetalleDistributivo.objects.filter(criterio__criteriodocenciaperiodo__periodo_id=126,
                    #                                                           criterio__criteriodocenciaperiodo__isnull=False,
                    #                                                           criterio__criteriodocenciaperiodo__criterio__tipo=1).exclude(criterio__id__in=[15, 16, 17, 18])
                    # sql = f"""
                    #         SELECT
                    #             (carr.nombre || ' ' || carr.mencion )as carreras,
                    #             EXTRACT(YEAR FROM	 malla.inicio) AS anio,
                    #             ses.nombre AS sesion,
                    #             nmalla.nombre AS nivel,
                    #             mat.paralelo,
                    #             asig.nombre AS	actividad,
                    #             mat.horassemanales,
                    #             (per.apellido1||' ' ||per.apellido2 ||' ' ||per.nombres) as docente,
                    #             'Materias' AS criterio,
                    #             per.emailinst,
                    #             (SELECT cat.nombre
                    #                 FROM
                    #                     sga_categorizaciondocente cat,
                    #                     sga_profesordistributivohoras dist
                    #                 WHERE cat.id=dist.categoria_id AND dist.periodo_id={periodo.id} AND dist.profesor_id=pro.id ) categorizacion,
                    #             (SELECT	pt1.nombre
                    #                 FROM
                    #                     sga_profesortipo pt1,
                    #                     sga_profesordistributivohoras dist
                    #                 WHERE
                    #                     pt1.id=dist.nivelcategoria_id
                    #                     AND dist.periodo_id={periodo.id}
                    #                     AND dist.profesor_id=pro.id) AS tipoprofesor,
                    #             td.nombre dedicacion,
                    #             coor.nombre AS facultad,
                    #             tipro.nombre AS tipoprofesor,
                    #                     (SELECT ARRAY_TO_STRING(array_agg(tit.nombre || '-' || ins.nombre),',')
                    #                 FROM
                    #                     sga_titulacion tc
                    #                     LEFT JOIN sga_titulo tit  ON tc.titulo_id=tit.id
                    #                     LEFT JOIN sga_institucioneducacionsuperior ins  ON ins.id=tc.institucion_id
                    #                 WHERE
                    #                     tc.persona_id=per.id AND tit.nivel_id=3  AND tc.verisenescyt=TRUE) AS tercernivel,
                    #             (SELECT ARRAY_TO_STRING(array_agg(tit.nombre || '-' || ins.nombre),',')
                    #                 FROM
                    #                     sga_titulacion tc
                    #                     LEFT JOIN sga_titulo tit  ON tc.titulo_id=tit.id
                    #                     LEFT JOIN sga_institucioneducacionsuperior ins  ON ins.id=tc.institucion_id
                    #                 WHERE
                    #                     tc.persona_id=per.id AND tit.nivel_id=4 AND tit.grado_id IN(2, 5) AND tc.verisenescyt=TRUE) AS master,
                    #             (SELECT ARRAY_TO_STRING(array_agg(tit.nombre),',')
                    #                 FROM
                    #                     sga_titulacion tc ,sga_titulo tit
                    #                 WHERE
                    #                     tc.titulo_id=tit.id AND	tc.persona_id=per.id AND tit.nivel_id=4 AND tit.grado_id=1 AND tc.verisenescyt=TRUE) AS phd,
                    #             (select (raza.nombre)
                    #                 FROM
                    #                     sga_perfilinscripcion perfil,
                    #                     sga_raza raza
                    #                 WHERE perfil.raza_id=raza.id AND perfil.persona_id=per.id AND perfil.status=TRUE)  AS etnia,
                    #             (SELECT nombre FROM sga_sexo sexo WHERE sexo.id=per.sexo_id ) AS sexo,
                    #             per.lgtbi,
                    #             aula.nombres AS aulas,
                    #             laboratorio.nombres AS laboratorios,
                    #             discapacidad.tipos AS tipos_discapacidades
                    #
                    #         from
                    #             sga_profesormateria pmat,
                    #             sga_materia mat,
                    #             sga_nivel niv,
                    #             sga_profesor pro,
                    #             sga_persona per,
                    #             sga_asignaturamalla asimalla,
                    #             sga_malla malla,
                    #             sga_carrera carr,
                    #             sga_asignatura asig,
                    #             sga_nivelmalla nmalla,
                    #             auth_user us,
                    #             sga_coordinacion_carrera corcar,
                    #             sga_coordinacion coor,
                    #             sga_tiempodedicaciondocente td ,
                    #             sga_sesion ses,
                    #             sga_tipoprofesor tipro
                    #             LEFT JOIN LATERAL	(SELECT  array_to_string(array_agg(DISTINCT tipodiscapacidad.nombre ),',') tipos
                    #                 FROM
                    #                     sga_materiaasignada matasig
                    #                     INNER JOIN sga_matricula matr ON matr.id=matasig.matricula_id
                    #                     INNER JOIN sga_inscripcion inscripcion ON inscripcion.id=matr.inscripcion_id
                    #                     INNER JOIN sga_persona persona ON persona.id=inscripcion.persona_id
                    #                     INNER JOIN sga_perfilinscripcion perfilinsc ON perfilinsc.persona_id=persona.id
                    #                     INNER JOIN sga_discapacidad tipodiscapacidad ON tipodiscapacidad.id= perfilinsc.tipodiscapacidad_id
                    #                     WHERE
                    #                      matasig.materia_id=mat.id
                    #                      AND mat."status"=TRUE
                    #                      AND perfilinsc.tienediscapacidad=TRUE
                    #                 ) discapacidad ON TRUE
                    #             LEFT JOIN 	LATERAL(SELECT  array_to_string(array_agg( distinct aula.nombre ),',') nombres
                    #                     FROM
                    #                         sga_clase clase
                    #                         left JOIN sga_aula aula ON aula.id=clase.aula_id
                    #                         WHERE
                    #                             clase.materia_id=mat.id
                    #                             AND aula.tipo_id=1
                    #                          AND clase."status") aula ON TRUE
                    #             LEFT JOIN 	LATERAL(SELECT  array_to_string(array_agg( distinct aula.nombre ),',') nombres
                    #                 FROM
                    #                         sga_clase clase
                    #                         left JOIN sga_aula aula ON aula.id=clase.aula_id
                    #                         WHERE
                    #                             clase.materia_id=mat.id
                    #                             AND  aula.tipo_id=2
                    #                          AND clase."status") laboratorio ON TRUE
                    #         where
                    #             pmat.profesor_id=pro.id
                    #             and pro.persona_id=per.id
                    #             and per.usuario_id=us.id
                    #             and pro.dedicacion_id=td.id
                    #             and pmat.materia_id=mat.id
                    #             and mat.nivel_id=niv.id
                    #             and niv.sesion_id=ses.id
                    #             and mat.asignaturamalla_id=asimalla.id
                    #             and asimalla.malla_id=malla.id
                    #             and malla.carrera_id=carr.id
                    #             and corcar.carrera_id=carr.id
                    #             and corcar.coordinacion_id=coor.id
                    #             and tipro.id not in (4)
                    #             and asimalla.asignatura_id=asig.id
                    #             and asimalla.nivelmalla_id=nmalla.id
                    #             and pmat.tipoprofesor_id=tipro.id
                    #             and niv.periodo_id={periodo.id}
                    # """
                    sql = f"""SELECT DISTINCT perpro.apellido1, perpro.apellido2, perpro.nombres, perpro.cedula,
                            perpro.sexo_id, perpro.emailinst, perpro.telefono, perpro.telefono_conv, td.nombre dedicacion, coor.nombre
                             FROM sga_profesormateria pmat 
                            INNER JOIN sga_profesor pro ON pro.id=pmat.profesor_id 
                            INNER JOIN sga_persona perpro ON perpro.id=pro.persona_id 
                            INNER JOIN sga_materia mat ON mat.id=pmat.materia_id
                            INNER JOIN sga_materiaasignada matasig ON mat.id=matasig.materia_id
                            INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
                            INNER JOIN sga_matricula matri ON matri.id=matasig.matricula_id 
                            INNER JOIN sga_inscripcion inscripcion ON inscripcion.id=matri.inscripcion_id
                            INNER JOIN sga_persona persona ON persona.id=inscripcion.persona_id
                            INNER JOIN sga_perfilinscripcion perfilinsc ON perfilinsc.persona_id=persona.id
                            INNER JOIN sga_discapacidad tipodiscapacidad ON tipodiscapacidad.id= perfilinsc.tipodiscapacidad_id
                            INNER JOIN sga_tiempodedicaciondocente td ON pro.dedicacion_id = td.id
                            INNER JOIN sga_coordinacion coor ON coor.id=pro.coordinacion_id
                            WHERE niv.periodo_id = {periodo.id} AND mat."status"= TRUE  AND perfilinsc.tienediscapacidad= TRUE AND perfilinsc.verificadiscapacidad = TRUE 
                            AND matri.nivel_id=niv.id AND pro.coordinacion_id NOT IN (7, 9, 11) ORDER BY perpro.apellido1, perpro.apellido2"""
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    for indice, per in enumerate(results):
                        ws.write(row_num, 0, "%s" % per[0] or '')
                        ws.write(row_num, 1, per[1] if per[1] != 0 else '')
                        ws.write(row_num, 2, "%s" % per[2] or '')
                        ws.write(row_num, 3, "%s" % per[3] or '')
                        ws.write(row_num, 4, 'MUJER' if int(per[4])==1 else 'HOMBRE')
                        ws.write(row_num, 5, "%s" % per[5] or '')
                        ws.write(row_num, 6, "%s" % per[6] or '')
                        ws.write(row_num, 7, "%s" % per[7] or '')
                        ws.write(row_num, 8, "%s" % per[8] or '')
                        ws.write(row_num, 9, "%s" % per[9] or '')
                        # ws.write(row_num, 11, "%s" % per[11] or '')
                        # ws.write(row_num, 12, "%s" % per[12] or '')
                        # ws.write(row_num, 13, "%s" % per[13] or '')
                        # ws.write(row_num, 14, "%s" % per[14] or '')
                        # ws.write(row_num, 15, "%s" % per[15] or '')
                        # ws.write(row_num, 16, "%s" % per[16] or '')
                        # ws.write(row_num, 17, "%s" % per[17] or '')
                        # ws.write(row_num, 18, "%s" % per[18] or '')
                        # ws.write(row_num, 19, "%s" % per[19] or '')
                        # ws.write(row_num, 20, ('SI' if per[20] else 'NO'))
                        # ws.write(row_num, 21, "%s" % per[21] or '')
                        # ws.write(row_num, 22, "%s" % per[22] or '')
                        # ws.write(row_num, 23, "%s" % ('SI' if per[23] else 'NO'))
                        # ws.write(row_num, 24, per[23] or '')
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'asignacion_carrera_distributivo_docentes':

                try:

                    __author__ = 'Unemi'
                    periodo = request.GET['periodo']
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('actividades_carrera_docentes')
                    ws.set_column(0, 0, 50)
                    ws.set_column(1, 3, 15)
                    ws.set_column(4, 4, 50)
                    ws.set_column(5, 8, 40)
                    ws.set_column(9, 10, 60)
                    ws.set_column(11, 13, 20)
                    ws.set_column(14, 14, 30)
                    ws.set_column(15, 15, 10)
                    formatoceldatitulo = workbook.add_format({'text_wrap': True, 'bg_color': 'silver', 'align': 'center'})
                    formatoceldacenter = workbook.add_format({'text_wrap': True, 'valign': 'vcenter', 'align': 'center'})

                    ws.write('A1', 'APELLIDOS Y NOMBRES', formatoceldatitulo)
                    ws.write('B1', 'CEDULA', formatoceldatitulo)
                    ws.write('C1', 'GENERO', formatoceldatitulo)
                    ws.write('D1', 'LGTBI', formatoceldatitulo)
                    ws.write('E1', 'CORREO INSTITUCIONAL', formatoceldatitulo)
                    ws.write('F1', 'CATEGORIZACION', formatoceldatitulo)
                    ws.write('G1', 'TIPO', formatoceldatitulo)
                    ws.write('H1', 'DEDICACION', formatoceldatitulo)
                    ws.write('I1', 'FACULTAD', formatoceldatitulo)
                    ws.write('J1', 'ACTIVIDADES', formatoceldatitulo)
                    ws.write('K1', 'SUBACTIVIDADES', formatoceldatitulo)
                    ws.write('L1', 'SUBACTIVIDADES FECHA DESDE', formatoceldatitulo)
                    ws.write('M1', 'SUBACTIVIDADES FECHA FIN', formatoceldatitulo)
                    ws.write('N1', 'SUBACTIVIDADES HORAS', formatoceldatitulo)
                    ws.write('O1', 'CARRERA', formatoceldatitulo)
                    ws.write('P1', 'HORAS', formatoceldatitulo)

                    actividades = ActividadDetalleDistributivo.objects.select_related("criterio", "criterio__distributivo", "criterio__distributivo__profesor", "criterio__distributivo__profesor__persona",

                                                                                      "criterio__distributivo__profesor__persona__sexo", "criterio__distributivo__dedicacion", "criterio__distributivo__categoria",

                                                                                      "criterio__distributivo__coordinacion", "criterio__distributivo__nivelcategoria", "criterio__criteriodocenciaperiodo__criterio").annotate(per_genero=F("criterio__distributivo__profesor__persona__sexo__nombre"),
                                                                                                                                                                                                                                per_lgtbi=F("criterio__distributivo__profesor__persona__lgtbi"),
                                                                                                                                                                                                                                per_nombres=Concat('criterio__distributivo__profesor__persona__apellido1', V(' '), 'criterio__distributivo__profesor__persona__apellido2', V(' '), 'criterio__distributivo__profesor__persona__nombres'),
                                                                                                                                                                                                                                per_cedula=F("criterio__distributivo__profesor__persona__cedula"),
                                                                                                                                                                                                                                per_email_inst=F("criterio__distributivo__profesor__persona__emailinst"),
                                                                                                                                                                                                                                prof_dedicacion=F("criterio__distributivo__dedicacion__nombre"),
                                                                                                                                                                                                                                prof_categorizacion=F("criterio__distributivo__categoria__nombre"),
                                                                                                                                                                                                                                prof_facultad=F("criterio__distributivo__coordinacion__nombre"),
                                                                                                                                                                                                                                prof_tipo_profesor=F("criterio__distributivo__nivelcategoria__nombre"),
                                                                                                                                                                                                                                dist_sub_actividad=F("nombre"),
                                                                                                                                                                                                                                dist_actividad=F("criterio__criteriodocenciaperiodo__criterio__nombre"),
                                                                                                                                                                                                                                dist_sub_actividad_hora=F("horas"),
                                                                                                                                                                                                                                dist_sub_fecha_desde=F("desde"),
                                                                                                                                                                                                                                dist_sub_fecha_hasta=F("hasta"),
                                                                                                                                                                                                                                id_act_det_dist=F("id")) \
                        .values("per_genero", "per_lgtbi", "per_nombres", "per_cedula", "per_email_inst", "prof_dedicacion", "prof_categorizacion", "prof_facultad", "prof_tipo_profesor", "dist_actividad", "dist_sub_actividad", "dist_sub_actividad_hora", "dist_sub_fecha_desde", "dist_sub_fecha_hasta", "id_act_det_dist") \
                        .filter(criterio__distributivo__periodo=periodo, status=True)

                    row_num = 1
                    for registro in actividades:
                        if registro['per_lgtbi']:
                            campo_lgtbi = 'SI'
                        else:
                            campo_lgtbi = 'NO'

                        if registro['dist_actividad']:
                            campo_relleno_nulo = registro['dist_actividad']

                        else:
                            campo_relleno_nulo = registro['dist_sub_actividad']

                        carreras_horas_actividades = ActividadDetalleDistributivoCarrera.objects.select_related('actividaddetalle', 'carrera', 'actividaddetalle__criterio', 'actividaddetalle__criterio__distributivo__profesor') \
                            .annotate(carrera_nombre=F('carrera__nombre')) \
                            .values('carrera_nombre', 'horas').filter(actividaddetalle__id=registro['id_act_det_dist'])

                        if carreras_horas_actividades.count() > 1:
                            cantidad_filas_agg = carreras_horas_actividades.count()
                            ws.merge_range('A' + str(row_num + 1) + ':A' + str(row_num + cantidad_filas_agg), str(registro['per_nombres']), formatoceldacenter)
                            ws.merge_range('B' + str(row_num + 1) + ':B' + str(row_num + cantidad_filas_agg), str(registro['per_cedula']), formatoceldacenter)
                            ws.merge_range('C' + str(row_num + 1) + ':C' + str(row_num + cantidad_filas_agg), str(registro['per_genero']), formatoceldacenter)
                            ws.merge_range('D' + str(row_num + 1) + ':D' + str(row_num + cantidad_filas_agg), str(campo_lgtbi), formatoceldacenter)
                            ws.merge_range('E' + str(row_num + 1) + ':E' + str(row_num + cantidad_filas_agg), str(registro['per_email_inst']), formatoceldacenter)
                            ws.merge_range('F' + str(row_num + 1) + ':F' + str(row_num + cantidad_filas_agg), str(registro['prof_categorizacion']), formatoceldacenter)
                            ws.merge_range('G' + str(row_num + 1) + ':G' + str(row_num + cantidad_filas_agg), str(registro['prof_tipo_profesor']), formatoceldacenter)
                            ws.merge_range('H' + str(row_num + 1) + ':H' + str(row_num + cantidad_filas_agg), str(registro['prof_dedicacion']), formatoceldacenter)
                            ws.merge_range('I' + str(row_num + 1) + ':I' + str(row_num + cantidad_filas_agg), str(registro['prof_facultad']), formatoceldacenter)
                            ws.merge_range('J' + str(row_num + 1) + ':J' + str(row_num + cantidad_filas_agg), str(campo_relleno_nulo), formatoceldacenter)
                            ws.merge_range('K' + str(row_num + 1) + ':K' + str(row_num + cantidad_filas_agg), str(registro['dist_sub_actividad']), formatoceldacenter)
                            ws.merge_range('L' + str(row_num + 1) + ':L' + str(row_num + cantidad_filas_agg), str(registro['dist_sub_fecha_desde']), formatoceldacenter)
                            ws.merge_range('M' + str(row_num + 1) + ':M' + str(row_num + cantidad_filas_agg), str(registro['dist_sub_fecha_hasta']), formatoceldacenter)
                            ws.merge_range('N' + str(row_num + 1) + ':N' + str(row_num + cantidad_filas_agg), int(registro['dist_sub_actividad_hora']), formatoceldacenter)

                            for carrera_hora in carreras_horas_actividades:
                                ws.write(row_num, 14, carrera_hora['carrera_nombre'], formatoceldacenter)
                                ws.write(row_num, 15, carrera_hora['horas'], formatoceldacenter)
                                row_num += 1

                        elif carreras_horas_actividades.count() == 1:
                            ws.write(row_num, 0, str(registro['per_nombres']), formatoceldacenter)
                            ws.write(row_num, 1, str(registro['per_cedula']), formatoceldacenter)
                            ws.write(row_num, 2, str(registro['per_genero']), formatoceldacenter)
                            ws.write(row_num, 3, str(campo_lgtbi), formatoceldacenter)
                            ws.write(row_num, 4, str(registro['per_email_inst']), formatoceldacenter)
                            ws.write(row_num, 5, str(registro['prof_categorizacion']), formatoceldacenter)
                            ws.write(row_num, 6, str(registro['prof_tipo_profesor']), formatoceldacenter)
                            ws.write(row_num, 7, str(registro['prof_dedicacion']), formatoceldacenter)
                            ws.write(row_num, 8, str(registro['prof_facultad']), formatoceldacenter)
                            ws.write(row_num, 9, str(campo_relleno_nulo), formatoceldacenter)
                            ws.write(row_num, 10, str(registro['dist_sub_actividad']), formatoceldacenter)
                            ws.write(row_num, 11, str(registro['dist_sub_fecha_desde']), formatoceldacenter)
                            ws.write(row_num, 12, str(registro['dist_sub_fecha_hasta']), formatoceldacenter)
                            ws.write_number(row_num, 13, int(registro['dist_sub_actividad_hora']), formatoceldacenter)

                            for carrera_hora in carreras_horas_actividades:
                                ws.write(row_num, 14, carrera_hora['carrera_nombre'], formatoceldacenter)
                                ws.write(row_num, 15, carrera_hora['horas'], formatoceldacenter)
                            row_num += 1

                        else:
                            ws.write(row_num, 0, str(registro['per_nombres']), formatoceldacenter)
                            ws.write(row_num, 1, str(registro['per_cedula']), formatoceldacenter)
                            ws.write(row_num, 2, str(registro['per_genero']), formatoceldacenter)
                            ws.write(row_num, 3, str(campo_lgtbi), formatoceldacenter)
                            ws.write(row_num, 4, str(registro['per_email_inst']), formatoceldacenter)
                            ws.write(row_num, 5, str(registro['prof_categorizacion']), formatoceldacenter)
                            ws.write(row_num, 6, str(registro['prof_tipo_profesor']), formatoceldacenter)
                            ws.write(row_num, 7, str(registro['prof_dedicacion']), formatoceldacenter)
                            ws.write(row_num, 8, str(registro['prof_facultad']), formatoceldacenter)
                            ws.write(row_num, 9, str(campo_relleno_nulo), formatoceldacenter)
                            ws.write(row_num, 10, str(registro['dist_sub_actividad']), formatoceldacenter)
                            ws.write(row_num, 11, str(registro['dist_sub_fecha_desde']), formatoceldacenter)
                            ws.write(row_num, 12, str(registro['dist_sub_fecha_hasta']), formatoceldacenter)
                            ws.write_number(row_num, 13, int(registro['dist_sub_actividad_hora']), formatoceldacenter)
                            ws.write(row_num, 14, "-", formatoceldacenter)
                            ws.write(row_num, 15, "-", formatoceldacenter)
                            row_num += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_actividades_carrera_distributivo_docentes' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response


                except Exception as ex:
                    pass

            elif action == 'tutoriasfacultadespdf':
                try:
                    # data['tutorias'] = AvTutorias.objects.filter(materia__asignaturamalla__malla__carrera__coordinacion=coordinacion,  materia__nivel__periodo_id=periodo.id).order_by("materia__asignaturamalla__malla__carrera").distinct()
                    data['coordinaciones'] = Coordinacion.objects.filter(pk__in=[1, 2, 3, 4, 5], status=True)
                    data['periodo'] = periodo
                    data['fecha'] = datetime.now().date()
                    return conviert_html_to_pdf(
                        'adm_criteriosactividadesdocente/reporte_tutoriafacultades_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'totalactividadesdocentesmaterias_conevidencias':
                try:
                    periodo = request.GET['periodo']
                    cursor = connections['default'].cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_actividaddocente_materia.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf(
                        'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    # ws.write_merge(0, 0, 0, 5, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 10000
                    ws.col(1).width = 4000
                    ws.col(2).width = 4000
                    ws.col(3).width = 4000
                    ws.col(4).width = 2000
                    ws.col(5).width = 6000
                    ws.col(6).width = 6000
                    ws.col(7).width = 3000
                    ws.col(8).width = 3000
                    ws.col(9).width = 2000
                    ws.col(10).width = 6000
                    ws.col(11).width = 2000
                    ws.col(12).width = 2000
                    ws.col(13).width = 6000
                    ws.col(14).width = 2000
                    ws.col(15).width = 10000
                    ws.col(16).width = 3000
                    ws.col(17).width = 3000
                    ws.col(18).width = 6000
                    ws.col(19).width = 6000
                    ws.col(20).width = 4000
                    ws.col(21).width = 6000
                    ws.col(22).width = 4000
                    ws.col(23).width = 10000
                    ws.col(24).width = 10000
                    ws.col(25).width = 5000
                    ws.col(26).width = 5000
                    ws.col(27).width = 5000
                    ws.col(28).width = 5000
                    ws.col(29).width = 5000
                    ws.write(0, 0, 'CARRERA')
                    ws.write(0, 1, 'MALLA')
                    ws.write(0, 2, 'SECCION')
                    ws.write(0, 3, 'NIVEL')
                    ws.write(0, 4, 'PARALELO')
                    ws.write(0, 5, 'ACTIVIDADES')
                    ws.write(0, 6, 'SUBACTIVIDADES')
                    ws.write(0, 7, 'SUBACTIVIDADES FECHA DESDE')
                    ws.write(0, 8, 'SUBACTIVIDADES FECHA FIN')
                    ws.write(0, 9, 'SUBACTIVIDADES HORAS')
                    ws.write(0, 10, 'DESCRIPCION EVIDENCIA')
                    ws.write(0, 11, 'FECHAS DESDE EVIDENCIAS')
                    ws.write(0, 12, 'FECHAS HASTA EVIDENCIAS')
                    ws.write(0, 13, 'MATERIAS')
                    ws.write(0, 14, 'HORAS')
                    ws.write(0, 15, 'APELLIDOS Y NOMBRES')
                    ws.write(0, 16, 'CRITERIO')
                    ws.write(0, 17, 'CEDULA')
                    ws.write(0, 18, 'CORREO INSTITUCIONAL')
                    ws.write(0, 19, u'CATEGORIZACIÓN')
                    ws.write(0, 20, u'TIPO')
                    ws.write(0, 21, 'DEDICACION')
                    ws.write(0, 22, 'FACULTAD')
                    ws.write(0, 23, 'TIPO PROFESOR')
                    ws.write(0, 24, 'TITULO TERCER NIVEL')
                    ws.write(0, 25, 'TITULO MASTER')
                    ws.write(0, 26, 'TITULO PHD')
                    ws.write(0, 27, 'ETNIA')
                    ws.write(0, 28, 'SEXO')
                    ws.write(0, 29, 'LGTBI')
                    a = 0
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaestudiante = "select 'Docencia' as criterio,coor.nombre as facultad,per.apellido1, per.apellido2 , per.nombres as docente,  " \
                                      "null,null as nivel,null, cri.nombre as actividad, actdetdis.nombre as subactividades, actdetdis.desde as subactividades_fechadesde, actdetdis.hasta as subactividades_fechahasta, actdetdis.horas as subactividades_horas, null as evidencias_actividad, null as evidencias_desde, null as evidencias_hasta, null as materia,detdis.horas,us.username, td.nombre,  " \
                                      "(select cat.nombre from sga_categorizaciondocente cat   " \
                                      "where cat.id=dis.categoria_id ),null,per.cedula,per.emailinst,us.username,  " \
                                      "null as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                      "left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                      "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                      "where tc.persona_id=per.id  " \
                                      "and tit.nivel_id=4  " \
                                      "and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master ,  " \
                                      "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit   " \
                                      "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd, " \
                                      "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True) as etnia, " \
                                      "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi,  " \
                                      "(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                      "left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                      "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                      "where tc.persona_id=per.id  " \
                                      "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,   " \
                                      "(select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0,0  " \
                                      "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd,   " \
                                      "sga_tiempodedicaciondocente td,   " \
                                      "sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us, sga_actividaddetalledistributivo actdetdis  " \
                                      "where dis.profesor_id=pro.id   " \
                                      "and td.id=dis.dedicacion_id   " \
                                      "and pro.persona_id=per.id    " \
                                      "and per.usuario_id=us.id   " \
                                      "and dis.coordinacion_id=coor.id   " \
                                      "and dis.id=detdis.distributivo_id   " \
                                      "and detdis.criteriodocenciaperiodo_id=critd.id   " \
                                      "and critd.criterio_id=cri.id   " \
                                      "and detdis.criteriodocenciaperiodo_id is not null   " \
                                      "and actdetdis.criterio_id = detdis.id " \
                                      "and dis.periodo_id= '" + periodo + "' and cri.id not in (15,16,17,18) " \
                                                                          "union all   " \
                                                                          "select distinct 'Investigacion' as criterio,tables.facultad,tables.apellido1,tables.apellido2,tables.docente,null, " \
                                                                          "null,null,tables.actividad,detdistribu.nombre as subactividades, " \
                                                                          "detdistribu.desde as subactividades_fechadesde, " \
                                                                          "detdistribu.hasta as subactividades_fechahasta,detdistribu.horas as subactividades_horas,eviactdistribu.actividad as evidencias_actividad, eviactdistribu.desde as evidencias_desde, eviactdistribu.hasta as evidencias_hasta, null,tables.horas, " \
                                                                          "tables.username,tables.nombre,tables.nocategoriadocente,tables.id_subactividades,null,tables.cedula, " \
                                                                          "tables.emailinst,tables.user1,tables.tipoprofesor,tables.master,tables.phd,tables.etnia, " \
                                                                          "tables.sexo,tables.lgtbi,tables.tercernivel,null,tables.zeta,tables.idinvestigacion " \
                                                                          "from (select '' as ade,coor.nombre as facultad,per.apellido1 , per.apellido2, per.nombres as docente, " \
                                                                          "cri.nombre as actividad,detdis.horas,us.username , td.nombre, " \
                                                                          "(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ) as nocategoriadocente,  " \
                                                                          " per.cedula,per.emailinst,us.username as user1,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')   FROM sga_titulacion tc  " \
                                                                          "  left join sga_titulo tit  on tc.titulo_id=tit.id   " \
                                                                          "  left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                                                          "  where tc.persona_id=per.id  " \
                                                                          "  and tit.nivel_id=4  " \
                                                                          "  and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master ,  " \
                                                                          "  (SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit " \
                                                                          "  where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd, " \
                                                                          "  (select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia,  " \
                                                                          "  (select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi,  " \
                                                                          "  (SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                                                          "  left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                                                          "  left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                                                          "  where tc.persona_id=per.id  " \
                                                                          "  and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,   " \
                                                                          "  (select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0 as zeta,detdis.id as idinvestigacion " \
                                                                          "  from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd,   " \
                                                                          "  sga_tiempodedicaciondocente td,   " \
                                                                          "  sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                          "  where dis.profesor_id=pro.id " \
                                                                          "  and td.id=dis.dedicacion_id   " \
                                                                          "  and pro.persona_id=per.id " \
                                                                          "  and per.usuario_id=us.id  " \
                                                                          "  and dis.coordinacion_id=coor.id " \
                                                                          "  and dis.id=detdis.distributivo_id   " \
                                                                          "  and detdis.criterioinvestigacionperiodo_id=critd.id   " \
                                                                          "  and critd.criterio_id=cri.id   " \
                                                                          "  and detdis.criterioinvestigacionperiodo_id is not null   " \
                                                                          "  and dis.periodo_id= '" + periodo + "' " \
                                                                                                                "  ) as tables " \
                                                                                                                "left join sga_actividaddetalledistributivo detdistribu on detdistribu.criterio_id=idinvestigacion " \
                                                                                                                "left join sga_evidenciaactividaddetalledistributivo eviactdistribu on eviactdistribu.criterio_id=idinvestigacion " \
                                                                                                                "union all   " \
                                                                                                                "select distinct 'Gestion' as criterio,tables.facultad,tables.apellido1,tables.apellido2,tables.docente,null, " \
                                                                                                                "null,null,tables.actividad,detdistribu.nombre as subactividades, " \
                                                                                                                "detdistribu.desde as subactividades_fechadesde, " \
                                                                                                                "detdistribu.hasta as subactividades_fechahasta,detdistribu.horas as subactividades_horas, eviactdistributivo.actividad as evidencias_actividad, eviactdistributivo.desde as evidencias_desde, eviactdistributivo.hasta as evidencias_hasta, null,tables.horas, " \
                                                                                                                "tables.username,tables.nombre,tables.nocategoriadocente,null,tables.cedula, " \
                                                                                                                "tables.emailinst,tables.user1,tables.tipoprofesor,tables.master,tables.phd,tables.etnia, " \
                                                                                                                "tables.sexo,tables.lgtbi,tables.tercernivel,null,tables.zeta,tables.idinvestigacion " \
                                                                                                                "from (select '' as ade,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente, " \
                                                                                                                "cri.nombre as actividad, detdis.horas,us.username , td.nombre as nombre, " \
                                                                                                                "(select cat.nombre from sga_categorizaciondocente cat where cat.id=dis.categoria_id ) as nocategoriadocente, " \
                                                                                                                " per.cedula,per.emailinst,us.username as user1,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                                                                " left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                                                                " left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                                                                " where tc.persona_id=per.id " \
                                                                                                                " and tit.nivel_id=4 " \
                                                                                                                " and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master , " \
                                                                                                                " (SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit " \
                                                                                                                " where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd, " \
                                                                                                                " (select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia, " \
                                                                                                                " (select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi, " \
                                                                                                                " (SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc " \
                                                                                                                "left join sga_titulo tit  on tc.titulo_id=tit.id " \
                                                                                                                "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id " \
                                                                                                                "where tc.persona_id=per.id " \
                                                                                                                "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel, " \
                                                                                                                "(select pt1.nombre from sga_profesortipo pt1 where pt1.id=dis.nivelcategoria_id) as tipoprofesor,0 as zeta,detdis.id as idinvestigacion " \
                                                                                                                "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                                                                                "sga_tiempodedicaciondocente td, " \
                                                                                                                "sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                                                                "where dis.profesor_id=pro.id " \
                                                                                                                "and td.id=dis.dedicacion_id " \
                                                                                                                "and pro.persona_id=per.id " \
                                                                                                                "and per.usuario_id=us.id " \
                                                                                                                "and dis.coordinacion_id=coor.id " \
                                                                                                                "and dis.id=detdis.distributivo_id " \
                                                                                                                "and detdis.criteriogestionperiodo_id=critd.id " \
                                                                                                                "and critd.criterio_id=cri.id " \
                                                                                                                "and detdis.criteriogestionperiodo_id is not null " \
                                                                                                                "and dis.periodo_id= '" + periodo + "') as tables " \
                                                                                                                                                    "left join sga_actividaddetalledistributivo detdistribu on detdistribu.criterio_id=idinvestigacion " \
                                                                                                                                                    "left join sga_evidenciaactividaddetalledistributivo eviactdistributivo on eviactdistributivo.criterio_id=idinvestigacion " \
                                                                                                                                                    "union all " \
                                                                                                                                                    "select 'Materias' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente,   " \
                                                                                                                                                    "mat.paralelo,nmalla.nombre as nivel,carr.nombre || ' ' || carr.mencion as carreras, null as actividad, null as subactividades, null as subactividades_fechadesde, null as subactividades_fechahasta, null as subactividades_horas, null as evidencias_actividad, null as evidencias_desde, null as evidencias_hasta, asig.nombre as materia,mat.horassemanales,us.username ,  " \
                                                                                                                                                    "td.nombre,(select cat.nombre from sga_categorizaciondocente cat, sga_profesordistributivohoras dist  " \
                                                                                                                                                    "where cat.id=dist.categoria_id and dist.periodo_id= '" + periodo + "'  and dist.profesor_id=pro.id ),ses.nombre as sesion,  " \
                                                                                                                                                                                                                        "per.cedula,per.emailinst,us.username,tipro.nombre as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                                                                                                                                                                                                        " left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                                                                                                                                                                                                        "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                                                                                                                                                                                                        "where tc.persona_id=per.id  " \
                                                                                                                                                                                                                        "and tit.nivel_id=4  " \
                                                                                                                                                                                                                        "and tit.grado_id in(2, 5) and tc.verisenescyt=true) as master ,  " \
                                                                                                                                                                                                                        "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
                                                                                                                                                                                                                        "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verisenescyt=true) as phd,   " \
                                                                                                                                                                                                                        "(select (raza.nombre) from sga_perfilinscripcion perfil,sga_raza raza where perfil.raza_id=raza.id and perfil.persona_id=per.id and perfil.status=True)  as etnia,   " \
                                                                                                                                                                                                                        "(select nombre from sga_sexo sexo where sexo.id=per.sexo_id ) as sexo,per.lgtbi,  " \
                                                                                                                                                                                                                        "(SELECT array_to_string(array_agg(tit.nombre || '-' || ins.nombre),',')  FROM sga_titulacion tc  " \
                                                                                                                                                                                                                        "left join sga_titulo tit  on tc.titulo_id=tit.id  " \
                                                                                                                                                                                                                        "left join sga_institucioneducacionsuperior ins  on ins.id=tc.institucion_id  " \
                                                                                                                                                                                                                        "where tc.persona_id=per.id  " \
                                                                                                                                                                                                                        "and tit.nivel_id=3  and tc.verisenescyt=true) as tercernivel,   " \
                                                                                                                                                                                                                        "(select pt1.nombre from sga_profesortipo pt1, sga_profesordistributivohoras dist where pt1.id=dist.nivelcategoria_id and dist.periodo_id= '" + periodo + "'  and dist.profesor_id=pro.id) as tipoprofesor,extract(year from malla.inicio) as anio,0  " \
                                                                                                                                                                                                                                                                                                                                                                                  "from sga_profesormateria pmat,sga_materia mat,sga_nivel niv,sga_profesor pro,sga_persona per,   " \
                                                                                                                                                                                                                                                                                                                                                                                  "sga_asignaturamalla asimalla,sga_malla malla,sga_carrera carr,sga_asignatura asig,   " \
                                                                                                                                                                                                                                                                                                                                                                                  "sga_nivelmalla nmalla,auth_user us,sga_coordinacion_carrera corcar,sga_coordinacion coor,   " \
                                                                                                                                                                                                                                                                                                                                                                                  "sga_tiempodedicaciondocente td ,sga_sesion ses, sga_tipoprofesor tipro   " \
                                                                                                                                                                                                                                                                                                                                                                                  "where pmat.profesor_id=pro.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and pro.persona_id=per.id    " \
                                                                                                                                                                                                                                                                                                                                                                                  "and per.usuario_id=us.id     " \
                                                                                                                                                                                                                                                                                                                                                                                  "and pro.dedicacion_id=td.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and pmat.materia_id=mat.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and mat.nivel_id=niv.id and niv.sesion_id=ses.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and mat.asignaturamalla_id=asimalla.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and asimalla.malla_id=malla.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and malla.carrera_id=carr.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and corcar.carrera_id=carr.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and corcar.coordinacion_id=coor.id and tipro.id not in (4)  " \
                                                                                                                                                                                                                                                                                                                                                                                  "and asimalla.asignatura_id=asig.id and asimalla.nivelmalla_id=nmalla.id and pmat.tipoprofesor_id=tipro.id   " \
                                                                                                                                                                                                                                                                                                                                                                                  "and niv.periodo_id= '" + periodo + "'"
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, per[7])
                        ws.write(a, 1, per[33] if per[33] != 0 else '')
                        ws.write(a, 2, per[21])
                        ws.write(a, 3, per[6])
                        ws.write(a, 4, per[5])
                        ws.write(a, 5, per[8])
                        ws.write(a, 6, per[9])
                        ws.write(a, 7, per[10].strftime("%d/%m/%Y") if per[10] else '')
                        ws.write(a, 8, per[11].strftime("%d/%m/%Y") if per[11] else '')
                        ws.write(a, 9, per[12])
                        ws.write(a, 10, per[13])
                        ws.write(a, 11, per[14].strftime("%d/%m/%Y") if per[14] else '')
                        ws.write(a, 12, per[15].strftime("%d/%m/%Y") if per[15] else '')
                        ws.write(a, 13, per[16])
                        ws.write(a, 14, per[17])
                        ws.write(a, 15, per[2] + ' ' + per[3] + ' ' + per[4])
                        ws.write(a, 16, per[0])
                        ws.write(a, 17, per[22])
                        ws.write(a, 18, per[24] + '@unemi.edu.ec')
                        ws.write(a, 19, per[20])
                        ws.write(a, 20, per[32])
                        ws.write(a, 21, per[19])
                        ws.write(a, 22, per[1])
                        ws.write(a, 23, per[25])
                        ws.write(a, 24, per[31])
                        ws.write(a, 25, per[26])
                        ws.write(a, 26, per[27])
                        ws.write(a, 27, per[28])
                        ws.write(a, 28, per[29])
                        if per[30]:
                            lgtbi = 'SI'
                        else:
                            lgtbi = 'NO'
                        ws.write(a, 29, lgtbi)
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'informedocente':
                mensaje = "Problemas al generar el informe de actividades."
                try:
                    profesor = Profesor.objects.get(pk=int(request.GET['iddocente']))
                    return conviert_html_to_pdf('adm_criteriosactividadesdocente/informe_actividad_docente_pdf.html', {'pagesize': 'A4', 'data': profesor.informe_actividades_mensual_docente(periodo, request.GET['fini'], request.GET['ffin'], 'TODO')})
                except Exception as ex:
                    return HttpResponseRedirect("/adm_criteriosactividadesdocente?info=%s" % mensaje)

            elif action == 'permisoinstitucional':
                try:
                    data['title'] = u'Aprobar Permiso Institucional(Director).'
                    search = None
                    ids = None
                    if Departamento.objects.filter(responsable=persona, permisogeneral=True).exists():
                        departamento = Departamento.objects.all()
                    else:
                        departamento = Departamento.objects.filter(responsable=persona, status=True, responsable__status=True)
                    depaid = departamento.values_list("id", flat=True)
                    administrativoid = DistributivoPersona.objects.values_list("persona__id", flat=True).filter(Q(status=True), (Q(regimenlaboral__id=1) | Q(regimenlaboral__id=4)))
                    coordinaciones = persona.mis_coordinaciones()
                    coordinaciones = coordinaciones.values_list("id", flat=True)
                    personaid = Persona.objects.values_list('id', flat=True).filter(profesor__profesordistributivohoras__coordinacion__id__in=coordinaciones, profesor__profesordistributivohoras__periodo=periodo).order_by('-usuario__is_active', 'profesor')
                    # excluir rector y vicerrector
                    #plantillas1 = PermisoInstitucional.objects.filter(solicita__id__in=personaid, estadosolicitud=1, regimenlaboral__id=2).exclude(solicita=persona).exclude(solicita__id__in=[26919, 28089]).order_by('-fechasolicitud')
                    #plantillas2 = PermisoInstitucional.objects.filter(solicita__id__in=administrativoid, estadosolicitud=1, regimenlaboral__id__in=[1, 4]).exclude(solicita=persona).exclude(solicita__id__in=[26919, 28089]).order_by('-fechasolicitud')
                    plantillas = PermisoInstitucional.objects.filter((Q(solicita__id__in=personaid) | Q(solicita__id__in=administrativoid)) , Q(estadosolicitud=1)).exclude(solicita=persona).order_by('-fechasolicitud')
                    plantillas = plantillas
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            plantillas = plantillas.filter(Q(solicita__nombres__icontains=search) |
                                                           Q(solicita__apellido1__icontains=search) |
                                                           Q(solicita__apellido2__icontains=search) |
                                                           Q(solicita__cedula__icontains=search) |
                                                           Q(solicita__pasaporte__icontains=search)).distinct().order_by('-fechasolicitud')
                        else:
                            plantillas = plantillas.filter(Q(solicita__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1])).distinct().order_by('-fechasolicitud')
                    if 'ids' in request.GET:
                        ids = int(request.GET['ids'])
                        if ids > 0:
                            plantillas = plantillas.filter(estadosolicitud=ids).distinct().order_by('-fechasolicitud')
                    paging = MiPaginador(plantillas, 20)
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
                    data['permisos'] = page.object_list
                    data['email_domain'] = EMAIL_DOMAIN
                    data['solicitudes'] = ESTADO_PERMISOS
                    return render(request, "adm_criteriosactividadesdocente/permisoinstitucional.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalle':
                try:
                    data = {}
                    detalle = PermisoInstitucional.objects.get(pk=int(request.GET['id']))
                    data['permiso'] = detalle
                    data['detallepermiso'] = detalle.permisoinstitucionaldetalle_set.all()
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['aprobadores'] = detalle.permisoaprobacion_set.all()
                    template = get_template("adm_criteriosactividadesdocente/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verdetalle':
                try:
                    data = {}
                    detalle = PermisoInstitucional.objects.get(pk=int(request.GET['id']))
                    data['permiso'] = detalle
                    data['detallepermiso'] = detalle.permisoinstitucionaldetalle_set.all()
                    data['aprobadores'] = detalle.permisoaprobacion_set.all()
                    template = get_template("th_permiso_institucional/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verlogmarcadas':
                try:
                    data['title'] = u'LOG de Marcadas'
                    # data['distributivo'] = distributivo = DistributivoPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['personaadmin'] = persona = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['anios'] = persona.lista_anios_trabajados_log()
                    if 's' in request.GET:
                        data['search'] = request.GET['s']
                    if 'idc' in request.GET:
                        data['idc'] = request.GET['idc']
                    data['jornadas'] = persona.historialjornadatrabajador_set.all()
                    return render(request, "adm_criteriosactividadesdocente/logmarcadas.html", data)
                except Exception as ex:
                    pass

            elif action == 'abrirdistributivo':
                try:
                    data['title'] = u'Abrir distributivo'
                    return render(request, "adm_criteriosactividadesdocente/abrirdistributivo.html", data)
                except:
                    pass

            elif action == 'cerrardistributivo':
                try:
                    data['title'] = u'Cerrar distributivo'
                    return render(request, "adm_criteriosactividadesdocente/cerrardistributivo.html", data)
                except:
                    pass

            elif action == 'activar':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_inscripciones')
                    data['title'] = u'Activar distributivo del profesor'
                    data['distributivo'] = ProfesorDistributivoHoras.objects.get(pk=encrypt(request.GET['id']))
                    return render(request, "adm_criteriosactividadesdocente/activar.html", data)
                except Exception as ex:
                    pass

            elif action == 'desactivar':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_inscripciones')
                    data['title'] = u'Desactivar distributivo del profesor'
                    data['distributivo'] = ProfesorDistributivoHoras.objects.get(pk=encrypt(request.GET['id']))
                    return render(request, "adm_criteriosactividadesdocente/desactivar.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobar_cronograma':
                try:
                    data['title'] = u'Aprobar Cronograma de actividades'
                    data['search'] = request.GET['s'] if 's' in request.GET else ''
                    data['idc'] = int(request.GET['idc']) if 'idc' in request.GET else None
                    data['cro'] = CronogramaActividad.objects.get(pk=request.GET['id'])
                    return render(request, "adm_criteriosactividadesdocente/aprobar_cronogramaactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'pdflistaafinidad':
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
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
                        1, 10000).__str__() + '.xls'
                    columns = [
                        (u"N.", 2500),
                        (u"CEDULA", 3000),
                        (u"DOCENTE", 10000),
                        (u"FACULTAD", 15000),
                        (u"CARRERA", 15000),
                        (u"ASIGNATURA", 15000),
                        (u"TÍTULO A FIN", 10000),
                        (u"CAMPO AMPLIO", 5000),
                        (u"CAMPO DETALLADO", 5000),
                        (u"CAMPO ESPECÍFICO", 5000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connections['default'].cursor()
                    # lista_json = []
                    # data = {}
                    # listado = ProfesorMateria.objects.values_list('profesor__id','profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres','materia__asignatura__id','materia__asignatura__nombre','materia__asignaturamalla__id').filter(materia__nivel__periodo=periodo)
                    # listado = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, profesor__persona__cedula='0919916346')
                    listado = ProfesorMateria.objects.filter(materia__nivel__periodo=periodo, tipoprofesor__id=1, status=True)
                    row_num = 4
                    i = 1
                    for lista in listado:
                        campo1 = i
                        campo2 = lista.profesor.persona.cedula
                        campo3 = lista.profesor.persona.apellido1 + ' ' + lista.profesor.persona.apellido2 + ' ' + lista.profesor.persona.nombres
                        campo4 = lista.materia.asignatura.nombre
                        campo5 = lista.materia.asignaturamalla.malla.carrera.nombre
                        campo6 = lista.materia.asignaturamalla.malla.carrera.mi_coordinacion()
                        areamateria = ''
                        subareamateria = ''
                        subespeareamateria = ''
                        respuestas = []
                        titulos = lista.profesor.persona.titulacion_set.filter(titulo__grado__id__in=[1, 2, 5], status=True).order_by('titulo__grado__id')
                        ban = 0
                        contartitulos = titulos.count()
                        contadorfor = 0
                        if titulos:
                            for titu in titulos:
                                contadorfor += 1
                                if ban == 0:
                                    tituloafin = ''
                                    area = 'NO'
                                    areap = False
                                    subarea = 'NO'
                                    subareap = False
                                    espe = 'NO'
                                    espep = False
                                    contador = 0
                                    if titu.titulo.grado:
                                        if titu.titulo.grado.id == 1:
                                            ban = 1
                                            if titu.titulo.areaconocimiento and lista.materia.asignaturamalla.areaconocimientotitulacion:
                                                if titu.titulo.areaconocimiento.id == lista.materia.asignaturamalla.areaconocimientotitulacion.id:
                                                    area = 'SI'
                                                    areap = True
                                                    contador += 1
                                            if titu.titulo.subareaconocimiento and lista.materia.asignaturamalla.subareaconocimiento:
                                                if titu.titulo.subareaconocimiento.id == lista.materia.asignaturamalla.subareaconocimiento.id:
                                                    subarea = 'SI'
                                                    subareap = True
                                                    contador += 1
                                            if titu.titulo.subareaespecificaconocimiento and lista.materia.asignaturamalla.subareaespecificaconocimiento:
                                                if titu.titulo.subareaespecificaconocimiento.id == lista.materia.asignaturamalla.subareaespecificaconocimiento.id:
                                                    espe = 'SI'
                                                    espep = True
                                                    contador += 1
                                            tituloafin = titu.titulo.nombre
                                            respuestas.append([titu.titulo.nombre, area, subarea, espe, contador])
                                            lista.tituloafin = titu.titulo
                                            lista.afinidadcampoamplio = areap
                                            lista.afinidadcampodetallado = subareap
                                            lista.afinidadcampoespecifico = espep
                                            lista.save()
                                        else:
                                            if titu.titulo.areaconocimiento and lista.materia.asignaturamalla.areaconocimientotitulacion:
                                                if titu.titulo.areaconocimiento.id == lista.materia.asignaturamalla.areaconocimientotitulacion.id:
                                                    area = 'SI'
                                                    areap = True
                                                    contador += 1
                                            if titu.titulo.subareaconocimiento and lista.materia.asignaturamalla.subareaconocimiento:
                                                if titu.titulo.subareaconocimiento.id == lista.materia.asignaturamalla.subareaconocimiento.id:
                                                    subarea = 'SI'
                                                    subareap = True
                                                    contador += 1
                                            if titu.titulo.subareaespecificaconocimiento and lista.materia.asignaturamalla.subareaespecificaconocimiento:
                                                if titu.titulo.subareaespecificaconocimiento.id == lista.materia.asignaturamalla.subareaespecificaconocimiento.id:
                                                    espe = 'SI'
                                                    espep = True
                                                    contador += 1
                                            if contador >= 1:
                                                lista.tituloafin = titu.titulo
                                                lista.afinidadcampoamplio = areap
                                                lista.afinidadcampodetallado = subareap
                                                lista.afinidadcampoespecifico = espep
                                                lista.save()
                                                tituloafin = titu.titulo.nombre
                                                respuestas.append([titu.titulo.nombre, area, subarea, espe, contador])
                                                ban == 1
                                                break
                                            if contadorfor == contartitulos and ban == 0:
                                                lista.tituloafin = titu.titulo
                                                lista.save()
                                                tituloafin = titu.titulo.nombre
                        else:
                            tituloafin = ''
                            area = 'NO'
                            subarea = 'NO'
                            espe = 'NO'
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo6, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo4, font_style2)
                        ws.write(row_num, 6, tituloafin, font_style2)
                        ws.write(row_num, 7, area, font_style2)
                        ws.write(row_num, 8, subarea, font_style2)
                        ws.write(row_num, 9, espe, font_style2)
                        row_num += 1
                        i += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'rechazar_cronograma':
                try:
                    data['title'] = u'Rechazar Cronograma de actividades'
                    data['form'] = RechazarCronogramaActividadFrom()
                    data['search'] = request.GET['s'] if 's' in request.GET else ''
                    data['idc'] = int(request.GET['idc']) if 'idc' in request.GET else None
                    data['cro'] = CronogramaActividad.objects.get(pk=request.GET['id'])
                    template = get_template("adm_criteriosactividadesdocente/rechazar_cronogramaactividad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'productoinvestigacion':
                try:
                    data['title'] = u'Productos Criterio Investigación'
                    data['detalledistributivo'] = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "adm_criteriosactividadesdocente/productoinvestigacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleproductoinvestigacion':
                try:
                    data = {}
                    data['tipo'] = tipo = int(request.GET['tipo'])
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    detalle = None
                    if tipo == 1:
                        data['articulo'] = articulo = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                        detalle = articulo.investigaciondocenteaprobacion_set.filter(status=True)
                        cronograma = articulo.cronogramatrabajoinvestigaciondocente_set.filter(status=True)
                    elif tipo == 2:
                        data['ponencia'] = ponencia = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                        detalle = ponencia.investigaciondocenteaprobacion_set.filter(status=True)
                        cronograma = ponencia.cronogramatrabajoinvestigaciondocente_set.filter(status=True)
                    elif tipo == 3:
                        data['libro'] = libro = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                        detalle = libro.investigaciondocenteaprobacion_set.filter(status=True)
                        cronograma = libro.cronogramatrabajoinvestigaciondocente_set.filter(status=True)
                    else:
                        data['capitulolibro'] = capitulolibro = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                        detalle = capitulolibro.investigaciondocenteaprobacion_set.filter(status=True)
                        cronograma = capitulolibro.cronogramatrabajoinvestigaciondocente_set.filter(status=True)
                    data['aprobadores'] = detalle
                    data['cronograma'] = cronograma
                    template = get_template("adm_criteriosactividadesdocente/detalleproductoinvestigcion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cronogramaproducto':
                try:
                    data['title'] = u'Productos Investigación '
                    data['tipo'] = tipo = int(request.GET['tipo'])
                    if tipo == 1:
                        data['articulo'] = articulo = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                        cronograma = articulo.cronogramatrabajoinvestigaciondocente_set.filter(status=True)
                    elif tipo == 2:
                        data['ponencia'] = ponencia = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                        cronograma = ponencia.cronogramatrabajoinvestigaciondocente_set.filter(status=True)
                    elif tipo == 3:
                        data['libro'] = libro = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                        cronograma = libro.cronogramatrabajoinvestigaciondocente_set.filter(status=True)
                    else:
                        data['capitulolibro'] = capitulolibro = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                        cronograma = capitulolibro.cronogramatrabajoinvestigaciondocente_set.filter(status=True)
                    data['cronograma'] = cronograma
                    return render(request, "adm_criteriosactividadesdocente/cronogramaproducto.html", data)
                except Exception as ex:
                    pass

            elif action == 'materias':
                try:
                    data['title'] = u'Materias del profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    periodo = request.session['periodo']
                    data['profesor'] = profesor
                    data['materias'] = profesor.mis_materiastodas(periodo).order_by('materia__asignatura__nombre')
                    data['reporte_0'] = obtener_reporte('listado_asistencia_dias')
                    data['reporte_1'] = obtener_reporte('lista_alumnos_matriculados_materia')
                    data['reporte_2'] = obtener_reporte("control_academico")
                    return render(request, "adm_criteriosactividadesdocente/materias.html", data)
                except Exception as ex:
                    pass

            elif action == 'verformulario':
                try:
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['idpm'])
                    if profesormateria.materia.asignaturamalla.malla.carrera.mi_coordinacion2 == 9:
                        if profesormateria.materia.asignaturamalla.malla.carrera.modalidad == 3:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricas_heteroadmisionvirtual()
                        else:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricas_heteroadmision()
                    else:
                        if profesormateria.materia.asignaturamalla.malla.carrera.modalidad == 3:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricas_heterovirtual()
                        else:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricas_hetero()
                    data['combomejoras'] = TipoObservacionEvaluacion.objects.filter(tipoinstrumento=1, tipo=1, status=True, activo=True).order_by('nombre')
                    data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                    data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                    data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                    if profesormateria.materia.asignaturamalla.malla.carrera.mi_coordinacion2 == 7:
                        return render(request, "adm_criteriosactividadesdocente/verformularioipec.html", data)
                    else:
                        return render(request, "adm_criteriosactividadesdocente/verformulario.html", data)
                except Exception as ex:
                    pass

            elif action == 'preferenciasactividades':
                try:
                    data['title'] = u'Reporte'
                    data['periodo'] = periodo
                    return render(request, "adm_criteriosactividadesdocente/preferenciasactividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcarrera':
                try:
                    data['postar'] = postar = ActividadDetalleDistributivo.objects.get(pk=request.GET['id'])
                    data['yaasignadas'] = detalle = ActividadDetalleDistributivoCarrera.objects.filter(actividaddetalle=postar)
                    data['carreras'] = Carrera.objects.filter(status=True).exclude(pk__in=detalle.values_list('carrera_id')).order_by('nombre')
                    template = get_template('adm_criteriosactividadesdocente/modal/addcarreras.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            elif action == 'solicitudeshorariotutoria':
                data['solicitud'] = DetalleSolicitudHorarioTutoria.objects.get(id=int(request.GET['id']))
                template = get_template("adm_criteriosactividadesdocente/modal/solictudhorariotutoria.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})

            # elif action == 'cargar_periodo':
            #     try:
            #         lista = []
            #         periodos = Periodo.objects.filter(status=True).distinct()
            #
            #         for periodo in periodos:
            #             if not buscar_dicc(lista, 'id', periodo.id):
            #                 lista.append({'id': periodo.id, 'nombre': periodo.nombre})
            #         return JsonResponse({'result': 'ok', 'lista': lista})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'reportetutoria':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('tutorias')
                    ws.set_column(0, 0, 30)
                    ws.set_column(1, 1, 20)
                    ws.set_column(2, 2, 45)
                    ws.set_column(3, 3, 60)
                    ws.set_column(4, 4, 25)
                    ws.set_column(5, 5, 20)

                    #                   ws.columm_dimensions['A'].width = 20

                    # formatotitulo = workbook.add_format(
                    #     {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'valign': 'middle',
                    #      'fg_color': '#A2D0EC'})
                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.write(0, 0, 'CARRERA', formatoceldacab)
                    ws.write(0, 1, 'CEDULA', formatoceldacab)
                    ws.write(0, 2, 'DOCENTE', formatoceldacab)
                    ws.write(0, 3, 'ASIGNATURA', formatoceldacab)
                    ws.write(0, 4, 'SOLICITUD TUTORIA ID', formatoceldacab)
                    ws.write(0, 5, 'ESTADO', formatoceldacab)

                    estado = request.GET['estado']
                    desde = request.GET['fdesde']
                    hasta = request.GET['fhasta']

                    filtros = Q(status=True)

                    if estado:
                        filtros = filtros & Q(estado=request.GET['estado'])

                    if desde and hasta:
                        filtros = filtros & Q(fecha_creacion__range=(request.GET['fdesde'], request.GET['fhasta']))

                    elif desde:
                        filtros = filtros & Q(fecha_creacion__gte=request.GET['fdesde'])

                    elif hasta:
                        filtros = filtros & Q(fecha_creacion__lte=request.GET['fhasta'])

                    #                    periodo1 = request.GET['periodo']
                    # periodo_nombre = request.GET['periodo_nombre']

                    #                    periodo = Periodo.objects.get(id=119)
                    #                     estado = 3
                    #                     filtros = Q(status=True)
                    #                     if 'estado' in request.GET:
                    #                         filtros = filtros & Q(estado=request.GET['estado'])
                    #
                    #                     if 'fdesde' and 'fhasta' in request.GET:
                    #                         filtros = filtros & Q(fecha_creacion__range=(request.GET['fdesde'], request.GET['fhasta']))
                    #
                    #                     elif 'fdesde' in request.GET:
                    #                         filtros = filtros & Q(fecha_creacion__gte=request.GET['fdesde'])
                    #
                    #                     elif 'fhasta' in request.GET:
                    #                         filtros = filtros & Q(fecha_creacion__lte=request.GET['fhasta'])
                    #
                    # desde = request.GET['fdesde']
                    # hasta = request.GET['fhasta']
                    #
                    # filtrofechas = Q(fecha_creacion__range=(desde, hasta))

                    # solicitudes = SolicitudTutoriaIndividual.objects.filter(status=True, estado=estado,
                    #                                                         materiaasignada__matricula__nivel__periodo_id=periodo1).order_by('profesor__persona__nombres',
                    #                                                                                                                      'profesor__persona__apellido1',
                    #                                                                                                                      'profesor__persona__apellido2',
                    #                                                                                                                      'materiaasignada__materia__asignatura__nombre',
                    #                                                                                                                      'materiaasignada__materia__identificacion',
                    #                                                                                                                      'materiaasignada__materia__paralelo')

                    solicitudes = SolicitudTutoriaIndividual.objects.filter(filtros).order_by('profesor__persona__nombres',
                                                                                              'profesor__persona__apellido1',
                                                                                              'profesor__persona__apellido2',
                                                                                              'materiaasignada__materia__asignatura__nombre',
                                                                                              'materiaasignada__materia__identificacion',
                                                                                              'materiaasignada__materia__paralelo')

                    filas_recorridas = 2
                    for solicitud in solicitudes:
                        est = ""
                        if solicitud.estado == 1:
                            est = "SOLICITADO"
                        if solicitud.estado == 2:
                            est = "PROGRAMADO"
                        if solicitud.estado == 3:
                            est = "EJECUTADO"
                        if solicitud.estado == 4:
                            est = "CANCELADO"

                        ws.write('A%s' % filas_recorridas, str(solicitud.materiaasignada.matricula.inscripcion.carrera), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(solicitud.profesor.persona.identificacion()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(solicitud.profesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(solicitud.materiaasignada.materia.asignatura.nombre + ' - ' + solicitud.materiaasignada.materia.identificacion + ' - ' + solicitud.materiaasignada.materia.paralelo), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(solicitud.id), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(est), formatoceldaleft)

                        filas_recorridas += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'ReporteDeTutorias.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass


            elif action == 'reportemarcadasprofesor':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('marcadasprofesor')
                    ws.set_column(0, 0, 40)
                    ws.set_column(1, 1, 45)
                    ws.set_column(2, 2, 40)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 25)
                    ws.set_column(5, 5, 25)
                    ws.set_column(6, 6, 60)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.write(0, 0, 'COORDINACION', formatoceldacab)
                    ws.write(0, 1, 'CARRERA', formatoceldacab)
                    ws.write(0, 2, 'DOCENTE', formatoceldacab)
                    ws.write(0, 3, 'FECHA DE MARCADA', formatoceldacab)
                    ws.write(0, 4, 'HORA DE MARCADA', formatoceldacab)
                    ws.write(0, 5, 'PROCESADO', formatoceldacab)
                    ws.write(0, 6, 'IP MARCADA', formatoceldacab)

                    # estado = request.GET['estado']
                    desde = request.GET['fdesde']
                    hasta = request.GET['fhasta']
                    peri = request.GET['periodo']
                    cordina = request.GET['coordinacion']

                    filtros = Q(status=True)

                    if desde and hasta:
                        filtros = filtros & Q(fecha_creacion__range=(desde, hasta))

                    elif desde:
                        filtros = filtros & Q(fecha_creacion__gte=desde)

                    elif hasta:
                        filtros = filtros & Q(fecha_creacion__lte=hasta)

                    if peri:
                        filtros = filtros & Q(logdia__persona__profesor__profesordistributivohoras__periodo=peri)

                    if cordina:
                        filtros = filtros & Q(logdia__persona__profesor__profesordistributivohoras__carrera__coordinacion=cordina)

                    marcadas = LogMarcada.objects.filter(filtros).order_by('logdia__persona__apellido1',
                                                                           'logdia__persona__apellido2',
                                                                           'logdia__persona__nombres',
                                                                           'logdia__fecha',
                                                                           'time')
                    filas_recorridas = 2
                    for marcada in marcadas:
                        coordinacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=peri, profesor__persona_id=marcada.logdia.persona.id).values_list('coordinacion__nombre', flat=True)[0]
                        carrera = ProfesorDistributivoHoras.objects.filter(status=True, periodo=peri, profesor__persona_id=marcada.logdia.persona.id).values_list('carrera__nombre', flat=True)[0]

                        ws.write('A%s' % filas_recorridas, str(coordinacion), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(carrera), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(marcada.logdia.persona), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(marcada.logdia.fecha), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(marcada.time.strftime("%H:%M:%S")), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str('PROCESADO' if marcada.logdia.procesado == True else 'SIN PROCESAR'), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(marcada.ipmarcada), formatoceldaleft)

                        filas_recorridas += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'ReporteMarcadasDocentes.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportedistributivo':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('datos_profesor')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 50)
                    ws.set_column(2, 2, 45)
                    ws.set_column(3, 3, 30)
                    ws.set_column(4, 4, 25)
                    ws.set_column(5, 5, 45)
                    ws.set_column(6, 6, 40)
                    ws.set_column(7, 7, 45)
                    ws.set_column(8, 8, 50)
                    ws.set_column(9, 9, 25)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 30)
                    ws.set_column(13, 13, 30)
                    ws.set_column(14, 14, 25)
                    ws.set_column(15, 15, 20)
                    ws.set_column(16, 16, 20)
                    ws.set_column(17, 17, 45)
                    ws.set_column(18, 18, 45)
                    ws.set_column(19, 19, 45)

                    #                   ws.columm_dimensions['A'].width = 20

                    # formatotitulo = workbook.add_format(
                    #     {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'valign': 'middle',
                    #      'fg_color': '#A2D0EC'})
                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.write(0, 0, 'Nº', formatoceldacab)
                    ws.write(0, 1, 'APELLIDOS Y NOMBRES', formatoceldacab)
                    ws.write(0, 2, 'CARGO', formatoceldacab)
                    ws.write(0, 3, 'CATEGORIZACION', formatoceldacab)
                    ws.write(0, 4, 'TIPO', formatoceldacab)
                    ws.write(0, 5, 'DEDICACION', formatoceldacab)
                    ws.write(0, 6, 'FACULTAD A LA QUE PERTENECE', formatoceldacab)
                    ws.write(0, 7, 'CARRERA A LA QUE PERTENECE', formatoceldacab)
                    ws.write(0, 8, 'ASIGNATURA QUE IMPARTE EL PROFESOR', formatoceldacab)
                    ws.write(0, 9, 'AFINIDAD', formatoceldacab)
                    ws.write(0, 10, 'AFINIDAD CAMPO AMPLIO', formatoceldacab)
                    ws.write(0, 11, 'AFINIDAD CAMPO ESPECIFICO', formatoceldacab)
                    ws.write(0, 12, 'AFINIDAD CAMPO DETALLADO', formatoceldacab)
                    ws.write(0, 13, 'TIPO PROFESOR', formatoceldacab)
                    ws.write(0, 14, 'HORAS A IMPARTIR', formatoceldacab)
                    ws.write(0, 15, 'MALLA', formatoceldacab)
                    ws.write(0, 16, 'CARRERA', formatoceldacab)
                    ws.write(0, 17, 'SECCION', formatoceldacab)
                    ws.write(0, 18, 'NIVEL', formatoceldacab)
                    ws.write(0, 19, 'PARALELO', formatoceldacab)
                    docentes = ProfesorMateria.objects.select_related('profesor', 'materia', 'tipoprofesor').filter(status=True, activo=True, materia__nivel__periodo_id=periodo).order_by('profesor__persona__apellido1',
                                                                                                                                                                                           'profesor__persona__apellido2',
                                                                                                                                                                                           'profesor__persona__nombres')

                    filas_recorridas = 2
                    num = 1
                    for docente in docentes:
                        if docente.afinidad == True:
                            afi = "A FIN"
                        else:
                            afi = "NO A FIN"
                        if docente.afinidadcampoamplio == True:
                            afiam = "A FIN"
                        else:
                            afiam = "NO A FIN"
                        if docente.afinidadcampoespecifico == True:
                            afiespe = "A FIN"
                        else:
                            afiespe = "NO A FIN"
                        if docente.afinidadcampodetallado == True:
                            afidet = "A FIN"
                        else:
                            afidet = "NO A FIN"

                        qcargo = DistributivoPersona.objects.filter(status=True, regimenlaboral_id=2, persona_id=docente.profesor.persona.id)
                        cargo = qcargo.values_list('denominacionpuesto__descripcion')[0][0] if qcargo.exists() else 'NO REGISTRA'
                        categorizacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor_id=docente.profesor.id).values_list('categoria__nombre', flat=True)[0]
                        tipo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor_id=docente.profesor.id).values_list('nivelcategoria__nombre', flat=True)[0]
                        dedicacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor_id=docente.profesor.id).values_list('dedicacion__nombre', flat=True)[0]
                        coordinacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor_id=docente.profesor.id).values_list('coordinacion__nombre', flat=True)[0]
                        carrera = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor_id=docente.profesor.id).values_list('carrera__nombre', flat=True)[0]

                        ws.write('A%s' % filas_recorridas, str(num), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(docente.profesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, cargo, formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(categorizacion), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(tipo), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(dedicacion), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(coordinacion), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(carrera), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(docente.materia.asignatura.nombre + ' - ' + docente.materia.identificacion + ' - ' + docente.materia.paralelo), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(afi), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(afiam), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(afiespe), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(afidet), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str(docente.tipoprofesor.nombre), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str(docente.hora), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str(docente.materia.asignaturamalla.malla.codigo), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str(docente.materia.asignaturamalla.malla.carrera.nombre), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str(docente.materia.nivel.sesion.nombre), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str(docente.materia.asignaturamalla.nivelmalla.nombre), formatoceldaleft)
                        ws.write('T%s' % filas_recorridas, str(docente.materia.paralelo), formatoceldaleft)

                        filas_recorridas += 1
                        num += 1

                    ws1 = workbook.add_worksheet('profesor_proyectos')
                    ws1.set_column(0, 0, 10)
                    ws1.set_column(1, 1, 50)
                    ws1.set_column(2, 2, 45)
                    ws1.set_column(3, 3, 30)
                    ws1.set_column(4, 4, 25)
                    ws1.set_column(5, 5, 45)
                    ws1.set_column(6, 6, 40)
                    ws1.set_column(7, 7, 45)
                    ws1.set_column(8, 8, 45)
                    ws1.set_column(9, 9, 45)
                    ws1.set_column(10, 10, 45)

                    ws1.write(0, 0, 'Nº', formatoceldacab)
                    ws1.write(0, 1, 'FACULTAD', formatoceldacab)
                    ws1.write(0, 2, 'CARRERA', formatoceldacab)
                    ws1.write(0, 3, 'APELLIDOS Y NOMBRES', formatoceldacab)
                    ws1.write(0, 4, 'CARGO', formatoceldacab)
                    ws1.write(0, 5, 'CATEGORIZACION', formatoceldacab)
                    ws1.write(0, 6, 'TIPO', formatoceldacab)
                    ws1.write(0, 7, 'DEDICACION', formatoceldacab)
                    ws1.write(0, 8, 'PROYECTOS DE INVESTIGACION', formatoceldacab)
                    ws1.write(0, 9, 'PROYECTOS DE VINCULACION', formatoceldacab)
                    ws1.write(0, 10, 'LINEA DE INVESTIGACION', formatoceldacab)

                    docentes1 = ParticipantesMatrices.objects.select_related('profesor', 'proyecto').filter(profesor__status=True, profesor__activo=True).order_by('profesor__persona__apellido1',
                                                                                                                                                                   'profesor__persona__apellido2',
                                                                                                                                                                   'profesor__persona__nombres')

                    filas_recorridas = 2
                    num = 1
                    for docente1 in docentes1:
                        qcargo = DistributivoPersona.objects.filter(status=True, regimenlaboral_id=2, persona_id=docente1.profesor.persona.id)
                        ditr_activ = None
                        if ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor=docente1.profesor).exists():
                            ditr_activ = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor=docente1.profesor)[0]
                        cargo = qcargo.values_list('denominacionpuesto__descripcion')[0][0] if qcargo.exists() else 'NO REGISTRA'
                        qcategorizacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor_id=docente1.profesor.id)
                        categorizacion = qcategorizacion.values_list('categoria__nombre')[0][0] if qcategorizacion.exists() else 'NO REGISTRA'
                        qtipo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor_id=docente1.profesor.id)
                        tipo = qtipo.values_list('nivelcategoria__nombre')[0][0] if qtipo.exists() else 'NO REGISTRA'
                        qdedicacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor_id=docente1.profesor.id)
                        dedicacion = qdedicacion.values_list('dedicacion__nombre')[0][0] if qdedicacion.exists() else 'NO REGISTRA'

                        qcarrera = ProfesorMateria.objects.filter(status=True, profesor_id=docente1.profesor.id)
                        carrera = qcarrera.values_list('materia__asignaturamalla__malla__carrera__nombre')[0][0] if qcarrera.exists() else 'NO REGISTRA'

                        ws1.write('A%s' % filas_recorridas, str(num), formatoceldaleft)
                        ws1.write('B%s' % filas_recorridas, str(ditr_activ.coordinacion) if ditr_activ else "", formatoceldaleft)
                        ws1.write('C%s' % filas_recorridas, str(ditr_activ.carrera) if ditr_activ else "", formatoceldaleft)
                        ws1.write('D%s' % filas_recorridas, str(docente1.profesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws1.write('E%s' % filas_recorridas, cargo, formatoceldaleft)
                        ws1.write('F%s' % filas_recorridas, str(categorizacion), formatoceldaleft)
                        ws1.write('G%s' % filas_recorridas, str(tipo), formatoceldaleft)
                        ws1.write('H%s' % filas_recorridas, str(dedicacion), formatoceldaleft)
                        if docente1.proyecto.tipo == 2:
                            ws1.write('I%s' % filas_recorridas, str(docente1.proyecto.nombre), formatoceldaleft)
                            ws1.write('J%s' % filas_recorridas, "---", formatoceldaleft)
                        elif docente1.proyecto.tipo == 1:
                            ws1.write('J%s' % filas_recorridas, str(docente1.proyecto.nombre), formatoceldaleft)
                            ws1.write('I%s' % filas_recorridas, "---", formatoceldaleft)
                        ws1.write('K%s' % filas_recorridas, str(docente1.proyecto.lineainvestigacion.nombre if docente1.proyecto.lineainvestigacion else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        num += 1

                    ws2 = workbook.add_worksheet('profesor_capacitaciones')
                    ws2.set_column(0, 0, 10)
                    ws2.set_column(1, 1, 50)
                    ws2.set_column(2, 2, 45)
                    ws2.set_column(3, 3, 30)
                    ws2.set_column(4, 4, 25)
                    ws2.set_column(5, 5, 45)
                    ws2.set_column(6, 6, 40)
                    ws2.set_column(7, 7, 45)
                    ws2.set_column(8, 8, 50)
                    ws2.set_column(9, 9, 50)
                    ws2.set_column(10, 10, 45)
                    ws2.set_column(11, 11, 45)
                    ws2.set_column(12, 12, 45)

                    ws2.write(0, 0, 'Nº', formatoceldacab)
                    ws2.write(0, 1, 'COORDINACION', formatoceldacab)
                    ws2.write(0, 2, 'CARRERA', formatoceldacab)
                    ws2.write(0, 3, 'APELLIDOS Y NOMBRES', formatoceldacab)
                    ws2.write(0, 4, 'CARGO', formatoceldacab)
                    ws2.write(0, 5, 'CATEGORIZACION', formatoceldacab)
                    ws2.write(0, 6, 'TIPO', formatoceldacab)
                    ws2.write(0, 7, 'DEDICACION', formatoceldacab)
                    ws2.write(0, 8, 'CAPACITACIÓN O ACTUALIZACIÓN CIENTÍFICA', formatoceldacab)
                    ws2.write(0, 9, 'FECHA DE FINALIZACIÓN DE LA CAPACITACIÓN O ACTUALIZACIÓN CIENTÍFICA', formatoceldacab)
                    ws2.write(0, 10, 'CAMPO AMPLIO DE CONOCIMIENTO DE LA ACTUALIZACIÓN CIENTÍFICA', formatoceldacab)
                    ws2.write(0, 11, 'CAMPO ESPECÍFICO DE CONOCIMIENTO DE LA ACTUALIZACIÓN CIENTÍFICA', formatoceldacab)
                    ws2.write(0, 12, 'CAMPO DETALLADO DE LA ACTUALIZACIÓN CIENTÍFICA', formatoceldacab)

                    profesoreslistado = Profesor.objects.filter(status=True).values_list('persona_id', flat=True)
                    docentes2 = Capacitacion.objects.select_related('persona', 'areaconocimiento', 'subareaconocimiento', 'subareaespecificaconocimiento').filter(persona_id__in=profesoreslistado).order_by('persona__apellido1',
                                                                                                                                                                                                             'persona__apellido2',
                                                                                                                                                                                                             'persona__nombres')

                    filas_recorridas = 2
                    num = 1
                    for docente2 in docentes2:
                        qcargo = DistributivoPersona.objects.filter(status=True, regimenlaboral_id=2, persona_id=docente2.persona.id)
                        cargo = qcargo.values_list('denominacionpuesto__descripcion')[0][0] if qcargo.exists() else 'NO REGISTRA'
                        qcategorizacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor__persona_id=docente2.persona.id)
                        categorizacion = qcategorizacion.values_list('categoria__nombre')[0][0] if qcategorizacion.exists() else 'NO REGISTRA'
                        qtipo = None
                        if ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor__persona_id=docente2.persona.id).exists():
                            qtipo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor__persona_id=docente2.persona.id)
                            tipo = qtipo.values_list('nivelcategoria__nombre')[0][0] if qtipo.exists() else 'NO REGISTRA'
                        qdedicacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor__persona_id=docente2.persona.id)
                        dedicacion = qdedicacion.values_list('dedicacion__nombre')[0][0] if qdedicacion.exists() else 'NO REGISTRA'

                        ws2.write('A%s' % filas_recorridas, str(""), formatoceldaleft)
                        ws2.write('B%s' % filas_recorridas, str(qtipo[0].coordinacion) if qtipo else "", formatoceldaleft)
                        ws2.write('C%s' % filas_recorridas, str(qtipo[0].carrera) if qtipo else "", formatoceldaleft)
                        ws2.write('D%s' % filas_recorridas, str(docente2.persona.nombre_completo_inverso() if docente2.persona.nombre_completo_inverso() else 'NO REGISTRA'), formatoceldaleft)
                        ws2.write('E%s' % filas_recorridas, cargo, formatoceldaleft)
                        ws2.write('F%s' % filas_recorridas, str(categorizacion), formatoceldaleft)
                        ws2.write('G%s' % filas_recorridas, str(tipo), formatoceldaleft)
                        ws2.write('H%s' % filas_recorridas, str(dedicacion), formatoceldaleft)
                        ws2.write('I%s' % filas_recorridas, str(docente2.nombre if docente2.nombre else 'NO REGISTRA'), formatoceldaleft)
                        ws2.write('J%s' % filas_recorridas, str(docente2.fechafin if docente2.fechafin else 'NO REGISTRA'), formatoceldaleft)
                        ws2.write('K%s' % filas_recorridas, str(docente2.areaconocimiento.nombre if docente2.areaconocimiento else 'NO REGISTRA'), formatoceldaleft)
                        ws2.write('L%s' % filas_recorridas, str(docente2.subareaconocimiento.nombre if docente2.subareaconocimiento else 'NO REGISTRA'), formatoceldaleft)
                        ws2.write('M%s' % filas_recorridas, str(docente2.subareaespecificaconocimiento.nombre if docente2.subareaespecificaconocimiento else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        num += 1

                    ws3 = workbook.add_worksheet('profesor_titulo')
                    ws3.set_column(0, 0, 45)
                    ws3.set_column(1, 1, 50)
                    ws3.set_column(2, 2, 45)
                    ws3.set_column(3, 3, 30)
                    ws3.set_column(4, 4, 25)
                    ws3.set_column(5, 5, 45)
                    ws3.set_column(6, 6, 40)
                    ws3.set_column(7, 7, 45)
                    ws3.set_column(8, 8, 50)
                    ws3.set_column(9, 9, 50)
                    ws3.set_column(10, 10, 45)
                    ws3.set_column(11, 11, 30)
                    ws3.set_column(12, 12, 25)
                    ws3.set_column(13, 13, 45)
                    ws3.set_column(14, 14, 40)
                    ws3.set_column(15, 15, 45)
                    ws3.set_column(16, 16, 45)
                    ws3.set_column(17, 17, 50)
                    ws3.set_column(18, 18, 50)

                    #                    ws3.write(0, 0, 'Nº', formatoceldacab)
                    ws3.write(0, 0, 'COORDINACION', formatoceldacab)
                    ws3.write(0, 1, 'CARRERA', formatoceldacab)
                    ws3.write(0, 2, 'APELLIDOS Y NOMBRES', formatoceldacab)
                    ws3.write(0, 3, 'CARGO', formatoceldacab)
                    ws3.write(0, 4, 'CATEGORIZACION', formatoceldacab)
                    ws3.write(0, 5, 'TIPO', formatoceldacab)
                    ws3.write(0, 6, 'DEDICACION', formatoceldacab)
                    ws3.write(0, 7, 'TITULO TERCER NIVEL', formatoceldacab)
                    ws3.write(0, 8, 'CAMPO AMPLIO DE CONOCIMIENTO DEL TERCER NIVEL', formatoceldacab)
                    ws3.write(0, 9, 'CAMPO ESPECÍFICO DE CONOCIMIENTO DE TERCER NIVEL', formatoceldacab)
                    ws3.write(0, 10, 'CAMPO DETALLADO DEL TERCER NIVEL', formatoceldacab)
                    ws3.write(0, 11, 'TITULO MASTER', formatoceldacab)
                    ws3.write(0, 12, 'CAMPO AMPLIO DE CONOCIMIENTO DEL MÁSTER', formatoceldacab)
                    ws3.write(0, 13, 'CAMPO ESPECÍFICO DE CONOCIMIENTO DE MASTER', formatoceldacab)
                    ws3.write(0, 14, 'CAMPO DETALLADO DEL MÁSTER', formatoceldacab)
                    ws3.write(0, 15, 'TITULO PHD', formatoceldacab)
                    ws3.write(0, 16, 'CAMPO AMPLIO DE CONOCIMIENTO DEL PHD', formatoceldacab)
                    ws3.write(0, 17, 'CAMPO ESPECÍFICO DE CONOCIMIENTO DE PHD', formatoceldacab)
                    ws3.write(0, 18, 'CAMPO DETALLADO DEL PHD', formatoceldacab)
                    plantillatalentohumano = DistributivoPersona.objects.filter(status=True, regimenlaboral_id=2, estadopuesto_id=1)
                    num = 1
                    filas_titulo_recorrida = 2
                    for plantilla in plantillatalentohumano:
                        distributivo = None
                        cargo = ""
                        categorizacion = ""
                        dedicacion = ""
                        if ProfesorDistributivoHoras.objects.values('id').filter(status=True, periodo=periodo, profesor__persona_id=plantilla.persona_id).exists():
                            distributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor__persona_id=plantilla.persona_id)[0]
                            cargo = plantilla.denominacionpuesto.descripcion if plantilla.denominacionpuesto else 'NO REGISTRA'
                            categorizacion = distributivo.categoria.nombre if distributivo.categoria else 'NO REGISTRA'
                            tipo = distributivo.nivelcategoria.nombre if distributivo.nivelcategoria else 'NO REGISTRA'
                            dedicacion = distributivo.dedicacion.nombre if distributivo.dedicacion else 'NO REGISTRA'
                        titulos = Titulacion.objects.select_related('titulo', 'persona').filter(persona__status=True, titulo__nivel_id__in=(3, 4),
                                                                                                persona_id=plantilla.persona_id).exclude(titulo__grado_id__isnull=True)

                        for titulo1 in titulos:
                            ws3.write('A%s' % filas_titulo_recorrida, str(distributivo.coordinacion) if distributivo else "", formatoceldaleft)
                            ws3.write('B%s' % filas_titulo_recorrida, str(distributivo.carrera) if distributivo else "", formatoceldaleft)
                            ws3.write('C%s' % filas_titulo_recorrida, str(plantilla.persona.nombre_completo_inverso() if plantilla else 'NO REGISTRA'), formatoceldaleft)
                            ws3.write('D%s' % filas_titulo_recorrida, cargo, formatoceldaleft)
                            ws3.write('E%s' % filas_titulo_recorrida, str(categorizacion), formatoceldaleft)
                            ws3.write('F%s' % filas_titulo_recorrida, str(tipo), formatoceldaleft)
                            ws3.write('G%s' % filas_titulo_recorrida, str(dedicacion), formatoceldaleft)
                            if titulo1.titulo:
                                ws3.write('H%s' % filas_titulo_recorrida, str(titulo1.titulo.nombre) if titulo1.titulo.nivel.id == 3 else "NO REGISTRA", formatoceldaleft)
                                ws3.write('I%s' % filas_titulo_recorrida, str(titulo1.titulo.areaconocimiento.nombre if titulo1.titulo.areaconocimiento and titulo1.titulo.nivel.id == 3 else 'NO REGISTRA'), formatoceldaleft)
                                ws3.write('J%s' % filas_titulo_recorrida, str(titulo1.titulo.subareaconocimiento.nombre if titulo1.titulo.subareaconocimiento and titulo1.titulo.nivel.id == 3 else 'NO REGISTRA'), formatoceldaleft)
                                ws3.write('K%s' % filas_titulo_recorrida, str(titulo1.titulo.subareaespecificaconocimiento.nombre if titulo1.titulo.subareaespecificaconocimiento and titulo1.titulo.nivel.id == 3 else 'NO REGISTRA'), formatoceldaleft)
                                ws3.write('L%s' % filas_titulo_recorrida, str(titulo1.titulo.nombre) if titulo1.titulo.nivel.id == 4 and titulo1.titulo.grado.id != 1 else "NO REGISTRA", formatoceldaleft)
                                ws3.write('M%s' % filas_titulo_recorrida, str(titulo1.titulo.areaconocimiento.nombre if titulo1.titulo.areaconocimiento and titulo1.titulo.nivel.id == 4 and titulo1.titulo.grado.id != 1 else 'NO REGISTRA'), formatoceldaleft)
                                ws3.write('N%s' % filas_titulo_recorrida, str(titulo1.titulo.subareaconocimiento.nombre if titulo1.titulo.subareaconocimiento and titulo1.titulo.nivel.id == 4 and titulo1.titulo.grado.id != 1 else 'NO REGISTRA'), formatoceldaleft)
                                ws3.write('O%s' % filas_titulo_recorrida, str(titulo1.titulo.subareaespecificaconocimiento.nombre if titulo1.titulo.subareaespecificaconocimiento and titulo1.titulo.nivel.id == 4 and titulo1.titulo.grado.id != 1 else 'NO REGISTRA'), formatoceldaleft)
                                ws3.write('P%s' % filas_titulo_recorrida, str(titulo1.titulo.nombre) if titulo1.titulo.nivel.id == 4 and titulo1.titulo.grado.id == 1 else "NO REGISTRA", formatoceldaleft)
                                ws3.write('Q%s' % filas_titulo_recorrida, str(titulo1.titulo.areaconocimiento.nombre if titulo1.titulo.areaconocimiento and titulo1.titulo.nivel.id == 4 and titulo1.titulo.grado.id == 1 else 'NO REGISTRA'), formatoceldaleft)
                                ws3.write('R%s' % filas_titulo_recorrida, str(titulo1.titulo.subareaconocimiento.nombre if titulo1.titulo.subareaconocimiento and titulo1.titulo.nivel.id == 4 and titulo1.titulo.grado.id == 1 else 'NO REGISTRA'), formatoceldaleft)
                                ws3.write('S%s' % filas_titulo_recorrida, str(titulo1.titulo.subareaespecificaconocimiento.nombre if titulo1.titulo.subareaespecificaconocimiento and titulo1.titulo.nivel.id == 4 and titulo1.titulo.grado.id == 1 else 'NO REGISTRA'), formatoceldaleft)
                            filas_titulo_recorrida += 1
                    ws4 = workbook.add_worksheet('experiencia_laboral')
                    ws4.set_column(0, 0, 45)
                    ws4.set_column(1, 1, 50)
                    ws4.set_column(2, 2, 45)
                    ws4.set_column(3, 3, 30)
                    ws4.set_column(4, 4, 25)
                    ws4.set_column(5, 5, 45)
                    ws4.set_column(6, 6, 40)
                    ws4.set_column(7, 7, 40)
                    ws4.set_column(8, 8, 40)
                    ws4.set_column(9, 9, 40)
                    ws4.set_column(10, 10, 40)
                    ws4.set_column(11, 11, 40)
                    ws4.set_column(12, 12, 40)

                    ws4.write(0, 0, 'COORDINACION', formatoceldacab)
                    ws4.write(0, 1, 'CARRERA', formatoceldacab)
                    ws4.write(0, 2, 'APELLIDOS Y NOMBRES', formatoceldacab)
                    ws4.write(0, 3, 'CARGO', formatoceldacab)
                    ws4.write(0, 4, 'CATEGORIZACION', formatoceldacab)
                    ws4.write(0, 5, 'TIPO', formatoceldacab)
                    ws4.write(0, 6, 'DEDICACION', formatoceldacab)
                    ws4.write(0, 7, 'CARGO EXPERIENCIA', formatoceldacab)
                    ws4.write(0, 8, 'TIPO INSTITUCION', formatoceldacab)
                    ws4.write(0, 9, 'INSTITUCION', formatoceldacab)
                    ws4.write(0, 10, 'DEPARTAMENTO', formatoceldacab)
                    ws4.write(0, 11, 'FECHA INICIO', formatoceldacab)
                    ws4.write(0, 12, 'FECHA FIN', formatoceldacab)

                    filas_experiencia_recorrida = 2
                    plantillatalentohumano = DistributivoPersona.objects.filter(status=True, regimenlaboral_id=2, estadopuesto_id=1)
                    for plantilla in plantillatalentohumano:
                        cargo = plantilla.denominacionpuesto.descripcion if plantilla.denominacionpuesto else ""
                        distributivo = None
                        if ProfesorDistributivoHoras.objects.values('id').filter(status=True, periodo=periodo, profesor__persona_id=plantilla.persona_id).exists():
                            distributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor__persona_id=plantilla.persona_id)[0]
                        if ExperienciaLaboral.objects.filter(status=True, persona_id=plantilla.persona_id).exists():
                            for expeciencias in ExperienciaLaboral.objects.filter(status=True, persona_id=plantilla.persona_id):
                                ws4.write('A%s' % filas_experiencia_recorrida, str(distributivo.coordinacion) if distributivo else "", formatoceldaleft)
                                ws4.write('B%s' % filas_experiencia_recorrida, str(distributivo.carrera) if distributivo else "", formatoceldaleft)
                                ws4.write('C%s' % filas_experiencia_recorrida, str(expeciencias.persona.nombre_completo_inverso() if expeciencias.persona.nombre_completo_inverso() else 'NO REGISTRA'), formatoceldaleft)
                                ws4.write('D%s' % filas_experiencia_recorrida, cargo, formatoceldaleft)
                                ws4.write('E%s' % filas_experiencia_recorrida, str(distributivo.categoria if distributivo else ""), formatoceldaleft)
                                ws4.write('F%s' % filas_experiencia_recorrida, str(distributivo.nivelcategoria) if distributivo else "", formatoceldaleft)
                                ws4.write('G%s' % filas_experiencia_recorrida, str(distributivo.dedicacion) if distributivo else "", formatoceldaleft)
                                ws4.write('H%s' % filas_experiencia_recorrida, str(expeciencias.cargo) if expeciencias else "", formatoceldaleft)
                                ws4.write('I%s' % filas_experiencia_recorrida, str(expeciencias.get_tipoinstitucion_display()) if expeciencias else "", formatoceldaleft)
                                ws4.write('J%s' % filas_experiencia_recorrida, str(expeciencias.institucion) if expeciencias else "", formatoceldaleft)
                                ws4.write('K%s' % filas_experiencia_recorrida, str(expeciencias.departamento) if expeciencias else "", formatoceldaleft)
                                ws4.write('L%s' % filas_experiencia_recorrida, str(expeciencias.fechainicio) if expeciencias.fechainicio else "", formatoceldaleft)
                                ws4.write('M%s' % filas_experiencia_recorrida, str(expeciencias.fechafin) if expeciencias.fechafin else "", formatoceldaleft)
                                filas_experiencia_recorrida += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'ReporteDistributivo.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'reportehorasnoaprobadas':
                try:
                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('horas de actividades docentes')
                    formatotitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format({'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    ws.write(0, 0, 'Nº', formatoceldacab)
                    ws.set_column(0, 0, 10)
                    ws.write(0, 1, 'APELLIDOS Y NOMBRES', formatoceldacab)
                    ws.set_column(1, 1, 40)
                    ws.write(0, 2, 'FACULTAD', formatoceldacab)
                    ws.set_column(2, 2, 40)
                    ws.write(0, 3, 'CARRERA', formatoceldacab)
                    ws.set_column(3, 3, 40)
                    ws.write(0, 4, 'N° HORAS PLANIFICADAS', formatoceldacab)
                    ws.set_column(4, 4, 15)
                    ws.write(0, 5, 'N° HORAS ASIGNADAS', formatoceldacab)
                    ws.set_column(5, 5, 15)
                    ws.write(0, 6, 'ESTADO', formatoceldacab)
                    ws.set_column(6, 6, 15)
                    # profesores = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__periodo=periodo).values_list('detalledistributivo__distributivo__profesor_id', flat=True).distinct()
                    profesores = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo).values_list('profesor_id', flat=True).distinct()
                    filas_recorridas = 2
                    num = 1
                    for profe in profesores:
                        profesor = Profesor.objects.get(id=profe)
                        horastotales = DetalleDistributivo.objects.filter(Q(distributivo__profesor=profesor, distributivo__periodo=periodo), Q(criteriodocenciaperiodo_id__isnull=False) | Q(criterioinvestigacionperiodo_id__isnull=False) | Q(criteriogestionperiodo_id__isnull=False)).exclude(criteriodocenciaperiodo__criterio_id__in=['15', '16', '17', '18', '20', '21', '27', '28', '19', '30', '46', '7']).aggregate(valor=Sum('horas'))['valor']
                        actividades = 0
                        claseactividad = ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo).values('id')
                        if claseactividad.exists():
                            actividades = len(claseactividad)
                        prof = ProfesorMateria.objects.filter(status=True, activo=True, materia__nivel__periodo=periodo, profesor=profesor, materia__nivel__periodo__visible=True,
                                                              materia__nivel__periodo__visiblehorario=True, principal=True).distinct().values_list('profesor_id', flat=True)
                        clase = Clase.objects.filter(status=True, activo=True, profesor_id__in=prof, materia__nivel__periodo=periodo, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True).values('id').distinct().order_by('inicio')
                        if clase.exists():
                            actividades += int(len(clase))
                        claseactividadestado = ClaseActividadEstado.objects.filter(profesor=profesor, periodo=periodo, status=True).order_by('-id')
                        estado = 'SIN PLANIFICACIÓN' if not claseactividad.exists() else 'FALTAN HORAS'
                        if horastotales == actividades:
                            estado = 'SOLICITADO'
                        if claseactividadestado:
                            if claseactividadestado[0].estadosolicitud > 1:
                                estado = claseactividadestado[0].get_estadosolicitud_display()
                        coordinacion = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor=profesor).values_list('coordinacion__nombre', flat=True)[0]
                        carrera = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, profesor=profesor).values_list('carrera__nombre', flat=True)[0]
                        ws.write('A%s' % filas_recorridas, str(num), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(profesor.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(coordinacion) if coordinacion else 'SIN FACULTAD', formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(carrera) if carrera else 'SIN CARRERA', formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(actividades), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(horastotales), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(estado), formatoceldaleft)
                        filas_recorridas += 1
                        num += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'ReporteDistributivo.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'reporterecursoscompenente':
                try:
                    coordinacion = Coordinacion.objects.get(pk=request.GET['cod_facultad'])
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Reporte cumplimiento (recursos de aprendizaje y actividad de recurso)' + str(coordinacion.nombre), destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_recurso_aprendizaje_background(request=request, notiid=noti.pk, periodo=periodo, coordinacion=coordinacion, codcarrera=request.GET['cod_carrera'], tipo='excel').start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'reportehorascriterios':
                docentes = ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo).values_list('profesor_id', flat=True).distinct()
                try:
                    nombre_archivo = "reporte_horas_planificadas_criterio.xls".format(random.randint(1, 10000).__str__())
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
                    ws = wb.add_sheet('Reporte de horas')

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=horarioactividades.xls'
                    ws.col(0).width = 1000
                    ws.col(1).width = 21500
                    ws.col(2).width = 25500
                    ws.col(3).width = 8000
                    ws.col(4).width = 8000

                    row_num = 0
                    ws.write(row_num, 0, "Nº", encabesado_tabla)
                    ws.write(row_num, 1, "DOCENTE", encabesado_tabla)
                    ws.write(row_num, 2, "CRITERIO", encabesado_tabla)
                    ws.write(row_num, 3, u"HORAS ASIGNADAS", encabesado_tabla)
                    ws.write(row_num, 4, u"HORAS PLANIFICADAS", encabesado_tabla)

                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    c = 1
                    row_num = 1
                    for p in docentes:
                        for actividad in DetalleDistributivo.objects.filter(status=True, distributivo__profesor_id=p, distributivo__periodo=periodo).distinct():
                            campo0 = c
                            campo2 = ' '
                            campo1 = actividad.distributivo.profesor.persona.nombre_completo()
                            if actividad.criteriodocenciaperiodo:
                                campo2 = actividad.criteriodocenciaperiodo.criterio.nombre
                            if actividad.criterioinvestigacionperiodo:
                                campo2 = actividad.criterioinvestigacionperiodo.criterio.nombre
                            if actividad.criteriogestionperiodo:
                                campo2 = actividad.criteriogestionperiodo.criterio.nombre

                            campo3 = str(int(actividad.horas))
                            horasact = (ClaseActividad.objects.values("id").filter(detalledistributivo=actividad).count())
                            if actividad.criteriodocenciaperiodo and actividad.criteriodocenciaperiodo.criterio_id == 118:
                                clase = Clase.objects.filter(status=True, activo=True, profesor=actividad.distributivo.profesor, materia__nivel__periodo=actividad.distributivo.periodo, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True).values('id').distinct().order_by('inicio')
                                if clase.exists():
                                    horasact += int(len(clase.values('dia', 'turno')))
                            if actividad.criteriodocenciaperiodo and actividad.criteriodocenciaperiodo.criterio_id == 159:
                                clase = Clase.objects.filter(status=True, activo=True, profesor=actividad.distributivo.profesor, materia__nivel__periodo=actividad.distributivo.periodo, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, tipoprofesor_id=13).values('id').distinct().order_by('inicio')
                                if clase.exists():
                                    horasact += int(len(clase))
                            if actividad.criteriodocenciaperiodo and actividad.criteriodocenciaperiodo.criterio_id == 185:
                                clase = Clase.objects.filter(status=True, activo=True, profesor=actividad.distributivo.profesor, materia__nivel__periodo=actividad.distributivo.periodo, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, tipoprofesor_id=22).values('id').distinct().order_by('inicio')
                                if clase.exists():
                                    horasact += int(len(clase))
                            campo4 = str(int(horasact))
                            ws.write(row_num, 0, campo0, normal)
                            ws.write(row_num, 1, campo1, normal)
                            ws.write(row_num, 2, campo2, normal)
                            ws.write(row_num, 3, campo3, normal)
                            ws.write(row_num, 4, campo4, normal)
                            row_num += 1
                            c +=1
                    wb.save(response)
                    return response

                except Exception as e:
                    print(e)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            if action == 'reportepracticasenfermeria_pdf':
                try:
                    # REPORTE PARA LA CARRERA DE ENFERMERIA
                    #id_carreras = [1, 110]  # ENFERMERIAS Y LICENCIATURA EN ENFERMERIA
                    idcoord = 1  # Coordinacion de FACS
                    coordinacion = Coordinacion.objects.get(id=idcoord)
                    tutorias = ProfesorDistributivoHoras.objects.filter(status=True,
                                                                        carrera__coordinacion__id=idcoord,
                                                                        periodo=periodo,
                                                                        profesor__horariotutoriaacademica__isnull=False) \
                        .order_by('profesor_id').distinct('profesor_id')
                    data['tutorias'] = tutorias
                    data['periodo'] = periodo
                    data['coordinacion'] = coordinacion
                    data['fecha'] = datetime.now().date()
                    return conviert_html_to_pdf(
                        'adm_criteriosactividadesdocente/reporte_tutoria_enfermeria.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            if action == 'reportepracticasgeneral_pdf':
                try:
                    codcarrera = 0
                    coordinacion = None
                    data['es_decano'] = False
                    fechahoy = datetime.now().date()
                    # Crear una fecha con el primer día del mes actual
                    primer_dia_mes_actual = fechahoy.replace(day=1)
                    data['fechafin'] = fechafin = primer_dia_mes_actual - timedelta(days=1)

                    # data['fechainicio'] = str(periodo.inicio.strftime("%d-%m-%Y"))
                    # data['fechafin'] = str(fechafin.strftime("%d-%m-%Y"))

                    filtro = Q(status=True)
                    if es_decano:
                        data['es_decano'] = True
                        data['codcarrera'] = codcarrera = int(request.GET['cod_carrera'])
                        codcoordinacion = querydecano.values_list('coordinacion_id', flat=True)
                        if codcarrera == 0:
                            if codcoordinacion == 2 or codcoordinacion == 3:
                                codcoordinacion = (2, 3)
                            else:
                                codcoordinacion = (codcoordinacion,)
                            filtro &= Q(carrera__coordinacion__id__in=codcoordinacion)
                        else:
                            filtro &= Q(carrera__id=codcarrera)
                        coordinacion = Coordinacion.objects.filter(pk__in=codcoordinacion, status=True).first()

                    if es_director_carr:
                        mallacarreras = Malla.objects.filter(status=True,
                                                             carrera__in=director_car.values_list('carrera', flat=True))
                        carreras = []
                        for carr in mallacarreras:
                            if carr.uso_en_periodo(periodo):
                                codcarrera = carr.carrera.id
                                coordinacion = Coordinacion.objects.get(pk__in=[carr.carrera.mi_coordinacion2()], status = True)
                                filtro &= Q(carrera__id=codcarrera)
                    if codcarrera > 0:
                        data['nomcarrera'] = nomcarrera = Carrera.objects.filter(status=True, pk=codcarrera).first()
                    tutorias = ProfesorDistributivoHoras.objects.filter(filtro,periodo=periodo,profesor__horariotutoriaacademica__isnull=False).order_by('carrera__nombre','profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres','profesor_id').distinct('carrera__nombre','profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres','profesor_id')
                    data['periodo'] = periodo
                    data['coordinacion'] = coordinacion
                    data['fecha'] = datetime.now().date()
                    data['tutoriaacademica'] = DetalleDistributivo.objects.filter(status=True, distributivo__in = tutorias.values_list('id',flat=True),criteriodocenciaperiodo__criterio=124).order_by('distributivo__carrera__nombre','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__profesor__persona_id').distinct('distributivo__carrera__nombre','distributivo__profesor__persona__apellido1','distributivo__profesor__persona__apellido2','distributivo__profesor__persona__nombres','distributivo__profesor__persona_id')
                    return conviert_html_to_pdf(
                        'adm_criteriosactividadesdocente/reporte_tutoria_V2.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            if action == 'detalleevidencia':
                try:
                    data = {}
                    detalle = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(request.GET['id']))
                    data['listadoanexos'] = detalle.anexoevidenciaactividad_set.filter(status=True)
                    data['permiso'] = detalle
                    data['detallepermiso'] = detalle.historialaprobacionevidenciaactividad_set.all()
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    # data['aprobadores'] = detalle.permisoaprobacion_set.all()
                    template = get_template("adm_criteriosactividadesdocente/detalle_aprobarevidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'firmadocumento':
                try:
                    detalle=EvidenciaActividadDetalleDistributivo.objects.get(id=request.GET['id'])
                    data['archivo'] = archivo = detalle.archivo.url
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = detalle.id
                    data['action_firma'] = 'firmadocumento'
                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'solicitudinforme':
                try:
                    data['title'] = u'Solicitudes de informes'
                    search, filtro, url_vars = None, Q(status=True), ''
                    firmado = '0'
                    puedesdescargar = False
                    esautoridad = False
                    if 'firmado' in request.GET:
                        firmado=request.GET['firmado']
                    data['es_decano'] = es_decano = ResponsableCoordinacion.objects.values('id').filter(periodo=periodo, status=True, persona=persona, tipo=1).exists()
                    data['es_coordinador'] = es_coordinador = CoordinadorCarrera.objects.values('id').filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True).exists()
                    if es_decano:
                        puedesdescargar = True
                    data['puedesdescargar'] = puedesdescargar

                    flrectorado = Q(denominacionpuesto__id__in=variable_valor('ID_DENOMINACIONPUESTO_RECTOR_VICERRECTORES'), status=True)
                    esrectorado = persona.distributivopersona_set.filter(flrectorado).exists()
                    if es_decano or es_coordinador or esrectorado:
                        esautoridad = True
                        filter = Q(informe__distributivo__periodo=periodo, personafirmas=persona, firmado=firmado, informe__distributivo__profesor__persona__real=True, status=True)
                    else:
                        filter = Q(informe__distributivo__periodo=periodo, firmado=1, estado=4, informe__estado=4, informe__distributivo__profesor__persona__real=True, status=True)
                        firmado = '1'
                    data['esautoridad'] = esautoridad
                    url_vars += f'&firmado={firmado}'
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        url_vars += f'&s={search}'
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filter &= Q(Q(informe__distributivo__profesor__persona__nombres__icontains=search) | Q(informe__distributivo__profesor__persona__apellido1__icontains=search) | Q(informe__distributivo__profesor__persona__apellido2__icontains=search) | Q(informe__distributivo__profesor__persona__cedula__icontains=search) | Q(informe__distributivo__profesor__persona__pasaporte__icontains=search))
                        else:
                            filter &= Q(Q(informe__distributivo__profesor__persona__apellido1__icontains=ss[0]) & Q(informe__distributivo__profesor__persona__apellido2__icontains=ss[1]))

                    numerofilas = 25
                    if mes := int(request.GET.get('mes', 0)):
                        data['nMes'] = mes
                        filter &= Q(informe__fechafin__month=mes)
                        url_vars += f'&mes={mes}'

                    listadosolicitudes = HistorialInforme.objects.filter(filter).exclude(informe__distributivo__profesor__persona__in=DistributivoPersona.objects.values_list('persona', flat=True).filter(flrectorado)).exclude(estado=2).order_by('-informe__estado','-informe__fechafin')

                    paging = MiPaginador(listadosolicitudes, numerofilas)
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

                    fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.inicio, until=periodo.fin))
                    envioemail = periodo.coordinadorcarrera_set.values('id').filter(persona=persona, sede_id=1, tipo=3, status=True).exists()

                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['numerofilasguiente'] = numerofilasguiente
                    data['numeropagina'] = p
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['listadosolicitudes'] = page.object_list
                    fechaactual = datetime.now()
                    data['horasegundo'] = fechaactual.strftime('%Y%m%d_%H%M%S')
                    data['firmado'] = firmado
                    data['es_decano'] = es_decano
                    data['envioemail'] = envioemail
                    data['esrectorado'] = esrectorado
                    data['listadomeses'] = [fm for fm in fechas_mensuales]
                    data['generar_informe'] = int(fechaactual.day) > variable_valor('DIA_LIMITE_INFORME_MENSUAL')
                    ids_coordinacion = [1, 2, 3, 4, 5, 12, 25, 31, 32]
                    if querydecano.exists():
                        ids_coordinacion = querydecano.values_list('coordinacion__id', flat=True)
                    data['coordinaciones'] = Coordinacion.objects.filter(pk__in=ids_coordinacion, status=True)
                    return render(request, 'adm_criteriosactividadesdocente/solicitudinforme.html', data)
                except Exception as ex:
                    pass

            elif action == 'addinforme':
                try:
                    data['evidencia'] = HistorialInforme.objects.get(pk=request.GET['id'])
                    form = InformeForm()
                    data['form'] = form
                    template = get_template("adm_criteriosactividadesdocente/addinforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addjustificacion':
                try:
                    data['evidencia'] = HistorialInforme.objects.get(pk=request.GET['id'])
                    form = JustificarInformeForm()
                    data['form'] = form
                    template = get_template("adm_criteriosactividadesdocente/addinforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'listadoperiodoinformes':
                try:
                    mesesperiodo = []
                    solomes = []
                    es_decano = ResponsableCoordinacion.objects.values('id').filter(periodo=periodo, status=True, persona=persona, tipo=1).exists()
                    es_coordinador = CoordinadorCarrera.objects.values('id').filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True).exists()
                    if es_decano or es_coordinador:
                        listadomeses = HistorialInforme.objects.values_list('informe__fechainicio__month', flat=True).filter(informe__distributivo__periodo=periodo, personafirmas=persona, firmado=True, estado=4, informe__estado=4, status=True).distinct().order_by('informe__fechainicio')
                    else:
                        listadomeses = HistorialInforme.objects.values_list('informe__fechainicio__month', flat=True).filter(informe__distributivo__periodo=periodo, firmado=True, estado=4, informe__estado=4, status=True).distinct().order_by('informe__fechainicio')
                    for lmes in listadomeses:
                        if lmes not in solomes:
                            mesesperiodo.append([lmes, nombremes(lmes).upper()])
                            solomes.append(lmes)
                    data = {"results": "ok", 'mesesperiodo': mesesperiodo}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listadodocentesfaltantes':
                try:
                    temp = listado_docentes_faltantes(request)
                    data = {"results": "ok", 'listadofantantesdocentes': temp}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'detalleinforme':
                try:
                    data = {}
                    data['informe'] = informe = InformeMensualDocente.objects.get(pk=int(request.GET['id']))
                    data['historial'] = informe.historialinforme_set.filter(status=True).order_by('id')
                    template = get_template("pro_cronograma/detalleinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalleinformetotal':
                try:
                    data = {}
                    listadomeses = []
                    fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.inicio, until=periodo.fin))
                    mes = 0
                    for fechames in fechas_mensuales:
                        listadomeses.append(fechames)
                        mes = fechames.month
                    if 'idmes' in request.GET:
                        mes = request.GET['idmes']

                    data['anioselected'] = numeroanio = request.GET.get('idanio', datetime.now().year)
                    data['meselec'] = int(mes)
                    data['periodolec'] = Periodo.objects.get(pk=periodo.id)
                    data['listadomeses'] = listadomeses
                    idsdocentesexcluir = excluir_docentes_inicio_fin_actividad(numeroanio, mes, periodo)
                    es_revisorinformefacultades = persona.usuario.has_perm('inno.puede_visualizar_detalle_informe_facultades')
                    es_decano = ResponsableCoordinacion.objects.values('id').filter(periodo=periodo, status=True, persona=persona, tipo=1).exists()
                    es_coordinador = CoordinadorCarrera.objects.values('id').filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True).exists()
                    if es_decano and not es_revisorinformefacultades:
                        if profesor := persona.profesor():
                            idsdocentesexcluir = list(idsdocentesexcluir) + [profesor.pk]
                        coordinaciones = ResponsableCoordinacion.objects.values_list('coordinacion_id', flat=True).filter(periodo=periodo, status=True, persona=persona, tipo=1)
                        data['listadodistributivo'] = listadodistributivo = ProfesorDistributivoHoras.objects \
                            .values('coordinacion_id', 'coordinacion__alias', 'carrera_id', 'carrera__nombre', 'carrera__modalidad', 'coordinacion__nombre') \
                            .filter(coordinacion__in=coordinaciones, periodo_id=periodo.id, carrera__isnull=False, status=True, profesor__persona__real=True).exclude(profesor__id__in=idsdocentesexcluir) \
                            .annotate(total_profesores=Count('id', distinct=True),
                                      profesores_apro_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=4, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes))),
                                      profesores_rev_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=3, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes))),
                                      profesores_fir_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=2, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes))),
                                      todos_informes_firmados=Value(int(mes), output_field=IntegerField())
                                ).order_by('coordinacion_id', 'carrera__nombre').distinct()

                    else:
                        if es_coordinador and not es_revisorinformefacultades:
                            carreras = CoordinadorCarrera.objects.values_list('carrera_id', flat=True).filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True)
                            data['listadodistributivo'] = ProfesorDistributivoHoras.objects \
                                .values('coordinacion_id', 'coordinacion__alias', 'carrera_id', 'carrera__nombre', 'carrera__modalidad', 'coordinacion__nombre') \
                                .filter(coordinacion__isnull=False, periodo_id=periodo.id, carrera_id__in=carreras, status=True, profesor__persona__real=True).exclude(profesor__id__in=idsdocentesexcluir) \
                                .annotate(total_profesores=Count('id', distinct=True),
                                          profesores_apro_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=4, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes))),
                                          profesores_rev_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=3, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes))),
                                          profesores_fir_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=2, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes)))).order_by('coordinacion_id', 'carrera__nombre').distinct()
                        else:
                            data['listadodistributivo'] = ProfesorDistributivoHoras.objects \
                                .values('coordinacion_id', 'coordinacion__alias', 'carrera_id', 'carrera__nombre', 'carrera__modalidad', 'coordinacion__nombre') \
                                .filter(coordinacion__isnull=False, periodo_id=periodo.id, carrera__isnull=False, status=True, profesor__persona__real=True).exclude(profesor__id__in=idsdocentesexcluir) \
                                .annotate(total_profesores=Count('id', distinct=True),
                                          profesores_apro_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=4, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes))),
                                          profesores_rev_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=3, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes))),
                                          profesores_fir_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=2, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=int(mes)))).order_by('coordinacion_id', 'carrera__nombre').distinct()

                    data['es_decano'] = es_decano
                    data['es_revisorinformefacultades'] = es_revisorinformefacultades
                    template = get_template("pro_cronograma/detalleinformetotal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'firmarinformesmasivo':
                try:
                    ids = None
                    if 'ids' in request.GET:
                        ids = request.GET['ids']
                    leadsselect = ids
                    docentes_cumplimiento_justificar = 0
                    if docentes_cumplimiento := HistorialInforme.objects.values_list('informe', flat=True).filter(status=True, pk__in=leadsselect.split(','), informe__promedio__lt=100).order_by('informe').distinct():
                        docentes_cumplimiento_justificar = len(docentes_cumplimiento) - len(HistorialJustificaInforme.objects.values_list('informe', flat=True).filter(status=True, informe__in=docentes_cumplimiento).order_by('informe').distinct())
                    data['docentes_cumplimiento_justificar'] = docentes_cumplimiento_justificar
                    data['listadoseleccion'] = leadsselect
                    data['accionfirma'] = 'firmarinformemasivo'
                    template = get_template("adm_criteriosactividadesdocente/firmarinformesmasivo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

            if action == 'reporte_cumplimiento_actividades':
                try:

                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso', titulo='Excel porcentaje de cumplimiento de actividades mensuales del docente', destinatario=persona, url='', prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2, en_proceso=True)
                    noti.save(request)

                    reporte_general_porcentaje_cumplimiento_background(request=request, data=data, notiid=noti.pk, periodo=periodo).start()

                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            if action == 'reporte-docentes-faltantes':
                try:
                    now = datetime.now()
                    m = datetime(now.year, int(request.GET.get('numeromes', now.month)), 1)
                    mes = nombremes(m).__str__().upper()
                    data = listado_docentes_faltantes(request)

                    nombre_archivo = generar_nombre(f"{data.__len__()}_reporte_faltantes_entrega_", '') + '.xls'
                    __author__ = 'Unemi'
                    titulo = easyxf('font: name Verdana, color-index black, bold on , height 350; alignment: horiz centre;borders: left thin, right thin, top thin, bottom thin')
                    titulo2 = easyxf('font: name Verdana, color-index black, bold on , height 250; alignment: horiz centre;borders: left thin, right thin, top thin, bottom thin')
                    encabesado_tabla = easyxf('font: name Verdana , bold on , height 150; alignment: horiz left;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour gray25')
                    fuentecabecera = easyxf('font: name Verdana, bold on, color-index black, height 150; alignment: vert distributed, horiz left; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalred = easyxf('font: name Verdana, color-index red, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenumeroentero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('FALTANTES')
                    ws.write_merge(0, 0, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 4, 'LISTADO DE DOCENTES QUE NO GENERARON SU INFORME EN EL MES DE %s' % mes, titulo2)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = f'attachment; filename={nombre_archivo}'

                    ws.col(0).width = 2000
                    ws.col(1).width = 15000
                    ws.col(2).width = 15000
                    ws.col(3).width = 15000
                    ws.col(4).width = 10000

                    row_num = 2

                    ws.write(row_num, 0, "Nº", encabesado_tabla)
                    ws.write(row_num, 1, "DOCENTE", encabesado_tabla)
                    ws.write(row_num, 2, "COORDINACIÓN", encabesado_tabla)
                    ws.write(row_num, 3, "CARRERA", encabesado_tabla)
                    ws.write(row_num, 4, "NOTIFICACIONES", encabesado_tabla)

                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    c = 1
                    row_num = 3
                    for d in data:
                        ws.write(row_num, 0, "%s" % c, fuentenormal)
                        ws.write(row_num, 1, "%s" % e if (e := d['docente']) else '', fuentenormal)
                        ws.write(row_num, 2, "%s" % e if (e := d['coordinacion']) else '', fuentenormal)
                        ws.write(row_num, 3, "%s" % e if (e := d['carrera']) else '', fuentenormal)
                        ws.write(row_num, 4, "%s" % e if (e := d['num_notify']) else '', fuentenormal)
                        row_num += 1
                        c += 1
                    wb.save(response)

                    return response
                except Exception as ex:
                    pass

            if action == 'reporteinformejustificados':
                try:
                    now = datetime.now()
                    todos_mes = int(request.GET.get('numeromes', 100)) == 100
                    todos_coor = int(request.GET.get('coordinacion', 100)) == 100
                    todos_carrera = int(request.GET.get('carrera', 100)) == 100
                    mes = 'TODOS LOS MESES'
                    month, year = int(request.GET.get('numeromes', now.month)), int(request.GET.get('year', now.year))
                    if not todos_mes:
                        mes = 'MES DE ' +nombremes(month).__str__().upper()

                    if _decano := ResponsableCoordinacion.objects.filter(periodo=periodo, persona=persona, tipo=1, status=True):
                        filtro = Q(status=True, informe__distributivo__profesor__persona__real=True, informe__distributivo__carrera__coordinacion__id__in=_decano.values_list('coordinacion_id', flat=True), informe__distributivo__periodo=periodo)
                        if not todos_mes: filtro &= Q(informe__fechafin__month=month, informe__fechafin__year=year)
                        if not todos_coor:
                            if cor := int(request.GET.get('coordinacion', 0)): filtro &= Q(informe__distributivo__carrera__coordinacion__id=cor)                        
                        if not todos_carrera:
                            if car := int(request.GET.get('carrera', 0)): filtro &= Q(informe__distributivo__carrera__id=car)
                        listado = HistorialJustificaInforme.objects.filter(filtro)

                    elif _director := CoordinadorCarrera.objects.filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True):
                        listado = HistorialJustificaInforme.objects.filter(status=True, informe__distributivo__profesor__persona__real=True, informe__distributivo__carrera__in=_director.values_list('carrera_id', flat=True), informe__distributivo__periodo=periodo)
                        if not todos_mes:
                            listado = listado.filter(informe__fechafin__month=month, informe__fechafin__year=year)

                    else:
                        filtro = Q(status=True, informe__distributivo__profesor__persona__real=True, informe__distributivo__periodo=periodo)
                        if not todos_mes:
                            filtro &= Q(informe__fechafin__month=month, informe__fechafin__year=year)

                        if cor := int(request.GET.get('coordinacion', 0)):
                            filtro &= Q(informe__distributivo__carrera__coordinacion__id=cor)

                        if car := int(request.GET.get('carrera', 0)):
                            filtro &= Q(informe__distributivo__carrera__id=car)

                        listado = HistorialJustificaInforme.objects.filter(filtro)

                    idsdocentesexcluir = list(excluir_docentes_inicio_fin_actividad(year, month, periodo))  # + decanofacultad
                    _exclude = DistributivoPersona.objects.filter(denominacionpuesto__id__in=list(map(int, variable_valor('ID_DENOMINACIONPUESTO_RECTOR_VICERRECTORES')))).values_list('persona', flat=True)
                    listado = listado.exclude(informe__distributivo__profesor__persona__in=_exclude).exclude(informe__distributivo__profesor__id__in=idsdocentesexcluir)

                    data = [{'docente': l.informe.distributivo.profesor.persona.nombre_completo_inverso(),
                             'porcentajecumplimiento': e.__str__() if (e := l.informe.promedio) else '',
                             'coordinacion': e.__str__() if (e := l.informe.distributivo.carrera.coordinacion_carrera()) else '',
                             'carrera': e.__str__() if (e := l.informe.distributivo.carrera) else '',
                             'descripcion': l.descripcion if l.descripcion else '',
                             'fecha': l.fecha.strftime('%d-%m-%Y') if l.fecha else '',
                             'persona_justifica': e.__str__() if (e := l.persona.nombre_completo_inverso()) else '',
                             'url_archivo': f'https://sga.unemi.edu.ec{l.archivo.url}' if l.archivo else ''
                             } for l in listado]

                    nombre_archivo = generar_nombre(f"{data.__len__()}_reporte_informe_justificados_", '') + '.xls'
                    __author__ = 'Unemi'
                    titulo = easyxf('font: name Verdana, color-index black, bold on , height 350; alignment: horiz centre;borders: left thin, right thin, top thin, bottom thin')
                    titulo2 = easyxf('font: name Verdana, color-index black, bold on , height 250; alignment: horiz centre;borders: left thin, right thin, top thin, bottom thin')
                    encabesado_tabla = easyxf('font: name Verdana , bold on , height 150; alignment: horiz left;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour gray25')
                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('FALTANTES')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 8, 'LISTADO DE DOCENTES QUE SE JUSTIFICÓ SU INFORME - %s' % mes, titulo2)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = f'attachment; filename={nombre_archivo}'

                    ws.col(0).width = 2000
                    ws.col(1).width = 10000
                    ws.col(2).width = 5000
                    ws.col(3).width = 15000
                    ws.col(4).width = 15000
                    ws.col(5).width = 20000
                    ws.col(6).width = 6000
                    ws.col(7).width = 10000
                    ws.col(8).width = 20000

                    row_num = 2

                    ws.write(row_num, 0, "Nº", encabesado_tabla)
                    ws.write(row_num, 1, "DOCENTE", encabesado_tabla)
                    ws.write(row_num, 2, "CUMPLIMIENTO", encabesado_tabla)
                    ws.write(row_num, 3, "COORDINACIÓN", encabesado_tabla)
                    ws.write(row_num, 4, "CARRERA", encabesado_tabla)
                    ws.write(row_num, 5, "DESCRIPCIÓN", encabesado_tabla)
                    ws.write(row_num, 6, "FECHA", encabesado_tabla)
                    ws.write(row_num, 7, "PERSONA JUSTIFICA", encabesado_tabla)
                    ws.write(row_num, 8, "ARCHIVO", encabesado_tabla)

                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    c = 1
                    row_num = 3
                    for d in data:
                        ws.write(row_num, 0, "%s" % c, fuentenormal)
                        ws.write(row_num, 1, "%s" % e if (e := d['docente']) else '', fuentenormal)
                        ws.write(row_num, 2, "%s" % e if (e := d['porcentajecumplimiento']) else '', fuentenormal)
                        ws.write(row_num, 3, "%s" % e if (e := d['coordinacion']) else '', fuentenormal)
                        ws.write(row_num, 4, "%s" % e if (e := d['carrera']) else '', fuentenormal)
                        ws.write(row_num, 5, "%s" % e if (e := d['descripcion']) else '', fuentenormal)
                        ws.write(row_num, 6, "%s" % e if (e := d['fecha']) else '', fuentenormal)
                        ws.write(row_num, 7, "%s" % e if (e := d['persona_justifica']) else '', fuentenormal)
                        ws.write(row_num, 8, "%s" % e if (e := d['url_archivo']) else '', fuentenormal)
                        row_num += 1
                        c += 1
                    wb.save(response)

                    return response
                except Exception as ex:
                    pass

            if action == 'terminoscondiciones':
                try:
                    if persona.id not in (25320, 26985):
                        return HttpResponseRedirect(request.path + f'?info=Estimad{"a" if persona.es_mujer() else "o"} {persona.nombres.split()[0].title()}, usted no tiene permiso para visualizar esta pantalla.')

                    data['title'] = "Adicionar terminos y condiciones"
                    data['terminos'] = TerminosCondiciones.objects.filter(status=True)
                    return render(request, 'adm_criteriosactividadesdocente/terminoscondiciones.html', data)
                except Exception as ex:
                    pass

            if action == 'addterminoscondiciones':
                try:
                    form = TerminosCondicionesForm()
                    data['form2'] = form
                    template = get_template("adm_criteriosactividadesdocente/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editterminoscondiciones':
                try:
                    model = TerminosCondiciones.objects.get(pk=request.GET['id'])
                    form = TerminosCondicionesForm(initial=model_to_dict(model))
                    data['form2'] = form
                    data['id'] = model.pk
                    template = get_template("adm_criteriosactividadesdocente/modal/formmodal.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action ==  'detalleterminoscondiciones':
                try:
                    model = TerminosCondiciones.objects.get(pk=request.GET['id'])
                    return JsonResponse({"result": 'ok', 'data': model.detalle, 'title': model.titulo})
                except Exception as ex:
                    pass

            if action == 'justificaciontutoriaacademica':
                try:
                    data['title'] = "Justificación de tutoría académica"
                    estado = int(request.GET.get('e', 1))
                    _filters = Q(Q(Q(periodo=periodo) | Q(horario__periodo=periodo)), estadojustificacion=estado, status=True)
                    url_vars = f'&action={action}&e={estado}'

                    if CoordinadorCarrera.objects.filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True).exists():
                        carreras = CoordinadorCarrera.objects.values_list('carrera_id', flat=True).filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, carrera__niveltitulacion_id=3, carrera__activa=True, status=True).exclude(carrera__coordinacionvalida=7)
                        _filters &= Q(horario__claseactividad__detalledistributivo__distributivo__carrera__in=carreras)


                    carreras = Carrera.objects.filter(id__in=RegistroClaseTutoriaDocente.objects.filter(_filters).values_list('horario__claseactividad__detalledistributivo__distributivo__carrera', flat=True), niveltitulacion_id=3, activa=True, status=True).exclude(coordinacionvalida=7)

                    if c := int(request.GET.get('c', 0)):
                        _filters &= Q(horario__claseactividad__detalledistributivo__distributivo__carrera_id=c)
                        url_vars += f'&c={c}'

                    if s := request.GET.get('s', ''):
                        url_vars += f'&s={s}'
                        fullname = s.split()
                        if fullname.__len__() == 1:
                            _filters &= Q(Q(horario__profesor__persona__apellido1__unaccent__icontains=fullname[0]) | Q(horario__profesor__persona__apellido2__unaccent__icontains=fullname[0]) | Q(horario__profesor__persona__nombres__unaccent__icontains=fullname[0]) | Q(horario__profesor__persona__cedula__unaccent__icontains=fullname[0]))
                        if fullname.__len__() == 2:
                            _filters &= Q(Q(horario__profesor__persona__apellido1__unaccent__icontains=fullname[0], horario__profesor__persona__apellido2__unaccent__icontains=fullname[1]) | Q(horario__profesor__persona__apellido1__unaccent__icontains=fullname[1], horario__profesor__persona__apellido2__unaccent__icontains=fullname[0]))
                        if fullname.__len__() == 4:
                            _filters &= Q(horario__profesor__persona__apellido1__unaccent__icontains=fullname[0], horario__profesor__persona__apellido2__unaccent__icontains=fullname[1], horario__profesor__persona__nombres__unaccent__icontains=f"{fullname[2]} {fullname[3]}")

                    paging = MiPaginador(RegistroClaseTutoriaDocente.objects.filter(_filters).order_by('-fecha'), 10)
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
                    data['url_vars'] = url_vars
                    data['justificaciones'] = page.object_list
                    data['carreras'] = carreras
                    data['estado'] = estado
                    data['search'] = s
                    data['carrera'] = c
                    return render(request, 'adm_criteriosactividadesdocente/justificaciontutoriaacademica.html', data)
                except Exception as ex:
                    pass

            if action == 'solicitudaperturaclase':
                try:
                    data['es_decano'] = es_decano = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, persona=persona, tipo=1).exists() or user.is_superuser
                    if not es_decano:
                        return HttpResponseRedirect("/adm_criteriosactividadesdocente?info='Solo los decanos tienen acceso a esta opción'")
                    data['title'] = "Solicitudes de apertura de clases vituales"
                    estado = int(request.GET.get('estado', 1))
                    _f = Q(status=True, estado=estado)

                    data['solicitudes'] = SolicitudAperturaClaseVirtual.objects.filter(periodo=periodo, estadosolicitud=estado, status=True)
                    data['estado'] = estado
                    return render(request, 'adm_criteriosactividadesdocente/solicitudclasesvirtuales.html', data)
                except Exception as ex:
                    pass

            if action == 'gestionarsolicitud':
                try:
                    data['es_decano'] = es_decano = ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, persona=persona, tipo=1).exists() or user.is_superuser
                    if not es_decano:
                        return HttpResponseRedirect("/adm_criteriosactividadesdocente?info='Solo los decanos tienen acceso a esta opción'")
                    data['solicitud'] = solicitud = SolicitudAperturaClaseVirtual.objects.filter(status=True, id=int(encrypt(request.GET['id']))).first()
                    if not solicitud:
                        raise NameError('Solicitud no encontrada')
                    data['action'] = action
                    form = GestionarAperturaClaseVirtualForm()
                    data['form'] = form
                    template = get_template("adm_criteriosactividadesdocente/modal/gstionarsolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'actualiza_estado_evidencia_criterios_varios':
                try:
                    _response = actualiza_estado_evidencia_criterios_varios(request, periodo)
                    return JsonResponse({"result": True, 'data': _response})
                except Exception as ex:
                    pass

            if action == 'reporte_remediales':
                try:
                    now = datetime.now()
                    yd, yh = request.GET.get('yd', 2022), request.GET.get('yh', now.year)
                    periodos = Periodo.objects.values_list('id', flat=True).filter(nombre__icontains='REMEDIAL', fin__year__gte=yd, fin__year__lte=yh, status=True)
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte_remediales_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [(u"N°", 4000), (u"ASIGNATURA", 12000), (u"PARALELO", 4000), (u"PERIODO", 10000), (u"INSCRITOS", 4500), (u"APROBADOS", 4500), (u"REPROBADOS", 4500), (u"EN CURSO", 4500), (u"HORAS", 4500), (u"CARRERA", 12000)]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num, cont = 2, 0
                    for m in Materia.objects.filter(nivel__periodo__in=periodos, status=True):
                        cont += 1
                        cApr = m.materiaasignada_set.filter(estado=1, retiramateria=False, retiromanual=False, status=True).count()
                        cRep = m.materiaasignada_set.filter(estado=2, retiramateria=False, retiromanual=False, status=True).count()
                        cCur = m.materiaasignada_set.filter(estado=3, retiramateria=False, retiromanual=False, status=True).count()
                        inscritos = m.materiaasignada_set.filter(retiramateria=False, retiromanual=False, status=True).count()
                        ws.write(row_num, 0, cont, font_style2)
                        ws.write(row_num, 1, f"{m.asignaturamalla.asignatura.nombre}", font_style2)
                        ws.write(row_num, 2, f"{m.paralelo}", font_style2)
                        ws.write(row_num, 3, f"{m.nivel.periodo.nombre}", font_style2)
                        ws.write(row_num, 4, f"{inscritos}", font_style2)
                        ws.write(row_num, 5, f"{cApr}", font_style2)
                        ws.write(row_num, 6, f"{cRep}", font_style2)
                        ws.write(row_num, 7, f"{cCur}", font_style2)
                        ws.write(row_num, 8, f"{m.horassemanales}", font_style2)
                        ws.write(row_num, 9, f"{m.carrera()}", font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex=}")

            elif action == 'reportemensualcumplimiento':
                try:
                    mes_selected = int(request.GET.get('id_mes'))
                    if es_director_carr:
                        mallacarreras = Malla.objects.filter(status=True,carrera__in=director_car.values_list('carrera', flat=True))
                        carreras = []
                        for carr in mallacarreras:
                            if carr.uso_en_periodo(periodo):
                                codcarrera = carr.carrera.id
                                coordinacion = Coordinacion.objects.get(pk__in=[carr.carrera.mi_coordinacion2()])
                    else:
                        coordinacion = Coordinacion.objects.get(pk=request.GET['cod_facultad'])
                        codcarrera = int(request.GET['cod_carrera'])

                    if mes_selected <= 0:
                        return JsonResponse({"result": False, "mensaje": u"Debe seleccionar un mes valido"})
                    fecha_año = list(rrule(YEARLY, dtstart=periodo.inicio, until=periodo.fin))
                    finicio = date(fecha_año[0].year, mes_selected, 1)
                    siguiente_mes = finicio.replace(day=28) + timedelta(days=4)
                    ffin = siguiente_mes - timedelta(days=siguiente_mes.day)

                    now = datetime.now()
                    # finicio, ffin = date(now.year, mes_selected, 1), date(now.year, mes_selected, calendar.monthrange(now.year, mes_selected)[1])


                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Reporte consolidado de cumplimiento de actividades y recursos de aprendizaje',
                                        destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_cumplimiento_background_v3(request=request, notiid=noti.pk, periodo=periodo, coordinacion=coordinacion, codcarrera=codcarrera, finicio=finicio, ffin=ffin, nompersona = persona.nombre_completo_inverso(), tipo='pdf').start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex=}")
                    return JsonResponse({"result": False,"mensaje": u"Ha ocurrido un error en la generación del reporte."})

            elif action == 'descargarplanificados':
                try:
                    idfac=request.GET['idfac']
                    numeromes=request.GET['numeromes']
                    numeroanio=request.GET.get('anio', datetime.now().year)
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    formatorojo = workbook.add_format({'bold': True, 'font_color': 'red'})

                    filtro = Q(coordinacion_id=idfac, periodo_id=periodo.id, status=True, profesor__persona__real=True)
                    if c := request.GET.get('idcarr', 0):
                        filtro &= Q(carrera_id=c)

                    worksheet = workbook.add_worksheet("Listado")

                    worksheet.write(0, 0, 'N')
                    worksheet.write(0, 1, 'COORDINACION')
                    worksheet.write(0, 2, 'CARRERA')
                    worksheet.write(0, 3, 'DOCENTE')
                    worksheet.write(0, 4, 'FIRMADO POR DOCENTE')
                    worksheet.write(0, 5, 'FIRMADO POR DIRECTOR')
                    worksheet.write(0, 6, 'FIRMADO POR DECANO')
                    worksheet.write(0, 7, '% DE CUMPLIMIENTO')

                    worksheet.set_column('A:A', 10)
                    worksheet.set_column('B:B', 10)
                    worksheet.set_column(0, 2, width=50)
                    worksheet.set_column(0, 3, width=50)
                    worksheet.set_column(0, 4, width=50)
                    worksheet.set_column(0, 5, width=50)
                    idsdocentesexcluir = excluir_docentes_inicio_fin_actividad(numeroanio, numeromes, periodo)
                    if persona.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, status=True).exists() and persona.profesor():
                        idsdocentesexcluir = list(idsdocentesexcluir) + [persona.profesor().pk]

                    listadodistributivo = ProfesorDistributivoHoras.objects.values('id', 'coordinacion_id', 'coordinacion__nombre', 'carrera_id', 'carrera__nombre', 'carrera__modalidad', 'coordinacion__nombre', 'profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres') \
                        .filter(filtro).exclude(profesor__id__in=idsdocentesexcluir) \
                        .annotate(total_profesores=Count('id', distinct=True),
                                  profesores_apro_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=4, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=numeromes)),
                                  profesores_rev_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=3, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=numeromes)),
                                  profesores_fir_informe=Count('id', filter=Q(informemensualdocente__historialinforme__estado=2, informemensualdocente__historialinforme__firmado=True, informemensualdocente__fechafin__month=numeromes))) \
                        .order_by('coordinacion_id', 'carrera__nombre').distinct()
                    fil = 1
                    cont = 0
                    for ldoc in listadodistributivo:
                        cont += 1
                        worksheet.write(fil, 0, cont)
                        worksheet.write(fil, 1, ldoc['coordinacion__nombre'])
                        worksheet.write(fil, 2, ldoc['carrera__nombre'])
                        worksheet.write(fil, 3, ldoc['profesor__persona__apellido1'] + ' ' + ldoc['profesor__persona__apellido2'] + ' ' + ldoc['profesor__persona__nombres'])
                        if int(ldoc['profesores_fir_informe']) == 1:
                            worksheet.write(fil, 4, 'SI')
                        else:
                            worksheet.write(fil, 4, 'NO', formatorojo)
                        if int(ldoc['profesores_rev_informe']) == 1:
                            worksheet.write(fil, 5, 'SI')
                        else:
                            worksheet.write(fil, 5, 'NO', formatorojo)
                        if int(ldoc['profesores_apro_informe']) == 1:
                            worksheet.write(fil, 6, 'SI')
                        else:
                            worksheet.write(fil, 6, 'NO', formatorojo)

                        informe = InformeMensualDocente.objects.filter(fechafin__year=numeroanio, fechafin__month=numeromes, distributivo=ldoc['id'], status=True).first()
                        worksheet.write(fil, 7, informe.promedio if informe else 0)
                        fil += 1
                    workbook.close()
                    output.seek(0)
                    filename = 'reporte_informesfirmados' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex=}")

            return HttpResponseRedirect(request.path)  # ===============================================================================================================
        else:
            try:
                url_vars = ''
                search = None
                if not request.user.has_perm('sga.puede_visible_periodo'):
                    if not request.session['periodo'].visible:
                        return HttpResponseRedirect("/?info=Periodo Inactivo.")
                ids = None
                if 'search_criterio' in request.session:
                    del request.session['search_criterio']
                if 'idc_criterio' in request.session:
                    del request.session['idc_criterio']
                periodo = request.session['periodo']
                data['coordinaciones'] = coordinaciones = persona.mis_coordinaciones()
                data['listadocarreras'] = carreras = Carrera.objects.filter(status=True).order_by('nombre')
                data['listadocarreraspregradovirtual'] = carreras.filter(status=True).order_by('nombre')
                periodoposgrado = False
                if periodo.tipo_id in [3, 4]:
                    periodoposgrado = True
                data['periodoposgrado'] = periodoposgrado
                if 'idc' in request.GET:
                    data['idc'] = idc = int(request.GET['idc'])
                    url_vars += f'&idc={idc}'
                else:
                    # data['idc'] = idc = coordinaciones[0].id
                    data['idc'] = idc = 0
                    url_vars += f'&idc={idc}'
                if 's' in request.GET:
                    search = request.GET['s']
                    url_vars += f'&s={search}'
                    ss = search.split(' ')
                    if len(ss) == 2:
                        if idc:
                            profesores = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=[idc], periodo=periodo).filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                                                                                                      Q(profesor__persona__apellido2__icontains=ss[1])).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                        else:
                            profesores = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=coordinaciones, periodo=periodo).filter(Q(profesor__persona__apellido1__icontains=ss[0]) &
                                                                                                                                               Q(profesor__persona__apellido2__icontains=ss[1])).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()

                    else:
                        if idc:
                            f'&idc={idc}'
                            profesores = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=[idc], periodo=periodo).filter(Q(profesor__persona__nombres__icontains=search) |
                                                                                                                                      Q(profesor__persona__apellido1__icontains=search) |
                                                                                                                                      Q(profesor__persona__apellido2__icontains=search) |
                                                                                                                                      Q(profesor__persona__cedula__icontains=search)).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                        else:
                            profesores = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=coordinaciones, periodo=periodo).filter(Q(profesor__persona__nombres__icontains=search) |
                                                                                                                                               Q(profesor__persona__apellido1__icontains=search) |
                                                                                                                                               Q(profesor__persona__apellido2__icontains=search) |
                                                                                                                                               Q(profesor__persona__cedula__icontains=search)).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    if idc:
                        profesores = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=[idc], periodo=periodo).filter(id=ids).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                    else:
                        profesores = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=coordinaciones, periodo=periodo).filter(id=ids).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                else:
                    if idc:
                        profesores = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=[idc], periodo=periodo).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                    else:
                        profesores = ProfesorDistributivoHoras.objects.filter(coordinacion__id__in=coordinaciones, periodo=periodo).order_by('-profesor__persona__usuario__is_active', 'profesor').distinct()
                numerofilas = 25
                paging = MiPaginador(profesores, numerofilas)
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
                ids_distributivos_pagina = [distributivo.id for distributivo in page.object_list]

                distributivos_con_anotacion = ProfesorDistributivoHoras.objects.filter(id__in=ids_distributivos_pagina).\
                    annotate(total_cridocencia=Count('id', filter=Q(detalledistributivo__criteriodocenciaperiodo__isnull=False, detalledistributivo__criteriodocenciaperiodo__criterio__tipo=1)),
                             total_crivinculacion=Count('id', filter=Q(detalledistributivo__criteriodocenciaperiodo__isnull=False, detalledistributivo__criteriodocenciaperiodo__criterio__tipo=2)),
                             total_criinvestigacion=Count('id', filter=Q(detalledistributivo__criterioinvestigacionperiodo__isnull=False)),
                             total_crigestion=Count('id', filter=Q(detalledistributivo__criteriogestionperiodo__isnull=False)))

                request.session['paginador'] = p
                data['paging'] = paging
                data['numerofilasguiente'] = numerofilasguiente
                data['numeropagina'] = p
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
                data['reporte_2'] = obtener_reporte('actividades_horas_docente_facu')
                data['reporte_3'] = obtener_reporte('actividades_horas_docente_facu_profesor')
                data['ids'] = ids if ids else ""
                data['idc'] = idc if idc else "0"
                # data['distributivos'] = page.object_list
                data['distributivos'] = distributivos_con_anotacion
                if Periodo.objects.filter(pk=periodo.id, status=True):
                    periodomigar = Periodo.objects.get(pk=periodo.id, status=True)
                    idperiodomigar = periodomigar.id
                else:
                    periodomigar = None
                    idperiodomigar = 0
                data['periodomigrar'] = periodomigar
                data['idperiodomigrar'] = idperiodomigar
                data['meses'] = extraer_meses_periodo(periodo)
                data['form2'] = FechaNotificacionEvaluacionForm()
                data['PUEDE_VER_TERMINOS_CONDICIONES'] = (25320, 26985)
                data["url_vars"] = url_vars
                data['es_decano'] =  ResponsableCoordinacion.objects.filter(periodo=periodo, status=True, persona=persona, tipo=1).exists() or user.is_superuser
                data['es_coordinador'] = CoordinadorCarrera.objects.filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True).exists() or user.is_superuser
                return render(request, "adm_criteriosactividadesdocente/view.html", data)
            except Exception as ex:
                pass


def listado_docentes_faltantes(request):
    try:
        now = datetime.now()
        decanofacultad = []
        periodo, persona = request.session.get('periodo'), request.session.get('persona')
        coordinaciones, listadofaltantes = None, ProfesorDistributivoHoras.objects.none()
        month, year = int(request.GET.get('numeromes', 0)), int(request.GET.get('year', now.year))
        if not request.GET.get('todas', 0):
            if ResponsableCoordinacion.objects.filter(periodo=periodo, persona=persona, tipo=1, status=True).exists():
                decanofacultad = [persona.profesor().pk] if persona.profesor() else []
                coordinaciones = ResponsableCoordinacion.objects.values_list('coordinacion_id').filter(periodo=periodo, persona=persona, tipo=1, status=True)
                docentesfirmaron = HistorialInforme.objects.values_list('informe__distributivo__profesor_id').filter(informe__fechafin__month=month, informe__fechafin__year=year,  informe__distributivo__periodo=periodo, informe__distributivo__coordinacion_id__in=coordinaciones, estado=2, status=True)
                listadofaltantes = ProfesorDistributivoHoras.objects.filter(periodo=periodo, coordinacion_id__in=coordinaciones, profesor__persona__real=True, status=True).exclude(profesor_id__in=docentesfirmaron).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')

            else:
                if CoordinadorCarrera.objects.filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True).exists():
                    carreras = CoordinadorCarrera.objects.values_list('carrera_id').filter(periodo=periodo, persona=persona, sede_id=1, tipo=3, status=True)
                    docentesfirmaron = HistorialInforme.objects.values_list('informe__distributivo__profesor_id').filter(informe__fechafin__month=month, informe__fechafin__year=year, informe__distributivo__periodo=periodo, informe__distributivo__carrera_id__in=carreras, estado=2, status=True)
                    listadofaltantes = ProfesorDistributivoHoras.objects.filter(periodo=periodo, carrera_id__in=carreras, profesor__persona__real=True, status=True).exclude(profesor_id__in=docentesfirmaron).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
        else:
            filtro = Q(periodo=periodo, profesor__persona__real=True, status=True)

            if cor := int(request.GET.get('coordinacion', 0)):
                filtro &= Q(carrera__coordinacion__id=cor)

            if car := int(request.GET.get('carrera', 0)):
                filtro &= Q(carrera__id=car)

            docentesfirmaron = HistorialInforme.objects.values_list('informe__distributivo__profesor_id').filter(informe__fechafin__month=month, informe__fechafin__year=year, informe__distributivo__periodo=periodo, estado=2, status=True)
            listadofaltantes = ProfesorDistributivoHoras.objects.filter(filtro).exclude(profesor_id__in=docentesfirmaron).order_by('profesor__persona__apellido1')

        idsdocentesexcluir = list(excluir_docentes_inicio_fin_actividad(year, month, periodo)) #+ decanofacultad
        _exclude = DistributivoPersona.objects.filter(denominacionpuesto__id__in=list(map(int, variable_valor('ID_DENOMINACIONPUESTO_RECTOR_VICERRECTORES')))).values_list('persona', flat=True)
        return [{'docente': l.profesor.persona.nombre_completo_inverso(),
                 'coordinacion': e.__str__() if (e := l.coordinacion) else '',
                 'carrera': e.__str__() if (e := l.carrera) else '',
                 'estado': e.get_estado_display() if (e := l.informemensualdocente_set.filter(fechafin__month=month, status=True).first()) else 'PENDIENTE',
                 'profesordistributivohoras': l.pk,
                 'num_notify': l.historialrecordatoriogenerarinforme_set.filter(fechafininforme__month=month, fechafininforme__year=year, status=True).count()} for l in listadofaltantes.exclude(profesor__persona__in=_exclude).exclude(profesor__id__in=idsdocentesexcluir)]

    except Exception as ex:
        pass


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def extraer_meses_periodo(periodo):
    mes_inicio = periodo.inicio.month
    mes_fin = 1
    fecha_inicio = datetime(periodo.inicio.year, periodo.inicio.month, 1, 0, 0, 0).date()
    if datetime.now().date() < periodo.fin:
        fecha_limite = datetime.now().date() + relativedelta(months=-1)
    else:
        fecha_limite = periodo.fin + relativedelta(months=-1)
    for contador in range(1, 12):
        if fecha_inicio <= fecha_limite:
            fecha_inicio = fecha_inicio + relativedelta(months=+1)
            mes_fin = fecha_inicio.month
        else:
            break
    meses = []
    if mes_inicio > mes_fin:
        for mes in MESES_CHOICES[mes_inicio - 1:12]:
            meses.append([mes[0], mes[1]])
        for mes1 in MESES_CHOICES[0:mes_fin]:
            meses.append([mes1[0], mes1[1]])
    else:
        meses = MESES_CHOICES[mes_inicio - 1:mes_fin]
    return meses


def contar_dias_sin_finsemana(fechainicio, fechafin, periodo):
    contador = 0
    fechaini = fechainicio
    while fechaini <= fechafin:
        if fechaini.weekday() == 5:
            dias = timedelta(days=3)
        else:
            dias = timedelta(days=1)
        fechaini = fechaini + dias
        if not DiasNoLaborable.objects.values('id').filter(fecha=fechaini, periodo=periodo, activo=True).exclude(motivo__in=[2, 3]).exists():
            contador += 1
    return contador


def asistencia_tutoria(periodopk, desde, hasta, profesor):
    from inno.models import RegistroClaseTutoriaDocente, PeriodoAcademia
    try:
        periodo = Periodo.objects.get(id=periodopk)
        periodoacademia = PeriodoAcademia.objects.get(periodo=periodo)
        for dis in ProfesorDistributivoHoras.objects.filter(status=True, periodo=periodo, activo=True,
                                                            detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True, profesor_id=profesor).distinct():
            print('DOCENTE .... ---  .....: %s' % dis.profesor)
            if DetalleDistributivo.objects.filter(distributivo__profesor=dis.profesor,
                                                  distributivo__periodo=periodo, criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).exists():
                totalhoras = int(DetalleDistributivo.objects.filter(distributivo__profesor=dis.profesor,
                                                                    distributivo__periodo=periodo, criteriodocenciaperiodo__criterio_id__procesotutoriaacademica=True).aggregate(total=Sum('horas'))['total'])

                actividadestutoria = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor=dis.profesor,
                                                                   detalledistributivo__distributivo__periodo=periodo,
                                                                   detalledistributivo__criteriodocenciaperiodo__isnull=False,
                                                                   detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True)
                aprobacion = ClaseActividadEstado.objects.filter(status=True, periodo=periodo, estadosolicitud=2, profesor=dis.profesor).exists()

                # if HorarioTutoriaAcademica.objects.filter(status=True, profesor=dis.profesor,periodo=periodo).exists() and aprobacion:
                if actividadestutoria.exists() and aprobacion:
                    fecha = convertir_fecha(desde.strftime("%d-%m-%Y"))
                    while fecha != convertir_fecha(hasta.strftime("%d-%m-%Y")):
                        for actividad in actividadestutoria:
                            horario = HorarioTutoriaAcademica.objects.filter(status=True, profesor=dis.profesor, periodo=periodo,
                                                                             dia=actividad.dia, turno=actividad.turno)
                            for tut in horario:
                                if HorarioTutoriaAcademica.objects.filter(status=True, profesor=dis.profesor, periodo=periodo,
                                                                          dia=actividad.dia, turno=actividad.turno).count() > 1:
                                    if tut.en_uso():
                                        duplicados = HorarioTutoriaAcademica.objects.filter(status=True, profesor=dis.profesor, periodo=periodo,
                                                                                            dia=actividad.dia, turno=actividad.turno).values_list('id', flat=True)
                                        solicitudes = SolicitudTutoriaIndividual.objects.filter(status=True, horario_id__in=duplicados)
                                        if solicitudes:
                                            mayor = solicitudes.values('horario_id').annotate(cant=Count('id')).values_list('cant', 'horario_id').order_by('-cant')[0][1]
                                            for s in solicitudes:
                                                s.horario_id = mayor
                                                s.save()
                                            if not tut.en_uso() and not tut.id == mayor:
                                                tut.delete()
                                    else:
                                        tut.delete()

                            totalhoras = actividadestutoria.count()

                            if horario.exists():
                                horario = horario[0]
                                if horario.fecha_fin_horario_tutoria != convertir_fecha(periodoacademia.fecha_fin_horario_tutoria.strftime("%d-%m-%Y")):
                                    horario.fecha_fin_horario_tutoria = convertir_fecha(periodoacademia.fecha_fin_horario_tutoria.strftime("%d-%m-%Y"))
                                    horario.save()
                            else:
                                horario = HorarioTutoriaAcademica(profesor=dis.profesor, periodo=periodo, dia=actividad.dia, turno=actividad.turno, claseactividad=actividad)
                                horario.save()
                            if horario.dia == fecha.isoweekday():
                                cantasissemana = RegistroClaseTutoriaDocente.objects.filter(numerosemana=fecha.isocalendar()[1], horario__profesor=dis.profesor, horario__periodo=periodo).aggregate(total=Count('id'))['total']
                                if totalhoras > cantasissemana or not RegistroClaseTutoriaDocente.objects.filter(horario=horario,
                                                                                                                 numerosemana=fecha.isocalendar()[1],
                                                                                                                 fecha__date=fecha).exists():
                                    if not RegistroClaseTutoriaDocente.objects.filter(horario=horario,
                                                                                      numerosemana=fecha.isocalendar()[1],
                                                                                      fecha__date=fecha).exists():
                                        clasetutoria = RegistroClaseTutoriaDocente(horario=horario,
                                                                                   numerosemana=fecha.isocalendar()[1],
                                                                                   fecha=fecha)
                                        clasetutoria.save()
                                        print('Se ingresa tutoria: %s' % clasetutoria)
                        fecha = fecha + timedelta(days=1)
                else:
                    print('No tiene horario: %s' % dis)
                if  HorarioTutoriaAcademica.objects.filter(status=True, profesor=dis.profesor, periodo=periodo).exclude(dia__in=actividadestutoria.values_list('dia', flat=True)).exists():
                    for horario in HorarioTutoriaAcademica.objects.filter(status=True, profesor=dis.profesor, periodo=periodo).exclude(dia__in=actividadestutoria.values_list('dia', flat=True)):
                        horario.status = False
                        horario.save()
    except Exception as ex:
        print('error: %s' % ex)


def get_promedio(distributivo, periodo, fini, ffin):
    try:
        now = datetime.now().date()
        profesor = distributivo.profesor
        _data = []
        subtotal, total, numeroactividades = 0, 0, 0
        finicresta = fini - timedelta(days=5)
        ffincresta = ffin - timedelta(days=5)

        if distributivo.detalledistributivo_set.values('id').filter(criteriodocenciaperiodo__criterio__tipo=1, status=True).exists():
            for actividad in distributivo.detalle_horas_docencia(fini, ffin):
                if h := actividad.actividaddetalledistributivofecha(fini, ffin):
                    if not h.horas:
                        continue

                flag, html = False, actividad.criteriodocenciaperiodo.nombrehtmldocente()
                if actividad.criteriodocenciaperiodo:
                    if actividad.criteriodocenciaperiodo.htmldocente:
                        if html == 'actividaddocente':
                            if actividaddocente := actividad.criteriodocenciaperiodo.horarios_actividaddocente_profesor(profesor, fini, ffin):
                                if actividaddocente.totalplanificadas:
                                    total += 100
                                    flag = True

                    if html == 'impartirclase':
                        profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, tipoprofesor__imparteclase=True, activo=True,materia__status=True).distinct().order_by('desde', 'materia__asignatura__nombre')
                        if periodo.clasificacion == 1:
                            asignaturas = profesormateria.filter(((Q(desde__gte=fini) & Q(hasta__lte=ffin)) | (Q(desde__lte=fini) & Q(hasta__gte=ffin)) | (Q(desde__lte=ffin) & Q(desde__gte=fini)) | (Q(hasta__gte=fini) & Q(hasta__lte=ffin)))).distinct().exclude(tipoprofesor_id=15, materia__asignaturamalla__transversal=True).order_by('desde','materia__asignatura__nombre')
                        else:
                            asignaturas = profesormateria.filter(((Q(desde__gte=fini) & Q(hasta__lte=ffin)) | (Q(desde__lte=fini) & Q(hasta__gte=ffin)) | (Q(desde__lte=ffin) & Q(desde__gte=fini)) | (Q(hasta__gte=fini) & Q(hasta__lte=ffin)))).distinct().order_by('desde', 'materia__asignatura__nombre')

                        totalimpartir = actividad.criteriodocenciaperiodo.totalimparticlase(distributivo.profesor, fini, ffin, asignaturas)

                        if totalimpartir[0][0]:
                            _value = totalimpartir[0][2]
                            total += _value
                            if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                            flag = True

                    if html == 'evidenciamoodle':
                        if listadoevidencias := actividad.criteriodocenciaperiodo.horario_evidencia_moodle(profesor,finicresta,ffincresta):
                            evidencia = listadoevidencias[-1]
                            if not evidencia[11] == 4 and evidencia[1]:
                                _value = evidencia[10]
                                total += _value
                                if evidencia[10] < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                    if html == 'materialsilabo':
                        if actividadhor := actividad.criteriodocenciaperiodo.horarios_actividad_profesor(profesor, fini, ffin):
                            if not actividadhor.__len__() <= 2:
                                _value = 0
                                for acti in actividadhor:
                                    if not acti[4] == 1: _value = acti[3]
                                if _value:
                                    total += _value
                                    if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                    flag = True

                    if html == 'cursonivelacion':
                        if actividadnivelacioncarrera := actividad.criteriodocenciaperiodo.horarios_nivelacioncarrera_profesor(profesor, fini, ffin):
                            total += 100
                            flag = True

                    if html == 'planificarcontenido':
                        if contenidohor := actividad.criteriodocenciaperiodo.horarios_contenido_profesor(profesor, fini, ffin):
                            _value = 0
                            for x in contenidohor:
                                if not x[6] == 3 and x[4]: _value = x[3]
                            if _value:
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                    if html == 'tutoriaacademica':
                        if tutoriasacademicas := actividad.criteriodocenciaperiodo.horarios_tutoriasacademicas_profesor(profesor, fini, ffin):
                            if tutoriasacademicas[0][1]:
                                _value = tutoriasacademicas[0][3]
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                    if html == 'seguimientoplataforma':
                        if listadoseguimientos := actividad.criteriodocenciaperiodo.horario_seguimiento_tutor_fecha(profesor, fini, ffin):
                            s = listadoseguimientos[-1]
                            if s[11]:
                                _value = s[9]
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                    if html == 'nivelacioncarrera':
                        if actividadgestion := actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(distributivo, fini, ffin):
                            if actividadgestion.totalplanificadas:
                                if actigestion := actividadgestion.listadoevidencias:
                                    if temp := list(filter(lambda x: x[0] == 2, actigestion)):
                                        _value = temp[0][2]
                                        total += _value
                                        if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo,'porcentaje': _value})
                                        flag = True

                    if html == 'seguimientotransversal':
                        if listadoseguimientos := actividad.criteriodocenciaperiodo.horario_seguimiento_transaversal_fecha(profesor, fini, ffin):
                            s = listadoseguimientos[-1]
                            if s[11]:
                                _value = s[9]
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                    if html == 'apoyovicerrectorado':
                        if actividadapoyo := actividad.criteriodocenciaperiodo.horarios_apoyo_profesor(profesor, fini, ffin):
                            if actividadapoyo.totalplanificadas:
                                total += 100
                                flag = True

                if flag:
                    numeroactividades += 1
                    subtotal = total

        if distributivo.detalledistributivo_set.values('id').filter(criterioinvestigacionperiodo__isnull=False).exists():
            for actividad in distributivo.detalle_horas_investigacion():
                flag = False
                if actividad.criterioinvestigacionperiodo:
                    if actividad.criterioinvestigacionperiodo.nombrehtmldocente() == 'actividadinvestigacion':
                        if actividadgestion := actividad.criterioinvestigacionperiodo.horarios_informesinvestigacion_profesor(distributivo, fini, ffin):
                            if actividadgestion.listadoevidencias:
                                _value = 0
                                for actigestion in actividadgestion.listadoevidencias:
                                    if actividadgestion.totalplanificadas:
                                        if actigestion[0] == 2:
                                            _value = actigestion[2]
                                if _value:
                                    total += _value
                                    if _value < 100: _data.append({'tipo': 2, 'criterio': actividad.criterioinvestigacionperiodo,'porcentaje': _value})
                                    flag = True

                if flag:
                    numeroactividades += 1
                    subtotal = total

        if distributivo.detalledistributivo_set.values('id').filter(criteriogestionperiodo__isnull=False).exists():
            for actividad in distributivo.detalle_horas_gestion(fini, ffin):
                flag = False
                if actividad.criteriogestionperiodo:
                    if actividad.criteriogestionperiodo.nombrehtmldocente() == 'actividadgestion':
                        if actividadgestion := actividad.criteriogestionperiodo.horarios_actividadgestion_profesor(profesor, fini, ffin):
                            if actividadgestion.totalplanificadas:
                                total += 100
                                flag = True

                if flag:
                    numeroactividades += 1
                    subtotal = total

        if distributivo.detalledistributivo_set.values('id').filter(criteriodocenciaperiodo__isnull=False, criteriodocenciaperiodo__criterio__tipo=2).exists():
            for actividad in distributivo.detalle_horas_vinculacion():
                flag = False
                if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'actividadvinculacion':
                    if actividadgestion := actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(distributivo, fini, ffin):
                        if actividadgestion.listadoevidencias and actividadgestion.totalplanificadas:
                            for actigestion in actividadgestion.listadoevidencias:
                                if actigestion[0] == 2:
                                    _value = actigestion[2]
                                    total += _value
                                    if _value < 100: _data.append({'tipo': 4, 'criterio': actividad.criteriodocenciaperiodo,'porcentaje': _value})
                                    flag = True

                if flag:
                    numeroactividades += 1
                    subtotal = total

        _porcent = 0

        try:
            _porcent = total / numeroactividades
        except ZeroDivisionError as ex:
            pass

        return [profesor, _porcent, _data, distributivo.carrera]
    except Exception as ex:
        pass


def reporte_porcentaje_general_cumplimiento(request):
    try:
        now = datetime.now().date()
        m = request.GET.get('m', now.month)
        fi, ff = date(now.year, int(m), 1), date(now.year, int(m), calendar.monthrange(now.year, int(m))[1])
        periodo = request.session.get('periodo')
        response = []
        distributivos = ProfesorDistributivoHoras.objects.filter(periodo=periodo, activo=True, status=True).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
        _ids_ = HistorialInforme.objects.values_list('informe__distributivo', flat=True).filter(informe__promedio=100, informe__fechafin__month=ff.month, informe__fechafin__year=ff.year, informe__distributivo__periodo=periodo, status=True).distinct()
        for i, distributivo in enumerate(distributivos):
            if distributivo.pk in _ids_:
                response.append([distributivo.profesor, 100, {}, distributivo.carrera, distributivo])
                continue

            response.append(get_promedio(distributivo, periodo, fi, ff) + [distributivo])
        return response
    except Exception as ex:
        pass


def reporte_porcentaje_cumplimiento(request):

    now = datetime.now().date()
    periodo = request.session.get('periodo')
    fi, ff =  request.GET.get('fi'), request.GET.get('ff')
    if m := request.GET.get('m'): fi, ff = date(now.year, int(m), 1), date(now.year, int(m), calendar.monthrange(now.year, int(m))[1])
    fini, ffin = fi, ff
    finicresta = fini - timedelta(days=5)
    ffincresta = ffin - timedelta(days=5)

    try:
        response, data, asignaturas = [], [], None
        #.exclude(informe__promedio=100)
        _historial_ = HistorialInforme.objects.filter(informe__fechafin__month=ff.month, informe__distributivo__periodo=periodo, status=True).order_by('informe__distributivo__profesor__persona__apellido1', 'informe__distributivo__profesor__persona__apellido2')
        for h in _historial_.filter(informe__promedio=100): response.append([h.informe.distributivo.profesor, 100, {}, h.informe.distributivo.carrera])

        _exclude_ = _historial_.values_list('informe__distributivo', flat=True).exclude(informe__promedio=100)
        distributivos = ProfesorDistributivoHoras.objects.filter(periodo=periodo, activo=True, status=True).exclude(id__in=_exclude_).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2')
        _count, forloop = distributivos.count(), 0
        for distributivo in distributivos[1:5]:
            profesor = distributivo.profesor
            # '01-08-2023'
            # d = distributivo.profesor.informe_actividades_mensual_docente_v4(periodo, "%s-%s-%s" % (fi.day, fi.month, fi.year), "%s-%s-%s" % (ff.day, ff.month, ff.year), 'FACULTAD')

            _data = []
            subtotal, total, numeroactividades = 0, 0, 0
            forloop += 1

            if distributivo.detalledistributivo_set.values('id').filter(criteriodocenciaperiodo__criterio__tipo=1, status=True).exists():
                for actividad in distributivo.detalle_horas_docencia(fini, ffin):
                    flag, html = False, actividad.criteriodocenciaperiodo.nombrehtmldocente()
                    if actividad.criteriodocenciaperiodo:
                        if actividad.criteriodocenciaperiodo.htmldocente:
                            if html == 'actividaddocente':
                                if actividaddocente := actividad.criteriodocenciaperiodo.horarios_actividaddocente_profesor(profesor, fini, ffin):
                                    total += 100
                                    flag = True

                        if html == 'impartirclase':

                            # Extraer solo asignaturas de la funcion informe_actividades_mensual_docente_v4
                            profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, tipoprofesor__imparteclase=True, activo=True, materia__status=True).distinct().order_by('desde', 'materia__asignatura__nombre')
                            if periodo.clasificacion == 1:
                                asignaturas = profesormateria.filter(((Q(desde__gte=fini) & Q(hasta__lte=ffin)) | (Q(desde__lte=fini) & Q(hasta__gte=ffin)) | (Q(desde__lte=ffin) & Q(desde__gte=fini)) | (Q(hasta__gte=fini) & Q(hasta__lte=ffin)))).distinct().exclude(tipoprofesor_id=15, materia__asignaturamalla__transversal=True).order_by('desde', 'materia__asignatura__nombre')
                            else:
                                asignaturas = profesormateria.filter(((Q(desde__gte=fini) & Q(hasta__lte=ffin)) | (Q(desde__lte=fini) & Q(hasta__gte=ffin)) | (Q(desde__lte=ffin) & Q(desde__gte=fini)) | (Q(hasta__gte=fini) & Q(hasta__lte=ffin)))).distinct().order_by('desde', 'materia__asignatura__nombre')

                            totalimpartir = actividad.criteriodocenciaperiodo.totalimparticlase(distributivo.profesor, fini, ffin, asignaturas)

                            if totalimpartir[0][0]:
                                _value = totalimpartir[0][2]
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                        if html == 'evidenciamoodle':
                            if listadoevidencias := actividad.criteriodocenciaperiodo.horario_evidencia_moodle(profesor, finicresta, ffincresta):
                                evidencia = listadoevidencias[-1]
                                if not evidencia[11] == 4:
                                    _value = evidencia[10]
                                    total += _value
                                    if evidencia[10] < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                    flag = True

                        if html == 'materialsilabo':
                            if actividadhor := actividad.criteriodocenciaperiodo.horarios_actividad_profesor(profesor, fini, ffin):
                                if actividadhor[-1][3]:
                                    _value = actividadhor[-1][3]
                                    total += _value
                                    if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                    flag = True

                        if html == 'cursonivelacion':
                            if actividadnivelacioncarrera := actividad.criteriodocenciaperiodo.horarios_nivelacioncarrera_profesor(profesor, fini, ffin):
                                total += 100
                                flag = True

                        if html == 'planificarcontenido':
                            if contenidohor := actividad.criteriodocenciaperiodo.horarios_contenido_profesor(profesor, fini, ffin):
                                evidencia = contenidohor[-1]
                                _value = evidencia[3]
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                        if html == 'tutoriaacademica':
                            if tutoriasacademicas := actividad.criteriodocenciaperiodo.horarios_tutoriasacademicas_profesor(profesor, fini, ffin):
                                _value = tutoriasacademicas[0][3]
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                        if html == 'seguimientoplataforma':
                            if listadoseguimientos := actividad.criteriodocenciaperiodo.horario_seguimiento_tutor_fecha(profesor, fini, ffin):
                                s = listadoseguimientos[-1]
                                _value = s[9]
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                        if html == 'nivelacioncarrera':
                            if actividadgestion := actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(distributivo, fini, ffin):
                                if actigestion := actividadgestion.listadoevidencias:
                                    if temp := list(filter(lambda x: x[0] == 2, actigestion)):
                                        _value = temp[0][2]
                                        total += _value
                                        if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                        flag = True

                        if html == 'seguimientotransversal':
                            if listadoseguimientos := actividad.criteriodocenciaperiodo.horario_seguimiento_transaversal_fecha(profesor, fini, ffin):
                                s = listadoseguimientos[-1]
                                _value = s[9]
                                total += _value
                                if _value < 100: _data.append({'tipo': 1, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                flag = True

                        if html == 'apoyovicerrectorado':
                            if actividadapoyo := actividad.criteriodocenciaperiodo.horarios_apoyo_profesor(profesor, fini, ffin):
                                total += 100
                                flag = True

                    if flag:
                        numeroactividades += 1
                        # print(f"DOC - {numeroactividades}.- {'%.2f' % total}  {actividad.criteriodocenciaperiodo.criterio}")
                        subtotal = total

            if distributivo.detalledistributivo_set.values('id').filter(criterioinvestigacionperiodo__isnull=False).exists():
                for actividad in distributivo.detalle_horas_investigacion():
                    flag = False
                    if actividad.criterioinvestigacionperiodo:
                        if actividad.criterioinvestigacionperiodo.nombrehtmldocente() == 'actividadinvestigacion':
                            if actividadgestion := actividad.criterioinvestigacionperiodo.horarios_informesinvestigacion_profesor(distributivo, fini, ffin):
                                if actividadgestion.listadoevidencias:
                                    for actigestion in actividadgestion.listadoevidencias:
                                        if actigestion[0] == 2:
                                            _value = actigestion[2]
                                            total += _value
                                            if _value < 100: _data.append({'tipo': 2, 'criterio': actividad.criterioinvestigacionperiodo, 'porcentaje': _value})
                                            flag = True

                    if flag :
                        numeroactividades += 1
                        # print(f"INV - {numeroactividades}.- {'%.2f' % total}  {actividad.criterioinvestigacionperiodo.criterio}")
                        subtotal = total

            if distributivo.detalledistributivo_set.values('id').filter(criteriogestionperiodo__isnull=False).exists():
                for actividad in distributivo.detalle_horas_gestion(fini, ffin):
                    flag = False
                    if actividad.criteriogestionperiodo:
                        if actividad.criteriogestionperiodo.nombrehtmldocente() == 'actividadgestion':
                            if actividadgestion := actividad.criteriogestionperiodo.horarios_actividadgestion_profesor(profesor, fini, ffin):
                                total += 100
                                flag = True

                    if flag :
                        numeroactividades += 1
                        # print(f"GES - {numeroactividades}.- {'%.2f' % total}  {actividad.criteriogestionperiodo.criterio}")
                        subtotal = total

            if distributivo.detalledistributivo_set.values('id').filter(criteriodocenciaperiodo__isnull=False, criteriodocenciaperiodo__criterio__tipo=2).exists():
                for actividad in distributivo.detalle_horas_vinculacion():
                    flag = False
                    if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'actividadvinculacion':
                        if actividadgestion := actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(distributivo, fini, ffin):
                            if actividadgestion.listadoevidencias:
                                for actigestion in actividadgestion.listadoevidencias:
                                    if actigestion[0] == 2:
                                        _value = actigestion[2]
                                        total += _value
                                        if _value < 100: _data.append({'tipo': 4, 'criterio': actividad.criteriodocenciaperiodo, 'porcentaje': _value})
                                        flag = True

                    if flag :
                        numeroactividades += 1
                        # print(f"VIN - {numeroactividades}.- {total}  {actividad.criteriodocenciaperiodo.criterio}")
                        subtotal = total

            _porcent = 0
            try: _porcent = total / numeroactividades
            except ZeroDivisionError as ex: pass

            response.append([profesor, _porcent, _data, distributivo.carrera])
        return response
    except Exception as ex:
        print(ex.__str__())


def actualiza_estado_evidencia_criterios_varios(request, periodo):
    try:
        import json
        from sga.models import CriterioDocencia, CriterioInvestigacion, CriterioVinculacion

        DOCENCIA, INVESTIGACION, VINCULACION = [135, 132, 131, 19, 159, 19, 176, 165, 126, 156], [59, 66], [10]

        if d := request.GET.get('docencia'):
            DOCENCIA = json.loads(d)

        if i := request.GET.get('investigacion'):
            INVESTIGACION = json.loads(i)

        if g := request.GET.get('gestion'):
            json.loads(g)

        if v := request.GET.get('vinculacion'):
            VINCULACION = json.loads(v)

        mes, est, year = int(request.GET.get('m', 9)), int(request.GET.get('e', 1)), int(request.GET.get('y', 2023))
        filter_1 = Q(Q(criterio__criteriodocenciaperiodo__criterio__id__in=DOCENCIA) | Q(criterio__criterioinvestigacionperiodo__criterio__id__in=INVESTIGACION) | Q(criterio__criteriovinculacionperiodo__criterio__id__in=VINCULACION) | Q(criterio__criteriogestionperiodo__isnull=False))
        filter_2 = Q(estadoaprobacion=est, hasta__year=year, criterio__distributivo__periodo=periodo, hasta__month=mes, status=True)

        _response = []
        for evidencia in EvidenciaActividadDetalleDistributivo.objects.filter(filter_1 & filter_2):
            c = ''
            if criterio := evidencia.criterio.criteriodocenciaperiodo:
                c = criterio.criterio.nombre
            if criterio := evidencia.criterio.criterioinvestigacionperiodo:
                c = criterio.criterio.nombre
            if criterio := evidencia.criterio.criteriovinculacionperiodo:
                c = criterio.criterio.nombre
            if criterio := evidencia.criterio.criteriogestionperiodo:
                c = criterio.criterio.nombre

            _response.append(f"{evidencia.pk}.- MES {evidencia.hasta.month}, {evidencia.criterio.distributivo.profesor} - {c}\n")
            evidencia.estadoaprobacion = 2 if not evidencia.archivofirmado else 5
            evidencia.save()

        return _response
    except Exception as ex:
        linea_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        print(f"ERROR: {ex=} - {linea_error}")


def es_actividad_macro(detalle, periodo, request=None):
    try:
        if detalle.criterioinvestigacionperiodo.criterio.pk == ACTIVIDAD_MACRO_INVESTIGACION:
            if actividad := detalle.actividaddetalledistributivo_set.filter(status=True, vigente=True).first():
                for subactividad in SubactividadDocentePeriodo.objects.filter(actividad__criterioinvestigacionperiodo=detalle.criterioinvestigacionperiodo, actividad__status=True, status=True):
                    if not SubactividadDetalleDistributivo.objects.values('id').filter(actividaddetalledistributivo=actividad, subactividaddocenteperiodo=subactividad, status=True).exists():
                        s = SubactividadDetalleDistributivo(actividaddetalledistributivo=actividad, subactividaddocenteperiodo=subactividad, fechainicio=periodo.inicio, fechafin=periodo.fin)
                        if request:
                            s.save(request)
                        else:
                            s.save()
                return True
        return False
    except Exception as ex:
        return False

def verificar_director_carrera(persona, periodo):
    try:
        es_director = False
        carreras = []
        profesor = persona.profesor()
        if profesor:
            distributivo = ProfesorDistributivoHoras.objects.filter(periodo_id=periodo.pk, profesor=profesor)
            if distributivo:
                carreras_coord = distributivo[0].coordinacion.listadocarreras(periodo)
                for carr in carreras_coord:
                    if persona == carr.coordinador(periodo, distributivo[0].coordinacion.sede).persona:
                        carreras.append(carr.id)
                if carreras:
                    if CoordinadorCarrera.objects.filter(carrera__in=carreras,periodo=periodo,status=True, persona=persona,tipo=3).exists():
                        es_director = True
                    else:
                        es_director = False
        return es_director, carreras
    except Exception as ex:
        return None, []


def excluir_docentes_inicio_fin_actividad(anio, mes, periodo):
    try:
        fechaexcluir = datetime(int(anio), int(mes), 1).date() + relativedelta(months=1)
        subconsulta = ActividadDetalleDistributivo.objects.filter(
            criterio__distributivo__profesor=OuterRef('criterio__distributivo__profesor'),
            status=True,
            criterio__distributivo__periodo_id=periodo.id,
            criterio__distributivo__coordinacion__isnull=False,
            criterio__distributivo__profesor__persona__real=True,
            criterio__distributivo__status=True,
            criterio__distributivo__carrera__isnull=False
        ).order_by('desde').values('desde')[:1]
        ids_docentes = ActividadDetalleDistributivo.objects.annotate(primer_desde=Subquery(subconsulta)).filter(desde=F('primer_desde'), primer_desde__gte=fechaexcluir).values_list('criterio__distributivo__profesor', flat=True).distinct()

        DIAS_MAXIMO = int(variable_valor('DIAS_MAXIMO_ACTIVIDAD_INFORME_MENSUAL')) if variable_valor('DIAS_MAXIMO_ACTIVIDAD_INFORME_MENSUAL') else 1
        try: fechaexcluir_fin = datetime(int(anio), int(mes), DIAS_MAXIMO).date()
        except Exception as ex:
            DIAS_MAXIMO = calendar.monthrange(int(anio), int(mes))[1] if DIAS_MAXIMO > 28 else 1
            fechaexcluir_fin = datetime(int(anio), int(mes), DIAS_MAXIMO).date()
        subconsulta_fin = ActividadDetalleDistributivo.objects.filter(
            criterio__distributivo__profesor=OuterRef('criterio__distributivo__profesor'),
            status=True,
            criterio__distributivo__periodo_id=periodo.id,
            criterio__distributivo__coordinacion__isnull=False,
            criterio__distributivo__profesor__persona__real=True,
            criterio__distributivo__status=True,
            criterio__distributivo__carrera__isnull=False
        ).order_by('-hasta').values('hasta')[:1]
        ids_docentes_fin = ActividadDetalleDistributivo.objects.annotate(primer_hasta=Subquery(subconsulta_fin)).filter(hasta=F('primer_hasta'), primer_hasta__lt=fechaexcluir_fin).values_list('criterio__distributivo__profesor', flat=True).distinct()
        return list(ids_docentes) + list(ids_docentes_fin)
    except Exception as ex:
        return []


def generar_informe_mensual_docente(id, fechainicio, fechafin):
    from sga.templatetags.sga_extras import listado_bitacora_docente, actividad_produccion_cientifica

    try:
        total_porcentaje = 0
        for distributivo in ProfesorDistributivoHoras.objects.filter(id=id, status=True):
            fechainiinforme, fechafininforme = fechainicio, fechafin

            fechainiinforme = fechainiinforme.strftime('%d-%m-%Y')
            fechafininforme = fechafininforme.strftime('%d-%m-%Y')

            adicional_lista = []
            periodo = distributivo.periodo
            profesor = distributivo.profesor
            count, count1, count2, count3, count4 = 0, 0, 0, 0, 0
            totalporcentaje, totalhdocentes, totalhinvestigacion, totalhgestion, totalhvinculacion = 0, 0, 0, 0, 0
            fechames = datetime.now().date()
            now = datetime.now()
            fini, ffin = fechainiinforme, fechafininforme
            fechainiresta = datetime.strptime(fini, '%d-%m-%Y') - timedelta(days=5)
            fechafinresta = datetime.strptime(ffin, '%d-%m-%Y') - timedelta(days=5)
            finicresta = fechainiresta
            ffincresta = fechafinresta

            data = profesor.informe_actividades_mensual_docente_v4(periodo, fechainiinforme, fechafininforme, 'FACULTAD')

            finiinicio = convertir_fecha(fechainiinforme)
            ffinal = convertir_fecha(fechafininforme)

            fechamesini = convertir_fecha(fechainiinforme)
            fechames = convertir_fecha(fechafininforme)
            qrname = 'informemensual_' + str(distributivo.id) + '_' + str(fechames.month) + '_2'
            generaautomatico = False
            if not InformeMensualDocente.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, fechafin__month=fechames.month, status=True):
                generaautomatico = True
            else:
                if InformeMensualDocente.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, fechafin__month=fechames.month, estado=1, status=True):
                    informedelete = InformeMensualDocente.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, fechafin__month=fechames.month, estado=1, status=True)[0]
                    informedelete.delete()
                    generaautomatico = True

            if generaautomatico:
                listDocencia = []
                if horasdocencia := distributivo.detalle_horas_docencia(finiinicio, ffinal):
                    dicDocencia = {'tipo': 'Horas Docencia'}
                    listDocencia.append([0, 'ACTIVIDADES DE DOCENCIA'])
                    for actividad in horasdocencia:
                        if nombrehtmldocente := actividad.criteriodocenciaperiodo.nombrehtmldocente():
                            try:
                                if nombrehtmldocente == 'impartirclase':
                                    totalimpartir = actividad.criteriodocenciaperiodo.totalimparticlase(distributivo.profesor, finiinicio, ffinal, data['asignaturas'], None, True)
                                    if totalimpartir[2]:
                                        count += 1
                                        totalhdocentes += totalimpartir[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, totalimpartir[0], totalimpartir[1]])

                                if nombrehtmldocente == 'evidenciamoodle':
                                    listadoevidencias = actividad.criteriodocenciaperiodo.horario_evidencia_moodle(distributivo.profesor, finicresta, ffincresta, True)
                                    if listadoevidencias[2]:
                                        count += 1
                                        totalhdocentes += listadoevidencias[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, listadoevidencias[0], listadoevidencias[1]])

                                if nombrehtmldocente == 'materialsilabo':
                                    actividadhor = actividad.criteriodocenciaperiodo.horarios_actividad_profesor(distributivo.profesor, finiinicio, ffinal, True)
                                    count += 1
                                    totalhdocentes += actividadhor[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividadhor[0], actividadhor[1]])

                                if nombrehtmldocente == 'cursonivelacion':
                                    totitem4 = 0
                                    if actividadnivelacioncarrera := actividad.criteriodocenciaperiodo.horarios_nivelacioncarrera_profesor(distributivo.profesor, finiinicio, ffinal):
                                        totitem4 += 100
                                        totalhdocentes += 100
                                        count += 1

                                if nombrehtmldocente == 'planificarcontenido':
                                    contenidohor = actividad.criteriodocenciaperiodo.horarios_contenido_profesor(distributivo.profesor, finiinicio, ffinal, True)
                                    if contenidohor == 0:
                                        listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, '-', '-'])
                                    else:
                                        count += 1
                                        totalhdocentes += contenidohor[1]
                                        listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, contenidohor[0], contenidohor[1]])

                                if nombrehtmldocente == 'tutoriaacademica':
                                    tutoriasacademicas = actividad.criteriodocenciaperiodo.horarios_tutoriasacademicas_profesor(
                                        distributivo.profesor, finiinicio, ffinal, True)
                                    count += 1
                                    totalhdocentes += tutoriasacademicas[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, tutoriasacademicas[0], tutoriasacademicas[1]])

                                if nombrehtmldocente == 'seguimientoplataforma':
                                    if listadoseguimientos := actividad.criteriodocenciaperiodo.horario_seguimiento_tutor_fecha(distributivo.profesor, finiinicio, ffinal, True):
                                        if listadoseguimientos[2]:
                                            count += 1
                                            totalhdocentes += listadoseguimientos[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, listadoseguimientos[0], listadoseguimientos[1]])

                                if nombrehtmldocente == 'nivelacioncarrera':
                                    actividadgestion = actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(distributivo, finiinicio, ffinal, True)
                                    count += 1
                                    totalhdocentes += actividadgestion[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas,actividadgestion[0], actividadgestion[1]])

                                if nombrehtmldocente == 'seguimientotransversal':
                                    listadoseguimientos = actividad.criteriodocenciaperiodo.horario_seguimiento_transaversal_fecha(distributivo.profesor, finiinicio, ffinal, True)
                                    if listadoseguimientos[2]:
                                        count += 1
                                        totalhdocentes += listadoseguimientos[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, listadoseguimientos[0], listadoseguimientos[1]])

                                if nombrehtmldocente == 'apoyovicerrectorado':
                                    totitem10 = 0
                                    if actividadapoyo := actividad.criteriodocenciaperiodo.horarios_apoyo_profesor(distributivo.profesor, finiinicio, ffinal):
                                        totitem10 += 100
                                        totalhdocentes += 100
                                        count += 1

                                if nombrehtmldocente == 'actividaddocente':
                                    if actividaddocente1 := actividad.criteriodocenciaperiodo.horarios_actividaddocente_profesor(distributivo.profesor, finiinicio, ffinal, True):
                                        count += 1
                                        totalhdocentes += 100
                                        listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividaddocente1[0], actividaddocente1[1]])
                                    else:
                                        count += 1
                                        totalhdocentes += 0
                                        listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, '-', '0.00'])

                                if nombrehtmldocente == 'criterioperiodoadmision':
                                    actividaddocente1 = actividad.criteriodocenciaperiodo.horario_criterio_nivelacion(distributivo.profesor, finiinicio, ffinal, True)
                                    count += 1
                                    totalhdocentes += actividaddocente1[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividaddocente1[0], actividaddocente1[1]])

                                if nombrehtmldocente == 'actividadbitacora':
                                    actividaddocente1 = listado_bitacora_docente(0, actividad, ffinal, True)
                                    count += 1
                                    hmes = actividaddocente1[0]
                                    totalhdocentes += actividaddocente1[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, hmes, actividaddocente1[1]])
                            except Exception as ex:
                                ...

                    adicional_lista.append(listDocencia)

                if horasinvestigacion := distributivo.detalle_horas_investigacion(finiinicio, ffinal):
                    docInvestigacion = {'tipo': 'Horas Investigación'}
                    listDocencia.append([0, 'ACTIVIDADES DE INVESTIGACIÓN'])
                    listInvestigacion = []
                    for actividad in horasinvestigacion:
                        if nombrehtmldocente := actividad.criterioinvestigacionperiodo.nombrehtmldocente():
                            if nombrehtmldocente == 'actividadinvestigacion':
                                actividadgestion = actividad.criterioinvestigacionperiodo.horarios_informesinvestigacion_profesor(distributivo, finiinicio, ffinal, True)
                                count1 += 1
                                totalhinvestigacion += actividadgestion[1]
                                listDocencia.append([actividad.criterioinvestigacionperiodo.id, actividad.criterioinvestigacionperiodo.criterio.nombre, actividad.horas, '', actividadgestion[1]])
                            if nombrehtmldocente == 'actividadbitacora':
                                actividadgestion = listado_bitacora_docente(0, actividad, ffinal, True)
                                count1 += 1
                                hmes = actividadgestion[0]
                                totalhinvestigacion += actividadgestion[1]
                                listDocencia.append([actividad.criterioinvestigacionperiodo.id, actividad.criterioinvestigacionperiodo.criterio.nombre, actividad.horas, hmes, actividadgestion[1]])
                            if nombrehtmldocente == 'actividadmacro':
                                actividadgestion = actividad_produccion_cientifica(actividad, finiinicio, ffinal, esautomatico=True)
                                count1 += 1
                                hmes = float(actividadgestion[0])
                                totalhinvestigacion += float(actividadgestion[1])
                                listDocencia.append([actividad.criterioinvestigacionperiodo.id, actividad.criterioinvestigacionperiodo.criterio.nombre, actividad.horas, hmes, actividadgestion[1]])

                    docInvestigacion['actividades'] = listInvestigacion
                    adicional_lista.append(listDocencia)

                if horasgestion := distributivo.detalle_horas_gestion(finiinicio, ffinal):
                    docGestion = {'tipo': 'Horas Gestión'}
                    listGestion = []
                    listDocencia.append([0, 'ACTIVIDADES DE GESTIÓN EDUCATIVA'])
                    for actividad in horasgestion:
                        if nombrehtmldocente := actividad.criteriogestionperiodo.nombrehtmldocente():
                            if nombrehtmldocente == 'actividadgestion':
                                actividadgestion = actividad.criteriogestionperiodo.horarios_actividadgestion_profesor(distributivo.profesor, finiinicio, ffinal, True)
                                if actividadgestion:
                                    count2 += 1
                                    totalhgestion += 100
                                    listDocencia.append([actividad.criteriogestionperiodo.id, actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])
                                else:
                                    count2 += 1
                                    totalhgestion += 0
                                    listDocencia.append([actividad.criteriogestionperiodo.id, actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, '-', '0.00'])
                            if nombrehtmldocente == 'actividadinformegestion':
                                actividadgestion = actividad.criteriogestionperiodo.horarios_informesgestion_profesor(distributivo, finiinicio, ffinal, True)
                                count2 += 1
                                totalhgestion += float(actividadgestion[1])
                                listDocencia.append([actividad.criteriogestionperiodo.id,actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, '', actividadgestion[1]])
                            if nombrehtmldocente == 'actividadbitacora':
                                actividadgestion = listado_bitacora_docente(0, actividad, ffinal, True)
                                count2 += 1
                                if actividadgestion:
                                    totalhgestion += float(actividadgestion[1])
                                    listDocencia.append([actividad.criteriogestionperiodo.id, actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])
                        else:
                            listDocencia.append([actividad.criteriogestionperiodo.id, actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, '-', '-'])
                    docGestion['actividades'] = listGestion
                    adicional_lista.append(listDocencia)

                if horasvinculacion := distributivo.detalle_horas_vinculacion():
                    docVinculacion = {'tipo': 'Horas Vinculacion'}
                    listVinculacion = []
                    listDocencia.append([0, 'ACTIVIDADES DE VINCULACIÓN CON LA SOCIEDAD'])
                    for actividad in horasvinculacion:
                        if nombrehtmldocente := actividad.criteriodocenciaperiodo.nombrehtmldocente():
                            if nombrehtmldocente == 'actividadvinculacion':
                                actividadgestion = actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(distributivo, finiinicio, ffinal, True)
                                if actividadgestion:
                                    count3 += 1
                                    totalhvinculacion += actividadgestion[1]
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])
                                else:
                                    count3 += 1
                                    totalhvinculacion += 0
                                    listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, '-', '0.00'])
                            if nombrehtmldocente == 'actividadbitacora':
                                actividadgestion = listado_bitacora_docente(0, actividad, ffinal, True)
                                count3 += 1
                                totalhvinculacion += actividadgestion[1]
                                listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])
                            if nombrehtmldocente == 'actividadmacro':
                                actividadgestion = actividad_produccion_cientifica(actividad, finiinicio, ffinal, esautomatico=True)
                                count1 += 1
                                hmes = float(actividadgestion[0])
                                totalhvinculacion += float(actividadgestion[1])
                                listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])

                    docVinculacion['actividades'] = listVinculacion
                    adicional_lista.append(listDocencia)

                totalporcentaje = totalhdocentes + totalhinvestigacion + totalhgestion + totalhvinculacion
                count4 = count + count1 + count2 + count3
                total_porcentaje = round(totalporcentaje / count4, 2) if count4 else 100.0

                listDocencia.append(['total', total_porcentaje])
                tienefirmas = False
                if distributivo.carrera:
                    if CoordinadorCarrera.objects.values('id').filter(carrera=distributivo.carrera, periodo=periodo, sede_id=1, tipo=3).exists():
                        personadirectorcarrera = CoordinadorCarrera.objects.filter(carrera=distributivo.carrera, periodo=periodo, sede_id=1, tipo=3)[0]
                        if distributivo.coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, status=True).exists():
                            personadirectorcoordinacion = distributivo.coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, status=True)[0]
                            tienefirmas = True

                if tienefirmas:
                    folder = os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', '')
                    rutainformepdf1 = folder + 'informemensual_' + str(distributivo.id) + '_' + str(fechames.month) + '_1.pdf'
                    if os.path.isfile(rutainformepdf1):
                        os.remove(rutainformepdf1)

                    rutainformepdf = folder + 'informemensual_' + str(distributivo.id) + '_' + str(fechames.month) + '_2.pdf'
                    if os.path.isfile(rutainformepdf):
                        os.remove(rutainformepdf)

                    if not HistorialInformeMensual.objects.values('id').filter(distributivo=distributivo, status=True, finicioreporte__month=fechames.month).exists():
                        instance = HistorialInformeMensual(distributivo=distributivo, finicioreporte=fechamesini, ffinreporte=fechames, total_porcentaje=total_porcentaje)
                        instance.datos_lista = adicional_lista
                        instance.save()
                    else:
                        if instance := HistorialInformeMensual.objects.filter(distributivo=distributivo, finicioreporte=fechamesini, ffinreporte=fechames, total_porcentaje=total_porcentaje).first():
                            instance.datos_lista = adicional_lista
                            instance.save()
                    data['tablepromedio'] = adicional_lista
                    data['informeautomatico'] = 1
                    generainforme = html_to_pdfsave_informemensualdocente('adm_criteriosactividadesdocente/informe_actividad_docentev4_pdf.html', {'pagesize': 'A4', 'data': data}, qrname + '.pdf', 'informemensualdocente')
                    nombrepdf = 'informemensual_' + str(distributivo.id) + '_' + str(fechames.month) + '_2'
                    folder_save = os.path.join('informemensualdocente', '').replace('\\', '/')
                    informe = InformeMensualDocente(distributivo_id=distributivo.id, fechainicio=fechamesini, fechafin=fechames, archivo=f'{folder_save}{nombrepdf}.pdf', promedio=total_porcentaje, estado=2, automatico=True)
                    informe.fechacreacion = fechames
                    informe.save()

                    if not HistorialInforme.objects.values('id').filter(informe=informe, estado=2).exists():
                        url_file_generado = f'{folder_save}{nombrepdf}.pdf'
                        historial = HistorialInforme(informe=informe, archivo=url_file_generado, estado=2, fechafirma=datetime.now().date(), firmado=True, personafirmas=informe.distributivo.profesor.persona)
                        historial.save()
                    if not HistorialInforme.objects.values('id').filter(informe=informe, estado=3).exists():
                        historial = HistorialInforme(informe=informe, personafirmas=personadirectorcarrera.persona, estado=3)
                        historial.save()
                    if not HistorialInforme.objects.values('id').filter(informe=informe, estado=4).exists():
                        historial = HistorialInforme(informe=informe, personafirmas=personadirectorcoordinacion.persona, estado=4)
                        historial.save()

            noti = Notificacion(titulo='Cron informes', cuerpo=f'INFORME MENSUAL {fechafin.month} - {profesor} GENERADO SATISFACTORIAMENTE...', destinatario_id=37121, url="", prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2, en_proceso=False, error=True)
            noti.save()
        return True, total_porcentaje
    except Exception as ex:
        cuerpo = f'Ha ocurrido un error {ex}.'
        noti = Notificacion(titulo='Error', cuerpo=cuerpo, destinatario_id=37121, url="", prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2, en_proceso=False, error=True)
        noti.save()
        return False, cuerpo

def actividad_macro_actividades_investigacion(actividad_detalle_distributivo_set, persona):
    """
    Función que procesa las actividades macro de una persona en base a su rol en proyectos de investigación y grupos de investigación.
    """
    try:
        from sga.pro_cronograma import (CRITERIO_DIRECTOR_PROYECTO, CRITERIO_ASOCIADO_PROYECTO,
                                        CRITERIO_CODIRECTOR_PROYECTO_INV, CRITERIO_DIRECTOR_GRUPOINVESTIGACION,
                                        CRITERIO_INTEGRANTE_GRUPOINVESTIGACION)
        from inno.models import ActividadDocentePeriodo, SubactividadDetalleDistributivo
        from django.db.models import Q

        data = {}

        # Excluir ciertos proyectos de investigación
        EXCLUIR_PROYECTOS_INVESTIGACION = variable_valor('EXCLUIR_PROYECTOS_INVESTIGACION')

        # Verificar si hay actividades
        if actividad := actividad_detalle_distributivo_set.actividaddetalledistributivo_set.filter(status=True, vigente=True).first():
            _exclude = Q()

            # Obtener los roles del integrante del proyecto de investigación
            tipointegranteproyecto = persona.proyectoinvestigacionintegrante_set.values_list('funcion',
                                                                                             flat=True).filter(
                tiporegistro__in=[1, 3, 4], proyecto__estado_id=37, status=True
            ).exclude(proyecto__in=EXCLUIR_PROYECTOS_INVESTIGACION)

            # Excluir criterios basados en los roles en proyectos
            if 1 not in tipointegranteproyecto:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_DIRECTOR_PROYECTO)
            if 2 not in tipointegranteproyecto:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_CODIRECTOR_PROYECTO_INV)
            if 3 not in tipointegranteproyecto:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_ASOCIADO_PROYECTO)

            # Obtener los roles en grupos de investigación
            tipointegrantegrupo = persona.grupoinvestigacionintegrante_set.values_list('funcion', flat=True).filter(
                grupo__vigente=True, grupo__status=True, status=True
            )

            # Excluir criterios basados en los roles en grupos
            if 1 not in tipointegrantegrupo:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_DIRECTOR_GRUPOINVESTIGACION)
            if 2 not in tipointegrantegrupo and 3 not in tipointegrantegrupo:
                _exclude |= Q(subactividaddocenteperiodo__criterio=CRITERIO_INTEGRANTE_GRUPOINVESTIGACION)

            # Obtener subactividades y actividades relacionadas
            data['subactividades'] = subactividades = SubactividadDetalleDistributivo.objects.filter(
                actividaddetalledistributivo=actividad,
                subactividaddocenteperiodo__criterio__status=True,
                status=True
            ).exclude(_exclude).order_by('subactividaddocenteperiodo__criterio__nombre')

            data['actividades'] = ActividadDocentePeriodo.objects.filter(
                pk__in=subactividades.values_list('subactividaddocenteperiodo__actividad', flat=True),
                criterio__status=True
            ).order_by('criterio__nombre')

        return data
    except Exception as ex:
        return {}