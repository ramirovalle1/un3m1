# -*- coding: UTF-8 -*-
import os
import io
import subprocess
import json
import sys
import calendar
from datetime import datetime, timedelta, date
import PyPDF2
import pyqrcode
import xlwt, time
from django.core.files.base import ContentFile
from decimal import Decimal
import locale
import fitz.utils
from dateutil.rrule import MONTHLY, rrule
from django.db.models.functions import Extract
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, connection, connections
from django.db.models import Q, Max, Count, PROTECT, Sum, Avg, Min, F, ExpressionWrapper, DurationField, TimeField, DateTimeField
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template import Context
from django.template.loader import get_template
from django.forms import model_to_dict
from xlwt import *
import random
import collections

from bd.models import InventarioOpcionSistema
from decorators import secure_module, last_access
from investigacion.forms import BitacoraActividadForm, UsuarioRevisaEvidenciaDocenteForm
from posgrado.models import InscripcionCohorte
from django.contrib.auth.models import Group
from sagest.commonviews import secuencia_convenio_devengacion
from sagest.forms import CapacitacionPersonaDocenteForm
from sagest.models import DistributivoPersona, LogDia, Departamento
from investigacion.models import ProyectoInvestigacionIntegrante, BitacoraActividadDocente, HistorialBitacoraActividadDocente, AnexoDetalleBitacoraDocente, DetalleBitacoraDocente, DepartamentoBitacora, PersonaBitacora, UserCriterioRevisor, GrupoInvestigacionIntegrante, ProyectoInvestigacion, GrupoInvestigacion, GrupoInvestigacionIntegrante
from settings import PRACTICAS_PREPROFESIONALES_ACTIVAS, \
    MATRICULACION_LIBRE, TIPO_DOCENTE_PRACTICA, SERVER_RESPONSE, TIPO_DOCENTE_AYUDANTIA, JR_JAVA_COMMAND, DATABASES, \
    JR_USEROUTPUT_FOLDER, JR_RUN, MEDIA_URL, SUBREPOTRS_FOLDER, MEDIA_ROOT, SITE_ROOT, DEBUG, SITE_STORAGE, EMAIL_DOMAIN
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import PracticaPreProfesionalForm, EvidenciaActividadDetalleDistributivoForm, AvTutoriasForm, \
    AprobarRechazarEvidenciaTutorForm, PonerFechaLimiteEvidenciaForm, RetiroPracticasForm, \
    ArpobarEvidenciaPracticasForm, ConfigurarFechaMasivaPracticaForm, InformeMensualSupervisorPracticaForm, \
    PracticasPreprofesionalesInscripcionSupervisorForm, DetalleDistributivoForm, PlanificarPonenciasForm, \
    PlanificarCapacitacionesForm, PlanificarCapacitacionesArchivoForm, ArticuloInvestigacionDocenteForm, \
    PonenciaInvestigacionDocenteForm, LibroInvestigacionDocenteForm, CapituloLibroInvestigacionDocenteForm, \
    CronogramaTrabajoInvestigacionDocenteForm, TutoriaAdicionalForm, \
    SubirEvidenciaEjecutadoCapacitacionesForm, BecaSolicitudSubirCedulaForm, PonenciaEvidenciaEjecutadoForm, \
    ConfiguracionInformePPPForm, AgendaTutoriaForm, ReemplazarInquietudForm, AsesoramientoSEEForm, AnexoEvidenciaActividadForm, InformeForm
from inno.models import SubactividadDetalleDistributivo, RegistroClaseTutoriaDocente, SolicitudTutoriaIndividual, HorarioTutoriaAcademica, \
    InformeMensualDocente, HistorialInforme, HistorialInformeMensual, TerminosCondicionesProfesorDistributivo, \
    TerminosCondiciones, SolicitudAperturaClaseVirtual, HorasInformeMensualDocente, AulaPlanificacionSedeVirtualExamen, MigracionEvidenciaActividad
from sga.funciones import log, generar_nombre, MiPaginador, convertir_fecha, variable_valor, null_to_decimal, \
    fechaletra_corta, tituloinstitucion, convertir_fecha_invertida, remover_caracteres_especiales_unicode, notificacion, get_director_vinculacion, \
    null_to_numeric, convertirfecha2, validar_archivo, cuenta_email_disponible_para_envio, fecha_letra_rango, convertir_fecha_hora_invertida
from sga.funciones_templatepdf import evidenciassilabosxcarrera, evidenciasrecursossilabo, totalestutoriasacademicas, download_html_to_pdf, \
    prapreprofesionales, totalorientarmodallinea, sistemanacionalnivadmision, html_to_pdfsave_informemensualdocente, seguimientotransver
from sga.models import ActividadExtraCurricular, ParticipanteActividadExtraCurricular, AgendaPracticasTutoria, \
    ProyectosVinculacion, \
    ParticipanteProyectoVinculacion, PracticaPreProfesional, Materia, MateriaAsignada, \
    ParticipantePracticaPreProfesional, MateriaCursoEscuelaComplementaria, \
    MateriaAsignadaCurso, EvidenciaActividadDetalleDistributivo, \
    EncargadoCriterioPeriodo, Coordinacion, Persona, AsignaturaMalla, \
    AsignaturaMallaPreferencia, PermisoPeriodo, PaeActividadesPeriodoAreas, PaeFechaActividad, \
    PaeInscripcionActividades, PaeAsistenciaFechaActividad, AvTutorias, AvTutoriasAlumnos, \
    AvPreguntaRespuesta, ProfesorMateria, PracticasPreprofesionalesInscripcion, \
    DetalleEvidenciasPracticasPro, ProfesorDistributivoHoras, miinstitucion, CUENTAS_CORREOS, \
    InscripcionCatedra, PeriodoCatedra, Carrera, ActividadInscripcionCatedra, Titulacion, \
    TipoProfesor, Leccion, PeriodoEvidenciaPracticaProfesionales, \
    FormatoPracticaPreProfesional, InformeMensualSupervisorPractica, ItinerariosMalla, MESES_CHOICES, \
    VisitaPractica, VisitaPractica_Detalle, ESTADO_VISITA_PRACTICA, ESTADO_TIPO_VISITA, DetalleDistributivo, \
    ArchivoGeneralPracticaPreProfesionales, DIAS_CHOICES, Silabo, CronogramaActividad, CriterioInvestigacion, \
    DetalleRecoridoCronogramaActividad, PlanificarPonencias, SugerenciaCongreso, Malla, NivelMalla, Turno, \
    HorarioPreferencia, ArticuloInvestigacion, HorarioPreferenciaObse, PlanificarCapacitaciones, \
    PlanificarCapacitacionesCriterios, CronogramaCapacitacionDocente, PlanificarCapacitacionesDetalleCriterios, \
    CoordinadorCarrera, ArticuloInvestigacionDocente, PonenciaInvestigacionDocente, \
    LibroInvestigacionDocente, CapituloLibroInvestigacionDocente, CronogramaTrabajoInvestigacionDocente, \
    PlanificarCapacitacionesRecorrido, \
    PreferenciaDetalleActividadesCriterio, GruposInvestigacion, PreferenciaGruposInvestigacion, Periodo, \
    AsignaturaMallaPreferenciaPosgrado, Sesion, PreferenciaDocente, ResponsableCoordinacion, Capacitacion, \
    InquietudPracticasPreprofesionales, RespuestaInquitudPracticasPreprofesionales, CriterioDocenciaPeriodo, \
    CriterioGestionPeriodo, Asignatura, DiapositivaSilaboSemanal, GuiaEstudianteSilaboSemanal, GuiaDocenteSilaboSemanal, \
    CompendioSilaboSemanal, EvidenciaActividadAudi, CriterioPonencia, PlanificarPonenciasCriterio, \
    PlanificarPonenciasRecorrido, PonderacionSeguimiento, Reporte, CriterioDocencia, SolicitudTutorSoporteMatricula, \
    CriterioGestion, \
    HistorialaprobacionTarea, HistorialaprobacionForo, HistorialaprobacionTareaPractica, HistorialaprobacionDiapositiva, \
    HistorialaprobacionGuiaEstudiante, \
    HistorialaprobacionGuiaDocente, HistorialaprobacionCompendio, HistorialaprobacionTest, Profesor, PracticasTutoria, \
    SolicitudTutorSoporteMateria, ConfiguracionInformePracticasPreprofesionales, \
    DetalleConfiguracionInformePracticasPreprofesionales, CabPeriodoEvidenciaPPP, InformeMensualDocentesPPP, \
    CapEnfocadaDocente, PropuestaLineaInvestigacion, PlanificarCapacitacionesEnfoque, EstudiantesAgendaPracticasTutoria, \
    FirmaPersona, AvPreguntaDocente, AsesoramientoSEE, ActividadDetalleDistributivoCarrera, HorarioTutoriaPacticasPP, \
    Clase, ComplexivoClase, ClaseActividad, ClaseAsincronica, ConvocatoriaPonencia, SilaboSemanal, HistorialAprobacionEvidenciaActividad, AnexoEvidenciaActividad, CriterioInvestigacionPeriodo, \
    ConfiguracionInformeVinculacion, ActividadExtraVinculacion, ProgramaAnaliticoAsignatura, DetalleEvidenciaHomologacionPractica
from postulaciondip.forms import FirmaElectronicaIndividualForm
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado, \
    conviert_html_to_pdfsave, conviert_html_to_pdfsaveqrinformepracticasmensual, convert_html_to_pdf, \
    conviert_html_to_pdf_name, conviert_html_to_pdf_name_bitacora, conviert_html_to_pdfsaveqr_generico
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt, encrypt_alu, nombremes
from sga.reportes import elimina_tildes, transform_jasperstarter_new, run_report_v1
from sga.formmodel import ReAgendarAgendaPracticasTutoriasForm, FinalizarAgendaTutoriaForm, AgendaPracticasTutoriaForm
from num2words import num2words
from core.firmar_documentos import firmararchivogenerado, firmar, obtener_posicion_x_y_saltolinea, verificarFirmasPDF
from core.firmar_documentos_ec import JavaFirmaEc
from laboratorio.models import Test, DetalleTest, UsuarioRespuesta, IntentoUsuario, LaboratorioOpcionSistema, SeguimientoDocente, DetalleSeguimientoDocente

unicode = str
CRITERIO_DIRECTOR_PROYECTO = 7
CRITERIO_CODIRECTOR_PROYECTO_INV = 8
CRITERIO_ASOCIADO_PROYECTO = 9
CRITERIO_DIRECTOR_GRUPOINVESTIGACION = 12
CRITERIO_INTEGRANTE_GRUPOINVESTIGACION = 13
CRITERIO_ASOCIADO_VIN, CRITERIO_DIRECTOR_VIN = 22, 21
CRITERIO_PAR_EVALUADOR = 17
CRITERIO_PONENCIAS = 11
CRITERIO_ELABORA_ARTICULO_CIENTIFICO = 18


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


# SE AGREGA PARA FORMATEAR FECHA A FORMATO DD-MM-AAAA
def formatear_fecha(fecha):
    return fecha.strftime('%d-%m-%Y')


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    es_profesor = perfilprincipal.es_profesor()
    if not periodo:
        return HttpResponseRedirect("/?info=Estimado docente, no tiene asignaturas en distributivo.")
    if not es_profesor:
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    if es_profesor and periodo.ocultarmateria:
        return HttpResponseRedirect("/?info=Lo sentimos este periodo aún está en planificación.")
    data['profesor'] = profesor = perfilprincipal.profesor
    TUTOR_PRACTICAS_INTERNADO_ROTATIVO = variable_valor('TUTOR_PRACTICAS_INTERNADO_ROTATIVO')  # 972
    CRITERIO_INTEGRANTE_PROYECTO_VINCULACION = 151
    responsablevinculacion = get_director_vinculacion()
    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://127.0.0.1:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'asistenciaregistrada':
                try:
                    with transaction.atomic():
                        data = json.loads(request.POST.get('data'))
                        pk, asistencia = data['pk'], data['value']
                        estudiante = EstudiantesAgendaPracticasTutoria.objects.get(pk=pk)
                        estudiante.asistio = asistencia
                        estudiante.fecha_asistencia = datetime.now()
                        estudiante.hora_asistencia = datetime.now().time()
                        estudiante.save(request)
                        mensaje = 'Asistencia registrada' if asistencia else 'Asistencia removida'
                        type = 'success' if asistencia else 'warning'
                        return HttpResponse(json.dumps({'resp': True, 'mensaje': mensaje, 'type': type}))
                except Exception as ex:
                    mensaje_error = 'Error al procesar la solicitud: {}'.format(str(ex))
                    return HttpResponse(json.dumps({'resp': False, 'mensaje': mensaje_error}))

            if action == 'addagenda':
                try:
                    with transaction.atomic():
                        inicio = ''
                        fin = ''
                        turno = None
                        agenda = AgendaPracticasTutoria.objects.filter(docente=perfilprincipal.profesor, fecha=request.POST['fecha'], status=True)
                        if 'turno' in request.POST:
                            turno = Turno.objects.get(id=request.POST['turno'])
                            # request.POST['hora_inicio'] = turno.comienza
                            # request.POST['hora_fin'] = turno.termina
                            inicio = turno.comienza
                            fin = turno.termina
                            if agenda.filter(hora_inicio=inicio).exclude(estados_agenda=3).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({'error': True, "message": 'Turno ya esta ocupado ({} {} - {}).'.format(request.POST['fecha'], inicio, fin)}, safe=False)
                        else:
                            inicio = request.POST['hora_inicio']
                            fin = request.POST['hora_fin']
                            if agenda.filter(hora_inicio=inicio).exclude(estados_agenda=3).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({'error': True, "message": 'Turno ya esta ocupado ({} {} - {}).'.format(request.POST['fecha'], inicio, fin)}, safe=False)

                        form = AgendaPracticasTutoriaForm(request.POST)
                        if form.is_valid():
                            instance = AgendaPracticasTutoria(docente=perfilprincipal.profesor,
                                                              asunto=form.cleaned_data['asunto'],
                                                              fecha=form.cleaned_data['fecha'],
                                                              hora_inicio=inicio,
                                                              hora_fin=fin,
                                                              observacion=form.cleaned_data['observacion'],
                                                              url_reunion=form.cleaned_data['url_reunion'],
                                                              turno=turno)
                            instance.save(request)
                            for est in request.POST.getlist('estudiantes'):
                                estudiante = EstudiantesAgendaPracticasTutoria(cab=instance, estudiante_id=int(est))
                                estudiante.save(request)
                            log(u'Adiciono Tutoria a Agenda: %s' % instance, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'editagenda':
                try:
                    with transaction.atomic():
                        filtro = AgendaPracticasTutoria.objects.get(pk=int(request.POST['id']))
                        if filtro.turno:
                            inicio = filtro.turno.comienza
                            fin = filtro.turno.termina
                        elif 'hora_inicio' in request.POST:
                            inicio = request.POST['hora_inicio']
                            fin = request.POST['hora_fin']
                        if AgendaPracticasTutoria.objects.filter(docente=perfilprincipal.profesor, fecha=request.POST['fecha'], hora_inicio=inicio, status=True).exclude(pk=filtro.pk).exclude(estados_agenda=3).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "mensaje": 'Turno ya esta ocupado ({} {} - {}).'.format(request.POST['fecha'], inicio, fin)}, safe=False)
                        form = AgendaPracticasTutoriaForm(request.POST, instance=filtro)
                        if form.is_valid():
                            filtro.docente = perfilprincipal.profesor
                            filtro.asunto = form.cleaned_data['asunto']
                            filtro.fecha = form.cleaned_data['fecha']
                            filtro.hora_inicio = inicio
                            filtro.hora_fin = fin
                            filtro.observacion = form.cleaned_data['observacion']
                            filtro.url_reunion = form.cleaned_data['url_reunion']
                            filtro.turno = form.cleaned_data['turno'] if 'turno' in request.POST else None
                            filtro.save(request)
                            lista_estudiante = request.POST.getlist('estudiantes')
                            excluidos = EstudiantesAgendaPracticasTutoria.objects.filter(cab=form.instance, status=True).exclude(estudiante__in=lista_estudiante)
                            excluidos.update(status=False)
                            for est in lista_estudiante:
                                if not EstudiantesAgendaPracticasTutoria.objects.filter(cab=form.instance, estudiante_id=int(est), status=True).exists():
                                    estudiante = EstudiantesAgendaPracticasTutoria(cab=form.instance, estudiante_id=int(est))
                                    estudiante.save(request)
                            log(u'Editar Tutoria a Agenda: %s' % filtro, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            elif action == 'delenlaceclase':
                try:
                    clase = ClaseAsincronica.objects.get(clase_id=request.POST['id'], idforomoodle=request.POST['idforo'])
                    clase.delete()
                    log(u'Elimino clase asincrónica: %s' % clase, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'anularagenda':
                try:
                    with transaction.atomic():
                        filtro = AgendaPracticasTutoria.objects.get(pk=int(request.POST['id']))
                        form = FinalizarAgendaTutoriaForm(request.POST, instance=filtro)
                        if form.is_valid():
                            filtro.fecha_conclusion = datetime.now()
                            filtro.hora_horaconclusion = datetime.now().time()
                            filtro.estados_agenda = 3
                            filtro.conclusion = form.cleaned_data['conclusion']
                            filtro.save(request)
                            log(u'Anulo Tutoria a Agenda: %s' % filtro, request, "edit")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'finagenda':
                try:
                    with transaction.atomic():
                        filtro = AgendaPracticasTutoria.objects.get(pk=int(request.POST['id']))
                        if filtro.estados_agenda == 0:
                            filtro.estados_agenda = 1
                            filtro.fecha_conclusion = datetime.now()
                            filtro.hora_horaconclusion = datetime.now().time()
                            filtro.save(request)
                            datos = request.POST.getlist('practicaseleccionadas[]')
                            if datos:
                                count = 0
                                while count < len(datos):
                                    id = int(datos[count])
                                    estudiante = EstudiantesAgendaPracticasTutoria.objects.get(pk=id)
                                    check = True if datos[count + 1] == '1' else False
                                    if check:
                                        observacionfalta = datos[count + 2]
                                        observacion = datos[count + 3]
                                        sugerencia = datos[count + 4]
                                        urlvideo = datos[count + 5]
                                        evidencia = None
                                        practica = PracticasPreprofesionalesInscripcion.objects.get(pk=estudiante.estudiante.pk)
                                        fecha = filtro.fecha
                                        tutoriasalumnos = PracticasTutoria(practica=practica,
                                                                           observacion=observacion,
                                                                           sugerencia=sugerencia,
                                                                           urlvideo=urlvideo,
                                                                           fechainicio=fecha,
                                                                           fechafin=fecha)
                                        if 'practicaseleccionadas{}'.format(estudiante.estudiante.id) in request.FILES:
                                            evidencia = request.FILES['practicaseleccionadas{}'.format(estudiante.estudiante.id)]
                                            nombredocumento = tutoriasalumnos.practica.inscripcion.persona.__str__()
                                            nombrecompletodocumento = remover_caracteres_especiales_unicode(nombredocumento).lower().replace(' ', '_')
                                            evidencia._name = generar_nombre(nombrecompletodocumento, evidencia._name)
                                            if evidencia.size > 10485760:
                                                transaction.set_rollback(True)
                                                return JsonResponse({"result": True, "mensaje": "Error, archivo mayor a 10 Mb."}, safe=False)
                                            tutoriasalumnos.archivo = evidencia
                                        tutoriasalumnos.save(request)
                                        log(u'Adiciono Tutoria Académica: %s' % tutoriasalumnos, request, "edit")
                                        count += 6
                                    else:
                                        observacionfalta = datos[count + 2]
                                        estudiante.observacion = observacionfalta
                                        count += 6
                                    estudiante.asistio = check
                                    estudiante.fecha_asistencia = datetime.now()
                                    estudiante.hora_asistencia = datetime.now().time()
                                    estudiante.save(request)
                            log(u'Finalizo la tutoria #%s' % filtro.pk, request, "edit")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "mensaje": "Acción no permitida, actividad ya fue finalizada."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'deleteevidenciappp':
                try:
                    with transaction.atomic():
                        id = request.POST['id']
                        # (pk=int(encrypt(request.POST['id']))
                        filtro = InformeMensualDocentesPPP.objects.get(pk=int(encrypt(id)))
                        filtro.delete()
                        log(u'Eliminar registro de evidencia: %s' % filtro, request, "del")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": str(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'deletetutoriaagendada':
                try:
                    with transaction.atomic():
                        id = request.POST['id']
                        filtro = AgendaPracticasTutoria.objects.get(pk=id)
                        filtro.status = False
                        filtro.save(request)
                        log(u'Eliminar registro de evidencia: %s' % filtro, request, "del")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": str(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'notificaremailagenda':
                try:
                    with transaction.atomic():
                        id = request.POST['id']
                        filtro = AgendaPracticasTutoria.objects.get(pk=id)
                        estudiantes = EstudiantesAgendaPracticasTutoria.objects.filter(status=True, cab=filtro)
                        for es in estudiantes:
                            asunto = '💡 Tutoría de Practicas: {}'.format(filtro.asunto)
                            template = 'emails/tutorias_agendadas.html'
                            datos_email = {'sistema': 'SGA UNEMI', 'filtro': filtro, 'estudiante': es}
                            lista_email = [es.estudiante.inscripcion.persona.emailinst, ]
                            # lista_email = ['hllerenaa@unemi.edu.ec',]
                            send_html_mail(asunto, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[4][1])
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": str(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'deletetutoria':
                try:
                    filtro = PracticasTutoria.objects.get(pk=request.POST['id'])
                    filtro.status = False
                    filtro.save(request)
                    log(u'Elimino tutoria {}'.format(filtro.pk), request, "del")
                    return JsonResponse({"result": "ok", "pk": filtro.pk})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'addguardartutoria':
                try:
                    datos = json.loads(request.POST['lista_items1'])
                    if datos:
                        for elemento in datos:
                            observacion = elemento['obser'].strip()
                            sugerencia = elemento['sug'].strip()
                            # archivo =  elemento['arch']
                            practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(elemento['idp']))

                            fecha = convertir_fecha(encrypt(request.POST['dia']) + '-' + encrypt(request.POST['mes']) + '-' + encrypt(request.POST['anio']))

                            tutoriasalumnos = PracticasTutoria(practica=practica,
                                                               observacion=observacion,
                                                               sugerencia=sugerencia,
                                                               fechainicio=fecha,
                                                               fechafin=fecha)
                            tutoriasalumnos.save(request)
                            log(u'Adiciono Tutoria Académica: %s' % tutoriasalumnos, request, "edit")
                    return JsonResponse({"result": "ok"})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            if action == 'addguardartutoria2':
                try:
                    datos = request.POST.getlist('practicaseleccionadas[]')
                    if datos:
                        count = 0
                        while count < len(datos):
                            id = datos[count]
                            check = True if datos[count + 1] == 'on' else False
                            if check:
                                observacion = datos[count + 2]
                                sugerencia = datos[count + 3]
                                urlvideo = datos[count + 4]
                                evidencia = None
                                practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(id))
                                fecha = convertir_fecha(encrypt(request.POST['dia']) + '-' + encrypt(request.POST['mes']) + '-' + encrypt(request.POST['anio']))
                                tutoriasalumnos = PracticasTutoria(practica=practica,
                                                                   observacion=observacion,
                                                                   sugerencia=sugerencia,
                                                                   urlvideo=urlvideo,
                                                                   fechainicio=fecha,
                                                                   fechafin=fecha)
                                if 'practicaseleccionadas{}'.format(id) in request.FILES:
                                    evidencia = request.FILES['practicaseleccionadas{}'.format(id)]
                                    nombredocumento = tutoriasalumnos.practica.inscripcion.persona.__str__()
                                    nombrecompletodocumento = remover_caracteres_especiales_unicode(nombredocumento).lower().replace(' ', '_')
                                    evidencia._name = generar_nombre(nombrecompletodocumento, evidencia._name)
                                    if evidencia.size > 10485760:
                                        return JsonResponse({"result": True, "mensaje": "Error, archivo mayor a 10 Mb."}, safe=False)
                                    tutoriasalumnos.archivo = evidencia
                                tutoriasalumnos.save(request)
                                log(u'Adiciono Tutoria Académica: %s' % tutoriasalumnos, request, "edit")
                                count += 5
                            else:
                                count += 4
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": ex}, safe=False)

            if action == 'editguardartutoria2':
                try:
                    datos = request.POST.getlist('practicaseleccionadas[]')
                    if datos:
                        count = 0
                        while count < len(datos):
                            id = datos[count]
                            check = True if datos[count + 1] == 'on' else False
                            if check:
                                observacion = datos[count + 2]
                                sugerencia = datos[count + 3]
                                urlvideo = datos[count + 4]
                                evidencia = None
                                tutoriasalumnos = PracticasTutoria.objects.get(pk=int(id))
                                fecha = convertir_fecha(encrypt(request.POST['dia']) + '-' + encrypt(request.POST['mes']) + '-' + encrypt(request.POST['anio']))
                                tutoriasalumnos.observacion = observacion
                                tutoriasalumnos.sugerencia = sugerencia
                                tutoriasalumnos.urlvideo = urlvideo
                                tutoriasalumnos.fechainicio = fecha
                                tutoriasalumnos.fechafin = fecha
                                if 'practicaseleccionadas{}'.format(id) in request.FILES:
                                    evidencia = request.FILES['practicaseleccionadas{}'.format(id)]
                                    nombredocumento = tutoriasalumnos.practica.inscripcion.persona.__str__()
                                    nombrecompletodocumento = remover_caracteres_especiales_unicode(nombredocumento).lower().replace(' ', '_')
                                    evidencia._name = generar_nombre(nombrecompletodocumento, evidencia._name)
                                    if evidencia.size > 10485760:
                                        return JsonResponse({"result": True, "mensaje": "Error, archivo mayor a 10 Mb."}, safe=False)
                                    tutoriasalumnos.archivo = evidencia
                                tutoriasalumnos.save(request)
                                log(u'Edito Tutoria Académica: %s' % tutoriasalumnos, request, "edit")
                                count += 5
                            else:
                                count += 4
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": ex}, safe=False)

            if action == 'culminatutoria':
                try:
                    practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['idp']))
                    practica.culminatutoria = True
                    practica.fechaculminacion = datetime.now()
                    practica.save()

                    log(u'Culmino Tutoria Académica: %s' % practica, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            if action == 'tutoriaadicional':
                try:
                    data['form2'] = TutoriaAdicionalForm()
                    template = get_template("pro_laboratoriocronograma/addtutoriaadicional.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'detallecongreso':
                try:
                    data['congreso'] = congreso = PlanificarPonencias.objects.get(id=encrypt(request.POST['id']))
                    data['congresorecorrido'] = congreso.planificarponenciasrecorrido_set.filter(status=True).order_by('id')

                    if congreso.id > 433:
                        data['criteriosponencia'] = congreso.planificarponenciascriterio_set.filter(status=True).order_by('id')

                    template = get_template("pro_laboratoriocronograma/detallecongreso.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detallecapacitacion':
                try:
                    data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=request.POST['id'])
                    data['capacitaciondetallecriterio'] = capacitacion.planificarcapacitacionesdetallecriterios_set.filter(status=True).order_by('criterio_id')
                    data['capacitacionrecorrido'] = capacitacion.planificarcapacitacionesrecorrido_set.filter(status=True).order_by('id')

                    template = get_template("pro_laboratoriocronograma/detallecapacitacion.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'generanumeroconvenio':
                try:
                    capacitacion = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not capacitacion.numeroconvenio:
                        secuencia = secuencia_convenio_devengacion(1)

                        if PlanificarCapacitaciones.objects.filter(fechaconvenio__year=datetime.now().year, numeroconvenio=secuencia, tipo=1, status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Error al generar el convenio, intente nuevamente"})

                        capacitacion.fechaconvenio = datetime.now()
                        capacitacion.numeroconvenio = secuencia
                        capacitacion.firmadocente = False
                        capacitacion.save(request)
                        log(u'Editó solicitud de capacitacion/actualización: %s' % capacitacion, request, "edit")

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar la secuencia del convenio."})

            if action == 'conveniodevengacion_pdf_old':
                try:
                    data = {}

                    data['dvice'] = dth = Departamento.objects.get(pk=158)
                    # data['dvice'] = dth = DistributivoPersona.objects.get(denominacionpuesto_id=115, estadopuesto_id=1, status=True)

                    titulos = dth.responsable.titulo3y4nivel()
                    data['titulo1dth'] = titulos['tit1']
                    data['titulo2dth'] = titulos['tit2']

                    data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=int(encrypt(request.POST['id'])))
                    data['cronograma'] = cronograma = capacitacion.cronograma
                    data['monto_natural'] = num2words(cronograma.monto, lang='es')

                    titulos = profesor.persona.titulo3y4nivel()
                    hoy = datetime.now().date()
                    data['titulo1bene'] = titulos['tit1']
                    data['titulo2bene'] = titulos['tit2']
                    data['fecha_natural'] = {'dia': num2words(hoy.day, lang='es'), 'mes': MESES_CHOICES[hoy.month - 1][1], 'anio': num2words(hoy.year, lang='es')}
                    # data['numeroconvenio'] = "N° " + str(capacitacion.numeroconvenio).zfill(3) + ".DEPA.LOES." + str(capacitacion.fechaconvenio.year)
                    data['numeroconvenio'] = "N° " + str(capacitacion.numeroconvenio).zfill(3) + '-' + str(capacitacion.fechaconvenio.year)
                    data['fechaconvenio'] = fechaletra_corta(capacitacion.fechaconvenio)
                    data['fechaconveniodevengacion'] = fechaletra_corta(cronograma.fechaconvenio)
                    data['fechainiciocap'] = str(capacitacion.fechainicio.day) + " de " + MESES_CHOICES[capacitacion.fechainicio.month - 1][1].capitalize() + " del " + str(capacitacion.fechainicio.year)
                    data['fechafincap'] = str(capacitacion.fechafin.day) + " de " + MESES_CHOICES[capacitacion.fechafin.month - 1][1].capitalize() + " del " + str(capacitacion.fechafin.year)
                    return conviert_html_to_pdf(
                        'pro_laboratoriocronograma/conveniodevengacion_pdf_new.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % "Error al generar el reporte")

            if action == 'conveniodevengacion_pdf':
                try:
                    data = {}

                    data['dvice'] = dth = Departamento.objects.get(pk=158)
                    # data['dvice'] = dth = DistributivoPersona.objects.get(denominacionpuesto_id=115, estadopuesto_id=1, status=True)

                    titulos = dth.responsable.titulo3y4nivel()
                    data['titulo1dth'] = titulos['tit1']
                    data['titulo2dth'] = titulos['tit2']

                    data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=int(encrypt(request.POST['id'])))
                    data['cronograma'] = cronograma = capacitacion.cronograma
                    data['monto_natural'] = num2words(cronograma.monto, lang='es')

                    titulos = profesor.persona.titulo3y4nivel()
                    hoy = datetime.now().date()
                    data['titulo1bene'] = titulos['tit1']
                    data['titulo2bene'] = titulos['tit2']
                    data['fecha_natural'] = {'dia': num2words(hoy.day, lang='es'), 'mes': MESES_CHOICES[hoy.month - 1][1], 'anio': num2words(hoy.year, lang='es')}
                    # data['numeroconvenio'] = "N° " + str(capacitacion.numeroconvenio).zfill(3) + ".DEPA.LOES." + str(capacitacion.fechaconvenio.year)
                    data['numeroconvenio'] = "N° " + str(capacitacion.numeroconvenio).zfill(3) + '-' + str(capacitacion.fechaconvenio.year)
                    data['fechaconvenio'] = fechaletra_corta(capacitacion.fechaconvenio)
                    data['fechaconveniodevengacion'] = fechaletra_corta(cronograma.fechaconvenio)
                    data['fechainiciocap'] = str(capacitacion.fechainicio.day) + " de " + MESES_CHOICES[capacitacion.fechainicio.month - 1][1].capitalize() + " del " + str(capacitacion.fechainicio.year)
                    data['fechafincap'] = str(capacitacion.fechafin.day) + " de " + MESES_CHOICES[capacitacion.fechafin.month - 1][1].capitalize() + " del " + str(capacitacion.fechafin.year)

                    output_folder = os.path.join(SITE_STORAGE, 'media', 'documentos')
                    current_date = datetime.now()
                    output_folder = os.path.join(output_folder, str(current_date.year), str(current_date.month).zfill(2), str(current_date.day).zfill(2))
                    os.makedirs(output_folder, exist_ok=True)
                    pdfname = generar_nombre("conveniodevengaciondocente_", str(capacitacion.id))
                    reportfile = conviert_html_to_pdfsaveqr_generico(request,
                                                                     'pro_laboratoriocronograma/conveniodevengacion_pdf_new.html', {
                                                                         'pagesize': 'A4',
                                                                         'data': data,
                                                                     }, output_folder, pdfname + '.pdf')

                    archivoconvenio_path = 'documentos/{}/{}/{}/{}.pdf'.format(
                        current_date.year,
                        str(current_date.month).zfill(2),
                        str(current_date.day).zfill(2),
                        pdfname
                    )
                    capacitacion.archivoconvenio = archivoconvenio_path
                    capacitacion.save(request)
                    random_number = random.randint(1, 1000000)
                    data['archivo'] = capacitacion.archivoconvenio.url
                    archivo = f"{capacitacion.archivoconvenio.url}?cache={random_number}"
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = capacitacion.id
                    data['action_firma'] = 'firmaconvenio'
                    if capacitacion.profesor.tienetoken:
                        return JsonResponse({"result": True, 'data': {}, 'tienetoken': True})

                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'tienetoken': False})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % "Error al generar el reporte")

            if action == 'firmaconvenio':
                idinforme = int(encrypt(request.POST['id_objeto']))
                capacitacion = PlanificarCapacitaciones.objects.get(pk=idinforme)
                try:
                    # Parametros
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas:
                        raise NameError("Debe seleccionar ubicación de la firma")
                    x = txtFirmas[-1]

                    tienefirmas = False
                    firma = request.FILES["firma"]
                    passfirma = request.POST['palabraclave']
                    url_archivo = (SITE_STORAGE + request.POST["url_archivo"]).replace('\\', '/')
                    _name = 'conveniodevengaciondocente_' + str(capacitacion.id) + '_2'
                    current_date = datetime.now()
                    archivoconvenio_path = 'documentos/{}/{}/{}'.format(
                        current_date.year,
                        str(current_date.month).zfill(2),
                        str(current_date.day).zfill(2)
                    )
                    folder = os.path.join(SITE_STORAGE, 'media', archivoconvenio_path, '')
                    try:
                        os.remove(folder + _name + '.pdf')
                    except Exception as ex:
                        pass
                    # Firmar y guardar archivo en folder definido.
                    firma = firmararchivogenerado(request, passfirma, firma, url_archivo, folder, _name, x["numPage"],
                                                  x["x"], x["y"], x["width"], x["height"])
                    if firma != True:
                        raise NameError(firma)
                    log(u'Firmo Documento: {}'.format(_name), request, "add")

                    folder_save = os.path.join(archivoconvenio_path, '').replace('\\', '/')
                    url_file_generado = f'{folder_save}{_name}.pdf'
                    capacitacion.archivoconvenio = url_file_generado
                    capacitacion.firmadocente = True
                    capacitacion.save(request)

                    rutapdf = folder + 'conveniodevengaciondocente_' + str(capacitacion.id) + '_' + '.pdf'
                    if os.path.isfile(rutapdf):
                        os.remove(rutapdf)
                    log(u'firmo convenio capacitacion: {}'.format(capacitacion), request, "add")
                    # return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
                    return HttpResponseRedirect(f'/pro_laboratoriocronograma?action=planificarcapacitaciones&convocatoria={capacitacion.cronograma_id}')
                except Exception as ex:
                    transaction.set_rollback(True)
                    # return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)
                    return HttpResponseRedirect(
                        f'/pro_laboratoriocronograma?action=planificarcapacitaciones&convocatoria={capacitacion.cronograma_id}&info=SysError: Error al guardar. {ex}')

            #                    return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

            if action == 'editcapacitacionth':
                try:
                    persona = request.session['persona']
                    capacitacion = Capacitacion.objects.get(pk=int(request.POST['id']))

                    f = CapacitacionPersonaDocenteForm(request.POST, request.FILES)
                    if f.is_valid():
                        capacitacion.institucion = f.cleaned_data['institucion']
                        capacitacion.nombre = f.cleaned_data['nombre']
                        capacitacion.descripcion = f.cleaned_data['descripcion']
                        capacitacion.tipocurso = f.cleaned_data['tipocurso']
                        capacitacion.tipocapacitacion = f.cleaned_data['tipocapacitacion']
                        capacitacion.tipocertificacion = f.cleaned_data['tipocertificacion']
                        capacitacion.tipoparticipacion = f.cleaned_data['tipoparticipacion']
                        # capacitacion.auspiciante = f.cleaned_data['auspiciante']
                        capacitacion.areaconocimiento = f.cleaned_data['areaconocimiento']
                        capacitacion.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                        capacitacion.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                        capacitacion.pais = f.cleaned_data['pais']
                        # capacitacion.contextocapacitacion = f.cleaned_data['contexto']
                        # capacitacion.detallecontextocapacitacion = f.cleaned_data['detallecontexto']
                        capacitacion.provincia = f.cleaned_data['provincia']
                        capacitacion.canton = f.cleaned_data['canton']
                        capacitacion.parroquia = f.cleaned_data['parroquia']
                        capacitacion.fechainicio = f.cleaned_data['fechainicio']
                        capacitacion.fechafin = f.cleaned_data['fechafin']
                        capacitacion.horas = f.cleaned_data['horas']
                        # capacitacion.expositor = f.cleaned_data['expositor']
                        capacitacion.modalidad = f.cleaned_data['modalidad']
                        capacitacion.otramodalidad = f.cleaned_data['otramodalidad']
                        capacitacion.save(request)

                        solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['idsolicitud'])))
                        solicitud.infocompletacap = True
                        solicitud.save(request)

                        log(u'Modifico capacitacion: %s' % persona, request, "edit")

                        # Enviar correo a Lic. Patricia Ortiz - UATH
                        revisor = solicitud.obtenerdatosautoridad('RHVTH', 0)
                        if revisor:
                            send_html_mail("Registro de Certificado de capacitación - " + str(profesor.persona),
                                           "emails/notificacion_capdocente.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fase': 'CER',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'numero': solicitud.id,
                                            'docente': profesor.persona,
                                            'autoridad1': revisor.persona,
                                            'autoridad2': '',
                                            't': miinstitucion()
                                            },
                                           revisor.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )

                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            if action == 'segmento':
                try:
                    data['carrera'] = carrera = Carrera.objects.get(pk=int(request.POST['carrera']), status=True)
                    data['periodocatedra'] = periodocatedra = PeriodoCatedra.objects.filter(pk=request.POST['idperiodo'], status=True)[0]
                    data['inscripcioncatedras'] = inscripcioncatedras = InscripcionCatedra.objects.filter(periodocatedra=periodocatedra, inscripcion__carrera=carrera, status=True, inscripcion__inscripcioncatedra__supervisor__persona=persona).order_by('materia__asignaturamalla__nivelmalla', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                    data['total_inscritos'] = inscripcioncatedras.count()
                    template = get_template("pro_laboratoriocronograma/segmento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'asistact':
                try:
                    participante = ParticipanteActividadExtraCurricular.objects.get(pk=request.POST['id'])
                    participante.asistencia = float(request.POST['valor'])
                    participante.save(request)
                    log(u'Participante Actividad ExtraCurricular: %s' % participante, request, "edit")
                    return JsonResponse({"result": "ok", "valor": participante.asistencia, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'notaact':
                try:
                    participante = ParticipanteActividadExtraCurricular.objects.get(pk=request.POST['id'])
                    participante.nota = float(request.POST['valor'])
                    participante.save(request)
                    log(u'Editó Participante Actividad ExtraCurricular: %s' % participante, request, "edit")
                    return JsonResponse({"result": "ok", "valor": participante.nota, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'asistpry':
                try:
                    participante = ParticipanteProyectoVinculacion.objects.get(pk=request.POST['id'])
                    participante.asistencia = float(request.POST['valor'])
                    participante.save(request)
                    log(u'Editó Participante Proyecto de Vinculación: %s' % participante, request, "edit")
                    return JsonResponse({"result": "ok", "valor": participante.asistencia, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'asistcurso':
                try:
                    participante = MateriaAsignadaCurso.objects.get(pk=request.POST['id'])
                    participante.asistencia = float(request.POST['valor'])
                    participante.save(request)
                    log(u'Editó Materia Asignada Curso: %s' % participante, request, "edit")
                    return JsonResponse({"result": "ok", "valor": participante.asistencia, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'aceptarrechazardistributivo':
                try:
                    profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                    if request.POST['valor'] == '1':
                        profesormateria.aceptarmateria = True
                    else:
                        profesormateria.aceptarmateria = False
                        profesormateria.hora = 0
                    profesormateria.aceptarmateriaobs = request.POST['motivo']
                    profesormateria.save(request)
                    # profesormateria.profesor.actualizar_todo_distributivo_docente(request, periodo)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'aceptarrechazardistributivohorario':
                try:
                    profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                    if request.POST['valor'] == '1':
                        profesormateria.aceptarhorario = True
                    else:
                        profesormateria.aceptarhorario = False
                    profesormateria.fecha_horario = datetime.now()
                    profesormateria.aceptarhorarioobs = request.POST['motivo']
                    profesormateria.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'notacurso':
                try:
                    participante = MateriaAsignadaCurso.objects.get(pk=request.POST['id'])
                    participante.calificacion = float(request.POST['valor'])
                    participante.save(request)
                    log(u'Editó Nota de curso: %s' % participante, request, "edit")
                    return JsonResponse({"result": "ok", "valor": participante.calificacion, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'afirmaasignaturapreferencia':
                try:
                    materia = AsignaturaMalla.objects.get(pk=int(encrypt(request.POST['id'])), status=True)
                    nombres = materia.asignatura.nombre
                    return JsonResponse({"result": "ok", 'asignatura': nombres, 'idasigmalla': materia.id})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'conasignaturapreferencia':
                try:
                    materia = AsignaturaMallaPreferencia.objects.get(pk=request.POST['id'], status=True)
                    nombres = materia.asignaturamalla.asignatura.nombre
                    return JsonResponse({"result": "ok", 'asignatura': nombres, 'idmateripreferencia': materia.id})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'conasignaturapreferenciaposgrado':
                try:
                    materia = AsignaturaMallaPreferenciaPosgrado.objects.get(pk=request.POST['id'], status=True)
                    nombres = materia.asignaturamalla.asignatura.nombre
                    return JsonResponse({"result": "ok", 'asignatura': nombres, 'idmateripreferencia': materia.id})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'conactividaddocente':
                try:
                    actividad = PreferenciaDetalleActividadesCriterio.objects.get(pk=request.POST['id'], status=True)
                    return JsonResponse({"result": "ok", 'actividad': actividad.criteriodocenciaperiodo.criterio.nombre, 'idactividad': actividad.id})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'conactividadinvestigacion':
                try:
                    actividad = PreferenciaDetalleActividadesCriterio.objects.get(pk=request.POST['id'], status=True)
                    return JsonResponse({"result": "ok", 'actividad': actividad.criterioinvestigacionperiodo.criterio.nombre, 'idactividad': actividad.id})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'conactividadgestion':
                try:
                    actividad = PreferenciaDetalleActividadesCriterio.objects.get(pk=request.POST['id'], status=True)
                    return JsonResponse({"result": "ok", 'actividad': actividad.criteriogestionperiodo.criterio.nombre, 'idactividad': actividad.id})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addasignaturapreferencia':
                try:
                    mallapreferencia = AsignaturaMallaPreferencia(profesor_id=request.POST['idprofesor'],
                                                                  asignaturamalla_id=request.POST['idasignaturamalla'],
                                                                  periodo_id=request.POST['idperiodo'],
                                                                  sesion_id=request.POST['id_sesion'])
                    mallapreferencia.save(request)
                    log(u'Adiciono Asignatura de preferencia: %s' % mallapreferencia, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addasignaturapreferenciaposgrado':
                try:
                    mallapreferencia = AsignaturaMallaPreferenciaPosgrado(profesor_id=request.POST['idprofesor'],
                                                                          asignaturamalla_id=request.POST['idasignaturamalla'],
                                                                          periodo_id=request.POST['idperiodo'])
                    mallapreferencia.save(request)
                    if mallapreferencia.profesor.persona.emailinst:
                        lista = [mallapreferencia.profesor.persona.emailinst, 'desarrollo.sistemas@unemi.edu.ec']
                        send_html_mail("Preferencia asignatura", "emails/preferenciaposgrado.html", {'sistema': request.session['nombresistema'], 'asignatura': mallapreferencia.asignaturamalla.asignatura.nombre, 'programa': mallapreferencia.asignaturamalla.malla.carrera.nombre, 'cohorte': mallapreferencia.periodo.nombre, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Adiciono Asignatura de preferencia posgrado: %s' % mallapreferencia, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delasignaturapreferencia':
                try:
                    asigpreferencia = AsignaturaMallaPreferencia.objects.get(pk=request.POST['idmatpreferencia'])
                    asigpreferencia.status = False
                    asigpreferencia.save(request)
                    log(u'Elimino Asignatura de preferencia: %s' % asigpreferencia, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delasignaturapreferenciaposgrado':
                try:
                    asigpreferencia = AsignaturaMallaPreferenciaPosgrado.objects.get(pk=request.POST['idmatpreferencia'])
                    asigpreferencia.delete()
                    log(u'Elimino Asignatura de preferencia: %s' % asigpreferencia, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delactividadpreferencia':
                try:
                    actividadpreferencia = PreferenciaDetalleActividadesCriterio.objects.get(pk=request.POST['idactividad'])
                    log(u'Elimino Actividad de preferencia: %s' % actividadpreferencia, request, "add")
                    actividadpreferencia.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'notapry':
                try:
                    participante = ParticipanteProyectoVinculacion.objects.get(pk=request.POST['id'])
                    participante.nota = float(request.POST['valor'])
                    participante.save(request)
                    log(u'Editó Nota Participante Proyecto de Vinculación: %s' % participante, request, "edit")
                    return JsonResponse({"result": "ok", "valor": participante.nota, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addasistencia':
                try:
                    cadenaselect = request.POST['cadenaselect']
                    cadenanoselect = request.POST['cadenanoselect']
                    fechaactividadesid = request.POST['fechaactividadesid']
                    cadenadatos = cadenaselect.split(',')
                    cadenanodatos = cadenanoselect.split(',')
                    for cadena in cadenadatos:
                        if cadena:
                            if PaeAsistenciaFechaActividad.objects.filter(actividadfecha_id=fechaactividadesid, inscripcionactividad_id=cadena, status=True).exists():
                                resultadovalores = PaeAsistenciaFechaActividad.objects.get(actividadfecha_id=fechaactividadesid, inscripcionactividad_id=cadena, status=True)
                                resultadovalores.asistencia = True
                                resultadovalores.save(request)
                                log(u'Adicionó Asistencia de actividad: %s' % resultadovalores, request, "add")
                            else:
                                resultadovalores = PaeAsistenciaFechaActividad(actividadfecha_id=fechaactividadesid,
                                                                               inscripcionactividad_id=cadena,
                                                                               asistencia=True)
                                resultadovalores.save(request)
                                log(u'Adicionó Asistencia de actividad: %s' % resultadovalores, request, "add")
                    for cadenano in cadenanodatos:
                        if cadenano:
                            if PaeAsistenciaFechaActividad.objects.filter(actividadfecha_id=fechaactividadesid, inscripcionactividad_id=cadenano, status=True).exists():
                                resultadovalores = PaeAsistenciaFechaActividad.objects.get(actividadfecha_id=fechaactividadesid, inscripcionactividad_id=cadenano, status=True)
                                resultadovalores.asistencia = False
                                resultadovalores.save(request)
                                log(u'Editó Asistencia de actividad: %s' % resultadovalores, request, "edit")
                            else:
                                resultadovalores = PaeAsistenciaFechaActividad(actividadfecha_id=fechaactividadesid,
                                                                               inscripcionactividad_id=cadenano,
                                                                               asistencia=False)
                                resultadovalores.save(request)
                                log(u'Editó Asistencia de actividad: %s' % resultadovalores, request, "edit")
                    return JsonResponse({"result": "ok", "mensaje": "DATOS GUARDADOS CORRECTAMENTE."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'horaspry':
                try:
                    horas = ParticipanteProyectoVinculacion.objects.get(pk=request.POST['id'])
                    horas.horas = float(request.POST['valor'])
                    horas.save(request)
                    return JsonResponse({"result": "ok", "valor": horas.horas})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'notappp':
                try:
                    participante = ParticipantePracticaPreProfesional.objects.get(pk=request.POST['id'])
                    participante.nota = float(request.POST['valor'])
                    participante.save(request)
                    return JsonResponse({"result": "ok", "valor": participante.nota, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'asistppp':
                try:
                    participante = ParticipantePracticaPreProfesional.objects.get(pk=request.POST['id'])
                    if request.POST['valor'] == u'true':
                        participante.asistencia = True
                    else:
                        participante.asistencia = False
                    participante.save(request)
                    return JsonResponse({"result": "ok", "valor": participante.nota, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'observacionppp':
                try:
                    asistencia = ParticipantePracticaPreProfesional.objects.get(pk=request.POST['id'])
                    asistencia.observacion = request.POST['valor']
                    asistencia.save(request)
                    return JsonResponse({"result": "ok", "valor": asistencia.observacion})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'pdflistainscritos':
                try:
                    actividad = PaeActividadesPeriodoAreas.objects.get(pk=request.POST['idactividad'])
                    return conviert_html_to_pdf('adm_paextracurricular/inscritosactividades_pdf.html', {'pagesize': 'A4', 'data': actividad.listado_inscritos_reporte()})
                except Exception as ex:
                    pass

            elif action == 'evidenciasilabos_pdf':
                try:
                    evidencias = evidenciassilabosxcarrera(periodo, persona)
                    return evidencias
                except Exception as ex:
                    pass

            elif action == 'totalestutoriasacademicas':
                try:
                    profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.POST['profesorid'])))
                    evidencias = totalestutoriasacademicas(periodo, profesorseleccionado)
                    return evidencias
                except Exception as ex:
                    pass

            elif action == 'totalorientarmodallinea':
                try:
                    idcrite = request.POST['idcrite']
                    profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.POST['profesorid'])))
                    evidencias = totalorientarmodallinea(periodo, profesorseleccionado, idcrite)
                    return evidencias
                except Exception as ex:
                    pass

            elif action == 'seguimientotransversal':
                try:
                    idcrite = request.POST['idcrite']
                    profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.POST['profesorid'])))
                    evidencias = seguimientotransver(periodo, profesorseleccionado, idcrite)
                    return evidencias
                except Exception as ex:
                    pass

            elif action == 'sistemanacionalnivadmision':
                try:
                    idcrite = request.POST['idcrite']
                    profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.POST['profesorid'])))
                    evidencias = sistemanacionalnivadmision(periodo, profesorseleccionado, idcrite)
                    return evidencias
                except Exception as ex:
                    pass

            elif action == 'detallerecursos':
                try:
                    tipo = request.POST['tipo']
                    detalleevaluado = Profesor.objects.get(pk=request.POST['codigoprofesor'])
                    evidenciasrecursos = evidenciasrecursossilabo(periodo, detalleevaluado.persona, tipo)
                    return evidenciasrecursos
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detallepracticas':
                try:
                    docentepracticas = Profesor.objects.get(pk=int(encrypt(request.POST['codigoprofesor'])))
                    evidenciasrecursos = prapreprofesionales(docentepracticas, periodo)
                    return evidenciasrecursos
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addpractica':
                try:
                    materia = Materia.objects.get(pk=int(encrypt(request.POST['id'])), status=True)
                    profesormateria = profesor.profesormateria_set.filter(materia=materia, status=True, tipoprofesor_id__in=[TIPO_DOCENTE_PRACTICA, TIPO_DOCENTE_AYUDANTIA])[0]
                    f = PracticaPreProfesionalForm(request.POST)
                    if f.is_valid():
                        if not f.cleaned_data['grupopractica']:
                            return JsonResponse({"result": "bad", "mensaje": u"Seleccione un grupo de práctica."})
                        if not profesormateria.esta_dia_con_horario_practica(f.cleaned_data['fecha'], f.cleaned_data['grupopractica']):
                            return JsonResponse({"result": "bad", "mensaje": u"No concuerda el dia de la fecha con el horario de la materia / no tiene grupo asignado"})
                        if PracticaPreProfesional.objects.filter(materia=materia, profesor=profesor, fecha=f.cleaned_data['fecha'], grupopractica=f.cleaned_data['grupopractica']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe una practica registrada para esa materia en ese dia."})
                        practica = PracticaPreProfesional(materia=materia,
                                                          profesor=profesor,
                                                          lugar=f.cleaned_data['lugar'],
                                                          fecha=f.cleaned_data['fecha'],
                                                          horas=f.cleaned_data['horas'],
                                                          objetivo=f.cleaned_data['objetivo'],
                                                          calificar=f.cleaned_data['calificar'],
                                                          grupopractica=f.cleaned_data['grupopractica'],
                                                          calfmaxima=f.cleaned_data['califmaxima'] if f.cleaned_data['calificar'] else 0,
                                                          calfminima=f.cleaned_data['califminima'] if f.cleaned_data['calificar'] else 0)
                        practica.save(request)
                        for alumnopractica in practica.grupopractica.listado_inscritos_grupos_practicas():
                            participante = ParticipantePracticaPreProfesional(practica=practica, materiaasignada=alumnopractica.materiaasignada)
                            participante.save(request)
                        log(u'Registro Guia de Práctica : %s' % practica, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aprobar':
                try:
                    registro = EvidenciaActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                    registro.aprobado = True
                    registro.usuarioaprobado = persona.usuario
                    registro.fechaaprobado = datetime.now()
                    registro.save(request)
                    log(u'Aprobo Evidencia: %s' % registro, request, "edir")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al aprobar la evidencia."})

            elif action == 'editarpractica':
                try:
                    practica = PracticaPreProfesional.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = PracticaPreProfesionalForm(request.POST)
                    if f.is_valid():
                        if not profesor.profesormateria_set.filter(materia=practica.materia, tipoprofesor_id__in=[TIPO_DOCENTE_PRACTICA, TIPO_DOCENTE_AYUDANTIA])[0].esta_dia_con_horario_practica(f.cleaned_data['fecha'], practica.grupopractica):
                            return JsonResponse({"result": "bad", "mensaje": u"No concuerda el dia de la fecha con el horario de la materia"})
                        practica.lugar = f.cleaned_data['lugar']
                        practica.fecha = f.cleaned_data['fecha']
                        practica.horas = f.cleaned_data['horas']
                        practica.objetivo = f.cleaned_data['objetivo']
                        if f.cleaned_data['calificar']:
                            practica.calfmaxima = f.cleaned_data['califmaxima']
                            practica.calfminima = f.cleaned_data['califminima']
                        else:
                            practica.calfmaxima = 0
                            practica.calfminima = 0
                        practica.save(request)
                        for participante in practica.participantepracticapreprofesional_set.all():
                            participante.save(request)
                        log(u'Modifico practica preprofesional: %s' % practica, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delpractica':
                try:
                    practica = PracticaPreProfesional.objects.get(pk=request.POST['id'])
                    log(u'Elimino practica preprofesional: %s' % practica, request, "del")
                    practica.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al elimnar los datos."})

            elif action == 'retirarpry':
                try:
                    participante = ParticipanteProyectoVinculacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    log(u'Retiro prarticipante proyecto de vinculacion: %s' % participante, request, "del")
                    participante.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al elimnar los datos."})

            elif action == 'subirevidencia':
                try:
                    subactividaddetalledistributivo = SubactividadDetalleDistributivo.objects.filter(pk=request.POST.get('ids', 0), status=True).first()
                    criterio = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id'])), distributivo__profesor=profesor, status=True)
                    # actividaddetalledistributivo = ActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id'])), criterio__distributivo__profesor=profesor, status=True)
                    f = EvidenciaActividadDetalleDistributivoForm(request.POST)
                    newfile = None
                    if not 'archivo' in request.FILES and not request.POST.get('idconf'):
                        return JsonResponse({"result": "bad", "mensaje": u"Favor subir archivo."})

                    newfile = request.FILES.get('archivo')
                    if newfile:
                        if newfile.size > 20971520:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if ext == '.pdf' or ext == '.PDF':
                                newfile._name = generar_nombre("evidencia_", newfile._name)
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extensión. pdf."})

                    if f.is_valid():
                        if f.cleaned_data['desde'] > f.cleaned_data['hasta']:
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha desde no puede ser mayor que fecha hasta."})
                        filtro = Q(hasta__month=f.cleaned_data['hasta'].month, hasta__year=f.cleaned_data['hasta'].year, status=True, criterio=criterio)
                        if subactividaddetalledistributivo:
                            filtro &= Q(subactividad=subactividaddetalledistributivo)
                        if EvidenciaActividadDetalleDistributivo.objects.filter(filtro).exclude(criterio__criterioinvestigacionperiodo__criterio__id__in=(58, 68)).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Esta actividad solo permite cargar una evidencia por mes, que corresponde al informe mensual de la actividad, los archivos adicionales deben subirse como anexo del informe del mes correspondiente."})
                        evidenciaactividaddetalledistributivo = EvidenciaActividadDetalleDistributivo(criterio=criterio,
                                                                                                      desde=f.cleaned_data['desde'],
                                                                                                      hasta=f.cleaned_data['hasta'],
                                                                                                      actividad=f.cleaned_data['actividad'],
                                                                                                      archivo=newfile,
                                                                                                      subactividad=subactividaddetalledistributivo)
                        evidenciaactividaddetalledistributivo.save(request)

                        if evidenciaactividaddetalledistributivo.archivo:
                            evidenciaaudi = EvidenciaActividadAudi(evidencia=evidenciaactividaddetalledistributivo, archivo=evidenciaactividaddetalledistributivo.archivo)
                            evidenciaaudi.save(request)

                        nfilas_ca_evi = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de evidencias
                        nfilas_evi = request.POST.getlist('nfila_evidencia[]')  # Todos los número de filas del detalle de evidencias
                        descripciones_evi = request.POST.getlist('descripcion_evidencia[]')  # Todas las descripciones
                        archivos_evi = request.FILES.getlist('archivo_evidencia[]')  # Todos los archivos
                        # Valido los archivos cargados de detalle de evidencias
                        for nfila, archivo in zip(nfilas_ca_evi, archivos_evi):
                            descripcionarchivo = 'Evidencia'
                            resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                            if resp['estado'] != "OK":
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                        # Guardar evidencias de informe
                        for nfila, descripcion in zip(nfilas_evi, descripciones_evi):
                            anexoevidencia = AnexoEvidenciaActividad(evidencia=evidenciaactividaddetalledistributivo, observacion=descripcion.strip())
                            anexoevidencia.save(request)

                            # Guardo el archivo del formato
                            for nfilaarchi, archivo in zip(nfilas_ca_evi, archivos_evi):
                                # Si la fila de la descripcion es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("anexo_evidencia_", archivoreg._name)
                                    anexoevidencia.archivo = archivoreg
                                    anexoevidencia.save(request)
                                    break

                        log(u'Evidencia Profesor Distributivo Horas: %s' % evidenciaactividaddetalledistributivo, request, "add")

                        # Generacion automatica de informe para ppp de internado rotativo
                        if docencia := criterio.criteriodocenciaperiodo:
                            if docencia.criterio.pk == TUTOR_PRACTICAS_INTERNADO_ROTATIVO:
                                pk = id if (id := request.POST.get('idconf', 0)) else 0
                                if conf := ConfiguracionInformePracticasPreprofesionales.objects.filter(pk=pk).first():
                                    generar_informe_practicas_preprofesionales(request=request, evidencia=evidenciaactividaddetalledistributivo, configuracion=conf)

                        if evidenciaactividaddetalledistributivo.criterio.criterioinvestigacionperiodo:
                            migrar_evidencia_integrante_grupo_investigacion(request=request, evidencia=evidenciaactividaddetalledistributivo, notificar=True)
                            migrar_evidencia_integrantes_proyecto_investigacion(request=request, evidencia=evidenciaactividaddetalledistributivo)

                        return JsonResponse({"result": "ok", 'id_evidencia': evidenciaactividaddetalledistributivo.pk})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos. " + ex.__str__()})

            if action == 'firmarinformepppinternadorotativo':
                evidenciaactividad = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id_objeto'])))

                try:
                    from django.core.files import File as DjangoFile

                    hoy, datas = datetime.now().date(), None
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas: raise NameError("Debe seleccionar ubicación de la firma")

                    responsables = request.POST.getlist('responsables[]')
                    certificado = request.FILES["firma"]
                    passfirma = request.POST['palabraclave']

                    if not passfirma: raise NameError(u"Ingrese la contraseña.")

                    _name = evidenciaactividad.archivo.name.__str__().split('/')[-1]

                    generar_archivo_firmado = io.BytesIO()
                    x = txtFirmas[-1]

                    posx, posy, numpaginafirma = x["x"] + 50, x["y"] + 40, x["numPage"]
                    documento_a_firmar = evidenciaactividad.archivo
                    bytes_certificado = certificado.read()
                    extension_certificado = os.path.splitext(certificado.name)[1][1:]

                    try:
                        datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado, password_certificado=passfirma, page=numpaginafirma, reason=f"Legalizar evidencia de practicas pre profesionales", lx=posx, ly=posy).sign_and_get_content_bytes()
                    except Exception as ex:
                        try:
                            datau, datas = firmar(request, passfirma, certificado, documento_a_firmar, numpaginafirma, posx, posy, x["width"], x["height"])
                        except Exception as ex:
                            raise NameError(f'Documento con inconsistencia en la firma. {ex.__str__()}.')

                    if not datau: raise NameError(f'Documento con inconsistencia en la firma.')

                    _old_name = os.path.join(SITE_STORAGE, 'media', evidenciaactividad.archivo.name.__str__())
                    generar_archivo_firmado.write(datau)
                    datas and generar_archivo_firmado.write(datas)
                    generar_archivo_firmado.seek(0)
                    file_obj = DjangoFile(generar_archivo_firmado, name=_name)
                    evidenciaactividad.archivo = file_obj
                    evidenciaactividad.save(request)

                    log(u'Firmo Documento: {}'.format(_name), request, "add")
                    evidenciaaudi = EvidenciaActividadAudi(evidencia=evidenciaactividad, archivo=evidenciaactividad.archivo)
                    evidenciaaudi.save(request)
                    log(u'Guardo archivo firmado: {}'.format(evidenciaactividad), request, "add")

                    try:
                        if os.path.exists(_old_name):
                            os.remove(_old_name)
                    except Exception as ex:
                        pass

                    return JsonResponse({"result": 'ok', 'r': f'/pro_laboratoriocronograma?action=verevidencia&id={encrypt(evidenciaactividad.criterio.pk)}'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    evidenciaactividad.delete()
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

            elif action == 'editevidencia':
                try:
                    evidenciaactividaddetalledistributivo = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id'])), criterio__distributivo__profesor=profesor, status=True)
                    estadoinicio = evidenciaactividaddetalledistributivo.estadoaprobacion
                    f = EvidenciaActividadDetalleDistributivoForm(request.POST)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 20971520:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.pdf' or ext == '.PDF':
                                    newfile._name = generar_nombre("evidencia_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extensión. pdf."})
                    if f.is_valid():
                        if f.cleaned_data['desde'] > f.cleaned_data['hasta']:
                            return JsonResponse({"result": "bad", "mensaje": u"Ingrese bien las Fechas."})
                        if EvidenciaActividadDetalleDistributivo.objects.filter(criterio=evidenciaactividaddetalledistributivo.criterio, hasta__month=f.cleaned_data['hasta'].month, hasta__year=f.cleaned_data['hasta'].year).exclude(pk=int(encrypt(request.POST['id']))).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Esta actividad solo permite cargar una evidencia por mes, que corresponde al informe mensual de la actividad, los archivos adicionales deben subirse como anexo del informe del mes correspondiente."})
                        evidenciaactividaddetalledistributivo.desde = f.cleaned_data['desde']
                        evidenciaactividaddetalledistributivo.hasta = f.cleaned_data['hasta']
                        evidenciaactividaddetalledistributivo.actividad = f.cleaned_data['actividad']

                        if newfile:
                            evidenciaactividaddetalledistributivo.archivo = newfile
                            evidenciaactividaddetalledistributivo.archivofirmado = None if estadoinicio in (1, 3) else newfile
                            evidenciaaudi = EvidenciaActividadAudi(evidencia=evidenciaactividaddetalledistributivo, archivo=evidenciaactividaddetalledistributivo.archivo)
                            evidenciaaudi.save(request)

                        if estadoinicio == 3:
                            if newfile:
                                personarevisor = None
                                if evidenciaactividaddetalledistributivo.criterio.criteriodocenciaperiodo:
                                    if UserCriterioRevisor.objects.filter(criteriodocenciaperiodo=evidenciaactividaddetalledistributivo.criterio.criteriodocenciaperiodo, tiporevisor=1, status=True).exists():
                                        personarevisor = UserCriterioRevisor.objects.filter(criteriodocenciaperiodo=evidenciaactividaddetalledistributivo.criterio.criteriodocenciaperiodo, tiporevisor=1, status=True)[0].persona
                                if evidenciaactividaddetalledistributivo.criterio.criterioinvestigacionperiodo:
                                    if UserCriterioRevisor.objects.filter(criterioinvestigacionperiodo=evidenciaactividaddetalledistributivo.criterio.criterioinvestigacionperiodo, tiporevisor=1, status=True).exists():
                                        personarevisor = UserCriterioRevisor.objects.filter(criterioinvestigacionperiodo=evidenciaactividaddetalledistributivo.criterio.criterioinvestigacionperiodo, tiporevisor=1, status=True)[0].persona
                                if evidenciaactividaddetalledistributivo.criterio.criteriogestionperiodo:
                                    if UserCriterioRevisor.objects.filter(criteriogestionperiodo=evidenciaactividaddetalledistributivo.criterio.criteriogestionperiodo, tiporevisor=1, status=True).exists():
                                        personarevisor = UserCriterioRevisor.objects.filter(criteriogestionperiodo=evidenciaactividaddetalledistributivo.criterio.criteriogestionperiodo, tiporevisor=1, status=True)[0].persona

                                if personarevisor and not estadoinicio == evidenciaactividaddetalledistributivo.estadoaprobacion:
                                    send_html_mail("Notificación de estado de evidencia.", "emails/updateevidenciadocente.html", {'sistema': 'SGA-EVIDENCIA', 'evidencia': evidenciaactividaddetalledistributivo, 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 't': miinstitucion()}, personarevisor.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                            evidenciaactividaddetalledistributivo.estadoaprobacion = 1
                            historial = HistorialAprobacionEvidenciaActividad(aprobacionpersona=persona, fechaaprobacion=datetime.now().date(), observacion='Edición de la evidencia', evidencia=evidenciaactividaddetalledistributivo, estadoaprobacion=1)
                            historial.save(request)

                        if doc := evidenciaactividaddetalledistributivo.criterio.criteriodocenciaperiodo:
                            if doc.criterio.pk == TUTOR_PRACTICAS_INTERNADO_ROTATIVO:
                                pk = id if (id := request.POST.get('conf', 0)) else 0
                                if conf := ConfiguracionInformePracticasPreprofesionales.objects.filter(pk=pk).first():
                                    generar_informe_practicas_preprofesionales(request=request, evidencia=evidenciaactividaddetalledistributivo, configuracion=conf)

                        evidenciaactividaddetalledistributivo.save(request)
                        if evidenciaactividaddetalledistributivo.criterio.criterioinvestigacionperiodo:
                            migrar_evidencia_integrantes_proyecto_investigacion(evidencia=evidenciaactividaddetalledistributivo, request=request)
                            migrar_evidencia_integrante_grupo_investigacion(request=request, evidencia=evidenciaactividaddetalledistributivo)

                        log(f'Modifico Evidencia Profesor Distributivo Horas: {evidenciaactividaddetalledistributivo}', request, "edit")
                        return JsonResponse({"result": "ok", 'id_evidencia': evidenciaactividaddetalledistributivo.pk})
                    else:
                        for k, v in f.errors.items():
                            raise NameError(k + ', ' + v[0])
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'addanexoevidencia':
                try:
                    form = AnexoEvidenciaActividadForm(request.POST)
                    newfile = None
                    if 'archivoanexo' in request.FILES:
                        newfile = request.FILES['archivoanexo']
                        if newfile:
                            if newfile.size > 20971520:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.pdf' or ext == '.PDF':
                                    newfile._name = generar_nombre("anexo_evidencia_", newfile._name)
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extensión. pdf."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta de subir anexo."})
                    evidencia = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id'])))
                    estadoinicio = evidencia.estadoaprobacion
                    evidencia.estadoaprobacion = 1
                    evidencia.save(request)
                    anexoevidencia = AnexoEvidenciaActividad(evidencia_id=int(encrypt(request.POST['id'])),
                                                             observacion=request.POST['observacion'],
                                                             archivo=newfile)
                    anexoevidencia.save(request)
                    if int(estadoinicio) == 3:
                        if newfile:
                            personarevisor = None
                            if evidencia.criterio.criteriodocenciaperiodo:
                                if UserCriterioRevisor.objects.filter(criteriodocenciaperiodo=evidencia.criterio.criteriodocenciaperiodo, tiporevisor=1, status=True).exists():
                                    personarevisor = UserCriterioRevisor.objects.filter(criteriodocenciaperiodo=evidencia.criterio.criteriodocenciaperiodo, tiporevisor=1, status=True)[0].persona
                            if evidencia.criterio.criterioinvestigacionperiodo:
                                if UserCriterioRevisor.objects.filter(criterioinvestigacionperiodo=evidencia.criterio.criterioinvestigacionperiodo, tiporevisor=1, status=True).exists():
                                    personarevisor = UserCriterioRevisor.objects.filter(criterioinvestigacionperiodo=evidencia.criterio.criterioinvestigacionperiodo, tiporevisor=1, status=True)[0].persona
                            if evidencia.criterio.criteriogestionperiodo:
                                if UserCriterioRevisor.objects.filter(criteriogestionperiodo=evidencia.criterio.criteriogestionperiodo, tiporevisor=1, status=True).exists():
                                    personarevisor = UserCriterioRevisor.objects.filter(criteriogestionperiodo=evidencia.criterio.criteriogestionperiodo, tiporevisor=1, status=True)[0].persona
                            if personarevisor:
                                send_html_mail("Notificación de estado de evidencia.", "emails/updateevidenciadocente.html", {'sistema': 'SGA-EVIDENCIA', 'evidencia': evidencia, 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 't': miinstitucion()}, personarevisor.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                    log(u'Adiciono anexo de evidencia: %s' % anexoevidencia, request, "add")
                    return JsonResponse({"result": "ok"}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addinforme':
                try:
                    evidenciaactividad = InformeMensualDocente.objects.get(pk=request.POST['id'])
                    if not 'archivoinforme' in request.FILES:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta de subir informe."})
                    newfile = request.FILES['archivoinforme']
                    if newfile:
                        if newfile.size > 20971520:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                        else:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext in ['.pdf', '.PDF']:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, Solo archivo con extensión. pdf."})
                            newfile._name = 'informemensual_' + str(evidenciaactividad.distributivo.id) + '_' + str(evidenciaactividad.fechafin.month) + '_2.pdf'
                    tienefirmas = False
                    if evidenciaactividad.distributivo.carrera:
                        personadirectorcarrera = CoordinadorCarrera.objects.filter(carrera=evidenciaactividad.distributivo.carrera, periodo=periodo, sede_id=1, tipo=3).first()
                        personadirectorcoordinacion = evidenciaactividad.distributivo.coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, status=True).first()
                        tienefirmas = True if personadirectorcarrera and personadirectorcoordinacion else False
                    if not tienefirmas:
                        raise NameError("Estimado/a Docente, no tiene configurada coordinaciones para generar informes, por favor diríjase a su director de carrera.")
                    folder_save = os.path.join('informemensualdocente', '').replace('\\', '/')
                    folder = os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', '')
                    try:
                        os.remove(f'{folder}{newfile._name}')
                    except Exception as ex:
                        pass
                    evidenciaactividad.archivo = f'{folder_save}{newfile._name}'
                    evidenciaactividad.estado = 2
                    evidenciaactividad.save(request)
                    if not HistorialInforme.objects.values('id').filter(informe=evidenciaactividad, estado=2).exists():
                        historial = HistorialInforme(informe=evidenciaactividad,
                                                     archivo=newfile,
                                                     estado=2,
                                                     fechafirma=datetime.now().date(),
                                                     firmado=True,
                                                     personafirmas=persona)
                        historial.save(request)
                    if not HistorialInforme.objects.values('id').filter(informe=evidenciaactividad, estado=3).exists():
                        historial = HistorialInforme(informe=evidenciaactividad,
                                                     personafirmas=personadirectorcarrera.persona,
                                                     estado=3)
                        historial.save(request)
                    if not HistorialInforme.objects.values('id').filter(informe=evidenciaactividad, estado=4).exists():
                        historial = HistorialInforme(informe=evidenciaactividad,
                                                     personafirmas=personadirectorcoordinacion.persona,
                                                     estado=4)
                        historial.save(request)

                    rutapdf = folder + 'informemensual_' + str(evidenciaactividad.distributivo.id) + '_' + str(evidenciaactividad.fechafin.month) + '.pdf'
                    if os.path.isfile(rutapdf):
                        os.remove(rutapdf)
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. {}".format(ex)})

            if action == 'eliminaranexo':
                try:
                    anexoevidencia = AnexoEvidenciaActividad.objects.get(pk=request.POST['id'])
                    anexoevidencia.delete()
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'delpersonabitacora':
                try:
                    perbitacora = PersonaBitacora.objects.get(pk=request.POST['id'])
                    perbitacora.delete()
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'deleteevidencia':
                try:
                    # registro = EvidenciaActividadDetalleDistributivo.objects.get(pk=request.POST['id'])
                    registro = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id'])), criterio__distributivo__profesor=profesor, status=True)
                    # Se elimina la configuración con sus actividades
                    registroconfig = ConfiguracionInformeVinculacion.objects.filter(fecha_inicio=registro.desde, fecha_fin=registro.hasta, profesor=profesor, status=True).last()
                    if registroconfig:
                        actividades = ActividadExtraVinculacion.objects.filter(status=True, configuracion=registroconfig)
                        for act in actividades:
                            act.status = False
                            act.save(request)
                        registroconfig.status = False
                        registroconfig.save(request)

                    # Se eliminan las evidencias propagadas
                    evidenciaspropagadas = MigracionEvidenciaActividad.objects.values_list('evidencia', flat=True).filter(evidenciabase=registro)
                    EvidenciaActividadDetalleDistributivo.objects.filter(id__in=evidenciaspropagadas).update(status=False)

                    # Se elimina el parrevisor
                    if objmigracion := MigracionEvidenciaActividad.objects.filter(evidencia=registro).first():
                        if objmigracion.parrevisor:
                            objmigracion.parrevisor.delete()
                            objmigracion.delete()

                    # Se elimina la evidencia del distributivo
                    registro.delete()
                    log(u'Elimino evidencia de Actividad: %s' % registro, request, "del")
                    # return JsonResponse({"result": "ok", 'id': registro.actividaddetalledistributivo.id})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

            elif action == 'detallelaboratorio':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=int(request.POST['id']), status=True)
                    data['laboratorio'] = materia.laboratorio
                    template = get_template("pro_laboratoriocronograma/detallelaboratorio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addconfiguracion':
                try:
                    f = ConfiguracionInformePPPForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['anio'] < 2010:
                            return JsonResponse({"result": "bad", "mensaje": "Ingrese un año valido."})
                        if ConfiguracionInformePracticasPreprofesionales.objects.filter(persona=profesor, status=True, anio=f.cleaned_data['anio'], mes=f.cleaned_data['mes']).exists():
                            return JsonResponse({"result": "bad", "mensaje": "Fecha ya esta registrada."})
                        filtro = ConfiguracionInformePracticasPreprofesionales(persona=profesor, anio=f.cleaned_data.get('anio'), mes=f.cleaned_data.get('mes'), objetivo=f.cleaned_data.get('objetivo'))
                        filtro.save(request)

                        observacion = request.POST.getlist('infoObservaciones[]')
                        for i in observacion: DetalleConfiguracionInformePracticasPreprofesionales(cab=filtro, descripcion=i, tipo=1).save()

                        sugerencias = request.POST.getlist('infoSugerencias[]')
                        for i in sugerencias: DetalleConfiguracionInformePracticasPreprofesionales(cab=filtro, descripcion=i, tipo=2).save()

                        antecedente = request.POST.getlist('infoAntecedentes[]')
                        for i in antecedente: DetalleConfiguracionInformePracticasPreprofesionales(cab=filtro, descripcion=i, tipo=3).save()

                        log(u'Adicono configuracion de informe mensual ppp: %s' % filtro, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'delconfiguracion':
                try:
                    filtro = ConfiguracionInformePracticasPreprofesionales.objects.get(pk=request.POST['id'])
                    filtro.status = False
                    filtro.save(request)
                    log(u'Elimino configuracion informe mensual pp: %s' % filtro, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'editconfiguracion':
                try:
                    f = ConfiguracionInformePPPForm(request.POST)
                    if f.is_valid():
                        if f.cleaned_data['anio'] < 2010:
                            return JsonResponse({"result": "bad", "mensaje": "Ingrese un año valido."})
                        filtro = ConfiguracionInformePracticasPreprofesionales.objects.get(pk=request.POST['id'])
                        filtro.objetivo = f.cleaned_data.get('objetivo')
                        filtro.anio = f.cleaned_data.get('anio')
                        filtro.mes = f.cleaned_data.get('mes')
                        filtro.save(request)

                        DetalleConfiguracionInformePracticasPreprofesionales.objects.filter(cab=filtro).delete()

                        observacion = request.POST.getlist('infoObservaciones[]')
                        for i in observacion: DetalleConfiguracionInformePracticasPreprofesionales(cab=filtro, descripcion=i, tipo=1).save()

                        sugerencias = request.POST.getlist('infoSugerencias[]')
                        for i in sugerencias: DetalleConfiguracionInformePracticasPreprofesionales(cab=filtro, descripcion=i, tipo=2).save()

                        antecedente = request.POST.getlist('infoAntecedentes[]')
                        for i in antecedente: DetalleConfiguracionInformePracticasPreprofesionales(cab=filtro, descripcion=i, tipo=3).save()

                        log(u'Edito configuracion de informe mensual ppp: %s' % filtro, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'aadtutoriaclase':
                try:
                    # materia = Materia.objects.get(pk=request.POST['idmate'])
                    materia = Materia.objects.filter(pk=int(encrypt(request.POST['id'])), status=True, profesormateria__profesor=profesor, profesormateria__activo=True)[0]
                    f = AvTutoriasForm(request.POST)
                    if f.is_valid():
                        avtutorias = AvTutorias(materia=materia,
                                                fecha=datetime.now().date(),
                                                observacion=f.cleaned_data['observacion'])
                        avtutorias.save(request)
                        datos = json.loads(request.POST['lista_items1'])
                        if datos:
                            for elemento in datos:
                                if elemento['obse'].strip() != "":
                                    avtutoriasalumnos = AvTutoriasAlumnos(avtutorias=avtutorias,
                                                                          materiaasignada_id=elemento['maa'],
                                                                          observacion=elemento['obse'])
                                    avtutoriasalumnos.save(request)
                        log(u'Adicono Tutoria Académica: %s' % avtutorias, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'edittutoriaclase':
                try:
                    avtutorias = AvTutorias.objects.get(pk=int(encrypt(request.POST['id'])), status=True, materia__profesormateria__profesor=profesor, materia__profesormateria__activo=True)
                    f = AvTutoriasForm(request.POST)
                    if f.is_valid():
                        avtutorias.observacion = observacion = f.cleaned_data['observacion']
                        avtutorias.save(request)
                        avtutorias.avtutoriasalumnos_set.all().delete()
                        datos = json.loads(request.POST['lista_items1'])
                        if datos:
                            for elemento in datos:
                                if elemento['obse'].strip() != "":
                                    avtutoriasalumnos = AvTutoriasAlumnos(avtutorias=avtutorias,
                                                                          materiaasignada_id=elemento['maa'],
                                                                          observacion=elemento['obse'])
                                    avtutoriasalumnos.save(request)
                        log(u'Edito Tutoria Académica: %s' % avtutorias, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'deletutoriaclase':
                try:
                    # avtutorias = AvTutorias.objects.get(pk=request.POST['id'])
                    avtutorias = AvTutorias.objects.get(pk=int(encrypt(request.POST['id'])), status=True, materia__profesormateria__profesor=profesor, materia__profesormateria__activo=True)
                    avtutorias.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'calificar':
                try:
                    idactividad = request.POST['idactividad']
                    asistencias = request.POST['asistencias']
                    notas = request.POST['notas']
                    estado = request.POST['estado']
                    asistencia = asistencias.split(',')
                    nota = notas.split(',')
                    estados = estado.split(',')
                    inscritos = PaeInscripcionActividades.objects.filter(actividades=idactividad, status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    i = 0
                    for inscrito in inscritos:
                        id = inscrito.id
                        resultadovalores = PaeInscripcionActividades.objects.filter(actividades=idactividad, matricula=inscrito.matricula, status=True)[0]
                        resultadovalores.asistencia = asistencia[i]
                        i = i + 1
                        resultadovalores.save(request)
                    i = 0
                    for inscrito1 in inscritos:
                        resultadovalores = PaeInscripcionActividades.objects.filter(actividades=idactividad, matricula=inscrito1.matricula, status=True)[0]
                        resultadovalores.nota = nota[i]
                        i = i + 1
                        resultadovalores.save(request)
                    i = 0
                    for inscrito2 in inscritos:
                        resultadovalores = PaeInscripcionActividades.objects.filter(actividades=idactividad, matricula=inscrito2.matricula, status=True)[0]
                        resultadovalores.aprobacion = estados[i]
                        i = i + 1
                        resultadovalores.save(request)

                    return JsonResponse({"result": "ok", "mensaje": "DATOS GUARDADOS CORRECTAMENTE."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'reporteindividual':
                try:
                    idmat = int(encrypt(request.POST['idmat']))
                    tutorias = AvPreguntaRespuesta.objects.filter(status=True, avpreguntadocente__status=True,
                                                                  avpreguntadocente__materiaasignada__matricula__inscripcion__persona__status=True,
                                                                  avpreguntadocente__materiaasignada__materia__status=True,
                                                                  avpreguntadocente__materiaasignada__materia__id=idmat)
                    materia = Materia.objects.get(pk=idmat)
                    carrera = materia.asignaturamalla.malla.carrera.nombre_completo()
                    asignatura = materia.asignatura.nombre
                    # docente= materia.profesormateria_set.get(status=True, principal=True, activo=True)
                    # docente=docente.profesor.persona.nombre_completo()
                    docente = profesor.persona.nombre_completo()
                    periodo = materia.nivel.periodo
                    paralelo = materia.paralelo
                    nivel = materia.asignaturamalla.nivelmalla
                    carrera1 = materia.asignaturamalla.malla.carrera
                    facultad = carrera1.coordinaciones()
                    for x in facultad:
                        facultad = x.nombre
                    return conviert_html_to_pdf('pro_laboratoriocronograma/reporteindividual_pdf.html',
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

            elif action == 'reporteimasivo':
                try:
                    idmat = int(encrypt(request.POST['idmat']))
                    tutorias = AvTutoriasAlumnos.objects.filter(status=True, avtutorias__materia=idmat)
                    materia = Materia.objects.get(pk=idmat)
                    carrera = materia.asignaturamalla.malla.carrera
                    asignatura = materia.asignatura.nombre
                    # profesormateria = materia.profesor_principal_pm()
                    # docente = profesormateria.profesor.persona.nombre_completo()
                    docente = profesor.persona.nombre_completo()
                    periodo = materia.nivel.periodo
                    paralelo = materia.paralelo
                    nivel = materia.asignaturamalla.nivelmalla
                    coordina = carrera.coordinaciones()
                    facultad = ''
                    for x in coordina:
                        facultad = x.nombre
                    return conviert_html_to_pdf('pro_laboratoriocronograma/reportemasivo_pdf.html',
                                                {'pagesize': 'A4 landscape',
                                                 'carrera': carrera.nombre_completo(),
                                                 'periodo': periodo,
                                                 'docente': docente,
                                                 'asignatura': asignatura,
                                                 'paralelo': paralelo,
                                                 'nivel': nivel,
                                                 'tutorias': tutorias,
                                                 'coordinador': coordina[0].responsable_periododos(periodo, 1) if coordina else None,
                                                 'coordinadorcarrera': carrera.coordinador(periodo, coordina[0].sede) if carrera and coordina else None,
                                                 'facultad': facultad
                                                 })
                except Exception as ex:
                    pass

            elif action == 'afinidad':
                try:
                    # profesormateria = ProfesorMateria.objects.get(pk=request.POST['idprofesor'])
                    # data['materia'] = profesormateria.materia.asignaturamalla
                    data['materia'] = Materia.objects.get(pk=request.POST['idmateria']).asignaturamalla
                    data['titulacion'] = Titulacion.objects.filter(persona=profesor.persona, status=True, titulo__nivel__id=4).exclude(titulo__grado__id=3).order_by('titulo__grado__id')
                    data['title'] = u'Detalle Título'
                    template = get_template("pro_laboratoriocronograma/afinidad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'afinidad_malla':
                try:
                    # iditem
                    if 'idp' in request.POST:
                        asignaturamallapreferencia = AsignaturaMallaPreferencia.objects.get(pk=request.POST['idp'])
                        data['materia'] = asignaturamallapreferencia.asignaturamalla
                    else:
                        # asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['iditem'])
                        # data['materia'] = asignaturamalla
                        # data['listasesion'] = Materia.objects.values_list('nivel__sesion__id', 'nivel__sesion__nombre').filter(asignaturamalla=asignaturamalla, nivel__periodo=periodo, status=True).distinct()
                        asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['iditem'])
                        data['materia'] = asignaturamalla
                        asignaturamallapreferencia = asignaturamalla.asignaturamallapreferencia_set.values_list('sesion__id').filter(profesor=profesor, periodo=periodo, status=True).distinct()
                        listasesion = Materia.objects.values_list('nivel__sesion__id').filter(asignaturamalla=asignaturamalla, nivel__periodo=periodo, status=True).distinct()
                        data['listasesion'] = Sesion.objects.filter(pk__in=listasesion, status=True).exclude(pk__in=asignaturamallapreferencia)

                    data['titulacion'] = Titulacion.objects.filter(persona=profesor.persona, status=True, titulo__nivel__id=4).exclude(titulo__grado__id=3).order_by('titulo__grado__id')
                    data['title'] = u'Detalle Título'
                    template = get_template("pro_laboratoriocronograma/afinidad.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'grupodocentes':
                try:
                    asignaturamallapreferencia = AsignaturaMallaPreferencia.objects.get(pk=request.POST['idp'])
                    data['grupodocentes'] = AsignaturaMallaPreferencia.objects.filter(periodo=asignaturamallapreferencia.periodo, asignaturamalla=asignaturamallapreferencia.asignaturamalla, status=True).exclude(profesor=asignaturamallapreferencia.profesor).order_by('profesor__persona__apellido1')
                    data['asignatura'] = asignaturamallapreferencia.asignaturamalla.asignatura
                    # data['titulacion'] = Titulacion.objects.filter(persona=profesor.persona, status=True, titulo__nivel__id=4).exclude(titulo__grado__id=3).order_by('titulo__grado__id')
                    data['title'] = u'Docentes'
                    template = get_template("pro_laboratoriocronograma/grupodocentes.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'grupodocentesposgrado':
                try:
                    asignaturamallapreferencia = AsignaturaMallaPreferenciaPosgrado.objects.get(pk=request.POST['idp'])
                    data['grupodocentes'] = AsignaturaMallaPreferenciaPosgrado.objects.values_list('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres').filter(asignaturamalla=asignaturamallapreferencia.asignaturamalla, status=True).exclude(profesor=asignaturamallapreferencia.profesor).distinct().order_by('profesor__persona__apellido1')
                    data['asignatura'] = asignaturamallapreferencia.asignaturamalla.asignatura
                    data['title'] = u'Docentes'
                    template = get_template("pro_laboratoriocronograma/grupodocentesposgrado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'grupoinvestigacion':
                try:
                    data['codigopreferencia'] = request.POST['idp']
                    data['preferenciacriterio'] = PreferenciaGruposInvestigacion.objects.values_list('grupoinvestigacion_id', flat=True).filter(preferenciaactividad_id=request.POST['idp'])
                    data['grupoinvestigacion'] = GruposInvestigacion.objects.filter(status=True).order_by('descripcion')
                    data['title'] = u'Docentes'
                    template = get_template("pro_laboratoriocronograma/grupoinvestigacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'preferenciacriteriosdocentes':
                try:
                    listaprefereciacriterio = profesor.preferenciadetalleactividadescriterio_set.values_list('criteriodocenciaperiodo_id').filter(criteriodocenciaperiodo__periodo=periodo, status=True)
                    data['criteriodocencia'] = periodo.criteriodocenciaperiodo_set.filter(periodo=periodo, actividad__isnull=False, status=True).exclude(pk__in=listaprefereciacriterio).order_by('actividad__nombre', 'criterio__nombre')
                    data['title'] = u'Docentes'
                    template = get_template("pro_laboratoriocronograma/preferenciacriteriodocentes.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'preferenciacriteriosinvestigacion':
                try:
                    listaprefereciacriterio = profesor.preferenciadetalleactividadescriterio_set.values_list('criterioinvestigacionperiodo_id').filter(criterioinvestigacionperiodo__periodo=periodo, status=True)
                    data['criterioinvestigacion'] = periodo.criterioinvestigacionperiodo_set.filter(periodo=periodo, actividad__isnull=False, status=True).exclude(pk__in=listaprefereciacriterio).order_by('actividad__nombre', 'criterio__nombre')
                    data['title'] = u'Investigación'
                    template = get_template("pro_laboratoriocronograma/preferenciacriterioinvestigacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'preferenciacriteriosgestion':
                try:
                    listaprefereciacriterio = profesor.preferenciadetalleactividadescriterio_set.values_list('criteriogestionperiodo_id').filter(criteriogestionperiodo__periodo=periodo, status=True)
                    data['criteriogestion'] = periodo.criteriogestionperiodo_set.filter(periodo=periodo, actividad__isnull=False, status=True).exclude(pk__in=listaprefereciacriterio).order_by('actividad__nombre', 'criterio__nombre')
                    data['title'] = u'Gestión'
                    template = get_template("pro_laboratoriocronograma/preferenciacriteriogestion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'addactividadpreferencia':
                try:
                    opcion = request.POST['opcion']
                    lista = request.POST['lista']
                    # elementos = lista.split(',')
                    if opcion == '1':
                        for valores in lista.split(','):
                            lis = valores.split('_')
                            criterio = PreferenciaDetalleActividadesCriterio(criteriodocenciaperiodo_id=lis[0],
                                                                             profesor=profesor,
                                                                             horas=lis[1])
                            criterio.save(request)
                    if opcion == '2':
                        for valores in lista.split(','):
                            lis = valores.split('_')
                            criterio = PreferenciaDetalleActividadesCriterio(criterioinvestigacionperiodo_id=lis[0],
                                                                             profesor=profesor,
                                                                             horas=lis[1])
                            criterio.save(request)
                    if opcion == '3':
                        for valores in lista.split(','):
                            lis = valores.split('_')
                            criterio = PreferenciaDetalleActividadesCriterio(criteriogestionperiodo_id=lis[0],
                                                                             profesor=profesor,
                                                                             horas=lis[1])
                            criterio.save(request)

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'addgrupoinvestigacion':
                try:
                    id_codigopreferencia = request.POST['id_codigopreferencia']
                    lista = request.POST['lista']
                    preferencia = PreferenciaGruposInvestigacion.objects.filter(preferenciaactividad_id=id_codigopreferencia)
                    preferencia.delete()
                    for valores in lista.split(','):
                        grupo = PreferenciaGruposInvestigacion(preferenciaactividad_id=id_codigopreferencia,
                                                               grupoinvestigacion_id=valores)
                        grupo.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'historicoasignaturas':
                try:
                    data['historicoasignaturas'] = profesor.profesormateria_set.filter(materia__status=True).order_by('materia__nivel__periodo', 'materia__asignatura', 'materia__paralelo')
                    data['title'] = u'Histórico de asignaturas asignadas'
                    template = get_template("pro_laboratoriocronograma/historicoasignaturas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            elif action == 'afinidad_publicaciones':
                try:
                    # iditem
                    asignaturamallapreferencia = AsignaturaMallaPreferencia.objects.get(pk=request.POST['idp'])
                    data['materia'] = asignaturamallapreferencia.asignaturamalla
                    data['titulacion'] = ArticuloInvestigacion.objects.select_related().filter(participantesarticulos__profesor=profesor, status=True, participantesarticulos__status=True).order_by('-fechapublicacion')
                    data['title'] = u'Detalle de Publicaciones de investifación'
                    template = get_template("pro_laboratoriocronograma/afinidadpublicaciones.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad"})

            # if action == 'registrarpractica':
            #     try:
            #         profesormateria = GPGuiaPracticaSemanal.objects.get(pk=request.POST['id'])
            #         return JsonResponse({"result": "ok", 'data': json_content})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad"})

            elif action == 'aprobarrechazartutor':
                try:
                    f = AprobarRechazarEvidenciaTutorForm(request.POST, request.FILES)
                    fechamodificacion = None
                    if f.is_valid():
                        if detalle := DetalleEvidenciasPracticasPro.objects.filter(evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'], status=True).first():
                            detalle.estadotutor = f.cleaned_data['estadotutor']
                            detalle.obstutor = f.cleaned_data['obstutor']
                            if detalle.fecha_modificacion:
                                fechamodificacion = detalle.fecha_modificacion
                            else:
                                fechamodificacion = datetime.now()
                            detalle.save(request)
                            cursor = connection.cursor()
                            if fechamodificacion:
                                sqlperiodo = "UPDATE sga_detalleevidenciaspracticaspro SET fecha_modificacion = '" + str(fechamodificacion) + "' WHERE sga_detalleevidenciaspracticaspro.id=" + str(detalle.id) + ""
                            else:
                                sqlperiodo = "UPDATE sga_detalleevidenciaspracticaspro SET fecha_modificacion = null WHERE sga_detalleevidenciaspracticaspro.id=" + str(detalle.id) + ""
                            cursor.execute(sqlperiodo)
                            log(u'Adiciono Fecha limite y fin apara subir evidencia: %s %s %s' % (detalle.id, detalle.fechainicio, detalle.fechafin), request, "add")
                        else:
                            detalle = DetalleEvidenciasPracticasPro(evidencia_id=request.POST['idevidencia'],
                                                                    inscripcionpracticas_id=request.POST['id'],
                                                                    estadotutor=f.cleaned_data['estadotutor'],
                                                                    obstutor=f.cleaned_data['obstutor'],
                                                                    estadorevision=0)
                            detalle.save(request)
                            cursor = connection.cursor()
                            sqlperiodo = "UPDATE sga_detalleevidenciaspracticaspro SET fecha_modificacion = null, fecha_creacion = null WHERE sga_detalleevidenciaspracticaspro.id=" + str(detalle.id) + ""
                            cursor.execute(sqlperiodo)
                            log(u'Aprobo Rechazo tutor evidencia practica : %s %s %s' % (detalle.id, detalle.estadotutor, detalle.obstutor), request, "add")

                        # Cambiar estado de revisión como si fueran supervisor
                        detalle.estadorevision = detalle.estadotutor
                        detalle.fechaaprueba = datetime.now()
                        detalle.personaaprueba = persona
                        if detalle.estadorevision == 3:
                            ppi = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['id'])
                            ppi.autorizarevidencia = True
                            ppi.fechaautorizarevidencia = datetime.now()
                            ppi.save(request)

                        detalle.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.%s " % ex})

            elif action == 'editzoom':
                try:
                    id_enlacezoom = request.POST['id_enlacezoom']
                    profe = Profesor.objects.get(pk=profesor.id)
                    profe.urlzoom = id_enlacezoom
                    profe.save()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.%s " % ex})

            elif action == 'ponerfechalimite':
                try:
                    f = PonerFechaLimiteEvidenciaForm(request.POST)
                    if f.is_valid():
                        practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                        practica.asignar_fechas_evidencia(request, request.POST['idevidencia'], convertir_fecha_invertida(request.POST['fechainicio']), convertir_fecha_invertida(request.POST['fechafin']))
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.%s " % ex})

            elif action == 'informedocenteposgrado':
                try:
                    from pdip.models import ContratoDip
                    idmate = int(encrypt(request.POST['idmate']))
                    data_inf = profesor.informe_actividades_mensual_docente_posgrado(periodo, idmate, 'FACULTAD')
                    data_inf['contrato'] = ContratoDip.objects.filter(status=True, persona=profesor.persona).order_by('-id').first()
                    profesorMateria = data_inf['asignaturas']
                    if profesorMateria:
                        proanali_id = profesorMateria.values_list('materia__asignaturamalla_id', flat=True)
                        programaanalistico = ProgramaAnaliticoAsignatura.objects.filter(status=True, asignaturamalla_id__in=proanali_id).order_by('-id').first()
                        data_inf['programa_analitico'] = programaanalistico
                    data_inf['periodoposgrado'] = True
                    data_inf['esdirectorescuela'] = variable_valor('FIRMA_DIRECTOR')
                    return download_html_to_pdf('adm_criteriosactividadesdocente/informe_actividad_docenteipec_pdf.html', {'pagesize': 'A4', 'data': data_inf})
                except Exception as ex:
                    return HttpResponseRedirect(f"/pro_laboratoriocronograma?info=[{sys.exc_info()[-1].tb_lineno}] Problemas al generar el informe. {ex.__str__()}")

            elif action == 'informetutorcoordinadorposgrado':
                try:
                    from sagest.models import BitacoraActividadDiaria
                    from pdip.models import SolicitudPago, ContratoDip, HistorialObseracionSolicitudPago
                    gender = 'a' if persona.es_mujer() else 'o'
                    mensaje = f"Estimad{gender} %s{gender}, usted no tiene registro de sus actividades en el periodo seleccionado."
                    filtro = Q(persona=persona, status=True)
                    idmate, mes = int(request.POST.get('idmate', 0)), int(request.POST.get('mes', 0))
                    finicio, ffin = request.POST['fi'], request.POST['ff']
                    hoy = datetime.now().date()
                    if mes and not finicio and not ffin:
                        finicio = datetime(hoy.year, mes, 1)
                        lastmonthday = calendar.monthrange(finicio.year, finicio.month)[1]
                        ffin = datetime(hoy.year, mes, lastmonthday)
                        fechainicio = u"%s 00:00" % finicio.date()
                        fechafin = u"%s 23:59" % ffin.date()
                    else:
                        fechainicio = u"%s 00:00" % convertir_fecha_invertida(finicio)
                        fechafin = u"%s 23:59" % convertir_fecha_invertida(ffin)

                    if fechainicio:
                        filtro = filtro & Q(fecha__gte=fechainicio)

                    if fechafin:
                        filtro = filtro & Q(fecha__lte=fechafin)

                    if int(request.POST['tipopersona']) == 1:
                        if not BitacoraActividadDiaria.objects.values('id').filter(filtro).exists():
                            return HttpResponseRedirect(f"/pro_laboratoriocronograma?info={mensaje % 'tutor'}")
                        return download_html_to_pdf('adm_criteriosactividadesdocente/informe_actividad_diaria_tutor_posgrado.html', {'pagesize': 'A4', 'data': profesor.informe_actividades_mensual_tutor_posgrado(periodo, fechainicio, fechafin, Materia.objects.get(pk=idmate) if idmate else None)})
                    else:
                        if not BitacoraActividadDiaria.objects.values('id').filter(filtro).exists():
                            return HttpResponseRedirect(f"/pro_laboratoriocronograma?info={mensaje % 'coordinador'}")
                        fil_contrato = Q(persona=persona, fechainicio__lte=finicio, fechainicio__lt=ffin, fechafin__gt=finicio, fechafin__gte=ffin, status=True)
                        contrato = ContratoDip.objects.filter(fil_contrato).exclude(estado=5).order_by('-fecha_creacion')
                        if not BitacoraActividadDiaria.objects.values('id').filter(filtro).exists():
                            return HttpResponseRedirect(f"/pro_laboratoriocronograma?info={mensaje % 'coordinador'}")

                        if not contrato.exists():
                            raise NameError(
                                f"Estimad{'o' if persona.es_mujer() else 'a'} {profesor.persona}, no se encontró un contrato vigente.")
                        contrato = contrato.first()

                        sec_informe = contrato.secuencia_informe()
                        if SolicitudPago.objects.values('id').filter(status=True, fechainicio__date=finicio, fechaifin__date=ffin, contrato=contrato).exists():
                            return HttpResponseRedirect(f"/pro_laboratoriocronograma?info=Estimad{'o' if persona.es_mujer() else 'a'} {persona}, ya cuenta con una solicitud en las fechas indicadas, favor de revisar en informes generados de posgrado.")

                        if SolicitudPago.objects.values('id').filter(status=True, numero=sec_informe - 1, fechainicio__date=finicio, fechaifin__date=ffin, contrato=contrato).exists():
                            solicitud = SolicitudPago.objects.filter(status=True, numero=sec_informe - 1, fechainicio__date=finicio, fechaifin__date=ffin, contrato=contrato).order_by('-id').first()
                        else:
                            solicitud = SolicitudPago(
                                fechainicio=finicio,
                                fechaifin=ffin,
                                contrato=contrato,
                                estado=0,
                                numero=sec_informe
                            )
                            solicitud.save(request)

                        nombresinciales = ''
                        nombre = persona.nombres.split()
                        if len(nombre) > 1:
                            nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                        else:
                            nombresiniciales = '{}'.format(nombre[0][0])
                        inicialespersona = '{}{}{}'.format(nombresiniciales, persona.apellido1[0],
                                                           persona.apellido2[0])
                        name_file = f'informe_actividad_diaria_{inicialespersona.lower()}_{solicitud.numero}.pdf'

                        resp = conviert_html_to_pdf_name_bitacora('pro_laboratoriocronograma/informe_actividad_diaria_coordinador_posgrado.html', {"data": profesor.informe_actividades_mensual_coordinador_posgrado(periodo, fechainicio, fechafin)}, name_file)

                        if resp[0]:
                            resp[1].seek(0)
                            fil_content = resp[1].read()
                            resp = ContentFile(fil_content)
                        else:
                            return resp[1]

                        requisito, hist_ = requisito = solicitud.guardar_informe_solicitud_pago(request,
                                                                                                requisito_id=14,
                                                                                                observacion=f'Informe generado por {persona.__str__()}',
                                                                                                hoy=hoy,
                                                                                                persona=persona,
                                                                                                observacion_historial=f'Informe firmado por {persona.__str__()}',
                                                                                                name_file=name_file,
                                                                                                resp=resp)
                        cuerpo = f"Informe mensual de posgrado generado por {persona}"
                        obshisto = HistorialObseracionSolicitudPago(
                            solicitud=solicitud,
                            observacion=cuerpo,
                            persona=persona,
                            estado=0,
                            fecha=hoy
                        )
                        obshisto.save(request)
                        log(f'Genero el informe mensual coordinador de la solicitud: {solicitud}', request, 'change')
                        return HttpResponseRedirect(f'/pro_solicitudpago?action=requisitos_solicitudes_pagos&id={encrypt(solicitud.pk)}')
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=Problemas al generar el informe. Error: %s" % ex.__str__())

            elif action == 'informedocente':
                mensaje = "Problemas al generar el informe de actividades."
                try:
                    periodo_ids_relacionado = []
                    periodo_ids_relacionado.append(periodo.id)
                    if periodo.periodo_academia() and not periodo.versionreporte == 4:
                        if periodo.periodo_academia().periodos_relacionados:
                            periodo_ids_relacionado = periodo.periodo_academia().periodos_relacionados.split(',')
                            return conviert_html_to_pdf('pro_laboratoriocronograma/informe_fuera_periodo.html', {'pagesize': 'A4',
                                                                                                                       'data': profesor.informe_actividades_mensual_docente_varios_periodos(periodo, periodo_ids_relacionado,
                                                                                                                                                                                            request.POST['fini'],
                                                                                                                                                                                            request.POST['ffin'],
                                                                                                                                                                                            'FACULTAD')})
                    if periodo.versionreporte == 1:
                        return conviert_html_to_pdf('pro_laboratoriocronograma/informe_actividad_docente_pdf.html', {'pagesize': 'A4', 'data': profesor.informe_actividades_mensual_docente(periodo, request.POST['fini'], request.POST['ffin'], 'FACULTAD')})
                    if periodo.versionreporte == 2:
                        return conviert_html_to_pdf('pro_laboratoriocronograma/informe_actividad_docente_new_pdf.html', {'pagesize': 'A4', 'data': profesor.informe_actividades_mensual_docente_new(periodo, request.POST['fini'], request.POST['ffin'], 'FACULTAD')})
                    if periodo.versionreporte == 3:
                        return conviert_html_to_pdf('pro_laboratoriocronograma/informe_actividad_docentev3_pdf.html', {'pagesize': 'A4', 'data': profesor.informe_actividades_mensual_docente_new(periodo, request.POST['fini'], request.POST['ffin'], 'FACULTAD')})
                    if periodo.versionreporte == 4:
                        return download_html_to_pdf('pro_laboratoriocronograma/informe_actividad_docentev4_pdf.html', {'pagesize': 'A4', 'data': profesor.informe_actividades_mensual_docente_v4(periodo, request.POST['fini'], request.POST['ffin'], 'FACULTAD', request.POST['contenidopromedio'])})

                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % ex)

            elif action == 'informedocenteadm':
                mensaje = "Problemas al generar el informe de actividades admision."
                try:
                    return conviert_html_to_pdf('pro_laboratoriocronograma/informe_actividad_docente_pdfadm.html', {'pagesize': 'A4', 'data': profesor.informe_actividades_mensual_docente(periodo, request.POST['fini'], request.POST['ffin'], 'ADMISION')})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % mensaje)

            elif action == 'reporte_mensajes':
                mensaje = "Problemas al generar el reporte"
                try:
                    opcionreport = int(request.POST['opcionreport'])
                    if opcionreport == 1:
                        coord = 0
                    # 2 virtual admision
                    if opcionreport == 2 or opcionreport == 3:
                        coord = 9
                    return conviert_html_to_pdf('pro_laboratoriocronograma/reporte_mensajes.html', {'pagesize': 'A4', 'data': {'profesor': profesor, 'coord': coord}})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % mensaje)

            elif action == 'reporte_foros':
                mensaje = "Problemas al generar el reporte"
                try:
                    opcionreport = int(request.POST['opcionreport'])
                    coord = 0
                    materias = []
                    profesormateria = None
                    if opcionreport == 1:
                        profesormateria = ProfesorMateria.objects.filter(profesor=profesor,
                                                                         materia__nivel__modalidad_id=3,
                                                                         materia__nivel__periodo=periodo, activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # 2 virtual admision
                    if opcionreport == 2:
                        coord = 9
                        profesormateria = ProfesorMateria.objects.filter(profesor=profesor,
                                                                         materia__nivel__modalidad_id=3,
                                                                         materia__nivel__periodo=periodo, activo=True,
                                                                         materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
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
                    return conviert_html_to_pdf('pro_laboratoriocronograma/reporte_foros.html', {'pagesize': 'A4', 'data': {'profesor': profesor, 'coord': coord, 'materias': materias}})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % mensaje)

            elif action == 'informe_seguimiento_general':
                mensaje = "Problemas al generar el informe"
                try:
                    materias = []
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
                    lista1 = ""
                    horas = 0
                    if (opcionreport == 2 or opcionreport == 3):
                        if periodo.id == 99:
                            profesor_ids = [(79, 18), (360, 16), (615, 20), (897, 20), (1237, 20), (1264, 16), (1388, 20), (1400, 20), (1402, 20), (1727, 16), (1824, 20), (1843, 20), (2118, 20), (2119, 20), (2120, 20), (1422, 20)]
                            for index, item in enumerate(profesor_ids):
                                if item[0] == profesor.id:
                                    horas = item[1]
                                    break

                        reporte = Reporte.objects.get(nombre='informe_admision_mensual_cumplimiento_actividades')
                        paRequest = {'coordinacion_id': 9,
                                     'date_begin': convertir_fecha(finio).strftime('%d-%m-%Y'),
                                     'date_end': convertir_fecha(ffino).strftime('%d-%m-%Y'),
                                     'horas': horas,
                                     'periodo_id': periodo.id,
                                     'profesor_id': profesor.id,
                                     }
                        d = run_report_v1(reporte=reporte, tipo='pdf', paRequest=paRequest, request=request)
                        if not d['isSuccess']:
                            raise NameError(d['mensaje'])
                        else:
                            return HttpResponseRedirect(d['data']['reportfile'])

                    # 1: grado virtual
                    if opcionreport == 1:
                        profesormateriaparacoordinacion = profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # 2 virtual admision
                    if opcionreport == 2:
                        coord = 9
                        # profesormateria = ProfesorMateria.objects.filter(hora__gt=0, profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                        profesormateriaparacoordinacion = ProfesorMateria.objects.filter(profesor=profesor,
                                                                                         materia__nivel__modalidad_id=3,
                                                                                         materia__nivel__periodo=periodo,
                                                                                         activo=True,
                                                                                         materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by(
                            'desde', 'materia__asignatura__nombre')
                        profesormateria = profesormateriaparacoordinacion.filter(hora__gt=0).distinct()

                    # 3 presencial admision
                    if opcionreport == 3:
                        coord = 9
                        # profesormateria = ProfesorMateria.objects.filter(hora__gt=0, profesor=profesor, materia__nivel__periodo=periodo, activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')
                        profesormateriaparacoordinacion = ProfesorMateria.objects.filter(profesor=profesor,
                                                                                         materia__nivel__periodo=periodo,
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
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2, 3],
                                                                      materia__id__in=profesormateriaparacoordinacion.values_list(
                                                                          'materia__id', flat=True)).distinct()
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
                        marcadas = LogDia.objects.filter(persona=distributivo.profesor.persona, fecha__in=fechas_clases, status=True).order_by('fecha')
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
                            porcentaje = Decimal(
                                ((asistencias_reg * 100) / (asistencias_reg + asistencias_no_registradas))).quantize(
                                Decimal('.01'))
                        resultado.append((asistencias_reg, asistencias_no_registradas, porcentaje))

                    return conviert_html_to_pdf('pro_laboratoriocronograma/informe_seguimiento.html', {'pagesize': 'A4',
                                                                                            'data': {'distributivo': distributivo,
                                                                                                     'periodo': periodo,
                                                                                                     'fini': finio,
                                                                                                     'ffin': ffino,
                                                                                                     'finic': finic,
                                                                                                     'ffinc': ffinc, 'suma': suma,
                                                                                                     'materias': materias,
                                                                                                     'titulaciones': titulaciones,
                                                                                                     'opcionreport': opcionreport,
                                                                                                     'resultado': resultado if opcionreport == 3 else None,
                                                                                                     'coord': coord, 'coordinacion': coordinacion,
                                                                                                     'listacarreras': listacarreras,
                                                                                                     'lista': lista1}})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % mensaje)

            elif action == 'informe_seguimiento_general_new':
                mensaje = "Problemas al generar el informe"
                try:
                    materias = []
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
                    fechainiresta = str(finic - timedelta(days=4))
                    fechafinresta = str(ffinc - timedelta(days=4))
                    finicresta = fechainiresta.split('-')[2] + '-' + fechainiresta.split('-')[1] + '-' + fechainiresta.split('-')[0]
                    ffincresta = fechafinresta.split('-')[2] + '-' + fechafinresta.split('-')[1] + '-' + fechafinresta.split('-')[0]
                    opcionreport = int(request.POST['opcionreport'])
                    lista1 = ""
                    # 1: grado virtual
                    if opcionreport == 1:
                        if profesor.id == 2044 and periodo.id == 112:  # Se hizo este caso unicamente para el docente manuel armando cedillo romero en este periodo
                            profesormateriaparacoordinacion = profesormateria = ProfesorMateria.objects.filter(profesor=profesor, tipoprofesor_id=8, materia__nivel__periodo=periodo, activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                        else:
                            profesormateriaparacoordinacion = profesormateria = ProfesorMateria.objects.filter(profesor=profesor, tipoprofesor_id=8, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                    # 2 virtual admision
                    if opcionreport == 2:
                        coord = 9
                        # profesormateria = ProfesorMateria.objects.filter(hora__gt=0, profesor=profesor, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
                        profesormateriaparacoordinacion = ProfesorMateria.objects.filter(profesor=profesor,
                                                                                         materia__nivel__modalidad_id=3,
                                                                                         materia__nivel__periodo=periodo,
                                                                                         activo=True,
                                                                                         materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by(
                            'desde', 'materia__asignatura__nombre')
                        profesormateria = profesormateriaparacoordinacion.filter(hora__gt=0).distinct()
                    # 3 presencial admision
                    if opcionreport == 3:
                        coord = 9
                        # profesormateria = ProfesorMateria.objects.filter(hora__gt=0, profesor=profesor, materia__nivel__periodo=periodo, activo=True, materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')
                        profesormateriaparacoordinacion = ProfesorMateria.objects.filter(profesor=profesor,
                                                                                         materia__nivel__periodo=periodo,
                                                                                         activo=True,
                                                                                         materia__nivel__nivellibrecoordinacion__coordinacion_id=9).exclude(
                            materia__nivel__modalidad_id=3).distinct().order_by('desde', 'materia__asignatura__nombre')
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
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True,
                                                                      matricula__estado_matricula__in=[2, 3],
                                                                      materia__id__in=profesormateriaparacoordinacion.values_list(
                                                                          'materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None

                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])
                    if distributivo:
                        midistributivo = distributivo
                    # evidencias subidas *************************************************
                    evidencias = EvidenciaActividadDetalleDistributivo.objects.filter(Q(criterio__distributivo=midistributivo) & ((Q(desde__gte=finic) & Q(hasta__lte=ffinc)) | (Q(desde__lte=finic) & Q(hasta__gte=ffinc)) | (Q(desde__lte=ffinc) & Q(desde__gte=finic)) | (Q(hasta__gte=finic) & Q(hasta__lte=ffinc)))).distinct().order_by('desde')
                    evidenciasgestion = None
                    evidenciasinvestigacion = None
                    evidenciasdocencia = None
                    evidenciasdocencianombre = None
                    if evidencias:
                        if evidencias.filter(criterio__criteriogestionperiodo__isnull=False).exists():
                            evidenciasgestion = evidencias.filter(criterio__criteriogestionperiodo__isnull=False).order_by('criterio__criteriogestionperiodo__criterio__nombre')
                        if evidencias.filter(criterio__criterioinvestigacionperiodo__isnull=False).exists():
                            evidenciasinvestigacion = evidencias.filter(criterio__criterioinvestigacionperiodo__isnull=False).order_by('criterio__criterioinvestigacionperiodo__criterio__nombre')
                        if evidencias.filter(criterio__criteriodocenciaperiodo__isnull=False).exists():
                            evidenciasdocencianombre = evidencias.values_list('criterio_id', 'criterio__criteriodocenciaperiodo__criterio__nombre').filter(criterio__criteriodocenciaperiodo__isnull=False).distinct()
                            evidenciasdocencia = evidencias.filter(criterio__criteriodocenciaperiodo__isnull=False).order_by('criterio__criteriodocenciaperiodo__criterio__nombre')

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
                        marcadas = LogDia.objects.filter(persona=distributivo.profesor.persona, fecha__in=fechas_clases, status=True).order_by('fecha')
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
                            porcentaje = Decimal(
                                ((asistencias_reg * 100) / (asistencias_reg + asistencias_no_registradas))).quantize(
                                Decimal('.01'))
                        resultado.append((asistencias_reg, asistencias_no_registradas, porcentaje))
                    if periodo.versionreporte == 2:
                        return conviert_html_to_pdf('pro_laboratoriocronograma/informe_seguimiento_new.html', {'pagesize': 'A4',
                                                                                                    'data': {'distributivo': distributivo,
                                                                                                             'periodo': periodo,
                                                                                                             'fini': finio,
                                                                                                             'ffin': ffino,
                                                                                                             'finic': finic,
                                                                                                             'ffinc': ffinc, 'suma': suma,
                                                                                                             'evidencias': evidencias,
                                                                                                             'evidenciasgestion': evidenciasgestion,
                                                                                                             'evidenciasinvestigacion': evidenciasinvestigacion,
                                                                                                             'evidenciasdocencia': evidenciasdocencia,
                                                                                                             'evidenciasdocencianombre': evidenciasdocencianombre,
                                                                                                             'materias': materias,
                                                                                                             'titulaciones': titulaciones,
                                                                                                             'opcionreport': opcionreport,
                                                                                                             'resultado': resultado if opcionreport == 3 else None,
                                                                                                             'coord': coord, 'coordinacion': coordinacion,
                                                                                                             'listacarreras': listacarreras,
                                                                                                             'lista': lista1}})
                    if periodo.versionreporte == 3:
                        numero_solicitudes_devuelto = SolicitudTutorSoporteMateria.objects.filter(fecha_creacion__range=(finic, ffinc), status=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, profesor=profesor, estado=4).distinct().count()
                        numero_solicitudes_tramite = SolicitudTutorSoporteMateria.objects.filter(fecha_creacion__range=(finic, ffinc), status=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, profesor=profesor, estado=2).distinct().count()
                        numero_solicitudes_cerrado = SolicitudTutorSoporteMateria.objects.filter(fecha_creacion__range=(finic, ffinc), status=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, profesor=profesor, estado=3).distinct().count()
                        numero_solicitudes_solicitado = SolicitudTutorSoporteMateria.objects.filter(fecha_creacion__range=(finic, ffinc), status=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, profesor=profesor, estado=1).distinct().count()
                        return conviert_html_to_pdf('pro_laboratoriocronograma/informe_seguimiento_newv3.html', {'pagesize': 'A4',
                                                                                                      'data': {
                                                                                                          'distributivo': distributivo,
                                                                                                          'periodo': periodo,
                                                                                                          'fini': finio,
                                                                                                          'ffin': ffino,
                                                                                                          'finic': finic,
                                                                                                          'ffinc': ffinc,
                                                                                                          'finicresta': finicresta,
                                                                                                          'ffincresta': ffincresta,
                                                                                                          'suma': suma,
                                                                                                          'evidencias': evidencias,
                                                                                                          'evidenciasgestion': evidenciasgestion,
                                                                                                          'evidenciasinvestigacion': evidenciasinvestigacion,
                                                                                                          'evidenciasdocencia': evidenciasdocencia,
                                                                                                          'evidenciasdocencianombre': evidenciasdocencianombre,
                                                                                                          'materias': materias,
                                                                                                          'titulaciones': titulaciones,
                                                                                                          'opcionreport': opcionreport,
                                                                                                          'resultado': resultado if opcionreport == 3 else None,
                                                                                                          'coord': coord,
                                                                                                          'coordinacion': coordinacion,
                                                                                                          'listacarreras': listacarreras,
                                                                                                          'lista': lista1,
                                                                                                          'numero_solicitudes_devuelto': numero_solicitudes_devuelto,
                                                                                                          'numero_solicitudes_tramite': numero_solicitudes_tramite,
                                                                                                          'numero_solicitudes_cerrado': numero_solicitudes_cerrado,
                                                                                                          'numero_solicitudes_solicitado': numero_solicitudes_solicitado}})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s - %s" % (mensaje, ex.__str__()))

            elif action == 'informe_general_tutorposgrado':
                mensaje = "Problemas al generar el informe"
                try:
                    materias = []
                    listacarreras = []
                    coord = 7
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    profesormateriaparacoordinacion = None
                    finio = request.POST['fini']
                    ffino = request.POST['ffin']
                    finic = convertir_fecha(finio)
                    ffinc = convertir_fecha(ffino)
                    fechainiresta = str(finic - timedelta(days=4))
                    fechafinresta = str(ffinc - timedelta(days=4))
                    finicresta = fechainiresta.split('-')[2] + '-' + fechainiresta.split('-')[1] + '-' + fechainiresta.split('-')[0]
                    ffincresta = fechafinresta.split('-')[2] + '-' + fechafinresta.split('-')[1] + '-' + fechafinresta.split('-')[0]
                    opcionreport = int(request.POST['opcionreport'])
                    lista1 = ""
                    # 1: grado virtual
                    profesormateriaparacoordinacion1 = ProfesorMateria.objects.filter(profesor=profesor, tipoprofesor_id=8, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion=7, activo=True, materia__inicio__range=(finic, ffinc)).distinct().order_by('desde', 'materia__asignatura__nombre')
                    profesormateriaparacoordinacion2 = ProfesorMateria.objects.filter(profesor=profesor, tipoprofesor_id=8, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__coordinacion=7, activo=True, materia__fin__range=(finic, ffinc)).distinct().order_by('desde', 'materia__asignatura__nombre')
                    profesormateriaparacoordinacion = profesormateria = profesormateriaparacoordinacion1 | profesormateriaparacoordinacion2
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
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True, matricula__estado_matricula__in=[2, 3], materia__id__in=profesormateriaparacoordinacion.values_list('materia__id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodleposgrado:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodleposgrado) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodleposgrado)
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True).exists() else None
                    totalrecibidosacompanamiento = AvPreguntaDocente.objects.values_list('id').filter(fecha_creacion__date__range=(finic, ffinc), profersormateria__profesor=distributivo.profesor, materiaasignada__materia_id__in=profesormateriaparacoordinacion.values_list('materia_id'))
                    totalatendidosacompanamiento = AvPreguntaRespuesta.objects.filter(avpreguntadocente_id__in=totalrecibidosacompanamiento).distinct('avpreguntadocente_id').count()
                    if totalrecibidosacompanamiento.count() == 0:
                        totalporcentajeacompanamiento = 0
                    else:
                        totalporcentajeacompanamiento = round(null_to_numeric((totalatendidosacompanamiento * 100) / totalrecibidosacompanamiento.count()), 2)
                    titulaciones = distributivo.profesor.persona.mis_titulaciones()
                    titulaciones = titulaciones.filter(titulo__nivel_id__in=[3, 4])
                    if distributivo:
                        midistributivo = distributivo
                    # evidencias subidas *************************************************
                    evidencias = EvidenciaActividadDetalleDistributivo.objects.filter(Q(criterio__distributivo=midistributivo) & ((Q(desde__gte=finic) & Q(hasta__lte=ffinc)) | (Q(desde__lte=finic) & Q(hasta__gte=ffinc)) | (Q(desde__lte=ffinc) & Q(desde__gte=finic)) | (Q(hasta__gte=finic) & Q(hasta__lte=ffinc)))).distinct().order_by('desde')
                    evidenciasgestion = None
                    evidenciasinvestigacion = None
                    evidenciasdocencia = None
                    evidenciasdocencianombre = None
                    if evidencias:
                        if evidencias.filter(criterio__criteriodocenciaperiodo__isnull=False).exists():
                            evidenciasdocencianombre = evidencias.values_list('criterio_id', 'criterio__criteriodocenciaperiodo__criterio__nombre').filter(criterio__criteriodocenciaperiodo__isnull=False).distinct()
                            evidenciasdocencia = evidencias.filter(criterio__criteriodocenciaperiodo__isnull=False).order_by('criterio__criteriodocenciaperiodo__criterio__nombre')

                    numero_solicitudes_devuelto = SolicitudTutorSoporteMateria.objects.filter(fecha_creacion__range=(finic, ffinc), status=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, profesor=profesor, estado=4).distinct().count()
                    numero_solicitudes_tramite = SolicitudTutorSoporteMateria.objects.filter(fecha_creacion__range=(finic, ffinc), status=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, profesor=profesor, estado=2).distinct().count()
                    numero_solicitudes_cerrado = SolicitudTutorSoporteMateria.objects.filter(fecha_creacion__range=(finic, ffinc), status=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, profesor=profesor, estado=3).distinct().count()
                    numero_solicitudes_solicitado = SolicitudTutorSoporteMateria.objects.filter(fecha_creacion__range=(finic, ffinc), status=True, materiaasignada__matricula__estado_matricula__in=[2, 3], materiaasignada__matricula__nivel__periodo=periodo, profesor=profesor, estado=1).distinct().count()
                    return download_html_to_pdf('pro_laboratoriocronograma/informe_tutor_posgrado.html', {'pagesize': 'A4',
                                                                                               'data': {
                                                                                                   'distributivo': distributivo,
                                                                                                   'periodo': periodo,
                                                                                                   'fini': finio,
                                                                                                   'ffin': ffino,
                                                                                                   'finic': finic,
                                                                                                   'ffinc': ffinc,
                                                                                                   'finicresta': finicresta,
                                                                                                   'ffincresta': ffincresta,
                                                                                                   'suma': suma,
                                                                                                   'evidencias': evidencias,
                                                                                                   'evidenciasgestion': evidenciasgestion,
                                                                                                   'evidenciasinvestigacion': evidenciasinvestigacion,
                                                                                                   'evidenciasdocencia': evidenciasdocencia,
                                                                                                   'evidenciasdocencianombre': evidenciasdocencianombre,
                                                                                                   'materias': materias,
                                                                                                   'titulaciones': titulaciones,
                                                                                                   'opcionreport': opcionreport,
                                                                                                   'resultado': None,
                                                                                                   'coord': coord,
                                                                                                   'coordinacion': coordinacion,
                                                                                                   'listacarreras': listacarreras,
                                                                                                   'lista': lista1,
                                                                                                   'totalrecibidosacompanamiento': totalrecibidosacompanamiento.count(),
                                                                                                   'totalatendidosacompanamiento': totalatendidosacompanamiento,
                                                                                                   'totalporcentajeacompanamiento': totalporcentajeacompanamiento,
                                                                                                   'numero_solicitudes_devuelto': numero_solicitudes_devuelto,
                                                                                                   'numero_solicitudes_tramite': numero_solicitudes_tramite,
                                                                                                   'numero_solicitudes_cerrado': numero_solicitudes_cerrado,
                                                                                                   'numero_solicitudes_solicitado': numero_solicitudes_solicitado}})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s - %s" % (mensaje, ex.__str__()))

            elif action == 'informe_seguimiento_virtual':
                mensaje = "Problemas al generar el informe"
                try:
                    materia = Materia.objects.get(pk=int(encrypt(request.POST['idmat'])))
                    materiasasignadas = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2, 3]).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    ponderacion_plataforma = PonderacionSeguimiento.objects.get(periodo=periodo, tiposeguimiento=1).porcentaje
                    ponderacion_recurso = PonderacionSeguimiento.objects.get(periodo=periodo, tiposeguimiento=2).porcentaje
                    ponderacion_actividad = PonderacionSeguimiento.objects.get(periodo=periodo, tiposeguimiento=3).porcentaje

                    hoy = datetime.now().date()
                    finio = request.POST['fini']
                    ffino = request.POST['ffin']
                    finic = convertir_fecha(finio)
                    ffinc = convertir_fecha(ffino)
                    lista = []
                    listaalumnos = []

                    if materia.tareas_asignatura_moodle(finic, ffinc):
                        listaidtareas = []
                        for listatarea in materia.tareas_asignatura_moodle(finic, ffinc):
                            listaidtareas.append(listatarea[0])
                        lista.append(listaidtareas)
                    else:
                        lista.append(0)
                    if materia.foros_asignatura_moodledos(finic, ffinc):
                        listaidforum = []
                        for listaforo in materia.foros_asignatura_moodledos(finic, ffinc):
                            listaidforum.append(listaforo[0])
                        lista.append(listaidforum)
                    else:
                        lista.append(0)
                    if materia.test_asignatura_moodle(finic, ffinc):
                        listaidtest = []
                        for listatest in materia.test_asignatura_moodle(finic, ffinc):
                            listaidtest.append(listatest)
                        lista.append(listaidtest)
                    else:
                        lista.append(0)
                    diapositivas = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, iddiapositivamoodle__gt=0)
                    if diapositivas:
                        listaidpresentacion = []
                        for listadias in diapositivas:
                            listaidpresentacion.append(listadias.iddiapositivamoodle)
                        lista.append(listaidpresentacion)
                    else:
                        lista.append(0)
                    fechacalcula = datetime.strptime('2020-07-24', '%Y-%m-%d').date()
                    if finic > fechacalcula:
                        guiasestudiantes = GuiaEstudianteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idguiaestudiantemoodle__gt=0)
                        if guiasestudiantes:
                            listaidguiaestudiante = []
                            for listaguiasestu in guiasestudiantes:
                                listaidguiaestudiante.append(listaguiasestu.idguiaestudiantemoodle)
                            lista.append(listaidguiaestudiante)
                        else:
                            lista.append(0)
                        guiasdocentes = GuiaDocenteSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idguiadocentemoodle__gt=0)
                        if guiasdocentes:
                            listaidguiadocente = []
                            for listaguiasdoce in guiasdocentes:
                                listaidguiadocente.append(listaguiasdoce.idguiadocentemoodle)
                            lista.append(listaidguiadocente)
                        else:
                            lista.append(0)
                        compendios = CompendioSilaboSemanal.objects.filter(silabosemanal__silabo__materia=materia, silabosemanal__fechafinciosemana__range=(finic, ffinc), silabosemanal__silabo__status=True, idmcompendiomoodle__gt=0)
                        if compendios:
                            listaidcompendio = []
                            for listacompendios in compendios:
                                listaidcompendio.append(listacompendios.idmcompendiomoodle)
                            lista.append(listaidcompendio)
                        else:
                            lista.append(0)
                    else:
                        lista.append(0)
                        lista.append(0)
                        lista.append(0)
                    totalverde = 0
                    totalamarillo = 0
                    totalrojo = 0
                    for alumnos in materiasasignadas:
                        nombres = alumnos.matricula.inscripcion.persona.apellido1 + ' ' + alumnos.matricula.inscripcion.persona.apellido2 + ' ' + alumnos.matricula.inscripcion.persona.nombres
                        esppl = 'NO'
                        esdiscapacidad = 'NO'
                        if alumnos.matricula.inscripcion.persona.ppl:
                            esppl = 'SI'
                        if alumnos.matricula.inscripcion.persona.mi_perfil().tienediscapacidad:
                            esdiscapacidad = 'SI'
                        totalaccesologuin = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_loguinusermoodle(finic, ffinc)))
                        totalaccesorecurso = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_accesorecursomoodle(finic, ffinc, materia.idcursomoodle, lista)))
                        totalcumplimiento = float("{:.2f}".format(alumnos.matricula.inscripcion.persona.total_cumplimientomoodle(finic, ffinc, materia.idcursomoodle, lista)))
                        totalporcentaje = float("{:.2f}".format(((((totalaccesologuin * ponderacion_plataforma) / 100) + ((totalaccesorecurso * ponderacion_recurso) / 100) + ((totalcumplimiento * ponderacion_actividad) / 100)))))

                        if totalporcentaje >= 70:
                            colorfondo = '5bb75b'
                            totalverde += 1
                        if totalporcentaje <= 30:
                            colorfondo = 'b94a48'
                            totalrojo += 1
                        if totalporcentaje > 31 and totalporcentaje < 70:
                            colorfondo = 'faa732'
                            totalamarillo += 1
                        listaalumnos.append([alumnos.matricula.inscripcion.persona.cedula,
                                             nombres,
                                             esppl,
                                             esdiscapacidad,
                                             totalaccesologuin,
                                             totalaccesorecurso,
                                             totalcumplimiento,
                                             totalporcentaje,
                                             alumnos.matricula.inscripcion.persona.email,
                                             alumnos.matricula.inscripcion.persona.telefono,
                                             alumnos.matricula.inscripcion.persona.canton,
                                             colorfondo])

                    porcentajeverde = float("{:.2f}".format((totalverde / materiasasignadas.count()) * 100))
                    porcentajerojo = float("{:.2f}".format((totalrojo / materiasasignadas.count()) * 100))
                    porcentajeamarillo = float("{:.2f}".format((totalamarillo / materiasasignadas.count()) * 100))
                    return conviert_html_to_pdf('pro_laboratoriocronograma/informe_seguimiento_virtual.html',
                                                {'pagesize': 'A4',
                                                 'data': {'materia': materia,
                                                          'periodo': periodo,
                                                          'materiasasignadas': materiasasignadas,
                                                          'fechaactual': hoy,
                                                          'fini': finic,
                                                          'ffin': ffinc,
                                                          'lista': lista,
                                                          'listaalumnos': listaalumnos,
                                                          'totalverde': totalverde,
                                                          'totalrojo': totalrojo,
                                                          'totalamarillo': totalamarillo,
                                                          'porcentajeverde': porcentajeverde,
                                                          'porcentajerojo': porcentajerojo,
                                                          'porcentajeamarillo': porcentajeamarillo
                                                          }
                                                 }
                                                )
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % mensaje)

            elif action == 'retiro':
                try:
                    f = RetiroPracticasForm(request.POST, request.FILES)
                    # 2.5MB - 2621440
                    # 5MB - 5242880
                    # 6MB - 6291456
                    # 10MB - 10485760
                    # 20MB - 20971520
                    # 50MB - 5242880
                    # 100MB 104857600
                    # 250MB - 214958080
                    # 500MB - 429916160
                    d = request.FILES['archivoretiro']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    if f.is_valid():
                        newfile = None
                        if 'archivoretiro' in request.FILES:
                            newfile = request.FILES['archivoretiro']
                            newfile._name = generar_nombre("archivoretiro_", newfile._name)

                        practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(
                            id=request.POST['id'])
                        practicaspreprofesionalesinscripcion.archivoretiro = newfile
                        practicaspreprofesionalesinscripcion.estadosolicitud = 5
                        practicaspreprofesionalesinscripcion.save(request)
                        log(u'Retiro de practicas profesionales: %s [%s]' % (practicaspreprofesionalesinscripcion, practicaspreprofesionalesinscripcion.id), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al Retirar los datos."})

            elif action == 'envioclave':
                try:
                    clave = profesor.generar_clave_notas()
                    datos = profesor.datos_habilitacion()
                    datos.habilitado = False
                    datos.clavegenerada = clave
                    datos.fecha = datetime.now().date()
                    datos.save(request)
                    cuenta = 0
                    if SERVER_RESPONSE in ['207', '209', '211']:
                        cuenta = 6
                    elif SERVER_RESPONSE in ['212', '213']:
                        cuenta = 14
                    elif SERVER_RESPONSE in ['214', '215']:
                        cuenta = 15
                    send_html_mail("Nueva clave para ingreso de calificaciones", "emails/nuevaclavecalificaciones.html", {'sistema': request.session['nombresistema'], 'profesor': profesor, 'clave': datos.clavegenerada, 'fecha': datos.fecha, 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[cuenta][1])
                    # send_html_mail("Nueva clave para ingreso de calificaciones", "emails/nuevaclavecalificaciones.html", {'sistema': request.session['nombresistema'], 'profesor': profesor, 'clave': datos.clavegenerada, 'fecha': datos.fecha, 't': miinstitucion()}, ['bbarcom@unemi.edu.ec'], [], cuenta=CUENTAS_CORREOS[cuenta][1])
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'verificacionclave':
                try:
                    clave = request.POST['clave'].strip()
                    datos = profesor.datos_habilitacion()
                    if datos.clavegenerada == clave and datos.fecha == datetime.now().date():
                        datos.habilitado = True
                        datos.save(request)
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Clave incorrecta'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'controlacademico_pdf':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=int(request.POST['id']), nivel__periodo=periodo)
                    data['profesor'] = materia.profesor_principal().persona.nombre_completo_inverso()
                    # lecciones = materia.mis_lecciones(materia.profesor_principal())
                    data['lecciones'] = lecciones = Leccion.objects.filter(clase__materia=materia)
                    data['periodo'] = periodo
                    return conviert_html_to_pdf(
                        'pro_laboratoriocronograma/controlacademico_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'informeestudiantepractica':
                try:
                    materia = Materia.objects.get(pk=int(encrypt(request.POST['id'])))
                    tipoprofesor = TipoProfesor.objects.get(pk=TIPO_DOCENTE_PRACTICA)
                    data['materia'] = materia
                    data['periodo'] = periodo
                    data['profesorpractica'] = tipoprofesor
                    profesormateria = materia.profesores_materia_segun_tipoprofesor_profe(profesor, TIPO_DOCENTE_PRACTICA)
                    data['profesormateria'] = profesormateria[0] if profesormateria else None
                    return conviert_html_to_pdf('pro_laboratoriocronograma/informeestudiantespracticas.html', {'pagesize': 'A4 landscape', 'datos': data})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % 'Error al generar informe de estudiantes de prácticas')

            elif action == 'informeseguimientopractica':
                try:
                    data['practica'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt(request.POST['idp'])))
                    return conviert_html_to_pdf('pro_laboratoriocronograma/informe_seguimiento_practica_pdf.html', {'pagesize': 'A4 landscape', 'datos': data})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % 'Error al generar informe de estudiantes de prácticas')

            elif action == 'addapruebaevidencias':
                try:
                    detallepracticas = DetalleEvidenciasPracticasPro.objects.get(evidencia_id=request.POST['idevidencia'], inscripcionpracticas_id=request.POST['id'])
                    f = ArpobarEvidenciaPracticasForm(request.POST)
                    if f.is_valid():
                        detallepracticas.estadorevision = f.cleaned_data['tipo']
                        detallepracticas.obseaprueba = f.cleaned_data['observacion']
                        detallepracticas.fechaaprueba = datetime.now()
                        detallepracticas.personaaprueba = persona
                        detallepracticas.aprobosupervisor = True
                        detallepracticas.save(request)
                        if f.cleaned_data['tipo'] == '3':
                            practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=request.POST['idpracins'])
                            practicaspreprofesionalesinscripcion.autorizarevidencia = True
                            practicaspreprofesionalesinscripcion.fechaautorizarevidencia = datetime.now()
                            practicaspreprofesionalesinscripcion.save(request)
                        log(u'Adiciono apruebas de evidencia supervisor en practicas profesionales inscripcion: %s [%s]' % (detallepracticas, detallepracticas.id), request, "edit")
                        asunto = u"NOTIFICACION DE CALIFICACIÓN"
                        send_html_mail(asunto, "emails/aprobacion_pracpreprofesionales.html", {'sistema': request.session['nombresistema'], 'evidencia': detallepracticas.evidencia.nombre, 'alumno': detallepracticas.inscripcionpracticas.inscripcion.persona}, detallepracticas.inscripcionpracticas.inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'configurarfechamasiva':
                try:
                    form = ConfigurarFechaMasivaPracticaForm(request.POST)
                    if form.is_valid():
                        listapracticas = json.loads(request.POST['lista_items1'])
                        if not listapracticas:
                            return JsonResponse({"result": "bad", "mensaje": u"Seleccione al menos una prácticas pre profesionales."})
                        practicasseleccionadas = PracticasPreprofesionalesInscripcion.objects.filter(id__in=[int(encrypt(idpractica['idp'])) for idpractica in listapracticas], periodoppp=form.cleaned_data['periodoevidencia'], supervisor=profesor, culminada=False)
                        for practica in practicasseleccionadas:
                            if not profesor.coordinacion.id == 1 and form.cleaned_data['aplicarpractica']:
                                practica.fechadesde = form.cleaned_data['fechainicio']
                                practica.fechahasta = form.cleaned_data['fechafin']
                                practica.save(request)
                            if form.cleaned_data['aplicarevidencia']:
                                for evidencia in practica.periodoppp.evidencias_practica().filter(Q(pk__in=form.cleaned_data['evidencias']), Q(status=True)).filter(Q(detalleevidenciaspracticaspro__estadorevision=1) & Q(detalleevidenciaspracticaspro__estadotutor=0)):
                                    practica.asignar_fechas_evidencia(request, evidencia.id, form.cleaned_data['fechainicio'], form.cleaned_data['fechafin'])
                        log(u'Se actualizo o genero fechas masiva: Aplica practica(%s) - Aplicar evidencia(%s) periodo evidencias(%s) evidencias(%s) fecha inicio(%s) fecha fin(%s)' % (form.cleaned_data['aplicarpractica'], form.cleaned_data['aplicarevidencia'], form.cleaned_data['periodoevidencia'], form.cleaned_data['evidencias'], form.cleaned_data['fechainicio'], form.cleaned_data['fechafin']), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'practicasasignadas':
                try:
                    periodoevidencia = CabPeriodoEvidenciaPPP.objects.get(id=int(request.POST['id']))
                    listaevidencia = []
                    for evidencia in periodoevidencia.evidencias_practica_configura_fecha():
                        listaevidencia.append([evidencia.id, evidencia.nombre])
                    data['practicasasignadas'] = PracticasPreprofesionalesInscripcion.objects.filter(status=True, supervisor=profesor, culminada=False, periodoppp=periodoevidencia).exclude(estadosolicitud__in=[3, 5]).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres').distinct()
                    template = get_template("pro_laboratoriocronograma/segmento_practica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "listaevidencia": listaevidencia, "data": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'addinformemensual':
                try:
                    form = InformeMensualSupervisorPracticaForm(request.POST, request.FILES)
                    if not 'archivo' in request.FILES:
                        return JsonResponse({"result": "bad", "mensaje": u"Falta de subir archivo de informe mensual."})
                    d = request.FILES['archivo']
                    newfilesd = d._name
                    ext = newfilesd[newfilesd.rfind("."):]
                    if ext == '.pdf' or ext == '.PDF':
                        a = 1
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                    if d.size > 20971520:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                    if form.is_valid():
                        if not form.cleaned_data['carrera']:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos una carrera"})
                        if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio no puede ser mayor a fecha fin"})
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("informemensualsupervisor", newfile._name)
                        informe = InformeMensualSupervisorPractica(persona=persona,
                                                                   fechainicio=form.cleaned_data['fechainicio'],
                                                                   fechafin=form.cleaned_data['fechafin'],
                                                                   observacion=form.cleaned_data['observacion'],
                                                                   archivo=newfile)
                        informe.save(request)
                        for data in form.cleaned_data['carrera']:
                            informe.carrera.add(data)
                            informe.save()
                        log(u'Adiciono supervisor informe mensual de practicas pre profesionales: fecha inicio(%s) - fecha fin(%s) - observacion(%s) - archivo(%s) id[%s]' % (informe.fechainicio, informe.fechafin, informe.observacion, informe.archivo, informe.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editinformemensual':
                try:
                    form = InformeMensualSupervisorPracticaForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        d = request.FILES['archivo']
                        newfilesd = d._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if ext == '.pdf' or ext == '.PDF':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf."})
                        if d.size > 20971520:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                    if form.is_valid():
                        if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio no puede ser mayor a fecha fin"})
                        if not form.cleaned_data['carrera']:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar al menos una carrera"})
                        informe = InformeMensualSupervisorPractica.objects.get(pk=int(encrypt(request.POST['id'])), persona=persona)
                        informe.fechainicio = form.cleaned_data['fechainicio']
                        informe.fechafin = form.cleaned_data['fechafin']
                        informe.observacion = form.cleaned_data['observacion']
                        informe.carrera = form.cleaned_data['carrera']
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("informemensualsupervisor", newfile._name)
                            informe.archivo = newfile
                        informe.save(request)
                        log(u'Edito supervisor informe mensual de practicas pre profesionales: fecha inicio(%s) - fecha fin(%s) - observacion(%s) - archivo(%s) id[%s]' % (informe.fechainicio, informe.fechafin, informe.observacion, informe.archivo, informe.id), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delinformemensual':
                try:
                    informe = InformeMensualSupervisorPractica.objects.get(pk=int(encrypt(request.POST['id'])), persona=persona)
                    log(u'Elimino supervisor informe mensual de practicas pre profesionales: fecha inicio(%s) - fecha fin(%s) - observacion(%s) - archivo(%s) id[%s]' % (informe.fechainicio, informe.fechafin, informe.observacion, informe.archivo, informe.id), request, "del")
                    informe.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'editpractica':
                try:
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = PracticasPreprofesionalesInscripcionSupervisorForm(request.POST)
                    if form.is_valid():
                        practicaspreprofesionalesinscripcion.fechadesde = form.cleaned_data['fechadesde']
                        practicaspreprofesionalesinscripcion.fechahasta = form.cleaned_data['fechahasta']
                        practicaspreprofesionalesinscripcion.tipo = form.cleaned_data['tipo']
                        practicaspreprofesionalesinscripcion.departamento = form.cleaned_data['departamento']
                        practicaspreprofesionalesinscripcion.numerohora = form.cleaned_data['numerohora']
                        practicaspreprofesionalesinscripcion.otraempresa = form.cleaned_data['otraempresa']
                        if form.cleaned_data['otraempresa'] == False:
                            practicaspreprofesionalesinscripcion.empresaempleadora_id = form.cleaned_data['empresaempleadora']
                            practicaspreprofesionalesinscripcion.otraempresaempleadora = ''
                        else:
                            practicaspreprofesionalesinscripcion.otraempresaempleadora = form.cleaned_data['otraempresaempleadora']
                            practicaspreprofesionalesinscripcion.empresaempleadora_id = None
                        practicaspreprofesionalesinscripcion.tutorempresa = form.cleaned_data['tutorempresa']
                        if int(form.cleaned_data['tipo']) == 1 or int(form.cleaned_data['tipo']) == 2:
                            malla = practicaspreprofesionalesinscripcion.inscripcion.mi_malla()
                            nivel = practicaspreprofesionalesinscripcion.inscripcion.mi_nivel().nivel
                            if ItinerariosMalla.objects.values('id').filter(malla=malla, nivel__id__lte=nivel.id, status=True).exists():
                                if not form.cleaned_data['itinerario']:
                                    practicaspreprofesionalesinscripcion.itinerariomalla = None
                                else:
                                    itinerario = ItinerariosMalla.objects.filter(pk=form.cleaned_data['itinerario'].id, malla=malla, nivel__id__lte=nivel.id)
                                    if itinerario:
                                        practicaspreprofesionalesinscripcion.itinerariomalla = form.cleaned_data['itinerario']
                                    else:
                                        if nivel.id <= 5:
                                            return JsonResponse({"result": "bad", "mensaje": u"Para solicitar debe tener aprobado 5 nivel."})

                                # if not form.cleaned_data['itinerario']:
                                #     return JsonResponse({"result": "bad", "mensaje": u"Seleccione un itinerario."})
                                # itinerario = ItinerariosMalla.objects.filter(pk=form.cleaned_data['itinerario'].id, malla=malla, nivel__id__lte=nivel.id)
                                # if itinerario:
                                #     practicaspreprofesionalesinscripcion.itinerariomalla = form.cleaned_data['itinerario']
                                # else:
                                #     if nivel.id <= 5:
                                #         return JsonResponse({"result": "bad", "mensaje": u"Para solicitar debe tener aprobado 5 nivel."})
                        else:
                            practicaspreprofesionalesinscripcion.itinerariomalla = None
                        practicaspreprofesionalesinscripcion.save(request)
                        log(u'Edito el supervisor practica preprofesionales inscripcion: %s %s' % (practicaspreprofesionalesinscripcion.inscripcion, practicaspreprofesionalesinscripcion.id), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addvisitasupervisor':
                try:
                    # data['supervisorpracticas'] = PracticasPreprofesionalesInscripcion.objects.filter(Q(status=True) & Q(fechadesde__lte=datetime.now().date()) & Q(fechahasta__gte=datetime.now().date()) & Q(supervisor=profesor) & ((Q(estadosolicitud=2) & Q(culminada=False)))).distinct().order_by('inscripcion__persona')
                    data['supervisorpracticas'] = PracticasPreprofesionalesInscripcion.objects.filter(Q(status=True) & Q(supervisor=profesor) & ((Q(estadosolicitud=2) & Q(culminada=False)))).distinct().order_by('inscripcion__persona')
                    data['fecha'] = convertir_fecha(encrypt(request.POST['dia']) + '-' + encrypt(request.POST['mes']) + '-' + encrypt(request.POST['anio']))
                    data['modolectura'] = False
                    data['ESTADO_TIPO_VISITA'] = ESTADO_TIPO_VISITA
                    template = get_template("pro_laboratoriocronograma/addvisitasupervisor.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'titulo': 'Agendar visita de prácticas asignadas', "data": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'addguardarvisitasupervisor':
                try:
                    listapracticas = json.loads(request.POST['lista_items1'])
                    fecha = convertir_fecha(encrypt(request.POST['dia']) + '-' + encrypt(request.POST['mes']) + '-' + encrypt(request.POST['anio']))
                    if not listapracticas:
                        return JsonResponse({"result": "bad", "mensaje": u"Seleccione al menos una prácticas pre profesionales."})
                    visitapractica = VisitaPractica(persona=persona, fecha=fecha)
                    visitapractica.save(request)
                    log(u'Adiciono visita de práctica del supervisor: visita practica [%s][%s]' % (visitapractica, visitapractica.id), request, "add")
                    for lista in listapracticas:
                        detallevisita = VisitaPractica_Detalle(visitapractica=visitapractica, practica_id=int(encrypt(lista['idp'])), tipo=int(encrypt(lista['idt'])))
                        detallevisita.save(request)
                        log(u'Adiciono detalle visita de práctica del supervisor: visita practica [%s][%s] - en detalle visita práctica: %s [%s]' % (visitapractica, visitapractica.id, detallevisita, detallevisita.id), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editvisitasupervisor':
                try:
                    data['visitapractica'] = visitapractica = VisitaPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                    data['total_detalles_visitada'] = visitapractica.total_detalles_culminada()
                    data['ESTADO_TIPO_VISITA'] = ESTADO_TIPO_VISITA
                    # data['supervisorpracticas'] = PracticasPreprofesionalesInscripcion.objects.filter(Q(status=True) & Q(fechadesde__lte=datetime.now().date()) & Q(fechahasta__gte=datetime.now().date()) & Q(supervisor=profesor) & ((Q(estadosolicitud=2) & Q(culminada=False)) | Q(pk__in=visitapractica.detalles_visitas().values_list('practica__id', flat=True)))).distinct().order_by('inscripcion__persona')
                    data['supervisorpracticas'] = PracticasPreprofesionalesInscripcion.objects.filter(Q(status=True) & Q(supervisor=profesor) & ((Q(estadosolicitud=2) & Q(culminada=False)) | Q(pk__in=visitapractica.detalles_visitas().values_list('practica__id', flat=True)))).distinct().order_by('inscripcion__persona')
                    template = get_template("pro_laboratoriocronograma/editvisitasupervisor.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'titulo': 'Agendar visita de prácticas asignadas', "data": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'editguardarvisitasupervisor':
                try:
                    listapracticas = json.loads(request.POST['lista_items1'])
                    if not listapracticas:
                        return JsonResponse({"result": "bad", "mensaje": u"Seleccione al menos una prácticas pre profesionales."})
                    visitapractica = VisitaPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                    for lista in listapracticas:
                        if visitapractica.visitapractica_detalle_set.values('id').filter(practica_id=int(encrypt(lista['idp'])), status=True).exists() and not visitapractica.visitapractica_detalle_set.values('id').filter(practica_id=int(encrypt(lista['idp'])), tipo=int(encrypt(lista['idt'])), status=True).exists():
                            detallevisita = visitapractica.visitapractica_detalle_set.get(practica_id=int(encrypt(lista['idp'])))
                            detallevisita.tipo = int(encrypt(lista['idt']))
                            detallevisita.save(request)
                            log(u'Edito tipo detalle visita de práctica del supervisor: visita practica [%s][%s] - en detalle visita práctica: %s [%s]' % (visitapractica, visitapractica.id, detallevisita, detallevisita.id), request, "edit")
                        elif not visitapractica.visitapractica_detalle_set.values('id').filter(practica_id=int(encrypt(lista['idp'])), status=True).exists():
                            detallevisita = VisitaPractica_Detalle(visitapractica=visitapractica, practica_id=int(encrypt(lista['idp'])), tipo=int(encrypt(lista['idt'])))
                            detallevisita.save(request)
                            log(u'Adiciono detalle visita de práctica del supervisor: visita practica [%s][%s] - en detalle visita práctica: %s [%s]' % (visitapractica, visitapractica.id, detallevisita, detallevisita.id), request, "add")
                    eliminarvisitapractica = visitapractica.detalles_visitas_sin_culminado().exclude(practica__id__in=[int(encrypt(lista['idp'])) for lista in listapracticas])
                    for eliminardetallevisita in eliminarvisitapractica:
                        log(u'Elimino detalle visita de práctica del supervisor: visita practica [%s][%s] - en detalle visita práctica: %s [%s]' % (eliminardetallevisita.visitapractica, eliminardetallevisita.visitapractica.id, eliminardetallevisita, eliminardetallevisita.id), request, "del")
                        eliminardetallevisita.delete()
                        # eliminardetallevisita.status = False
                        # eliminardetallevisita.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'listavisitasupervisor':
                try:
                    data['visitapractica'] = VisitaPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                    data['ESTADO_TIPO_VISITA'] = ESTADO_TIPO_VISITA
                    template = get_template("pro_laboratoriocronograma/listavisitasupervisor.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'titulo': 'Lista visitas agendada', "data": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'delvisitasupervisor':
                try:
                    eliminarvisitapractica = VisitaPractica.objects.filter(pk=encrypt(request.POST['id']))
                    for eliminarvisita in eliminarvisitapractica:
                        log(u'Elimino visita de práctica con su detalle de práctica a visitar del supervisor: %s - en fecha: %s [%s]' % (eliminarvisita.persona, eliminarvisita.fecha, eliminarvisita.id), request, "del")
                        eliminarvisita.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'obsvisitasupervisor':
                try:
                    data['modolectura'] = False
                    data['visitapractica'] = VisitaPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                    data['ESTADO_VISITA_PRACTICA'] = ESTADO_VISITA_PRACTICA
                    template = get_template("pro_laboratoriocronograma/obsvisitasupervisor.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'titulo': 'Culminar visitas agendada', "data": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'estadovisitapractica':
                try:
                    detallevisita = VisitaPractica_Detalle.objects.get(pk=int(encrypt(request.POST['id'])))
                    detallevisita.estado = int(encrypt(request.POST['estado']))
                    detallevisita.save(request)
                    log(u'Cambio estado de visita[%s] en detalle visita de práctica del supervisor: visita practica [%s][%s] - en detalle visita práctica: %s [%s]' % (detallevisita.get_estado_display(), detallevisita.visitapractica, detallevisita.visitapractica.id, detallevisita, detallevisita.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addobsvisitasupervisor':
                try:
                    detallevisita = VisitaPractica_Detalle.objects.get(pk=int(encrypt(request.POST['id'])))
                    if request.POST['del'] == 'true':
                        detallevisita.observacion = None
                    else:
                        detallevisita.observacion = request.POST['observacion']
                    detallevisita.save(request)
                    log(u'Edito observacion de detalle visita de práctica del supervisor: visita practica [%s][%s] - en detalle visita práctica: %s [%s] - con observacion %s' % (detallevisita.visitapractica, detallevisita.visitapractica.id, detallevisita, detallevisita.id, detallevisita.observacion), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'listaobsvisitasupervisor':
                try:
                    data['modolectura'] = True
                    data['visitapractica'] = VisitaPractica.objects.get(pk=int(encrypt(request.POST['id'])))
                    template = get_template("pro_laboratoriocronograma/obsvisitasupervisor.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'titulo': 'Observaciones de visitas agendada', "data": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'inscripcionvisitapractica':
                try:
                    listacarreras = []
                    listainscripciones = []
                    listaidcarreras = []
                    idcor = int(encrypt(request.POST['idcor']))
                    idcar = int(encrypt(request.POST['idcar']))
                    cargcar = request.POST['cargcar']
                    inscripciones = PracticasPreprofesionalesInscripcion.objects.filter(status=True, supervisor=profesor).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    # CARGAR POR CARRERA
                    if cargcar == 'Si':
                        if idcor > 0:
                            listaidcarreras = inscripciones.values_list('inscripcion__carrera__id').filter(inscripcion__carrera__coordinacion__id=idcor).distinct('inscripcion__carrera__id').order_by('inscripcion__carrera__id')
                            inscripciones = inscripciones.filter(inscripcion__carrera__coordinacion__id=idcor).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                        carreras = Carrera.objects.filter(pk__in=listaidcarreras)
                        for carrera in carreras:
                            listacarreras.append([encrypt(carrera.id).__str__(), carrera.__str__()])
                    else:
                        inscripciones = inscripciones.filter(inscripcion__carrera__id=idcar).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    # CARGAR INSCRIPCIONES
                    for inscripcion in inscripciones.values_list('inscripcion__id', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres').distinct():
                        listainscripciones.append([encrypt(inscripcion[0]).__str__(), u'%s %s %s' % (inscripcion[1], inscripcion[2], inscripcion[3])])
                    return JsonResponse({'result': 'ok', 'inscripciones': listainscripciones, 'carreras': listacarreras})
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'informevinculacionpractica':
                try:
                    data['visitapractica'] = VisitaPractica.objects.get(pk=int(encrypt(request.POST['id'])), persona=persona)
                    return conviert_html_to_pdf('pro_laboratoriocronograma/informe_vinculacion_practica_pdf.html', {'pagesize': 'A4 landscape', 'datos': data})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?action=visitasupervisor&info=%s" % 'Error al generar informe de vinculación de prácticas')

            elif action == 'informefichaseguimientopractica':
                try:
                    data['visitapractica'] = VisitaPractica.objects.get(pk=int(encrypt(request.POST['id'])), persona=persona)
                    return conviert_html_to_pdf('pro_laboratoriocronograma/informe_ficha_seguimiento_practica_pdf.html', {'pagesize': 'A4 landscape', 'datos': data})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?action=visitasupervisor&info=%s" % 'Error al generar informe de vinculación de prácticas')

            elif action == 'informeprofesor':
                mensaje = "Problemas al generar el informe de actividades."
                try:
                    profesordistributivo = ProfesorDistributivoHoras.objects.get(pk=int(encrypt(request.POST['idd'])))
                    return conviert_html_to_pdf('adm_criteriosactividadesdocente/informe_actividad_docente_pdf.html', {'pagesize': 'A4', 'data': profesordistributivo.profesor.informe_actividades_mensual_docente(periodo, request.POST['fini'], request.POST['ffin'], 'TODO')})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % mensaje)

            elif action == 'detalleaprobacionsilabo':
                try:
                    data['silabo'] = silabo = Silabo.objects.get(pk=int(request.POST['id']))
                    data['historialaprobacion'] = silabo.aprobarsilabo_set.filter(status=True).order_by('-id').exclude(
                        estadoaprobacion=variable_valor('PENDIENTE_SILABO'))
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    template = get_template("pro_laboratoriocronograma/detalleaprobacionsilabo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'seguimientosilabo':
                try:
                    data['title'] = u'Seguimiento de sílabo'
                    materia = Materia.objects.get(pk=request.POST['id'])
                    data['silabo'] = materia.silabo_actual()
                    data['profesormateria'] = ProfesorMateria.objects.filter(materia=materia, status=True)[0]
                    silabo = materia.silabo_actual()
                    data['semanas'] = silabo.silabosemanal_set.filter(status=True).order_by('numsemana')
                    template = get_template("pro_laboratoriocronograma/seguimientosilabo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subircronograma':
                try:
                    actividad = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['id'])), distributivo__profesor=profesor, status=True)
                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extencion = arch._name.split('.')
                        exte = extencion[1]
                        if arch.size > 20971520:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                        if not exte == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivo_", newfile._name)
                        if not actividad.cronogramaactividad_set.filter(profesor=profesor).exists():
                            cron = CronogramaActividad(actividad=actividad, profesor=profesor, archivo=newfile)
                            cron.save(request)
                            recorido = DetalleRecoridoCronogramaActividad(cronogramaactividad=cron,
                                                                          fecha=datetime.now().date(),
                                                                          observacion=u'Registro cronograma de actividades')
                            recorido.save(request)
                        else:
                            cron = CronogramaActividad.objects.filter(actividad=actividad, profesor=profesor)[0]
                            if cron.estado == 3:
                                recorido = DetalleRecoridoCronogramaActividad(cronogramaactividad=cron,
                                                                              fecha=datetime.now().date(),
                                                                              observacion=u'Registro cronograma de actividades')
                                recorido.save(request)
                                cron.estado = 1
                            cron.archivo = newfile
                            cron.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detalleobservacion':
                try:
                    data['cron'] = cron = CronogramaActividad.objects.get(pk=int(request.POST['id']))
                    data['detalles'] = cron.detallerecoridocronogramaactividad_set.filter(status=True).order_by('-fecha')
                    template = get_template("pro_laboratoriocronograma/detalleobservacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'cargardatoscongreso':
                try:
                    congresoid = request.POST['id']
                    congreso = SugerenciaCongreso.objects.get(pk=congresoid)
                    return JsonResponse({"result": "ok", "idpais": congreso.pais_id, "fechai": congreso.fechainicio, "fechaf": congreso.fechafin, "link": congreso.link})
                except Exception as ex:
                    pass

            elif action == 'addponencia':
                try:
                    form = PlanificarPonenciasForm(request.POST, request.FILES)

                    if 'archivoabstract' in request.FILES:
                        archivo = request.FILES['archivoabstract']
                        descripcionarchivo = 'Abstract(Resumen)'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if 'archivocartaaceptacion' in request.FILES:
                        archivo = request.FILES['archivocartaaceptacion']
                        descripcionarchivo = 'Carta de Aceptación'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if 'archivocronograma' in request.FILES:
                        archivo = request.FILES['archivocronograma']
                        descripcionarchivo = 'Cronograma de actividades'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if 'archivocomite' in request.FILES:
                        archivo = request.FILES['archivocomite']
                        descripcionarchivo = 'Comité científico'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if form.is_valid():
                        if PlanificarPonencias.objects.values('id').filter(tema__icontains=form.cleaned_data['tema'], status=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Tema de la ponencia ya ha sido ingresado anterioromente", "showSwal": "True", "swalType": "warning"})

                        if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin", "showSwal": "True", "swalType": "warning"})

                        lista = json.loads(request.POST['lista_items1'])
                        existecomite = False
                        for l in lista:
                            if l['obligatorio'] is True and l['valor'] is False:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El criterio [ %s ] es obligatorio de marcar" % l['criterio'], "showSwal": "True", "swalType": "warning"})

                            if form.cleaned_data['pais'].id == 1:
                                if l['orden'] == '2' and l['valor'] is True:
                                    existecomite = True
                            else:
                                if l['orden'] == '3' and l['valor'] is True:
                                    existecomite = True

                        convocatoria = ConvocatoriaPonencia.objects.get(pk=int(encrypt(request.POST['idc'])))
                        nombreotrabase = ''
                        otrabase = len(request.POST['nombreotrabasenac'].strip()) > 0 or len(request.POST['nombreotrabaseint'].strip()) > 0
                        if otrabase:
                            nombreotrabase = request.POST['nombreotrabasenac'].strip().upper() if len(request.POST['nombreotrabasenac'].strip()) > 0 else request.POST['nombreotrabaseint'].strip().upper()

                        planificarponencias = PlanificarPonencias(
                            convocatoria=convocatoria,
                            periodo=periodo,
                            profesor=profesor,
                            nombre=form.cleaned_data['nombre'],
                            tema=form.cleaned_data['tema'],
                            pais=form.cleaned_data['pais'],
                            fecha_fin=form.cleaned_data['fechafin'],
                            fecha_inicio=form.cleaned_data['fechainicio'],
                            costo=form.cleaned_data['costo'],
                            modalidad=form.cleaned_data['modalidad'],
                            link=form.cleaned_data['link'],
                            justificacion=form.cleaned_data['justificacion'],
                            areaconocimiento=form.cleaned_data['areaconocimiento'],
                            subareaconocimiento=form.cleaned_data['subareaconocimiento'],
                            subareaespecificaconocimiento=form.cleaned_data['subareaespecificaconocimiento'],
                            lineainvestigacion=form.cleaned_data['lineainvestigacion'],
                            sublineainvestigacion=form.cleaned_data['sublineainvestigacion'],
                            provieneproyecto=form.cleaned_data['provieneproyecto'],
                            tipoproyecto=form.cleaned_data['tipoproyecto'] if form.cleaned_data['provieneproyecto'] else None,
                            existecomite=existecomite,
                            otrabase=otrabase,
                            nombreotrabase=nombreotrabase,
                            pertenecegrupoinv=form.cleaned_data['pertenecegrupoinv'],
                            grupoinvestigacion=form.cleaned_data['grupoinvestigacion'],
                            estado=1
                        )
                        planificarponencias.save(request)

                        if form.cleaned_data['provieneproyecto']:
                            if int(form.cleaned_data['tipoproyecto']) != 3:
                                planificarponencias.proyectointerno = form.cleaned_data['proyectointerno']
                            else:
                                planificarponencias.proyectoexterno = form.cleaned_data['proyectoexterno']

                        if 'archivoabstract' in request.FILES:
                            newfile = request.FILES['archivoabstract']
                            newfile._name = generar_nombre("pabstract", newfile._name)
                            planificarponencias.archivoabstract = newfile

                        if 'archivocartaaceptacion' in request.FILES:
                            newfile = request.FILES['archivocartaaceptacion']
                            newfile._name = generar_nombre("pcartaaceptacion", newfile._name)
                            planificarponencias.archivocartaaceptacion = newfile

                        if 'archivocronograma' in request.FILES:
                            newfile = request.FILES['archivocronograma']
                            newfile._name = generar_nombre("pcronograma", newfile._name)
                            planificarponencias.archivocronograma = newfile

                        if 'archivocomite' in request.FILES:
                            newfile = request.FILES['archivocomite']
                            newfile._name = generar_nombre("pcomitecientifico", newfile._name)
                            planificarponencias.archivocomite = newfile

                        planificarponencias.save(request)

                        if 'lista_items1' in request.POST:
                            lista = json.loads(request.POST['lista_items1'])
                            for l in lista:
                                detallecriterio = PlanificarPonenciasCriterio(
                                    ponencia=planificarponencias,
                                    criterio_id=l['id'],
                                    valor=l['valor']
                                )
                                detallecriterio.save()

                        recorrido = PlanificarPonenciasRecorrido(planificarponencias=planificarponencias,
                                                                 observacion='SOLICITADO',
                                                                 estado=1,
                                                                 fecha=datetime.now().date(),
                                                                 persona=profesor.persona)
                        recorrido.save(request)

                        log(u'%s adicionó solicitdu de financiamiento a ponencias: %s' % (persona, planificarponencias), request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'addcapacitacion':
                try:
                    form = PlanificarCapacitacionesForm(request.POST, request.FILES)
                    convocatoria = CronogramaCapacitacionDocente.objects.get(pk=int(request.POST['convocatoria']))
                    fechainicio = formatear_fecha(convocatoria.iniciocapacitacion)
                    # fechainicio = fechainicio[8:10] + '-' + fechainicio[5:7] + '-' + fechainicio[0:4]
                    fechafin = formatear_fecha(convocatoria.fincapacitacion)
                    # fechafin = fechafin[8:10] + '-' + fechafin[5:7] + '-' + fechafin[0:4]
                    fechainiciotecdoc = formatear_fecha(convocatoria.iniciocapacitaciontecdoc)
                    # fechainiciotecdoc = fechainiciotecdoc[8:10] + '-' + fechainiciotecdoc[5:7] + '-' + fechainiciotecdoc[0:4]
                    fechafintecdoc = formatear_fecha(convocatoria.fincapacitaciontecdoc)
                    # fechafintecdoc = fechafintecdoc[8:10] + '-' + fechafintecdoc[5:7] + '-' + fechafintecdoc[0:4]
                    saldo = null_to_decimal(convocatoria.monto - convocatoria.totalmonto_profesor(profesor=profesor, convocatoria=convocatoria))

                    # INICIO --- incluye y valida archivo pdf
                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]

                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    # FIN --- incluye y valida archivo pdf
                    profesorperiodo = ProfesorDistributivoHoras.objects.get(periodo=periodo, profesor=profesor, status=True)
                    tipocategoria = profesorperiodo.categoria.id

                    if form.is_valid():
                        fecha_actual = datetime.now().date()
                        fechaminimains = fecha_actual + timedelta(days=29)
                        if tipocategoria == 9:

                            if form.cleaned_data['fechainicio'] <= fechaminimains:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser al menos un mes después del registro de la solicitud"})

                            if form.cleaned_data['fechainicio'] < convocatoria.iniciocapacitaciontecdoc:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser mayor o igual a %s" % (fechainiciotecdoc)})

                            if form.cleaned_data['fechafin'] > convocatoria.fincapacitaciontecdoc:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin debe ser menor o igual a %s" % (fechafintecdoc)})

                            if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin"})
                        else:

                            if form.cleaned_data['fechainicio'] <= fechaminimains:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser al menos un mes después del registro de la solicitud"})

                            if form.cleaned_data['fechainicio'] < convocatoria.iniciocapacitacion:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser mayor o igual a %s" % (fechainicio)})

                            if form.cleaned_data['fechafin'] > convocatoria.fincapacitacion:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin debe ser menor o igual a %s" % (fechafin)})

                            if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin"})

                        if form.cleaned_data['horas'] <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"El número de horas debe ser mayor a 0"})

                        if form.cleaned_data['costo'] <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"El costo debe ser mayor a $ 0.00"})

                        costo = Decimal(form.cleaned_data['costo']).quantize(Decimal('0.00'))
                        if costo > saldo:
                            return JsonResponse({"result": "bad", "mensaje": u"El costo supera el monto disponible: $ %s" % saldo})

                        lista = json.loads(request.POST['lista_items1'])
                        for l in lista:
                            if l['obligatorio'] is True and l['valor'] is False:
                                return JsonResponse({"result": "bad", "mensaje": u'El criterio "%s" es obligatorio de marcar' % l['criterio']})
                        idenfoque = json.loads(request.POST['lista_items2'])
                        planificarcapacitacion = PlanificarCapacitaciones(cronograma=convocatoria,
                                                                          profesor=profesor,
                                                                          tema=form.cleaned_data['tema'],
                                                                          justificacion=form.cleaned_data['justificacion'],
                                                                          institucion=form.cleaned_data['institucion'].upper(),
                                                                          link=form.cleaned_data['link'],
                                                                          fechainicio=form.cleaned_data['fechainicio'],
                                                                          fechafin=form.cleaned_data['fechafin'],
                                                                          pais=form.cleaned_data['pais'],
                                                                          modalidad=form.cleaned_data['modalidad'],
                                                                          costo=form.cleaned_data['costo'],
                                                                          devolucion=0.00,
                                                                          costoneto=form.cleaned_data['costo'],
                                                                          horas=form.cleaned_data['horas'],
                                                                          enfoque_id=idenfoque[0],
                                                                          periodo=periodo,
                                                                          estado=1,
                                                                          tipo=1,
                                                                          infocompletacap=False)

                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivocapacitaciondocente", newfile._name)
                            planificarcapacitacion.archivo = newfile

                        planificarcapacitacion.save(request)

                        listaitemenfoque = json.loads(request.POST['lista_items3'])
                        for inve in listaitemenfoque:
                            if int(idenfoque[0]) == 4 or int(idenfoque[0]) == 12:
                                ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=planificarcapacitacion, lineainvestigacion_id=inve)
                            if int(idenfoque[0]) == 7:
                                ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=planificarcapacitacion, titulacion_id=inve)
                            if int(idenfoque[0]) == 8:
                                ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=planificarcapacitacion, materia_id=inve)
                            ingresoenfoque.save()

                        if 'lista_items1' in request.POST:
                            lista = json.loads(request.POST['lista_items1'])
                            for l in lista:
                                detallecriterios = PlanificarCapacitacionesDetalleCriterios(capacitacion=planificarcapacitacion,
                                                                                            criterio_id=l['id'],
                                                                                            estadodocente=l['valor'],
                                                                                            estadodirector=False,
                                                                                            estadouath=False)
                                detallecriterios.save()

                        # micorreo = Persona.objects.get(cedula='0923704928')

                        send_html_mail("Solicitud de capacitación",
                                       "emails/solicitud_capdocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'docente': profesor.persona,
                                        'numero': planificarcapacitacion.id,
                                        't': miinstitucion()},
                                       profesor.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        # Coordinador de carrera - envio de e-mail
                        coordinador = planificarcapacitacion.obtenerdatosautoridad('DIR', periodo)
                        decano = planificarcapacitacion.obtenerdatosautoridad('DEC', periodo)
                        vice = planificarcapacitacion.obtenerdatosautoridad('VICE', periodo)
                        viceacade = planificarcapacitacion.obtenerdatosautoridad('VICEACADE', periodo)
                        profesor_id = profesor.persona_id
                        if coordinador.persona_id == profesor_id:
                            planificarcapacitacion.estado = 2
                            recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=planificarcapacitacion,
                                                                             observacion='Validado',
                                                                             estado=2,
                                                                             fecha=datetime.now().date(),
                                                                             persona=persona)
                            recorridocap.save(request)
                        elif decano.persona_id == profesor_id:
                            planificarcapacitacion.estado = 3
                            recorridocap = PlanificarCapacitacionesRecorrido(
                                planificarcapacitaciones=planificarcapacitacion,
                                observacion='Aprobado',
                                estado=3,
                                fecha=datetime.now().date(),
                                persona=persona)
                            recorridocap.save(request)
                        planificarcapacitacion.save(request)

                        if coordinador and decano and vice and viceacade:
                            if coordinador.persona_id == profesor_id:
                                autoridad = decano.persona
                            elif decano.persona_id == profesor_id:
                                autoridad = vice.persona

                            else:
                                autoridad = coordinador.persona
                            send_html_mail("Solicitud de capacitación",
                                           "emails/notificacion_capdocente.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fase': 'SOL',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'numero': planificarcapacitacion.id,
                                            'docente': profesor.persona,
                                            'autoridad1': autoridad,
                                            'autoridad2': '',
                                            't': miinstitucion()
                                            },
                                           coordinador.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )

                        log(u'Adicionó solicitud de capacitacion/actualización: %s' % planificarcapacitacion, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editcapacitacion':
                try:
                    form = PlanificarCapacitacionesForm(request.POST, request.FILES)
                    convocatoria = CronogramaCapacitacionDocente.objects.get(pk=int(request.POST['convocatoria']))
                    fechainicio = str(convocatoria.iniciocapacitacion)
                    fechainicio = fechainicio[8:10] + '-' + fechainicio[5:7] + '-' + fechainicio[0:4]
                    fechafin = str(convocatoria.fincapacitacion)
                    fechafin = fechafin[8:10] + '-' + fechafin[5:7] + '-' + fechafin[0:4]
                    fechainiciotecdoc = str(convocatoria.iniciocapacitaciontecdoc)
                    fechainiciotecdoc = fechainiciotecdoc[8:10] + '-' + fechainiciotecdoc[5:7] + '-' + fechainiciotecdoc[0:4]
                    fechafintecdoc = str(convocatoria.fincapacitaciontecdoc)
                    fechafintecdoc = fechafintecdoc[8:10] + '-' + fechafintecdoc[5:7] + '-' + fechafintecdoc[0:4]
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                    costosolcap = solicitud.costo

                    saldo = null_to_decimal(convocatoria.monto - (convocatoria.totalmonto_profesor(profesor=profesor, convocatoria=convocatoria) - costosolcap))
                    # INICIO --- Incluye archivo y valida
                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]

                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    # FIN --- Incluye archivo y valida
                    profesorperiodo = ProfesorDistributivoHoras.objects.get(periodo=periodo, profesor=profesor, status=True)
                    tipocategoria = profesorperiodo.categoria.id
                    fechaminimains = datetime.now().date() + timedelta(days=29)
                    if form.is_valid():
                        if tipocategoria == 9:

                            if form.cleaned_data['fechainicio'] <= fechaminimains:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser al menos un mes después del registro de la solicitud"})

                            if form.cleaned_data['fechainicio'] < convocatoria.iniciocapacitaciontecdoc:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser mayor o igual a %s" % (fechainiciotecdoc)})

                            if form.cleaned_data['fechafin'] > convocatoria.fincapacitaciontecdoc:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin debe ser menor o igual a %s" % (fechafintecdoc)})

                            if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin"})
                        else:

                            if form.cleaned_data['fechainicio'] <= fechaminimains:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser al menos un mes después del registro de la solicitud"})

                            if form.cleaned_data['fechainicio'] < convocatoria.iniciocapacitacion:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser mayor o igual a %s" % (fechainicio)})

                            if form.cleaned_data['fechafin'] > convocatoria.fincapacitacion:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin debe ser menor o igual a %s" % (fechafin)})

                            if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin"})
                        if form.cleaned_data['horas'] <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"El número de horas debe ser mayor a 0"})

                        if form.cleaned_data['costo'] <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"El costo debe ser mayor a $ 0.00"})

                        costo = Decimal(form.cleaned_data['costo']).quantize(Decimal('0.00'))
                        if costo > saldo:
                            return JsonResponse({"result": "bad", "mensaje": u"El costo supera el monto disponible: $ %s" % saldo})

                        lista = json.loads(request.POST['lista_items1'])
                        for l in lista:
                            if l['obligatorio'] is True and l['valor'] is False:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u'El criterio "%s" es obligatorio de marcar' % l['criterio']})

                        solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                        codigoenfoqueactual = solicitud.enfoque_id
                        solicitud.tema = form.cleaned_data['tema']
                        solicitud.justificacion = form.cleaned_data['justificacion']
                        solicitud.institucion = form.cleaned_data['institucion'].upper()
                        solicitud.link = form.cleaned_data['link']
                        solicitud.fechainicio = form.cleaned_data['fechainicio']
                        solicitud.fechafin = form.cleaned_data['fechafin']
                        solicitud.pais = form.cleaned_data['pais']
                        solicitud.modalidad = form.cleaned_data['modalidad']
                        solicitud.costo = form.cleaned_data['costo']
                        solicitud.costoneto = form.cleaned_data['costo']
                        solicitud.horas = form.cleaned_data['horas']
                        idenfoque = json.loads(request.POST['lista_items2'])
                        solicitud.enfoque_id = idenfoque[0]
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivocapacitaciondocente", newfile._name)
                            solicitud.archivo = newfile

                        solicitud.save(request)

                        if 'lista_items1' in request.POST:
                            lista = json.loads(request.POST['lista_items1'])
                            for l in lista:
                                detallecriterios = PlanificarCapacitacionesDetalleCriterios.objects.get(pk=int(l['id']))
                                detallecriterios.estadodocente = l['valor']
                                detallecriterios.save()

                        listaitemenfoque = json.loads(request.POST['lista_items3'])
                        if idenfoque[0]:
                            if codigoenfoqueactual == int(idenfoque[0]):
                                if int(idenfoque[0]) == 4:
                                    listadosenfoque = PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud).exclude(lineainvestigacion_id__in=listaitemenfoque)
                                    listadosenfoque.delete()
                                    for inve in listaitemenfoque:
                                        if not PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud, lineainvestigacion_id=inve):
                                            ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=solicitud, lineainvestigacion_id=inve)
                                            ingresoenfoque.save()
                                if int(idenfoque[0]) == 12:
                                    listadosenfoque = PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud).exclude(lineainvestigacion_id__in=listaitemenfoque)
                                    listadosenfoque.delete()
                                    for inve in listaitemenfoque:
                                        if not PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud, lineainvestigacion_id=inve):
                                            ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=solicitud, lineainvestigacion_id=inve)
                                            ingresoenfoque.save()
                                if int(idenfoque[0]) == 7:
                                    listadosenfoque = PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud).exclude(titulacion_id__in=listaitemenfoque)
                                    listadosenfoque.delete()
                                    for inve in listaitemenfoque:
                                        if not PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud, titulacion_id=inve):
                                            ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=solicitud, titulacion_id=inve)
                                            ingresoenfoque.save()
                                if int(idenfoque[0]) == 8:
                                    listadosenfoque = PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud).exclude(materia_id__in=listaitemenfoque)
                                    listadosenfoque.delete()
                                    for inve in listaitemenfoque:
                                        if not PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud, materia_id=inve):
                                            ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=solicitud, materia_id=inve)
                                            ingresoenfoque.save()
                            else:
                                listadosenfoque = PlanificarCapacitacionesEnfoque.objects.filter(planificarcapacitaciones=solicitud)
                                listadosenfoque.delete()
                                for inve in listaitemenfoque:
                                    if int(idenfoque[0]) == 4 or int(idenfoque[0]) == 12:
                                        ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=solicitud, lineainvestigacion_id=inve)
                                    if int(idenfoque[0]) == 7:
                                        ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=solicitud, titulacion_id=inve)
                                    if int(idenfoque[0]) == 8:
                                        ingresoenfoque = PlanificarCapacitacionesEnfoque(planificarcapacitaciones=solicitud, materia_id=inve)
                                    ingresoenfoque.save()
                        log(u'Editó solicitud de capacitacion/actualización: %s' % solicitud, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addarchivoconvenio':
                try:
                    f = PlanificarCapacitacionesArchivoForm(request.FILES)
                    newfile = None

                    if 'archivoconvenio' in request.FILES:
                        arch = request.FILES['archivoconvenio']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                    if f.is_valid():
                        solicitud = PlanificarCapacitaciones.objects.get(pk=int(request.POST['id']))
                        newfile = request.FILES['archivoconvenio']
                        newfile._name = generar_nombre("conveniodevengaciondocente", newfile._name)
                        solicitud.archivoconvenio = newfile
                        solicitud.firmadocente = True
                        solicitud.save(request)
                        log(u'Agregó archivo de convenio a la solicitud de capacitacion/actualización: %s' % solicitud, request, "edit")

                        email_autoridad2 = 'formacion_uath@unemi.edu.ec'
                        tituloemail = 'Registro de Convenio de Devengación - ' + str(persona)
                        autoridad2nombre = ''

                        send_html_mail(tituloemail,
                                       "emails/notificacion_capadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'fase': 'CDE',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'numero': solicitud.id,
                                        'docente': persona,
                                        'autoridad1': autoridad2nombre,
                                        't': miinstitucion()
                                        },
                                       [email_autoridad2],
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addVideoVirtualPos':
                try:
                    from Moodle_Funciones import CrearClaseVirtualClaseMoodleDiferidoPosgrado
                    if not 'idc' in request.POST:
                        raise NameError(u"Parametro de clase no encontrado")
                    if not 'link_1' in request.POST:
                        raise NameError(u"Parametro de enlace 1  de la clase no encontrado")
                    if not 'link_2' in request.POST:
                        raise NameError(u"Parametro de enlace 2 de la clase no encontrado")
                    if not 'link_3' in request.POST:
                        raise NameError(u"Parametro de enlace 3 de la clase no encontrado")
                    if not 'dia' in request.POST:
                        raise NameError(u"Parametro de día de la clase no encontrado")
                    if not 'num_semana' in request.POST:
                        raise NameError(u"Parametro de numero de la semana de la clase no encontrado")
                    if not 'fecha_subida' in request.POST:
                        raise NameError(u"Parametro de fecha de la clase no encontrado")
                    if not request.POST['link_1']:
                        raise NameError(u"Enlace de la grabación 1 es obligatorio")
                    idc = int(request.POST['idc'])
                    link_1 = request.POST['link_1']
                    link_2 = request.POST['link_2']
                    link_3 = request.POST['link_3']
                    dia = request.POST['dia']
                    num_semana = request.POST['num_semana']
                    fecha_subida = request.POST['fecha_subida']
                    id_nombredia = request.POST['id_nombredia']
                    crearaula = CrearClaseVirtualClaseMoodleDiferidoPosgrado(idc, persona, link_1, link_2, link_3, dia, num_semana, fecha_subida, id_nombredia)
                    if crearaula:
                        return JsonResponse({"result": "ok", "mensaje": u"Se subio correctamente la información de la clase"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No tine planificación de la semana del sílabo"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            elif action == 'subirevidenciaejecutadocap':
                try:
                    f = SubirEvidenciaEjecutadoCapacitacionesForm(request.POST, request.FILES)
                    evidenciavalidar = request.POST['evidenciavalidar']
                    newfile = None

                    if evidenciavalidar == 'FAC':
                        if not 'factura' in request.FILES:
                            return JsonResponse({"result": "bad", "mensaje": u"Atención, debe subir el archivo de la factura."})
                    # else:
                    #     if not 'informe' in request.FILES and not 'certificado' in request.FILES:
                    #         return JsonResponse({"result": "bad", "mensaje": u"Atención, debe subir mínimo un archivo de las evidencias."})

                    # if 'informe' in request.FILES:
                    #     arch = request.FILES['informe']
                    #     extension = arch._name.split('.')
                    #     tam = len(extension)
                    #     exte = extension[tam - 1]
                    #     if arch.size > 4194304:
                    #         return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    #     if not exte.lower() == 'pdf':
                    #         return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if 'factura' in request.FILES:
                        arch = request.FILES['factura']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if 'certificado' in request.FILES:
                        arch = request.FILES['certificado']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if f.is_valid():
                        capacitacion = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))

                        # if 'informe' in request.FILES:
                        #     newfile = request.FILES['informe']
                        #     newfile._name = generar_nombre("evidejecapinforme", newfile._name)
                        #     capacitacion.archivoinforme = newfile

                        if 'factura' in request.FILES:
                            newfile = request.FILES['factura']
                            newfile._name = generar_nombre("evidejecapfactura", newfile._name)
                            capacitacion.archivofactura = newfile

                        if 'certificado' in request.FILES:
                            newfile = request.FILES['certificado']
                            newfile._name = generar_nombre("evidejecapcertificado", newfile._name)
                            capacitacion.archivocertificado = newfile

                            newfile = request.FILES['certificado']
                            newfile._name = generar_nombre("capacitacion_", newfile._name)
                            if capacitacion.capacitacion is None:
                                capacitacionth = Capacitacion(persona=persona,
                                                              institucion=capacitacion.institucion,
                                                              nombre=capacitacion.tema,
                                                              anio=datetime.now().date().year,
                                                              pais=capacitacion.pais,
                                                              fechainicio=capacitacion.fechainicio,
                                                              fechafin=capacitacion.fechafin,
                                                              horas=capacitacion.horas,
                                                              modalidad=capacitacion.modalidad,
                                                              tipocapacitacion_id=1,
                                                              archivo=newfile)
                                capacitacionth.save(request)
                                log(u'Adiciono capacitacion: %s' % persona, request, "add")

                                capacitacion.capacitacion = capacitacionth
                            else:
                                capacitacionth = Capacitacion.objects.get(pk=capacitacion.capacitacion.id)
                                capacitacionth.archivo = newfile

                        capacitacion.estado = 14
                        capacitacion.save(request)

                        log(u'Agregó archivos de evidencia de ejecución a la solicitud de capacitacion/actualización: %s' % capacitacion, request, "edit")

                        recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=capacitacion,
                                                                         observacion='Agregó archivos de evidencia de capacitación ejecutada',
                                                                         estado=14,
                                                                         fecha=datetime.now().date(),
                                                                         persona=persona)
                        recorridocap.save(request)
                        log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")

                        # Direccion de talento humano - envio de e-mail
                        correouath = 'evaluaciondocente@unemi.edu.ec'
                        if evidenciavalidar == 'FAC':
                            tituloemail = "Registro de evidencia - Factura de pago realizado por evento de capacitación"
                        else:
                            if 'certificado' in request.FILES:
                                tituloemail = "Registro de evidencia - Certificado por evento de capacitación"
                            # if 'informe' in request.FILES and 'certificado' in request.FILES:
                            #     tituloemail = "Registro de evidencias - Informe de comisión y Certificado por evento de capacitación"
                            # elif 'informe' in request.FILES:
                            #     tituloemail = "Registro de evidencia - Informe de comisión por evento de capacitación"
                            # else:
                            #     tituloemail = "Registro de evidencia - Certificado por evento de capacitación"

                        send_html_mail(tituloemail,
                                       "emails/notificacion_capdocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'fase': 'EVI',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'numero': capacitacion.id,
                                        'docente': profesor.persona,
                                        'autoridad1': '',
                                        'autoridad2': '',
                                        't': miinstitucion()
                                        },
                                       [correouath],
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editponencia':
                try:
                    form = PlanificarPonenciasForm(request.POST, request.FILES)

                    if 'archivoabstract' in request.FILES:
                        archivo = request.FILES['archivoabstract']
                        descripcionarchivo = 'Abstract(Resumen)'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if 'archivocartaaceptacion' in request.FILES:
                        archivo = request.FILES['archivocartaaceptacion']
                        descripcionarchivo = 'Carta de Aceptación'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if 'archivocronograma' in request.FILES:
                        archivo = request.FILES['archivocronograma']
                        descripcionarchivo = 'Cronograma de actividades'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if 'archivocomite' in request.FILES:
                        archivo = request.FILES['archivocomite']
                        descripcionarchivo = 'Comité científico'
                        resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    if form.is_valid():
                        if PlanificarPonencias.objects.values('id').filter(tema__icontains=form.cleaned_data['tema'], status=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Tema de la ponencia ya ha sido ingresado anterioromente", "showSwal": "True", "swalType": "warning"})

                        if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin", "showSwal": "True", "swalType": "warning"})

                        lista = json.loads(request.POST['lista_items1'])
                        existecomite = False
                        for l in lista:
                            if l['obligatorio'] is True and l['valor'] is False:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El criterio [ %s ] es obligatorio de marcar" % l['criterio'], "showSwal": "True", "swalType": "warning"})

                            if form.cleaned_data['pais'].id == 1:
                                if l['orden'] == '4' and l['valor'] is True:
                                    existecomite = True
                            else:
                                if l['orden'] == '3' and l['valor'] is True:
                                    existecomite = True

                        ponencia = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                        nombreotrabase = ''
                        otrabase = len(request.POST['nombreotrabasenac'].strip()) > 0 or len(request.POST['nombreotrabaseint'].strip()) > 0
                        if otrabase:
                            nombreotrabase = request.POST['nombreotrabasenac'].strip().upper() if len(request.POST['nombreotrabasenac'].strip()) > 0 else request.POST['nombreotrabaseint'].strip().upper()

                        ponencia.nombre = form.cleaned_data['nombre']
                        ponencia.tema = form.cleaned_data['tema']
                        ponencia.pais = form.cleaned_data['pais']
                        ponencia.fecha_fin = form.cleaned_data['fechafin']
                        ponencia.fecha_inicio = form.cleaned_data['fechainicio']
                        ponencia.costo = form.cleaned_data['costo']
                        ponencia.modalidad = form.cleaned_data['modalidad']
                        ponencia.link = form.cleaned_data['link']
                        ponencia.justificacion = form.cleaned_data['justificacion']
                        ponencia.areaconocimiento = form.cleaned_data['areaconocimiento']
                        ponencia.subareaconocimiento = form.cleaned_data['subareaconocimiento']
                        ponencia.subareaespecificaconocimiento = form.cleaned_data['subareaespecificaconocimiento']
                        ponencia.lineainvestigacion = form.cleaned_data['lineainvestigacion']
                        ponencia.sublineainvestigacion = form.cleaned_data['sublineainvestigacion']
                        ponencia.provieneproyecto = form.cleaned_data['provieneproyecto']
                        ponencia.tipoproyecto = form.cleaned_data['tipoproyecto'] if form.cleaned_data['provieneproyecto'] else None
                        ponencia.existecomite = existecomite
                        ponencia.otrabase = otrabase
                        ponencia.nombreotrabase = nombreotrabase
                        ponencia.pertenecegrupoinv = form.cleaned_data['pertenecegrupoinv']
                        ponencia.grupoinvestigacion = form.cleaned_data['grupoinvestigacion']
                        ponencia.cartagenerada = False
                        ponencia.archivocartacompromiso = None

                        if not existecomite:
                            ponencia.archivocomite = None

                        if form.cleaned_data['provieneproyecto']:
                            if int(form.cleaned_data['tipoproyecto']) != 3:
                                ponencia.proyectointerno = form.cleaned_data['proyectointerno']
                            else:
                                ponencia.proyectoexterno = form.cleaned_data['proyectoexterno']

                        if 'archivoabstract' in request.FILES:
                            newfile = request.FILES['archivoabstract']
                            newfile._name = generar_nombre("pabstract", newfile._name)
                            ponencia.archivoabstract = newfile

                        if 'archivocartaaceptacion' in request.FILES:
                            newfile = request.FILES['archivocartaaceptacion']
                            newfile._name = generar_nombre("pcartaaceptacion", newfile._name)
                            ponencia.archivocartaaceptacion = newfile

                        if 'archivocronograma' in request.FILES:
                            newfile = request.FILES['archivocronograma']
                            newfile._name = generar_nombre("pcronograma", newfile._name)
                            ponencia.archivocronograma = newfile

                        if 'archivocomite' in request.FILES:
                            newfile = request.FILES['archivocomite']
                            newfile._name = generar_nombre("pcomitecientifico", newfile._name)
                            ponencia.archivocomite = newfile

                        ponencia.save(request)

                        if 'lista_items1' in request.POST:
                            lista = json.loads(request.POST['lista_items1'])

                            editar = ponencia.planificarponenciascriterio_set.filter(status=True, criterio_id=lista[0]['id']).exists()
                            if editar is False:
                                PlanificarPonenciasCriterio.objects.filter(ponencia=ponencia, status=True).update(status=False)

                            for l in lista:
                                if editar:
                                    PlanificarPonenciasCriterio.objects.filter(ponencia=ponencia, status=True, criterio_id=l['id']).update(valor=l['valor'])
                                else:
                                    detallecriterio = PlanificarPonenciasCriterio(
                                        ponencia=ponencia,
                                        criterio_id=l['id'],
                                        valor=l['valor']
                                    )
                                    detallecriterio.save()

                        log(u'%s editó solicitud de financiamiento a ponencias: %s' % (persona, ponencia), request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'cartacompromisoponenciapdf':
                try:
                    data = {}

                    # Consulto la solicitud de financiamiento de ponencia
                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))
                    solicitud.cartagenerada = True
                    solicitud.save(request)

                    data['solicitud'] = solicitud
                    data['solicitante'] = solicitud.profesor
                    data['fechasolicitud'] = str(solicitud.fecha_creacion.day) + " de " + MESES_CHOICES[solicitud.fecha_creacion.month - 1][1].capitalize() + " del " + str(solicitud.fecha_creacion.year)
                    data['fechacongreso'] = fecha_letra_rango(solicitud.fecha_inicio, solicitud.fecha_fin)

                    # Creacion del archivo
                    directorio = SITE_STORAGE + '/media/ponencias/cartacompromiso'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la solicitud de beca
                    nombrearchivo = generar_nombre('cartacompromisoponencia', 'cartacompromisoponencia.pdf')

                    valida = convert_html_to_pdf(
                        'pro_laboratoriocronograma/cartacompromisoponenciapdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento de la carta de compromiso.", "showSwal": "True", "swalType": "error"})

                    # archivo = directorio + "/" + nombrearchivo

                    archivo = 'media/ponencias/cartacompromiso/' + nombrearchivo

                    # return JsonResponse({"result": "ok", "documento": archivo})
                    return JsonResponse({"result": "ok", "documento": archivo})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar carta de compromiso de la solicitud. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'subircartacompromiso':
                try:
                    if 'id' not in request.POST:
                        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                    archivo = request.FILES['archivocarta']
                    descripcionarchivo = 'Archivo Carta de compromiso de ponencia firmada'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    numeropagina = 0
                    # Verifica que el archivo no presente problemas
                    try:
                        pdf2ReaderEvi = PyPDF2.PdfFileReader(archivo)
                        numeropagina = pdf2ReaderEvi.numPages
                    except Exception as ex:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "El archivo presenta problemas", "showSwal": "True", "swalType": "warning"})

                    # Consulto la solicitud de financiamiento de ponencia
                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                    archivo._name = generar_nombre("pcartacompromiso", archivo._name)
                    solicitud.archivocartacompromiso = archivo
                    solicitud.save(request)

                    log(u'%s subió carta de compromiso firmada para la solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'confirmarponencia':
                try:
                    # Consulto la solicitud de ponencia
                    solicitud = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))

                    # Actualizo la solicitud
                    solicitud.confirmada = True
                    solicitud.save(request)

                    # # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                    listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                    # E-mail del destinatario
                    lista_email_envio = persona.lista_emails_envio()
                    # lista_email_envio = ['isaltosm@unemi.edu.ec']
                    lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                    lista_adjuntos = [solicitud.archivocartacompromiso]

                    fechaenvio = datetime.now().date()
                    horaenvio = datetime.now().time()
                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                    tituloemail = "Registro de Solicitud de Financiamiento a Ponencia"
                    tiponotificacion = "REGSOL"
                    titulo = "Postulación y Financiamiento de Ponencias"

                    send_html_mail(tituloemail,
                                   "emails/financiamientoponencia.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                                    'nombrepersona': persona.nombre_completo_inverso(),
                                    'solicitud': solicitud
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    # Notificar por e-mail a la Coordinación de Investigación
                    lista_email_envio = ['investigacion.dip@unemi.edu.ec']
                    # lista_email_envio = ['isaltosm@unemi.edu.ec']

                    tituloemail = "Registro de Solicitud de Financiamiento a Ponencia"
                    tiponotificacion = "REGCOORDINV"

                    send_html_mail(tituloemail,
                                   "emails/financiamientoponencia.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimados',
                                    'nombredocente': persona.nombre_completo_inverso(),
                                    'saludodocente': 'la docente' if persona.sexo_id == 1 else 'el docente',
                                    'solicitud': solicitud
                                    },
                                   lista_email_envio,
                                   lista_email_cco,
                                   lista_adjuntos,
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                    log(u'%s confirmó solicitud de financiamiento a ponencias: %s' % (persona, solicitud), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro de solicitud confirmado con éxito", "showSwal": True})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'deleponencia':
                try:
                    ponencia = PlanificarPonencias.objects.get(pk=int(encrypt(request.POST['id'])))
                    if ponencia.estado != 1:
                        return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar el Registro porque tiene estado %s" % ponencia.get_estado_display()})

                    log(u'Elimino planificación de ponencias:[%s]' % ponencia, request, "del")
                    ponencia.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'delcapacitacion':
                try:
                    planificarcapacitaciones = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))

                    if planificarcapacitaciones.estado != 1 and planificarcapacitaciones.estado != 7:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"No se puede eliminar el Registro porque tiene estado %s" % planificarcapacitaciones.get_estado_display()})

                    log(u'Elimino planificación de capacitacion del docente:[%s]' % planificarcapacitaciones, request, "del")
                    planificarcapacitaciones.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'mostrarmalla':
                try:
                    data['malla'] = malla = Malla.objects.get(pk=int(request.POST['id']))
                    data['idprofesor'] = profesor.id
                    materiaspreferencias = AsignaturaMallaPreferencia.objects.values_list('asignaturamalla').filter(profesor=profesor, periodo=periodo, status=True)
                    data['nivelesdemallas'] = NivelMalla.objects.filter(status=True, pk__in=AsignaturaMalla.objects.values_list('nivelmalla').filter(malla=malla).exclude(pk__in=materiaspreferencias)).order_by('id')
                    # data['asignaturasmallas'] = AsignaturaMalla.objects.filter(malla=malla).exclude(pk__in=materiaspreferencias)
                    data['asignaturasmallas'] = AsignaturaMalla.objects.filter(malla=malla)
                    template = get_template("pro_laboratoriocronograma/mostrarmalla.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'malla': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'informe_seguimiento_anexo':
                mensaje = "Problemas al generar el informe"
                try:
                    materias = []
                    listacarreras = []
                    lista1 = ""
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    profesormateriaparacoordinacion = None
                    hoy = datetime.now().date()
                    profesorseleccionado = Profesor.objects.get(pk=request.POST['profesorid'])
                    profesormateriaparacoordinacion = profesormateria = ProfesorMateria.objects.filter(profesor=profesorseleccionado, tipoprofesor_id=8, materia__nivel__modalidad_id=3, materia__nivel__periodo=periodo, activo=True).exclude(materia__nivel__nivellibrecoordinacion__coordinacion_id=9).distinct().order_by('desde', 'materia__asignatura__nombre')
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
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True, matricula__estado_matricula__in=[2, 3], materia__id__in=profesormateriaparacoordinacion.values_list('materia__id', flat=True)).distinct()
                    distributivo = ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesor, status=True)[0] if ProfesorDistributivoHoras.objects.filter(periodo=periodo, profesor=profesorseleccionado, status=True).exists() else None
                    carreramateriasprofesor = Carrera.objects.filter(status=True, malla__asignaturamalla__materia__materiaasignada__soporteacademicotutor__tutor=profesorseleccionado, malla__asignaturamalla__materia__materiaasignada__status=True, malla__asignaturamalla__materia__materiaasignada__soporteacademicotutor__periodo=periodo, malla__asignaturamalla__materia__materiaasignada__soporteacademicotutor__status=True).distinct().order_by('id').distinct()
                    numero_solicitudes_devuelto = SolicitudTutorSoporteMatricula.objects.filter(fecha_creacion__range=(periodo.inicio, periodo.fin), status=True, matricula__estado_matricula__in=[2, 3], matricula__materiaasignada__soporteacademicotutor__periodo=periodo, matricula__materiaasignada__soporteacademicotutor__tutor=profesorseleccionado, estado=4).distinct().count()
                    numero_solicitudes_tramite = SolicitudTutorSoporteMatricula.objects.filter(fecha_creacion__range=(periodo.inicio, periodo.fin), status=True, matricula__estado_matricula__in=[2, 3], matricula__materiaasignada__soporteacademicotutor__periodo=periodo, matricula__materiaasignada__soporteacademicotutor__tutor=profesorseleccionado, estado=2).distinct().count()
                    numero_solicitudes_cerrado = SolicitudTutorSoporteMatricula.objects.filter(fecha_creacion__range=(periodo.inicio, periodo.fin), status=True, matricula__estado_matricula__in=[2, 3], matricula__materiaasignada__soporteacademicotutor__periodo=periodo, matricula__materiaasignada__soporteacademicotutor__tutor=profesorseleccionado, estado=3).distinct().count()
                    numero_solicitudes_solicitado = SolicitudTutorSoporteMatricula.objects.filter(fecha_creacion__range=(periodo.inicio, periodo.fin), status=True, matricula__estado_matricula__in=[2, 3], matricula__materiaasignada__soporteacademicotutor__periodo=periodo, matricula__materiaasignada__soporteacademicotutor__tutor=profesorseleccionado, estado=1).distinct().count()

                    return conviert_html_to_pdf('pro_tutoria/informe_seguimiento_virtual.html', {'pagesize': 'A4',
                                                                                                 'data': {
                                                                                                     'profesor': profesorseleccionado,
                                                                                                     'periodo': periodo,
                                                                                                     'fechaactual': hoy,
                                                                                                     'fini': periodo.inicio,
                                                                                                     'ffin': periodo.fin,
                                                                                                     'inicio': periodo.inicio,
                                                                                                     'fin': periodo.fin,
                                                                                                     'coordinacion': coordinacion,
                                                                                                     'distributivo': distributivo,
                                                                                                     'materias': materias,
                                                                                                     'materias_soporte': carreramateriasprofesor,
                                                                                                     'numero_solicitudes_devuelto': numero_solicitudes_devuelto,
                                                                                                     'numero_solicitudes_tramite': numero_solicitudes_tramite,
                                                                                                     'numero_solicitudes_cerrado': numero_solicitudes_cerrado,
                                                                                                     'numero_solicitudes_solicitado': numero_solicitudes_solicitado
                                                                                                 }
                                                                                                 })
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al generar el pdf."})

            elif action == 'mostrarmallaposgrado':
                try:
                    data['hoy'] = datetime.now().date()
                    data['malla'] = malla = Malla.objects.get(pk=int(request.POST['id']))
                    data['idperiodo'] = idperiodo = Periodo.objects.get(pk=int(request.POST['idperiodo']))
                    materiaspreferencias = AsignaturaMallaPreferenciaPosgrado.objects.values_list('asignaturamalla').filter(profesor=profesor, periodo=idperiodo, status=True)
                    data['nivelesdemallas'] = NivelMalla.objects.filter(status=True, pk__in=AsignaturaMalla.objects.values_list('nivelmalla').filter(malla=malla).exclude(pk__in=materiaspreferencias)).order_by('id')
                    data['asignaturasmallas'] = AsignaturaMalla.objects.filter(malla=malla).exclude(pk__in=materiaspreferencias)
                    template = get_template("pro_laboratoriocronograma/mostrarmallaposgrado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'malla': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'mostrarseleccionadas':
                try:
                    fecha = datetime.now().date()
                    if (fecha >= periodo.preferencia_inicio and fecha <= periodo.preferencia_final):
                        data['accesopreferencia'] = True
                    else:
                        data['accesopreferencia'] = False
                    data['asignaturaspreferencias'] = materiaspreferencias = AsignaturaMallaPreferencia.objects.filter(profesor=profesor, periodo=periodo, status=True)
                    data['totalpreferencia'] = materiaspreferencias.count()
                    data['asignaturasprofesor'] = profesor.asignatura.all()
                    template = get_template("pro_laboratoriocronograma/mostrarseleccionadas.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'malla': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'mostrarseleccionadasposgrado':
                try:
                    data['periodo'] = periodo = request.session['periodo']
                    data['profesor'] = profesor
                    tieneprerenciaposgrado = False
                    if profesor.asignaturamallapreferenciaposgrado_set.filter(status=True):
                        tieneprerenciaposgrado = True
                    data['tieneprerenciaposgrado'] = tieneprerenciaposgrado
                    data['asignaturaspreferencias'] = materiaspreferencias = AsignaturaMallaPreferenciaPosgrado.objects.filter(profesor=profesor, status=True)
                    data['totalpreferencia'] = materiaspreferencias.count()
                    template = get_template("pro_laboratoriocronograma/mostrarseleccionadasposgrado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'malla': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'horariopreferencias':
                try:
                    fecha = datetime.now().date()
                    if not (fecha >= periodo.inicioprehorario and fecha <= periodo.finprehorario):
                        return JsonResponse({"result": "bad", "mensaje": "No se puede seleccionar ya que el periodo termino."})
                    id = None
                    if not HorarioPreferencia.objects.filter(profesor=profesor, periodo=periodo, turno_id=int(request.POST['turno']), dia=int(request.POST['dia'])).exists():
                        horariopreferencia = HorarioPreferencia(profesor=profesor,
                                                                periodo=periodo,
                                                                turno_id=int(request.POST['turno']),
                                                                dia=int(request.POST['dia']))
                        horariopreferencia.save(request)
                        id = horariopreferencia.id
                    else:
                        HorarioPreferencia.objects.filter(profesor=profesor, periodo=periodo, turno_id=int(request.POST['turno']), dia=int(request.POST['dia'])).delete()
                    return JsonResponse({"result": "ok", 'id': id})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'horariopreferenciasobse':
                try:
                    fecha = datetime.now().date()
                    if not (fecha >= periodo.inicioprehorario and fecha <= periodo.finprehorario):
                        return JsonResponse({"result": "bad", "mensaje": "No se puede seleccionar ya que el periodo termino."})
                    if not HorarioPreferenciaObse.objects.filter(profesor=profesor, periodo=periodo).exists():
                        horariopreferencia = HorarioPreferenciaObse(profesor=profesor,
                                                                    periodo=periodo,
                                                                    observacion=request.POST['obse'])
                    else:
                        horariopreferencia = HorarioPreferenciaObse.objects.filter(profesor=profesor, periodo=periodo)[0]
                        horariopreferencia.observacion = request.POST['obse']
                    horariopreferencia.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'addproductoinvestigacionarticulo':
                try:
                    f = ArticuloInvestigacionDocenteForm(request.POST)
                    detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['detalledistributivo'])), distributivo__profesor=profesor, status=True)
                    if f.is_valid():
                        articulo = ArticuloInvestigacionDocente(detalledistributivo=detalledistributivo,
                                                                tematica=f.cleaned_data['tematica'],
                                                                revista=f.cleaned_data['revista'],
                                                                metodologia=f.cleaned_data['metodologia'],
                                                                estado=1, horas=f.cleaned_data['horas']
                                                                )
                        articulo.save(request)
                        log(u'Adiciono nuevo articulo investigacion: %s' % profesor, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addproductoinvestigacionponencia':
                try:
                    f = PonenciaInvestigacionDocenteForm(request.POST)
                    detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['detalledistributivo'])), distributivo__profesor=profesor, status=True)
                    if f.is_valid():
                        ponencia = PonenciaInvestigacionDocente(detalledistributivo=detalledistributivo,
                                                                tematica=f.cleaned_data['tematica'],
                                                                congreso=f.cleaned_data['congreso'],
                                                                estado=1,
                                                                horas=f.cleaned_data['horas']
                                                                )
                        ponencia.save(request)
                        log(u'Adiciono nuevoa ponencia investigacion: %s' % profesor, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addproductoinvestigacionlibro':
                try:
                    f = LibroInvestigacionDocenteForm(request.POST)
                    detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['detalledistributivo'])), distributivo__profesor=profesor, status=True)
                    if f.is_valid():
                        libro = LibroInvestigacionDocente(detalledistributivo=detalledistributivo,
                                                          nombre=f.cleaned_data['nombre'], estado=1, horas=f.cleaned_data['horas']
                                                          )
                        libro.save(request)
                        log(u'Adiciono nuevo libro investigacion: %s' % profesor, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addproductoinvestigacioncapitulolibro':
                try:
                    f = CapituloLibroInvestigacionDocenteForm(request.POST)
                    detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.POST['detalledistributivo'])), distributivo__profesor=profesor, status=True)
                    if f.is_valid():
                        capitulolibro = CapituloLibroInvestigacionDocente(detalledistributivo=detalledistributivo,
                                                                          nombre=f.cleaned_data['nombre'], estado=1, horas=f.cleaned_data['horas']
                                                                          )
                        capitulolibro.save(request)
                        log(u'Adiciono nuevo capitulo libro investigacion: %s' % profesor, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editarproductoarticulo':
                try:
                    articulo = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['articulo'])))
                    f = ArticuloInvestigacionDocenteForm(request.POST)
                    if f.is_valid():
                        articulo.tematica = f.cleaned_data['tematica']
                        articulo.revista = f.cleaned_data['revista']
                        articulo.metodologia = f.cleaned_data['metodologia']
                        articulo.horas = f.cleaned_data['horas']
                        if articulo.estado == 3:
                            articulo.estado = 1
                        articulo.save(request)
                        log(u'Modificó articulo investigacion: %s' % profesor, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editarproductoponencia':
                try:
                    ponencia = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['ponencia'])))
                    f = PonenciaInvestigacionDocenteForm(request.POST)
                    if f.is_valid():
                        ponencia.tematica = f.cleaned_data['tematica']
                        ponencia.congreso = f.cleaned_data['congreso']
                        if ponencia.estado == 3:
                            ponencia.estado = 1
                        ponencia.horas = f.cleaned_data['horas']
                        ponencia.save(request)
                        log(u'Modificó ponencia investigacion: %s' % profesor, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editarproductolibro':
                try:
                    libro = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['libro'])))
                    f = LibroInvestigacionDocenteForm(request.POST)
                    if f.is_valid():
                        libro.nombre = f.cleaned_data['nombre']
                        if libro.estado == 3:
                            libro.estado = 1
                        libro.horas = f.cleaned_data['horas']
                        libro.save(request)
                        log(u'Modificó libro investigacion: %s' % profesor, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editarproductocapitulolibro':
                try:
                    capitulolibro = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['capitulolibro'])))
                    f = CapituloLibroInvestigacionDocenteForm(request.POST)
                    if f.is_valid():
                        capitulolibro.nombre = f.cleaned_data['nombre']
                        if capitulolibro.estado == 3:
                            capitulolibro.estado = 1
                        capitulolibro.horas = f.cleaned_data['horas']
                        capitulolibro.save(request)
                        log(u'Modificó capitulo libro investigacion: %s' % profesor, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delproductoarticulo':
                try:
                    articulo = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    if articulo.en_uso():
                        return JsonResponse({"result": "bad", "mensaje": u"El articulo se encuentra en uso, no es posible eliminar."})
                    log(u'Eliminó proveedor: %s' % articulo, request, "del")
                    articulo.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'delproductoponencia':
                try:
                    ponencia = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    if ponencia.en_uso():
                        return JsonResponse({"result": "bad", "mensaje": u"La ponencia se encuentra en uso, no es posible eliminar."})
                    log(u'Eliminó ponencia: %s' % ponencia, request, "del")
                    ponencia.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'delproductolibro':
                try:
                    libro = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    if libro.en_uso():
                        return JsonResponse({"result": "bad", "mensaje": u"El libro se encuentra en uso, no es posible eliminar."})
                    log(u'Eliminó libro: %s' % libro, request, "del")
                    libro.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'delproductocapitulolibro':
                try:
                    capitulolibro = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    if capitulolibro.en_uso():
                        return JsonResponse({"result": "bad", "mensaje": u"El capitulo libro se encuentra en uso, no es posible eliminar."})
                    log(u'Eliminó capitulolibro: %s' % capitulolibro, request, "del")
                    capitulolibro.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'addcronogramaproducto':
                try:
                    f = CronogramaTrabajoInvestigacionDocenteForm(request.POST)
                    if f.is_valid():
                        data['tipo'] = tipo = int(request.POST['tipo'])
                        cronograma = None
                        if tipo == 1:
                            producto = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                            cronograma = CronogramaTrabajoInvestigacionDocente(articulo=producto,
                                                                               fechainicio=f.cleaned_data['fechainicio'],
                                                                               fechafin=f.cleaned_data['fechafin'],
                                                                               actividad=f.cleaned_data['actividad'],
                                                                               )
                            cronograma.save(request)
                        elif tipo == 2:
                            producto = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                            cronograma = CronogramaTrabajoInvestigacionDocente(ponencia=producto,
                                                                               fechainicio=f.cleaned_data['fechainicio'],
                                                                               fechafin=f.cleaned_data['fechafin'],
                                                                               actividad=f.cleaned_data['actividad'],
                                                                               )
                            cronograma.save(request)
                        elif tipo == 3:
                            producto = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                            cronograma = CronogramaTrabajoInvestigacionDocente(libro=producto,
                                                                               fechainicio=f.cleaned_data['fechainicio'],
                                                                               fechafin=f.cleaned_data['fechafin'],
                                                                               actividad=f.cleaned_data['actividad'],
                                                                               )
                            cronograma.save(request)
                        else:
                            producto = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                            cronograma = CronogramaTrabajoInvestigacionDocente(capitulolibro=producto,
                                                                               fechainicio=f.cleaned_data['fechainicio'],
                                                                               fechafin=f.cleaned_data['fechafin'],
                                                                               actividad=f.cleaned_data['actividad'],
                                                                               )
                        if cronograma:
                            if producto.estado == 3:
                                producto.estado = 1
                                producto.save(request)
                            cronograma.save(request)
                        log(u'Adiciono cronograma de producto: %s' % profesor, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editcronogramaproducto':
                try:
                    f = CronogramaTrabajoInvestigacionDocenteForm(request.POST)
                    if f.is_valid():
                        cronograma = CronogramaTrabajoInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                        if cronograma.articulo:
                            if cronograma.articulo.estado == 3:
                                cronograma.articulo.estado = 1
                                cronograma.articulo.save(request)
                        elif cronograma.ponencia:
                            if cronograma.ponencia.estado == 3:
                                cronograma.ponencia.estado = 1
                                cronograma.ponencia.save(request)
                        elif cronograma.libro:
                            if cronograma.libro.estado == 3:
                                cronograma.libro.estado = 1
                                cronograma.libro.save(request)
                        elif cronograma.capitulolibro:
                            if cronograma.capitulolibro.estado == 3:
                                cronograma.capitulolibro.estado = 1
                                cronograma.capitulolibro.save(request)
                        cronograma.fechainicio = f.cleaned_data['fechainicio']
                        cronograma.fechafin = f.cleaned_data['fechafin']
                        cronograma.actividad = f.cleaned_data['actividad']
                        cronograma.save(request)
                        log(u'Modificó cronograma producto investigacion: %s' % cronograma, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delcronogramaproducto':
                try:
                    cronograma = CronogramaTrabajoInvestigacionDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    log(u'Eliminó cronograma producto investigacion: %s' % cronograma, request, "del")
                    cronograma.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'imprimirproductopdf':
                try:
                    distributivo = profesor.distributivohoraseval(periodo)
                    decano = None
                    director = None
                    if distributivo:
                        decano = distributivo.coordinacion.responsable_periododos(periodo, 1)
                        director = distributivo.carrera.coordinador(periodo, distributivo.coordinacion.sede)
                    return conviert_html_to_pdf('pro_laboratoriocronograma/imprimirproductopdf.html',
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

            elif action == 'informe_autor':
                mensaje = "Problemas al generar el informe"
                try:
                    paralelos = []
                    carreras = []
                    listacarreras = []
                    coord = 0
                    suma = 0
                    coordinacion = None
                    profesormateria = None
                    finio = request.POST['fini']
                    ffino = request.POST['ffin']
                    idmateria = int(encrypt(request.POST['idmateriaaautor']))
                    materia = Materia.objects.filter(status=True, id=idmateria)
                    finic = convertir_fecha(finio)
                    ffinc = convertir_fecha(ffino)
                    idmaterias = ProfesorMateria.objects.values_list('materia__id').filter(profesor=profesor, tipoprofesor__id=9, materia__nivel__periodo=periodo, activo=True).distinct()
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
                    return conviert_html_to_pdf('pro_laboratoriocronograma/informe_seguimiento_autor.html', {'pagesize': 'A4',
                                                                                                  'data': {'distributivo': distributivo,
                                                                                                           'periodo': periodo,
                                                                                                           'fini': finio,
                                                                                                           'ffin': ffino,
                                                                                                           'finic': finic, 'carreras': carreras,
                                                                                                           'ffinc': ffinc, 'suma': suma, 'materia1': materia[0],
                                                                                                           'materiasg': materia, 'paralelos': paralelos,
                                                                                                           'titulaciones': titulaciones}})
                except Exception as ex:
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % mensaje)

            elif action == 'aceptapreferenciaasignaturaposgrado':
                try:
                    if profesor.preferenciadocente_set.values('id').filter(status=True, tipopreferencia=4).exists():
                        dato = PreferenciaDocente.objects.get(profesor=profesor, tipopreferencia=4)
                        dato.delete()
                    else:
                        dato = PreferenciaDocente(status=True, profesor=profesor, tipopreferencia=4, fecha=datetime.now())
                        dato.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'data_inquietudconsultaestudiante':
                try:
                    inquietud = InquietudPracticasPreprofesionales.objects.get(pk=int(encrypt(request.POST['mid'])))
                    inquietud.visto = True
                    inquietud.save(request)
                    if inquietud.respuestainquitudpracticaspreprofesionales_set.filter(status=True).exists():
                        respuesta = inquietud.respuestainquitudpracticaspreprofesionales_set.filter(status=True).order_by("id")[0]
                        respuesta.respuesta = request.POST['vc']
                        respuesta.persona = persona
                        respuesta.save(request)
                        log(u'Modificó respuesta de una inquetud por parte del profesor: %s' % respuesta, request, "edit")
                    else:
                        respuesta = RespuestaInquitudPracticasPreprofesionales(inquietud=inquietud, persona=persona,
                                                                               respuesta=request.POST['vc'])
                        respuesta.save(request)
                        log(u'Adiciono respuesta de una inquetud por parte del profesor: %s' % respuesta, request, "add")

                    asunto = u"RESPUESTA INQUIETUD DE PRÁCTICAS PRE PROFESIONALES"
                    para = inquietud.practica.inscripcion.persona
                    observacion = 'Acceder a inquietudes para responder.'
                    notificacion(asunto, observacion, para, None, '/alu_practicaspro?action=inquietudconsultaestudiante&id_practica={}'.format(encrypt_alu(inquietud.practica.pk)), inquietud.practica.pk, 1, 'sga', InquietudPracticasPreprofesionales, request)

                    return JsonResponse({"result": "ok", "valor": respuesta.respuesta})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cambiar la respuesta."})

            elif action == 'data_inquietudconsultaestudianteobservacion':
                try:
                    inquietud = InquietudPracticasPreprofesionales.objects.get(pk=int(encrypt(request.POST['mid'])))
                    inquietud.observacion = request.POST['vc']
                    inquietud.save(request)
                    log(u'Modificó observacion de una inquetud por parte del profesor: %s' % inquietud, request, "edit")

                    return JsonResponse({"result": "ok", "valor": inquietud.observacion})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cambiar la respuesta."})

            elif action == 'addtutoria':
                try:
                    fecha = convertir_fecha(encrypt(request.POST['dia']) + '-' + encrypt(request.POST['mes']) + '-' + encrypt(request.POST['anio']))
                    listatutorias = PracticasTutoria.objects.filter(fechainicio=fecha, fechafin=fecha, practica__tutorunemi=profesor, status=True).values_list('practica_id', flat=True)
                    data['estudiantes'] = estudiantes = PracticasPreprofesionalesInscripcion.objects.filter(status=True,
                                                                                                            culminatutoria=False,
                                                                                                            culminada=False,
                                                                                                            tutorunemi=perfilprincipal.profesor,
                                                                                                            tipo__in=[1, 2]).exclude(estadosolicitud=3).exclude(pk__in=listatutorias)

                    template = get_template("pro_laboratoriocronograma/modaltutorias.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'titulo': 'Lista de tutorias', "data": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'edittutoria':
                try:
                    data['titulo'] = 'Editar Tutorias'
                    fecha = convertir_fecha(encrypt(request.POST['dia']) + '-' + encrypt(request.POST['mes']) + '-' + encrypt(request.POST['anio']))
                    data['estudiantes'] = estudiantes = PracticasTutoria.objects.filter(fechainicio=fecha, fechafin=fecha, practica__tutorunemi=profesor, status=True).order_by('pk')
                    template = get_template("pro_laboratoriocronograma/modaltutoriasedit.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'titulo': 'Lista de tutorias', "data": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'culminartutoria':
                try:
                    practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.POST['id']))
                    if practica.culminatutoria:
                        practica.culminatutoria = False
                    else:
                        practica.culminatutoria = True
                        practica.fechaculminacion = datetime.now()
                    practica.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            if action == 'reemplazardocumentoinquietud':
                try:
                    with transaction.atomic():
                        form = ReemplazarInquietudForm(request.POST, request.FILES)
                        if form.is_valid():
                            filtro = InquietudPracticasPreprofesionales.objects.get(pk=request.POST['id'])
                            if 'archivo' in request.FILES:
                                nfile = request.FILES['archivo']
                                nombre_persona = remover_caracteres_especiales_unicode(filtro.practica.preinscripcion.inscripcion.persona.apellido1).lower().replace(' ', '_')
                                nfile._name = generar_nombre("inquietud_{}".format(nombre_persona), nfile._name)
                                filtro.archivo = nfile
                            filtro.save(request)
                            log(u'Reemplazo Documento Estudiante, Inquietud: %s' % filtro, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."},
                                                safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'addasesoramientossee':
                try:
                    with transaction.atomic():
                        form = AsesoramientoSEEForm(request.POST)
                        if not form.is_valid():
                            # [(k, v[0]) for k, v in f.errors.items()]
                            for k, v in form.errors.items():
                                raise NameError(v[0])

                        solicitud = AsesoramientoSEE(
                            periodo=periodo,
                            persona=persona,
                            titulo=form.cleaned_data['titulo'],
                            tipotrabajo=form.cleaned_data['tipotrabajo'],
                            descripcion=form.cleaned_data['descripcion'],
                            coordinacion=form.cleaned_data['coordinacion'],
                            carrera=form.cleaned_data['carrera'],
                            fechaatencion=form.cleaned_data['fechaatencion'],
                            horaatencion=form.cleaned_data['horaatencion'],
                        )
                        solicitud.save(request)
                        log(u'Adiciono Solicitud de Asesoramiento de Servicios de Estudios Estadísticos : %s' % solicitud, request, "add")
                        grupo_centro_estadistico = Group.objects.filter(pk=variable_valor('CENTRO_ESTUDIOS_ESTADISTICOS_GROUP_ID'))
                        if grupo_centro_estadistico:
                            correos = Persona.objects.filter(usuario__groups__in=grupo_centro_estadistico).values_list('emailinst', flat=True)
                            titulo = "Tiene una nueva solicitud de asesoramiento pendiente del Centro de Gestión de Estudios Estadísticos .!"
                            send_html_mail(titulo,
                                           "pro_laboratoriocronograma/emails/notificacionsolicitudemail.html",
                                           {'sistema': request.session['nombresistema'], 'registro': solicitud,
                                            't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, list(correos), [],
                                           cuenta=CUENTAS_CORREOS[0][1])
                        return JsonResponse({"result": True, 'mensaje': u'Solicitud creada correctamente'}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            if action == 'editasesoramientossee':
                try:
                    with transaction.atomic():
                        form = AsesoramientoSEEForm(request.POST)
                        if not form.is_valid():
                            # [(k, v[0]) for k, v in f.errors.items()]
                            for k, v in form.errors.items():
                                raise NameError(f'{k} {v[0]}')

                        solictudanterior = AsesoramientoSEE.objects.get(id=request.POST['id'])
                        solicitud = AsesoramientoSEE.objects.get(id=request.POST['id'])
                        solicitud.periodo = periodo
                        solicitud.persona = persona
                        solicitud.titulo = form.cleaned_data['titulo']
                        solicitud.tipotrabajo = form.cleaned_data['tipotrabajo']
                        solicitud.descripcion = form.cleaned_data['descripcion']
                        solicitud.coordinacion = form.cleaned_data['coordinacion']
                        solicitud.carrera = form.cleaned_data['carrera']
                        solicitud.fechaatencion = form.cleaned_data['fechaatencion']
                        solicitud.horaatencion = form.cleaned_data['horaatencion']

                        solicitud.save(request)
                        log(u'Edito Solicitud de Asesoramiento de Servicios de Estudios Estadísticos : %s' % solicitud, request, "edit")
                        grupo_centro_estadistico = Group.objects.filter(pk=variable_valor('CENTRO_ESTUDIOS_ESTADISTICOS_GROUP_ID'))
                        if grupo_centro_estadistico:
                            correos = Persona.objects.filter(usuario__groups__in=grupo_centro_estadistico).values_list('emailinst', flat=True)
                            titulo = f"Modificó solicitud de Asesoramiento Estudio Estadisticos  el docente {solicitud.persona} !"
                            send_html_mail(titulo,
                                           "pro_laboratoriocronograma/emails/notificacionsolicitudmodificadaemail.html",
                                           {'sistema': request.session['nombresistema'], 'registro': solicitud,
                                            'registroanterior': solictudanterior,
                                            't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, list(correos), [],
                                           cuenta=CUENTAS_CORREOS[0][1])
                        return JsonResponse({"result": True, 'mensaje': u'Solicitud editada correctamente'}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            if action == 'delasesoramientossee':
                try:
                    asesoramiento = AsesoramientoSEE.objects.get(pk=request.POST['id'])
                    asesoramiento.status = False
                    asesoramiento.save(request)
                    log(u'Eliminó Asesoramiento de Estudio Estadisticos: %s' % asesoramiento, request, "del")
                    grupo_centro_estadistico = Group.objects.filter(pk=variable_valor('CENTRO_ESTUDIOS_ESTADISTICOS_GROUP_ID'))
                    if grupo_centro_estadistico:
                        correos = Persona.objects.filter(usuario__groups__in=grupo_centro_estadistico).values_list('emailinst', flat=True)
                        titulo = f"Eliminó solicitud de Asesoramiento Estudio Estadisticos el docente {asesoramiento.persona} !"
                        send_html_mail(titulo,
                                       "pro_laboratoriocronograma/emails/notificacionsolicitudeliminadaemail.html",
                                       {'sistema': request.session['nombresistema'], 'registro': asesoramiento,
                                        't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, list(correos), [],
                                       cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": "ok", 'mensaje': u'Registro eliminado correctamente.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            ## Actualizar fecha de inicio de practicas por el supervisor

            if action == 'editfecha':
                try:
                    id = request.POST['id']
                    valor = request.POST['valor']
                    fecha_ = convertirfecha2(valor) + timedelta(days=1)
                    practica = PracticasPreprofesionalesInscripcion.objects.get(id=id)
                    practica.fechadesde = fecha_
                    practica.save(request)
                    log(u'Modificó fecha de inicio de practicas : %s' % practica, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as e:
                    print(e)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": str(e)})

            if action == 'editfecha2':
                try:
                    id = request.POST['id']
                    valor = request.POST['valor']
                    fecha_ = convertirfecha2(valor) + timedelta(days=1)
                    practica = PracticasPreprofesionalesInscripcion.objects.get(id=id)
                    practica.fechahasta = fecha_
                    practica.save(request)
                    log(u'Modificó fecha de inicio de practicas : %s' % practica, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as e:
                    print(e)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": str(e)})

            if action == 'addhorariotutoria':
                try:
                    iddia = int(request.POST['iddia'])
                    idturno = int(request.POST['idturno'])
                    turno = Turno.objects.get(id=idturno)
                    suma = 0
                    sumaactividad = int(request.POST['sumaactividad'])
                    if not HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo, dia=iddia, turno=turno).exists():
                        if HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                            suma = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo).aggregate(total=Sum('turno__horas'))['total']
                        # if DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                        #                                       distributivo__periodo=periodo,
                        #                                       criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                        #     sumaactividad = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                        #                                                        distributivo__periodo=periodo,
                        #                                                        criteriodocenciaperiodo__criterio_id__in=[7]).aggregate(total=Sum('horas'))['total']

                        if int(suma) < int(sumaactividad):
                            horario = HorarioTutoriaPacticasPP(profesor=profesor, periodo=periodo, dia=iddia, turno=turno)
                            horario.save(request)
                            log(u'Ingreso un horario de tutoría de Practicas PP: %s' % horario, request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Ya cumple con sus horas de tutoria de practicas planificada."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un horario ingresado."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'buscarturnos':
                try:
                    dia = int(request.POST['dia'])
                    if periodo.tipo_id in [3, 4] or periodo.es_posgrado():
                        turnosadd = Turno.objects.filter(status=True, sesion_id__in=[19, 15]).order_by('comienza')
                    else:
                        turnosparatutoria = Turno.objects.filter(status=True, sesion_id=15).distinct().order_by('comienza')
                        idturnos = []
                        idturnoscomplexivo = []
                        idturnoactividades = []
                        idturnostutoria = []
                        idturnostutoriapracticaspp = []
                        idmatriculas = []
                        idmaterias_matricula = []
                        idturnos_matricula = []
                        profesormaterias = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo, activo=True).distinct()
                        idmaterias = profesormaterias.values_list('materia_id')

                        for profemate in profesormaterias:
                            idmatriculas += MateriaAsignada.objects.values_list('matricula_id').filter(
                                materia=profemate.materia,
                                status=True, estado_id=3,
                                materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(materia__asignaturamalla__malla_id__in=[353, 22]).distinct()
                            idmaterias_matricula = MateriaAsignada.objects.values_list('materia_id').filter(
                                matricula_id__in=idmatriculas,
                                status=True, estado_id=3,
                                materia__asignaturamalla__nivelmalla=profemate.materia.asignaturamalla.nivelmalla).exclude(materia__asignaturamalla__malla_id__in=[353, 22]).distinct().distinct()

                        if Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                                         materia__nivel__periodo=periodo,
                                                                         materia_id__in=idmaterias_matricula, dia=dia).exists():
                            idturnos_matricula = Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                                                               materia__nivel__periodo=periodo,
                                                                                               materia_id__in=idmaterias_matricula,
                                                                                               dia=dia).distinct()

                        if Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                                         materia__nivel__periodo=periodo,
                                                                         materia_id__in=idmaterias, dia=dia).exists():
                            idturnos = Clase.objects.values_list('turno__id').filter(status=True, activo=True,
                                                                                     materia__nivel__periodo=periodo,
                                                                                     materia_id__in=idmaterias, dia=dia).distinct()

                        if ComplexivoClase.objects.values_list('turno__id').filter(activo=True,
                                                                                   materia__profesor__profesorTitulacion=profesor,
                                                                                   materia__status=True, dia=dia).exists():
                            idturnoscomplexivo = ComplexivoClase.objects.values_list('turno__id').filter(activo=True,
                                                                                                         materia__profesor__profesorTitulacion=profesor,
                                                                                                         materia__status=True, dia=dia).distinct()

                        if ClaseActividad.objects.filter(detalledistributivo__distributivo__periodo=periodo,
                                                         detalledistributivo__distributivo__profesor=profesor, dia=dia).exists():
                            idturnoactividades = ClaseActividad.objects.values_list('turno__id').filter(
                                detalledistributivo__distributivo__periodo=periodo,
                                detalledistributivo__distributivo__profesor=profesor, dia=dia).distinct()
                        else:
                            if ClaseActividad.objects.values_list('turno__id').filter(
                                    actividaddetalle__criterio__distributivo__periodo=periodo,
                                    actividaddetalle__criterio__distributivo__profesor=profesor, dia=dia).exists():
                                idturnoactividades = ClaseActividad.objects.values_list('turno__id').filter(
                                    actividaddetalle__criterio__distributivo__periodo=periodo,
                                    actividaddetalle__criterio__distributivo__profesor=profesor, dia=dia).distinct()
                        if HorarioTutoriaAcademica.objects.filter(status=True, dia=dia, profesor=profesor, periodo=periodo).exists():
                            idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, dia=dia, profesor=profesor, periodo=periodo).distinct()
                        if HorarioTutoriaPacticasPP.objects.filter(status=True, dia=dia, profesor=profesor, periodo=periodo).exists():
                            idturnostutoriapracticaspp = HorarioTutoriaPacticasPP.objects.values_list('turno_id').filter(status=True, dia=dia, profesor=profesor, periodo=periodo).distinct()
                        turnoclases = Turno.objects.filter(Q(id__in=idturnos) |
                                                           Q(id__in=idturnoscomplexivo) |
                                                           Q(id__in=idturnoactividades) |
                                                           Q(id__in=idturnostutoria) |
                                                           Q(id__in=idturnos_matricula) |
                                                           Q(id__in=idturnostutoriapracticaspp)
                                                           ).distinct().order_by('comienza')

                        idturnosadd = []
                        for turnotutoria in turnosparatutoria:
                            for turnoclase in turnoclases:
                                if turnotutoria.comienza <= turnoclase.termina and turnotutoria.termina >= turnoclase.comienza:
                                    idturnosadd.append(turnotutoria.id)

                        turnosadd = Turno.objects.filter(status=True, sesion_id=15).exclude(id__in=idturnosadd).distinct().order_by('comienza')
                    lista = []
                    for turno in turnosadd:
                        lista.append([turno.id, u'Turno %s [%s a %s]' % (str(turno.turno), turno.comienza.strftime("%H:%M %p"), turno.termina.strftime("%H:%M %p"))])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'delhorario':
                try:
                    horario = HorarioTutoriaPacticasPP.objects.get(id=int(encrypt(request.POST['id'])))
                    exed = True if 'max' in request.POST and request.POST['max'] == '1' else False
                    # if horario.en_uso() and not exed:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Ya existen horario creado."})
                    horario.status = False
                    horario.save(request)
                    log(u'Eliminó un horario de tutoría de practicas pp: %s' % horario, request, "add")
                    return JsonResponse({"error": False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addbitacora':
                try:
                    persona = request.session['persona']
                    bitacoradocente = BitacoraActividadDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = BitacoraActividadForm(request.POST, bitacora=bitacoradocente)
                    hi = request.POST['hora'] if 'hora' in request.POST else ''
                    hf = request.POST['horafin'] if 'horafin' in request.POST else ''

                    if hi and hf:
                        h1 = timedelta(hours=int(hi.split(':')[0]), minutes=int(hi.split(':')[1]))
                        h2 = timedelta(hours=int(hf.split(':')[0]), minutes=int(hf.split(':')[1]))
                        if h2 <= h1:
                            return JsonResponse({"result": "bad", "mensaje": "Hora fin no puede ser menor o igual que hora inicio."})
                        total = f"{h2 - h1}"
                        if int(total.split(':')[0]) == 0 and int(total.split(':')[1]) < 59:
                            return JsonResponse({"result": "bad", "mensaje": "La duración de la actividad debe ser mayor a 59 minutos."})

                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            newfilesd = newfile._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if newfile.size > 12582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            if newfile:
                                newfile._name = generar_nombre("bitacora", newfile._name)

                    fechapost = request.POST['fecha']
                    fechapost = datetime.strptime(fechapost, '%Y-%m-%d').date()
                    if bitacoradocente.fechaini.date() <= fechapost <= bitacoradocente.fechafin.date():
                        if form.is_valid():
                            detallebitacora = DetalleBitacoraDocente(bitacoradocente=bitacoradocente,
                                                                     titulo=form.cleaned_data.get('titulo'),
                                                                     fecha=form.cleaned_data.get('fecha'),
                                                                     fechafin=form.cleaned_data.get('fechafin'),
                                                                     horainicio=form.cleaned_data.get('hora'),
                                                                     horafin=form.cleaned_data.get('horafin'),
                                                                     descripcion=u'%s' % form.cleaned_data['descripcion'],
                                                                     link=form.cleaned_data.get('link'),
                                                                     archivo=newfile)
                            detallebitacora.save(request)
                            listadepartamento = form.cleaned_data.get('departamento', [])
                            for depa in listadepartamento:
                                departamentobitacora = DepartamentoBitacora(detallebitacora=detallebitacora, departamento=depa)
                                departamentobitacora.save(request)
                            listadopersona = form.cleaned_data.get('persona', [])
                            for lperso in listadopersona:
                                personabitacora = PersonaBitacora(detallebitacora=detallebitacora, persona=lperso)
                                personabitacora.save(request)

                            nfilas_ca_evi = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []
                            nfilas_evi = request.POST.getlist('nfila_evidencia[]')
                            descripciones_evi = request.POST.getlist('descripcion_evidencia[]')
                            archivos_evi = request.FILES.getlist('archivo_evidencia[]')

                            for nfila, archivo in zip(nfilas_ca_evi, archivos_evi):
                                descripcionarchivo = 'Evidencia'
                                resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                                if resp['estado'] != "OK":
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"] + " en la fila # " + str(nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                            # Guardar evidencias de informe
                            for nfila, descripcion in zip(nfilas_evi, descripciones_evi):
                                anexoevidencia = AnexoDetalleBitacoraDocente(detallebitacoradocente=detallebitacora, observacion=descripcion.strip())
                                anexoevidencia.save(request)
                                # Guardo el archivo del formato
                                for nfilaarchi, archivo in zip(nfilas_ca_evi, archivos_evi):
                                    # Si la fila de la descripcion es igual a la fila que contiene archivo
                                    if int(nfilaarchi['nfila']) == int(nfila):
                                        archivoreg = archivo
                                        archivoreg._name = generar_nombre("anexo_bitacora_", archivoreg._name)
                                        anexoevidencia.archivo = archivoreg
                                        anexoevidencia.save(request)
                                        break
                            log(u'Adicinó anexo en bitacora de actividades docente %s' % detallebitacora, request, "add")
                            log(u'Adicionó bitacora de actividades docente %s' % (detallebitacora), request, "add")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": f"Favor ingresar una fecha que se encuentre en el rango desde {bitacoradocente.fechaini.strftime('%d/%m/%Y')} hasta {bitacoradocente.fechafin.strftime('%d/%m/%Y')}"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editbitacora':
                try:
                    bitacoradocente = DetalleBitacoraDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = BitacoraActividadForm(request.POST, bitacora=bitacoradocente.bitacoradocente)
                    hi = request.POST['hora'] if 'hora' in request.POST else ''
                    hf = request.POST['horafin'] if 'horafin' in request.POST else ''

                    if hi and hf:
                        if hf <= hi:
                            return JsonResponse({"result": "bad", "mensaje": "Hora fin no puede ser menor o igual a hora inicio."})
                        h1 = timedelta(hours=int(hi.split(':')[0]), minutes=int(hi.split(':')[1]))
                        h2 = timedelta(hours=int(hf.split(':')[0]), minutes=int(hf.split(':')[1]))
                        total = f"{h2 - h1}"
                        if int(total.split(':')[0]) == 0 and int(total.split(':')[1]) < 59:
                            return JsonResponse({"result": "bad", "mensaje": "La duración de la actividad debe ser mayor a 59 minutos."})
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            if newfile.size > 20971520:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                newfile._name = generar_nombre("bitacora", newfile._name)

                    if f.is_valid():
                        listadepar = []
                        bitacoradocente.titulo = f.cleaned_data.get('titulo')
                        bitacoradocente.fecha = f.cleaned_data.get('fecha')
                        bitacoradocente.horainicio = f.cleaned_data.get('hora')
                        bitacoradocente.horafin = f.cleaned_data.get('horafin')
                        bitacoradocente.descripcion = f.cleaned_data.get('descripcion')
                        bitacoradocente.link = f.cleaned_data.get('link')
                        if newfile:
                            bitacoradocente.archivo = newfile
                        bitacoradocente.save(request)
                        listadepartamento = f.cleaned_data.get('departamento', [])
                        listadepar = [o.pk for o in listadepartamento]
                        departamentoseliminados = DepartamentoBitacora.objects.filter(detallebitacora=bitacoradocente).exclude(departamento_id__in=listadepar)
                        departamentoseliminados.delete()
                        for depa in listadepartamento:
                            if not DepartamentoBitacora.objects.filter(detallebitacora=bitacoradocente, departamento=depa):
                                departamentobitacora = DepartamentoBitacora(detallebitacora=bitacoradocente, departamento=depa)
                                departamentobitacora.save(request)

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            if action == 'addpersonabitacora':
                f = UsuarioRevisaEvidenciaDocenteForm(request.POST)
                f.ocultar_campo('rol')
                if f.is_valid():
                    try:
                        perbitacora = PersonaBitacora(detallebitacora_id=int(request.POST['id']),
                                                      persona_id=request.POST['personarevisa'])
                        perbitacora.save(request)
                        return JsonResponse({"result": "ok"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            if action == 'deletedetallebitacora':
                try:
                    criterio = DetalleBitacoraDocente.objects.get(id=request.POST['id'], status=True)
                    criterio.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            if action == 'ejecutarinformemensual':
                try:
                    fechaini = convertir_fecha(request.POST['fini'])
                    fechafin = convertir_fecha(request.POST['ffin'])
                    distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['id'])
                    qrname = 'informemensual_' + str(distributivo.id) + '_' + str(fechafin.month)
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', ''))
                    os.makedirs(folder, exist_ok=True)
                    generainforme = html_to_pdfsave_informemensualdocente('adm_criteriosactividadesdocente/informe_actividad_docentev4_pdf.html',
                                                                          {'pagesize': 'A4',
                                                                           'data': profesor.informe_actividades_mensual_docente_v4(periodo, request.POST['fini'], request.POST['ffin'], 'FACULTAD', request.POST['contenidopromedio'])
                                                                           }, qrname + '.pdf', 'informemensualdocente'
                                                                          )
                    promediototal_texto = request.POST['promediototal']
                    promediototal_sin_ultimo_caracter = promediototal_texto[:-1]
                    promediototal_float = float(promediototal_sin_ultimo_caracter)
                    informemensual = InformeMensualDocente(distributivo_id=distributivo.id,
                                                           fechainicio=fechaini,
                                                           fechafin=fechafin,
                                                           archivo='informemensualdocente/' + qrname + '.pdf',
                                                           promedio=promediototal_float)
                    informemensual.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % ex})

            if action == 'deleteinformemensual':
                try:
                    informemensual = InformeMensualDocente.objects.get(pk=request.POST['id'])
                    generado = 'informemensual_' + str(informemensual.distributivo.id) + '_' + str(informemensual.fechafin.month)
                    firmado = 'informemensual_' + str(informemensual.distributivo.id) + '_' + str(informemensual.fechafin.month) + '_2'
                    folder = os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', '')
                    try:
                        os.remove(folder + generado + '.pdf')
                    except Exception as ex:
                        pass
                    try:
                        os.remove(folder + firmado + '.pdf')
                    except Exception as ex:
                        pass
                    informemensual.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'firmainformemensual':
                try:
                    # Parametros
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas:
                        raise NameError("Debe seleccionar ubicación de la firma")
                    x = txtFirmas[-1]
                    idinforme = int(encrypt(request.POST['id_objeto']))
                    evidenciaactividad = InformeMensualDocente.objects.get(pk=idinforme)
                    tienefirmas = False
                    if evidenciaactividad.distributivo.carrera:
                        if CoordinadorCarrera.objects.values('id').filter(carrera=evidenciaactividad.distributivo.carrera, periodo=periodo, sede_id=1, tipo=3).exists():
                            personadirectorcarrera = CoordinadorCarrera.objects.filter(carrera=evidenciaactividad.distributivo.carrera, periodo=periodo, sede_id=1, tipo=3)[0]
                            if evidenciaactividad.distributivo.coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, status=True).exists():
                                personadirectorcoordinacion = evidenciaactividad.distributivo.coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, status=True)[0]
                                tienefirmas = True
                    if not tienefirmas:
                        raise NameError("Estimado/a Docente, no tiene configurada coordinaciones para generar informes, por favor diríjase a su director de carrera.")
                    responsables = request.POST.getlist('responsables[]')
                    firma = request.FILES["firma"]
                    passfirma = request.POST['palabraclave']
                    url_archivo = (SITE_STORAGE + request.POST["url_archivo"]).replace('\\', '/')
                    # _name = generar_nombre(f'informemensual_{request.user.username}_{idinforme}_', 'firmada')
                    _name = 'informemensual_' + str(evidenciaactividad.distributivo.id) + '_' + str(evidenciaactividad.fechafin.month) + '_2'
                    folder = os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', '')
                    try:
                        os.remove(folder + _name + '.pdf')
                    except Exception as ex:
                        pass
                    # Firmar y guardar archivo en folder definido.
                    firma = firmararchivogenerado(request, passfirma, firma, url_archivo, folder, _name, x["numPage"], x["x"], x["y"], x["width"], x["height"])
                    if firma != True:
                        raise NameError(firma)
                    log(u'Firmo Documento: {}'.format(_name), request, "add")

                    folder_save = os.path.join('informemensualdocente', '').replace('\\', '/')
                    url_file_generado = f'{folder_save}{_name}.pdf'
                    evidenciaactividad.archivo = url_file_generado
                    evidenciaactividad.estado = 2
                    evidenciaactividad.save(request)
                    if not HistorialInforme.objects.values('id').filter(informe=evidenciaactividad, estado=2).exists():
                        historial = HistorialInforme(informe=evidenciaactividad,
                                                     archivo=url_file_generado,
                                                     estado=2,
                                                     fechafirma=datetime.now().date(),
                                                     firmado=True,
                                                     personafirmas=persona)
                        historial.save(request)
                    if not HistorialInforme.objects.values('id').filter(informe=evidenciaactividad, estado=3).exists():
                        historial = HistorialInforme(informe=evidenciaactividad,
                                                     personafirmas=personadirectorcarrera.persona,
                                                     estado=3)
                        historial.save(request)
                    if not HistorialInforme.objects.values('id').filter(informe=evidenciaactividad, estado=4).exists():
                        historial = HistorialInforme(informe=evidenciaactividad,
                                                     personafirmas=personadirectorcoordinacion.persona,
                                                     estado=4)
                        historial.save(request)

                    rutapdf = folder + 'informemensual_' + str(evidenciaactividad.distributivo.id) + '_' + str(evidenciaactividad.fechafin.month) + '.pdf'
                    if os.path.isfile(rutapdf):
                        os.remove(rutapdf)
                    log(u'firmo informe mensual: {}'.format(evidenciaactividad), request, "add")
                    return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

            if action == 'generainformefirmar':
                try:
                    from pdip.models import ContratoDip, ContratoCarrera, ContratoAreaPrograma, SolicitudPago
                    hoy = datetime.now()
                    fechaini = convertir_fecha(request.POST['fini'])
                    fechafin = convertir_fecha(request.POST['ffin'])
                    resumen_activities = json.loads(request.POST.get('list_summary', 'null'))
                    distributivo = ProfesorDistributivoHoras.objects.get(pk=request.POST['id'])
                    if distributivo.informemensualdocente_set.filter(fechafin__month=fechafin.month, status=True):
                        return JsonResponse({"result": "bad", "message": u"Ya has generado un informe. Si deseas generar otro, por favor elimina el informe ya generado."})
                    qrname = 'informemensual_' + str(distributivo.id) + '_' + str(fechafin.month)
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', ''))
                    os.makedirs(folder, exist_ok=True)
                    if periodo.tipo.id in [3, 4]:
                        dat_infor = profesor.informe_actividades_mensual_docente_v4(periodo, request.POST['fini'],
                                                                                    request.POST['ffin'], 'FACULTAD',
                                                                                    request.POST['contenidopromedio'])
                        dat_infor['contrato'] = contrato = ContratoDip.objects.filter(status=True, persona=profesor.persona).order_by('-id').first()
                        dat_infor['carreras'] = ContratoCarrera.objects.filter(contrato=contrato, status=True)
                        dat_infor['areasprogramas'] = ContratoAreaPrograma.objects.filter(contrato=contrato, status=True)
                        profesorMateria = dat_infor['asignaturas']
                        if profesorMateria:
                            proanali_id = profesorMateria.values_list('materia__asignaturamalla_id', flat=True)
                            programaanalistico = ProgramaAnaliticoAsignatura.objects.filter(status=True, asignaturamalla_id__in=proanali_id).order_by('-id').first()
                            dat_infor['programa_analitico'] = programaanalistico
                        dat_infor['periodoposgrado'] = True
                        generainforme = html_to_pdfsave_informemensualdocente(
                            'adm_criteriosactividadesdocentepos/informe_actividad_docentev4posgrado_pdf.html',
                            {'pagesize': 'A4',
                             'data': dat_infor
                             }, qrname + '.pdf', 'informemensualdocente'
                        )

                    else:
                        bitacora = BitacoraActividadDocente.objects.filter(profesor=profesor, status=True).first()
                        aplicador = profesor_aplicador(profesor, periodo, request.POST['fini'], request.POST['ffin'], distributivo)
                        generainforme = html_to_pdfsave_informemensualdocente('adm_criteriosactividadesdocente/informe_actividad_docentev4_pdf.html',
                                                                              {'pagesize': 'A4',
                                                                               'data': profesor.informe_actividades_mensual_docente_v4(periodo, request.POST['fini'], request.POST['ffin'], 'FACULTAD', request.POST['contenidopromedio']),
                                                                               'bitacora': bitacora, 'aplicador': aplicador, 'tablapdf': True
                                                                               }, qrname + '.pdf', 'informemensualdocente'
                                                                              )
                    time.sleep(5)
                    promediototal_texto = request.POST['promediototal']
                    promediototal_sin_ultimo_caracter = promediototal_texto[:-1]
                    promediototal_float = float(promediototal_sin_ultimo_caracter)

                    if distributivo.informemensualdocente_set.filter(fechafin__month=fechafin.month, status=True):
                        informe = distributivo.informemensualdocente_set.filter(fechafin__month=fechafin.month, status=True)[0]
                        informe.archivo = 'informemensualdocente/' + qrname + '.pdf'
                        informe.promedio = promediototal_float
                        informe.save(request)
                    # if InformeMensualDocente.objects.filter(distributivo__periodo=periodo, distributivo__profesor=profesor, fechafin__month=month).exists():
                    else:
                        informe = InformeMensualDocente(distributivo_id=distributivo.id,
                                                        fechainicio=fechaini,
                                                        fechafin=fechafin,
                                                        archivo='informemensualdocente/' + qrname + '.pdf',
                                                        promedio=promediototal_float)
                        informe.save(request)
                    if resumen_activities:
                        for res in resumen_activities:
                            id_criterio = res['criterio_id']
                            hpm = res['hpm']
                            hem = res['hem']
                            pcm = res['pcm']
                            if informe.horasinformemensualdocente_set.values('id').filter(status=True, criteriodocenciaperiodo_id=int((id_criterio))).exists():
                                resumen = informe.horasinformemensualdocente_set.filter(status=True, criteriodocenciaperiodo_id=int((id_criterio))).order_by('-id').first()
                                resumen.hpm = hpm
                                resumen.hem = hem
                                resumen.pcm = pcm
                                resumen.save(request)
                                log(f"Actualizo el registro de resumen del informe mensual: {resumen}", request, 'change')
                            else:
                                resumen = HorasInformeMensualDocente(
                                    informe=informe,
                                    criteriodocenciaperiodo_id=int(id_criterio),
                                    hpm=hpm,
                                    hem=hem,
                                    pcm=pcm
                                )
                                resumen.save(request)
                                log(f"Agrego resumen del informe mesual: {resumen}", request, 'add')
                    random_number = random.randint(1, 1000000)
                    data['archivo'] = informe.archivo.url
                    archivo = f"{informe.archivo.url}?cache={random_number}"
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = informe.id
                    data['action_firma'] = 'firmainformemensual'
                    if distributivo.profesor.tienetoken:
                        return JsonResponse({"result": True, 'data': {}, 'tienetoken': True})

                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'tienetoken': False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'actualizarValorInformeMensual':
                try:
                    fechames = datetime.now().date()
                    now = datetime.now()
                    qsbase = HistorialInformeMensual.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo,
                                                                    status=True, fecha_creacion__month=now.month,
                                                                    fecha_creacion__year=now.year, fecha_creacion__day=now.day)
                    if qsbase.exists():
                        historial_ = qsbase.first()
                        historial_.total_porcentaje = request.POST['total_porcentaje']
                        historial_.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "msg": f"Error al guardar los datos. {ex.__str__()}"})

            if action == 'uploadfile':
                try:
                    t = TerminosCondicionesProfesorDistributivo.objects.get(id=request.POST.get('id'))
                    archivo = request.FILES.get('archivo', None)

                    if not archivo:
                        raise NameError(f'Por favor ingrese un archivo firmado.')

                    valido, _, dict = verificarFirmasPDF(archivo)

                    if dict:
                        if firmas_validas := dict.get('firmasValidas'):
                            # if not list(filter(lambda x: x.get('emitidoPara') == persona.nombre_completo(), dict.get('certificado'))):
                            #     raise NameError(f'La firma electronica del archivo ingresado no corresponde a la del usuario {persona.usuario.username}')

                            t.archivo = archivo
                            t.legalizado = True
                            t.fechalegalizacion = datetime.now()
                            t.save(request)
                            return JsonResponse({'result': 'ok'})

                        raise NameError('El documento no tiene ninguna firma electrónica')

                    return JsonResponse({'result': 'bad', 'mensaje': 'Error en la carga de archivo.'})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

            if action == 'legalizarterminoscondiciones':
                try:
                    terms = TerminosCondicionesProfesorDistributivo.objects.get(id=int(encrypt(request.POST.get('id_objeto'))))

                    if not terms.archivo:
                        # try:
                        #     path = os.path.join(os.path.join(SITE_STORAGE, 'media', terms.archivo.__str__()))
                        #     os.path.isfile(path) and os.remove(path)
                        # except Exception as ex:
                        #     ...
                        genera_archivo_terminos_condiciones(request, terms)

                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas: raise NameError("Debe seleccionar ubicación de la firma")
                    x = txtFirmas[-1]

                    # Legalizar archivo
                    passfirma = request.POST['palabraclave']
                    if not passfirma: raise NameError(u"Ingrese la contraseña")

                    certificado = request.FILES['firma']
                    documento_a_firmar = terms.archivo
                    name_documento_a_firmar, extension_documento_a_firmar = os.path.splitext(documento_a_firmar.name)
                    extension_certificado = os.path.splitext(certificado.name)[1][1:]
                    bytes_certificado = certificado.read()
                    palabras = u"%s" % persona.nombre_titulos3y4().title()
                    posx, posy, numpaginafirma, datau = x["x"], x["y"], x["numPage"], None  # obtener_posicion_x_y_saltolinea(documento_a_firmar.url, palabras)

                    if not posy: raise NameError(f"No se encontró el nombre {palabras} en el archivo del informe, por favor verifique si el nombre de esta persona se encuentra en la sección de firmas.")

                    posx, posy = posx + 30, posy + 40

                    try:
                        datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado, password_certificado=passfirma, page=numpaginafirma, reason=f"Legalizar terminos y condiciones N{terms.terminos.pk}", lx=posx, ly=posy).sign_and_get_content_bytes()
                    except Exception as x:
                        try:
                            datau, datas = firmar(request, passfirma, certificado, documento_a_firmar, numpaginafirma, posx, posy, 150, 45)
                        except Exception as es:
                            ...

                    if not datau: raise NameError(f'Problemas de conexión con la plataforma de Firma EC. Por favor intentelo más tarde.')

                    documento_a_firmar = io.BytesIO()
                    documento_a_firmar.write(datau)
                    documento_a_firmar.seek(0)

                    _name = name_documento_a_firmar.__str__().split('/')[-1].replace('.pdf', '') + '_signed_.pdf'
                    terms.archivo.save(_name, ContentFile(documento_a_firmar.read()))

                    terms.legalizado = True
                    terms.fechalegalizacion = datetime.now()
                    terms.save(request)

                    return JsonResponse({"result": 'ok', "mensaje": "Guardado con exito", }, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

            if action == 'add_solicitud':
                try:
                    from inno.forms import SolictudAperturaClaseVirtualForm
                    if SolicitudAperturaClaseVirtual.objects.filter(status=True, profesor=profesor, periodo=periodo,
                                                                    estadosolicitud__in=[1]).exists():
                        raise NameError('Ya cuenta cuenta con una solicitud que aún no ha sido atendida')
                    solactual = SolicitudAperturaClaseVirtual.objects.filter(status=True, profesor=profesor,
                                                                             periodo=periodo, estadosolicitud__in=[2],
                                                                             fechafin__gte=datetime.now().date()).first()
                    if solactual:
                        raise NameError(
                            'Ya cuenta cuenta con una solicitud APROBADA hasta el: {}'.format(str(solactual.fechafin.date())))

                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        ext = newfile._name[newfile._name.rfind("."):]
                        if ext not in ['.pdf', '.PDF']:
                            raise NameError('Debe subir un archivo en formato .pdf')
                        if newfile.size > 20971520:
                            raise NameError('Debe subir un archivo no mayor a 2 Mb.')
                    form = SolictudAperturaClaseVirtualForm(request.POST, request.FILES)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    solicitud = SolicitudAperturaClaseVirtual()
                    solicitud.profesor = profesor
                    solicitud.periodo = periodo
                    solicitud.descripcion = form.cleaned_data['descripcion']
                    if newfile:
                        solicitud.archivo = newfile
                    solicitud.save(request)
                    log(u'Agregó solicitud de apertura de clase virtual: %s' % persona, request, "add")
                    dist = profesor.profesordistributivohoras_set.filter(status=True, periodo=periodo).first()
                    coordinacion = dist.coordinacion if dist else None
                    mensaje = 'Solicitud enviada para su aprobación'
                    if coordinacion:
                        responsable = coordinacion.responsable_periododos(periodo, 1)
                        if responsable:
                            mensaje = 'Solicitud enviada para su aprobación al decano: {}'.format(responsable.persona.nombre_completo_minus())
                            notificacion('Solicitud de apertura de clases', 'El docente {} solicita la probación de apertura de clases virtuales'.format(profesor.persona.nombre_completo_minus()), responsable.persona,
                                         None, '/adm_criteriosactividadesdocente?action=solicitudaperturaclase', responsable.persona_id, 2, 'sga', solicitud, request)
                    return JsonResponse({'result': False, 'modalsuccess': True, 'mensaje': mensaje})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': f'{ex}'})

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

            if action == 'solicitarrevisionbitacora':
                try:
                    bitacora = BitacoraActividadDocente.objects.get(pk=request.POST.get('pk'))
                    bitacora.estadorevision = 2
                    bitacora.save(request, update_fields=['estadorevision'])

                    h = HistorialBitacoraActividadDocente(bitacora=bitacora, estadorevision=2, persona=persona)
                    h.save(request)

                    # if distributivo := bitacora.criterio.distributivo:
                    #     coordinador, coordinadorcarrera = distributivo.coordinacion.responsable_periododos(periodo, 1), None
                    #     if distributivo.carrera:
                    #         coordinadorcarrera = distributivo.carrera.coordinador(periodo, distributivo.coordinacion.sede)
                    #     notificacion()

                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': f'Error de conexión. {ex=}'})

            if action == 'addanexobitacora':
                try:
                    detallebitacora = DetalleBitacoraDocente.objects.get(id=int(encrypt(request.POST['id'])))
                    f = AnexoEvidenciaActividadForm(request.POST, request.FILES)
                    newfile = None
                    if 'archivoanexo' in request.FILES:
                        if newfile := request.FILES['archivoanexo']:
                            if newfile.size > 20971520:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 20 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                newfile._name = generar_nombre("anexo_bitacora_", newfile._name)
                    if f.is_valid():
                        anexo = AnexoDetalleBitacoraDocente(observacion=f.cleaned_data.get('observacion'), archivo=newfile, detallebitacoradocente=detallebitacora)
                        anexo.save(request)
                        return JsonResponse({'result': 'ok'})
                    raise NameError('Error en el formulario')
                except Exception as ex:
                    return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

            if action == 'delanexobitacora':
                try:
                    anexo = AnexoDetalleBitacoraDocente.objects.get(id=request.POST['id'])
                    anexo.delete()
                    return JsonResponse({'error': False})
                except Exception as ex:
                    return JsonResponse({'error': True, 'mensaje': ex.__str__()})

            if action == 'validarseleccion':
                try:
                    intento = int(request.POST['intento'])
                    pregunta = DetalleTest.objects.get(pk=int(request.POST['idpregunta']))
                    tolapreguntas = pregunta.test.detalletest().count()
                    seleccion = int(request.POST['seleccion'])
                    es_correcto = False
                    if pregunta and seleccion:
                        if pregunta.respuesta == seleccion:
                            es_correcto = True
                            seleccion = pregunta.valor
                        else:
                            seleccion = 0
                        respuestausuario = UsuarioRespuesta(detalletest=pregunta, intento_id=intento, correcto=es_correcto, valor=seleccion)
                        respuestausuario.save(request)
                        if tolapreguntas == respuestausuario.intento.totalrespuestausuario():
                            eintento = respuestausuario.intento
                            eintento.finalizo = True
                            eintento.save(request)
                        if es_correcto:
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "fail"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
            elif action == 'siguiente':
                try:
                    if not 'idseguimiento'  in request.POST:
                        raise NameError('Test no encontrado')
                    if not 'iddetalle' in request.POST:
                        raise NameError('Pregunta no encontrada')
                    seguimiento = SeguimientoDocente.objects.filter(status=True, id=request.POST['idseguimiento']).first()
                    if not seguimiento:
                        raise NameError('Test no encontrado')
                    detalle = DetalleSeguimientoDocente.objects.filter(id=request.POST['iddetalle']).first()
                    if not detalle:
                        raise NameError('Pregunta no encontrada')
                    detalle.fechainteraccion = datetime.now()
                    detalle.encontroopcion = request.POST['encontroopcion'] == 'true'
                    detalle.escaladificultad = request.POST['valordificultad']
                    detalle.tiempointeraccion = request.POST['tiempotranscurrido']
                    detalle.respondido = True
                    detalle.save(request)
                    log('Registro respuesta de test', request, 'add')
                    es_ultimo = request.POST['es_ultimo'] == 'True'
                    if not es_ultimo:
                        data['detalle'] = detalle = seguimiento.detalle().first()
                        data['es_ultimo'] = detalle.id == seguimiento.detalle().last().id
                        url = f'/pro_laboratoriocronograma?action=testnavegacion&idseguimiento={seguimiento.id}'
                        return JsonResponse({"result": "ok", "nexthref": url})
                    from laboratorio.models import ResultadoPerfilDocente
                    seguimiento.estado_intento = 1
                    hora_actual = datetime.now().time()
                    hora_creacion = seguimiento.fecha_creacion.time()
                    # Convertir ambos tiempos a datetime para calcular la diferencia
                    fecha_actual = datetime.combine(datetime.today(), hora_actual)
                    fecha_creacion = datetime.combine(datetime.today(), hora_creacion)
                    # Calcular la diferencia
                    diferencia = fecha_actual - fecha_creacion
                    seguimiento.tiempointeracciontotal = diferencia.total_seconds()
                    seguimiento.save(request)
                    # Guardar test realizados para asignacion de perfil
                    intentocontraste = IntentoUsuario.objects.filter(status=True, usuario=seguimiento.profesor).order_by('fecha').first()
                    result = ResultadoPerfilDocente(seguimiento=seguimiento, testcontraste=intentocontraste)
                    result.save(request)
                    # testTraining(result)
                    return JsonResponse({"result": "ok", "nexthref": '/pro_laboratoriocronograma'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": f'Solicitud Incorrecta. {ex}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'generararchivoterminoscondiciones':
                try:
                    terms = TerminosCondicionesProfesorDistributivo.objects.get(id=request.GET.get('id'))
                    genera_archivo_terminos_condiciones(request, terms)
                except Exception as ex:
                    pass

            if action == 'legalizarterminoscondiciones':
                try:
                    # data['form2'] = FirmaElectronicaIndividualForm()
                    # data['id'] = request.GET.get('id')
                    # template = get_template("adm_revisioncriteriosactividades/modal/firmardocumento.html")
                    # return JsonResponse({"result": "ok", 'data': template.render(data)})

                    t = TerminosCondicionesProfesorDistributivo.objects.get(id=request.GET.get('id'))
                    if not t.archivo:
                        genera_archivo_terminos_condiciones(request, t)

                    archivo = t.archivo.url
                    data['archivo'] = archivo
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = t.id
                    data['action_firma'] = action
                    template = get_template("pro_laboratoriocronograma/modal/firmarinformepppinternadorotativo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'firmarinformepppinternadorotativo':
                try:
                    detalle = EvidenciaActividadDetalleDistributivo.objects.get(id=request.GET['id'])
                    data['evidencia'] = detalle
                    data['archivo'] = archivo = detalle.archivo.url
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = detalle.id
                    data['action_firma'] = 'firmarinformepppinternadorotativo'
                    template = get_template("pro_laboratoriocronograma/modal/firmarinformepppinternadorotativo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'culminartutoria':
                try:
                    data['practica'] = practica = PracticasPreprofesionalesInscripcion.objects.get(status=True, pk=int(encrypt(request.GET['id'])))
                    data['title'] = u"Culminar tutoria"
                    return render(request, "pro_laboratoriocronograma/culminartutoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'reemplazardocumentoinquietud':
                try:
                    data['filtro'] = filtro = InquietudPracticasPreprofesionales.objects.get(pk=int(request.GET['id']))
                    form = ReemplazarInquietudForm(initial=model_to_dict(filtro))
                    data['form2'] = form
                    template = get_template("pro_laboratoriocronograma/modal/modalform.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'programartutoria':
                try:
                    data['title'] = u"Programar Tutoria"
                    url_vars = ''
                    url_vars += '&action={}'.format(action)
                    query = AgendaPracticasTutoria.objects.filter(docente=perfilprincipal.profesor, status=True).order_by('-fecha')
                    data["url_vars"] = url_vars
                    paging = MiPaginador(query, 15)
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
                    data['listado'] = page.object_list
                    return render(request, "pro_laboratoriocronograma/listadotutorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'miagendatutoria':
                try:
                    data['title'] = u"Programar Tutoria"
                    url_vars = ''
                    url_vars += '&action={}'.format(action)
                    query = AgendaPracticasTutoria.objects.filter(docente=perfilprincipal.profesor, status=True).order_by('-fecha')
                    data['listado'] = query
                    return render(request, "pro_laboratoriocronograma/programartutoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'addagenda':
                try:
                    form = AgendaPracticasTutoriaForm()
                    form.fields['url_reunion'].initial = profesor.urlzoom if profesor.urlzoom else ''
                    form.fields['estudiantes'].queryset = PracticasPreprofesionalesInscripcion.objects.filter(status=True, culminatutoria=False, culminada=False, tutorunemi=perfilprincipal.profesor, tipo__in=[1, 2]).exclude(estadosolicitud=3)
                    data['form2'] = form
                    template = get_template("pro_laboratoriocronograma/modal/formagenda.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'addtutoriacalendario':
                try:
                    data['action'] = 'addagenda'
                    fecha_str = request.GET['id']
                    fecha = convertir_fecha_invertida(fecha_str)
                    form = AgendaPracticasTutoriaForm()
                    form.fields['url_reunion'].initial = profesor.urlzoom if profesor.urlzoom else ''
                    form.fields['fecha'].widget.attrs['readonly'] = 'readonly'
                    form.fields['fecha'].initial = fecha
                    dataagenda = AgendaPracticasTutoria.objects.filter(status=True, fecha=fecha, turno__isnull=False, docente=profesor)
                    ocupados = dataagenda.values_list('turno_id', flat=True)
                    estudiantesagendados = []
                    for ag in dataagenda:
                        estudiantesagendados += ag.inscritos().values_list('estudiante_id', flat=True)
                    form.fields['estudiantes'].queryset = PracticasPreprofesionalesInscripcion.objects.filter(status=True, culminatutoria=False, culminada=False, tutorunemi=perfilprincipal.profesor, tipo__in=[1, 2]).exclude(estadosolicitud=3).exclude(id__in=estudiantesagendados)
                    # horariosturno = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo, dia=fecha.weekday() + 1).values_list('turno_id', flat=True)
                    # if horariosturno.exists():
                    #     form.fields['turno'].queryset = Turno.objects.filter(id__in=horariosturno).exclude(id__in=ocupados)
                    #     del form.fields['hora_inicio']
                    #     del form.fields['hora_fin']
                    # else:
                    del form.fields['turno']
                    data['form2'] = form
                    template = get_template("pro_laboratoriocronograma/modal/formagenda.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'editagenda':
                try:
                    data['id'] = id = int(request.GET['id'])
                    instancia = AgendaPracticasTutoria.objects.get(pk=id)
                    form = AgendaPracticasTutoriaForm(instance=instancia, periodo=periodo)
                    form.fields['fecha'].widget.attrs['readonly'] = 'readonly'
                    dataagenda = AgendaPracticasTutoria.objects.filter(status=True, fecha=instancia.fecha, turno__isnull=False).exclude(id=id)
                    ocupados = dataagenda.values_list('turno_id', flat=True)
                    estudiantesagendados = []
                    for ag in dataagenda:
                        estudiantesagendados += ag.inscritos().values_list('estudiante_id', flat=True)
                    form.fields['estudiantes'].queryset = PracticasPreprofesionalesInscripcion.objects.filter(status=True, culminatutoria=False, culminada=False, tutorunemi=perfilprincipal.profesor, tipo__in=[1, 2]).exclude(estadosolicitud=3, id__in=estudiantesagendados)
                    horariosturno = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo, dia=instancia.fecha.weekday() + 1).values_list('turno_id', flat=True)
                    if horariosturno.exists():
                        form.fields['turno'].queryset = Turno.objects.filter(id__in=horariosturno).exclude(id__in=ocupados)
                        del form.fields['hora_inicio']
                        del form.fields['hora_fin']
                        # form.fields['turno'].queryset = Turno.objects.filter(id__in=horariosturno)
                    # else:
                    #     del form.fields['turno']

                    data['form2'] = form
                    template = get_template("pro_laboratoriocronograma/modal/formagenda.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'veragenda':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['instancia'] = instancia = AgendaPracticasTutoria.objects.get(pk=id)
                    form = AgendaPracticasTutoriaForm(instance=instancia, ver=True, periodo=periodo)
                    del form.fields['estudiantes']
                    # form.fields['estudiantes'].queryset = PracticasPreprofesionalesInscripcion.objects.filter(status=True,  culminatutoria=False, culminada=False, tutorunemi=perfilprincipal.profesor, tipo__in=[1, 2]).exclude(estadosolicitud=3)
                    horariosturno = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo, dia=instancia.fecha.weekday() + 1).values_list('turno_id', flat=True)

                    data['form2'] = form
                    template = get_template("pro_laboratoriocronograma/modal/veragenda.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'reagendartutoria':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['filtro'] = instancia = AgendaPracticasTutoria.objects.get(pk=id)
                    form = ReAgendarAgendaPracticasTutoriasForm(initial=model_to_dict(instancia))
                    data['form2'] = form
                    template = get_template("pro_laboratoriocronograma/modal/formobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'finagenda':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['filtro'] = instancia = AgendaPracticasTutoria.objects.get(pk=id)
                    data['estudiantes'] = estudiantes = EstudiantesAgendaPracticasTutoria.objects.filter(status=True, cab=instancia)
                    form = FinalizarAgendaTutoriaForm()
                    data['form2'] = form
                    template = get_template("pro_laboratoriocronograma/modal/formfinalizacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'anularagenda':
                try:
                    data['id'] = id = int(request.GET['id'])
                    data['filtro'] = instancia = AgendaPracticasTutoria.objects.get(pk=id)
                    form = FinalizarAgendaTutoriaForm()
                    data['form2'] = form
                    template = get_template("pro_laboratoriocronograma/modal/formobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'consultarestudiantestutoria':
                fecha_str = request.GET['fecha']
                fecha = convertir_fecha_invertida(fecha_str)
                # qspersonas = AgendaPracticasTutoria.objects.filter(status=True, practica__tutorunemi=perfilprincipal.profesor, fecha=fecha).values_list('practica_id', flat=True)
                filtro = PracticasPreprofesionalesInscripcion.objects.filter(status=True, culminatutoria=False, culminada=False, tutorunemi=perfilprincipal.profesor, tipo__in=[1, 2]).exclude(estadosolicitud=3)
                if 'search' in request.GET:
                    search = request.GET['search']
                    filtro = filtro.filter(inscripcion__persona__apellido1__icontains=search)
                resp = [{'id': cr.pk, 'text': '{}, Itinerario: {}'.format(cr.inscripcion.persona.__str__(), cr.itinerariomalla)} for cr in filtro]
                return HttpResponse(json.dumps({'state': True, 'result': resp}))

            elif action == 'descargatutorias':
                try:
                    tutorias = PracticasTutoria.objects.filter(practica__tutorunemi=profesor, status=True)

                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Lista de tutorias ' + random.randint(1,
                                                                                                                 10000).__str__() + '.xls'
                    columns = [
                        (u"FACULTAD", 12000),
                        (u"CARRERA", 12000),
                        (u"ESTUDIANTE", 12000),
                        (u"CEDULA", 10000),
                        (u"CORREO INSTITUCIONAL", 10000),
                        (u"TELÉFONO", 12000),
                        (u"TUTOR ACADÉMICO", 4500),
                        (u"CORREO TUTOR ACADÉMICO", 4500),
                        (u"INSTITUCIÓN", 4500),
                        (u"HORAS DE PRÁCTICAS", 4500),
                        (u"ITINERARIO", 4500),
                        (u"OBSERVACIONES", 4500),
                        (u"RECOMENDACIONES", 4500),
                        (u"N° TUTORÍAS", 4500),
                        (u"FECHA DE TUTORÍA", 4500),
                        (u"ARCHIVO", 4500),
                        (u"NOMBRE ARCHIVO", 4500),
                        (u"URL ARCHIVO", 4500),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    cont = 0
                    for tuto in tutorias:
                        cont += 1
                        cfacu = tuto.practica.inscripcion.coordinacion.nombre if tuto.practica.inscripcion.coordinacion else ''
                        ccarrera = tuto.practica.inscripcion.carrera.nombre if tuto.practica.inscripcion.carrera else ''
                        cestudiante = tuto.practica.inscripcion.persona.nombre_completo_inverso()
                        ccedula = tuto.practica.inscripcion.persona.identificacion()
                        ccorreo = tuto.practica.inscripcion.persona.emailinst
                        ctelefono = tuto.practica.inscripcion.persona.telefono
                        ctutor = profesor.persona.nombre_completo_inverso()
                        ccorreotutor = profesor.persona.emailinst
                        cinstitucion = profesor.persona.nombre_completo_inverso()
                        choras = profesor.persona.nombre_completo_inverso()
                        citinerarios = tuto.practica.itinerariomalla.nombre if tuto.practica.itinerariomalla else ''
                        cobservacion = tuto.observacion
                        crecomendacion = tuto.sugerencia
                        ctutoria = cont
                        cfecha = tuto.fechainicio

                        if tuto.archivo:
                            estado = 'SI'
                        else:
                            estado = 'NO'
                        carchivo = estado
                        ws.write(row_num, 0, cfacu, font_style2)
                        ws.write(row_num, 1, ccarrera, font_style2)
                        ws.write(row_num, 2, cestudiante, font_style2)
                        ws.write(row_num, 3, ccedula, font_style2)
                        ws.write(row_num, 4, ccorreo, font_style2)
                        ws.write(row_num, 5, ctelefono, font_style2)
                        ws.write(row_num, 6, ctutor, font_style2)
                        ws.write(row_num, 7, ccorreotutor, font_style2)
                        ws.write(row_num, 8, cinstitucion, font_style2)
                        ws.write(row_num, 9, choras, font_style2)
                        ws.write(row_num, 10, citinerarios, font_style2)
                        ws.write(row_num, 11, cobservacion, font_style2)
                        ws.write(row_num, 12, crecomendacion, font_style2)
                        ws.write(row_num, 13, ctutoria, font_style2)
                        ws.write(row_num, 14, u"%s" % cfecha, date_format)
                        ws.write(row_num, 15, carchivo, font_style2)
                        urldominio = request.build_absolute_uri('/')[:-1].strip("/")
                        if tuto.archivo:
                            ws.write(row_num, 16, tuto.archivo.name.split('/')[len(tuto.archivo.name.split('/')) - 1], font_style2)
                            link = "{}{}".format(urldominio, tuto.archivo.url)
                            ws.write(row_num, 17, xlwt.Formula('HYPERLINK("{}";"{}")'.format(link, link)), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'descargatutoriasfechas':
                try:
                    fecinicio = request.GET['fecinicio']
                    fecfin = request.GET['fecfin']
                    tutorias = PracticasTutoria.objects.filter(practica__tutorunemi=profesor, status=True, fechainicio__gte=fecinicio, fechainicio__lte=fecfin)

                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Lista de tutorias ' + random.randint(1,
                                                                                                                 10000).__str__() + '.xls'
                    columns = [
                        (u"FACULTAD", 12000),
                        (u"CARRERA", 12000),
                        (u"ESTUDIANTE", 12000),
                        (u"CEDULA", 10000),
                        (u"CORREO INSTITUCIONAL", 10000),
                        (u"TELÉFONO", 12000),
                        (u"TUTOR ACADÉMICO", 4500),
                        (u"CORREO TUTOR ACADÉMICO", 4500),
                        (u"INSTITUCIÓN", 4500),
                        (u"HORAS DE PRÁCTICAS", 4500),
                        (u"ITINERARIO", 4500),
                        (u"OBSERVACIONES", 4500),
                        (u"RECOMENDACIONES", 4500),
                        (u"N° TUTORÍAS", 4500),
                        (u"FECHA DE TUTORÍA", 4500),
                        (u"ARCHIVO", 4500),
                        (u"NOMBRE ARCHIVO", 4500),
                        (u"URL ARCHIVO", 4500),
                    ]

                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    cont = 0
                    for tuto in tutorias:
                        cont += 1
                        cfacu = tuto.practica.inscripcion.coordinacion.nombre if tuto.practica.inscripcion.coordinacion else ''
                        ccarrera = tuto.practica.inscripcion.carrera.nombre if tuto.practica.inscripcion.carrera else ''
                        cestudiante = tuto.practica.inscripcion.persona.nombre_completo_inverso()
                        ccedula = tuto.practica.inscripcion.persona.identificacion()
                        ccorreo = tuto.practica.inscripcion.persona.emailinst
                        ctelefono = tuto.practica.inscripcion.persona.telefono
                        ctutor = profesor.persona.nombre_completo_inverso()
                        ccorreotutor = profesor.persona.emailinst
                        cinstitucion = profesor.persona.nombre_completo_inverso()
                        choras = profesor.persona.nombre_completo_inverso()
                        citinerarios = tuto.practica.itinerariomalla.nombre if tuto.practica.itinerariomalla else ''
                        cobservacion = tuto.observacion
                        crecomendacion = tuto.sugerencia
                        ctutoria = cont
                        cfecha = tuto.fechainicio

                        if tuto.archivo:
                            estado = 'SI'
                        else:
                            estado = 'NO'
                        carchivo = estado
                        ws.write(row_num, 0, cfacu, font_style2)
                        ws.write(row_num, 1, ccarrera, font_style2)
                        ws.write(row_num, 2, cestudiante, font_style2)
                        ws.write(row_num, 3, ccedula, font_style2)
                        ws.write(row_num, 4, ccorreo, font_style2)
                        ws.write(row_num, 5, ctelefono, font_style2)
                        ws.write(row_num, 6, ctutor, font_style2)
                        ws.write(row_num, 7, ccorreotutor, font_style2)
                        ws.write(row_num, 8, cinstitucion, font_style2)
                        ws.write(row_num, 9, choras, font_style2)
                        ws.write(row_num, 10, citinerarios, font_style2)
                        ws.write(row_num, 11, cobservacion, font_style2)
                        ws.write(row_num, 12, crecomendacion, font_style2)
                        ws.write(row_num, 13, ctutoria, font_style2)
                        ws.write(row_num, 14, u"%s" % cfecha, date_format)
                        ws.write(row_num, 15, carchivo, font_style2)
                        urldominio = request.build_absolute_uri('/')[:-1].strip("/")
                        if tuto.archivo:
                            ws.write(row_num, 16, tuto.archivo.name.split('/')[len(tuto.archivo.name.split('/')) - 1], font_style2)
                            link = "{}{}".format(urldominio, tuto.archivo.url)
                            ws.write(row_num, 17, xlwt.Formula('HYPERLINK("{}";"{}")'.format(link, link)), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'informemensualpdf':
                try:
                    data['title'] = u'Informe Mensual'
                    data['fechaactual'] = datetime.now().date()
                    data['horaactual'] = datetime.now().time()
                    data['carrera'] = carrera = Carrera.objects.get(pk=int(request.GET['carrera']))
                    mes = request.GET['mesinforme']
                    data['fechafin'] = fecfin = convertir_fecha_invertida(request.GET['fecfin'])
                    data['configuracionesinforme'] = configuracionesinforme = ConfiguracionInformePracticasPreprofesionales.objects.get(pk=mes)
                    data['mesinforme'] = configuracionesinforme.get_mes()
                    nombresinciales = ''
                    nombre = persona.nombres.split()
                    if len(nombre) > 1:
                        nombresiniciales = '{}{}'.format(nombre[0][0], nombre[1][0])
                    else:
                        nombresiniciales = '{}'.format(nombre[0][0])
                    inicialespersona = '{}{}{}'.format(persona.apellido1[0], persona.apellido2[0], nombresiniciales)
                    data['numinforme'] = 'ITI-{}-{}-{}-{}'.format(configuracionesinforme.mes, configuracionesinforme.anio, inicialespersona, carrera.alias)
                    baseestudiantes = PracticasPreprofesionalesInscripcion.objects.select_related('tutorunemi').filter(status=True, tutorunemi=profesor, culminada=False, preinscripcion__preinscripcion__periodo=periodo).distinct().exclude(estadosolicitud=3).order_by('-fecha_creacion').distinct()
                    data['totalestudiantesasignados'] = baseestudiantes.count()
                    baseperiodoagenda = EstudiantesAgendaPracticasTutoria.objects.filter(status=True, cab__status=True, estudiante__in=baseestudiantes.values_list('pk', flat=True))
                    data['totalestudiantesconagendames'] = baseestudiantes.filter(pk__in=baseperiodoagenda.values_list('estudiante__id', flat=True)).count()
                    data['totalagendaperiodo'] = AgendaPracticasTutoria.objects.filter(pk__in=baseperiodoagenda.values_list('cab__id', flat=True)).count()
                    data['tutorias'] = tutorias = PracticasTutoria.objects.filter(practica__inscripcion__carrera=carrera, practica__tutorunemi=profesor, status=True, fechainicio__month=configuracionesinforme.mes, fechainicio__year=configuracionesinforme.anio).order_by('fechainicio')
                    baseagenda = AgendaPracticasTutoria.objects.filter(docente=profesor, status=True, fecha__month=configuracionesinforme.mes, fecha__year=configuracionesinforme.anio)
                    data['agendames'] = agendames = baseagenda.order_by('fecha', 'hora_inicio')
                    data['totalagendames'] = baseagenda.count()
                    data['totalagendamespend'] = baseagenda.filter(estados_agenda=0).count()
                    data['totalagendamesfin'] = baseagenda.filter(estados_agenda=1).count()
                    data['totalagendamesanul'] = baseagenda.filter(estados_agenda=3).count()
                    directory = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'informesppp')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    qrname = 'qr_docente_{}_{}_{}_{}'.format(configuracionesinforme.mes, configuracionesinforme.anio, persona.pk, random.randint(1, 100000).__str__())
                    rutaimg = '{}/{}.png'.format(directory, qrname)
                    if os.path.isfile(rutaimg):
                        os.remove(rutaimg)
                    url = pyqrcode.create('DOCENTE: {}\nCARGO: {}'.format(persona.__str__(), persona.mis_cargos()[0]))
                    imageqr = url.png('{}/{}.png'.format(directory, qrname), 16, '#000000')
                    data['qrname'] = qrname

                    if responsablevinculacion:
                        data['responsablevinculacion'] = responsablevinculacion
                        # firma = FirmaPersona.objects.filter(persona=responsablevinculacion, tipofirma=2, status=True).first()

                        # data['firmaimg'] = firma if firma else None
                        data['firmaimg'] = responsablevinculacion

                    valida = conviert_html_to_pdfsaveqrinformepracticasmensual(
                        'pro_laboratoriocronograma/informemensualpdf.html',
                        {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                    )
                    if valida:
                        if InformeMensualDocentesPPP.objects.filter(status=True, anio=configuracionesinforme.anio, mes=configuracionesinforme.mes, persona=profesor, carrera=carrera).exists():
                            informe = InformeMensualDocentesPPP.objects.filter(status=True, anio=configuracionesinforme.anio, mes=configuracionesinforme.mes, persona=profesor, carrera=carrera).first()
                            informe.delete()
                            informe = InformeMensualDocentesPPP(status=True, anio=configuracionesinforme.anio, mes=configuracionesinforme.mes, persona=profesor, carrera=carrera, fechageneracion=fecfin)
                            informe.save(request)
                            # informe.fechageneracion = fecfin
                        else:
                            informe = InformeMensualDocentesPPP(status=True, anio=configuracionesinforme.anio, mes=configuracionesinforme.mes, persona=profesor, carrera=carrera, fechageneracion=fecfin)
                            informe.save(request)
                        os.remove(rutaimg)
                        informe.archivodescargar = 'qrcode/informesppp/' + qrname + '.pdf'
                        informe.save(request)
                        return redirect('https://sga.unemi.edu.ec/media/{}'.format(informe.archivodescargar))
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return redirect('{}?info={}&linea={}'.format(request.path, str(ex), sys.exc_info()[-1].tb_lineno))

            elif action == 'calificacionact':
                try:
                    data['title'] = u'Calificación de actividad extracurricular'
                    actividad = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    data['actividad'] = actividad
                    data['registrados'] = actividad.participanteactividadextracurricular_set.all().order_by('inscripcion__persona')
                    return render(request, "pro_laboratoriocronograma/calificacionact.html", data)
                except Exception as ex:
                    pass

            elif action == 'traertutorias':
                try:
                    data['title'] = u'Culminar tutoria'
                    data['practica'] = practica = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    data['tutorias'] = PracticasTutoria.objects.filter(practica=practica, status=True)
                    template = get_template("pro_laboratoriocronograma/modal/modaltutoria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})

                except Exception as ex:
                    pass

            elif action == 'cerraract':
                try:
                    actividad = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    actividad.cerrado = True
                    actividad.save(request)
                    for participante in actividad.participanteactividadextracurricular_set.all():
                        participante.save(request)
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'preferencia_old':
                try:
                    data['title'] = u''
                    data['periodo'] = periodo = request.session['periodo']
                    search = None
                    ids = None
                    fecha = datetime.now().date()
                    if (fecha >= periodo.preferencia_inicio and fecha <= periodo.preferencia_final):
                        data['accesopreferencia'] = True
                    else:
                        data['accesopreferencia'] = False
                    data['asignaturaspreferencias'] = materiaspreferencias = AsignaturaMallaPreferencia.objects.filter(profesor=profesor, periodo=periodo, status=True)
                    data['totalpreferencia'] = materiaspreferencias.count()
                    listado = materiaspreferencias.values_list('asignaturamalla_id')
                    if 's' in request.GET:
                        search = request.GET['s']
                        asignaturasmallas = AsignaturaMalla.objects.select_related().filter(malla__vigente=True, status=True).filter(asignatura__nombre__icontains=search).exclude(pk__in=listado)
                    else:
                        asignaturasmallas = AsignaturaMalla.objects.select_related().filter(malla__vigente=True, status=True).order_by('malla__id', 'malla__carrera__id', 'nivelmalla__id').exclude(pk__in=listado)
                    paging = MiPaginador(asignaturasmallas, 25)
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
                    data['asignaturasmallas'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "pro_laboratoriocronograma/listaasignaturas.html", data)
                except Exception as ex:
                    pass

            elif action == 'preferencia':
                try:
                    data['title'] = u'Seleccione los parametros de preferencias de asignaturas'
                    data['periodo'] = periodo = request.session['periodo']
                    fecha = datetime.now().date()
                    if (fecha >= periodo.preferencia_inicio and fecha <= periodo.preferencia_final):
                        data['accesopreferencia'] = True
                    else:
                        data['accesopreferencia'] = False
                    # if periodo.tipo.id==2:
                    cordinaciones = Coordinacion.objects.filter(carrera__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(status=True, nivel__periodo=periodo).distinct()).exclude(pk__in=[6]).distinct()
                    # else:
                    #     cordinaciones = Coordinacion.objects.filter(carrera__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(nivel__periodo=periodo).distinct()).exclude(pk__in=[6, 9]).distinct()
                    data['cordinaciones'] = cordinaciones
                    return render(request, "pro_laboratoriocronograma/preferencias.html", data)
                except Exception as ex:
                    pass

            elif action == 'preferenciaactividad':
                try:
                    data['title'] = u'Seleccione los parametros de preferencias de actividades'
                    data['t'] = None
                    if 't' in request.GET:
                        data['t'] = int(request.GET['t'])
                    data['periodo'] = periodo = request.session['periodo']
                    data['profesor'] = profesor
                    fecha = datetime.now().date()
                    if periodo.preferencia_actividadinicio and periodo.preferencia_actividadfinal:
                        if (fecha >= periodo.preferencia_actividadinicio and fecha <= periodo.preferencia_actividadfinal):
                            data['accesopreferenciaactividad'] = True
                        else:
                            data['accesopreferenciaactividad'] = False
                    else:
                        data['accesopreferenciaactividad'] = False
                    data['criteriodocencia'] = criteriodocencia = profesor.preferenciadetalleactividadescriterio_set.filter(criteriodocenciaperiodo__periodo=periodo, status=True).order_by('criteriodocenciaperiodo__actividad__nombre', 'criteriodocenciaperiodo__criterio__nombre')
                    data['criterioinvestigacion'] = criterioinvestigacion = profesor.preferenciadetalleactividadescriterio_set.filter(criterioinvestigacionperiodo__periodo=periodo, status=True).order_by('criterioinvestigacionperiodo__actividad__nombre', 'criterioinvestigacionperiodo__criterio__nombre')
                    data['criteriogestion'] = criteriogestion = profesor.preferenciadetalleactividadescriterio_set.filter(criteriogestionperiodo__periodo=periodo, status=True).order_by('criteriogestionperiodo__actividad__nombre', 'criteriogestionperiodo__criterio__nombre')
                    # criteriodocencia = criteriodocencia.aggregate(horas=Sum('horas'))
                    # d=criteriodocencia.horas
                    return render(request, "pro_laboratoriocronograma/preferenciasactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'preferenciaposgrado':
                try:
                    data['title'] = u'Seleccione los parametros de preferencias de asignaturas posgrado'
                    data['periodo'] = periodo = request.session['periodo']
                    data['profesor'] = profesor
                    tieneprerenciaposgrado = False
                    if profesor.preferenciadocente_set.filter(tipopreferencia=4, status=True):
                        tieneprerenciaposgrado = True
                    data['tieneprerenciaposgrado'] = tieneprerenciaposgrado
                    fecha = datetime.now().date()
                    if (fecha >= periodo.preferencia_inicio and fecha <= periodo.preferencia_final):
                        data['accesopreferencia'] = True
                    else:
                        data['accesopreferencia'] = False
                    hoy = datetime.now().date()

                    listaperiodos = Materia.objects.values_list('nivel__periodo_id').filter(status=True, inicio__gte=hoy, nivel__periodo__tipo_id__in=[3, 4]).distinct()
                    periodosposgrado = Periodo.objects.filter(tipo_id__in=[3, 4], pk__in=listaperiodos).order_by('tipo_id', 'nombre')
                    data['periodosposgrado'] = periodosposgrado
                    return render(request, "pro_laboratoriocronograma/preferenciaposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'planificarhorario':
                try:
                    data['title'] = u'Seleccione el horario de preferencia'
                    data['periodo'] = periodo = request.session['periodo']
                    data['profesor'] = profesor
                    fecha = datetime.now().date()
                    if (fecha >= periodo.inicioprehorario and fecha <= periodo.finprehorario):
                        data['accesopreferencia'] = True
                    else:
                        data['accesopreferencia'] = False
                    data['turnos'] = Turno.objects.filter(sesion_id=1, status=True).distinct().order_by('comienza')
                    data['observacion'] = HorarioPreferenciaObse.objects.get(profesor=profesor, periodo=periodo) if HorarioPreferenciaObse.objects.filter(profesor=profesor, periodo=periodo).exists() else None
                    return render(request, "pro_laboratoriocronograma/prehorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'carreradistributivo':
                try:
                    coordinacion = Coordinacion.objects.get(pk=int(request.GET['id']))
                    carreras = Carrera.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(status=True, nivel__periodo=periodo, asignaturamalla__malla__carrera__coordinacion=coordinacion).distinct()).distinct()
                    lista = []
                    for ca in carreras:
                        lista.append([ca.id, "%s" % ca])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'carreradistributivoposgrado':
                try:
                    periodoposgrado = Periodo.objects.get(pk=int(request.GET['id']))
                    hoy = datetime.now().date()
                    carreras = Carrera.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(status=True, inicio__gte=hoy, nivel__periodo=periodoposgrado, asignaturamalla__malla__carrera__coordinacion=7).distinct()).distinct()
                    # carreras = Carrera.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(fin__gte=hoy, nivel__periodo=periodoposgrado).distinct()).distinct()
                    lista = []
                    for ca in carreras:
                        lista.append([ca.id, "%s" % ca])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'malladistributivo':
                try:
                    carrera = Carrera.objects.get(pk=int(request.GET['id']))
                    mallas = Malla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla').filter(status=True, nivel__periodo=periodo, asignaturamalla__malla__carrera=carrera).distinct()).distinct()
                    lista = []
                    for ca in mallas:
                        lista.append([ca.id, "%s" % ca])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'malladistributivoposgrado':
                try:
                    carrera = Carrera.objects.get(pk=int(request.GET['id']))
                    idperiodo = int(request.GET['idperiodo'])
                    hoy = datetime.now().date()
                    mallas = Malla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla').filter(status=True, fin__gte=hoy, nivel__periodo_id=idperiodo, asignaturamalla__malla__carrera=carrera).distinct()).distinct()
                    lista = []
                    for ca in mallas:
                        lista.append([ca.id, "%s" % ca])
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'abriract':
                try:
                    actividad = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    actividad.cerrado = False
                    actividad.save(request)
                    for participante in actividad.participanteactividadextracurricular_set.all():
                        participante.save(request)
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'addpractica':
                try:
                    data['title'] = u'Adicionar práctica pre-profesional'
                    # data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])), status=True, profesormateria__profesor=profesor, profesormateria__tipoprofesor_id__in=[TIPO_DOCENTE_PRACTICA, TIPO_DOCENTE_AYUDANTIA])
                    hoy = datetime.now().date()
                    iniciomateria = materia.inicio
                    finmateria = materia.fin
                    # if iniciomateria <= hoy and finmateria >= hoy:
                    form = PracticaPreProfesionalForm()
                    form.cargargrupoprofesor(materia, profesor)
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/addpractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarpractica':
                try:
                    data['title'] = u'Editar práctica pre-profesional'
                    practica = PracticaPreProfesional.objects.get(pk=request.GET['id'])
                    form = PracticaPreProfesionalForm(initial={'lugar': practica.lugar,
                                                               'horas': practica.horas,
                                                               'fecha': practica.fecha,
                                                               'objetivo': practica.objetivo,
                                                               'calificar': practica.calificar,
                                                               'califmaxima': practica.calfmaxima,
                                                               'grupopractica': practica.grupopractica,
                                                               'califminima': practica.calfminima})
                    form.deshabilitar_grupopractica()
                    data['form'] = form
                    data['practica'] = practica
                    return render(request, "pro_laboratoriocronograma/editarpractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delpractica':
                try:
                    data['title'] = u'Borrar práctica pre-profesional'
                    data['practica'] = PracticaPreProfesional.objects.get(pk=request.GET['id'])
                    return render(request, "pro_laboratoriocronograma/delpractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'retirarpractica':
                try:
                    participante = ParticipantePracticaPreProfesional.objects.get(pk=request.GET['id'])
                    practica = participante.practica
                    log(u'Retiro prarticipante practica pre-profesional: %s' % participante, request, "del")
                    participante.delete()
                    return HttpResponseRedirect("pro_laboratoriocronograma?action=calificarpractica&id=" + str(practica.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'retirarpry':
                try:
                    data['title'] = u'Elimnar participante'
                    participante = ParticipanteProyectoVinculacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['participante'] = participante
                    return render(request, "pro_laboratoriocronograma/retirarpry.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrarpractica':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    practica = PracticaPreProfesional.objects.get(pk=request.GET['ppp'])
                    participantepractica = ParticipantePracticaPreProfesional(practica=practica,
                                                                              materiaasignada=materiaasignada)
                    participantepractica.save(request)
                    log(u'Registro practicante practica pre-profesional: %s' % participantepractica, request, "edit")
                    return HttpResponseRedirect("pro_laboratoriocronograma?action=calificarpractica&id=" + str(practica.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'practicas':
                try:
                    data['title'] = u'Prácticas de Asignaturas'
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])), status=True, profesormateria__profesor=profesor, profesormateria__tipoprofesor_id__in=[TIPO_DOCENTE_PRACTICA, TIPO_DOCENTE_AYUDANTIA])
                    data['practicas'] = materia.practicapreprofesional_set.filter(profesor=profesor).order_by('-fecha')
                    data['persona'] = Persona.objects.get(usuario=request.user)
                    data['hoy'] = datetime.now().date()
                    return render(request, "pro_laboratoriocronograma/practicas.html", data)
                except Exception as ex:
                    pass

            # elif action == 'practicas':
            #     try:
            #         periodo = request.session['periodo']
            #         data['title'] = u'Prácticas de Asignaturas'
            #         data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
            #         data['silabosemanal'] = materia.silabo_set.filter(status=True)[0].silabosemanal_set.filter(status=True)
            #         data['form'] = PracticaMateriaForm()
            #         data['practicas'] = materia.practicapreprofesional_set.all().order_by('-fecha')
            #         data['persona'] = Persona.objects.get(usuario=request.user)
            #         data['hoy'] = datetime.now().date()
            #         data['materiaspracticas'] = Materia.objects.filter((Q(practicas=True) | Q(asignaturamalla__practicas=True)), profesormateria__profesor=profesor,
            #             nivel__periodo=periodo).distinct().exclude(profesormateria__tipoprofesor=TIPO_DOCENTE_FIRMA)
            #         return render(request, "pro_laboratoriocronograma/practicamateria.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'calificarpractica':
                try:
                    data['title'] = u'Calificación de práctica pre-profesional'
                    data['practica'] = practica = PracticaPreProfesional.objects.get(pk=request.GET['id'])
                    data['registrados'] = registrados = practica.participantepracticapreprofesional_set.all()
                    # data['no_registrados'] = MateriaAsignada.objects.filter(materia=practica.materia).exclude(matricula__inscripcion__in=[x.materiaasignada.matricula.inscripcion for x in registrados])
                    return render(request, "pro_laboratoriocronograma/calificarpractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'calificacionpry':
                try:
                    data['title'] = u'Calificación de proyecto de vinculación'
                    proyecto = ProyectosVinculacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['proyecto'] = proyecto
                    data['registrados'] = proyecto.participanteproyectovinculacion_set.all().order_by('inscripcion__persona')
                    return render(request, "pro_laboratoriocronograma/calificacionpry.html", data)
                except Exception as ex:
                    pass

            elif action == 'calificacioncurso':
                try:
                    search = None
                    data['title'] = u'Calificación de cursos o escuelas'
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=int(encrypt(request.GET['id'])),
                                                                            status=True, profesor=profesor)
                    data['materia'] = materia
                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 2:
                            data['registrados'] = materia.materiaasignadacurso_set.filter(
                                Q(inscripcion__inscripcion__persona__apellido1__icontains=s[0]) |
                                Q(inscripcion__inscripcion__persona__apellido1__icontains=s[1])).distinct().order_by('inscripcion__inscripcion__persona__apellido1')
                        else:
                            data['registrados'] = materia.materiaasignadacurso_set.filter(
                                Q(inscripcion__inscripcion__persona__apellido1__icontains=search) |
                                Q(inscripcion__inscripcion__persona__apellido1__icontains=search)).distinct().order_by('inscripcion__inscripcion__persona__apellido1')
                    else:
                        data['registrados'] = materia.materiaasignadacurso_set.all().order_by('inscripcion__inscripcion__persona__apellido1')

                    data['utiliza_validacion_calificaciones'] = variable_valor('UTILIZA_VALIDACION_CALIFICACIONES')
                    data['habilitado_ingreso_calificaciones'] = profesor.habilitado_ingreso_calificaciones()
                    data['search'] = search if search else ""
                    return render(request, "pro_laboratoriocronograma/calificacioncurso.html", data)
                except Exception as ex:
                    pass

            elif action == 'cerrarpry':
                try:
                    proyecto = ProyectosVinculacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    proyecto.cerrado = True
                    proyecto.save(request)
                    for participante in proyecto.participanteproyectovinculacion_set.all():
                        participante.save(request)
                    log(u'Cerrar proyecto de vinculacion: %s' % proyecto, request, "edit")
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'abrirpry':
                try:
                    proyecto = ProyectosVinculacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    proyecto.cerrado = False
                    proyecto.save(request)
                    for participante in proyecto.participanteproyectovinculacion_set.all():
                        participante.save(request)
                    log(u'Abrir proyecto de vinculacion: %s' % proyecto, request, "edit")
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'cerrarmateriacurso':
                try:
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=int(encrypt(request.GET['id'])))
                    materia.cerrada = True
                    materia.save(request)
                    for materiaasignada in materia.materiaasignadacurso_set.all():
                        materiaasignada.cierre_materia_asignada()
                        # materiaasignada.inscripcion.inscripcion.actualizar_nivel()
                    log(u'Cerrar materia de curso o escuela complementaria: %s' % materia, request, "edit")
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponseRedirect(f"{request.path}?info={str(ex)}")

            elif action == 'abrirmateriacurso':
                try:
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    materia.cerrada = False
                    materia.save(request)
                    for materiaasignada in materia.materiaasignadacurso_set.all():
                        materiaasignada.save(request)
                    log(u'Abrir materia de curso o escuela complementaria: %s' % materia, request, "edit")
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'cerrarppp':
                try:
                    practica = PracticaPreProfesional.objects.get(pk=request.GET['id'])
                    practica.cerrado = True
                    practica.save(request)
                    for participante in practica.participantepracticapreprofesional_set.all():
                        participante.save(request)
                    log(u'Cerrar practica pre-profesional: %s' % practica, request, "edit")
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'abrirppp':
                try:
                    practica = PracticaPreProfesional.objects.get(pk=request.GET['id'])
                    practica.cerrado = False
                    practica.save(request)
                    for participante in practica.participantepracticapreprofesional_set.all():
                        participante.save(request)
                    log(u'Abrir practica pre-profesional: %s' % practica, request, "edit")
                    return HttpResponseRedirect(request.path)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'subirevidencia':
                try:
                    data['title'] = u'Subir Evidencia'
                    fecha_ini, fecha_fin = request.GET.get('fechaini'), request.GET.get('fechafin')
                    detalledistributivo = DetalleDistributivo.objects.filter(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesor, status=True).first()

                    if 'ids' in request.GET:
                        data['subactividad'] = SubactividadDetalleDistributivo.objects.get(id=int(encrypt(request.GET['ids'])))

                    if conf := ConfiguracionInformePracticasPreprofesionales.objects.filter(pk=request.GET.get('conf')).first():
                        n = calendar.monthrange(conf.anio, conf.mes)[1]
                        fecha_ini = datetime(conf.anio, conf.mes, 1).date().__str__()
                        fecha_fin = datetime(conf.anio, conf.mes, n).date().__str__()
                        data['configuracion'] = conf

                    data['p'] = int(request.GET['p'])
                    fechaini = datetime.strptime(fecha_ini, '%Y-%m-%d').date()
                    fechafin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    data['detalledistributivo'] = detalledistributivo
                    form = EvidenciaActividadDetalleDistributivoForm(initial={'desde': fechaini, 'hasta': fechafin})
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/subirevidencia.html", data)
                    # data['actividaddetalledistributivo'] = ActividadDetalleDistributivo.objects.get(pk=request.GET['id'])
                    # data['actividaddetalledistributivo'] = ActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), criterio__distributivo__profesor=profesor, status=True)
                except Exception as ex:
                    pass

            elif action == 'editevidencia':
                try:
                    data['title'] = u'Modificar Evidencia'
                    evidenciaactividaddetalledistributivo = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), criterio__distributivo__profesor=profesor, status=True)

                    # if id_conf := request.GET.get('conf', None):
                    # # Generacion automatica de informe para ppp de internado rotativo
                    #      if docencia := evidenciaactividaddetalledistributivo.criterio.criteriodocenciaperiodo:
                    #          if docencia.criterio.pk == TUTOR_PRACTICAS_INTERNADO_ROTATIVO:
                    #              if conf := ConfiguracionInformePracticasPreprofesionales.objects.filter(pk=id_conf).first():
                    #                  if informe := generar_informe_practicas_preprofesionales(request=request, evidencia=evidenciaactividaddetalledistributivo, configuracion=conf, edit=True):
                    #                      evidenciaactividaddetalledistributivo.archivo.save(informe.archivodescargar.name.split('/')[-1], ContentFile(informe.archivodescargar.read()), save=True)
                    #                      evidenciaactividaddetalledistributivo.save(request)

                    data['evidenciaactividaddetalledistributivo'] = evidenciaactividaddetalledistributivo
                    data['listadoanexos'] = evidenciaactividaddetalledistributivo.anexoevidenciaactividad_set.filter(status=True)
                    data['conf'] = request.GET['conf'] if 'conf' in request.GET else 0
                    form = EvidenciaActividadDetalleDistributivoForm(initial={'desde': evidenciaactividaddetalledistributivo.desde,
                                                                              'hasta': evidenciaactividaddetalledistributivo.hasta,
                                                                              'actividad': evidenciaactividaddetalledistributivo.actividad})
                    data['form'] = form
                    data['subactividad'] = evidenciaactividaddetalledistributivo.subactividad
                    return render(request, "pro_laboratoriocronograma/editevidencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addanexoevidencia':
                try:
                    data['evidencia'] = tipo = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = AnexoEvidenciaActividadForm()
                    data['formanexo'] = form
                    template = get_template("pro_laboratoriocronograma/addanexoevidencia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addanexobitacora':
                try:
                    data['evidencia'] = tipo = DetalleBitacoraDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = AnexoEvidenciaActividadForm()
                    data['formanexo'] = form
                    template = get_template("pro_laboratoriocronograma/addanexoevidencia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addinforme':
                try:
                    data['evidencia'] = InformeMensualDocente.objects.get(pk=request.GET['id'])
                    form = InformeForm()
                    data['form'] = form
                    template = get_template("pro_laboratoriocronograma/addinforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verevidencia':
                try:
                    listadomeses = []
                    data['title'] = u'Ver Evidencia'
                    data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesor, status=True)
                    can_upload_evidence, can_delete_evidence = True, False
                    evidenciaactividaddetalledistributivo = EvidenciaActividadDetalleDistributivo.objects.filter(criterio=detalledistributivo, status=True).order_by('desde')
                    data['listado'] = listado = InformeMensualDocentesPPP.objects.filter(status=True, persona=profesor).order_by('-fechageneracion')
                    data['liscount'] = listado.count()
                    data['fechainicio'] = periodo.inicio
                    data['fechafin'] = datetime.now().date()
                    fechaactual, filtro = datetime.now().date(), Q(status=True)
                    ids, subactividad = 0, None
                    if 'ids' in request.GET:
                        data['subactividad'] = subactividad = SubactividadDetalleDistributivo.objects.get(id=int(encrypt(request.GET['ids'])))
                        evidenciaactividaddetalledistributivo = evidenciaactividaddetalledistributivo.filter(subactividad=subactividad)
                        ids = subactividad.subactividaddocenteperiodo.criterio.pk

                    if doc := detalledistributivo.criteriodocenciaperiodo:
                        filtro = Q(criterio__criteriodocenciaperiodo__criterio=doc.criterio)
                        can_upload_evidence = not doc.criterio.pk == CRITERIO_INTEGRANTE_PROYECTO_VINCULACION and not doc.criterio.pk == TUTOR_PRACTICAS_INTERNADO_ROTATIVO
                        can_delete_evidence = doc.criterio.pk == TUTOR_PRACTICAS_INTERNADO_ROTATIVO

                    if inv := detalledistributivo.criterioinvestigacionperiodo:
                        if ids in [CRITERIO_INTEGRANTE_GRUPOINVESTIGACION]:
                            data['integrante_grupo_inv'] = persona.grupoinvestigacionintegrante_set.filter(status=True).exclude(funcion=1).values('id').exists()
                        if ids in [CRITERIO_CODIRECTOR_PROYECTO_INV, CRITERIO_ASOCIADO_PROYECTO]:
                            data['integrante_proyecto_inv'] = persona.proyectoinvestigacionintegrante_set.filter(tiporegistro__in=[1, 3, 4], profesor__status=True, funcion__in=[2, 3], status=True).exclude(funcion=1).values('id').exists()
                        filtro = Q(criterio__criterioinvestigacionperiodo__criterio=inv.criterio)
                        if inv.criterio.id == 58:
                            can_upload_evidence = persona.grupoinvestigacionintegrante_set.filter(funcion=1, status=True).values('id').exists()
                        else:
                            can_upload_evidence = not inv.criterio.pk in list(map(int, variable_valor('CRITERIO_DIRECTOR_GRUPO_INVESTIGACION')))

                        if inv.criterio.id == 56:
                            if integrante := ProyectoInvestigacionIntegrante.objects.filter(tiporegistro__in=[1, 3, 4], persona=persona, funcion=2, status=True).first():
                                if lider := integrante.proyecto.integrantes_proyecto().filter(funcion=1).first():
                                    can_upload_evidence = not DetalleDistributivo.objects.values('id').filter(distributivo__activo=True, criterioinvestigacionperiodo__criterio__id=55, distributivo__profesor__persona=lider.persona, distributivo__periodo=periodo, status=True).exists()

                    if subactividad:
                        carga_evdiencia_codirector = False
                        if codirector := persona.proyectoinvestigacionintegrante_set.filter(tiporegistro__in=[1, 3, 4], funcion=2, status=True).first():
                            if lider := codirector.proyecto.integrantes_proyecto().filter(funcion=1).first():
                                carga_evdiencia_codirector = not SubactividadDetalleDistributivo.objects.values('id').filter(subactividaddocenteperiodo__criterio=CRITERIO_DIRECTOR_PROYECTO, actividaddetalledistributivo__criterio__distributivo__profesor__persona=lider.persona, subactividaddocenteperiodo__criterio__status=True, status=True).exists()
                        can_upload_evidence = subactividad.subactividaddocenteperiodo.cargaevidencia or carga_evdiencia_codirector

                    if ges := detalledistributivo.criteriogestionperiodo:
                        filtro = Q(criterio__criteriogestionperiodo__criterio=ges.criterio)

                    if vin := detalledistributivo.criteriovinculacionperiodo:
                        filtro = Q(criterio__criteriovinculacionperiodo__criterio=vin.criterio)

                    if actividad := detalledistributivo.actividaddetalledistributivo_set.filter(vigente=True, status=True).first():
                        fechas_mensuales = list(rrule(MONTHLY, dtstart=actividad.desde, until=actividad.hasta))
                    else:
                        fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.inicio, until=periodo.fin))

                    for i, fecha in enumerate(fechas_mensuales):
                        lastmonthday = calendar.monthrange(fecha.year, fecha.month)[1]
                        # Si el nuevo periodo inicia en los 5 ultimos días del mes se muestra la evidencia de la misma actividad del periodo pasado
                        if (lastmonthday - fecha.day) <= 5 and i == 0:
                            if evidencia := EvidenciaActividadDetalleDistributivo.objects.filter(Q(criterio__distributivo__profesor=profesor, hasta__month=fecha.month, hasta__year=fecha.year, status=True) & filtro).order_by('-id').first():
                                evidenciaactividaddetalledistributivo = [evidencia] + [e for e in evidenciaactividaddetalledistributivo]
                            continue
                        else:
                            primer_dia = fecha.replace(day=1)
                            ultimo_dia = fecha.replace(day=lastmonthday)
                            numeromes = fecha.month
                            anio = fecha.year
                            nomostrar = 0

                            for bita in evidenciaactividaddetalledistributivo:
                                if bita.hasta.month == fecha.month:
                                    nomostrar = 1

                            if inv and inv.criterio.pk == 58:
                                if gii := GrupoInvestigacionIntegrante.objects.filter(persona=persona, grupo__vigente=True, grupo__status=True, funcion=1, status=True).first():
                                    data['grupoinvestigacion'] = gii.grupo
                                    if not evidenciaactividaddetalledistributivo.filter(hasta__month=numeromes, grupoinvestigacion=gii.grupo).values('id').exists():
                                        nomostrar = 0

                            if nomostrar == 0:
                                if fechaactual >= primer_dia.date():
                                    listadomeses.append([primer_dia, anio, '01', str(numeromes), str(ultimo_dia.day)])

                    data['listadomeses'] = listadomeses
                    data['puede_subir_evidencia'] = can_upload_evidence
                    data['puede_eliminar_evidencia'] = can_delete_evidence
                    data['evidenciaactividaddetalledistributivo'] = evidenciaactividaddetalledistributivo
                    data['CRITERIO_PAR_EVALUADOR'] = CRITERIO_PAR_EVALUADOR
                    return render(request, "pro_laboratoriocronograma/verevidencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadobitacora':
                try:
                    data['title'] = u'Listado de registros de bitácora'
                    listadomeses, fechas_mensuales = [], []
                    dias_plazo_llenar_bitacora = variable_valor('PLAZO_DIAS_LLENAR_BITACORA_DOCENTE')
                    detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])))
                    es_actividad_macro = 'ids' in request.GET
                    subactividad = None
                    if es_actividad_macro:
                        data['subactividad'] = subactividad = SubactividadDetalleDistributivo.objects.get(id=request.GET['ids'])
                        fechas_mensuales = list(rrule(MONTHLY, dtstart=subactividad.fechainicio, until=subactividad.fechafin))
                    else:
                        if actividad := detalledistributivo.actividaddetalledistributivo_set.filter(vigente=True, status=True).first():
                            fechas_mensuales = list(rrule(MONTHLY, dtstart=actividad.desde, until=actividad.hasta))
                        else:
                            fechas_mensuales = list(rrule(MONTHLY, dtstart=periodo.inicio, until=periodo.fin))

                    registrobitacoras = BitacoraActividadDocente.objects.filter(criterio=detalledistributivo, subactividad=subactividad, status=True).order_by('fechaini').annotate(fechamaxima=ExpressionWrapper(F('fechafin') + timedelta(days=dias_plazo_llenar_bitacora), output_field=DateTimeField()))
                    data['evidenciaactividaddetalledistributivo'] = registrobitacoras.filter(fechamaxima__gte=datetime.now())
                    fechaactual = datetime.now().date()
                    fechabitacora = "2023-05-31"  # Desde esta fecha la evidencias de llenar bitacora comenzaron a llenar, fechas atras llenaban informes
                    fechabitacora = datetime.strptime(fechabitacora, "%Y-%m-%d").date()
                    for fecha in fechas_mensuales:
                        ultimo_dia = fecha.replace(day=calendar.monthrange(fecha.year, fecha.month)[1])
                        primer_dia = fecha.replace(day=1)
                        numeromes = fecha.month
                        anio = fecha.year
                        nomostrar = 0

                        # Genera cabecera de bitácora
                        tienebitacoraperiodoactual = BitacoraActividadDocente.objects.values('id').filter(criterio=detalledistributivo, subactividad=subactividad, fechafin__month=ultimo_dia.month, fechafin__year=ultimo_dia.year, profesor=profesor, status=True).exists()
                        if primer_dia.date() <= datetime.now().date() and not tienebitacoraperiodoactual:
                            mesbitacora = BitacoraActividadDocente(subactividad=subactividad, profesor=profesor, criterio=detalledistributivo, nombre='REGISTRO DE BITÁCORA MES DE: ' + MESES_CHOICES[ultimo_dia.month - 1][1].upper(), fechaini=primer_dia, fechafin=ultimo_dia)
                            mesbitacora.save(request)
                            mesbitacora.get_horasplanificadas()
                            h = HistorialBitacoraActividadDocente(bitacora=mesbitacora, persona=persona, estadorevision=mesbitacora.estadorevision)
                            h.save(request)
                            nomostrar = 1
                        # -------------------------------------------------------------------------

                        for bita in registrobitacoras:
                            if bita.fechaini.month == fecha.month:
                                nomostrar = 1

                        if nomostrar == 0 and fechaactual >= primer_dia.date():
                            if ultimo_dia.date() > fechabitacora:
                                listadomeses.append([primer_dia, anio, '01', str(numeromes), str(ultimo_dia.day), ultimo_dia.date() + timedelta(days=dias_plazo_llenar_bitacora)])

                    data['periodo'] = periodo
                    data['fechaactual'] = fechaactual
                    data['listadomeses'] = listadomeses
                    data['detalledistributivo'] = detalledistributivo
                    data['bitacoras'] = registrobitacoras.filter(fechamaxima__lte=datetime.now(), fecha_creacion__gte=fechabitacora)
                    return render(request, "pro_laboratoriocronograma/listadobitacora.html", data)
                except Exception as ex:
                    pass

            elif action == 'detallebitacora':
                try:
                    data['title'] = u'Listado actividades bitacora'

                    dias_plazo_llenar_bitacora = variable_valor('PLAZO_DIAS_LLENAR_BITACORA_DOCENTE')
                    valida_registro_tardio_bitacora, now = False, datetime.now().date()
                    puede_modificar_bitacora, puede_enviar_a_revision = True, True

                    mesbitacora = BitacoraActividadDocente.objects.get(pk=int(encrypt(request.GET['idbitacora'])))
                    if 'idbitacora' in request.GET:
                        data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=mesbitacora.criterio.id, distributivo__profesor=profesor, status=True)
                        if variable_valor('VALIDA_REGISTRO_BITACORA_PPPIR'):
                            mes = mesbitacora.fechafin.month
                            fecha = date(now.year, mes, calendar.monthrange(now.year, mes)[1]) + timedelta(days=dias_plazo_llenar_bitacora)
                            puede_modificar_bitacora = now <= fecha

                    # data['listadodetalle'] = mesbitacora.detallebitacoradocente_set.filter(status=True).annotate(
                    #     diferencia_horas=Extract('horafin', 'hour') - Extract('horainicio', 'hour'),
                    #     diferencia_minutos=Extract('horafin', 'minute') - Extract('horainicio', 'minute')
                    # ).annotate(cantidad_horas=(F('diferencia_horas') + F('diferencia_minutos') / 60))
                    data['mesbitacora'] = mesbitacora
                    data['listadodetalle'] = listadodetalle = mesbitacora.detallebitacoradocente_set.filter(status=True).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')
                    totalhorasplanificadas = mesbitacora.get_horasplanificadas()
                    totalhorasregistradas, totalhorasaprobadas, porcentaje_cumplimiento = mesbitacora.get_horasregistradas(), 0, 0

                    if th := listadodetalle.filter(estadoaprobacion=2, status=True).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                        totalhorasaprobadas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    if totalhorasplanificadas:
                        if mesbitacora.estadorevision == 3:
                            porcentaje_cumplimiento = 100 if totalhorasaprobadas > totalhorasplanificadas else round((totalhorasaprobadas / totalhorasplanificadas) * 100, 2)
                        else:
                            porcentaje_cumplimiento = 100 if totalhorasregistradas > totalhorasplanificadas else round((totalhorasregistradas / totalhorasplanificadas) * 100, 2)

                    if c := mesbitacora.criterio.criteriodocenciaperiodo:
                        if c.criterio.pk == 167:
                            puede_enviar_a_revision = False

                    data['idsubactividad'] = request.GET.get('ids')
                    data['totalhorasaprobadas'] = totalhorasaprobadas
                    data['totalhorasregistradas'] = totalhorasregistradas
                    data['totalhorasplanificadas'] = totalhorasplanificadas
                    data['puede_enviar_a_revision'] = puede_enviar_a_revision
                    data['porcentaje_cumplimiento'] = porcentaje_cumplimiento
                    data['valida_registro_tardio_bitacora'] = valida_registro_tardio_bitacora
                    data['puede_modificar_bitacora'] = puede_modificar_bitacora and mesbitacora.estadorevision == 1
                    return render(request, "pro_laboratoriocronograma/detallebitacora.html", data)
                except Exception as ex:
                    return JsonResponse({"result": False, "aData": {}, "message": '{} - Error on line {}'.format(str(ex), sys.exc_info()[-1].tb_lineno)})

            elif action == 'detalleregistrobitacora':
                try:
                    data = {}
                    data['detalle'] = detalle = DetalleBitacoraDocente.objects.get(pk=int(request.GET['id']))
                    data['detalledepartamento'] = detalle.departamentobitacora_set.filter(status=True)
                    data['detallepersona'] = detalle.personabitacora_set.filter(status=True)
                    data['anexodetallebitacora'] = detalle.anexodetallebitacoradocente_set.filter(status=True)
                    template = get_template("pro_laboratoriocronograma/detalleregistrobitacora.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addpersonabitacora':
                try:
                    data['detalle'] = DetalleBitacoraDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = UsuarioRevisaEvidenciaDocenteForm()
                    form.ocultar_campo('rol')
                    data['formaddpersona'] = form
                    template = get_template("pro_laboratoriocronograma/addpersonabitacora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addbitacora':
                try:
                    data['title'] = u'Adicionar bitácora'
                    mesbitacora = BitacoraActividadDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['detalledistributivo'] = mesbitacora.criterio.id
                    form = BitacoraActividadForm(initial={'fecha': mesbitacora.fechaini.date()}, bitacora=mesbitacora)
                    if form.fields.get('persona'):
                        form.fields['persona'].queryset = Persona.objects.none()
                    data['form'] = form
                    data['mesbitacora'] = mesbitacora
                    data['mBitacora'] = "%02d" % mesbitacora.fechaini.month
                    data['actividadarticulocientifico'] = mesbitacora.subactividad and mesbitacora.subactividad.subactividaddocenteperiodo.criterio.pk == CRITERIO_ELABORA_ARTICULO_CIENTIFICO
                    return render(request, "pro_laboratoriocronograma/addbitacora.html", data)
                    # return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editbitacora':
                try:
                    data['title'] = u'Modificar bitácora'
                    data['detallebitacora'] = detallebitacora = DetalleBitacoraDocente.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    departamentos = Departamento.objects.filter(pk__in=detallebitacora.departamentobitacora_set.values_list('departamento_id', flat=True).filter(status=True))
                    data['listadopersona'] = detallebitacora.personabitacora_set.filter(status=True).order_by('persona__apellido1', 'persona__apellido2')
                    form = BitacoraActividadForm(initial={'titulo': detallebitacora.titulo,
                                                          'fecha': detallebitacora.fecha.date(),
                                                          'hora': detallebitacora.horainicio,
                                                          'horafin': detallebitacora.horafin,
                                                          'descripcion': detallebitacora.descripcion,
                                                          'departamento': departamentos,
                                                          'link': detallebitacora.link}, bitacora=detallebitacora.bitacoradocente)
                    if form.fields.get('persona'):
                        form.fields['persona'].queryset = Persona.objects.none()
                        form.ocultarcampos()
                    data['form'] = form
                    data['anexos'] = detallebitacora.anexodetallebitacoradocente_set.filter(status=True)
                    return render(request, "pro_laboratoriocronograma/editbitacora.html", data)
                except Exception as ex:
                    pass

            if action == 'buscarpersonas':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    filter = Q(Q(Q(profesor__isnull=False) | Q(administrativo__isnull=False)) & Q(status=True))
                    if len(s) == 1: filter &= Q(Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q))
                    if len(s) == 2: filter &= Q(Q(Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) | (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1])))
                    if len(s) > 2: filter &= Q((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2])))

                    return JsonResponse({"result": "ok", "results": [{"id": x.id, "name": "{}".format(x.nombre_completo())} for x in Persona.objects.filter(filter).order_by('apellido1')[:15]]})
                except Exception as ex:
                    pass

            elif action == 'subircronograma':
                try:
                    data['title'] = u'Subir Cronograma de actividades'
                    data['detalledistributivo'] = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesor, status=True)
                    data['form'] = DetalleDistributivoForm()
                    return render(request, "pro_laboratoriocronograma/subirconograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteevidencia':
                try:
                    data['title'] = u'Eliminar Evidencia'
                    # data['evidenciaactividaddetalledistributivo'] = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(request.GET['id']))
                    data['evidenciaactividaddetalledistributivo'] = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), criterio__distributivo__profesor=profesor, status=True)
                    return render(request, "pro_laboratoriocronograma/deleteevidencia.html", data)
                except:
                    pass

            elif action == 'aprobarevidenciasactividades':
                try:
                    data['title'] = u'Evidencias de las actividades'
                    periodo = request.session['periodo']
                    # puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    coordinaciones = Coordinacion.objects.all()
                    data['periodo'] = periodo
                    data['permite_modificar'] = False
                    encargadocriterioperiododocencia = EncargadoCriterioPeriodo.objects.filter(periodo=periodo, profesor=profesor, criteriodocencia__isnull=False).distinct()
                    encargadocriterioperiodoinvestigacion = EncargadoCriterioPeriodo.objects.filter(periodo=periodo, profesor=profesor, criterioinvestigacion__isnull=False).distinct()
                    encargadocriterioperiodogestion = EncargadoCriterioPeriodo.objects.filter(periodo=periodo, profesor=profesor, criteriogestion__isnull=False).distinct()
                    data['evidenciaactividaddetalledistributivodocencia'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__periodo=periodo, criterio__criteriodocenciaperiodo__criterio__encargadocriterioperiodo__in=encargadocriterioperiododocencia, criterio__distributivo__profesor__coordinacion__encargadocriterioperiodo__in=encargadocriterioperiododocencia).distinct().order_by('criterio__distributivo__profesor', 'desde')
                    data['evidenciaactividaddetalledistributivoinvestigacion'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__periodo=periodo, criterio__criterioinvestigacionperiodo__criterio__encargadocriterioperiodo__in=encargadocriterioperiodoinvestigacion, criterio__distributivo__profesor__coordinacion__encargadocriterioperiodo__in=encargadocriterioperiodoinvestigacion).distinct().order_by('criterio__distributivo__profesor', 'desde')
                    data['evidenciaactividaddetalledistributivogestion'] = EvidenciaActividadDetalleDistributivo.objects.filter(criterio__distributivo__periodo=periodo, criterio__criteriogestionperiodo__criterio__encargadocriterioperiodo__in=encargadocriterioperiodogestion, criterio__distributivo__profesor__coordinacion__encargadocriterioperiodo__in=encargadocriterioperiodogestion).distinct().order_by('criterio__distributivo__profesor', 'desde')
                    return render(request, "pro_laboratoriocronograma/aprobarevidenciasactividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobar':
                try:
                    data['title'] = u'Aprobar Evidencias'
                    periodo = request.session['periodo']
                    # puede_realizar_accion(request, 'sga.puede_modificar_criteriosdocentes')
                    data['evidenciaactividaddetalledistributivo'] = EvidenciaActividadDetalleDistributivo.objects.filter(pk=int(request.GET['id']))[0]
                    return render(request, "pro_laboratoriocronograma/aprobar.html", data)
                except Exception as ex:
                    pass

            elif action == 'cronograma':
                try:
                    data['title'] = u'Cronograma'
                    data['fechaactual'] = datetime.now().date()
                    data['actividad'] = actividad = PaeActividadesPeriodoAreas.objects.get(pk=int(encrypt(request.GET['idactividad'])))
                    data['fechaactividades'] = PaeFechaActividad.objects.filter(tutor=profesor, actividad=actividad, status=True)
                    return render(request, "pro_laboratoriocronograma/cronograma.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasistencia':
                try:
                    data['title'] = u'Asistencia'
                    data['fechaactividades'] = fechaactividad = PaeFechaActividad.objects.get(pk=int(encrypt(request.GET['idfechaactividad'])))
                    data['listaconasistencia'] = PaeAsistenciaFechaActividad.objects.filter(actividadfecha=fechaactividad, asistencia=True, status=True)
                    data['listadoinscritos'] = PaeInscripcionActividades.objects.filter(actividades=fechaactividad.actividad, status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    return render(request, "pro_laboratoriocronograma/listadoinscritos.html", data)
                except Exception as ex:
                    pass

            elif action == 'aadtutoriaclase':
                try:
                    data['title'] = u'Tutorías y Acompañamiento Académico'
                    # data['materia'] = materia = Materia.objects.get(pk=int(request.GET['id']))
                    data['materia'] = materia = Materia.objects.filter(pk=int(encrypt(request.GET['id'])), status=True, profesormateria__profesor=profesor, profesormateria__activo=True).order_by('profesormateria__tipoprofesor__id')[0]
                    # data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])), status=True, profesormateria__profesor=profesor, profesormateria__activo=True)
                    form = AvTutoriasForm()
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/avtutorias/addtutoriaclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittutoriaclase':
                try:
                    data['title'] = u'Tutorías y Acompañamiento Académico'
                    # data['avtutorias'] = avtutorias = AvTutorias.objects.get(pk=int(request.GET['id']))
                    data['avtutorias'] = avtutorias = AvTutorias.objects.get(pk=int(encrypt(request.GET['id'])), status=True, materia__profesormateria__profesor=profesor, materia__profesormateria__activo=True)
                    form = AvTutoriasForm(initial={'observacion': avtutorias.observacion})
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/avtutorias/edittutoriaclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletutoriaclase':
                try:
                    data['title'] = u'Eliminar Evidencia'
                    # data['avtutorias'] = AvTutorias.objects.get(pk=int(request.GET['id']))
                    data['avtutorias'] = AvTutorias.objects.get(pk=int(encrypt(request.GET['id'])), status=True, materia__profesormateria__profesor=profesor, materia__profesormateria__activo=True)
                    return render(request, "pro_laboratoriocronograma/avtutorias/deletutoriaclase.html", data)
                except:
                    pass

            elif action == 'tutoriaclase':
                try:
                    data['title'] = u'Tutorías y Acompañamiento Académico'
                    # data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['materia'] = materia = Materia.objects.filter(pk=int(encrypt(request.GET['id'])), status=True, profesormateria__profesor=profesor, profesormateria__activo=True).order_by('profesormateria__tipoprofesor__id')[0]
                    if not materia:
                        return HttpResponseRedirect("/?info=Ud. aun no ha seleccionado una materia.")
                    tutorias = AvTutorias.objects.filter(materia=materia).order_by('-fecha')
                    paging = Paginator(tutorias, 30)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['page'] = page
                    data['tutorias'] = page.object_list
                    return render(request, "pro_laboratoriocronograma/avtutorias/view.html", data)
                except Exception as ex:
                    pass

            elif action == 'calificar':
                try:
                    data['title'] = u'Calificar'
                    data['fechaactual'] = datetime.now().date()
                    data['actividad'] = actividad = PaeActividadesPeriodoAreas.objects.get(pk=int(encrypt(request.GET['idactividad'])), status=True)
                    data['fechaactividades'] = PaeFechaActividad.objects.filter(tutor=profesor, actividad=actividad, status=True)
                    data['listadoinscritos'] = PaeInscripcionActividades.objects.filter(actividades=int(encrypt(request.GET['idactividad'])), status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    return render(request, "pro_laboratoriocronograma/listainscritocalificar.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirarchivos':
                try:
                    opc = request.GET['opc']
                    data['id'] = request.GET['id']
                    if 'tipo' in request.GET:
                        data['tipo'] = request.GET['tipo']
                    if opc == '1':
                        data['title'] = u'Evidencias de Prácticas Pre Profesionales'
                        data['practicas'] = practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])
                        data['evidencias'] = practicas.periodoppp.evidencias_practica()
                        # data['formevidencias'] = EvidenciaPracticasForm()
                        return render(request, "pro_laboratoriocronograma/evidenciaspracticas.html", data)
                    elif opc == '2':
                        data['title'] = u'Evidencias de Prácticas Pre Profesionales'
                        data['practicas'] = practicas = PracticasPreprofesionalesInscripcion.objects.get(pk=request.GET['id'])
                        data['evidencias'] = practicas.periodoppp.evidencias_practica()
                        data['essupervisor'] = practicas.supervisor == profesor
                        return render(request, "pro_laboratoriocronograma/evidenciaspracticassupervisor.html", data)
                except Exception as ex:
                    pass

            elif action == 'addapruebaevidencias':
                try:
                    data['title'] = u'Aprobar o Rechazar'
                    data['form'] = ArpobarEvidenciaPracticasForm()
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    data['idpracins'] = request.GET['idpracins']
                    data['opc'] = 2
                    template = get_template("pro_laboratoriocronograma/modal/formmodal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'aprobarrechazartutor':
                try:
                    data['title'] = u'Aprobar / Rechazar Evidencia '
                    data['form'] = AprobarRechazarEvidenciaTutorForm
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    data['modal'] = 'aprobarrechazartutor'
                    template = get_template("pro_laboratoriocronograma/modal/formmodal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'ponerfechalimite':
                try:
                    data['title'] = u'Asignar fechas para subir evidencia'
                    form = PonerFechaLimiteEvidenciaForm()
                    if d := DetalleEvidenciasPracticasPro.objects.filter(pk=request.GET.get('idd')).first():
                        form = PonerFechaLimiteEvidenciaForm(initial={'fechainicio': d.fechainicio, 'fechafin': d.fechafin})

                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['idevidencia'] = request.GET['idevidencia']
                    data['modal'] = 'ponerfechalimite'
                    template = get_template("pro_laboratoriocronograma/modal/formmodal.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'listatutorias':
                try:
                    data['title'] = u'Tutorías de Prácticas Pre Profesionales'
                    search = None
                    tipo = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.filter(Q(inscripcion__persona__cedula__icontains=search), status=True,
                                                                                                    tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                        else:
                            search = request.GET['s'].strip()
                            ss = search.split(' ')
                            if len(ss) == 1:
                                tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                    Q(inscripcion__persona__apellido1__icontains=search) |
                                    Q(inscripcion__persona__apellido2__icontains=search) |
                                    Q(inscripcion__persona__nombres__icontains=search),
                                    status=True, tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                            else:
                                tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.select_related().filter(
                                    Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                    Q(inscripcion__persona__apellido2__icontains=ss[1]),
                                    status=True, tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.filter(pk=ids, status=True, tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                    else:
                        tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.select_related().filter(status=True, tutorunemi=profesor, culminada=False).distinct().exclude(estadosolicitud=3).order_by('-fecha_creacion').distinct()

                    if 'tipo' in request.GET:
                        tipo = int(request.GET['tipo'])
                        search1 = int(request.GET['tipo'])
                        if search1 != 0:
                            if search1 == 10:
                                tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.filter(
                                    culminada=True, status=True, tutorunemi=profesor).order_by('-fecha_creacion').distinct()
                            else:
                                if search1 == 11:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    sql = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and evid.estadotutor=0 and evid.estadorevision=1 and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13)"
                                    cursor.execute(sql)
                                    results = cursor.fetchall()
                                    for r in results:
                                        llenardocentes.append(r[0])
                                    tutoriaspracticas = tutoriaspracticas.filter(pk__in=llenardocentes, status=True).order_by('-fecha_creacion')
                                elif search1 == 12:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    # sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and evid.estadorevision=3 and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13)"
                                    sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13) and evid.fechainicio is not null and evid.fechafin is not null and evid.estadotutor=0 group by ins.id"
                                    cursor.execute(sql1)
                                    results = cursor.fetchall()
                                    for r in results:
                                        llenardocentes.append(r[0])
                                    tutoriaspracticas = tutoriaspracticas.filter(pk__in=llenardocentes, status=True).order_by('-fecha_creacion')
                                elif search1 == 13:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    # sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and evid.estadorevision=3 and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13)"
                                    sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.tutorunemi_id=" + str(profesor.id) + " and evid.evidencia_id in (9,10,11,13) and (evid.estadorevision=3 or evid.estadotutor=3 ) group by ins.id"
                                    cursor.execute(sql1)
                                    results = cursor.fetchall()
                                    for r in results:
                                        llenardocentes.append(r[0])
                                    tutoriaspracticas = tutoriaspracticas.filter(pk__in=llenardocentes, status=True).order_by('-fecha_creacion')
                                elif search1 == 14:
                                    tutoriaspracticas = tutoriaspracticas.filter(estadosolicitud=1, culminada=False, status=True).order_by('-fecha_creacion')
                    data['carrerasdocente'] = Carrera.objects.filter(pk__in=tutoriaspracticas.values_list('inscripcion__carrera', flat=True))
                    paging = MiPaginador(tutoriaspracticas, 10)
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
                    data['tutoriaspracticas'] = page.object_list
                    data['search'] = search if search else ""
                    data['tipo'] = tipo if tipo else ""
                    data['ids'] = ids if ids else ""
                    data['meses'] = ConfiguracionInformePracticasPreprofesionales.objects.filter(status=True, persona=profesor).order_by('-mes', '-anio')
                    data['anioactual'] = anioactual = datetime.now().year
                    data['formatospractica'] = FormatoPracticaPreProfesional.objects.filter(status=True, vigente=True)
                    data['archivosgenerales'] = ArchivoGeneralPracticaPreProfesionales.objects.filter(status=True, visible=True)
                    return render(request, "pro_laboratoriocronograma/listatutorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'listasupervisionayudantia':
                try:
                    data['periodocatedra'] = periodocatedra = PeriodoCatedra.objects.filter(periodolectivo=periodo, status=True)[0]
                    data['title'] = u'SEGUIMIENTO  - ' + periodocatedra.nombre

                    idcarrera = 0
                    # carrera
                    data['carreras'] = carreras1 = Carrera.objects.filter(inscripcion__inscripcioncatedra__supervisor__persona=persona, inscripcion__inscripcioncatedra__periodocatedra=periodocatedra, inscripcion__inscripcioncatedra__isnull=False, inscripcion__inscripcioncatedra__status=True).distinct()
                    if 'idcarrera' in request.GET:
                        idcarrera = request.GET['idcarrera']
                    else:
                        if carreras1:
                            idcarrera = carreras1[0].id

                    data['idcarrera'] = idcarrera
                    return render(request, "pro_laboratoriocronograma/seguimiento.html", data)
                except Exception as ex:
                    pass

            elif action == 'evidenciainformesmmensual':
                try:
                    data['title'] = u'EVIDENCIAS INFORMES MENSUALES'
                    data['listado'] = listado = InformeMensualDocentesPPP.objects.filter(status=True, persona=profesor).order_by('-fechageneracion')
                    data['liscount'] = listado.count()
                    return render(request, "pro_laboratoriocronograma/evidenciainformes.html", data)
                except Exception as ex:
                    pass

            elif action == 'actividades':
                try:
                    data['inscripcioncatedra'] = inscripcioncatedra = InscripcionCatedra.objects.get(pk=request.GET['idinscripcion'])
                    data['actividadinscripcioncatedras'] = inscripcioncatedra.actividadinscripcioncatedra_set.filter(status=True).order_by('-id')
                    data['title'] = u'AYUDANTIA DE CATEDRA  - ' + inscripcioncatedra.materia.asignatura.nombre + ' - ' + inscripcioncatedra.inscripcion.persona.nombre_completo_inverso()

                    template = get_template("pro_laboratoriocronograma/actividades.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'verasistencia':
                try:
                    data['actividadinscripcioncatedra'] = actividadinscripcioncatedra = ActividadInscripcionCatedra.objects.get(pk=request.GET['idactividad'])
                    data['asistenciaactividadinscripcioncatedras'] = actividadinscripcioncatedra.asistenciaactividadinscripcioncatedra_set.filter(status=True).order_by('inscripcionalumno__persona__apellido1', 'inscripcionalumno__persona__apellido2')

                    template = get_template("pro_laboratoriocronograma/verasistencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'listasupervision':
                try:
                    data['title'] = u'Supervisión de Prácticas Pre Profesionales'
                    filter, url_vars = Q(supervisor=profesor, status=True), '&action=listasupervision'
                    if search := request.GET.get('s', None):
                        data['s'] = search.strip()
                        url_vars += f'&s={search}'
                        if search.isdigit():
                            filter &= Q(Q(inscripcion__persona__cedula__icontains=search), status=True, supervisor=profesor)
                        else:
                            ss = search.split(' ')
                            if len(ss) == 1:
                                filter &= Q(Q(inscripcion__persona__apellido1__icontains=search) | Q(inscripcion__persona__apellido2__icontains=search) | Q(inscripcion__persona__nombres__icontains=search), status=True, supervisor=profesor)
                            else:
                                filter &= Q(Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(inscripcion__persona__apellido2__icontains=ss[1]), status=True, supervisor=profesor)

                    if ids := request.GET.get('id', None):
                        data['ids'] = ids
                        filter &= Q(pk=ids)
                        url_vars += f'&id={ids}'

                    if tipo := request.GET.get('tipo', 0):
                        url_vars += f'&tipo={tipo}'
                        data['tipo'] = search1 = int(tipo)
                        if search1 != 0:
                            if search1 == 10:
                                filter &= Q(culminada=True, status=True)
                            else:
                                if search1 == 11:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.supervisor_id=" + str(profesor.id) + " and evid.fechainicio is null and evid.fechafin is null group by ins.id"
                                    cursor.execute(sql1)
                                    results = cursor.fetchall()
                                    for r in results: llenardocentes.append(r[0])
                                    filter &= Q(pk__in=llenardocentes)
                                if search1 == 12:
                                    llenardocentes = []
                                    cursor = connection.cursor()
                                    sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.supervisor_id=" + str(profesor.id) + " and evid.fechainicio is not null and evid.fechafin is not null group by ins.id"
                                    cursor.execute(sql1)
                                    results = cursor.fetchall()
                                    for r in results: llenardocentes.append(r[0])
                                    filter &= Q(pk__in=llenardocentes)
                                if search1 == 13:
                                    cursor = connection.cursor()
                                    sql1 = "select ins.id from sga_practicaspreprofesionalesinscripcion ins,sga_detalleevidenciaspracticaspro evid where ins.id=evid.inscripcionpracticas_id and ins.status=true and evid.status=True and ins.supervisor_id=" + str(profesor.id) + " and  (evid.estadorevision=3 or evid.estadotutor=3)  group by ins.id"
                                    cursor.execute(sql1)
                                    results = cursor.fetchall()
                                    llenardocentes = [r[0] for r in results]
                                    filter &= Q(pk__in=llenardocentes)
                                if search1 == 14:
                                    filter &= Q(estadosolicitud=1, culminada=False)

                    paging = MiPaginador(PracticasPreprofesionalesInscripcion.objects.filter(filter).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres').distinct(), 10)
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
                    data['fechaactual'] = datetime.now().date().strftime('%d-%m-%Y')
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['supervisorpracticas'] = page.object_list
                    data['url_vars'] = url_vars
                    data['formatospractica'] = FormatoPracticaPreProfesional.objects.filter(status=True, vigente=True)
                    data['archivosgenerales'] = ArchivoGeneralPracticaPreProfesionales.objects.filter(status=True, visible=True)
                    data['detalledistributivo'] = DetalleDistributivo.objects.filter(distributivo__periodo=periodo, distributivo__profesor=profesor, distributivo__status=True, status=True).first()
                    return render(request, "pro_laboratoriocronograma/listasupervision.html", data)
                except Exception as ex:
                    pass

            elif action == 'configurarfechamasiva':
                try:
                    data['title'] = u'Configuración de fechas masiva de prácticas'
                    form = ConfigurarFechaMasivaPracticaForm()
                    form.configuracion_inicial()
                    if profesor.coordinacion.id == 1:
                        del form.fields['aplicarpractica']
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/configurarfechamasivapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'tomaronm':
                try:
                    data['title'] = u'Matriculados en la asignatura'
                    data['periodo'] = periodo
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['materia'])))
                    data['materiasasignadas'] = materia.materiaasignada_set.filter(matricula__estado_matricula__in=[2, 3], status=True).order_by('matricula__inscripcion__persona')
                    return render(request, "pro_laboratoriocronograma/tomandom.html", data)
                except Exception as ex:
                    pass

            elif action == 'retiro':
                try:
                    data['title'] = u'Retiro de Prácticas Pre Profesionales'
                    data['id'] = request.GET['id']
                    data['practicaspreprofesionalesinscripcion'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    form = RetiroPracticasForm()
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/retiro.html", data)
                except Exception as ex:
                    pass

            elif action == 'excelpracticas':
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
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Listas_Practicas' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 3000),
                        (u"PERIODO ACADEMICO", 4500),
                        (u"CEDULA", 3000),
                        (u"ESTUDIANTE", 10000),
                        (u"CELULAR", 3000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INSTITUCIONAL", 10000),
                        (u"EGRESADO", 2000),
                        (u"TIPO PRACTICAS", 3000),
                        (u"TUTOR ACADÉMICO", 3000),
                        (u"TUTOR PROFESIONAL", 3000),
                        (u"SUPERVISOR", 3000),
                        (u"FECHA DESDE", 3000),
                        (u"FECHA HASTA", 3000),
                        (u"HORAS PRACTICAS", 2000),
                        (u"HORAS HOMOLOGACIÓN", 2000),
                        (u"INSTITUCION", 13000),
                        (u"OTRA EMPRESA", 13000),
                        (u"TIPO INSTITUCION", 3000),
                        (u"SECTOR ECONOMICO", 6500),
                        (u"PRACTICAS CULMINADAS", 2000),
                        (u"EVIDENCIAS APROBADAS / TOTAL ", 2000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listapracticas = PracticasPreprofesionalesInscripcion.objects.select_related().filter(status=True, tutorunemi=profesor).order_by('inscripcion__persona__apellido1')
                    row_num = 4
                    i = 0
                    for practicas in listapracticas:
                        campo1 = practicas.inscripcion.coordinacion.nombre
                        campo2 = practicas.inscripcion.carrera.nombre_completo()
                        campo3 = ''
                        campo4 = ''
                        if practicas.inscripcion.nivelperiodo(periodo):
                            matriculado = practicas.inscripcion.nivelperiodo(periodo)
                            campo3 = matriculado.nivelmalla.nombre
                            campo4 = matriculado.nivel.periodo.nombre
                        campo5 = practicas.inscripcion.persona.cedula
                        campo6 = practicas.inscripcion.persona.nombre_completo_inverso()
                        campo7 = practicas.inscripcion.persona.telefono + " - " + practicas.inscripcion.persona.telefono_conv
                        campo8 = practicas.inscripcion.persona.email
                        campo9 = practicas.inscripcion.persona.emailinst
                        if practicas.inscripcion.egresado():
                            campo10 = 'SI'
                        else:
                            campo10 = 'NO'
                        campo11 = practicas.get_tipo_display()
                        campo12 = practicas.tutorunemi.persona.nombre_completo_inverso() if practicas.tutorunemi else ""
                        campo13 = practicas.tutorempresa if practicas.tutorempresa else ""
                        campo14 = practicas.supervisor.persona.nombre_completo_inverso() if practicas.supervisor else ""
                        campo15 = practicas.fechadesde if practicas.fechadesde else ""
                        campo16 = practicas.fechahasta if practicas.fechahasta else ""
                        campo17 = practicas.numerohora
                        campo18 = practicas.horahomologacion
                        campo19 = practicas.empresaempleadora.nombre if practicas.empresaempleadora else ""
                        campo20 = practicas.otraempresaempleadora if practicas.otraempresaempleadora else ""
                        campo21 = practicas.get_tipoinstitucion_display()
                        campo22 = practicas.get_sectoreconomico_display()
                        if practicas.culminada:
                            campo23 = 'SI'
                        else:
                            campo23 = 'NO'
                        if practicas.fechadesde:
                            campo24 = str(practicas.evidenciasaprobadas()) + ' / ' + str(practicas.totalevidencias())
                        else:
                            campo24 = "0/0"
                        ws.write(row_num, 0, campo1, font_style2)
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
                        ws.write(row_num, 14, campo15, date_format)
                        ws.write(row_num, 15, campo16, date_format)
                        ws.write(row_num, 16, campo17, font_style2)
                        ws.write(row_num, 17, campo18, font_style2)
                        ws.write(row_num, 18, campo19, font_style2)
                        ws.write(row_num, 19, campo20, font_style2)
                        ws.write(row_num, 20, campo21, font_style2)
                        ws.write(row_num, 21, campo22, font_style2)
                        ws.write(row_num, 22, campo23, font_style2)
                        ws.write(row_num, 23, campo24, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelsupervisor':
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
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Lista_supervision_practicas' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 3000),
                        (u"PERIODO ACADEMICO", 4500),
                        (u"CEDULA", 3000),
                        (u"ESTUDIANTE", 10000),
                        (u"CELULAR", 3000),
                        (u"EMAIL", 10000),
                        (u"EMAIL INSTITUCIONAL", 10000),
                        (u"EGRESADO", 2000),
                        (u"TIPO PRACTICAS", 3000),
                        (u"TUTOR ACADÉMICO", 3000),
                        (u"TUTOR PROFESIONAL", 3000),
                        (u"SUPERVISOR", 3000),
                        (u"FECHA DESDE", 3000),
                        (u"FECHA HASTA", 3000),
                        (u"HORAS PRACTICAS", 2000),
                        (u"HORAS HOMOLOGACIÓN", 2000),
                        (u"INSTITUCION", 13000),
                        (u"OTRA EMPRESA", 13000),
                        (u"TIPO INSTITUCION", 3000),
                        (u"SECTOR ECONOMICO", 6500),
                        (u"PRACTICAS CULMINADAS", 2000),
                        (u"EVIDENCIAS APROBADAS / TOTAL ", 2000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listapracticas = PracticasPreprofesionalesInscripcion.objects.select_related().filter(status=True, supervisor=profesor).order_by('inscripcion__persona__apellido1')
                    row_num = 4
                    i = 0
                    for practicas in listapracticas:
                        campo1 = practicas.inscripcion.coordinacion.nombre
                        campo2 = practicas.inscripcion.carrera.nombre_completo()
                        campo3 = ''
                        campo4 = ''
                        if practicas.inscripcion.nivelperiodo(periodo):
                            matriculado = practicas.inscripcion.nivelperiodo(periodo)
                            campo3 = matriculado.nivelmalla.nombre
                            campo4 = matriculado.nivel.periodo.nombre
                        campo5 = practicas.inscripcion.persona.cedula
                        campo6 = practicas.inscripcion.persona.nombre_completo_inverso()
                        campo7 = practicas.inscripcion.persona.telefono + " - " + practicas.inscripcion.persona.telefono_conv
                        campo8 = practicas.inscripcion.persona.email
                        campo9 = practicas.inscripcion.persona.emailinst
                        if practicas.inscripcion.egresado():
                            campo10 = 'SI'
                        else:
                            campo10 = 'NO'
                        campo11 = practicas.get_tipo_display()
                        campo12 = practicas.tutorunemi.persona.nombre_completo_inverso() if practicas.tutorunemi else ""
                        campo13 = practicas.tutorempresa if practicas.tutorempresa else ""
                        campo14 = practicas.supervisor.persona.nombre_completo_inverso() if practicas.supervisor else ""
                        campo15 = practicas.fechadesde if practicas.fechadesde else ""
                        campo16 = practicas.fechahasta if practicas.fechahasta else ""
                        campo17 = practicas.numerohora
                        campo18 = practicas.horahomologacion
                        campo19 = practicas.empresaempleadora.nombre if practicas.empresaempleadora else ""
                        campo20 = practicas.otraempresaempleadora if practicas.otraempresaempleadora else ""
                        campo21 = practicas.get_tipoinstitucion_display()
                        campo22 = practicas.get_sectoreconomico_display()
                        if practicas.culminada:
                            campo23 = 'SI'
                        else:
                            campo23 = 'NO'
                        if practicas.fechadesde:
                            campo24 = str(practicas.evidenciasaprobadas()) + ' / ' + str(practicas.totalevidencias())
                        else:
                            campo24 = "0/0"
                        ws.write(row_num, 0, campo1, font_style2)
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
                        ws.write(row_num, 14, campo15, date_format)
                        ws.write(row_num, 15, campo16, date_format)
                        ws.write(row_num, 16, campo17, font_style2)
                        ws.write(row_num, 17, campo18, font_style2)
                        ws.write(row_num, 18, campo19, font_style2)
                        ws.write(row_num, 19, campo20, font_style2)
                        ws.write(row_num, 20, campo21, font_style2)
                        ws.write(row_num, 21, campo22, font_style2)
                        ws.write(row_num, 22, campo23, font_style2)
                        ws.write(row_num, 23, campo24, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'informemensual':
                try:
                    data['title'] = u'Informe mensual de Prácticas Pre Profesionales'
                    search = None
                    ids = None
                    informe = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        informe = InformeMensualSupervisorPractica.objects.filter(pk=ids, persona=persona, status=True)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            informe = InformeMensualSupervisorPractica.objects.filter(pk=search, status=True, persona=persona)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    informe = InformeMensualSupervisorPractica.objects.filter(Q(observacion__icontains=s[0]), Q(status=True), Q(persona=persona))
                                elif len(s) == 2:
                                    informe = InformeMensualSupervisorPractica.objects.filter(Q(observacion__icontains=s[0]), Q(observacion__icontains=s[1]), Q(status=True), Q(persona=persona))
                                elif len(s) == 3:
                                    informe = InformeMensualSupervisorPractica.objects.filter(Q(observacion__icontains=s[0]), Q(observacion__icontains=s[1]), Q(observacion__icontains=s[2]), Q(status=True), Q(persona=persona))
                            else:
                                informe = InformeMensualSupervisorPractica.objects.filter(status=True, persona=persona)
                    else:
                        informe = InformeMensualSupervisorPractica.objects.filter(status=True, persona=persona)
                    paging = MiPaginador(informe, 25)
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
                    data['informesupervisor'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "pro_laboratoriocronograma/viewinformemensualsupervisor.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinformemensual':
                try:
                    data['title'] = u'Adicionar informe mensual de Prácticas Pre Profesionales'
                    form = InformeMensualSupervisorPracticaForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/addinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinformemensual':
                try:
                    data['title'] = u'Editar informe mensual de Prácticas Pre Profesionales'
                    data['informesupervisor'] = informe = InformeMensualSupervisorPractica.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = InformeMensualSupervisorPracticaForm(initial={'fechainicio': informe.fechainicio,
                                                                                 'fechafin': informe.fechafin,
                                                                                 'observacion': informe.observacion,
                                                                                 'carrera': informe.carreras()})
                    return render(request, "pro_laboratoriocronograma/editinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinformemensual':
                try:
                    data['title'] = u'Eliminar informe mensual de Prácticas Pre Profesionales'
                    data['informesupervisor'] = InformeMensualSupervisorPractica.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_laboratoriocronograma/delinformemensual.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_observacion':
                try:
                    solicitud = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['idsolicitud']))
                    return JsonResponse({"result": "ok", 'data': solicitud.obseaprueba})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informemensualsupervisor':
                try:
                    data['title'] = u'Informe mensual (Supervisor)'
                    search = None
                    ids = None
                    informe = None
                    listaidsupervisores = PracticasPreprofesionalesInscripcion.objects.values_list('supervisor__persona__id').filter(tutorunemi=profesor, status=True)
                    carreras = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__carrera__id').filter(tutorunemi=profesor, status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                        if search:
                            s = search.split(" ")
                            if len(s) == 1:
                                informe = InformeMensualSupervisorPractica.objects.filter((Q(persona__apellido1__icontains=s[0]) |
                                                                                           Q(persona__apellido2__icontains=s[0]) |
                                                                                           Q(persona__nombres__icontains=s[0])) &
                                                                                          Q(status=True) & Q(persona__id__in=listaidsupervisores) & Q(carrera__id__in=carreras)).distinct()
                            elif len(s) == 2:
                                informe = InformeMensualSupervisorPractica.objects.filter(((Q(persona__apellido1__icontains=s[0]) &
                                                                                            Q(persona__apellido2__icontains=s[1])) |
                                                                                           Q(persona__nombres__icontains=s[0]) &
                                                                                           Q(persona__nombres__icontains=s[1])) &
                                                                                          Q(status=True) & Q(persona__id__in=listaidsupervisores) & Q(carrera__id__in=carreras)).distinct()
                            elif len(s) == 3:
                                informe = InformeMensualSupervisorPractica.objects.filter(Q(persona__apellido1__icontains=s[0]) &
                                                                                          Q(persona__apellido2__icontains=s[1]) &
                                                                                          Q(persona__nombres__icontains=s[2]) &
                                                                                          Q(status=True) & Q(persona__id__in=listaidsupervisores) & Q(carrera__id__in=carreras)).distinct()
                            elif len(s) == 4:
                                informe = InformeMensualSupervisorPractica.objects.filter(Q(persona__apellido1__icontains=s[0]) &
                                                                                          Q(persona__apellido2__icontains=s[1]) &
                                                                                          Q(persona__nombres__icontains=s[2]) &
                                                                                          Q(persona__nombres__icontains=s[3]) &
                                                                                          Q(status=True) & Q(persona__id__in=listaidsupervisores) & Q(carrera__id__in=carreras)).distinct()
                        else:
                            informe = InformeMensualSupervisorPractica.objects.filter(status=True, persona__id__in=listaidsupervisores, carrera__id__in=carreras)
                    else:
                        informe = InformeMensualSupervisorPractica.objects.filter(status=True, persona__id__in=listaidsupervisores, carrera__id__in=carreras)
                    paging = MiPaginador(informe, 25)
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
                    data['informesupervisor'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "pro_laboratoriocronograma/viewinformemensualsupervisor_tutor.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpractica':
                try:
                    data['title'] = u'Editar Prácticas Pre-Profesionales'
                    data['practicaspreprofesionalesinscripcion'] = practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = PracticasPreprofesionalesInscripcionSupervisorForm(initial={'inscripcion': practicaspreprofesionalesinscripcion.inscripcion.id,
                                                                                       'tipo': practicaspreprofesionalesinscripcion.tipo,
                                                                                       'fechadesde': practicaspreprofesionalesinscripcion.fechadesde,
                                                                                       'fechahasta': practicaspreprofesionalesinscripcion.fechahasta,
                                                                                       'empresaempleadora': practicaspreprofesionalesinscripcion.empresaempleadora.id if practicaspreprofesionalesinscripcion.empresaempleadora else "",
                                                                                       'tutorempresa': practicaspreprofesionalesinscripcion.tutorempresa,
                                                                                       'numerohora': practicaspreprofesionalesinscripcion.numerohora,
                                                                                       'departamento': practicaspreprofesionalesinscripcion.departamento,
                                                                                       'otraempresaempleadora': practicaspreprofesionalesinscripcion.otraempresaempleadora,
                                                                                       'otraempresa': practicaspreprofesionalesinscripcion.otraempresa,
                                                                                       'itinerario': practicaspreprofesionalesinscripcion.itinerariomalla})
                    form.editar(practicaspreprofesionalesinscripcion)
                    malla = practicaspreprofesionalesinscripcion.inscripcion.mi_malla()
                    nivel = practicaspreprofesionalesinscripcion.inscripcion.mi_nivel().nivel
                    form.cargaritinerario(malla, nivel)
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/editpractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'visitasupervisor':
                try:
                    data['title'] = u'Registro de vinculacion y seguimiento'
                    hoy = datetime.now().date()
                    panio = hoy.year
                    pmes = hoy.month
                    fecha = hoy
                    if 'proximo' in request.GET:
                        mes = int(request.GET['mes'])
                        anio = int(request.GET['anio'])
                        pmes = mes + 1
                        if pmes == 13:
                            pmes = 1
                            panio = anio + 1
                        else:
                            panio = anio
                    if 'anterior' in request.GET:
                        mes = int(request.GET['mes'])
                        anio = int(request.GET['anio'])
                        pmes = mes - 1
                        if pmes == 0:
                            pmes = 12
                            panio = anio - 1
                        else:
                            panio = anio
                    fechainicio = date(panio, pmes, 1)
                    try:
                        fechafin = date(panio, pmes, 31)
                    except Exception as ex:
                        try:
                            fechafin = date(panio, pmes, 30)
                        except Exception as ex:
                            try:
                                fechafin = date(panio, pmes, 29)
                            except Exception as ex:
                                fechafin = date(panio, pmes, 28)
                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listaadicionarficha = {}
                    listafichas = {}
                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        diatut = {i: False}
                        tutoriadia = {i: None}
                        lista.update(dia)
                        listaadicionarficha.update(diatut)
                        listafichas.update(tutoriadia)
                    comienzo = False
                    fin = False
                    num = 0
                    for i in lista.items():
                        try:
                            fecha = date(s_anio, s_mes, s_dia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(s_anio, s_mes, s_dia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: s_dia}
                            lista.update(dia)
                            if date(s_anio, s_mes, s_dia) >= hoy:
                                diatut = {i[0]: True}
                                listaadicionarficha.update(diatut)
                            visitapractica = VisitaPractica.objects.filter(persona=profesor.persona, fecha=fecha)
                            diaact = []
                            if visitapractica:
                                totalvisitapractica = visitapractica[0].total_detalles_visitas()
                                diaact.append(['default', totalvisitapractica.__str__(), 'Visitas', visitapractica[0]])
                            listafichas.update({i[0]: diaact})
                            s_dia += 1
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['listafichas'] = listafichas
                    data['listaadicionarficha'] = listaadicionarficha
                    data['dia_actual'] = datetime.now().date().day
                    dia_anterior = datetime.now().date() + timedelta(days=-2)
                    data['dia_anterior'] = dia_anterior.day
                    data['mostrar_dia_anterior'] = fecha.month == dia_anterior.month and fecha.year == dia_anterior.year
                    data['mostrar_dia_actual'] = fecha.month == datetime.now().date().month and fecha.year == datetime.now().date().year
                    # data['supervisorpracticas'] = supervisorpracticas = PracticasPreprofesionalesInscripcion.objects.filter(status=True, fechadesde__lte=datetime.now().date(), fechahasta__gte=datetime.now().date(), supervisor=profesor,  estadosolicitud=2, culminada=False)
                    data['supervisorpracticas'] = supervisorpracticas = PracticasPreprofesionalesInscripcion.objects.filter(status=True, supervisor=profesor, tipo__in=[1, 2], culminada=False).exclude(estadosolicitud=3)
                    data['total_supervisorpracticas'] = supervisorpracticas.values('id').count()
                    return render(request, "pro_laboratoriocronograma/visitapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delvisitasupervisor':
                try:
                    data['title'] = u'Eliminar visita agendada'
                    data['visitapractica'] = VisitaPractica.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_laboratoriocronograma/delvisitaagendada.html", data)
                except Exception as ex:
                    pass

            elif action == 'practicasvisitada':
                try:
                    data['title'] = u'Prácticas visitadas (Supervisor)'
                    fechainicio = None
                    fechafin = None
                    idi = None
                    idt = None
                    ide = None
                    idcor = None
                    idcar = None
                    empezarabuscar = True
                    detallevisitas = []
                    if 'idcor' in request.GET:
                        empezarabuscar = False
                        detallevisitas = VisitaPractica_Detalle.objects.filter(visitapractica__persona=profesor.persona, status=True)
                        idcor = int(encrypt(request.GET['idcor']))
                        if idcor > 0:
                            detallevisitas = detallevisitas.filter(practica__inscripcion__carrera__coordinacion__id=idcor)
                        else:
                            idcor = None
                    if 'idcar' in request.GET:
                        idcar = int(encrypt(request.GET['idcar']))
                        if idcar > 0:
                            detallevisitas = detallevisitas.filter(practica__inscripcion__carrera__id=idcar)
                        else:
                            idcar = None
                    if 'idi' in request.GET:
                        idi = int(encrypt(request.GET['idi']))
                        if idi > 0:
                            detallevisitas = detallevisitas.filter(practica__inscripcion__id=idi)
                        else:
                            idi = None
                    if 'fi' in request.GET and 'ff' in request.GET:
                        fechainicio = convertir_fecha(request.GET['fi'])
                        fechafin = convertir_fecha(request.GET['ff'])
                        detallevisitas = detallevisitas.filter(visitapractica__fecha__range=(fechainicio, fechafin), )
                    if 'idt' in request.GET:
                        idt = int(encrypt(request.GET['idt']))
                        detallevisitas = detallevisitas.filter(tipo=idt)
                    if 'ide' in request.GET:
                        ide = int(encrypt(request.GET['ide']))
                        detallevisitas = detallevisitas.filter(estado=ide)
                    paging = MiPaginador(detallevisitas, 25)
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
                    data['detallesvisitas'] = page.object_list
                    data['fechainicio'] = fechainicio
                    data['fechafin'] = fechafin
                    data['ESTADO_TIPO_VISITA'] = ESTADO_TIPO_VISITA
                    data['ESTADO_VISITA_PRACTICA'] = ESTADO_VISITA_PRACTICA
                    data['idi'] = idi
                    data['idt'] = idt
                    data['ide'] = ide
                    data['idcor'] = idcor
                    data['idcar'] = idcar
                    data['empezarabuscar'] = empezarabuscar
                    data['if_idt'] = True if 'idt' in request.GET else False
                    data['if_ide'] = True if 'ide' in request.GET else False
                    data['inscripciones'] = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__id', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres').filter(status=True, supervisor=profesor).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    listacarreras = PracticasPreprofesionalesInscripcion.objects.values_list('inscripcion__carrera__id').filter(status=True, supervisor=profesor).distinct().order_by('inscripcion__carrera__id')
                    carreras = []
                    if not empezarabuscar:
                        carreras = Carrera.objects.filter(pk__in=listacarreras).distinct()
                    data['carreras'] = carreras
                    data['coordinaciones'] = Coordinacion.objects.filter(carrera__id__in=listacarreras).distinct()
                    return render(request, "pro_laboratoriocronograma/viewdetallevisita.html", data)
                except Exception as ex:
                    pass

            elif action == 'matrizvisitasupervisor':
                try:
                    fini = convertir_fecha(request.GET['fini'])
                    ffin = convertir_fecha(request.GET['ffin'])
                    __author__ = 'Unemi'
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('vinculación y seguimiento')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Matriz de seguimiento del supervisor ' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"PERIODO EVIDENCIA", 10000),
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 3000),
                        (u"ESTUDIANTE", 10000),
                        (u"CÉDULA", 3000),
                        (u"TIPO PRACTICAS", 4000),
                        (u"TUTOR ACADÉMICO", 10000),
                        (u"FECHA DESDE", 3000),
                        (u"FECHA HASTA", 3000),
                        (u"HORAS PRACTICAS", 4000),
                        (u"ITINERARIO", 10000),
                        (u"INSTITUCION", 10000),
                        (u"OTRA EMPRESA", 10000),
                        (u"DEPARTAMENTO", 10000),
                        (u"ESTADO SOLICITUD", 4000),
                        (u"PRACTICAS CULMINADAS", 4000),
                        (u"OBSERVACIÓN", 10000),
                        (u"VALIDACIÓN", 10000),
                        (u"FECHA VALIDACIÓN", 3000),
                        (u"SESIÓN", 4000),
                        (u"PARALELO", 3000),
                        (u"FECHA DE VISITA", 3000),
                        (u"TIPO DE VISITA", 4000),
                        (u"ESTADO DEL TIPO DE VISITA", 4000),
                        (u"OBSERVACIONES INGRESADAS POR SUPERVISIÓN", 10000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 4
                    detallesvisitas = VisitaPractica_Detalle.objects.filter(visitapractica__persona=persona, visitapractica__fecha__range=(fini, ffin), status=True)
                    for detallevisita in detallesvisitas:
                        campo1 = detallevisita.practica.periodoppp if detallevisita.practica.periodoppp else ''
                        campo2 = detallevisita.practica.inscripcion.carrera.mi_coordinacion() if detallevisita.practica.inscripcion.carrera.mi_coordinacion() else ''
                        campo3 = detallevisita.practica.inscripcion.carrera if detallevisita.practica.inscripcion.carrera else ''
                        campo4 = detallevisita.practica.inscripcion.mi_nivel() if detallevisita.practica.inscripcion.mi_nivel() else ''
                        campo5 = detallevisita.practica.inscripcion.persona.nombre_completo_inverso()
                        campo6 = detallevisita.practica.inscripcion.persona.cedula
                        campo7 = detallevisita.practica.get_tipo_display()
                        campo8 = detallevisita.practica.tutorunemi if detallevisita.practica.tutorunemi else ''
                        campo9 = detallevisita.practica.fechadesde.strftime('%d-%m-%Y') if detallevisita.practica.fechadesde else ''
                        campo10 = detallevisita.practica.fechahasta.strftime('%d-%m-%Y') if detallevisita.practica.fechahasta else ''
                        campo11 = detallevisita.practica.numerohora
                        campo12 = detallevisita.practica.itinerariomalla
                        campo13 = detallevisita.practica.empresaempleadora.nombre if detallevisita.practica.empresaempleadora else ''
                        campo14 = detallevisita.practica.otraempresaempleadora if detallevisita.practica.otraempresaempleadora else ''
                        campo15 = detallevisita.practica.departamento if detallevisita.practica.departamento else ''
                        campo16 = detallevisita.practica.get_estadosolicitud_display()
                        if detallevisita.practica.culminada:
                            campo17 = 'SI'
                        else:
                            campo17 = 'NO'
                        campo18 = detallevisita.practica.observacion if detallevisita.practica.observacion else ''
                        campo19 = detallevisita.practica.validacion if detallevisita.practica.validacion else ''
                        campo20 = detallevisita.practica.fechavalidacion.strftime('%d-%m-%Y') if detallevisita.practica.fechavalidacion else ''
                        campo21 = ''
                        campo22 = ''
                        matriculado = detallevisita.practica.inscripcion.nivelperiodo(periodo)
                        if matriculado:
                            campo21 = matriculado.nivel.sesion.nombre.__str__()
                            campo22 = matriculado.paralelo_mayor_frecuencia().__str__()
                        campo23 = detallevisita.visitapractica.fecha.strftime('%d-%m-%Y')
                        campo24 = detallevisita.get_tipo_display()
                        campo25 = detallevisita.get_estado_display()
                        campo26 = detallevisita.observacion if detallevisita.observacion else ''
                        ws.write(row_num, 0, campo1.__str__(), font_style2)
                        ws.write(row_num, 1, campo2.__str__(), font_style2)
                        ws.write(row_num, 2, campo3.__str__(), font_style2)
                        ws.write(row_num, 3, campo4.__str__(), font_style2)
                        ws.write(row_num, 4, campo5.__str__(), font_style2)
                        ws.write(row_num, 5, campo6.__str__(), font_style2)
                        ws.write(row_num, 6, campo7.__str__(), font_style2)
                        ws.write(row_num, 7, campo8.__str__(), font_style2)
                        ws.write(row_num, 8, campo9.__str__(), font_style2)
                        ws.write(row_num, 9, campo10.__str__(), date_format)
                        ws.write(row_num, 10, campo11.__str__(), date_format)
                        ws.write(row_num, 11, campo12.__str__(), font_style2)
                        ws.write(row_num, 12, campo13.__str__(), font_style2)
                        ws.write(row_num, 13, campo14.__str__(), font_style2)
                        ws.write(row_num, 14, campo15.__str__(), font_style2)
                        ws.write(row_num, 15, campo16.__str__(), font_style2)
                        ws.write(row_num, 16, campo17.__str__(), font_style2)
                        ws.write(row_num, 17, campo18.__str__(), font_style2)
                        ws.write(row_num, 18, campo19.__str__(), font_style2)
                        ws.write(row_num, 19, campo20.__str__(), font_style2)
                        ws.write(row_num, 20, campo21.__str__(), date_format)
                        ws.write(row_num, 21, campo22.__str__(), font_style2)
                        ws.write(row_num, 22, campo23.__str__(), font_style2)
                        ws.write(row_num, 23, campo24.__str__(), date_format)
                        ws.write(row_num, 24, campo25.__str__(), font_style2)
                        ws.write(row_num, 25, campo26.__str__(), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'aceptarmateria':
                try:
                    pass
                except Exception as ex:
                    pass

            elif action == 'supervisionmateriaprofesor':
                try:
                    data['title'] = u'Supervisión y control de profesor'
                    data['materia'] = Materia.objects.get(pk=int(encrypt(request.GET['idm'])))
                    return render(request, "pro_laboratoriocronograma/supervisionmateriaprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'horarioprofesor':
                try:
                    data['title'] = u'Horario del profesor'
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=int(encrypt(request.GET['idpm'])))
                    data['semana'] = DIAS_CHOICES
                    data['turnos'] = profesormateria.extrae_turnos_y_clases_docente()[1]
                    data['puede_ver_horario'] = periodo.visible == True and periodo.visiblehorario == True
                    return render(request, "pro_laboratoriocronograma/horarioprofesor.html", data)
                except Exception as ex:
                    pass

            elif action == 'asistenciaprofesor':
                try:
                    data['title'] = u'Asistencias del profesor'
                    if not periodo.visible:
                        return HttpResponseRedirect("/?info=Periodo Inactivo.")
                    profesormateria = ProfesorMateria.objects.get(pk=int(encrypt(request.GET['idpm'])))
                    profesormateriafilter = ProfesorMateria.objects.filter(pk=int(encrypt(request.GET['idpm'])))
                    listas_clases_resultados = profesormateria.profesor.asistencia_profesor_segun_periodo(periodo, profesormateriafilter)
                    clases = listas_clases_resultados['lista_clases']
                    resultado = listas_clases_resultados['lista_resultado']
                    inicio = listas_clases_resultados['fechainicio']
                    fin = listas_clases_resultados['fechafin']
                    data['clases'] = clases
                    data['resultado'] = resultado
                    data['profesor'] = profesormateria.profesor
                    data['hoy'] = datetime.now().date() == inicio and datetime.now().date() == fin
                    data['atras'] = 'pro_laboratoriocronograma?action=supervisionmateriaprofesor&idm=' + encrypt(profesormateria.materia_id)
                    return render(request, "pro_clases/asistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'listar_silabos':
                try:
                    data['title'] = u'Sílabo de digital'
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['silabos'] = materia.silabo_set.filter(status=True).order_by('fecha_creacion')
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    template = get_template("pro_laboratoriocronograma/seguimientosilabodigital.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'planificarponencias':
                try:
                    data['title'] = u'Listado de Solicitudes de Financiamiento a ponencias'

                    tienedistributivo = profesor.profesordistributivohoras_set.values('id').filter(periodo=periodo, status=True).exists()

                    ponencias = PlanificarPonencias.objects.filter(profesor=profesor).order_by('-fecha_creacion')
                    paging = Paginator(ponencias, 30)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['page'] = page
                    data['ponencias'] = page.object_list
                    hoy = datetime.now().date()

                    convocatoria = None
                    convocatorias = ConvocatoriaPonencia.objects.filter(status=True, publicada=True, iniciopos__lte=hoy, finpos__gte=hoy)
                    if convocatorias:
                        convocatoria = convocatorias[0]

                    data['habilitaingresoponencias'] = True if convocatoria else False
                    data['tienedistributivo'] = tienedistributivo
                    data['convocatoria'] = convocatoria
                    return render(request, "pro_laboratoriocronograma/planificarponencias.html", data)
                except Exception as ex:
                    pass

            elif action == 'planificarcapacitaciones':
                try:
                    data['title'] = u'Registro de solicitudes para capacitaciones/actualizaciones'
                    convocatoria = CronogramaCapacitacionDocente.objects.get(pk=int(request.GET['convocatoria']))
                    # tienemateriasperiodo = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo=periodo,
                    #                                   materia__nivel__periodo__visible=True, status=True, activo=True,
                    #                                   materia__cerrado=False,
                    #                                   ).exists()
                    tienemateriasperiodo = True
                    profesorperiodo = profesor.profesordistributivohoras_set.filter(periodo=periodo, status=True).first()
                    tipocategoria = profesorperiodo.categoria.id
                    fechainiciotecdoc = convocatoria.iniciocapacitaciontecdoc

                    if tipocategoria == 9:
                        if fechainiciotecdoc:
                            data['fecha_valida'] = True
                        else:
                            data['fecha_valida'] = False
                    else:
                        data['fecha_valida'] = True

                    if profesor.profesordistributivohoras_set.values_list('coordinacion_id', 'carrera_id').filter(periodo=periodo, status=True).exists():
                        tienedistributivo = True
                        datosdistrib = profesor.profesordistributivohoras_set.values_list('coordinacion_id', 'carrera_id').filter(periodo=periodo, status=True)[0]
                        codigofacultad = datosdistrib[0]
                        codigocarrera = datosdistrib[1]

                        existedirectorcarrera = CoordinadorCarrera.objects.filter(periodo=periodo, carrera_id=codigocarrera, status=True).exists()
                        existedecanofacultad = ResponsableCoordinacion.objects.filter(periodo=periodo, coordinacion_id=codigofacultad, status=True).exists()
                    else:
                        tienedistributivo = False

                    infoperiodocompleta = True
                    mensaje = ""

                    if tienemateriasperiodo is False:
                        mensaje = "El Docente no tiene asignaturas activas asignadas en el Periodo"
                        infoperiodocompleta = False
                    elif tienedistributivo is False:
                        mensaje = "El Docente no tiene distributivo asignado en el Periodo"
                        infoperiodocompleta = False
                    elif existedirectorcarrera is False:
                        mensaje = "La Carrera no tiene asignado director en el Periodo"
                        # infoperiodocompleta = False
                        infoperiodocompleta = True
                    elif existedecanofacultad is False:
                        mensaje = "La Facultad no tiene asignado decano en el Periodo"
                        # infoperiodocompleta = False
                        infoperiodocompleta = True

                    data['infoperiodocompleta'] = infoperiodocompleta
                    data['mensaje'] = mensaje

                    hoy = datetime.now().date()
                    if convocatoria.inicio.date() <= hoy <= convocatoria.fin.date():
                        data['puede_solicitar'] = True
                    else:
                        data['puede_solicitar'] = False

                    data['convocatoria'] = convocatoria.id
                    data['cronogramacapacitacion'] = convocatoria
                    modeloinforme = None
                    if convocatoria.modeloinforme:
                        modeloinforme = convocatoria.modeloinforme.url
                    data['modeloinforme'] = modeloinforme
                    capacitaciones = PlanificarCapacitaciones.objects.filter(profesor=profesor, cronograma=convocatoria).order_by('-fecha_creacion')
                    data['saldo'] = null_to_decimal(convocatoria.monto - convocatoria.totalmonto_profesor(profesor=profesor, convocatoria=convocatoria))
                    paging = Paginator(capacitaciones, 30)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['page'] = page
                    data['capacitaciones'] = page.object_list
                    data['form2'] = PlanificarCapacitacionesArchivoForm()
                    data['periodo'] = periodo
                    data['token'] = profesor.tienetoken
                    return render(request, "pro_laboratoriocronograma/planificarcapacitaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'cronogramacapacitaciones':
                try:
                    data['title'] = u'Cronograma y bases para la capacitación/actualización académica'
                    capacitaciones = CronogramaCapacitacionDocente.objects.filter(status=True, tipo=1).order_by('-inicio')
                    paging = Paginator(capacitaciones, 50)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['page'] = page
                    data['capacitaciones'] = page.object_list
                    data['tipopersonal'] = 1
                    data['url_vars'] = f'&action={action}'
                    return render(request, "pro_laboratoriocronograma/cronogramacapacitaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'informesgenerados':
                try:
                    data['title'] = u'Listado de informes mensuales'
                    data['docente'] = Profesor.objects.get(pk=profesor.id)
                    hoy = datetime.now()
                    data['versioninfo'] = hoy.strftime('%Y%m%d_%H%M%S')
                    data['eliminartodo'] = variable_valor('ELIMINAR_INFORMES_FIRMADOS')
                    data['listadoinformes'] = InformeMensualDocente.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, status=True).order_by('id')
                    return render(request, "pro_laboratoriocronograma/informesgenerados.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleinforme':
                try:
                    data = {}
                    data['informe'] = informe = InformeMensualDocente.objects.get(pk=int(request.GET['id']))
                    data['historial'] = informe.historialinforme_set.filter(status=True).order_by('id')
                    template = get_template("pro_laboratoriocronograma/detalleinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmainforme':
                try:
                    informe = InformeMensualDocente.objects.get(id=request.GET['id'])
                    data['archivo'] = archivo = informe.archivo.url
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = informe.id
                    data['action_firma'] = 'firmainformemensual'
                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addponencia':
                try:
                    data['title'] = u'Agregar Solicitud de Financiamiento a ponencias'
                    form = PlanificarPonenciasForm()
                    data['criteriosnac'] = CriterioPonencia.objects.filter(status=True, tipoponencia=1, vigente=True).order_by('orden')
                    data['criteriosint'] = CriterioPonencia.objects.filter(status=True, tipoponencia=2, vigente=True).order_by('orden')
                    data['convocatoria'] = ConvocatoriaPonencia.objects.get(pk=int(encrypt(request.GET['idc'])))
                    data['idc'] = request.GET['idc']
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/addponencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcapacitacion':
                try:
                    data['title'] = u'Solicitud de capacitación/actualización'
                    form = PlanificarCapacitacionesForm()
                    data['form'] = form
                    data['convocatoria'] = convocatoria = request.GET['convocatoria']
                    data['listadoenfoque'] = CapEnfocadaDocente.objects.filter(status=True)
                    data['criterios'] = PlanificarCapacitacionesCriterios.objects.filter(status=True, tipo=1).order_by('id')
                    return render(request, "pro_laboratoriocronograma/addcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcapacitacion':
                try:
                    data['title'] = u'Editar solicitud de capacitación/actualización'
                    data['convocatoria'] = convocatoria = request.GET['convocatoria']
                    data['solicitud'] = solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listadoenfoque'] = CapEnfocadaDocente.objects.filter(status=True)
                    data['detalleenfoque'] = detalleenfoque = solicitud.planificarcapacitacionesenfoque_set.filter(status=True)
                    listacodigosenfoque = []
                    for enfo in detalleenfoque:
                        if solicitud.enfoque:
                            if solicitud.enfoque_id == 4 or solicitud.enfoque_id == 12:
                                listacodigosenfoque.append(enfo.lineainvestigacion_id)
                            if solicitud.enfoque_id == 7:
                                listacodigosenfoque.append(enfo.titulacion_id)
                            if solicitud.enfoque_id == 8:
                                listacodigosenfoque.append(enfo.materia_id)
                    data['listacodigosenfoque'] = listacodigosenfoque
                    form = PlanificarCapacitacionesForm(initial={'tema': solicitud.tema,
                                                                 'institucion': solicitud.institucion,
                                                                 'pais': solicitud.pais,
                                                                 'justificacion': solicitud.justificacion,
                                                                 'modalidad': solicitud.modalidad,
                                                                 'fechainicio': solicitud.fechainicio,
                                                                 'fechafin': solicitud.fechafin,
                                                                 'costo': solicitud.costo,
                                                                 'horas': solicitud.horas,
                                                                 'link': solicitud.link})

                    data['form'] = form
                    data['criterios'] = solicitud.planificarcapacitacionesdetallecriterios_set.filter(status=True).order_by('criterio_id')
                    return render(request, "pro_laboratoriocronograma/editcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadolineasinvestigacion':
                try:
                    lista = []
                    listadoitems = []
                    tipoopcion = int(request.GET['tipoopcion'])
                    if int(request.GET['idsolicitud']) > 0:
                        solicitud = PlanificarCapacitaciones.objects.get(pk=int(request.GET['idsolicitud']))
                        puede = 1
                        if tipoopcion == 4 or tipoopcion == 12:
                            listadoitems = solicitud.planificarcapacitacionesenfoque_set.values_list('lineainvestigacion_id', flat=True).filter(status=True)
                        if tipoopcion == 7:
                            listadoitems = solicitud.planificarcapacitacionesenfoque_set.values_list('titulacion_id', flat=True).filter(status=True)
                        if tipoopcion == 8:
                            listadoitems = solicitud.planificarcapacitacionesenfoque_set.values_list('materia_id', flat=True).filter(status=True)
                    else:
                        puede = 0
                    if tipoopcion == 4 or tipoopcion == 12:
                        listadoinvestigacion = PropuestaLineaInvestigacion.objects.filter(activo=True, status=True).order_by('nombre')
                        for lis in listadoinvestigacion:
                            chequeado = ''
                            if lis.id in listadoitems:
                                chequeado = 'checked'
                            lista.append([lis.id, lis.nombre, chequeado])
                    if tipoopcion == 7:
                        listadotitulo = Titulacion.objects.filter(persona=profesor.persona, titulo__nivel_id=4, titulo__grado_id__in=[1, 2], status=True)
                        for lis in listadotitulo:
                            chequeado = ''
                            if lis.id in listadoitems:
                                chequeado = 'checked'
                            nombretitulo = lis.titulo.nombre
                            lista.append([lis.id, nombretitulo, chequeado])
                    if tipoopcion == 8:
                        listadomaterias = Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo=periodo, nivel__periodo__visible=True, profesormateria__status=True, status=True, profesormateria__activo=True).distinct().order_by('asignatura').distinct()
                        for lis in listadomaterias:
                            chequeado = ''
                            if lis.id in listadoitems:
                                chequeado = 'checked'
                            nombremateria = lis.asignaturamalla.asignatura.nombre + ' - ' + lis.paralelo + ' - ' + lis.asignaturamalla.nivelmalla.nombre + ' - ' + lis.asignaturamalla.malla.carrera.nombre
                            lista.append([lis.id, nombremateria, chequeado])
                    data = {"results": "ok", 'listadolineas': lista}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'subirevidenciaejecutadocap':
                try:
                    data['title'] = u'Subir Evidencias de capacitación Ejecutada'
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = SubirEvidenciaEjecutadoCapacitacionesForm()

                    # if datetime.now().date() < solicitud.fechafin:
                    #     form.quitarcamposevidencia('OTR')
                    #     data['evidenciavalidar'] = 'FAC'
                    # elif not solicitud.archivofactura:
                    #     form.quitarcamposevidencia('OTR')
                    #     data['evidenciavalidar'] = 'FAC'
                    # else:
                    #     form.quitarcamposevidencia('FAC')
                    #     data['evidenciavalidar'] = 'OTR'
                    data['evidenciavalidar'] = 'FAC'
                    form.quitarcamposevidencia('FAC')

                    data['form'] = form
                    data['tema'] = solicitud.tema

                    # data['informe'] = solicitud.archivoinforme
                    data['factura'] = solicitud.archivofactura
                    data['certificado'] = solicitud.archivocertificado

                    data['id'] = request.GET['id']
                    data['convocatoria'] = request.GET['convocatoria']

                    return render(request, "pro_laboratoriocronograma/subirevidenciaejecutado.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirevidenciaejecutadopon':
                try:
                    # cedula1oblig = cert1oblig = cedula2oblig = cert2oblig = actaoblig = False
                    # documentos = persona.documentos_personales()
                    ponencia = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = PonenciaEvidenciaEjecutadoForm()

                    #
                    # mostrarcampoacta = True if solicitud.becatipo.id == 16 else False
                    #
                    # if documentos:
                    #     if documentos.estadocedula == 3:
                    #         cedula1oblig = True
                    #     elif documentos.estadocedula == 2:
                    #         form.borrar_campos(1)
                    #
                    #     if documentos.estadopapeleta == 3:
                    #         cert1oblig = True
                    #     elif documentos.estadopapeleta == 2:
                    #         form.borrar_campos(2)
                    #
                    #     if documentos.estadocedularepresentantesol == 3:
                    #         cedula2oblig = True
                    #     elif documentos.estadocedularepresentantesol == 2:
                    #         form.borrar_campos(3)
                    #
                    #     if documentos.estadopapeletarepresentantesol == 3:
                    #         cert2oblig = True
                    #     elif documentos.estadopapeletarepresentantesol == 2:
                    #         form.borrar_campos(4)
                    #
                    #     if documentos.estadoactagrado == 3 or documentos.estadoactagrado is None:
                    #         actaoblig = True
                    #     elif documentos.estadoactagrado == 2:
                    #         form.borrar_campos(5)
                    # else:
                    #     cedula1oblig = cert1oblig = cedula2oblig = cert2oblig = True
                    #     if mostrarcampoacta:
                    #         actaoblig = True
                    #
                    # if not mostrarcampoacta:
                    #     form.borrar_campos(5)
                    #
                    # data['title'] = u'Actualizar PDF Documentos'
                    # data['id'] = int(request.GET['id'])
                    # data['form'] = form
                    # data['cedula1oblig'] = cedula1oblig
                    # data['cert1oblig'] = cert1oblig
                    # data['cedula2oblig'] = cedula2oblig
                    # data['cert2oblig'] = cert2oblig
                    # data['actaoblig'] = actaoblig
                    # data['mostrarcampoacta'] = mostrarcampoacta
                    data['title'] = u'Subir Evidencias Ponencia Ejecutada'
                    data['congreso'] = ponencia.nombre
                    data['id'] = 123
                    data['form'] = form
                    template = get_template("pro_laboratoriocronograma/subirevidenciaejecutadopon.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'editponencia':
                try:
                    data['title'] = u'Editar Solicitud de Financiamiennto a ponencias'
                    ponencia = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['planificarponencias'] = ponencia
                    form = PlanificarPonenciasForm(initial={'tema': ponencia.tema,
                                                            'fechainicio': ponencia.fecha_inicio,
                                                            'fechafin': ponencia.fecha_fin,
                                                            'justificacion': ponencia.justificacion,
                                                            'link': ponencia.link,
                                                            'nombre': ponencia.nombre,
                                                            'pais': ponencia.pais,
                                                            'sugerenciacongreso': ponencia.sugerenciacongreso,
                                                            'costo': ponencia.costo,
                                                            'modalidad': ponencia.modalidad,
                                                            'areaconocimiento': ponencia.areaconocimiento,
                                                            'subareaconocimiento': ponencia.subareaconocimiento,
                                                            'subareaespecificaconocimiento': ponencia.subareaespecificaconocimiento,
                                                            'lineainvestigacion': ponencia.lineainvestigacion,
                                                            'sublineainvestigacion': ponencia.sublineainvestigacion,
                                                            'provieneproyecto': ponencia.provieneproyecto,
                                                            'tipoproyecto': ponencia.tipoproyecto,
                                                            'proyectointerno': ponencia.proyectointerno,
                                                            'proyectoexterno': ponencia.proyectoexterno,
                                                            'pertenecegrupoinv': ponencia.pertenecegrupoinv,
                                                            'grupoinvestigacion': ponencia.grupoinvestigacion})
                    form.editar(ponencia)
                    data['form'] = form

                    data['tipoponencia'] = tipoponencia = 'N' if ponencia.pais.id == 1 else 'I'
                    data['existecomite'] = ponencia.existecomite

                    if tipoponencia == 'N':
                        data['nombreotrabasenac'] = ponencia.nombreotrabase
                    else:
                        data['nombreotrabaseint'] = ponencia.nombreotrabase

                    data['criteriosdocente'] = ponencia.planificarponenciascriterio_set.filter(status=True).order_by('criterio__orden')
                    data['criteriosnac'] = CriterioPonencia.objects.filter(status=True, tipoponencia=1, vigente=True).order_by('orden')
                    data['criteriosint'] = CriterioPonencia.objects.filter(status=True, tipoponencia=2, vigente=True).order_by('orden')
                    data['convocatoria'] = ponencia.convocatoria

                    return render(request, "pro_laboratoriocronograma/editponencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'subircartacompromiso':
                try:
                    data['title'] = u'Subir Carta de Compromiso de Ponencia Firmada'
                    data['solicitud'] = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("pro_laboratoriocronograma/subircartacompromiso.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'deleponencia':
                try:
                    data['title'] = u'Eliminar planificación de ponencias'
                    data['planificarponencias'] = PlanificarPonencias.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_laboratoriocronograma/deleponencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcapacitacion':
                try:
                    data['title'] = u'Eliminar solicitud de capacitaciones'
                    data['planificarcapacitaciones'] = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_laboratoriocronograma/delcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'productoinvestigacion':
                try:
                    data['title'] = u'Productos Investigación'
                    data['detalledistributivo'] = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesor, status=True)
                    return render(request, "pro_laboratoriocronograma/productoinvestigacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addproductoinvestigacionarticulo':
                try:
                    data['title'] = u'Añadir producto investigación articulo'
                    form = ArticuloInvestigacionDocenteForm()
                    data['form'] = form
                    data['detalledistributivo'] = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesor, status=True)
                    return render(request, "pro_laboratoriocronograma/addproductoinvestigacionarticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addproductoinvestigacionponencia':
                try:
                    data['title'] = u'Añadir producto investigación ponencia'
                    form = PonenciaInvestigacionDocenteForm()
                    data['form'] = form
                    data['detalledistributivo'] = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesor, status=True)
                    return render(request, "pro_laboratoriocronograma/addproductoinvestigacionponencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addproductoinvestigacionlibro':
                try:
                    data['title'] = u'Añadir producto investigación libro'
                    form = LibroInvestigacionDocenteForm()
                    data['form'] = form
                    data['detalledistributivo'] = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesor, status=True)
                    return render(request, "pro_laboratoriocronograma/addproductoinvestigacionlibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'addproductoinvestigacioncapitulolibro':
                try:
                    data['title'] = u'Añadir producto investigación capítulo libro'
                    form = CapituloLibroInvestigacionDocenteForm()
                    data['form'] = form
                    data['detalledistributivo'] = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), distributivo__profesor=profesor, status=True)
                    return render(request, "pro_laboratoriocronograma/addproductoinvestigacioncapitulolibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarproductoarticulo':
                try:
                    data['title'] = u'Editar producto investigación artículo'
                    data['articulo'] = articulo = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['articulo'])))
                    initial = model_to_dict(articulo)
                    data['form'] = ArticuloInvestigacionDocenteForm(initial=initial)
                    return render(request, "pro_laboratoriocronograma/editarproductoarticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarproductoponencia':
                try:
                    data['title'] = u'Editar producto investigación ponecnia'
                    data['ponencia'] = ponencia = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['ponencia'])))
                    initial = model_to_dict(ponencia)
                    data['form'] = PonenciaInvestigacionDocenteForm(initial=initial)
                    return render(request, "pro_laboratoriocronograma/editarproductoponencia.html", data)
                except Exception as ex:
                    pass


            elif action == 'editarproductolibro':
                try:
                    data['title'] = u'Editar producto investigación libro'
                    data['libro'] = libro = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['libro'])))
                    initial = model_to_dict(libro)
                    data['form'] = LibroInvestigacionDocenteForm(initial=initial)
                    return render(request, "pro_laboratoriocronograma/editarproductolibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarproductocapitulolibro':
                try:
                    data['title'] = u'Editar producto investigación capítulo libro'
                    data['capitulolibro'] = capitulolibro = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['capitulolibro'])))
                    initial = model_to_dict(capitulolibro)
                    data['form'] = CapituloLibroInvestigacionDocenteForm(initial=initial)
                    return render(request, "pro_laboratoriocronograma/editarproductocapitulolibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'delproductoarticulo':
                try:
                    data['title'] = u'Borrar producto investigación artículo'
                    data['articulo'] = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['articulo'])))
                    return render(request, "pro_laboratoriocronograma/delproductoarticulo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delproductoponencia':
                try:
                    data['title'] = u'Borrar producto investigación ponencia'
                    data['ponencia'] = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['ponencia'])))
                    return render(request, "pro_laboratoriocronograma/delproductoponencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'delproductolibro':
                try:
                    data['title'] = u'Borrar producto investigación libro'
                    data['libro'] = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['libro'])))
                    return render(request, "pro_laboratoriocronograma/delproductolibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'delproductocapitulolibro':
                try:
                    data['title'] = u'Borrar producto investigación capítulo libro'
                    data['capitulolibro'] = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['capitulolibro'])))
                    return render(request, "pro_laboratoriocronograma/delproductocapitulolibro.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleproductoinvestigacion':
                try:
                    data = {}
                    data['tipo'] = tipo = int(request.GET['tipo'])
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
                    template = get_template("pro_laboratoriocronograma/detalleproductoinvestigcion.html")
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
                    return render(request, "pro_laboratoriocronograma/cronogramaproducto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcronogramaproducto':
                try:
                    data['title'] = u'Añadir  cronograma'
                    form = CronogramaTrabajoInvestigacionDocenteForm()
                    data['form'] = form
                    data['tipo'] = tipo = int(request.GET['tipo'])
                    if tipo == 1:
                        data['producto'] = ArticuloInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    elif tipo == 2:
                        data['producto'] = PonenciaInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    elif tipo == 3:
                        data['producto'] = LibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    else:
                        data['producto'] = CapituloLibroInvestigacionDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "pro_laboratoriocronograma/addcronogramaproducto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcronogramaproducto':
                try:
                    data['title'] = u'Editar cronograma'
                    data['cronograma'] = cronograma = CronogramaTrabajoInvestigacionDocente.objects.get(id=int(encrypt(request.GET['id'])))
                    if cronograma.articulo:
                        data['tipo'] = 1
                        data['producto'] = cronograma.articulo
                    elif cronograma.ponencia:
                        data['tipo'] = 2
                        data['producto'] = cronograma.ponencia
                    elif cronograma.libro:
                        data['tipo'] = 3
                        data['producto'] = cronograma.libro
                    else:
                        data['tipo'] = 4
                        data['producto'] = cronograma.capitulolibro
                    initial = model_to_dict(cronograma)
                    data['form'] = CronogramaTrabajoInvestigacionDocenteForm(initial=initial)
                    return render(request, "pro_laboratoriocronograma/editcronogramaproducto.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcronogramaproducto':
                try:
                    data['title'] = u'Borrar cronograma'
                    data['cronograma'] = cronograma = CronogramaTrabajoInvestigacionDocente.objects.get(id=int(encrypt(request.GET['id'])))
                    if cronograma.articulo:
                        data['tipo'] = 1
                        data['producto'] = cronograma.articulo
                    elif cronograma.ponencia:
                        data['tipo'] = 2
                        data['producto'] = cronograma.ponencia
                    elif cronograma.libro:
                        data['tipo'] = 3
                        data['producto'] = cronograma.libro
                    else:
                        data['tipo'] = 4
                        data['producto'] = cronograma.capitulolibro
                    return render(request, "pro_laboratoriocronograma/delcronogramaproducto.html", data)
                except Exception as ex:
                    pass

            elif action == 'verevidenciadesvinculadas':
                try:
                    data['title'] = u'Evidencias de actividades que han sido inactivadas'
                    data['evidenciaseliminadas'] = EvidenciaActividadDetalleDistributivo.objects.filter(
                        ((Q(desde__gte=periodo.inicio) & Q(hasta__lte=periodo.fin)) |
                         (Q(desde__lte=periodo.inicio) & Q(hasta__gte=periodo.fin)) |
                         (Q(desde__lte=periodo.fin) & Q(desde__gte=periodo.inicio)) |
                         (Q(hasta__gte=periodo.inicio) & Q(hasta__lte=periodo.fin)))
                        , criterio_id__isnull=False, actividaddetalledistributivo__id__isnull=True, usuario_creacion=profesor.persona.usuario).order_by('desde')
                    return render(request, "pro_laboratoriocronograma/verevidenciadesvinculadas.html", data)
                except Exception as ex:
                    pass

            elif action == 'aceptapreferenciaasignatura':
                try:
                    data['title'] = u'No deseo aplicar preferencia asignatura'
                    data['profesor'] = profesor
                    return render(request, "pro_laboratoriocronograma/aceptapreferenciaassignatura.html", data)
                except Exception as ex:
                    pass

            elif action == 'aceptapreferenciacriterio':
                try:
                    data['title'] = u'No deseo aplicar preferencias de criterio'
                    data['profesor'] = profesor
                    return render(request, "pro_laboratoriocronograma/aceptapreferenciacriterio.html", data)
                except Exception as ex:
                    pass

            elif action == 'aceptapreferenciahorario':
                try:
                    data['title'] = u'No deseo aplicar preferencias de horario'
                    data['profesor'] = profesor
                    return render(request, "pro_laboratoriocronograma/aceptapreferenciahorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'aceptapreferenciaasignaturaposgrado':
                try:
                    data['title'] = u'No deseo aplicar preferencias de asignatura de posgrado'
                    data['profesor'] = profesor
                    return render(request, "pro_laboratoriocronograma/aceptapreferenciaasignaturaposgrado.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcapacitacionth':
                try:
                    data['title'] = u'Registrar certificado - Hoja de vida'
                    data['convocatoria'] = request.GET['convocatoria']
                    data['idsolicitud'] = request.GET['id']
                    data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.GET['idcth']))
                    data['modalidad1'] = capacitacion.modalidad
                    form = CapacitacionPersonaDocenteForm(initial={'institucion': capacitacion.institucion,
                                                                   'nombre': capacitacion.nombre,
                                                                   'descripcion': capacitacion.descripcion,
                                                                   'tipocurso': capacitacion.tipocurso,
                                                                   'tipocertificacion': capacitacion.tipocertificacion,
                                                                   'tipocapacitacion': capacitacion.tipocapacitacion,
                                                                   'tipoparticipacion': capacitacion.tipoparticipacion,
                                                                   # 'auspiciante': capacitacion.auspiciante,
                                                                   # 'expositor': capacitacion.expositor,
                                                                   'anio': capacitacion.anio,
                                                                   # 'contexto': capacitacion.contextocapacitacion,
                                                                   # 'detallecontexto': capacitacion.detallecontextocapacitacion,
                                                                   'areaconocimiento': capacitacion.areaconocimiento,
                                                                   'subareaconocimiento': capacitacion.subareaconocimiento,
                                                                   'subareaespecificaconocimiento': capacitacion.subareaespecificaconocimiento,
                                                                   'pais': capacitacion.pais,
                                                                   'provincia': capacitacion.provincia,
                                                                   'canton': capacitacion.canton,
                                                                   'parroquia': capacitacion.parroquia,
                                                                   'fechainicio': capacitacion.fechainicio,
                                                                   'fechafin': capacitacion.fechafin,
                                                                   'horas': capacitacion.horas,
                                                                   'modalidad': capacitacion.modalidad,
                                                                   'otramodalidad': capacitacion.otramodalidad})
                    form.editar(capacitacion)
                    form.quitar_campo_archivo()
                    data['form'] = form
                    return render(request, "pro_laboratoriocronograma/editcapacitacionth.html", data)
                except Exception as ex:
                    pass

            elif action == 'inquietudconsultaestudiante':
                try:
                    data['title'] = u'Ingreso de Consulta de Estudiante'
                    search = None

                    # practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=perfilprincipal.inscripcion, status=True).exclude(culminada=True,retirado=True,tiposolicitud=2).distinct().order_by('-fecha_creacion')
                    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.get(pk=int(encrypt(request.GET['id'])))
                    inquietudes = InquietudPracticasPreprofesionales.objects.filter(status=True, practica=practicaspreprofesionalesinscripcion).order_by('-id')
                    data['practica'] = practicaspreprofesionalesinscripcion

                    # for pr in preinscripciones:
                    #     pr.recorrido1(request)

                    if 's' in request.GET:
                        search = request.GET['s']
                        s = search.split(" ")
                        if len(s) == 1:
                            inquietudes = inquietudes.filter(Q(inquietud__icontains=search))
                        elif len(s) == 2:
                            inquietudes = inquietudes.filter((Q(inquietud__icontains=s[0])))
                    # paging = MiPaginador(inquietudes, 10)
                    # p = 1
                    # try:
                    #     paginasesion = 1
                    #     if 'paginador' in request.session:
                    #         paginasesion = int(request.session['paginador'])
                    #     if 'page' in request.GET:
                    #         p = int(request.GET['page'])
                    #     else:
                    #         p = paginasesion
                    #     try:
                    #         page = paging.page(p)
                    #     except:
                    #         p = 1
                    #     page = paging.page(p)
                    # except:
                    #     page = paging.page(p)
                    # request.session['paginador'] = p
                    # data['paging'] = paging
                    # data['page'] = page
                    # data['rangospaging'] = paging.rangos_paginado(p)
                    data['inquietudes'] = inquietudes.order_by('-pk')
                    data['search'] = search if search else ""
                    return render(request, "pro_laboratoriocronograma/listarinquietudconsultaestudiante.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteinquietudconsultaestudiante':
                try:
                    data['title'] = u'Reporte de Inquietud de Estudiantes'
                    data['fechaimpresion'] = datetime.now().date()
                    # return render(request, "", data)
                    data['tutoriaspracticas'] = PracticasPreprofesionalesInscripcion.objects.select_related().filter(status=True, tutorunemi=profesor, culminada=False).distinct().exclude(estadosolicitud=3).order_by('-fecha_creacion').distinct()
                    data['profesor'] = profesor

                    return conviert_html_to_pdf(
                        'pro_laboratoriocronograma/reporteinquietudconsultaestudiante.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'excelinquietudconsultaestudiante':
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
                    ws = wb.add_sheet('practicas')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Listas_Inquietudes' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"N°", 1000),
                        (u"FECHA", 2700),
                        (u"ESTUDIANTE", 11000),
                        (u"CARRERA", 11000),
                        (u"INQUIETUD DEL ESTUDIANTE", 11000),
                        (u"RESPUESTA DEL TUTOR", 11000),
                        (u"OBSERVACIÓN", 11000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    lista_data = PracticasPreprofesionalesInscripcion.objects.select_related().filter(status=True, tutorunemi=profesor, culminada=False).distinct().exclude(estadosolicitud=3).order_by('-fecha_creacion').distinct()

                    row_num = 4
                    i = 0
                    for practicaspreprofesional in lista_data:
                        for index, inquietud in enumerate(practicaspreprofesional.inquietudes()):
                            campo1 = index + 1
                            campo2 = inquietud.fechaingreso
                            campo3 = practicaspreprofesional.inscripcion.persona.__str__()
                            campo4 = practicaspreprofesional.inscripcion.carrera.__str__()

                            campo5 = inquietud.inquietud
                            if inquietud.respuestas():
                                campo6 = inquietud.respuestas().respuesta
                            else:
                                campo6 = 'Sin Respuesta'
                            if inquietud.observacion:
                                campo7 = inquietud.observacion
                            else:
                                campo7 = 'Sin Obersvacion'
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, date_format)
                            ws.write(row_num, 2, campo3, font_style2)
                            ws.write(row_num, 3, campo4, font_style2)
                            ws.write(row_num, 4, campo5, font_style2)
                            ws.write(row_num, 5, campo6, font_style2)
                            ws.write(row_num, 6, campo7, font_style2)

                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'ver_rubrica':
                try:
                    data = {}
                    data['detalledistibutivo'] = detalledistibutivo = DetalleDistributivo.objects.get(pk=int(request.GET['id']))
                    template = get_template("pro_laboratoriocronograma/ver_rubrica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_calificaciones':
                try:
                    data = {}
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['idm'])))
                    data['inscritos'] = inscritos = materia.asignados_a_esta_materia_moodle()
                    template = get_template("pro_laboratoriocronograma/ver_calificaciones.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_recursos':
                try:
                    data = {}
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['idm'])))
                    template = get_template("pro_laboratoriocronograma/ver_recursos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verasistencias_linkmateria':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date() - timedelta(days=1)
                    cursor = connections['default'].cursor()
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    listaasistencias = []
                    # sql_old = "select distinct ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, " \
                    #       "ten.horario,ten.rangofecha, " \
                    #       "ten.rangodia,sincronica.fecha as sincronica,asincronica.fechaforo as asincronica, asignatura, paralelo,asincronica.idforomoodle as idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id,extract(week from ten.rangofecha::date) as numerosemana,ten.tipoprofesor,asincronica.enlaceuno,asincronica.enlacedos,asincronica.enlacetres " \
                    #       "from ( select distinct cla.tipoprofesor_id,cla.id as codigoclase, " \
                    #       "cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, " \
                    #       "cla.tipohorario, " \
                    #       "case " \
                    #       "WHEN cla.tipohorario in(2,8)  THEN 2 " \
                    #       "WHEN cla.tipohorario in(7,9)  THEN 7 " \
                    #       "end as horario, " \
                    #       "CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, " \
                    #       "EXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion,tipro.nombre as tipoprofesor " \
                    #       "from sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar, sga_tipoprofesor tipro " \
                    #       "where  cla.profesor_id=" + str(profesorseleccionado.id) + " and tipro.id!=10 and cla.activo=True and  cla.materia_id = mate.id and mate.asignaturamalla_id = asimalla.id and asimalla.malla_id=malla.id and asimalla.asignatura_id = asig.id and cla.turno_id=tur.id and asimalla.nivelmalla_id=nimalla.id and malla.carrera_id=carre.id and coorcar.carrera_id=carre.id " \
                    #                                                                 "AND cla.tipohorario IN (8, 9, 2, 7) and mate.nivel_id=niv.id and cla.tipoprofesor_id=tipro.id and niv.periodo_id=" + str(periodo.id) + "  " \
                    #                                                                                                                                                                                                         ") as ten " \
                    #                                                                                                                                                                                                         "left join " \
                    #                                                                                                                                                                                                         "(select clas.materia_id,asi.fecha_creacion::timestamp::date as fecha,asi.fecha_creacion as fecharegistro " \
                    #                                                                                                                                                                                                         "from sga_clasesincronica asi, sga_clase clas " \
                    #                                                                                                                                                                                                         "where asi.clase_id=clas.id and clas.profesor_id=" + str(profesorseleccionado.id) + " " \
                    #                                                                                                                                                                                                                                                                                             ") as sincronica on ten.rangofecha=fecha and ten.horario=2 " \
                    #                                                                                                                                                                                                                                                                                             "left join " \
                    #                                                                                                                                                                                                                                                                                             "(select  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id,enlaceuno,enlacedos,enlacetres " \
                    #                                                                                                                                                                                                                                                                                             "from sga_claseasincronica asi, sga_clase clas " \
                    #                                                                                                                                                                                                                                                                                             "where asi.clase_id=clas.id " \
                    #                                                                                                                                                                                                                                                                                             ") as asincronica on asincronica.materia_id=ten.materia_id and ten.rangofecha=asincronica.fechaforo and ten.horario=2 and ten.tipoprofesor_id=asincronica.tipoprofesor_id " \
                    #                                                                                                                                                                                                                                                                                             "left join " \
                    #                                                                                                                                                                                                                                                                                             "(select nolab.observaciones, nolab.fecha from sga_diasnolaborable nolab " \
                    #                                                                                                                                                                                                                                                                                             "where nolab.periodo_id=" + str(periodo.id) + ") as nolaborables on nolaborables.fecha = ten.rangofecha " \
                    #                                                                                                                                                                                                                                                                                                                                           "where ten.dia=ten.rangodia and ten.rangofecha <'" + str(hoy) + "' order by materia_id,ten.rangofecha,ten.turno_id,tipohorario"
                    sql = f"""
                            SELECT	DISTINCT 
                                    ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, 
                                    ten.horario,ten.rangofecha, ten.rangodia,
                                    sincronica.fecha as sincronica,
                                    asincronica.fechaforo as asincronica, 
                                    asignatura, paralelo,
                                   CASE 
                                    WHEN asincronica.idforomoodle IS NOT  NULL THEN asincronica.idforomoodle 
                                    ELSE sincronica.idforomoodle 
                                   END  idforomoodle,
                                    ten.comienza,ten.termina,nolaborables.fecha,
                                    nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id,
                                    extract(week from ten.rangofecha::date) as numerosemana,ten.tipoprofesor,
                                    CASE WHEN asincronica.idforomoodle IS NOT  NULL THEN asincronica.enlaceuno  ELSE sincronica.enlaceuno END enlaceuno,
                                    CASE WHEN asincronica.idforomoodle IS NOT  NULL THEN asincronica.enlacedos  ELSE sincronica.enlacedos END enlacedos,
                                    CASE WHEN asincronica.idforomoodle IS NOT  NULL THEN asincronica.enlacetres  ELSE sincronica.enlacetres END enlacetres	
                            FROM ( SELECT DISTINCT 
                                                cla.tipoprofesor_id,cla.id as codigoclase, cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, cla.tipohorario, 
                                                CASE WHEN cla.tipohorario in(2,8)  THEN 2 WHEN cla.tipohorario in(7,9)  THEN 7 end as horario, 
                                                CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, 
                                                EXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,
                                                asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,
                                                nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion,
                                                tipro.nombre as tipoprofesor 
                                        FROM	
                                            sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,
                                            sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,
                                            sga_carrera carre, sga_coordinacion_carrera coorcar, sga_tipoprofesor tipro 
                                        WHERE  
                                            cla.profesor_id={profesorseleccionado.id} 
                                            AND tipro.id!=10 
                                            AND cla.activo=TRUE 
                                            AND  cla.materia_id = mate.id 
                                            AND mate.asignaturamalla_id = asimalla.id 
                                            AND asimalla.malla_id=malla.id 
                                            AND asimalla.asignatura_id = asig.id 
                                            AND cla.turno_id=tur.id 
                                            AND asimalla.nivelmalla_id=nimalla.id 
                                            AND malla.carrera_id=carre.id 
                                            AND coorcar.carrera_id=carre.id 
                                            AND cla.tipohorario IN (8, 9, 2, 7) 
                                            AND mate.nivel_id=niv.id 
                                            AND cla.tipoprofesor_id=tipro.id and niv.periodo_id={periodo.id}  ) as ten 

                                        LEFT JOIN (SELECT clas.id  clase_id, clas.materia_id,asi.fecha_creacion::timestamp::date AS fecha, clas.tipoprofesor_id,
                                                       asi.fecha_creacion AS fecharegistro, asi.fechaforo AS fechaforo, asi.idforomoodle idforomoodle,
                                                          asi.enlaceuno,asi.enlacedos, asi.enlacetres
                                                        FROM sga_clasesincronica asi, sga_clase clas 
                                                        WHERE asi.clase_id=clas.id AND clas.profesor_id={profesorseleccionado.id} ) as sincronica 
                                                        ON (ten.rangofecha=fechaforo AND ten.horario=2 AND sincronica.materia_id=ten.materia_id  AND sincronica.tipoprofesor_id=ten.tipoprofesor_id)OR 
                                                   (sincronica.materia_id=ten.materia_id AND ten.horario=2  AND sincronica.fechaforo=ten.rangofecha AND EXTRACT(dow from  sincronica.fechaforo)=ten.rangodia AND sincronica.tipoprofesor_id=ten.tipoprofesor_id) 


                                     LEFT JOIN(SELECT   
                                                      clas.id  clase_id,  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id, 
                                                             asi.enlaceuno,asi.enlacedos, asi.enlacetres
                                                  FROM sga_claseasincronica asi, sga_clase clas 
                                                  WHERE asi.clase_id=clas.id AND asi.status=true) AS asincronica 
                                          ON (asincronica.materia_id=ten.materia_id  AND  ten.rangofecha=asincronica.fechaforo AND	ten.horario=2  AND asincronica.tipoprofesor_id=ten.tipoprofesor_id)OR 
                                              (asincronica.materia_id=ten.materia_id AND	 asincronica.fechaforo=ten.rangofecha AND  EXTRACT(dow from  asincronica.fechaforo)=ten.rangodia AND asincronica.tipoprofesor_id=ten.tipoprofesor_id)

                                        LEFT	JOIN (SELECT nolab.observaciones, nolab.fecha 
                                                        FROM sga_diasnolaborable nolab WHERE nolab.periodo_id={periodo.id}) as nolaborables on nolaborables.fecha = ten.rangofecha 
                            WHERE	 
                                ten.dia=ten.rangodia 
                                AND ten.rangofecha <'{hoy}' 
                                ORDER	BY materia_id,ten.rangofecha,ten.turno_id,tipohorario
                           """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        materia = None
                        if Materia.objects.values("id").filter(pk=cuentamarcadas[5]).exists():
                            materia = Materia.objects.get(pk=cuentamarcadas[5])
                        sinasistencia = periodo.tiene_dias_nolaborables(fecha=cuentamarcadas[8], materia=materia)
                        dianolaborable = periodo.dias_nolaborables(fecha=cuentamarcadas[8], materia=materia)

                        # sinasistencia = False
                        # if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], status=True).exists():
                        #     if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                        #         sinasistencia = True
                        # else:
                        #     if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                        #         if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #             sinasistencia = True
                        #     else:
                        #         if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                        #             if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #                 sinasistencia = True
                        #         else:
                        #             if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                        #                 if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                        #                     sinasistencia = True
                        listaasistencias.append([cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                                                 cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                                                 cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                                                 cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                                                 cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                                                 sinasistencia, cuentamarcadas[24], cuentamarcadas[25], cuentamarcadas[26],
                                                 cuentamarcadas[27], cuentamarcadas[28], dianolaborable])

                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    data['profesormateria'] = ProfesorMateria.objects.filter(profesor=profesorseleccionado, materia__nivel__periodo=periodo, tipoprofesor__imparteclase=True, activo=True).exclude(materia__asignaturamalla__malla__carrera__coordinacion__id=9).exclude(tipoprofesor_id=15).distinct().order_by('desde', 'materia__asignatura__nombre')
                    return render(request, "pro_laboratoriocronograma/verasistencias_link.html", data)
                except Exception as ex:
                    pass

            elif action == 'verasistencias_linkorientacion':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    cursor = connections['default'].cursor()
                    listaasistencias = []
                    sql = "select distinct ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, " \
                          "ten.horario,ten.rangofecha, " \
                          "ten.rangodia,sincronica.fecha as sincronica,asincronica.fechaforo as asincronica, asignatura, paralelo,asincronica.idforomoodle as idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id,extract(week from ten.rangofecha::date) as numerosemana,ten.tipoprofesor,asincronica.enlaceuno,asincronica.enlacedos,asincronica.enlacetres " \
                          "from ( select distinct cla.tipoprofesor_id,cla.id as codigoclase, " \
                          "cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, " \
                          "cla.tipohorario, " \
                          "case " \
                          "WHEN cla.tipohorario in(2,8)  THEN 2 " \
                          "WHEN cla.tipohorario in(7,9)  THEN 7 " \
                          "end as horario, " \
                          "CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE ) as rangofecha, " \
                          "EXTRACT (isodow  FROM  CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE )) as rangodia,asig.nombre as asignatura, mate.paralelo as paralelo,tur.comienza,tur.termina,nimalla.nombre as nivelmalla,nimalla.id as idnivelmalla,malla.carrera_id as idcarrera,coorcar.coordinacion_id as idcoordinacion,tipro.nombre as tipoprofesor " \
                          "from sga_clase cla , sga_materia mate, sga_asignaturamalla asimalla,sga_asignatura asig,sga_turno tur,sga_nivel niv,sga_nivelmalla nimalla,sga_malla malla,sga_carrera carre, sga_coordinacion_carrera coorcar, sga_tipoprofesor tipro " \
                          "where cla.profesor_id=" + str(profesorseleccionado.id) + " and tipro.id=10 and cla.materia_id = mate.id and mate.asignaturamalla_id = asimalla.id and asimalla.malla_id=malla.id and asimalla.asignatura_id = asig.id and cla.turno_id=tur.id and asimalla.nivelmalla_id=nimalla.id and malla.carrera_id=carre.id and coorcar.carrera_id=carre.id " \
                                                                                    "AND cla.tipohorario IN (8, 9, 2, 7) and mate.nivel_id=niv.id and cla.tipoprofesor_id=tipro.id and niv.periodo_id=" + str(periodo.id) + "  " \
                                                                                                                                                                                                                            ") as ten " \
                                                                                                                                                                                                                            "left join " \
                                                                                                                                                                                                                            "(select clas.materia_id,asi.fecha_creacion::timestamp::date as fecha,asi.fecha_creacion as fecharegistro " \
                                                                                                                                                                                                                            "from sga_clasesincronica asi, sga_clase clas " \
                                                                                                                                                                                                                            "where asi.clase_id=clas.id and clas.profesor_id=" + str(profesorseleccionado.id) + " " \
                                                                                                                                                                                                                                                                                                                ") as sincronica on ten.rangofecha=fecha and ten.horario=2 " \
                                                                                                                                                                                                                                                                                                                "left join " \
                                                                                                                                                                                                                                                                                                                "(select  clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id,enlaceuno,enlacedos,enlacetres " \
                                                                                                                                                                                                                                                                                                                "from sga_claseasincronica asi, sga_clase clas " \
                                                                                                                                                                                                                                                                                                                "where asi.clase_id=clas.id " \
                                                                                                                                                                                                                                                                                                                ") as asincronica on asincronica.materia_id=ten.materia_id and ten.rangofecha=asincronica.fechaforo and ten.horario=2 and ten.tipoprofesor_id=asincronica.tipoprofesor_id " \
                                                                                                                                                                                                                                                                                                                "left join " \
                                                                                                                                                                                                                                                                                                                "(select nolab.observaciones, nolab.fecha from sga_diasnolaborable nolab " \
                                                                                                                                                                                                                                                                                                                "where nolab.periodo_id=" + str(periodo.id) + ") as nolaborables on nolaborables.fecha = ten.rangofecha " \
                                                                                                                                                                                                                                                                                                                                                              "where ten.dia=ten.rangodia and ten.rangofecha <'" + str(hoy) + "' order by materia_id,ten.rangofecha,ten.turno_id,tipohorario"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    for cuentamarcadas in results:
                        sinasistencia = False
                        if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], status=True).exists():
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                                sinasistencia = True
                        else:
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                    sinasistencia = True
                            else:
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                    if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                        sinasistencia = True
                                else:
                                    if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                        if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                            sinasistencia = True
                        listaasistencias.append([cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                                                 cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                                                 cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                                                 cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                                                 cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                                                 sinasistencia, cuentamarcadas[24], cuentamarcadas[25], cuentamarcadas[26],
                                                 cuentamarcadas[27], cuentamarcadas[28]])

                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1
                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica

                    data['registroclases'] = RegistroClaseTutoriaDocente.objects.filter(status=True, horario__profesor=profesorseleccionado, horario__periodo=periodo).order_by('fecha', 'numerosemana')

                    data['solicitudestutoria'] = SolicitudTutoriaIndividual.objects.filter(status=True, horario__profesor=profesorseleccionado, horario__periodo=periodo, estado=3).order_by('tipotutoria')
                    return render(request, "pro_laboratoriocronograma/verasistencias_link.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadocontenidos':
                try:
                    data['title'] = u'Criterio'
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    data['criterio'] = CriterioDocencia.objects.get(pk=int(request.GET['idcriterio']))
                    data['listadomaterias'] = Materia.objects.filter(status=True, pk__in=profesorseleccionado.profesormateria_set.values_list('materia_id').filter(materia__nivel__periodo=periodo, activo=True, status=True))
                    return render(request, "pro_laboratoriocronograma/listadocontenidos.html", data)
                except Exception as ex:
                    pass

            elif action == 'planificacionrecurso':
                try:
                    data['title'] = u'Criterio'
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    data['periodo'] = periodo
                    data['criterio'] = CriterioDocenciaPeriodo.objects.get(pk=int(request.GET['idcriterioperiodo']))
                    data['listadomaterias'] = Materia.objects.filter(status=True, pk__in=profesorseleccionado.profesormateria_set.values_list('materia_id').filter(materia__nivel__periodo=periodo, activo=True, status=True))
                    return render(request, "pro_laboratoriocronograma/planificacionrecurso.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadomateriales':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    data['criterio'] = CriterioDocencia.objects.get(pk=int(request.GET['idcriterio']))
                    data['listadomaterias'] = Materia.objects.filter(status=True, pk__in=profesorseleccionado.profesormateria_set.values_list('materia_id').filter(materia__nivel__periodo=periodo, activo=True, status=True))
                    return render(request, "pro_laboratoriocronograma/listadomateriales.html", data)
                except Exception as ex:
                    pass

            elif action == 'contenidocalificado':
                try:
                    data['title'] = u'Criterio'
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    data['criterio'] = CriterioDocencia.objects.get(pk=int(request.GET['idcriterio']))
                    # listacarreras = Carrera.objects.values_list('id').filter(modalidad=3, status=True).exclude(pk=133)
                    # data['listadomaterias'] = Materia.objects.filter(pk__in=profesorseleccionado.profesormateria_set.values_list('materia_id').filter(materia__nivel__periodo=periodo,materia__nivel__modalidad_id__in=[1,2], status=True))
                    # data['listadomaterias'] = Materia.objects.filter(pk__in=profesorseleccionado.profesormateria_set.values_list('materia_id').filter(materia__nivel__periodo=periodo, materia__nivel__modalidad_id__in=[1, 2, 3], activo=True, status=True).exclude(materia__asignaturamalla__malla__carrera_id__in=listacarreras))
                    data['listadomaterias'] = Materia.objects.filter(status=True, pk__in=profesorseleccionado.profesormateria_set.values_list('materia_id').filter(materia__nivel__periodo=periodo, materia__nivel__modalidad_id__in=[1, 2, 3], activo=True, status=True))
                    return render(request, "pro_laboratoriocronograma/contenidocalificado.html", data)
                except Exception as ex:
                    pass

            elif action == 'contenidocalificadoonline':
                try:
                    data['title'] = u'Actividades'
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['tipoevi'] = int(encrypt(request.GET['tipoevi']))
                    data['criterio'] = CriterioDocencia.objects.get(pk=int(request.GET['idcriterio']))
                    data['listadomaterias'] = listadomaterias = Materia.objects.filter(status=True, pk__in=profesorseleccionado.profesormateria_set.values_list('materia_id').filter(materia__nivel__periodo=periodo, materia__nivel__modalidad_id=3, activo=True, status=True))
                    data['periodo'] = periodo
                    data['coord'] = 0
                    lista1 = ""
                    if listadomaterias:
                        matriculados = MateriaAsignada.objects.filter(materiaasignadaretiro__isnull=True, matricula__estado_matricula__in=[2, 3], materia__id__in=listadomaterias.values_list('id', flat=True)).distinct()
                        for x in matriculados:
                            if x.id != matriculados.order_by('-id')[0].id:
                                if x.matricula.inscripcion.persona.idusermoodle:
                                    lista1 += str(x.matricula.inscripcion.persona.idusermoodle) + ","
                            else:
                                lista1 += str(x.matricula.inscripcion.persona.idusermoodle)
                    data['lista'] = lista1
                    return render(request, "pro_laboratoriocronograma/contenidocalificadoonline.html", data)
                except Exception as ex:
                    pass

            elif action == 'veractividadrevisor':
                try:
                    data['title'] = u'Actividad revisor'
                    data['profesor'] = profesorseleccionado = Profesor.objects.get(pk=int(encrypt(request.GET['profesorid'])))
                    data['opcion'] = int(encrypt(request.GET['opcion']))
                    data['criterio'] = CriterioGestion.objects.get(pk=int(request.GET['idcriterio']))
                    # tareasaprobadas = HistorialaprobacionTarea.objects.filter(tarea__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True)
                    # tareaspracticas = HistorialaprobacionTareaPractica.objects.filter(tareapractica__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True)
                    # forosaprobadas = HistorialaprobacionForo.objects.filter(foro__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True)
                    # diapositivasaprobadas = HistorialaprobacionDiapositiva.objects.filter(diapositiva__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True)
                    # guiaestudianteaprobadas = HistorialaprobacionGuiaEstudiante.objects.filter(guiaestudiante__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True)
                    # guiadocenteaprobadas = HistorialaprobacionGuiaDocente.objects.filter(guiadocente__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True)
                    # compendioaprobadas = HistorialaprobacionCompendio.objects.filter(compendio__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True)
                    # testaprobadas = HistorialaprobacionTest.objects.filter(test__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True)
                    data['totaltareas'] = HistorialaprobacionTarea.objects.filter(tarea__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True).count()
                    data['totalforos'] = HistorialaprobacionForo.objects.filter(foro__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True).count()
                    data['totaltareaspracticas'] = HistorialaprobacionTareaPractica.objects.filter(tareapractica__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True).count()
                    data['totaldiapositivasaprobadas'] = HistorialaprobacionDiapositiva.objects.filter(diapositiva__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True).count()
                    data['totalguiaestudianteaprobadas'] = HistorialaprobacionGuiaEstudiante.objects.filter(guiaestudiante__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True).count()
                    data['totalguiadocenteaprobadas'] = HistorialaprobacionGuiaDocente.objects.filter(guiadocente__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True).count()
                    data['totalcompendioaprobadas'] = HistorialaprobacionCompendio.objects.filter(compendio__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True).count()
                    data['totaltestaprobadas'] = HistorialaprobacionTest.objects.filter(test__silabosemanal__silabo__materia__nivel__periodo=periodo, usuario_creacion=profesorseleccionado.persona.usuario, estado_id=2, status=True).count()
                    return render(request, "pro_laboratoriocronograma/veractividadrevisor.html", data)
                except Exception as ex:
                    pass

            elif action == 'ver_detalleevidencia':
                try:
                    data = {}
                    data['evidencia'] = evidencia = EvidenciaActividadDetalleDistributivo.objects.get(pk=int(request.GET['id']))
                    data['listadoanexos'] = evidencia.anexoevidenciaactividad_set.filter(status=True)
                    data['historial'] = evidencia.evidenciaactividadaudi_set.filter(status=True)
                    data['historialestados'] = evidencia.historialaprobacionevidenciaactividad_set.filter(status=True)
                    template = get_template("pro_laboratoriocronograma/ver_detalleevidencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'tutoriapractica':
                try:
                    data['title'] = u'Registro de tutorías en prácticas'
                    hoy = datetime.now().date()
                    data['hoy_str'] = hoy
                    panio = hoy.year
                    pmes = hoy.month
                    fecha = hoy
                    if 'proximo' in request.GET:
                        mes = int(request.GET['mes'])
                        anio = int(request.GET['anio'])
                        pmes = mes + 1
                        if pmes == 13:
                            pmes = 1
                            panio = anio + 1
                        else:
                            panio = anio
                    if 'anterior' in request.GET:
                        mes = int(request.GET['mes'])
                        anio = int(request.GET['anio'])
                        pmes = mes - 1
                        if pmes == 0:
                            pmes = 12
                            panio = anio - 1
                        else:
                            panio = anio
                    fechainicio = date(panio, pmes, 1)
                    try:
                        fechafin = date(panio, pmes, 31)
                    except Exception as ex:
                        try:
                            fechafin = date(panio, pmes, 30)
                        except Exception as ex:
                            try:
                                fechafin = date(panio, pmes, 29)
                            except Exception as ex:
                                fechafin = date(panio, pmes, 28)
                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listaadicionarficha = {}
                    listafichas = {}
                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        diatut = {i: False}
                        tutoriadia = {i: None}
                        lista.update(dia)
                        listaadicionarficha.update(diatut)
                        listafichas.update(tutoriadia)
                    comienzo = False
                    fin = False
                    num = 0
                    for i in lista.items():
                        try:
                            fecha = date(s_anio, s_mes, s_dia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(s_anio, s_mes, s_dia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: s_dia}
                            lista.update(dia)
                            if date(s_anio, s_mes, s_dia) >= hoy:
                                diatut = {i[0]: True}
                                listaadicionarficha.update(diatut)
                            registratutoria = PracticasTutoria.objects.select_related('practica').filter(practica__tutorunemi=profesor, fechainicio=fecha, status=True)
                            registraagenda = AgendaPracticasTutoria.objects.select_related('docente').filter(docente=perfilprincipal.profesor, status=True, fecha=fecha).exists()
                            diaact = []
                            diaagact = []
                            if registratutoria:
                                totalregistratutoria = registratutoria[0].total_detalles_tutorias(profesor)
                                diaact.append(['default', totalregistratutoria.__str__(), 'Tutorias', registratutoria[0], fecha, True, registraagenda])
                            else:
                                diaact.append([None, None, None, None, fecha, False, registraagenda])

                            listafichas.update({i[0]: diaact})
                            s_dia += 1
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    # data['habiles'] = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo).values_list('dia', flat=True) if HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo).exists() else [1, 2, 3, 4, 5, 6, 7]
                    data['habiles'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['listafichas'] = listafichas
                    data['listaadicionarficha'] = listaadicionarficha
                    data['dia_actual'] = datetime.now().date().day
                    dia_anterior = datetime.now().date() + timedelta(days=-2)
                    data['dia_anterior'] = dia_anterior.day
                    data['mostrar_dia_anterior'] = fecha.month == dia_anterior.month and fecha.year == dia_anterior.year
                    data['mostrar_dia_actual'] = fecha.month == datetime.now().date().month and fecha.year == datetime.now().date().year
                    querytutorias = AgendaPracticasTutoria.objects.select_related('docente').filter(docente=perfilprincipal.profesor, status=True, fecha__month=s_mes, fecha__year=s_anio)
                    data['tutoriashoy'] = tutoriashoy = querytutorias.filter(fecha=hoy).order_by('-fecha', 'hora_inicio')
                    data['tutpendientesfin'] = querytutorias.filter(fecha__lt=hoy, estados_agenda=0).count()
                    data['tutoriasagendadas'] = tutoriasmes = querytutorias.exclude(fecha=hoy).order_by('-fecha', 'hora_inicio')
                    data['tutoriasdehoy'] = tutoriashoy.filter(estados_agenda=0).count()
                    data['tutoriasgeneral'] = querytutorias.count()
                    data['tutoriaspracticas'] = tutoriaspracticas = PracticasPreprofesionalesInscripcion.objects.select_related('tutorunemi').filter(status=True, tutorunemi=profesor, culminada=False).distinct().exclude(estadosolicitud=3)
                    data['total_supervisorpracticas'] = tutoriaspracticas.count()
                    data['tiene_planificacion'] = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo).exists()
                    return render(request, "pro_laboratoriocronograma/viewtutorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'practicastutoria':
                try:
                    data['title'] = u'Registro de tutorías en prácticas'
                    data['estudiantes'] = PracticasPreprofesionalesInscripcion.objects.filter(status=True, culminatutoria=False, culminada=False, tutorunemi=perfilprincipal.profesor).exclude(estadosolicitud=3)

                    return render(request, "pro_laboratoriocronograma/viewregistrotutorias.html", data)
                except Exception as ex:
                    pass

            elif action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones Informe Mensual Practicas Pre Profesionales'
                    url_vars = ''
                    url_vars += '&action={}'.format(action)
                    query = ConfiguracionInformePracticasPreprofesionales.objects.filter(status=True, persona=profesor).order_by('-anio', '-mes')
                    data["url_vars"] = url_vars
                    paging = MiPaginador(query, 15)
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
                    data['listado'] = page.object_list
                    data['distributivo'] = DetalleDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo__criterio__id=TUTOR_PRACTICAS_INTERNADO_ROTATIVO, status=True).first()
                    return render(request, "pro_laboratoriocronograma/configuraciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'addconfiguracion':
                try:
                    data['title'] = u'Adicionar Configuración Informe Mensual'
                    mensajeantecedentes = 'De acuerdo a los Lineamientos para el Periodo Académico Estudiantil establece que “4.1.N Para el caso de la actividad de Dirección,' \
                                          ' tutorías, seguimiento y evaluación de prácticas o pasantías pre profesionales, se considerará una carga entre 1 a 4 horas, considerando que por cada hora asignada el profesor ' \
                                          'tendrá a su cargo 5 estudiantes” Según el programa de prácticas pre profesionales de la carrera establece “Las actividades a desarrollar por el estudiante en el campo laboral y ' \
                                          'las horas por itinerario”. Mediante documento de autorización emitido por la Dirección de Vinculación y notificación mediante el SGA sobre la asignación como tutor académico ' \
                                          'se ejecuta las respectivas tutorías académicas a los estudiantes asignados.'
                    form = ConfiguracionInformePPPForm()
                    data['form'] = form
                    data['date'] = datetime.now()
                    return render(request, "pro_laboratoriocronograma/formconfiguracion.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconfiguracion':
                try:
                    data['title'] = u'Editar Configuración Informe Mensual'
                    data['filtro'] = filtro = ConfiguracionInformePracticasPreprofesionales.objects.get(pk=int(request.GET['id']))
                    data['form'] = ConfiguracionInformePPPForm(initial=model_to_dict(filtro))
                    return render(request, "pro_laboratoriocronograma/formconfiguracion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delconfiguracion':
                try:
                    data['title'] = u'ELIMINAR CONIGURACION'
                    data['filtro'] = ConfiguracionInformePracticasPreprofesionales.objects.get(pk=request.GET['id'])
                    return render(request, 'pro_laboratoriocronograma/delconfiguracion.html', data)
                except Exception as ex:
                    pass

            elif action == 'detalle_clasesvideo':
                try:
                    data['title'] = u'Detalle clases sincrónicas y asincrónicas'
                    data['hoy'] = hoy = datetime.now().date()
                    listaasistencias = []
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['materiaid'])))
                    materia.update_silabo_semanal_numero_semana()
                    cursor = connections['default'].cursor()
                    sql = f"""
                        SELECT DISTINCT 
                        ten.codigoclase,ten.dia,ten.turno_id,ten.inicio,ten.fin,ten.materia_id,ten.tipohorario, ten.horario,
                        ten.rangofecha, ten.rangodia,0 AS sincronica,asincronica.fechaforo AS asincronica, asignatura, paralelo,
                        asincronica.idforomoodle AS idforomoodle,ten.comienza,ten.termina,nolaborables.fecha,nolaborables.observaciones,
                        ten.nivelmalla,ten.idnivelmalla,ten.idcarrera,ten.idcoordinacion,ten.tipoprofesor_id, EXTRACT(week
                        FROM ten.rangofecha:: DATE) AS numerosemana,ten.tipoprofesor,ten.subirenlace, CASE EXTRACT(dow
                        FROM ten.rangofecha) WHEN 1 THEN 'Lunes' WHEN 2 THEN 'Martes' WHEN 3 THEN 'Miercoles' WHEN 4 THEN 'Jueves' WHEN 5 THEN 'Viernes' WHEN 6 THEN 'Sabado' ELSE 'Domingo' END AS nombredia
                        FROM (
                            SELECT DISTINCT 
                                niv.id AS nivel_id, mate.nivel_id AS nivel_materia, niv.periodo_id AS periodo,
                                cla.tipoprofesor_id,cla.id AS codigoclase, cla.dia,cla.turno_id,cla.inicio,cla.fin,cla.materia_id, cla.tipohorario, 
                                CASE WHEN cla.tipohorario in(2,8) THEN 2 WHEN cla.tipohorario in(7,9) THEN 7 END AS horario, 
                                CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE) AS rangofecha, 
                                EXTRACT (isodow FROM CURRENT_DATE + generate_series(cla.inicio- CURRENT_DATE, cla.fin - CURRENT_DATE)) AS rangodia,
                                asig.nombre AS asignatura, mate.paralelo AS paralelo,tur.comienza,tur.termina,nimalla.nombre AS nivelmalla,nimalla.id AS idnivelmalla,malla.carrera_id AS 
                                idcarrera,coorcar.coordinacion_id AS idcoordinacion,tipro.nombre AS tipoprofesor,cla.subirenlace
                            FROM sga_clase cla
                                INNER JOIN sga_materia mate ON mate.id=cla.materia_id
                                INNER JOIN sga_asignaturamalla asimalla ON asimalla.id=mate.asignaturamalla_id
                                INNER JOIN sga_asignatura asig ON asig.id=mate.asignatura_id
                                INNER JOIN sga_turno tur ON tur.id=cla.turno_id
                                INNER JOIN sga_nivel niv ON niv.id=mate.nivel_id
                                INNER JOIN sga_nivelmalla nimalla ON nimalla.id=asimalla.nivelmalla_id
                                INNER JOIN sga_malla malla ON malla.id=asimalla.malla_id
                                INNER JOIN sga_carrera carre ON carre.id=malla.carrera_id
                                INNER JOIN sga_coordinacion_carrera coorcar ON coorcar.carrera_id=carre.id
                                INNER JOIN sga_tipoprofesor tipro ON tipro.id=cla.tipoprofesor_id	
                            WHERE 
                                cla.status AND cla.activo AND cla.profesor_id = {profesor.id} AND cla.materia_id = mate.id AND mate.asignaturamalla_id = asimalla.id AND asimalla.malla_id=malla.id 
                                AND asimalla.asignatura_id = asig.id AND cla.turno_id=tur.id AND asimalla.nivelmalla_id=nimalla.id AND malla.carrera_id=carre.id 
                                AND coorcar.carrera_id=carre.id AND cla.tipohorario IN (8, 9, 2, 7) AND mate.nivel_id=niv.id AND cla.tipoprofesor_id=tipro.id AND niv.periodo_id = {periodo.id}	
                        ) AS ten left JOIN (
                            SELECT clas.materia_id,asi.fechaforo,asi.idforomoodle, clas.tipoprofesor_id,clas.id AS id_clase
                            FROM sga_claseasincronica asi, sga_clase clas
                            WHERE asi.clase_id=clas.id and asi.status and clas.status
                        ) AS asincronica ON asincronica.materia_id=ten.materia_id AND ten.rangofecha=asincronica.fechaforo AND ten.horario in(2,7) AND ten.tipoprofesor_id=asincronica.tipoprofesor_id 
                        left JOIN (
                            SELECT nolab.observaciones, nolab.fecha
                            FROM sga_diasnolaborable nolab
                            WHERE nolab.periodo_id = {periodo.id} AND nolab.status
                        ) AS nolaborables ON nolaborables.fecha = ten.rangofecha
                        WHERE ten.dia=ten.rangodia AND ten.materia_id = {materia.id} AND 
                            EXTRACT(week FROM ten.rangofecha:: DATE) IN (SELECT semana FROM sga_silabosemanal silabosemanal 
                            INNER JOIN sga_silabo silabo ON (silabosemanal.silabo_id = silabo.id) 
                            WHERE (silabo.materia_id = {materia.id} AND silabo.status AND silabosemanal.status)
                        )
                        ORDER BY ten.rangofecha,materia_id,ten.comienza,tipohorario
                        """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    totalsincronica = 0
                    totalasincronica = 0
                    totalplansincronica = 0
                    totalplanasincronica = 0
                    idclase, numdia = 0, 0
                    listaSubirEnlace = []
                    for (i, cuentamarcadas) in enumerate(results):
                        if numdia and not numdia == cuentamarcadas[1]:
                            if not results[i - 1][26]:
                                listaSubirEnlace.append(idclase)
                        idclase, numdia, sinasistencia = cuentamarcadas[0], cuentamarcadas[1], False
                        if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], status=True).exists():
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id=cuentamarcadas[20], fecha=cuentamarcadas[8], status=True).exists():
                                sinasistencia = True
                        else:
                            if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, status=True).exists():
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id=cuentamarcadas[21], nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                    sinasistencia = True
                            else:
                                if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                    if periodo.diasnolaborable_set.filter(coordinacion_id=cuentamarcadas[22], carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                        sinasistencia = True
                                else:
                                    if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, status=True).exists():
                                        if periodo.diasnolaborable_set.filter(coordinacion_id__isnull=True, carrera_id__isnull=True, nivelmalla_id__isnull=True, fecha=cuentamarcadas[8], status=True).exists():
                                            sinasistencia = True
                        listaasistencias.append([cuentamarcadas[0], cuentamarcadas[1], cuentamarcadas[2], cuentamarcadas[3],
                                                 cuentamarcadas[4], cuentamarcadas[5], cuentamarcadas[6], cuentamarcadas[7],
                                                 cuentamarcadas[8], cuentamarcadas[9], cuentamarcadas[10], cuentamarcadas[11],
                                                 cuentamarcadas[12], cuentamarcadas[13], cuentamarcadas[14], cuentamarcadas[15],
                                                 cuentamarcadas[16], cuentamarcadas[17], cuentamarcadas[18], cuentamarcadas[19],
                                                 sinasistencia, cuentamarcadas[24], cuentamarcadas[25], cuentamarcadas[26], cuentamarcadas[27], 0])

                        if cuentamarcadas[7] == 2:
                            totalsincronica += 1
                        if cuentamarcadas[7] == 7:
                            totalasincronica += 1
                        totalplansincronica += 1
                        if cuentamarcadas[11]:
                            totalplanasincronica += 1

                    numsemanas = SilaboSemanal.objects.values_list('semana', 'fechainiciosemana', 'fechafinciosemana').filter(silabo__materia=materia, status=True, silabo__status=True, silabo__materia__status=True).distinct('semana').order_by('semana')
                    if len(listaSubirEnlace):
                        listaSubirEnlace.append(idclase)
                        Clase.objects.filter(pk__in=set(listaSubirEnlace), status=True, materia=materia, activo=True).update(subirenlace=True)

                    for (i, x) in enumerate(listaasistencias):

                        if len(listaSubirEnlace):
                            x[23] = True if x[0] in set(listaSubirEnlace) else None

                        for y in numsemanas:
                            if x[8] in daterange(y[1], y[2] + timedelta(1)):
                                x[25] = y[0]

                    data['listaasistencias'] = listaasistencias
                    data['totalsincronica'] = totalsincronica
                    data['totalasincronica'] = totalasincronica
                    data['totalplansincronica'] = totalplansincronica
                    data['totalplanasincronica'] = totalplanasincronica
                    data['profesor'] = profesor
                    return render(request, "pro_laboratoriocronograma/detalle_clasesvideo.html", data)
                except Exception as ex:
                    pass

            elif action == 'verasesoramientossee':
                try:
                    data['detalle'] = detalle = AsesoramientoSEE.objects.filter(persona=persona, periodo=periodo, status=True)
                    template = get_template("pro_laboratoriocronograma/modal/detalleasesoramientossee.html")
                    return JsonResponse({"result": True, "data": template.render(data)})
                except Exception as ex:
                    # transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            elif action == 'asesoramientosseehorariodisponible':
                try:
                    data['asesoramientos'] = asesoramientos = AsesoramientoSEE.objects.filter(periodo=periodo, status=True)
                    # data['fecha'] = fecha = request.GET['fecha']
                    fecha_convertir = datetime.strptime(request.GET['fecha'], '%Y-%m-%d')
                    data['fecha'] = fecha = str(fecha_convertir.strftime('%d-%m-%Y'))
                    hor_ini = datetime.strptime(f'{fecha} 08:00:00', '%d-%m-%Y %H:%M:%S')
                    hor_fin = datetime.strptime(f'{fecha} 17:00:00', '%d-%m-%Y %H:%M:%S')
                    fecha_filtro = datetime.strptime(f'{fecha}', '%d-%m-%Y')
                    data['horas'] = []
                    fechaactual = datetime.now()
                    print(hor_ini.time())
                    print(asesoramientos.filter(estado__in=[1, 2], fechaatencion=fecha_filtro, horaatencion=hor_ini.time()).exists())
                    if fecha_filtro.date() >= fechaactual.date():
                        while (hor_ini < hor_fin):
                            if hor_ini.hour != 13 and not asesoramientos.filter(estado__in=[1, 2], fechaatencion=fecha_filtro, horaatencion=hor_ini.time()).exists():
                                if hor_ini.hour > fechaactual.hour or fechaactual.date() != fecha_filtro.date():
                                    data['horas'].append(hor_ini.time().strftime('%H:%M'))
                            hor_ini = hor_ini + timedelta(hours=1)
                        template = get_template("pro_laboratoriocronograma/modal/tabla_horariodisponibles.html")
                        return JsonResponse({"result": True, "data": template.render(data)})
                    else:
                        raise NameError('Debe  ingresar Una fecha actual o Mayor')
                except Exception as ex:
                    # transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error: %s" % ex.__str__()})

            elif action == 'addasesoramientossee':
                try:
                    data['action'] = action
                    data['title'] = u'Adicionar solicitud de  Asesoramiento '
                    data['form'] = AsesoramientoSEEForm()
                    template = get_template("pro_laboratoriocronograma/modal/formasesoramientosee.html")
                    return JsonResponse({"result": True, "data": template.render(data), "title": data['title']})
                except Exception as ex:
                    # transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            elif action == 'editasesoramientossee':
                try:
                    data['action'] = action
                    data['title'] = u'Editar solicitud de  Asesoramiento '
                    data['asesoramiento'] = asesoramiento = AsesoramientoSEE.objects.get(id=request.GET['id'])
                    data['form'] = AsesoramientoSEEForm(model_to_dict(asesoramiento))
                    template = get_template("pro_laboratoriocronograma/modal/formasesoramientosee.html")
                    return JsonResponse({"result": True, "data": template.render(data), "title": data['title']})
                except Exception as ex:
                    # transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            elif action == 'registrarhorario':
                try:
                    data['title'] = u'Planificacion de tutorias de practicas preprofesionales'
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado']]
                    data['sumaactividad'] = 0
                    data['suma'] = 0
                    # periodoacademia=periodo.periodo_academia()
                    if ActividadDetalleDistributivoCarrera.objects.filter(
                            actividaddetalle__criterio__criteriodocenciaperiodo__criterio__id__in=[6, 154],  # id de criterios de practicas 154 es nuevo
                            actividaddetalle__criterio__distributivo__periodo=periodo,
                            actividaddetalle__criterio__distributivo__profesor=profesor,
                            actividaddetalle__criterio__distributivo__status=True, status=True).exists():
                        data['sumaactividad'] = int(ActividadDetalleDistributivoCarrera.objects.filter(
                            actividaddetalle__criterio__criteriodocenciaperiodo__criterio__id__in=[6, 154],
                            actividaddetalle__criterio__distributivo__periodo=periodo,
                            actividaddetalle__criterio__distributivo__status=True, status=True).first().horas)
                    idturnostutoria = []
                    turnosparatutoria = None
                    if HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo).exists():
                        horarios = HorarioTutoriaPacticasPP.objects.filter(status=True, profesor=profesor, periodo=periodo)
                        data['suma'] = int(horarios.aggregate(total=Sum('turno__horas'))['total'])
                        idturnostutoria = horarios.values_list('turno_id').distinct()
                        if periodo.tipo_id in (3, 4) or periodo.es_posgrado():
                            turnosparatutoria = Turno.objects.filter(status=True, sesion_id__in=[19, 15], id__in=idturnostutoria).distinct().order_by('comienza')
                        else:
                            turnosparatutoria = Turno.objects.filter(status=True, sesion_id=15, id__in=idturnostutoria).distinct().order_by('comienza')
                    data['turnos'] = turnosparatutoria
                    data['puede_ver_horario'] = periodo.visible == True and periodo.visiblehorario == True
                    data['puede_registrar'] = False
                    # data['solicitud'] = solicitud = periodo.solicitud_horario_tutoria_docente(profesor)
                    # carrera = profesor.profesordistributivohoras_set.filter(periodo=periodo).first()
                    # data['director'] = CoordinadorCarrera.objects.filter(carrera=carrera.carrera, periodo=periodo, tipo=3).first()
                    if periodo.preinscripcionpracticaspp_set.values('id').filter(status=True).exists():
                        if datetime.now().date() <= periodo.preinscripcionpracticaspp_set.values('fechamaximoagendatutoria').filter(status=True)[0]['fechamaximoagendatutoria']:
                            data['puede_registrar'] = True
                    # #     elif solicitud:
                    # #         if solicitud.fecha and (solicitud.fecha >= datetime.now().date() and solicitud.estadosolicitud == 1):
                    # #             data['puede_registrar'] = True
                    # #         elif solicitud.fecha and (solicitud.fecha <= datetime.now().date() and solicitud.estadosolicitud == 1):
                    # data['puede_registrar'] = True
                    return render(request, "pro_laboratoriocronograma/horarioplanificacionpracticaspp.html", data)
                except Exception as ex:
                    pass

            elif action == 'vertutorias':
                try:
                    id = encrypt(request.GET['id'])
                    data['plantutoria'] = plantutoria = HorarioTutoriaPacticasPP.objects.get(id=id)
                    data['tutoriasagendadas'] = plantutoria.listatutorias()
                    template = get_template("pro_laboratoriocronograma/detalletutorias.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as e:
                    return JsonResponse({"result": "bad", 'mensaje': 'Error al obtener los datos' + str(e)})

            elif action == 'vercumplimiento':
                try:
                    now = datetime.now()
                    data['title'] = u'Cumplimiento'
                    if 'fechaini' in request.GET:
                        fechaini = request.GET['fechaini']
                        fechainisplit = fechaini.split('-')
                        yearini = int(fechainisplit[0])
                        monthini = int(fechainisplit[1])
                        dayini = int(fechainisplit[2])
                        if 'fechames' in request.GET:
                            fechames = request.GET['fechames']
                            fechasplit = fechames.split('-')
                            year = int(fechasplit[0])
                            month = int(fechasplit[1])
                            last_day = int(fechasplit[2])
                    else:
                        fechames = now.date()
                        yearini = now.year
                        year = now.year
                        dayini = 1
                        # month = now.month
                        dia = int(now.day)
                        if dia >= 28:
                            month = now.month
                            monthini = now.month
                        else:
                            if int(now.month) == 1:
                                month = int(now.month)
                                monthini = int(now.month)
                            else:
                                month = int(now.month) - 1
                                monthini = int(now.month) - 1
                        last_day = calendar.monthrange(year, month)[1]

                    calendar.monthrange(year, month)
                    existe = False
                    if HistorialInforme.objects.values('id').filter(informe__distributivo__periodo=periodo, informe__distributivo__profesor=profesor, informe__fechafin__month=month, estado=2, informe__status=True, status=True).exists():
                        existe = True
                    data['existeinforme'] = existe
                    start = date(yearini, monthini, dayini)
                    fini = str(start.day) + '-' + str(start.month) + '-' + str(start.year)
                    end = date(year, month, last_day)
                    ffin = str(end.day) + '-' + str(end.month) + '-' + str(end.year)
                    data['start'] = start
                    data['end'] = end
                    data['fechaconmes'] = fechames
                    data['fechainicial'] = datetime.strptime(fini, '%d-%m-%Y').date()
                    data['fechafinal'] = datetime.strptime(ffin, '%d-%m-%Y').date()
                    data['mesnombre'] = str(nombremes(fecha=datetime.strptime(ffin, '%d-%m-%Y').date()))
                    data['listadomeses'] = MESES_CHOICES
                    data['data'] = eData = profesor.informe_actividades_mensual_docente_v4(periodo, fini, ffin, 'FACULTAD')
                    periodoposgrado = False
                    if periodo.tipo_id in [3, 4]:
                        periodoposgrado = True
                    data['periodoposgrado'] = periodoposgrado
                    data['aplicador'] = aplicador = profesor_aplicador(profesor, periodo, fini, ffin, eData['distributivo'])
                    data['tienehorarioaprobado'] = periodo.claseactividadestado_set.filter(profesor=profesor, estadosolicitud=2, status=True).exists() if not periodoposgrado else True
                    # TODA MODIFICACIÓN DEL INFORME MENSUAL ACTUALIZAR TAMBIEN EN /runback/arreglos/corte_informe_mensual.py
                    # calcularPorcentajeInformeMensual()
                    data['DEBUG'] = DEBUG
                    if profesor.persona.id.__str__() in variable_valor('PROFESOR_HABILITAN_INFORME'):
                        data['dias_generar'] = True
                    else:
                        data['dias_generar'] = int(now.day) <= variable_valor('DIA_LIMITE_INFORME_MENSUAL')

                    if periodo.tipo.id in [3, 4]:
                        return render(request, "pro_laboratoriocronograma/vercumplimientopos.html", data)
                    else:
                        return render(request, "pro_laboratoriocronograma/vercumplimiento.html", data)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return HttpResponseRedirect("/pro_laboratoriocronograma?info=%s" % ex)

            elif action == 'delevidencia':
                try:
                    ev = EvidenciaActividadDetalleDistributivo.objects.get(pk=request.GET.get('id'))
                    ev.delete()
                    return JsonResponse({'result': True})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': ex.__str__()})

            elif action == 'misterminosycondiciones':
                try:
                    data['title'] = u"Mis términos y condiciones"
                    data['terminos'] = terminos = TerminosCondicionesProfesorDistributivo.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, status=True).order_by('id')

                    for t in terminos:
                        if t.aceptado and t.terminos.legalizar and not t.archivo:
                            genera_archivo_terminos_condiciones(request, terminos)

                    data['tiene_token'] = profesor.tienetoken
                    return render(request, "pro_laboratoriocronograma/misterminosycondiciones.html", data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': ex.__str__()})

            elif action == 'add_solicitud':
                try:
                    from inno.forms import SolictudAperturaClaseVirtualForm
                    if SolicitudAperturaClaseVirtual.objects.filter(status=True, profesor=profesor, periodo=periodo, estadosolicitud__in=[1]).exists():
                        raise NameError('Ya cuenta cuenta con una solicitud que aún no ha sido atendida')
                    solactual = SolicitudAperturaClaseVirtual.objects.filter(status=True, profesor=profesor, periodo=periodo, estadosolicitud__in=[2], fechafin__gte=datetime.now().date()).first()
                    if solactual:
                        raise NameError('Ya cuenta cuenta con una solicitud APROBADA hasta el: {}'.format(str(solactual.fechafin.date())))
                    data['title'] = u'Solicitud de clase virtual'
                    form = SolictudAperturaClaseVirtualForm()
                    data['form'] = form
                    template = get_template('pro_laboratoriocronograma/modal/formsolicitud.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'{ex}'})

            elif action == 'aceptarterminos':
                try:
                    term, response = TerminosCondiciones.objects.get(id=request.GET['id']), {}
                    if terms := TerminosCondicionesProfesorDistributivo.objects.filter(distributivo_id=request.GET['id_dist'], terminos=term, terminos__periodo=periodo, status=True).first():
                        terms.aceptado = True
                        terms.fechaaceptacion = datetime.now()
                        terms.save(request, update_fields=['aceptado', 'fechaaceptacion'])
                    else:
                        terms = TerminosCondicionesProfesorDistributivo(distributivo_id=request.GET['id_dist'], terminos=term, aceptado=True, fechaaceptacion=datetime.now())
                        terms.save(request)

                    if term.legalizar:
                        # Generar archivo
                        genera_archivo_terminos_condiciones(request, terms)
                        # ------------------------------------------

                        data['archivo'] = terms.archivo.url
                        data['url_archivo'] = '{}{}'.format(dominio_sistema, terms.archivo.url)
                        data['id_objeto'] = terms.id
                        data['action_firma'] = 'legalizarterminoscondiciones'
                        template = get_template("pro_laboratoriocronograma/modal/firmarinformepppinternadorotativo.html")
                        response = {'data': template.render(data)}

                    return JsonResponse({"result": "ok"} | response)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generarbitacorapdf':
                try:
                    data_extra, valida_estado_2 = {}, True
                    bitacora = BitacoraActividadDocente.objects.filter(id=int(request.GET.get('id', 0)), status=True).first()
                    detallebitacora = DetalleBitacoraDocente.objects.filter(bitacoradocente=bitacora, status=True).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')
                    claseactividad = ClaseActividad.objects.filter(detalledistributivo=bitacora.criterio, detalledistributivo__distributivo__profesor=bitacora.criterio.distributivo.profesor, status=True).values_list('dia', 'turno_id').order_by('inicio', 'dia', 'turno__comienza')
                    dt, end = bitacora.fechaini, bitacora.fechafin
                    result = []
                    while dt <= end:
                        dias_nolaborables = periodo.dias_nolaborables(dt)
                        if not dias_nolaborables:
                            for dclase in claseactividad:
                                if dt.isocalendar()[2] == dclase[0]:
                                    result.append(dt.strftime('%Y-%m-%d'))
                        dt += timedelta(days=1)

                    data_extra['totalhorasplanificadas'] = totalhorasplanificadas = result.__len__()
                    totalhorasregistradas, totalhorasaprobadas, porcentaje_cumplimiento = 0, 0, 0

                    if th := detallebitacora.filter(status=True).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                        totalhorasregistradas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    if th := detallebitacora.filter(estadoaprobacion=2, status=True).aggregate(total=Sum('diferencia'))['total']:
                        horas, minutos = (th.total_seconds() / 3600).__str__().split('.')
                        totalhorasaprobadas = float("%s.%s" % (horas, round(float('0.' + minutos) * 60)))

                    if bitacora.criterio.criteriodocenciaperiodo:
                        if valida_estado_2 := not bitacora.criterio.criteriodocenciaperiodo.criterio.pk == 167:
                            porcentaje_cumplimiento = (100 if totalhorasaprobadas > totalhorasplanificadas else ((totalhorasaprobadas / totalhorasplanificadas) * 100)) if totalhorasplanificadas else 0
                    else:
                        porcentaje_cumplimiento = (100 if totalhorasregistradas > totalhorasplanificadas else ((totalhorasregistradas / totalhorasplanificadas) * 100)) if totalhorasplanificadas else 0

                    data_extra['DEBUG'] = DEBUG
                    data_extra['persona'] = persona
                    data_extra['bitacora'] = bitacora
                    data_extra['valida_estado_2'] = valida_estado_2
                    data_extra['detallebitacora'] = detallebitacora
                    data_extra['fecha_creacion'] = datetime.now().date()
                    data_extra['totalhorasaprobadas'] = totalhorasaprobadas
                    data_extra['totalhorasregistradas'] = totalhorasregistradas
                    data_extra['porcentaje_cumplimiento'] = porcentaje_cumplimiento

                    return conviert_html_to_pdf_name('../inno/templates/pro_laboratoriocronograma/informe_bitacora_actividad_docente.html', data_extra, f"bitacora_{persona.usuario.username}_{bitacora.pk}.pdf")
                except Exception as ex:
                    pass

            elif action == 'update-grupoinvestigacion':
                try:
                    ev = EvidenciaActividadDetalleDistributivo.objects.get(pk=request.GET.get('id'))
                    ev.grupoinvestigacion_id = int(request.GET.get('grupo', None))
                    ev.save()

                    return JsonResponse({'result': True})
                except Exception as ex:
                    pass

            elif action == 'usuariotest':
                try:
                    data['title'] = u'Test - visión de contrastes'
                    filter, url_vars = Q(supervisor=profesor, status=True), '&action=usuariotest'
                    data['test'] = test = Test.objects.filter(status=True).first()
                    data['intentos'] = IntentoUsuario.objects.filter(status=True, test=test)
                    data['url_vars'] = url_vars
                    return render(request, "pro_laboratoriocronograma/test/usuariotest.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargarpreguntatest':
                try:
                    data['hoy'] = hoy = datetime.now().date()
                    data['test'] = test = Test.objects.filter(status=True).first()
                    nuevointento = True if int(request.GET.get('ext', 0)) == 1 else False
                    intento_test = IntentoUsuario.objects.filter(status=True, usuario=profesor, test=test).order_by('-numero')
                    if not nuevointento and intento_test:
                        if ultimo_intento := intento_test.filter(finalizo=False): intento_test = ultimo_intento.first()
                        else: intento_test = intento_test.first()
                    else:
                        numerointento = len(intento_test)+1
                        intento_test = IntentoUsuario(usuario=profesor, test=test, numero=numerointento, fecha=hoy)
                        intento_test.save()
                    data['intento_test'] = intento_test
                    data['usuario_respuestas'] = usuariorespuestas = UsuarioRespuesta.objects.filter(detalletest__test=test, intento=intento_test, status=True)
                    preguntasprofesor = usuariorespuestas.values_list('detalletest_id', flat=True)
                    data['pregunta'] = preguntastest = test.detalletest_set.filter(status=True).order_by('orden').exclude(pk__in=preguntasprofesor).first()
                    data['fechaactual'] = hoy.strftime('%d-%m-%Y')
                    data['valortotal'] = round(usuariorespuestas.filter(correcto=True).count() * 0.15, 2)
                    template = get_template("pro_laboratoriocronograma/test/detallepregunta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    pass

            elif action == 'finalizartestusuario':
                try:
                    idintento = int(request.GET.get('intento', 0)) if int(request.GET.get('intento', 0)) > 0 else None
                    if not idintento: raise NameError('Problemas al obtener los datos, intente nuevamente más tarde')
                    version = 5
                    data['intento'] = eIntento = IntentoUsuario.objects.get(status=True, pk=idintento)
                    usuariorespuestas = UsuarioRespuesta.objects.filter(detalletest__test=eIntento.test, intento=eIntento, status=True)
                    valortotaltest = usuariorespuestas.filter(correcto=True).count() * 0.15
                    if valortotaltest > 2:
                        version = 10
                    return JsonResponse({"result": "ok", 'version': version})
                except Exception as ex:
                    return JsonResponse({'result': "bad", 'mensaje': f'{ex}'})

            elif action == 'testnavegacion':
                try:
                    data['title'] = 'Test de navegación'
                    if 'idseguimiento' in request.GET:
                        seguimiento = SeguimientoDocente.objects.filter(status=True, id=request.GET['idseguimiento']).first()
                    else:
                        seguimiento = SeguimientoDocente.objects.filter(status=True,estado_intento=0, periodo=periodo, profesor=profesor, fechainteraccion=datetime.now().date()).first()
                    if not seguimiento:
                        seguimiento = SeguimientoDocente(periodo=periodo, profesor=profesor, fechainteraccion=datetime.now().date())
                        seguimiento.save(request)
                        contador = 1
                        for inventario in LaboratorioOpcionSistema.objects.filter(activo=True):
                            detalle = DetalleSeguimientoDocente(seguimiento=seguimiento, inventario=inventario, orden=contador)
                            detalle.save(request)
                            contador +=1
                    # LaboratorioOpcionSistema.objects.get(pk=request.POST['id'])
                    data['detalle'] = detalle = seguimiento.detalle().first()
                    data['es_ultimo'] = detalle.id == seguimiento.detalle().last().id
                    data['idseguimiento'] = seguimiento.id
                    return render(request, "pro_laboratoriocronograma/testnavegacion.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)

            return HttpResponseRedirect(request.path)
        else:
            try:
                from laboratorio.models import ResultadoPerfilDocente
                resultperfil = ResultadoPerfilDocente.objects.filter(status=True, seguimiento__profesor=profesor, testcontraste__usuario=profesor, perfilasignado__gt=0, perfilseleccionado__gt=0).first()
                if not resultperfil:
                    data['title'] = u'Test - visión de contrastes'
                    filter, url_vars = Q(supervisor=profesor, status=True), '&action=usuariotest'
                    data['test'] = test = Test.objects.filter(status=True).first()
                    data['intentos'] = IntentoUsuario.objects.filter(status=True, test=test)
                    data['url_vars'] = url_vars
                    return render(request, "pro_laboratoriocronograma/test/usuariotest.html", data)
                from pdip.models import ContratoDip
                data['title'] = u'Cronograma de asignaturas y actividades del profesor'
                grado_virtual = False
                grado_presencial = False
                presencial_admision = False
                virtual_admision = False
                tipo_autor = False
                data['periodo'] = periodo
                data['profesor'] = profesor
                periodoposgrado = False
                if periodo.tipo_id in [3, 4]:
                    periodoposgrado = True
                data['periodoposgrado'] = periodoposgrado
                if not periodo.visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                periodo_ids_relacionado = []
                periodo_ids_relacionado.append(periodo.id)
                if periodo.periodo_academia():
                    if periodo.periodo_academia().periodos_relacionados:
                        periodo_ids_relacionado = periodo.periodo_academia().periodos_relacionados.split(',')

                # data['materias'] = Materia.objects.filter(profesormateria__profesor=profesor, profesormateria__principal=True, nivel__periodo=periodo, nivel__periodo__visible=True).distinct().order_by('asignatura')
                data['materias'] = Materia.objects.filter(status=True, profesormateria__profesor=profesor, nivel__periodo__in=periodo_ids_relacionado, nivel__periodo__visible=True).distinct().order_by('asignatura')
                data['profesormaterias'] = profesormateria = ProfesorMateria.objects.filter(profesor=profesor, materia__nivel__periodo__in=periodo_ids_relacionado, materia__nivel__periodo__visible=True, status=True, activo=True).distinct().order_by('materia__asignatura')
                if periodo.ocultarmateria:
                    materiasprofesor = False
                else:
                    materiasprofesor = Materia.objects.filter(nivel__visibledistributivomateria=True, profesormateria__profesor=profesor, nivel__periodo__in=periodo_ids_relacionado, nivel__periodo__visible=True, profesormateria__status=True, status=True, profesormateria__activo=True).distinct().order_by('id', 'asignatura').distinct()
                data['materiasprofesor'] = materiasprofesor
                ver_reporte = False
                ver_reportetutores = False
                if profesormateria.filter(tipoprofesor_id__in=[1, 11, 12, 14]):
                    ver_reporte = True
                if profesormateria.filter(tipoprofesor_id__in=[8]):
                    ver_reportetutores = True
                if profesor.profesordistributivohoras_set.filter(periodo__in=periodo_ids_relacionado, verinforme=True, status=True):
                    ver_reporte = True
                data['ver_reporte'] = ver_reporte
                data['ver_reportetutores'] = ver_reportetutores
                for x in profesormateria:
                    if x.materia.coordinacion().id != 9 and x.materia.nivel.modalidad.id == 3:
                        grado_virtual = True
                    if x.materia.coordinacion().id == 9 and x.materia.nivel.modalidad.id != 3:
                        presencial_admision = True
                    if x.materia.coordinacion().id == 9 and x.materia.nivel.modalidad.id == 3:
                        virtual_admision = True
                    if x.materia.coordinacion().id != 9 and x.materia.nivel.modalidad.id != 3:
                        grado_presencial = True
                    if x.tipoprofesor_id == 9:
                        tipo_autor = True

                data['tipo_autor'] = tipo_autor
                data['grado_virtual'] = grado_virtual
                data['grado_presencial'] = grado_presencial
                data['presencial_admision'] = presencial_admision
                data['virtual_admision'] = virtual_admision
                data['actividades'] = actividad = PaeActividadesPeriodoAreas.objects.filter((Q(paefechaactividad__tutor=profesor) | Q(tutorprincipal=profesor)), periodoarea__periodo=periodo, status=True).order_by('nombre').distinct()
                for activi in actividad:
                    if activi.tutorprincipal == profesor:
                        data['sicalifica'] = True
                        data['idactividad'] = activi.id
                # data['materiascursos'] = MateriaCursoEscuelaComplementaria.objects.filter(profesor=profesor, fecha_fin__gte=(datetime.now().date() - timedelta(days=15))).distinct().order_by('-fecha_inicio')
                fechacursosanoant = datetime.now().year - 1
                data['materiascursos'] = MateriaCursoEscuelaComplementaria.objects.filter((Q(fecha_fin__year__gte=fechacursosanoant) | Q(fecha_fin__year__lte=(datetime.now().year))) & Q(profesor=profesor)).distinct().order_by('-fecha_inicio')
                if periodo.id < 112:
                    materiaspracticas = Materia.objects.filter((Q(practicas=True) | Q(asignaturamalla__practicas=True)), profesormateria__tipoprofesor=TIPO_DOCENTE_PRACTICA, profesormateria__profesor=profesor, profesormateria__activo=True, nivel__periodo=periodo, status=True).distinct()
                else:
                    materiaspracticas = None
                data['materiaspracticas'] = materiaspracticas
                data['proyectos'] = ProyectosVinculacion.objects.filter(profesorproyectovinculacion__profesor=profesor, fin__gte=(datetime.now().date() - timedelta(days=15)), cerrado=False).distinct().order_by('-inicio')
                data['practicas'] = PracticaPreProfesional.objects.filter(materia__profesormateria__profesor=profesor, materia__nivel__periodo=periodo).distinct().order_by('-fecha')
                data['matriculacion_libre'] = MATRICULACION_LIBRE
                data['reporte_0'] = obtener_reporte('mate_cronogramaprofesor')
                data['reporte_1'] = obtener_reporte('listado_estudiantes_inscritos_vcc')
                data['reporte_2'] = obtener_reporte('acta_vcc')
                data['reporte_3'] = obtener_reporte("lista_alumnos_inscritos_actividad")
                data['reporte_4'] = obtener_reporte("control_academico")
                data['reporte_5'] = obtener_reporte("lista_alumnos_inscritos_cursos")
                data['reporte_6'] = obtener_reporte("listado_asistencia_dias")
                data['reporte_7'] = obtener_reporte("lista_alumnos_matriculados_materia")
                data['reporte_9'] = obtener_reporte("clases_consolidado")
                data['reporte_10'] = obtener_reporte('acta_calificacion_curso')
                data['fechaactual'] = fecha = datetime.now().date()
                if periodo.preferencia_inicio and periodo.preferencia_final:
                    if (fecha >= periodo.preferencia_inicio and fecha <= periodo.preferencia_final):
                        data['accesopreferencia'] = True
                    else:
                        data['accesopreferencia'] = False
                else:
                    data['accesopreferencia'] = False
                if periodo.preferencia_actividadinicio and periodo.preferencia_actividadfinal:
                    if (fecha >= periodo.preferencia_actividadinicio and fecha <= periodo.preferencia_actividadfinal):
                        data['accesopreferenciaactividad'] = True
                    else:
                        data['accesopreferenciaactividad'] = False
                else:
                    data['accesopreferenciaactividad'] = False
                if PermisoPeriodo.objects.filter(periodo=periodo).exists():
                    data['permiso'] = True
                else:
                    data['permiso'] = False
                data['asignaturaspreferencias'] = AsignaturaMallaPreferencia.objects.filter(profesor=profesor, periodo=periodo, status=True)
                data['practicas_preprofesionales_activas'] = PRACTICAS_PREPROFESIONALES_ACTIVAS
                data['distributivo_horas'] = distributivo_horas = profesor.distributivohoraseval(periodo)
                data['es_admision'] = profesor.distributivohorasesadmision(periodo)
                data['es_facultad'] = profesor.distributivohorasesfacultad(periodo)
                data['supervisorpracticas'] = PracticasPreprofesionalesInscripcion.objects.values_list('id', flat=True).filter(Q(estadosolicitud=1) | Q(estadosolicitud=2), status=True, supervisor=profesor, culminada=False).distinct().count()
                data['supervisorayudantia'] = InscripcionCatedra.objects.values_list('id', flat=True).filter(status=True, supervisor=profesor, periodocatedra__periodolectivo=periodo).distinct().count()
                data['tutoriaspracticas'] = PracticasPreprofesionalesInscripcion.objects.filter(status=True, tutorunemi=profesor, culminada=False).distinct().exclude(estadosolicitud=3).count()
                data['CRITERIO_IMPARTICION_CLASE_ID'] = variable_valor('CRITERIO_IMPARTICION_CLASE_ID')
                data['criterio_docencia_subir_cronograma'] = variable_valor('CRITERIO_DOCENCIA_SUBIR_CRONOGRAMA')
                data['criterio_investigacion_subir_cronograma'] = CriterioInvestigacion.objects.values_list('id', flat=True).filter(status=True)
                data['criterio_gestion_subir_cronograma'] = variable_valor('CRITERIO_GESTION_SUBIR_CRONOGRAMA')
                # data['cronogramacapacitacionactivo'] = CronogramaCapacitacionDocente.objects.filter(status=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).exists()
                data['profesor'] = Profesor.objects.get(pk=profesor.id)
                data['actividadesdocente'] = actividadesdocente = CriterioDocenciaPeriodo.objects.filter(status=True, detalledistributivo__distributivo__profesor=profesor, detalledistributivo__status=True, detalledistributivo__distributivo__periodo=periodo, actividaddocenciarecursoaprendizaje__isnull=False).distinct()
                data['actividadesgestion'] = actividadesgestion = CriterioGestionPeriodo.objects.filter(status=True, detalledistributivo__distributivo__profesor=profesor, detalledistributivo__status=True, detalledistributivo__distributivo__periodo=periodo, actividadgestionrecursoaprendizaje__isnull=False).distinct()
                data['asignaturas_presencial'] = Asignatura.objects.filter(asignaturamalla__materia__nivel__periodo=periodo, asignaturamalla__materia__nivel__modalidad_id__in=[1, 2], asignaturamalla__materia__profesormateria__profesor=profesor).distinct()
                data['asignaturas_enlinea'] = Asignatura.objects.filter(asignaturamalla__materia__nivel__periodo=periodo, asignaturamalla__materia__nivel__modalidad_id__in=[3], asignaturamalla__materia__profesormateria__profesor=profesor).distinct()
                data['tiposprofesorpresencial'] = TipoProfesor.objects.filter(profesormateria__materia__nivel__modalidad_id__in=[1, 2], profesormateria__profesor=profesor, status=True, profesormateria__status=True, profesormateria__materia__nivel__periodo=periodo).distinct()
                data['tiposprofesorlinea'] = TipoProfesor.objects.filter(profesormateria__materia__nivel__modalidad_id__in=[3], profesormateria__profesor=profesor, status=True, profesormateria__status=True, profesormateria__materia__nivel__periodo=periodo).distinct()
                data['modalidadpresencial'] = modalidadpresencial = [1, 2]
                data['nopedirevidencia'] = [37, 9, 106, 30, 1, 4, 15, 16, 21, 4, 3, 99, 105, 61, 7, 53, 81]
                data['modalidadlinea'] = [3]
                tienehorarioaprobado = False
                if periodo.claseactividadestado_set.filter(profesor=profesor, estadosolicitud=2, status=True):
                    tienehorarioaprobado = True
                data['tienehorarioaprobado'] = tienehorarioaprobado
                data['reporte_11'] = obtener_reporte('evidencias_distributivo')
                data['tienelogs'] = periodo.logdeberes_set.filter(status=True).exists()
                data['tutoriasdehoy'] = AgendaPracticasTutoria.objects.filter(docente=perfilprincipal.profesor, status=True, fecha=datetime.now().date(), estados_agenda=0).count()
                data['tutpendientesfin'] = AgendaPracticasTutoria.objects.filter(docente=perfilprincipal.profesor, status=True, fecha__lt=datetime.now().date(), estados_agenda=0).count()
                data['es_tutor'] = profesor.profesormateria_set.values('id').filter(materia__nivel__periodo=periodo, profesor_id=profesor.id, tipoprofesor_id__in=[8], tipoprofesor__status=True, materia__status=True, materia__nivel__status=True, status=True).exists()
                data['es_coordinador'] = ContratoDip.objects.values('id').filter(Q(persona=persona, status=True) & Q(Q(cargo__nombre__icontains="COORDINADORA DEL PROGRAMA") | Q(cargo__nombre__icontains="COORDINADOR DEL PROGRAMA") | Q(cargo__nombre__icontains="COORDINADOR/A DEL PROGRAMA"))).exists()
                data['hoy'] = now = datetime.now().date()
                data['historialcerti_'] = historialcerti_ = HistorialInformeMensual.objects.values('finicioreporte', 'total_porcentaje').filter(distributivo__profesor=profesor, distributivo__periodo=periodo, status=True, fecha_creacion__month=now.month, fecha_creacion__year=now.year, fecha_creacion__day=now.day).order_by('-id').first()
                data['profesor_presencial'] = profesor_presencial = any(elemento in profesor.profesormateria_set.filter(status=True, materia__nivel__periodo=periodo).values_list('materia__asignaturamalla__malla__carrera__modalidad', flat=True).distinct() for elemento in modalidadpresencial)
                if profesor_presencial:
                    data['solictudes_clase_virtual'] = profesor.solicitudaperturaclasevirtual_set.filter(periodo=periodo, status=True)
                if distributivo := ProfesorDistributivoHoras.objects.filter(profesor__persona=persona, periodo=periodo, activo=True, status=True).first():
                    data['distributivo'] = distributivo
                    terminos_aceptados = TerminosCondicionesProfesorDistributivo.objects.filter(distributivo=distributivo, aceptado=True, terminos__status=True, status=True).values_list('terminos__id', flat=True)
                    data['terminoscondicionesprofesor'] = terminos_condiciones = TerminosCondiciones.objects.filter(periodo=periodo, visible=True, status=True).exclude(id__in=terminos_aceptados).first()
                    data['notificar_terminos_condiciones'] = terminos_aceptados.filter(terminos__legalizar=True, legalizado=False).exists() and not terminos_condiciones
                    aprobar_bitacora_termino_plazo(request=request, periodo=periodo, profesor=profesor)
                _perfil = resultperfil.perfilseleccionado
                if _perfil == 1:
                    return render(request, "pro_laboratoriocronograma/view.html", data)
                elif _perfil == 2:
                    return render(request, "pro_laboratoriocronograma/view2.html", data)
                elif _perfil == 3:
                    return render(request, "pro_laboratoriocronograma/view-dark.html", data)
            except Exception as ex:
                print('Error on pro_laboratoriocronograma line {} {}'.format(sys.exc_info()[-1].tb_lineno, ex.__str__()))


def migrar_evidencia_integrantes_proyecto_investigacion(**kwargs):
    try:
        from inno.models import Criterio, SubactividadDocentePeriodo
        CRITERIO_ACTIVIDAD_MACRO = 68
        evidencia, request = kwargs.pop('evidencia'), kwargs.pop('request')
        periodo = evidencia.criterio.distributivo.periodo
        persona = evidencia.criterio.distributivo.profesor.persona
        funcionacriterio = lambda x: {1: 55, 2: 56, 3: 57}[x] if x in (1, 2, 3) else None
        funcion = 0
        if evidencia.subactividad.subactividaddocenteperiodo.criterio.pk == CRITERIO_CODIRECTOR_PROYECTO_INV:
            funcion = 2
        if evidencia.subactividad.subactividaddocenteperiodo.criterio.pk == CRITERIO_DIRECTOR_PROYECTO:
            funcion = 1
        if inv := evidencia.criterio.criterioinvestigacionperiodo:
            can_upload_evidence, exclude_ = False, [1]
            if lider := ProyectoInvestigacionIntegrante.objects.filter(tiporegistro__in=[1, 3, 4], persona=persona, proyecto__estado_id=37, funcion=funcion, status=True).exclude(proyecto__cerrado=True).first():
                proyecto = lider.proyecto
                if not inv.es_actividadmacro:
                    if inv.criterio.id == 56:
                        if not DetalleDistributivo.objects.values('id').filter(distributivo__activo=True, criterioinvestigacionperiodo__criterio__id=55, distributivo__profesor__persona=lider.persona, distributivo__periodo=evidencia.criterio.distributivo.periodo, status=True).exists():
                            can_upload_evidence, exclude_ = True, [1, 2]
                    if inv.criterio.id == 55 or can_upload_evidence:
                        for integrante in lider.proyecto.integrantes_proyecto().exclude(funcion__in=exclude_):
                            _evidencia = None
                            integrante_profesor = integrante.profesor if integrante.profesor else Profesor.objects.filter(persona=integrante.persona).first()
                            distributivo = DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=funcionacriterio(integrante.funcion), distributivo__profesor=integrante_profesor, distributivo__periodo=evidencia.criterio.distributivo.periodo, status=True).first()
                            if distributivo:
                                _evidencia = EvidenciaActividadDetalleDistributivo.objects.filter(criterio=distributivo, hasta__month=evidencia.hasta.month, hasta__year=evidencia.hasta.year).first()
                                if _evidencia:
                                    _evidencia.actividaddetalledistributivo = evidencia.actividaddetalledistributivo
                                    _evidencia.desde = evidencia.desde
                                    _evidencia.hasta = evidencia.hasta
                                    _evidencia.actividad = evidencia.actividad
                                    _evidencia.aprobado = evidencia.aprobado
                                    _evidencia.archivo = evidencia.archivo
                                    _evidencia.usuarioaprobado = evidencia.usuarioaprobado
                                    _evidencia.fechaaprobado = evidencia.fechaaprobado
                                    _evidencia.estadoaprobacion = evidencia.estadoaprobacion
                                    _evidencia.archivofirmado = evidencia.archivofirmado
                                else:
                                    _dict = EvidenciaActividadDetalleDistributivo.objects.filter(pk=evidencia.pk).values()[0]
                                    _dict.pop('id')
                                    _evidencia = EvidenciaActividadDetalleDistributivo(**_dict)
                                    _evidencia.criterio = distributivo

                                _evidencia.save(request)

                                _evidencia.anexoevidenciaactividad_set.filter(status=True).delete()
                                for anexo in evidencia.anexoevidenciaactividad_set.filter(status=True):
                                    a = AnexoEvidenciaActividad(evidencia=_evidencia, observacion=anexo.observacion, archivo=anexo.archivo)
                                    a.save(request)

                                _evidencia.evidenciaactividadaudi_set.filter(status=True).delete()
                                for anexo in evidencia.evidenciaactividadaudi_set.filter(status=True):
                                    a = EvidenciaActividadAudi(evidencia=_evidencia, archivo=anexo.archivo)
                                    a.save(request)

                                _evidencia.historialaprobacionevidenciaactividad_set.filter(status=True).delete()
                                for anexo in evidencia.historialaprobacionevidenciaactividad_set.filter(status=True):
                                    a = HistorialAprobacionEvidenciaActividad(evidencia=_evidencia, aprobacionpersona=anexo.aprobacionpersona, observacion=anexo.observacion, fechaaprobacion=anexo.fechaaprobacion, estadoaprobacion=anexo.estadoaprobacion)
                                    a.save(request)

                            if not distributivo and not _evidencia:
                                criterio = CriterioInvestigacionPeriodo.objects.filter(criterio__id=funcionacriterio(integrante.funcion)).first()
                                gnro = "a" if integrante.persona.es_mujer() else "o"
                                msj = f'Estimad{gnro} {integrante.persona.__str__().lower().title()}, usted se encuentra asociad{gnro} al proyecto de investigación "{proyecto.titulo}" como <b>{integrante.get_funcion_display().__str__().lower().title()}</b> pero no cuenta con el criterio <b>{criterio.criterio.nombre.__str__().lower().title() if criterio else funcionacriterio(integrante.funcion)}</b> en su distributivo de horas.<br><br> Por favor comuníquese con su director de carrera.'
                                notificacion("Problemas en el distributivo del docente", msj, integrante.persona, None, 'notificacion', funcionacriterio(integrante.funcion), 1, 'sga', CriterioInvestigacionPeriodo, request)
                else:
                    # Cambios para actividad macro
                    lider_proyecto = lider.proyecto.integrantes_proyecto().filter(funcion=1).first()
                    if not SubactividadDetalleDistributivo.objects.filter(subactividaddocenteperiodo__criterio=CRITERIO_DIRECTOR_PROYECTO, actividaddetalledistributivo__criterio__distributivo__profesor__persona=lider_proyecto.persona, actividaddetalledistributivo__criterio__distributivo__periodo=periodo, status=True).exists():
                        can_upload_evidence, exclude_ = True, [1, 2]

                    if (evidencia.subactividad and evidencia.subactividad.subactividaddocenteperiodo.criterio.pk == CRITERIO_DIRECTOR_PROYECTO) or can_upload_evidence:
                        if not MigracionEvidenciaActividad.objects.values('id').filter(evidencia=evidencia, evidenciabase=evidencia.pk, proyectoinvestigacion=lider.proyecto, status=True).exists():
                            m = MigracionEvidenciaActividad(evidencia=evidencia, proyectoinvestigacion=lider.proyecto)
                            m.save(request)
                        for integrante in lider.proyecto.integrantes_proyecto().exclude(funcion__in=exclude_):
                            _evidencia, subactividad = None, None
                            integrante_profesor = integrante.profesor if integrante.profesor else Profesor.objects.filter(persona=integrante.persona).first()
                            if distributivo := DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=CRITERIO_ACTIVIDAD_MACRO, distributivo__profesor=integrante_profesor, distributivo__periodo=evidencia.criterio.distributivo.periodo, status=True).first():
                                CRITERIO = CRITERIO_ASOCIADO_PROYECTO
                                if integrante.funcion == 2:
                                    CRITERIO = CRITERIO_CODIRECTOR_PROYECTO_INV
                                if subactividad := SubactividadDetalleDistributivo.objects.filter(actividaddetalledistributivo__criterio=distributivo, subactividaddocenteperiodo__criterio=CRITERIO, subactividaddocenteperiodo__actividad__status=True, subactividaddocenteperiodo__actividad__criterio__status=True, subactividaddocenteperiodo__status=True, subactividaddocenteperiodo__criterio__status=True, actividaddetalledistributivo__status=True, status=True).first():
                                    if migracion := MigracionEvidenciaActividad.objects.filter(evidencia__subactividad=subactividad, evidenciabase=evidencia.pk, status=True).first():
                                        _evidencia = migracion.evidencia
                                        _evidencia.actividaddetalledistributivo = evidencia.actividaddetalledistributivo
                                        _evidencia.desde = evidencia.desde
                                        _evidencia.hasta = evidencia.hasta
                                        _evidencia.actividad = evidencia.actividad
                                        _evidencia.aprobado = evidencia.aprobado
                                        _evidencia.archivo = evidencia.archivo
                                        _evidencia.usuarioaprobado = evidencia.usuarioaprobado
                                        _evidencia.fechaaprobado = evidencia.fechaaprobado
                                        _evidencia.estadoaprobacion = evidencia.estadoaprobacion
                                        _evidencia.archivofirmado = evidencia.archivofirmado
                                        _evidencia.save(request)
                                    else:
                                        _dict = EvidenciaActividadDetalleDistributivo.objects.filter(pk=evidencia.pk).values()[0]
                                        _dict.pop('id')
                                        _evidencia = EvidenciaActividadDetalleDistributivo(**_dict)
                                        _evidencia.criterio = distributivo
                                        _evidencia.subactividad = subactividad
                                        _evidencia.save(request)
                                        m = MigracionEvidenciaActividad(evidencia=_evidencia, evidenciabase=evidencia, proyectoinvestigacion=lider.proyecto)
                                        m.save(request)
                                    _evidencia.anexoevidenciaactividad_set.filter(status=True).delete()
                                    for anexo in evidencia.anexoevidenciaactividad_set.filter(status=True):
                                        a = AnexoEvidenciaActividad(evidencia=_evidencia, observacion=anexo.observacion, archivo=anexo.archivo)
                                        a.save(request)
                                    _evidencia.evidenciaactividadaudi_set.filter(status=True).delete()
                                    for anexo in evidencia.evidenciaactividadaudi_set.filter(status=True):
                                        a = EvidenciaActividadAudi(evidencia=_evidencia, archivo=anexo.archivo)
                                        a.save(request)
                                    _evidencia.historialaprobacionevidenciaactividad_set.filter(status=True).delete()
                                    for anexo in evidencia.historialaprobacionevidenciaactividad_set.filter(status=True):
                                        a = HistorialAprobacionEvidenciaActividad(evidencia=_evidencia, aprobacionpersona=anexo.aprobacionpersona, observacion=anexo.observacion, fechaaprobacion=anexo.fechaaprobacion, estadoaprobacion=anexo.estadoaprobacion)
                                        a.save(request)
                            if (not distributivo or not subactividad) and not _evidencia:
                                subactividad = Criterio.objects.get(id=CRITERIO_ASOCIADO_PROYECTO)
                                g = "a" if integrante.persona.es_mujer() else "o"
                                msj = f'Estimad{g} {integrante.persona}, usted se encuentra asociad{g} al proyecto de investigación "{lider.proyecto.titulo}" como <b>{integrante.get_funcion_display()}</b> pero no cuenta con el criterio <b>{subactividad}</b> en su distributivo.<br><br> Por favor comuníquese con su director de carrera.'
                                notificacion("Problemas en el distributivo del docente", msj, integrante.persona, None, 'notificacion', funcionacriterio(integrante.funcion), 1, 'sga', CriterioInvestigacion, request)
    except Exception as ex:
        raise NameError(ex.__str__())


def generar_informe_practicas_preprofesionales(**kwargs):
    try:
        from sagest.models import PersonaDepartamentoFirmas, AnioEjercicio
        from inno.models import SecuenciaInformeMensualActividades, FirmaInformeMensualActividades, InsumoInformeInternadoRotativo
        from sga.funciones import null_to_decimal

        request = kwargs.get('request', None)

        _var = lambda x: request.session.get(x, None) if not x in kwargs else kwargs.get(x, None)
        _get_num_pag = lambda url: fitz.open(os.path.join(SITE_STORAGE, 'media', "%s" % url)).page_count

        data = {}
        criteriodocencia = 167  # Tutor ppp (internado rotativo)
        evidencia = _var('evidencia')
        configuracion = _var('configuracion')
        persona = _var('persona')
        pprincipal = _var('perfilprincipal')
        periodo = _var('periodo')
        profesor = pprincipal.profesor
        hoy, abreviaturanombre = datetime.now(), ''
        informeppp = InformeMensualDocentesPPP.objects.filter(persona=profesor, mes=configuracion.mes, anio=configuracion.anio, status=True).first()
        if not configuracion: configuracion = ConfiguracionInformePracticasPreprofesionales.objects.filter(persona=profesor, anio=hoy.year, mes=hoy.month, status=True).first()
        aModel = AnioEjercicio.objects.filter(anioejercicio=configuracion.anio, status=True).first()
        anioejercicio = AnioEjercicio.objects.create(anioejercicio=configuracion.anio) if not aModel else aModel
        secuencia = null_to_decimal(InformeMensualDocentesPPP.objects.filter(persona=profesor, status=True, secuencia__status=True, secuencia__anioejercicio=anioejercicio, secuencia__tipo=1).aggregate(valor=Max('secuencia__secuencia'))['valor'])
        numeracion = '%03d' % ((1 + secuencia) if not informeppp else informeppp.secuencia.secuencia)

        for c in persona.nombre_completo().split(' '): abreviaturanombre += c[0] if c.__len__() else ''
        codigo = f"ITI-FACS-CPPP-{abreviaturanombre}-{anioejercicio}-SGA{numeracion}"
        filename = f"/{codigo.replace('-', '_')}.pdf"
        filepath = u"infomensualppp/%s" % hoy.year
        folder_pdf = os.path.join(SITE_STORAGE, 'media', 'infomensualppp', '')

        os.makedirs(folder_pdf, exist_ok=True)
        os.makedirs(os.path.join(folder_pdf, hoy.year.__str__(), ''), exist_ok=True)

        bitacora = BitacoraActividadDocente.objects.filter(profesor=profesor, criterio=evidencia.criterio, status=True).values_list('id', flat=True)
        detallebitacora = DetalleBitacoraDocente.objects.filter(bitacoradocente__id__in=bitacora, fecha__year=configuracion.anio, fecha__month=configuracion.mes, status=True).annotate(diferencia=ExpressionWrapper(F('horafin') - F('horainicio'), output_field=TimeField())).order_by('fecha', 'horainicio', 'horafin')
        detalleanexos = AnexoEvidenciaActividad.objects.filter(evidencia=evidencia, status=True)
        insumo = InsumoInformeInternadoRotativo.objects.filter(status=True, activo=True, informe=1).first()
        data['hoy'] = hoy
        data['fecha_creacion'] = datetime(hoy.year, configuracion.mes, calendar.monthrange(hoy.year, configuracion.mes)[1])
        data['pagesize'] = 'A4'
        data['codigo'] = codigo
        data['persona'] = persona
        data['configuracion'] = configuracion
        data['firmas'] = insumo.get_firmas()
        data['para'] = insumo.get_firmas().filter(responsabilidad=1).first()
        data['marcojuridico'] = insumo
        data['detallebitacora'] = detallebitacora
        anexos = [{'archivo': x.observacion, 'url': x.archivo.url, 'fecha_creacion': x.fecha_creacion, 'numpag': _get_num_pag(x.archivo)} for x in detalleanexos if x.archivo]
        data['anexos'] = anexos
        data['detalledistributivo'] = evidencia.criterio
        if newfile := convert_html_to_pdf('../inno/templates/pro_laboratoriocronograma/informe_mensual_practicas_preprofesionales_salud.html', data, filename, os.path.join(os.path.join(SITE_STORAGE, 'media', filepath, ''))):
            file = filepath + filename
            if not informeppp:
                secuencia = SecuenciaInformeMensualActividades(tipo=1, secuencia=numeracion, anioejercicio=anioejercicio)
                secuencia.save()
                informeppp = InformeMensualDocentesPPP(persona=profesor, mes=configuracion.mes, anio=configuracion.anio, fechageneracion=hoy, archivodescargar=file, secuencia=secuencia, configuracion=configuracion)
            else:
                informeppp.fechageneracion = hoy
                informeppp.archivodescargar = file

            informeppp.save(request)
            configuracion.insumo = insumo
            configuracion.save(request)

        evidencia.archivo.save(informeppp.archivodescargar.name.split('/')[-1], ContentFile(informeppp.archivodescargar.read()), save=True)
        evidencia.informe = informeppp
        evidencia.save(request)
        return True
    except Exception as ex:
        if not kwargs.pop('edit', None):
            evidencia.delete()
        raise NameError(ex.__str__() + f' linea {sys.exc_info()[-1].tb_lineno}')


def migrar_evidencia_integrante_grupo_investigacion(**kwargs):
    CRITERIO_INTEGRANTE_DIRECTOR_GRUPO_INVESTIGACION = 58
    CRITERIO_ACTIVIDAD_MACRO = 68
    evidencia = kwargs.pop('evidencia')
    if inv := evidencia.criterio.criterioinvestigacionperiodo:
        request, detalledistributivo = kwargs.pop('request'), evidencia.criterio
        periodo = detalledistributivo.distributivo.periodo
        persona = detalledistributivo.distributivo.profesor.persona
        if inv.criterio.pk == CRITERIO_INTEGRANTE_DIRECTOR_GRUPO_INVESTIGACION:
            try:
                if director := GrupoInvestigacionIntegrante.objects.filter(persona=persona, grupo__vigente=True, grupo__status=True, funcion=1, status=True).first():
                    grupo = director.grupo
                    evidencia.grupoinvestigacion = grupo
                    evidencia.save(request)

                    for integrante in grupo.grupoinvestigacionintegrante_set.filter(status=True).exclude(funcion=1):
                        if distributivo := DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=CRITERIO_INTEGRANTE_DIRECTOR_GRUPO_INVESTIGACION, distributivo__profesor__persona=integrante.persona, distributivo__periodo=detalledistributivo.distributivo.periodo, distributivo__activo=True, status=True).first():
                            if _evidencia := grupo.evidenciaactividaddetalledistributivo_set.filter(grupoinvestigacion=grupo, criterio=distributivo, hasta__month=evidencia.hasta.month, hasta__year=evidencia.hasta.year, status=True).first():
                                _evidencia.actividaddetalledistributivo = evidencia.actividaddetalledistributivo
                                _evidencia.desde = evidencia.desde
                                _evidencia.hasta = evidencia.hasta
                                _evidencia.actividad = evidencia.actividad
                                _evidencia.aprobado = evidencia.aprobado
                                _evidencia.archivo = evidencia.archivo
                                _evidencia.usuarioaprobado = evidencia.usuarioaprobado
                                _evidencia.fechaaprobado = evidencia.fechaaprobado
                                _evidencia.estadoaprobacion = evidencia.estadoaprobacion
                                _evidencia.archivofirmado = evidencia.archivofirmado
                            else:
                                _dict = EvidenciaActividadDetalleDistributivo.objects.filter(pk=evidencia.pk).values()[0]
                                _dict.pop('id')
                                _evidencia = EvidenciaActividadDetalleDistributivo(**_dict)
                                _evidencia.criterio = distributivo

                            _evidencia.save(request)

                            _evidencia.anexoevidenciaactividad_set.filter(status=True).delete()
                            for anexo in evidencia.anexoevidenciaactividad_set.filter(status=True):
                                a = AnexoEvidenciaActividad(evidencia=_evidencia, observacion=anexo.observacion, archivo=anexo.archivo)
                                a.save(request)

                            _evidencia.evidenciaactividadaudi_set.filter(status=True).delete()
                            for anexo in evidencia.evidenciaactividadaudi_set.filter(status=True):
                                a = EvidenciaActividadAudi(evidencia=_evidencia, archivo=anexo.archivo)
                                a.save(request)

                            _evidencia.historialaprobacionevidenciaactividad_set.filter(status=True).delete()
                            for anexo in evidencia.historialaprobacionevidenciaactividad_set.filter(status=True):
                                model = HistorialAprobacionEvidenciaActividad(evidencia=_evidencia, aprobacionpersona=anexo.aprobacionpersona, observacion=anexo.observacion, fechaaprobacion=anexo.fechaaprobacion, estadoaprobacion=anexo.estadoaprobacion)
                                model.save(request)
                        else:
                            if kwargs.get('notificar'):
                                if DetalleDistributivo.objects.filter(distributivo__profesor__persona=integrante.persona, distributivo__periodo=detalledistributivo.distributivo.periodo, distributivo__activo=True, status=True).values('id').exists():
                                    gnro = "a" if integrante.persona.es_mujer() else "o"
                                    msj = (f"""Estimad{gnro} {integrante.persona.__str__().lower().title()}, usted se encuentra asociad{gnro} al grupo de investigación "{grupo.nombre}" como <b>{integrante.get_funcion_display().lower().title()}</b> pero no cuenta con el criterio
                                               <b>{detalledistributivo.criterioinvestigacionperiodo.criterio.nombre.lower().title()}</b> en su distributivo de horas.<br><br> Por favor comuníquese con su director de carrera.""")

                                    notificacion("Problemas en el distributivo del docente", msj, integrante.persona, None, 'notificacion', CRITERIO_INTEGRANTE_DIRECTOR_GRUPO_INVESTIGACION, 1, 'sga', CriterioInvestigacion, request)
            except Exception as ex:
                evidencia.delete()
        elif inv.es_actividadmacro:
            if evidencia.subactividad and evidencia.subactividad.subactividaddocenteperiodo.criterio.pk == CRITERIO_DIRECTOR_GRUPOINVESTIGACION:
                # Nueva migracion de evidencias por actividad macro
                if director := GrupoInvestigacionIntegrante.objects.filter(persona=persona, grupo__vigente=True, grupo__status=True, funcion=1, status=True).first():
                    grupo = director.grupo
                    evidencia.grupoinvestigacion = grupo
                    evidencia.save(request)
                    for integrante in grupo.grupoinvestigacionintegrante_set.filter(status=True).exclude(funcion=1):
                        if distributivo := DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=CRITERIO_ACTIVIDAD_MACRO, distributivo__profesor__persona=integrante.persona, distributivo__periodo=periodo, distributivo__activo=True, status=True).first():
                            if subactividad := SubactividadDetalleDistributivo.objects.filter(actividaddetalledistributivo__criterio=distributivo, subactividaddocenteperiodo__criterio=CRITERIO_INTEGRANTE_GRUPOINVESTIGACION, status=True).first():
                                if migracion := MigracionEvidenciaActividad.objects.filter(evidencia__grupoinvestigacion=grupo, evidencia__subactividad=subactividad, evidenciabase=evidencia, status=True).first():
                                    _evidencia = migracion.evidencia
                                    _evidencia.actividaddetalledistributivo = evidencia.actividaddetalledistributivo
                                    _evidencia.desde = evidencia.desde
                                    _evidencia.hasta = evidencia.hasta
                                    _evidencia.actividad = evidencia.actividad
                                    _evidencia.aprobado = evidencia.aprobado
                                    _evidencia.archivo = evidencia.archivo
                                    _evidencia.usuarioaprobado = evidencia.usuarioaprobado
                                    _evidencia.fechaaprobado = evidencia.fechaaprobado
                                    _evidencia.estadoaprobacion = evidencia.estadoaprobacion
                                    _evidencia.archivofirmado = evidencia.archivofirmado
                                    _evidencia.save(request)
                                else:
                                    _dict = EvidenciaActividadDetalleDistributivo.objects.filter(pk=evidencia.pk).values()[0]
                                    _dict.pop('id')
                                    _evidencia = EvidenciaActividadDetalleDistributivo(**_dict)
                                    _evidencia.subactividad = subactividad
                                    _evidencia.criterio = distributivo
                                    _evidencia.save(request)
                                    m = MigracionEvidenciaActividad(evidencia=_evidencia, evidenciabase=evidencia)
                                    m.save(request)

                                _evidencia.anexoevidenciaactividad_set.filter(status=True).delete()
                                for anexo in evidencia.anexoevidenciaactividad_set.filter(status=True):
                                    a = AnexoEvidenciaActividad(evidencia=_evidencia, observacion=anexo.observacion, archivo=anexo.archivo)
                                    a.save(request)

                                _evidencia.evidenciaactividadaudi_set.filter(status=True).delete()
                                for anexo in evidencia.evidenciaactividadaudi_set.filter(status=True):
                                    a = EvidenciaActividadAudi(evidencia=_evidencia, archivo=anexo.archivo)
                                    a.save(request)

                                _evidencia.historialaprobacionevidenciaactividad_set.filter(status=True).delete()
                                for anexo in evidencia.historialaprobacionevidenciaactividad_set.filter(status=True):
                                    model = HistorialAprobacionEvidenciaActividad(evidencia=_evidencia, aprobacionpersona=anexo.aprobacionpersona, observacion=anexo.observacion, fechaaprobacion=anexo.fechaaprobacion, estadoaprobacion=anexo.estadoaprobacion)
                                    model.save(request)
                        else:
                            if kwargs.get('notificar'):
                                if DetalleDistributivo.objects.filter(distributivo__profesor__persona=integrante.persona, distributivo__periodo=detalledistributivo.distributivo.periodo, distributivo__activo=True, status=True).values('id').exists():
                                    gnro = "a" if integrante.persona.es_mujer() else "o"
                                    msj = (f"""Estimad{gnro} {integrante.persona.__str__().lower().title()}, usted se encuentra asociad{gnro} al grupo de investigación "{grupo.nombre}" como <b>{integrante.get_funcion_display().lower().title()}</b> pero no cuenta con el criterio
                                               <b>{detalledistributivo.criterioinvestigacionperiodo.criterio.nombre.lower().title()}</b> en su distributivo de horas.<br><br> Por favor comuníquese con su director de carrera.""")
                                    notificacion("Problemas en el distributivo del docente", msj, integrante.persona, None, 'notificacion', CRITERIO_INTEGRANTE_DIRECTOR_GRUPO_INVESTIGACION, 1, 'sga', CriterioInvestigacion, request)


def genera_archivo_terminos_condiciones(request, terms):
    try:
        persona, data = request.session.get('persona'), {}
        filename = f"{persona.usuario.username}_acuerdo_terminos_condiciones_{terms.pk}.pdf"
        filepath = u"terminoscondiciones/profesor"

        os.makedirs(os.path.join(SITE_STORAGE, 'media', 'terminoscondiciones', ''), exist_ok=True)
        os.makedirs(os.path.join(SITE_STORAGE, 'media', 'terminoscondiciones', 'profesor', ''), exist_ok=True)

        data['term'] = terms.terminos
        data['codigo'] = "%03d" % terms.terminos.pk
        data['fecha_creacion'] = datetime.now()
        data['persona'] = persona

        if convert_html_to_pdf('../inno/templates/pro_laboratoriocronograma/terminos_condiciones_docente.html', data, filename, os.path.join(os.path.join(SITE_STORAGE, 'media', filepath, ''))):
            terms.archivo = filepath + '/' + filename
            terms.save(request)

    except Exception as ex:
        pass


def delete_evidencia_integrante_grupo_proyecto_investigacion(**kwargs):
    try:
        evidencia = kwargs['evidencia']
        if evidencia.estadoaprobacion == 1:
            if ci := evidencia.criterio.criterioinvestigacionperiodo:
                # Integrantes proyecto investigacion
                if ci.criterio.id == 55:
                    funcionacriterio = lambda x: {1: 55, 2: 56, 3: 57}[x] if x in (1, 2, 3) else None
                    if proyecto := ProyectoInvestigacion.objects.filter(profesor=evidencia.criterio.distributivo.profesor, estado_id=37, status=True).exclude(cerrado=True).first():
                        for integrante in proyecto.integrantes_proyecto().exclude(funcion=1):
                            if distributivo := DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=funcionacriterio(integrante.funcion), distributivo__profesor__persona=integrante.profesor.persona if integrante.profesor else integrante.persona, distributivo__periodo=evidencia.criterio.distributivo.periodo, status=True).first():
                                _evidencia = EvidenciaActividadDetalleDistributivo.objects.filter(criterio=distributivo, hasta__month=evidencia.hasta.month, hasta__year=evidencia.hasta.year).first()
                                if _evidencia.estadoaprobacion in (1, 3): _evidencia.delete()

                # Integrantes grupo investigacion
                elif ci.criterio.id == 58:
                    if director := GrupoInvestigacionIntegrante.objects.filter(persona=evidencia.criterio.distributivo.profesor.persona, grupo__vigente=True, grupo__status=True, funcion=1, status=True).first():
                        for integrante in GrupoInvestigacionIntegrante.objects.filter(grupo=director.grupo, grupo__vigente=True, grupo__status=True, status=True).exclude(funcion=1):
                            if distributivo := DetalleDistributivo.objects.filter(criterioinvestigacionperiodo__criterio__id=58, distributivo__profesor__persona=integrante.persona, distributivo__periodo=evidencia.criterio.distributivo.periodo, status=True).first():
                                _evidencia = EvidenciaActividadDetalleDistributivo.objects.filter(criterio=distributivo, hasta__month=evidencia.hasta.month, hasta__year=evidencia.hasta.year).first()
                                if _evidencia.estadoaprobacion in (1, 3): _evidencia.delete()

    except Exception as ex:
        pass


def aprobar_bitacora_termino_plazo(**kwargs):
    try:
        now = datetime.now().date()
        lastmonth = now.month - 1
        if BitacoraActividadDocente.objects.filter(estadorevision=2, status=True).values('id').exists():
            request = kwargs.get('request')
            if variable_valor('VALIDA_REGISTRO_BITACORA_PPPIR') and now.day >= variable_valor('PLAZO_APROBACION_AUTOMATICA_BITACORA'):
                BitacoraActividadDocente.objects.filter(estadorevision=1, fechafin__month=lastmonth, status=True).update(estadorevision=2)
                for bitacora in BitacoraActividadDocente.objects.filter(estadorevision=2, criterio__distributivo__periodo=kwargs.get('periodo'), registrotardio=False, status=True).exclude(fechafin__month=now.month):
                    bitacora.get_detallebitacora().filter(estadoaprobacion=1).update(estadoaprobacion=2, usuario_modificacion=1)
                    bitacora.estadorevision = 3
                    bitacora.save(request)

                    h = HistorialBitacoraActividadDocente(bitacora=bitacora, persona_id=1, estadorevision=bitacora.estadorevision)
                    h.save(request)

    except Exception as ex:
        pass


def profesor_aplicador(profesor, periodo, fini, ffin, eDistributivo):
    try:
        fini = convertir_fecha(fini)
        ffin = convertir_fecha(ffin)
        listado = []
        claseactividad = []
        _result = []
        porcentajetotal = 0
        distributivo = eDistributivo.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo__isnull=False)
        if distributivo:
            if distributivo.filter(criteriodocenciaperiodo__criterio__id=183).exists():  # APLICAR EXAMENES PARCIALES O FINALES
                criterio = distributivo.filter(criteriodocenciaperiodo__criterio__id=183).first()
                claseactividad = ClaseActividad.objects.filter(detalledistributivo=criterio, detalledistributivo__distributivo__profesor=profesor, status=True).order_by('inicio', 'dia', 'turno__comienza')
                inicio, fin = periodo.inicio, periodo.fin
                if actividad := criterio.actividaddetalledistributivo_set.filter(status=True).first():
                    inicio, fin = actividad.desde, actividad.hasta
                dt, end, step = date(ffin.year, ffin.month, 1), ffin, timedelta(days=1)
                while dt <= end:
                    if inicio <= dt <= fin:
                        if not criterio.distributivo.periodo.diasnolaborable_set.values('id').filter(status=True, fecha=dt, activo=True):
                            _result += [dt.strftime('%Y-%m-%d') for dclase in claseactividad.values_list('dia', 'turno_id') if dt.isocalendar()[2] == dclase[0]]
                    dt += step
                if AulaPlanificacionSedeVirtualExamen.objects.filter(responsable=profesor.persona, turnoplanificacion__fechaplanificacion__fecha__range=(fini, ffin),
                                                                     turnoplanificacion__fechaplanificacion__periodo=periodo, status=True).values('id').exists():
                    listado = AulaPlanificacionSedeVirtualExamen.objects.filter(responsable=profesor.persona, turnoplanificacion__fechaplanificacion__fecha__range=(fini, ffin),
                                                                                turnoplanificacion__fechaplanificacion__periodo=periodo, status=True).order_by('turnoplanificacion__fechaplanificacion__fecha')
                    porcentajetotal = 100 if len(listado) > 0 else 0

        return {'listado': listado, 'claseactividad': claseactividad, 'porcentajetotal': porcentajetotal if porcentajetotal <= 100 else 100, 'planificadas_mes': _result.__len__()}
    except Exception as ex:
        return []


def testTraining(asignacion):
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix
    from sklearn import tree
    import matplotlib.pyplot as plt
    data = {
        'feature1': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'feature2': [5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        'label': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    }
    df = pd.DataFrame(data)

    # Separar características y etiquetas
    X = df[['feature1', 'feature2']]
    y = df['label']

    # Dividir los datos en conjuntos de entrenamiento y prueba
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    # Crear el modelo
    clf = DecisionTreeClassifier(random_state=42)

    # Entrenar el modelo
    clf.fit(X_train, y_train)

    # Realizar predicciones en el conjunto de prueba
    y_pred = clf.predict(X_test)

    # Calcular la exactitud
    accuracy = accuracy_score(y_test, y_pred)
    print(f'Accuracy: {accuracy}')

    # Mostrar la matriz de confusión
    conf_matrix = confusion_matrix(y_test, y_pred)
    print(f'Confusion Matrix:\n{conf_matrix}')

    # Visualizar el árbol de decisión
    plt.figure(figsize=(12, 8))
    tree.plot_tree(clf, feature_names=['feature1', 'feature2'], class_names=['0', '1'], filled=True)
    plt.show()


