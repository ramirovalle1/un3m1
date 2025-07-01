# -*- coding: UTF-8 -*-
import os
import subprocess
import json
import sys
from datetime import datetime, timedelta, date

import pyqrcode
import xlwt, time
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, connection,connections
from django.db.models import Q, Max, Count, PROTECT, Sum, Avg, Min
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template import Context
from django.template.loader import get_template
from django.forms import model_to_dict
from xlwt import *
import random
import collections
from decorators import secure_module, last_access
from posgrado.models import InscripcionCohorte
from sagest.commonviews import secuencia_convenio_devengacion
from sagest.forms import CapacitacionPersonaDocenteForm
from sagest.models import DistributivoPersona, LogDia
from settings import PRACTICAS_PREPROFESIONALES_ACTIVAS, \
    MATRICULACION_LIBRE, TIPO_DOCENTE_PRACTICA, SERVER_RESPONSE, TIPO_DOCENTE_AYUDANTIA, JR_JAVA_COMMAND, DATABASES, \
    JR_USEROUTPUT_FOLDER, JR_RUN, MEDIA_URL, SUBREPOTRS_FOLDER, MEDIA_ROOT, SITE_ROOT, DEBUG, SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import PracticaPreProfesionalForm, EvidenciaActividadDetalleDistributivoForm, AvTutoriasForm, \
    AprobarRechazarEvidenciaTutorForm, PonerFechaLimiteEvidenciaForm, RetiroPracticasForm, \
    ArpobarEvidenciaPracticasForm, ConfigurarFechaMasivaPracticaForm, InformeMensualSupervisorPracticaForm, \
    PracticasPreprofesionalesInscripcionSupervisorForm, DetalleDistributivoForm, PlanificarPonenciasForm, \
    PlanificarCapacitacionesForm, PlanificarCapacitacionesArchivoForm, ArticuloInvestigacionDocenteForm, \
    PonenciaInvestigacionDocenteForm, LibroInvestigacionDocenteForm, CapituloLibroInvestigacionDocenteForm, \
    CronogramaTrabajoInvestigacionDocenteForm, TutoriaAdicionalForm, \
    SubirEvidenciaEjecutadoCapacitacionesForm, BecaSolicitudSubirCedulaForm, PonenciaEvidenciaEjecutadoForm, \
    ConfiguracionInformePPPForm, AgendaTutoriaForm, ReemplazarInquietudForm, \
    PracticasPreprofesionalesInscripcionSolicitarForm
from inno.models import RegistroClaseTutoriaDocente, SolicitudTutoriaIndividual
from sga.funciones import log, generar_nombre, MiPaginador, convertir_fecha, variable_valor, null_to_decimal, \
    fechaletra_corta, tituloinstitucion, convertir_fecha_invertida, remover_caracteres_especiales_unicode, notificacion,get_director_vinculacion, \
    null_to_numeric
from sga.funciones_templatepdf import evidenciassilabosxcarrera, evidenciasrecursossilabo, totalestutoriasacademicas
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
    FirmaPersona, AvPreguntaDocente, AperturaPracticaPreProfesional, ESTADO_SOLICITUD_HOMOLOGACION, \
    ESTADOS_PASOS_SOLICITUD, SolicitudHomologacionPracticas, DocumentosSolicitudHomologacionPracticas, \
    CarreraHomologacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado, conviert_html_to_pdfsave, conviert_html_to_pdfsaveqrinformepracticasmensual
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
from sga.reportes import elimina_tildes, transform_jasperstarter_new, run_report_v1
from .formmodel import AgendaPracticasTutoriaForm, ReAgendarAgendaPracticasTutoriasForm, FinalizarAgendaTutoriaForm

unicode =str

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    miscarreras = persona.mis_carreras_tercer_nivel()
    tiene_carreras_director = True if miscarreras else False
    if not tiene_carreras_director:
        return HttpResponseRedirect("/?info=Solo los directores de carreras pueden ingresar al modulo.")
    periodo = request.session['periodo']
    responsablevinculacion = get_director_vinculacion()
    data['es_director_carr'] = tiene_carreras_director

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'notidecano':
                try:
                    soli = SolicitudHomologacionPracticas.objects.get(pk=request.POST['id'])
                    soli.fecha_notificacion_decano = datetime.now()
                    soli.save(request)
                    subject = 'DECANO(A) SOLICITUD DE HOMOLOGACIÓN PENDIENTE DE REVISIÓN {}'.format(soli.inscripcion.persona.__str__())
                    template = 'emails/homologacion_decano.html'
                    datos_email = {'sistema': 'SGA UNEMI', 'filtro': soli}
                    decano = ResponsableCoordinacion.objects.filter(coordinacion=soli.inscripcion.carrera.coordinacion_carrera(), periodo=periodo, tipo=1).first()
                    email_decano = decano.persona.emailinst if decano else ''
                    lista_email = [email_decano, ]
                    send_html_mail(subject, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[4][1])
                    response = JsonResponse({'resp': True})
                except Exception as ex:
                    response = JsonResponse({'resp': False, 'mensaje': ex})
                return HttpResponse(response.content)

            elif action == 'validacionhorashomologar':
                try:
                    with transaction.atomic():
                        filtro = SolicitudHomologacionPracticas.objects.get(pk=int(request.POST['id']))
                        filtro.revision_director = request.POST['estado']
                        filtro.horas_homologadas = request.POST['horas_homologadas']
                        filtro.observacion_director = request.POST['observacion'].upper()
                        filtro.fecha_revision_director = datetime.now()
                        filtro.persona_director = persona
                        filtro.save(request)
                        if filtro.revision_director == '2':
                            filtro.estados = 7
                            messages.success(request, 'Validación de Horas Homologación Rechazada.')
                        else:
                            filtro.estados = 4
                            messages.success(request, 'Validación de Horas Homologación Aprobada.')
                        filtro.save(request)
                        asunto = u"VALIDACIÒN DE HORAS DE HOMOLOGACIÒN PRACTICAS {}".format(filtro.get_estados_display())
                        para = filtro.inscripcion.persona
                        notificacion(asunto, filtro.observacion_director, para, None, '/alu_practicaspro?action=verproceso&id={}'.format(encrypt(filtro.pk)), filtro.pk, 1, 'sga', SolicitudHomologacionPracticas, request)
                        filtro.save(request)
                        log(u'Finalizo Validación de Horas Homologación: {} {}'.format(filtro.inscripcion, filtro.get_revision_director_display()), request, "add")
                        return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'solicitantes':
                data['title'] = u'Solicitantes Homologación'
                data['id'] = id = int(request.GET['id'])
                data['apertura'] = apertura = AperturaPracticaPreProfesional.objects.get(pk=id)
                carreras = apertura.carrerahomologacion_set.filter(status=True)
                valcarreras = False
                carreras = carreras.filter(carrera__in=miscarreras.values_list('id', flat=True))
                valcarreras = True
                data['carreras'] = carreras.order_by('carrera__nombre')
                data['cantidad_carreras'] = len(carreras)
                data['estado_solicitud'] = ESTADO_SOLICITUD_HOMOLOGACION
                data['estado_pasos'] = ESTADOS_PASOS_SOLICITUD
                querybase = SolicitudHomologacionPracticas.objects.filter(apertura=apertura)
                estsolicitud, carreraid, desde, hasta, search, filtros, url_vars = request.GET.get('estsolicitud',''), request.GET.get('carreraid', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('search', ''), Q(status=True), ''
                if estsolicitud:
                    data['estsolicitud'] = estsolicitud = int(estsolicitud)
                    url_vars += "&estsolicitud={}".format(estsolicitud)
                    filtros = filtros & Q(estados=estsolicitud)
                if carreraid:
                    data['carreraid'] = int(carreraid)
                    url_vars += "&carreraid={}".format(carreraid)
                    filtros = filtros & Q(inscripcion__carrera__id=carreraid)
                if desde:
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    filtros = filtros & Q(fecha_creacion__gte=desde)
                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    filtros = filtros & Q(fecha_creacion__lte=hasta)
                if search:
                    data['search'] = search
                    s = search.split()
                    if len(s) == 1:
                        filtros = filtros & (Q(itinerario__persona__apellido2__icontains=search) | Q(
                            itinerario__persona__cedula__icontains=search) | Q(
                            itinerario__persona__apellido1__icontains=search))
                    else:
                        filtros = filtros & (Q(itinerario__persona__apellido1__icontains=s[0]) & Q(
                            itinerario__persona__apellido2__icontains=s[1]))
                    url_vars += '&search={}'.format(search)
                url_vars += '&action={}&id={}'.format(action, id)
                data["url_vars"] = url_vars
                if valcarreras:
                    query = querybase.filter(filtros).select_related('inscripcion').filter(
                        inscripcion__carrera__in=carreras.values_list('carrera_id', flat=True)).order_by('-pk')
                else:
                    query = querybase.select_related('inscripcion').filter(filtros).order_by('-pk')
                data['listcount'] = query.count()
                paging = MiPaginador(query, 25)
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
                data['lista'] = page.object_list
                return render(request, "dir_cronograma/solicitanteshomologacion.html", data)

            elif action == 'verdocumentos':
                try:
                    data['solicitud'] = solicitud = SolicitudHomologacionPracticas.objects.get(
                        pk=int(request.GET['id']))
                    ESTADOS_PASOS_SOLICITUD_1 = (
                        (1, u'APROBADO'),
                        (2, u'RECHAZADO')
                    )
                    data['estados'] = ESTADOS_PASOS_SOLICITUD_1
                    ESTADOS_DOCUMENTOS = (
                        (1, u'APROBADO'),
                        (3, u'CORREGIR')
                    )
                    data['estados_documentos'] = ESTADOS_DOCUMENTOS
                    data['documentos'] = DocumentosSolicitudHomologacionPracticas.objects.filter(solicitud=solicitud, status=True).order_by('documento__documento__nombre')
                    template = get_template('dir_cronograma/modal/documentoshomologacionsolicitud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'verproceso':
                try:
                    data['solicitud'] = solicitud = SolicitudHomologacionPracticas.objects.get(
                        pk=int(request.GET['id']))
                    data['documentos'] = documentos = DocumentosSolicitudHomologacionPracticas.objects.filter(
                        solicitud=solicitud).order_by('documento__documento__nombre')
                    data['filtro'] = filtro = solicitud.apertura
                    carreraqs = CarreraHomologacion.objects.filter(apertura=filtro,
                                                                   carrera=solicitud.inscripcion.carrera)
                    form = PracticasPreprofesionalesInscripcionSolicitarForm(initial=model_to_dict(solicitud))
                    malla = solicitud.inscripcion.mi_malla()
                    nivel = solicitud.inscripcion.mi_nivel().nivel
                    form.cargar_itinerario(malla, nivel)
                    form.ver_proceso()
                    data['form'] = form
                    if carreraqs.exists():
                        data['carrerahomologacion'] = carreraqs.first()
                    pasoactual = 1
                    data['paso2'] = paso2 = False if not documentos.exists() else True
                    data['paso3'] = paso3 = False if not solicitud.revision_vinculacion == 1 else True
                    data['paso4'] = paso4 = False if not solicitud.revision_director == 1 else True
                    data['paso5'] = paso5 = False if not solicitud.estados == 1 else True
                    if paso2:
                        pasoactual = 2
                    if paso3:
                        pasoactual = 3
                    if paso4:
                        pasoactual = 4
                    if paso5:
                        pasoactual = 5
                    data['pasoactual'] = pasoactual
                    template = get_template('dir_cronograma/modal/modalproceso.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

            elif action == 'validarhorashomologacion':
                try:
                    data['solicitud'] = solicitud = SolicitudHomologacionPracticas.objects.get(
                        pk=int(request.GET['id']))
                    data['documentos'] = documentos = DocumentosSolicitudHomologacionPracticas.objects.filter(
                        solicitud=solicitud).order_by('documento__documento__nombre')
                    data['filtro'] = filtro = solicitud.apertura
                    carreraqs = CarreraHomologacion.objects.filter(apertura=filtro, carrera=solicitud.inscripcion.carrera)
                    form = PracticasPreprofesionalesInscripcionSolicitarForm(initial=model_to_dict(solicitud))
                    malla = solicitud.inscripcion.mi_malla()
                    nivel = solicitud.inscripcion.mi_nivel().nivel
                    form.cargar_itinerario(malla, nivel)
                    form.ver_proceso()
                    data['form'] = form
                    if carreraqs.exists():
                        data['carrerahomologacion'] = carreraqs.first()
                    pasoactual = 1
                    data['paso2'] = paso2 = False if not documentos.exists() else True
                    data['paso3'] = paso3 = False if not solicitud.revision_vinculacion == 1 else True
                    data['paso4'] = paso4 = False if not solicitud.revision_director == 1 else True
                    data['paso5'] = paso5 = False if not solicitud.estados == 1 else True
                    if paso2:
                        pasoactual = 2
                    if paso3:
                        pasoactual = 3
                    if paso4:
                        pasoactual = 4
                    if paso5:
                        pasoactual = 5
                    data['pasoactual'] = pasoactual
                    template = get_template('dir_cronograma/modal/validardirectordecano.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": ex})

    try:
        data['title'] = u'Actividades Director de Carrera'
        periodo = request.session['periodo']
        data['periodos_homologacion'] = AperturaPracticaPreProfesional.objects.filter(status=True, periodo=periodo).order_by('-pk')
        return render(request, "dir_cronograma/view.html", data)
    except Exception as ex:
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
